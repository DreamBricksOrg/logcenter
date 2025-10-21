from __future__ import annotations
import hmac
import hashlib
import secrets

from bson import ObjectId
from typing import Optional, Dict, Any
from fastapi import Header, HTTPException, status, Depends

from db.utils import get_db
from core.config import settings
from core.security import verify_secret

"""
Autenticação/Autorização simples:
- Cliente: envia X-API-Key (chave de projeto). O principal terá role=client e project_codes=[code].
- Admin: envia X-Admin-Email e X-Admin-Password (básico, para admin dashboard/CRUD). Retorna role=admin.
"""

ADMIN_KEY_SEPARATOR = "."

async def _find_project_by_api_key(db, api_key_plain: str) -> Optional[Dict[str, Any]]:
    """
    Procura um projeto cuja api_key (salt+hash) valide contra `api_key_plain`.
    Usa varredura simples (pode ser otimizada futuramente para índice/coleção separada).
    """
    projection = {"_id": 1, "code": 1, "api_key_salt": 1, "api_key_hash": 1}
    async for p in db["projects"].find({}, projection):  # Motor: iteração assíncrona
        salt = p.get("api_key_salt")
        hsh = p.get("api_key_hash")
        if salt and hsh and verify_secret(api_key_plain, salt, hsh):
            return p
    return None

async def generate_admin_key(secret_key: str = None) -> str:
    """
    Gera uma admin API key no formato: <id>.<hex_mac>
    """
    sk = secret_key or settings.SECRET_KEY
    rnd = secrets.token_hex(16)  # 32 hex chars
    mac = hmac.new(sk.encode("utf-8"), rnd.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{rnd}{ADMIN_KEY_SEPARATOR}{mac}"

async def is_admin_key(key: str, secret_key: str = None) -> bool:
    """
    Valida se `key` é uma admin key válida derivada do secret_key.
    """
    sk = secret_key or settings.SECRET_KEY
    if not key or ADMIN_KEY_SEPARATOR not in key:
        return False
    try:
        rnd, mac = key.split(ADMIN_KEY_SEPARATOR, 1)
    except ValueError:
        return False
    expected = hmac.new(sk.encode("utf-8"), rnd.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, mac)


async def require_principal(
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    x_admin_email: Optional[str] = Header(default=None, alias="X-Admin-Email"),
    x_admin_password: Optional[str] = Header(default=None, alias="X-Admin-Password"),
) -> Dict[str, Any]:
    """
    Retorna um "principal" (contexto de autorização) para uso nos endpoints.
    - Se X-API-Key presente e válida → client.
    - Se X-Admin-Email + X-Admin-Password válidos → admin.
    - Caso contrário:
      * Se REQUIRE_API_KEY=True → 401 Missing credentials
      * Se REQUIRE_API_KEY=False → role=guest (para dev/diagnóstico)
    """
    db = await get_db()

    # Autenticação por API Key (admin)
    if x_api_key and is_admin_key(x_api_key):
        return {
            "role": "admin",
            "method": "admin_key",
        }

    # Auttenticação por project API key (cliente)
    if x_api_key:
        project = await _find_project_by_api_key(db, x_api_key)
        if not project:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
            )
        return {
            "role": "client",
            "project_codes": [project["code"]],
            "project_ids": [str(project["_id"])],
        }

    # Autenticação de Admin (email/senha)
    if x_admin_email and x_admin_password:
        user = await db["users"].find_one({"email": x_admin_email.lower().strip()})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid admin credentials",
            )
        salt = user.get("password_salt")
        hsh = user.get("password_hash")
        if not (salt and hsh and verify_secret(x_admin_password, salt, hsh)):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid admin credentials",
            )
        if user.get("role") != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not an admin",
            )
        return {
            "role": "admin",
            "user_id": str(user["_id"]),
            "project_codes": user.get("project_codes", []),
        }

    if settings.REQUIRE_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing credentials",
        )

    # Guest (apenas em dev/diagnóstico quando REQUIRE_API_KEY=False)
    return {"role": "guest", "project_codes": []}


async def enforce_visibility(principal: Dict[str, Any] = Depends(require_principal)) -> Dict[str, Any]:
    """
    Gera um filtro de visibilidade para consultas:
    - admin: acesso total ({}), a menos que tenha project_codes definidos (usa $in).
    - client: restrito aos project_codes da API key.
    - guest: acesso total ({}), apenas quando permitido (REQUIRE_API_KEY=False).
    """
    role = principal.get("role")
    if role == "admin":
        ids = principal.get("project_ids") or []
        if ids:
            # Converte para ObjectId
            return {"project_id": {"$in": [ObjectId(x) for x in ids]}}
        return {}
    if role == "client":
        ids = principal.get("project_ids", [])
        if not ids:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No project bound to API key")
        return {"project_id": {"$in": [ObjectId(x) for x in ids]}}
    return {}
