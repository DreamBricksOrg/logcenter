from typing import List, Dict, Any, Optional
from bson import ObjectId
from datetime import datetime
from fastapi import HTTPException, status

from db.utils import get_db
from core.security import hash_secret, encrypt_secret, decrypt_secret
from util.helpers import utcnow_iso, format_datetime, generate_uuid


def _ensure_config_dict(cfg_in: Optional[dict]) -> Dict[str, Any]:
    """
    Normaliza a estrutura 'config' no documento
    """
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


def _normalize_status(value: Optional[str]) -> str:
    """
    Normaliza status -> 'active' | 'inactive'. Default = 'active'.
    """
    if not value:
        return "active"
    v = str(value).strip().lower()
    return v if v in ("active", "inactive") else "active"


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
        "status": _normalize_status(doc.get("status")),
    }


async def create_project(
    *,
    name: str,
    code: str,
    api_key_plain: Optional[str] = None,
    description: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
    status: Optional[str] = None,
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
        "status": _normalize_status(status or "active"),
    }

    if api_key_plain:
        salt, hsh = hash_secret(api_key_plain)
        doc["api_key_salt"] = salt
        doc["api_key_hash"] = hsh

    res = await db["projects"].insert_one(doc)
    doc["_id"] = res.inserted_id
    return _public_out(doc)


async def list_projects(
    name: Optional[str] = None,
    code: Optional[str] = None,
    *,
    include_inactive: bool = False,
) -> List[Dict[str, Any]]:
    """
    Retorna projetos (sem expor hash/salt).
    Por padrão, NÃO retorna inativos (include_inactive=False).
    """
    db = await get_db()
    query: Dict[str, Any] = {}
    if name:
        query["name"] = {"$regex": name, "$options": "i"}  # case-insensitive
    if code:
        query["code"] = code
    if not include_inactive:
        query["status"] = "active"

    cursor = db["projects"].find(query)
    docs = await cursor.to_list(length=1000)
    return [_public_out(d) for d in docs]


async def list_projects_paginated(
    name: Optional[str] = None,
    code: Optional[str] = None,
    status: Optional[str] = None,
    has_api_key: Optional[bool] = None,
    *,
    include_inactive: bool = False,
    page: int = 1,
    page_size: int = 30,
) -> Dict[str, Any]:
    db = await get_db()

    query: Dict[str, Any] = {}

    if name:
        query["name"] = {"$regex": name, "$options": "i"}

    if code:
        query["code"] = {"$regex": code, "$options": "i"}

    if status:
        query["status"] = status
    else:
        if not include_inactive:
            query["status"] = "active"

    if has_api_key is True:
        query["api_key_hash"] = {"$exists": True, "$ne": None}
    elif has_api_key is False:
        query["$or"] = [
            {"api_key_hash": {"$exists": False}},
            {"api_key_hash": None},
        ]

    total = await db["projects"].count_documents(query)

    skip = (page - 1) * page_size

    cursor = (
        db["projects"]
        .find(query)
        .sort("createdAt", -1)
        .skip(skip)
        .limit(page_size)
    )

    docs = await cursor.to_list(length=page_size)

    return {
        "items": [_public_out(d) for d in docs],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def update_project(
    project_id: str,
    *,
    name: Optional[str] = None,
    code: Optional[str] = None,
    api_key_plain: Optional[str] = None,
    description: Optional[str] = None,
    config: Optional[Dict[str, Any]] = None,
    status: Optional[str] = None,
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

    if status is not None:
        updates["status"] = _normalize_status(status)

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
        {"name": 1, "code": 1, "api_key_hash": 1, "description": 1, "config": 1, "status": 1, "createdAt": 1},
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


async def generate_api_key_for_project(project_id: str) -> str:
    """
    Gera uma nova API key para o projeto (substituindo a anterior).
    Salva salt e hash no documento do projeto.
    Retorna a nova API key gerada (plaintext).
    """
    try:
        oid = ObjectId(project_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Invalid project ID")

    db = await get_db()

    project = await db["projects"].find_one({"_id": oid})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Gera uma nova API Keys
    api_key = generate_uuid().replace("-", "")  # 32-char hex string
    salt, hsh = hash_secret(api_key)

    aad = str(oid).encode("utf-8")
    nonce_b64, ct_b64 = encrypt_secret(api_key, aad=aad)

    await db["projects"].update_one({"_id": oid}, {"$set": {
        "api_key_salt": salt,
        "api_key_hash": hsh,
        "api_key_nonce": nonce_b64,
        "api_key_enc": ct_b64,
    }})

    return api_key

async def get_api_key_for_project(project_id: str) -> str:
    """
    Retorna a API key existente para o projeto.
    """
    try:
        oid = ObjectId(project_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Invalid project ID")

    db = await get_db()

    project = await db["projects"].find_one({"_id": oid})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    nonce = project.get("api_key_nonce")
    enc = project.get("api_key_enc")
    if not nonce or not enc:
        raise HTTPException(status_code=404, detail="Project has no API key")

    aad = str(oid).encode("utf-8")
    try:
        api_key = decrypt_secret(nonce, enc, aad=aad)
    except Exception:
        # se a master key mudou ou dado corrompeu
        raise HTTPException(status_code=500, detail="Could not decrypt API key")

    return api_key
