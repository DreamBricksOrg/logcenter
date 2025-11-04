from fastapi import APIRouter, HTTPException, Depends, Response, Query, Header, Request
from fastapi.responses import StreamingResponse
from starlette.datastructures import QueryParams
from typing import List, Optional, Dict, Any
from models.log import LogCreate, LogModel
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
            project_id=payload.project_id,
            status=payload.status,
            level=payload.level,
            message=payload.message,
            tags=payload.tags,
            data=payload.data,
            request_id=payload.request_id,
        )
        return {"id": log_id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/", response_model=List[LogModel])
async def list_logs(
    request: Request,
    visibility: Dict[str, Any] = Depends(enforce_visibility),
):
    filters = log_service.build_filter(request.query_params)
    return await log_service.list_logs_filtered(filters, visibility)

@router.get("/latest", response_model=Dict[str, Optional[str]])
async def latest(project: Optional[str] = Query(default=None)):
    ts = await log_service.latest_timestamp(project)
    return {"timestamp": ts}

@router.get("/levels", response_model=List[Dict[str, Any]])
async def level_counts(project_id: Optional[str] = Query(default=None)):
    return await log_service.level_counts(project_id)


@router.get("/export")
async def export_logs(
    request: Request,
    format: str = Query(default="xlsx", pattern="^(csv|xlsx)$"),
    visibility: Dict[str, Any] = Depends(enforce_visibility),
):
    # remove 'format' antes de passar ao filtro
    query_params = {k: v for k, v in request.query_params.items() if k != "format"}
    filters = log_service.build_filter(QueryParams(query_params))

    if format == "xlsx":
        xlsx_buffer = await log_service.generate_logs_excel(filters, visibility)
        return StreamingResponse(
            xlsx_buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="logs.xlsx"'}
        )
    elif format == "csv":
        csv_buffer = await log_service.generate_logs_csv(filters, visibility)
        return StreamingResponse(
            csv_buffer,
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="logs.csv"'}
        )

