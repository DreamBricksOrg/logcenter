from __future__ import annotations
import secrets
import hmac
import hashlib
from typing import Optional, Dict, Any, List

from bson import ObjectId
from db.utils import get_db
from core.security import hash_secret, verify_secret
from core.config import settings


ADMIN_KEY_SEPARATOR = "."


def _new_token() -> str:
    # 32 bytes -> 64 hex chars
    return secrets.token_hex(32)

async def _active_projects_by_ids(db, ids: List[ObjectId]) -> List[Dict[str, Any]]:
    if not ids:
        return []
    cur = db["projects"].find(
        {"_id": {"$in": ids}, "status": "active"},
        {"_id": 1, "code": 1}
    )
    return [doc async for doc in cur]


async def login_user(email: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Login unificado (admin/cliente) por e-mail+senha.
    - Valida senha (salt/hash).
    - Rotaciona e persiste api_key (api_key_salt/hash) do usuário.
    - Retorna payload com api_key plaintext, role, name, user_id, projects ativos (ids/codes).
    """
    db = await get_db()
    user = await db["users"].find_one({"email": email.lower().strip()})
    if not user:
        return None

    salt = user.get("password_salt")
    hsh = user.get("password_hash")
    if not (salt and hsh and verify_secret(password, salt, hsh)):
        return None

    role = (user.get("role") or "").strip().lower()
    if role not in ("admin", "client"):
        return None

    # Projs permitidos (para admin pode ser vazio => acesso global)
    raw_ids = user.get("project_ids") or []
    # Converte para ObjectId válidos
    proj_oids: List[ObjectId] = []
    for val in raw_ids:
        try:
            proj_oids.append(ObjectId(str(val)))
        except Exception:
            continue

    active = await _active_projects_by_ids(db, proj_oids) if proj_oids else []
    active_ids = [str(p["_id"]) for p in active]
    active_codes = [p["code"] for p in active]

    # Gera/rotaciona API key do usuário e persiste salt/hash
    api_key_plain = _new_token()
    ak_salt, ak_hash = hash_secret(api_key_plain)
    await db["users"].update_one(
        {"_id": user["_id"]},
        {"$set": {
            "api_key_salt": ak_salt,
            "api_key_hash": ak_hash,
        }}
    )

    return {
        "api_key": api_key_plain,
        "role": role,
        "name": user.get("name") or user.get("email"),
        "user_id": str(user["_id"]),
        "project_ids": active_ids if role == "client" else active_ids,
        "project_codes": active_codes if role == "client" else active_codes,
    }


async def find_user_by_api_key(api_key_plain: str) -> Optional[Dict[str, Any]]:
    """
    Varre users para encontrar quem possui api_key_salt/hash compatível.
    (Poderíamos indexar em outra coleção, por ora mantemos simples.)
    """
    db = await get_db()
    projection = {
        "_id": 1, "email": 1, "role": 1, "name": 1,
        "api_key_salt": 1, "api_key_hash": 1, "project_ids": 1
    }
    async for u in db["users"].find({}, projection):
        salt = u.get("api_key_salt")
        hsh = u.get("api_key_hash")
        if not (salt and hsh):
            continue
        if verify_secret(api_key_plain, salt, hsh):
            return u
    return None


async def validate_project_api_key(api_key: str) -> Optional[Dict[str, Any]]:
    db = await get_db()
    async for p in db["projects"].find({}, {"_id": 1, "code": 1, "api_key_salt": 1, "api_key_hash": 1, "status": 1}):
        salt = p.get("api_key_salt")
        hsh = p.get("api_key_hash")
        if not (salt and hsh):
            continue
        if verify_secret(api_key, salt, hsh):
            # Bloqueia projeto INATIVO
            if p.get("status") != "active":
                return None
            return {"project_id": str(p["_id"]), "project_code": p["code"], "role": "client"}
    return None


def _hmac_admin_key(secret_key: str, rnd: str) -> str:
    return hmac.new(secret_key.encode(), rnd.encode(), hashlib.sha256).hexdigest()


async def generate_admin_key(secret_key: Optional[str] = None) -> str:
    secret_key = secret_key or settings.SECRET_KEY
    rnd = secrets.token_hex(16)
    mac = _hmac_admin_key(secret_key, rnd)
    return f"{rnd}{ADMIN_KEY_SEPARATOR}{mac}"


async def is_admin_key(key: str, secret_key: Optional[str] = None) -> bool:
    secret_key = secret_key or settings.SECRET_KEY
    if ADMIN_KEY_SEPARATOR not in key:
        return False
    try:
        rnd, mac = key.split(ADMIN_KEY_SEPARATOR, 1)
    except ValueError:
        return False
    expected = _hmac_admin_key(secret_key, rnd)
    return hmac.compare_digest(mac, expected)
