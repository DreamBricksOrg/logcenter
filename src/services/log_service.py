import uuid
import io
import csv
import json
import zipfile
from typing import List, Optional, Dict, Any
from bson import ObjectId
from db.utils import get_db
from util.helpers import utcnow_iso, format_datetime, generate_uuid
from services.stream_service import manager


def _normalize(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Normaliza ObjectId -> str para JSON serializável."""
    out = {}
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            out[k] = str(v)
        else:
            out[k] = v
    return out


async def create_log(
    project: str,
    level: str,
    message: str,
    tags: Optional[List[str]] = None,
    data: Optional[Dict] = None,
    request_id: Optional[str] = None,
) -> str:
    """Cria e insere log no MongoDB + emite broadcast."""
    log_doc = {
        "id": str(generate_uuid()),
        "timestamp": utcnow_iso(),
        "project": project,
        "level": level,
        "message": message,
        "tags": tags or [],
        "data": data or {},
        "request_id": request_id or None,
    }

    db = await get_db()

    await db["logs"].insert_one(log_doc)

    # envia broadcast em tempo real
    await manager.broadcast(
        project,
        json.dumps(log_doc, ensure_ascii=False, separators=(",", ":"))
    )

    return log_doc["id"]


async def list_logs(
    project: Optional[str] = None,
    visibility: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Lista até 1000 logs mais recentes.
    Aplica visibilidade se fornecida (ex: enforce_visibility).
    """
    db = await get_db()

    query: Dict[str, Any] = {}
    if visibility:
        query.update(visibility)

    if project:
        # Se já existe filtro de visibilidade com $in, restringe sem permitir bypass
        if "project" in query and isinstance(query["project"], dict) and "$in" in query["project"]:
            if project not in query["project"]["$in"]:
                return []  # cliente tentando acessar projeto que não pode
        query["project"] = project

    cursor = db["logs"].find(query).sort("timestamp", -1).limit(1000)
    docs = await cursor.to_list(length=1000)

    # Normaliza ObjectId -> str
    for d in docs:
        if "_id" in d:
            d["_id"] = str(d["_id"])
    return docs


async def latest_timestamp(project: Optional[str] = None) -> Optional[str]:
    """Retorna timestamp mais recente de log de um projeto."""
    db = await get_db()
    query = {}
    if project:
        query["project"] = project

    doc = await db["logs"].find_one(query, sort=[("timestamp", -1)])
    return doc["timestamp"] if doc else None


async def level_counts(project: Optional[str] = None) -> List[Dict[str, Any]]:
    """Conta logs agrupados por nível normalizado (UPPER)."""
    pipeline: List[Dict[str, Any]] = []

    if project:
        pipeline.append({"$match": {"project": project}})

    pipeline.extend([
        # Normaliza o campo 'level' para UPPER antes de agrupar
        {"$addFields": {"_norm_level": {"$toUpper": "$level"}}},
        {"$group": {"_id": "$_norm_level", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
        {"$project": {"level": "$_id", "_id": 0, "count": 1}},
    ])
    db = await get_db()

    cursor = db["logs"].aggregate(pipeline)
    return [doc async for doc in cursor]


async def generate_logs_csv(project: Optional[str] = None) -> io.BytesIO:
    """Exporta logs em CSV dentro de um ZIP."""
    db = await get_db()

    query: Dict[str, Any] = {}
    if project:
        query["project"] = project

    cursor = db["logs"].find(query, {
        "_id": 0,
        "id": 1,
        "timestamp": 1,
        "project": 1,
        "level": 1,
        "message": 1,
        "tags": 1,
        "data": 1,
        "request_id": 1,
    }).sort("timestamp", -1)

    docs = await cursor.to_list(length=10000)

    output = io.StringIO()
    fieldnames = ["id", "timestamp", "project", "level", "message", "tags", "data", "request_id"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for d in docs:
        norm_level = (d.get("level") or "")
        if isinstance(norm_level, str):
            norm_level = norm_level.upper()

        tags_val = d.get("tags") or []
        tags_str = ";".join(map(str, tags_val)) if isinstance(tags_val, list) else str(tags_val)

        data_val = d.get("data") or {}
        try:
            data_json = json.dumps(data_val, ensure_ascii=False, separators=(",", ":"))
        except Exception:
            data_json = "{}"

        writer.writerow({
            "id": d.get("id", ""),
            "timestamp": d.get("timestamp", ""),
            "project": d.get("project", ""),
            "level": norm_level,
            "message": d.get("message", ""),
            "tags": tags_str,
            "data": data_json,
            "request_id": d.get("request_id", "") or "",
        })

    output.seek(0)

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("logs.csv", output.getvalue())
    zip_buffer.seek(0)
    return zip_buffer
