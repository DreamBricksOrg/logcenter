import io
import csv
import json
import zipfile
import openpyxl
from openpyxl.utils import get_column_letter
from typing import List, Optional, Dict, Any
from bson import ObjectId
from db.utils import get_db
from util.helpers import utcnow_iso, format_datetime
from services.stream_service import manager

def build_filter(params: Dict[str, Any]) -> Dict[str, Any]:
    """Filtro a partir de parâmetros de query.
    Suporta operadores __in (lista separada por vírgula), __gte, __lte, __regex e igualdade simples."""
    filt: Dict[str, Any] = {}
    for key, value in params.items():
        if key.startswith("_") or not value:
            continue
        if "__" in key:
            field, op = key.split("__", 1)
        else:
            field, op = key, None

        if op == "in":
            filt[field] = {"$in": value.split(",")}
        elif op == "gte":
            filt[field] = {"$gte": value}
        elif op == "lte":
            filt[field] = {"$lte": value}
        elif op == "regex":
            filt[field] = {"$regex": value}
        else:
            filt[field] = value
    return filt

def _serialize_ids(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Normaliza ObjectId -> str em _id e project_id para resposta JSON."""
    out = dict(doc)
    for k in ["_id", "project_id"]:
        if k in out and isinstance(out[k], ObjectId):
            out[k] = str(out[k])
    if "status" not in out:
        out["status"] = str(out.get("level", "INFO")).upper()
    if "uploadedAt" not in out:
        out["uploadedAt"] = utcnow_iso()
    return out


async def _ensure_project_exists(db, project_id: str) -> ObjectId:
    """Valida project_id (string OID) e garante que o projeto existe."""
    try:
        oid = ObjectId(project_id)
    except Exception:
        raise ValueError("Invalid project_id (must be a valid ObjectId string)")

    proj = await db["projects"].find_one({"_id": oid}, {"_id": 1})
    if not proj:
        raise ValueError("Project not found for given project_id")
    return oid


def _empty_csv() -> io.BytesIO:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["_id", "uploadedAt", "timestamp", "status", "level", "message", "tags", "data", "request_id", "project_id"])
    buffer.seek(0)
    return io.BytesIO(buffer.getvalue().encode("utf-8"))


async def create_log(
    project_id: str,
    status: str,
    level: str,
    message: str,
    timestamp: Optional[str] = None,
    tags: Optional[List[str]] = None,
    data: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
) -> str:
    """Cria e insere log no MongoDB + emite broadcast."""
    db = await get_db()

    # valida project_id e converte para ObjectId
    proj_oid = await _ensure_project_exists(db, project_id)

    # uploadedAt é o "agora" do servidor em ISO Z sem micros, via helper obrigatória
    uploaded_at = utcnow_iso()

    # timestamp do evento: se vier vazio, assumimos agora (ISO Z)
    event_ts = timestamp or utcnow_iso()

    log_doc: Dict[str, Any] = {
        "uploadedAt": uploaded_at,
        "timestamp": event_ts,
        "status": status,
        "level": level,
        "message": message,
        "tags": tags or [],
        "data": data or {},
        "request_id": request_id or None,
        "project_id": proj_oid,
    }

    res = await db["logs"].insert_one(log_doc)

    # Broadcast em tempo real por canal do project_id (string)
    await manager.broadcast(str(proj_oid), json.dumps({
        **_serialize_ids(log_doc),
        "_id": str(res.inserted_id)
    }, ensure_ascii=False, separators=(",", ":")))

    return str(res.inserted_id)


async def list_logs(
    project_id: Optional[str] = None,
    visibility: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Lista até 1000 logs mais recentes.
    Aplica visibilidade (espera receber filtros por project_id) e filtro opcional por project_id.
    """
    db = await get_db()
    query: Dict[str, Any] = {}
    if visibility:
        query.update(visibility)
    if project_id:
        # Se já existe filtro de visibilidade com $in, restringe sem permitir bypass
        if "project_id" in query and isinstance(query["project_id"], dict) and "$in" in query["project_id"]:
            allowed = {str(x) for x in query["project_id"]["$in"]}
            if project_id not in allowed:
                return []
        try:
            query["project_id"] = ObjectId(project_id)
        except Exception:
            return []

    cursor = db["logs"].find(query).sort("timestamp", -1).limit(1000)
    docs = await cursor.to_list(length=1000)
    return [_serialize_ids(d) for d in docs]

async def list_logs_filtered(filters: Optional[Dict[str, Any]] = None, visibility: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    db = await get_db()
    query_parts = []
    if filters:
        f: Dict[str, Any] = {}
        for k, v in filters.items():
            if k == "project_id":
                if isinstance(v, dict) and "$in" in v:
                    try:
                        f[k] = {"$in": [ObjectId(x) for x in v["$in"]]}
                    except Exception:
                        return []
                else:
                    try:
                        f[k] = ObjectId(v)
                    except Exception:
                        return []
            else:
                f[k] = v
        query_parts.append(f)
    if visibility:
        query_parts.append(visibility)
    if len(query_parts) == 2:
        query = {"$and": query_parts}
    elif len(query_parts) == 1:
        query = query_parts[0]
    else:
        query = {}
    cursor = db["logs"].find(query).sort("timestamp", -1).limit(1000)
    docs = await cursor.to_list(length=1000)
    return [_serialize_ids(d) for d in docs]

async def latest_timestamp(project_id: Optional[str] = None) -> Optional[str]:
    """Retorna o timestamp mais recente de um projeto (ou geral)."""
    db = await get_db()
    query: Dict[str, Any] = {}
    if project_id:
        try:
            query["project_id"] = ObjectId(project_id)
        except Exception:
            return None

    doc = await db["logs"].find_one(query, sort=[("timestamp", -1)], projection={"timestamp": 1})
    return doc["timestamp"] if doc else None


async def level_counts(project_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Conta logs agrupados por 'level' (normalizado para UPPER)."""
    db = await get_db()
    pipeline: List[Dict[str, Any]] = []

    if project_id:
        try:
            pipeline.append({"$match": {"project_id": ObjectId(project_id)}})
        except Exception:
            return []

    pipeline.extend([
        {"$addFields": {"_norm_level": {"$toUpper": "$level"}}},
        {"$group": {"_id": "$_norm_level", "count": {"$sum": 1}}},
        {"$sort": {"_id": 1}},
        {"$project": {"level": "$_id", "_id": 0, "count": 1}},
    ])

    cursor = db["logs"].aggregate(pipeline)
    return [doc async for doc in cursor]


async def generate_logs_csv(
    filters: Optional[Dict[str, Any]] = None,
    visibility: Optional[Dict[str, Any]] = None
) -> io.BytesIO:
    """Exporta logs filtrados como CSV puro (não zipado)."""
    db = await get_db()

    print("Filtros finais aplicados:", filters)
    print("Visibilidade:", visibility)

    query_parts = []
    if filters:
        f: Dict[str, Any] = {}
        for k, v in filters.items():
            if k == "project_id":
                if isinstance(v, dict) and "$in" in v:
                    try:
                        f[k] = {"$in": [ObjectId(x) for x in v["$in"]]}
                    except Exception:
                        return _empty_csv()
                else:
                    try:
                        f[k] = ObjectId(v)
                    except Exception:
                        return _empty_csv()
            else:
                f[k] = v
        query_parts.append(f)

    if visibility:
        query_parts.append(visibility)

    if len(query_parts) == 2:
        query = {"$and": query_parts}
    elif len(query_parts) == 1:
        query = query_parts[0]
    else:
        query = {}

    projection = {
        "_id": 1, "uploadedAt": 1, "timestamp": 1, "status": 1,
        "level": 1, "message": 1, "tags": 1, "data": 1,
        "request_id": 1, "project_id": 1,
    }

    cursor = db["logs"].find(query, projection).sort("timestamp", -1)
    docs = [_serialize_ids(d) async for d in cursor]

    output = io.StringIO()
    fieldnames = ["_id", "uploadedAt", "timestamp", "status", "level",
                  "message", "tags", "data", "request_id", "project_id"]
    writer = csv.DictWriter(output, fieldnames=fieldnames)
    writer.writeheader()

    for d in docs:
        tags_val = d.get("tags") or []
        tags_str = ";".join(map(str, tags_val)) if isinstance(tags_val, list) else str(tags_val)

        data_val = d.get("data") or {}
        try:
            data_json = json.dumps(data_val, ensure_ascii=False, separators=(",", ":"))
        except Exception:
            data_json = "{}"

        writer.writerow({
            "_id": d.get("_id", ""),
            "uploadedAt": d.get("uploadedAt", ""),
            "timestamp": d.get("timestamp", ""),
            "status": d.get("status", ""),
            "level": d.get("level", ""),
            "message": d.get("message", ""),
            "tags": tags_str,
            "data": data_json,
            "request_id": d.get("request_id", "") or "",
            "project_id": d.get("project_id", ""),
        })

    output.seek(0)
    return io.BytesIO(output.getvalue().encode("utf-8"))



async def generate_logs_excel(
    filters: Optional[Dict[str, Any]] = None,
    visibility: Optional[Dict[str, Any]] = None
) -> io.BytesIO:
    """Exporta logs filtrados em Excel (.xlsx)."""
    db = await get_db()
    query_parts = []

    print("Filtros finais aplicados:", filters)
    print("Visibilidade:", visibility)
    
    if filters:
        f: Dict[str, Any] = {}
        for k, v in filters.items():
            if k == "project_id":
                try:
                    f[k] = ObjectId(v)
                except Exception:
                    continue
            else:
                f[k] = v
        query_parts.append(f)

    if visibility:
        query_parts.append(visibility)

    query = {"$and": query_parts} if len(query_parts) > 1 else query_parts[0] if query_parts else {}

    cursor = db["logs"].find(query).sort("timestamp", -1)
    docs = [_serialize_ids(d) async for d in cursor]

    # Cria workbook e sheet
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Logs"

    headers = ["_id", "uploadedAt", "timestamp", "status", "level",
               "message", "tags", "data", "request_id", "project_id"]
    ws.append(headers)

    for d in docs:
        tags_str = ";".join(map(str, d.get("tags") or []))
        data_json = json.dumps(d.get("data") or {}, ensure_ascii=False, separators=(",", ":"))
        row = [
            d.get("_id", ""),
            d.get("uploadedAt", ""),
            d.get("timestamp", ""),
            d.get("status", ""),
            d.get("level", ""),
            d.get("message", ""),
            tags_str,
            data_json,
            d.get("request_id", ""),
            d.get("project_id", ""),
        ]
        ws.append(row)

    for col in ws.columns:
        max_length = max((len(str(cell.value)) for cell in col if cell.value), default=10)
        ws.column_dimensions[get_column_letter(col[0].column)].width = max_length + 2

    stream = io.BytesIO()
    wb.save(stream)
    stream.seek(0)
    return stream
