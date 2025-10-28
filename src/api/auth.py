from __future__ import annotations
from fastapi import APIRouter, HTTPException

from models.auth import (
    UnifiedLoginRequest, UnifiedLoginResponse,
    AdminLoginRequest, AdminLoginResponse,  # legacy
    ProjectLoginRequest, ProjectLoginResponse,  # legacy
)
from services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=UnifiedLoginResponse, summary="Unified login (admin or client) with email+password")
async def unified_login(payload: UnifiedLoginRequest):
    result = await auth_service.login_user(payload.email, payload.password)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return result


@router.post("/project", response_model=ProjectLoginResponse, include_in_schema=False)
async def project_login_legacy(payload: ProjectLoginRequest):
    result = await auth_service.validate_project_api_key(payload.api_key)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return result
