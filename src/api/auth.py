from fastapi import APIRouter, HTTPException
from models.auth import (
    AdminLoginRequest, AdminLoginResponse,
    ProjectLoginRequest, ProjectLoginResponse
)
from services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/admin", response_model=AdminLoginResponse)
async def admin_login(payload: AdminLoginRequest):
    api_key = await auth_service.login_admin(payload.email, payload.password)
    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    return {"api_key": api_key}

@router.post("/project", response_model=ProjectLoginResponse)
async def project_login(payload: ProjectLoginRequest):
    result = await auth_service.validate_project_api_key(payload.api_key)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return result