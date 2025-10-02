from fastapi import APIRouter, HTTPException, Depends, Response, Query, Header
from typing import List, Optional, Dict, Any
from models.log import LogCreate
from services import log_service
from core.config import settings
from core.auth import enforce_visibility

router = APIRouter(prefix="/logs", tags=["logs"])


def require_api_key(x_api_key: Optional[str] = Header(default=None, convert_underscores=False)):
    if settings.REQUIRE_API_KEY and not x_api_key:
        raise HTTPException(status_code=401, detail="Missing API key")
    return True

@router.post("/", response_model=Dict[str, str], status_code=201)
async def create_log(payload: LogCreate, ok: bool = Depends(require_api_key)):
    try:
        log_id = await log_service.create_log(
            project=payload.project,
            level=payload.level,
            message=payload.message,
            tags=payload.tags,
            data=payload.data,
            request_id=payload.request_id,
        )
        return {"id": log_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[Dict[str, Any]])
async def list_logs(
    q_project: Optional[str] = Query(default=None, alias="project"),
    visibility: Dict[str, Any] = Depends(enforce_visibility),
):
    return await log_service.list_logs(project=q_project, visibility=visibility)

@router.get("/latest", response_model=Dict[str, Optional[str]])
async def latest(project: Optional[str] = Query(default=None)):
    ts = await log_service.latest_timestamp(project)
    return {"timestamp": ts}

@router.get("/levels", response_model=List[Dict[str, Any]])
async def level_counts(project: Optional[str] = Query(default=None)):
    return await log_service.level_counts(project)
