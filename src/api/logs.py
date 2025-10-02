from fastapi import APIRouter, HTTPException, Depends, Response, Query, Header
from typing import List, Optional, Dict, Any
from models.log import LogCreate
from services import log_service
from core.config import settings

router = APIRouter(prefix="/logs", tags=["logs"])

def require_api_key(x_api_key: Optional[str] = Header(default=None, convert_underscores=False)):
    if settings.REQUIRE_API_KEY and not x_api_key:
        raise HTTPException(status_code=401, detail="Missing API key")
    return True

@router.post("/", response_model=Dict[str, str], status_code=201)
def create_log(payload: LogCreate, ok: bool = Depends(require_api_key)):
    try:
        log_id = log_service.create_log(
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
def list_logs(project: Optional[str] = Query(default=None)):
    return log_service.list_logs(project)

@router.get("/latest", response_model=Dict[str, Optional[str]])
def latest(project: Optional[str] = Query(default=None)):
    return {"timestamp": log_service.latest_timestamp(project)}

@router.get("/levels", response_model=List[Dict[str, Any]])
def level_counts(project: Optional[str] = Query(default=None)):
    return log_service.level_counts(project)
