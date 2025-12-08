from __future__ import annotations

from typing import Optional, List, Dict, Any
from bson import ObjectId

from db.utils import get_db
from util.queries import (
    apply_extra_filters,
    restrict_to_active_and_visibility,
    apply_time_window,
)

RESERVED_KEYS = {"levels", "item"}


async def dash_level_counts(
    project_id: Optional[str],
    timestamp_gte: Optional[str],
    timestamp_lte: Optional[str],
    levels: Optional[List[str]],
    limit: int,
    visibility: Optional[Dict[str, Any]],
    extra_filters: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Conta logs agrupados por level (UPPER), respeitando:
      - projetos ATIVOS, visibilidade, janela temporal.
      - filtro opcional de levels (case-insensitive).
    """
    db = await get_db()

    match = await restrict_to_active_and_visibility(visibility, project_id)
    match = apply_time_window(match, timestamp_gte, timestamp_lte)

    if levels:
        match["level"] = {"$in": [lvl.upper() for lvl in levels]}

    match = apply_extra_filters(match, extra_filters, reserved_keys=RESERVED_KEYS)

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
    extra_filters: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Conta usuários. Considera: user_email, user, user.id, actor, actor.email.
    """
    db = await get_db()

    match = await restrict_to_active_and_visibility(visibility, project_id)
    match = apply_time_window(match, timestamp_gte, timestamp_lte)
    match = apply_extra_filters(match, extra_filters, reserved_keys=RESERVED_KEYS)

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
    extra_filters: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Conta endpoints/URLs. Tenta em ordem:
      - Campos top-level: endpoint, path, request.path, url, request.url
      - Campos em data.*:  data.endpoint, data.path, data.request.path, data.url, data.request.url
      - Fallback: primeiro valor string em data que pareça endpoint (regex ^/ ou ^https?://)
    Normaliza: minúsculas e sem query string.
    """
    db = await get_db()

    match = await restrict_to_active_and_visibility(visibility, project_id)
    match = apply_time_window(match, timestamp_gte, timestamp_lte)
    match = apply_extra_filters(match, extra_filters, reserved_keys=RESERVED_KEYS)

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

    endpoint_expr = {"$ifNull": [candidate, {"$ifNull": [fallback_from_data, "unknown"]}]}

    normalized = {
        "$toLower": {
            "$let": {
                "vars": {"raw": endpoint_expr},
                "in": {"$first": {"$split": ["$$raw", "?"]}},
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
    extra_filters: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Conta tags. Garante array com ifNull e filtra tipos indevidos.
    """
    db = await get_db()

    match = await restrict_to_active_and_visibility(visibility, project_id)
    match = apply_time_window(match, timestamp_gte, timestamp_lte)
    match = apply_extra_filters(match, extra_filters, reserved_keys=RESERVED_KEYS)

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


async def dash_top_messages(
    project_id: Optional[str],
    timestamp_gte: Optional[str],
    timestamp_lte: Optional[str],
    limit: int,
    visibility: Optional[Dict[str, Any]],
    extra_filters: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Conta mensagens (campo 'message').
    - Respeita projetos ATIVOS, visibilidade e janela temporal.
    - Considera apenas docs em que message é string.
    - Filtros adicionais extra_filters, regex message__regex="timeout".
    """
    db = await get_db()

    match = await restrict_to_active_and_visibility(visibility, project_id)
    match = apply_time_window(match, timestamp_gte, timestamp_lte)
    match = apply_extra_filters(match, extra_filters, reserved_keys=RESERVED_KEYS)

    pipeline: List[Dict[str, Any]] = [
        {"$match": match},
        {"$match": {"message": {"$type": "string"}}},
        {"$group": {"_id": "$message", "count": {"$sum": 1}}},
        {"$sort": {"count": -1, "_id": 1}},
        {"$limit": int(limit)},
        {"$project": {"_id": 0, "message": "$_id", "count": 1}},
    ]
    return [doc async for doc in db["logs"].aggregate(pipeline)]


async def dash_top_data_keys(
    project_id: Optional[str],
    timestamp_gte: Optional[str],
    timestamp_lte: Optional[str],
    limit: int,
    visibility: Optional[Dict[str, Any]],
    extra_filters: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Conta a ocorrência de CHAVES dentro de data (usa objectToArray).
    """
    db = await get_db()

    match = await restrict_to_active_and_visibility(visibility, project_id)
    match = apply_time_window(match, timestamp_gte, timestamp_lte)
    match = apply_extra_filters(match, extra_filters, reserved_keys=RESERVED_KEYS)

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
    item: Optional[str] = None,
    extra_filters: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Conta combinações (chave,value) em data. Quando 'item' é informado,
    conta apenas os valores daquela chave, devolvendo [{item, value, count}].
    """
    db = await get_db()

    match = await restrict_to_active_and_visibility(visibility, project_id)
    match = apply_time_window(match, timestamp_gte, timestamp_lte)
    match = apply_extra_filters(match, extra_filters, reserved_keys=RESERVED_KEYS)

    pipeline: List[Dict[str, Any]] = [
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
