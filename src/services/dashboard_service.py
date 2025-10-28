from __future__ import annotations

from typing import Optional, List, Dict, Any
from bson import ObjectId
from db.utils import get_db


async def _active_project_ids() -> List[ObjectId]:
    db = await get_db()
    cursor = db["projects"].find({"status": "active"}, {"_id": 1})
    return [doc["_id"] async for doc in cursor]

def _coerce_oid(value: Any) -> Optional[ObjectId]:
    try:
        return ObjectId(str(value))
    except Exception:
        return None

async def _visibility_only_active(visibility: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Retorna um filtro de visibilidade SEMPRE restrito a projetos ATIVOS.
    - Sempre devolve project_id como ObjectId (não string).
    - Se 'visibility' trouxer project_id (single ou $in), cruza com ativos.
    """
    active_ids = await _active_project_ids()
    if not active_ids:
        return {"project_id": {"$in": []}}

    if not visibility:
        return {"project_id": {"$in": active_ids}}

    vis = dict(visibility)
    if "project_id" in vis:
        val = vis["project_id"]

        if isinstance(val, dict) and "$in" in val:
            converted: List[ObjectId] = []
            for x in val["$in"]:
                oid = _coerce_oid(x)
                if oid is not None:
                    converted.append(oid)
            final_in = [oid for oid in converted if oid in set(active_ids)]
            vis["project_id"] = {"$in": final_in}
            return vis

        oid = _coerce_oid(val)
        if oid is None or oid not in set(active_ids):
            return {"project_id": {"$in": []}}
        vis["project_id"] = oid
        return vis

    # Sem project_id explícito: injeta $in com ativos
    vis["project_id"] = {"$in": active_ids}
    return vis


async def _build_match(
    *,
    project_id: Optional[str] = None,
    timestamp_gte: Optional[str] = None,
    timestamp_lte: Optional[str] = None,
    levels: Optional[List[str]] = None,
    visibility: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Monta um estágio $match válido SEMPRE.
    - Intersecciona visibilidade com projetos ATIVOS (sempre ObjectId).
    - Se project_id for inválido ou não autorizado, retorna $match que zera o resultado.
    """
    vis = await _visibility_only_active(visibility)

    match_stage: Dict[str, Any] = {}
    if vis:
        match_stage.update(vis)

    if project_id:
        pid = _coerce_oid(project_id)
        if pid is None:
            return {"$match": {"project_id": {"$in": []}}}

        if "project_id" in match_stage and isinstance(match_stage["project_id"], dict) and "$in" in match_stage["project_id"]:
            allowed: set[ObjectId] = set(match_stage["project_id"]["$in"])
            if pid not in allowed:
                return {"$match": {"project_id": {"$in": []}}}

        match_stage["project_id"] = pid

    if timestamp_gte or timestamp_lte:
        match_stage["timestamp"] = {}
        if timestamp_gte:
            match_stage["timestamp"]["$gte"] = timestamp_gte
        if timestamp_lte:
            match_stage["timestamp"]["$lte"] = timestamp_lte

    if levels:
        match_stage["level"] = {"$in": [lvl.upper() for lvl in levels]}

    return {"$match": match_stage}



async def dash_level_counts(
    *,
    project_id: Optional[str] = None,
    timestamp_gte: Optional[str] = None,
    timestamp_lte: Optional[str] = None,
    levels: Optional[List[str]] = None,
    visibility: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Conta logs agrupados por level (UPPER), respeitando:
      - projetos ATIVOS,
      - visibilidade,
      - filtros opcionais de project_id e tempo.
    """
    db = await get_db()
    pipeline: List[Dict[str, Any]] = []

    match_stage = await _build_match(
        project_id=project_id,
        timestamp_gte=timestamp_gte,
        timestamp_lte=timestamp_lte,
        levels=levels,
        visibility=visibility,
    )
    pipeline.append(match_stage)

    pipeline += [
        {"$addFields": {"_norm_level": {"$toUpper": "$level"}}},
        {"$group": {"_id": "$_norm_level", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$project": {"level": "$_id", "count": 1, "_id": 0}},
        {"$limit": 50},
    ]
    return [doc async for doc in db["logs"].aggregate(pipeline)]


async def dash_top_users(
    *,
    project_id: Optional[str] = None,
    timestamp_gte: Optional[str] = None,
    timestamp_lte: Optional[str] = None,
    visibility: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Top usuários por contagem (usa data.userId), respeitando ativos/visibilidade e tempo.
    Ignora userId nulo.
    """
    db = await get_db()
    pipeline: List[Dict[str, Any]] = []

    match_stage = await _build_match(
        project_id=project_id,
        timestamp_gte=timestamp_gte,
        timestamp_lte=timestamp_lte,
        levels=None,
        visibility=visibility,
    )
    pipeline.append(match_stage)

    pipeline += [
        {"$match": {"data.userId": {"$exists": True, "$ne": None}}},
        {"$group": {"_id": "$data.userId", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$project": {"userId": "$_id", "count": 1, "_id": 0}},
        {"$limit": 50},
    ]
    return [doc async for doc in db["logs"].aggregate(pipeline)]


async def dash_top_endpoints(
    *,
    project_id: Optional[str] = None,
    timestamp_gte: Optional[str] = None,
    timestamp_lte: Optional[str] = None,
    visibility: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Top endpoints por contagem (usa data.endpoint), respeitando ativos/visibilidade e tempo.
    Ignora endpoint nulo.
    """
    db = await get_db()
    pipeline: List[Dict[str, Any]] = []

    match_stage = await _build_match(
        project_id=project_id,
        timestamp_gte=timestamp_gte,
        timestamp_lte=timestamp_lte,
        levels=None,
        visibility=visibility,
    )
    pipeline.append(match_stage)

    pipeline += [
        {"$match": {"data.endpoint": {"$exists": True, "$ne": None}}},
        {"$group": {"_id": "$data.endpoint", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$project": {"endpoint": "$_id", "count": 1, "_id": 0}},
        {"$limit": 50},
    ]
    return [doc async for doc in db["logs"].aggregate(pipeline)]
