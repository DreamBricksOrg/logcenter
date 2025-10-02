from fastapi import APIRouter, HTTPException, Depends
from typing import List
from models.project import ProjectCreate, ProjectUpdate, ProjectOut
from core.auth import require_principal
from services import project_service

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("/", response_model=ProjectOut, status_code=201)
async def create_project(payload: ProjectCreate, principal=Depends(require_principal)):
    if principal["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin required")
    try:
        return await project_service.create_project(
            name=payload.name,
            code=payload.code,
            api_key_plain=payload.api_key_plain,
        )
    except ValueError as e:
        raise HTTPException(status_code=409 if "exists" in str(e) else 400, detail=str(e))


@router.get("/", response_model=List[ProjectOut])
async def list_projects(principal=Depends(require_principal)):
    if principal["role"] not in ("admin", "client", "guest"):
        raise HTTPException(status_code=403)
    return await project_service.list_projects()


@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project(project_id: str, payload: ProjectUpdate, principal=Depends(require_principal)):
    if principal["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin required")
    try:
        return await project_service.update_project(
            project_id,
            name=payload.name,
            code=payload.code,
            api_key_plain=payload.api_key_plain,
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
    if principal["role"] != "admin":
        raise HTTPException(status_code=403, detail="Admin required")
    try:
        await project_service.delete_project(project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return None
