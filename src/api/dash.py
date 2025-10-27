from fastapi import APIRouter, Depends, Query, Request
from typing import Optional, List, Dict, Any
from services.dashboard_service import dash_level_counts, dash_top_users, dash_top_endpoints
from core.auth import enforce_visibility

router = APIRouter(prefix="/dash", tags=["dash"])

@router.get("/levels")
async def dash_levels(
    request: Request,
    project_id: Optional[str] = Query(None),
    timestamp__gte: Optional[str] = Query(None),
    timestamp__lte: Optional[str] = Query(None),
    level__in: Optional[List[str]] = Query(None),
    visibility: Dict[str, Any] = Depends(enforce_visibility)
):
    return await dash_level_counts(
        project_id=project_id,
        timestamp_gte=timestamp__gte,
        timestamp_lte=timestamp__lte,
        levels=level__in,
        visibility=visibility
    )

@router.get("/top-users")
async def dash_top_users_view(
    request: Request,
    visibility: Dict[str, Any] = Depends(enforce_visibility)
):
    return await dash_top_users(visibility=visibility)

@router.get("/top-endpoints")
async def dash_top_endpoints_view(
    request: Request,
    visibility: Dict[str, Any] = Depends(enforce_visibility)
):
    return await dash_top_endpoints(visibility=visibility)
