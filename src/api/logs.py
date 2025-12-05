from __future__ import annotations

from typing import List, Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Depends, Response, Query, Header, Request
from fastapi.responses import StreamingResponse
from starlette.datastructures import QueryParams

from models.log import LogCreate, LogModel
from core.config import settings
from core.auth import enforce_visibility
from services.log_service import (
    create_log as svc_create_log,
    list_logs as svc_list_log,
    latest_timestamp,
    level_counts as svc_level_counts,
    generate_logs_csv,
    generate_logs_excel,
    build_filter,
)

router = APIRouter(prefix="/logs", tags=["logs"])


def require_api_key(x_api_key: Optional[str] = Header(default=None, convert_underscores=False)):
    if settings.REQUIRE_API_KEY and not x_api_key:
        raise HTTPException(status_code=401, detail="Missing API key")
    return True


@router.post("/", response_model=Dict[str, str], status_code=201)
async def create_log(payload: LogCreate, ok: bool = Depends(require_api_key)):
    try:
        log_id = await svc_create_log(
            project_id=payload.project_id,
            status=payload.status,
            level=payload.level,
            message=payload.message,
            timestamp=payload.timestamp,
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
    project_id: Optional[str] = Query(default=None, description="Filtra por um único projeto"),
    limit: Optional[int] = Query(default=None, ge=1, description="Limite de registros (teto no service 5000)"),
    visibility: Dict[str, Any] = Depends(enforce_visibility),
):
    raw_qs = dict(request.query_params)
    raw_qs.pop("project_id", None)
    raw_qs.pop("limit", None)
    filters = build_filter(QueryParams(raw_qs)) if raw_qs else None

    return await svc_list_log(filters=filters, project_id=project_id, visibility=visibility, limit=limit)


@router.get("/latest", response_model=Dict[str, Optional[str]])
async def latest(project_id: Optional[str] = Query(default=None)):
    ts = await latest_timestamp(project_id)
    return {"timestamp": ts}


@router.get("/levels", response_model=List[Dict[str, Any]])
async def level_counts(project_id: Optional[str] = Query(default=None)):
    return await svc_level_counts(project_id)


@router.get("/export")
async def export_logs(
    request: Request,
    format: str = Query(default="xlsx", pattern="^(csv|xlsx)$"),
    project_id: Optional[str] = Query(default=None, description="Filtra explicitamente por um projeto"),
    limit: Optional[int] = Query(default=None, ge=1, description="Limite opcional do export (sem teto)"),
    visibility: Dict[str, Any] = Depends(enforce_visibility),
):
    raw_qs = dict(request.query_params)
    raw_qs.pop("format", None)
    raw_qs.pop("project_id", None)
    raw_qs.pop("limit", None)
    filters = build_filter(QueryParams(raw_qs)) if raw_qs else None

    if format == "xlsx":
        xlsx_buffer = await generate_logs_excel(
            filters=filters,
            visibility=visibility,
            project_id=project_id,
            limit=limit,
        )
        return StreamingResponse(
            xlsx_buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": 'attachment; filename="logs.xlsx"'},
        )

    csv_buffer = await generate_logs_csv(
        filters=filters,
        visibility=visibility,
        project_id=project_id,
        limit=limit,
    )
    return StreamingResponse(
        csv_buffer,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="logs.csv"'},
    )
