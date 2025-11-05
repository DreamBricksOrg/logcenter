from __future__ import annotations

from typing import Optional, List, Dict, Any
from bson import ObjectId

from db.utils import get_db


async def _active_project_ids(db) -> List[str]:
    cur = db["projects"].find({"status": "active"}, {"_id": 1})
    return [str(d["_id"]) async for d in cur]


async def _restrict_to_active_and_visibility(
    visibility: Optional[Dict[str, Any]],
    project_id: Optional[str],
) -> Dict[str, Any]:
    """
    $match com:
      - Apenas projetos ATIVOS.
      - Restrições de visibilidade (project_ids permitidos).
      - Opcionalmente força um único project_id (se ativo/visível).
    """
    db = await get_db()
    active_ids = await _active_project_ids(db)
    if not active_ids:
        return {"project_id": {"$in": []}}

    match: Dict[str, Any] = {"project_id": {"$in": [ObjectId(x) for x in active_ids]}}

    if visibility and "project_id" in visibility:
        vis = visibility["project_id"]
        if isinstance(vis, dict) and "$in" in vis:
            # restringe ao cruzamento: visíveis ∩ ativos
            allowed = [ObjectId(x) for x in vis["$in"] if x in active_ids]
            match["project_id"] = {"$in": allowed}
        else:
            if str(vis) not in active_ids:
                return {"project_id": {"$in": []}}
            match["project_id"] = ObjectId(str(vis))

    if project_id:
        if project_id not in active_ids:
            return {"project_id": {"$in": []}}
        # cruza se já existir $in
        if isinstance(match.get("project_id"), dict) and "$in" in match["project_id"]:
            current = set(match["project_id"]["$in"])
            only = {ObjectId(project_id)}
            inter = list(current & only)
            match["project_id"] = {"$in": inter}
        else:
            match["project_id"] = ObjectId(project_id)

    return match


def _apply_time_window(match: Dict[str, Any], gte: Optional[str], lte: Optional[str]) -> Dict[str, Any]:
    if gte or lte:
        cond: Dict[str, Any] = {}
        if gte:
            cond["$gte"] = gte
        if lte:
            cond["$lte"] = lte
        match["timestamp"] = cond
    return match


