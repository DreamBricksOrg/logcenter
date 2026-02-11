from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, Dict

from models.project import ProjectCreate, ProjectUpdate, ProjectOut, ProjectListResponse, ProjectStatus
from core.auth import require_principal
from core.config import settings
from services import project_service

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("/", response_model=ProjectOut, response_model_by_alias=True, status_code=201)
async def create_project(payload: ProjectCreate, principal=Depends(require_principal)):
    if settings.REQUIRE_API_KEY and principal.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin required")
    try:
        return await project_service.create_project(
            name=payload.name,
            code=payload.code,
            api_key_plain=payload.api_key_plain,
            description=payload.description,
            config=(payload.config.model_dump() if payload.config else None),
            status=payload.status,
        )
    except ValueError as e:
        raise HTTPException(status_code=409 if "exists" in str(e) else 400, detail=str(e))


@router.get("/", response_model=ProjectListResponse, response_model_by_alias=True)
async def list_projects(
    principal=Depends(require_principal),

    name: Optional[str] = Query(default=None),
    code: Optional[str] = Query(default=None),

    status: Optional[ProjectStatus] = Query(default=None),
    has_api_key: Optional[bool] = Query(default=None),

    include_inactive: bool = Query(
        default=False,
        description="Se true, inclui projetos inativos (apenas para admin)."
    ),

    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=30, ge=1, le=100),
):
    allow_inactive = include_inactive and (
        not settings.REQUIRE_API_KEY or principal.get("role") == "admin"
    )

    effective_status = status
    if not allow_inactive and status == "inactive":
        effective_status = "active"

    return await project_service.list_projects_paginated(
        name=name,
        code=code,
        status=effective_status,
        has_api_key=has_api_key,
        include_inactive=allow_inactive,
        page=page,
        page_size=page_size,
    )


@router.patch("/{project_id}", response_model=ProjectOut, response_model_by_alias=True)
async def update_project(project_id: str, payload: ProjectUpdate, principal=Depends(require_principal)):
    if settings.REQUIRE_API_KEY and principal.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin required")
    try:
        return await project_service.update_project(
            project_id,
            name=payload.name,
            code=payload.code,
            api_key_plain=payload.api_key_plain,
            description=payload.description,
            config=(payload.config.model_dump() if payload.config else None),
            status=payload.status,
        )
    except ValueError as e:
        msg = str(e)
        if "Invalid id" in msg:
            raise HTTPException(status_code=404, detail=msg)
        if "No changes" in msg:
            raise HTTPException(status_code=400, detail=msg)
        if "exists" in msg:
            raise HTTPException(status_code=409, detail=msg)
        raise HTTPException(status_code=400, detail=msg)
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: str, principal=Depends(require_principal)):
    if settings.REQUIRE_API_KEY and principal.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin required")
    try:
        await project_service.delete_project(project_id)
    except (ValueError, LookupError) as e:
        raise HTTPException(status_code=404, detail=str(e))
    return None


@router.post("/{project_id}/apikey", response_model=Dict[str, str], status_code=201)
async def regenerate_project_apikey(project_id: str, principal=Depends(require_principal)):
    if settings.REQUIRE_API_KEY and principal.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin required")
    try:
        api_key = await project_service.generate_api_key_for_project(project_id)
        return {"project_id": project_id, "api_key": api_key}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{project_id}/apikey", response_model=Dict[str, str], status_code=200)
async def get_project_apikey(project_id: str, principal=Depends(require_principal)):
    if settings.REQUIRE_API_KEY and principal.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin required")
    try:
        api_key = await project_service.get_api_key_for_project(project_id)
        return {"project_id": project_id, "api_key": api_key}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
