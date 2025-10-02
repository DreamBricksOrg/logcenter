from typing import List, Dict, Any, Optional
from bson import ObjectId
from datetime import datetime

from db.utils import get_db 
from core.security import hash_secret


def _to_str_id(doc: Dict[str, Any]) -> Dict[str, Any]:
    if not doc:
        return doc
    d = dict(doc)
    if "_id" in d:
        d["_id"] = str(d["_id"])
    return d


async def create_project(*, name: str, code: str, api_key_plain: Optional[str] = None) -> Dict[str, Any]:
    """
    Cria projeto com (name, code) e opcionalmente define API Key (salt/hash).
    Garante unicidade de 'code'.
    """
    db = await get_db()

    # code unique
    exists = await db["projects"].find_one({"code": code})
    if exists:
        raise ValueError("Project code already exists")

    doc: Dict[str, Any] = {
        "name": name.strip(),
        "code": code.strip(),
        "createdAt": datetime.utcnow().replace(microsecond=0),
    }

    if api_key_plain:
        salt, hsh = hash_secret(api_key_plain)
        doc["api_key_salt"] = salt
        doc["api_key_hash"] = hsh

    res = await db["projects"].insert_one(doc)
    doc["_id"] = str(res.inserted_id)
    return {
        "_id": doc["_id"],
        "name": doc["name"],
        "code": doc["code"],
        "has_api_key": "api_key_hash" in doc,
    }


async def list_projects() -> List[Dict[str, Any]]:
    """Retorna todos os projetos (sem expor hash/salt)."""
    db = await get_db()
    cursor = db["projects"].find({}, {"name": 1, "code": 1})
    docs = await cursor.to_list(length=1000)
    out: List[Dict[str, Any]] = []
    for d in docs:
        out.append({
            "_id": str(d["_id"]),
            "name": d["name"],
            "code": d["code"],
            "has_api_key": True,
        })
    return out


async def update_project(
    project_id: str,
    *,
    name: Optional[str] = None,
    code: Optional[str] = None,
    api_key_plain: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Atualiza campos do projeto. Garante unicidade de 'code'.
    Retorna ProjectOut.
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
        conflict = await db["projects"].find_one({"code": code, "_id": {"$ne": oid}})
        if conflict:
            raise ValueError("Project code already exists")
        updates["code"] = code.strip()
    if api_key_plain:
        salt, hsh = hash_secret(api_key_plain)
        updates["api_key_salt"] = salt
        updates["api_key_hash"] = hsh

    if not updates:
        raise ValueError("No changes")

    res = await db["projects"].update_one({"_id": oid}, {"$set": updates})
    if res.matched_count == 0:
        raise LookupError("Project not found")

    doc = await db["projects"].find_one({"_id": oid}, {"name": 1, "code": 1, "api_key_hash": 1})
    return {
        "_id": str(doc["_id"]),
        "name": doc["name"],
        "code": doc["code"],
        "has_api_key": "api_key_hash" in doc,
    }


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
