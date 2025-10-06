from typing import List, Dict, Any, Optional
from bson import ObjectId
from datetime import datetime

from db.utils import get_db
from core.security import hash_secret
from util.helpers import utcnow_iso, format_datetime  


def _ensure_config_dict(cfg_in: Optional[dict]) -> Dict[str, Any]:
    """
    Normaliza a estrutura 'config' no documento"""
    cfg: Dict[str, Any] = {}
    if cfg_in:
        cfg = {
            "defaultTags": list(cfg_in.get("defaultTags") or []),
            "separator": (cfg_in.get("separator") or ","),
            "exportFields": list(cfg_in.get("exportFields") or []),
        }
    else:
        cfg = {
            "defaultTags": [],
            "separator": ",",
            "exportFields": [],
        }
    return cfg

def _public_out(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Formata a saída pública (ProjectOut) sem expor hash/salt.
    Se 'config' existir, devolve como dicionário.
    """
    created_raw = doc.get("createdAt")

    if isinstance(created_raw, datetime):
        created_iso = format_datetime(created_raw)
    elif isinstance(created_raw, str) and created_raw.strip():
        created_iso = created_raw
    else:
        created_iso = utcnow_iso()

    return {
        "_id": str(doc["_id"]),
        "name": doc["name"],
        "code": doc["code"],
        "has_api_key": bool(doc.get("api_key_hash")),
        "description": doc.get("description"),
        "config": doc.get("config"),
        "createdAt": created_iso,
    }

async def create_project(
    *,
    name: str,
    code: str,
    api_key_plain: Optional[str] = None,
    description: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Cria projeto com (name, code).
    Garante unicidade de 'code'.
    """
    db = await get_db()

    if await db["projects"].find_one({"code": code}):
        raise ValueError("Project code already exists")

    created_at_iso = utcnow_iso()

    doc: Dict[str, Any] = {
        "name": name.strip(),
        "code": code.strip(),
        "description": (description.strip() if isinstance(description, str) else None),
        "createdAt": created_at_iso,
        "config": _ensure_config_dict(config),
    }

    if api_key_plain:
        salt, hsh = hash_secret(api_key_plain)
        doc["api_key_salt"] = salt
        doc["api_key_hash"] = hsh

    res = await db["projects"].insert_one(doc)
    doc["_id"] = res.inserted_id
    return _public_out(doc)


async def list_projects(name: Optional[str] = None, code: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retorna todos os projetos (sem expor hash/salt). Com filtro opcional de nome ou code"""
    db = await get_db()
    query = {}
    if name:
        query["name"] = {"$regex": name, "$options": "i"}  # case-insensitive
    if code:
        query["code"] = code

    cursor = db["projects"].find(query)
    docs = await cursor.to_list(length=1000)

    return [ _public_out(d) for d in docs]



async def update_project(
    project_id: str,
    *,
    name: Optional[str] = None,
    code: Optional[str] = None,
    api_key_plain: Optional[str] = None,
    description: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Atualiza campos do projeto, garantindo unicidade de 'code'.
    Retorna ProjectOut (sem hash/salt).
    """
    db = await get_db()
    try:
        oid = ObjectId(project_id)
    except Exception:
        raise ValueError("Invalid id")

    updates: Dict[str, Any] = {}

    if name is not None:
        updates["name"] = name.strip()

    if code is not None:
        # checa conflito de code
        conflict = await db["projects"].find_one({"code": code, "_id": {"$ne": oid}})
        if conflict:
            raise ValueError("Project code already exists")
        updates["code"] = code.strip()

    if description is not None:
        updates["description"] = description.strip()

    if config is not None:
        updates["config"] = _ensure_config_dict(config)

    if api_key_plain:
        salt, hsh = hash_secret(api_key_plain)
        updates["api_key_salt"] = salt
        updates["api_key_hash"] = hsh

    if not updates:
        raise ValueError("No changes")

    res = await db["projects"].update_one({"_id": oid}, {"$set": updates})
    if res.matched_count == 0:
        raise LookupError("Project not found")

    doc = await db["projects"].find_one(
        {"_id": oid},
        {"name": 1, "code": 1, "api_key_hash": 1, "description": 1, "config": 1},
    )
    return _public_out(doc)


async def delete_project(project_id: str) -> None:
    """Remove projeto por id."""
    db = await get_db()
    try:
        oid = ObjectId(project_id)
    except Exception:
        raise ValueError("Invalid id")

    res = await db["projects"].delete_one({"_id": oid})
    if res.deleted_count == 0:
        raise LookupError("Project not found")