async def dash_level_counts(
    project_id: Optional[str],
    timestamp_gte: Optional[str],
    timestamp_lte: Optional[str],
    levels: Optional[List[str]],
    limit: int,
    visibility: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Conta logs agrupados por level (UPPER), respeitando:
      - projetos ATIVOS, visibilidade, janela temporal.
      - filtro opcional de levels (case-insensitive).
    """
    db = await get_db()
    match = await _restrict_to_active_and_visibility(visibility, project_id)
    match = _apply_time_window(match, timestamp_gte, timestamp_lte)

    if levels:
        match["level"] = {"$in": [lvl.upper() for lvl in levels]}

    pipeline = [
        {"$match": match},
        {"$project": {"level_norm": {"$toUpper": {"$ifNull": ["$level", "UNKNOWN"]}}}},
        {"$group": {"_id": "$level_norm", "count": {"$sum": 1}}},
        {"$project": {"_id": 0, "level": "$_id", "count": 1}},
        {"$sort": {"count": -1, "level": 1}},
        {"$limit": int(limit)},
    ]
    return [doc async for doc in db["logs"].aggregate(pipeline)]


async def dash_top_users(
    project_id: Optional[str],
    timestamp_gte: Optional[str],
    timestamp_lte: Optional[str],
    limit: int,
    visibility: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Conta usuários. Considera: user_email, user, user.id, actor, actor.email.
    """
    db = await get_db()
    match = await _restrict_to_active_and_visibility(visibility, project_id)
    match = _apply_time_window(match, timestamp_gte, timestamp_lte)

    user_expr = {
        "$ifNull": [
            "$user_email",
            {"$ifNull": ["$user", {"$ifNull": ["$user.id", {"$ifNull": ["$actor", {"$ifNull": ["$actor.email", "unknown"]}]}]}]},
        ]
    }

    pipeline = [
        {"$match": match},
        {"$project": {"user": user_expr}},
        {"$group": {"_id": "$user", "count": {"$sum": 1}}},
        {"$sort": {"count": -1, "_id": 1}},
        {"$limit": int(limit)},
        {"$project": {"_id": 0, "user": "$_id", "count": 1}},
    ]
    return [doc async for doc in db["logs"].aggregate(pipeline)]


async def dash_top_endpoints(
    project_id: Optional[str],
    timestamp_gte: Optional[str],
    timestamp_lte: Optional[str],
    limit: int,
    visibility: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Conta endpoints/URLs. Tenta em ordem:
      - Campos top-level: endpoint, path, request.path, url, request.url
      - Campos em data.*:  data.endpoint, data.path, data.request.path, data.url, data.request.url
      - Fallback: primeiro valor string em data que pareça endpoint (regex ^/ ou ^https?://)
    Normaliza: minúsculas e sem query string.
    """
    db = await get_db()
    match = await _restrict_to_active_and_visibility(visibility, project_id)
    match = _apply_time_window(match, timestamp_gte, timestamp_lte)

    candidate = {
        "$ifNull": [
            "$endpoint",
            {"$ifNull": [
                "$path",
                {"$ifNull": [
                    "$request.path",
                    {"$ifNull": [
                        "$url",
                        {"$ifNull": [
                            "$request.url",
                            {"$ifNull": [
                                "$data.endpoint",
                                {"$ifNull": [
                                    "$data.path",
                                    {"$ifNull": [
                                        "$data.request.path",
                                        {"$ifNull": [
                                            "$data.url",
                                            {"$ifNull": ["$data.request.url", None]}
                                        ]}
                                    ]}
                                ]}
                            ]}
                        ]}
                    ]}
                ]}
            ]}
        ]
    }

    fallback_from_data = {
        "$let": {
            "vars": {
                "arr": {"$objectToArray": {"$ifNull": ["$data", {}]}},
                "hits": {
                    "$filter": {
                        "input": {"$objectToArray": {"$ifNull": ["$data", {}]}},
                        "as": "kv",
                        "cond": {
                            "$and": [
                                {"$eq": [{"$type": "$$kv.v"}, "string"]},
                                {"$or": [
                                    {"$regexMatch": {"input": "$$kv.v", "regex": r"^/"}},
                                    {"$regexMatch": {"input": "$$kv.v", "regex": r"^https?://"}}
                                ]}
                            ]
                        },
                    }
                },
            },
            "in": {"$cond": [
                {"$gt": [{"$size": "$$hits"}, 0]},
                {"$first": {"$map": {"input": "$$hits", "as": "h", "in": "$$h.v"}}},
                None
            ]}
        }
    }

    endpoint_expr = {
        "$ifNull": [
            candidate,
            {"$ifNull": [fallback_from_data, "unknown"]}
        ]
    }

    normalized = {
        "$toLower": {
            "$let": {
                "vars": {"raw": endpoint_expr},
                "in": {"$first": {"$split": ["$$raw", "?"]}}
            }
        }
    }

    pipeline = [
        {"$match": match},
        {"$project": {"endpoint": normalized}},
        {"$group": {"_id": "$endpoint", "count": {"$sum": 1}}},
        {"$sort": {"count": -1, "_id": 1}},
        {"$limit": int(limit)},
        {"$project": {"_id": 0, "endpoint": "$_id", "count": 1}},
    ]

    return [doc async for doc in db["logs"].aggregate(pipeline)]


async def dash_top_tags(
    project_id: Optional[str],
    timestamp_gte: Optional[str],
    timestamp_lte: Optional[str],
    limit: int,
    visibility: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Conta tags. Garante array com ifNull e filtra tipos indevidos.
    """
    db = await get_db()
    match = await _restrict_to_active_and_visibility(visibility, project_id)
    match = _apply_time_window(match, timestamp_gte, timestamp_lte)

    pipeline = [
        {"$match": match},
        {"$project": {"tags": {"$ifNull": ["$tags", []]}}},
        {"$unwind": "$tags"},
        {"$match": {"tags": {"$type": "string"}}},
        {"$group": {"_id": "$tags", "count": {"$sum": 1}}},
        {"$sort": {"count": -1, "_id": 1}},
        {"$limit": int(limit)},
        {"$project": {"_id": 0, "tag": "$_id", "count": 1}},
    ]
    return [doc async for doc in db["logs"].aggregate(pipeline)]


async def dash_top_data_keys(
    project_id: Optional[str],
    timestamp_gte: Optional[str],
    timestamp_lte: Optional[str],
    limit: int,
    visibility: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Conta a ocorrência de CHAVES dentro de data (usa objectToArray).
    """
    db = await get_db()
    match = await _restrict_to_active_and_visibility(visibility, project_id)
    match = _apply_time_window(match, timestamp_gte, timestamp_lte)

    pipeline: List[Dict[str, Any]] = [
        {"$match": match},
        {"$addFields": {"_kv": {"$objectToArray": {"$ifNull": ["$data", {}]}}}},
        {"$unwind": {"path": "$_kv", "preserveNullAndEmptyArrays": False}},
        {"$group": {"_id": "$_kv.k", "count": {"$sum": 1}}},
        {"$sort": {"count": -1, "_id": 1}},
        {"$limit": int(limit)},
        {"$project": {"_id": 0, "key": "$_id", "count": 1}},
    ]
    return [doc async for doc in db["logs"].aggregate(pipeline)]


async def dash_top_data_values(
    project_id: Optional[str],
    timestamp_gte: Optional[str],
    timestamp_lte: Optional[str],
    limit: int,
    visibility: Optional[Dict[str, Any]],
    item: Optional[str] = None,  # <— NOVO
) -> List[Dict[str, Any]]:
    """
    Conta combinações (chave,value) em data. Quando 'item' é informado,
    conta apenas os valores daquela chave, devolvendo [{item, value, count}].
    """
    db = await get_db()
    match = await _restrict_to_active_and_visibility(visibility, project_id)
    match = _apply_time_window(match, timestamp_gte, timestamp_lte)

    pipeline = [
        {"$match": match},
        {"$addFields": {"_pairs": {"$objectToArray": {"$ifNull": ["$data", {}]}}}},
        {"$unwind": "$_pairs"},
    ]

    if item:
        pipeline += [
            {"$match": {"_pairs.k": item}},
            {"$group": {"_id": "$_pairs.v", "count": {"$sum": 1}}},
            {"$sort": {"count": -1, "_id": 1}},
            {"$limit": int(limit)},
            {"$project": {"_id": 0, "item": {"$literal": item}, "value": "$_id", "count": 1}},
        ]
    else:
        pipeline += [
            {"$group": {"_id": {"k": "$_pairs.k", "v": "$_pairs.v"}, "count": {"$sum": 1}}},
            {"$sort": {"count": -1, "_id.k": 1, "_id.v": 1}},
            {"$limit": int(limit)},
            {"$project": {"_id": 0, "item": "$_id.k", "value": "$_id.v", "count": 1}},
        ]

    return [doc async for doc in db["logs"].aggregate(pipeline)]
