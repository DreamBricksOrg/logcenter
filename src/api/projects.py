from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List, Dict
from models.project import ProjectCreate, ProjectUpdate, ProjectOut
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


@router.get("/", response_model=List[ProjectOut], response_model_by_alias=True)
async def list_projects(
    principal=Depends(require_principal),
    name: Optional[str] = Query(default=None),
    code: Optional[str] = Query(default=None),
    include_inactive: bool = Query(
        default=False,
        description="Se true, inclui projetos inativos (apenas para admin)."
    ),
):
    # Apenas admin pode ver inativos quando a auth estiver ligada
    allow_inactive = include_inactive and (not settings.REQUIRE_API_KEY or principal.get("role") == "admin")
    return await project_service.list_projects(name=name, code=code, include_inactive=allow_inactive)


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
