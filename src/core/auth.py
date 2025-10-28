from __future__ import annotations
from typing import Optional, Dict, Any, List
from bson import ObjectId
from fastapi import Header, HTTPException, status, Depends

from core.config import settings
from services.auth_service import find_user_by_api_key, is_admin_key, validate_project_api_key

"""
Fluxo unificado:
- Cliente/Admin envia X-API-Key (de USUÁRIO) -> valida em users.api_key_salt/hash.
- Define principal com role=admin|client, user_id, name, e project_ids (se client, ou admin escopado).
- (LEGACY) Se a API key bater como admin-key efêmera (antigo) => role=admin.
- (LEGACY) Se a API key bater como project-key => role=client (escopo do projeto).
"""

async def require_principal(
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
) -> Dict[str, Any]:
    # 1) API key de USUÁRIO (preferencial no novo fluxo)
    if x_api_key:
        user = await find_user_by_api_key(x_api_key)
        if user:
            role = (user.get("role") or "").strip().lower()
            if role not in ("admin", "client"):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid role")
            # monta project_ids do usuário (string)
            raw_ids = user.get("project_ids") or []
            proj_ids: List[str] = []
            for v in raw_ids:
                try:
                    _ = ObjectId(str(v))  # valida
                    proj_ids.append(str(v))
                except Exception:
                    continue
            return {
                "role": role,
                "user_id": str(user["_id"]),
                "name": user.get("name") or user.get("email"),
                "project_ids": proj_ids,
            }

        # 2) (LEGACY) admin key efêmera
        if await is_admin_key(x_api_key):
            return {"role": "admin", "method": "legacy_admin_key"}

        # 3) project API key (cliente de um único projeto)
        project = await validate_project_api_key(x_api_key)
        if project:
            return {
                "role": "client",
                "project_ids": [project["project_id"]],
            }

        # nenhuma bateu
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    if settings.REQUIRE_API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing credentials")

    # Guest (somente quando permitido)
    return {"role": "guest", "project_ids": []}

async def enforce_visibility(principal: Dict[str, Any] = Depends(require_principal)) -> Dict[str, Any]:
    """
    Visibilidade:
    - admin sem escopo: {}
    - admin com escopo (se você optar por dar project_ids no admin): {"project_id": {"$in": [oids]}}
    - client: {"project_id": {"$in": [oids]}}
    - guest: {}
    """
    role = principal.get("role")
    ids = principal.get("project_ids") or []
    if role == "admin":
        if ids:
            return {"project_id": {"$in": [ObjectId(x) for x in ids]}}
        return {}
    if role == "client":
        if not ids:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No project bound to user")
        return {"project_id": {"$in": [ObjectId(x) for x in ids]}}
    return {}
