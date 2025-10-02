import uuid
import io
import csv
import json
import zipfile
from typing import List, Optional, Dict, Any
from bson import ObjectId
from db.utils import get_db
from util.helpers import utcnow_iso, format_datetime, generate_uuid

db = get_db()

def _normalize(doc: Dict[str, Any]) -> Dict[str, Any]:
    out = {}
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            out[k] = str(v)
        else:
            out[k] = v
    return out

def create_log(project: str, level: str, message: str,
               tags: Optional[List[str]] = None,
               data: Optional[Dict] = None,
               request_id: Optional[str] = None) -> str:
    log_doc = {
        "id": str(generate_uuid),
        "timestamp": utcnow_iso(),
        "project": project,
        "level": level,
        "message": message,
        "tags": tags or [],
        "data": data or {},
        "request_id": request_id or None,
    }
    db["logs"].insert_one(log_doc)
    return log_doc["id"]

def list_logs(project: Optional[str] = None) -> List[Dict[str, Any]]:
    query = {}
    if project:
        query["project"] = project
    docs = list(db["logs"].find(query).sort("timestamp", -1).limit(1000))
    return [_normalize(d) for d in docs]

def latest_timestamp(project: Optional[str] = None) -> Optional[str]:
    query = {}
    if project:
        query["project"] = project
    doc = db["logs"].find_one(query, sort=[("timestamp", -1)])
    return doc["timestamp"] if doc else None

def level_counts(project: Optional[str] = None) -> List[Dict[str, Any]]:
    pipeline: List[Dict[str, Any]] = []

    if project:
        pipeline.append({"$match": {"project": project}})

    pipeline.extend([
        # Normaliza o campo 'level' para UPPER antes de agrupar
        {"$addFields": {"_norm_level": {"$toUpper": "$level"}}},
        {"$group": {"_id": "$_norm_level", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
        {"$project": {"level": "$_id", "_id": 0, "count": 1}}
    ])

    return list(db["logs"].aggregate(pipeline))

def generate_logs_csv(project: Optional[str] = None):
    query: Dict[str, Any] = {}
    if project:
        query["project"] = project

    docs = list(db["logs"].find(query, {
        "_id": 0,
        "id": 1,
        "timestamp": 1,
        "project": 1,
        "level": 1,
        "message": 1,
        "tags": 1,
        "data": 1,
        "request_id": 1
    }).sort("timestamp", -1))

    output = io.StringIO()
    fieldnames = ["id", "timestamp", "project", "level", "message", "tags", "data", "request_id"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for d in docs:
        norm_level = (d.get("level") or "")
        if isinstance(norm_level, str):
            norm_level = norm_level.upper()

        tags_val = d.get("tags") or []
        if isinstance(tags_val, list):
            tags_str = ";".join(map(str, tags_val))
        else:
            tags_str = str(tags_val)

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
            "request_id": d.get("request_id", "") or ""
        })

    output.seek(0)

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("logs.csv", output.getvalue())
    zip_buffer.seek(0)
    return zip_buffer
