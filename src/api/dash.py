from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from typing import Optional, List, Dict, Any

from services.dashboard_service import (
    dash_level_counts,
    dash_top_users,
    dash_top_endpoints,
)
from core.auth import enforce_visibility
from models.dash import DashLevelCount, DashTopUser, DashTopEndpoint

router = APIRouter(prefix="/dash", tags=["dash"])

@router.get(
    "/levels",
    response_model=List[DashLevelCount],
    summary="Contagem de logs por nível (apenas projetos ativos + visibilidade)",
)
async def dash_levels(
    request: Request,
    project_id: Optional[str] = Query(None, description="Restringe a um único projeto"),
    timestamp__gte: Optional[str] = Query(None, description="ISO-8601 inclusive"),
    timestamp__lte: Optional[str] = Query(None, description="ISO-8601 inclusive"),
    level__in: Optional[List[str]] = Query(None, description="Lista de níveis (qualquer casing)"),
    visibility: Dict[str, Any] = Depends(enforce_visibility),
):
    return await dash_level_counts(
        project_id=project_id,
        timestamp_gte=timestamp__gte,
        timestamp_lte=timestamp__lte,
        levels=level__in,
        visibility=visibility,
    )

@router.get(
    "/top-users",
    response_model=List[DashTopUser],
    summary="Top usuários por contagem (apenas projetos ativos + visibilidade)",
)
async def dash_top_users_view(
    request: Request,
    project_id: Optional[str] = Query(None),
    timestamp__gte: Optional[str] = Query(None),
    timestamp__lte: Optional[str] = Query(None),
    visibility: Dict[str, Any] = Depends(enforce_visibility),
):
    return await dash_top_users(
        project_id=project_id,
        timestamp_gte=timestamp__gte,
        timestamp_lte=timestamp__lte,
        visibility=visibility,
    )

@router.get(
    "/top-endpoints",
    response_model=List[DashTopEndpoint],
    summary="Top endpoints por contagem (apenas projetos ativos + visibilidade)",
)
async def dash_top_endpoints_view(
    request: Request,
    project_id: Optional[str] = Query(None),
    timestamp__gte: Optional[str] = Query(None),
    timestamp__lte: Optional[str] = Query(None),
    visibility: Dict[str, Any] = Depends(enforce_visibility),
):
    return await dash_top_endpoints(
        project_id=project_id,
        timestamp_gte=timestamp__gte,
        timestamp_lte=timestamp__lte,
        visibility=visibility,
    )
