from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from typing import Optional, List, Dict, Any

from services.dashboard_service import (
    dash_level_counts,
    dash_top_users,
    dash_top_endpoints,
    dash_top_tags,
    dash_top_data_keys,
    dash_top_data_values,
)
from core.auth import enforce_visibility
from models.dash import (
    DashLevelCount,
    DashTopUser,
    DashTopEndpoint,
    DashTopTag,
    DashTopDataKey,
    DashTopDataValue,
)

router = APIRouter(prefix="/dash", tags=["dash"])


@router.get(
    "/levels",
    response_model=List[DashLevelCount],
    summary="Contagem de logs por nível (projetos ativos + visibilidade)",
)
async def dash_levels(
    request: Request,
    project_id: Optional[str] = Query(None, description="Restringe a um único projeto"),
    timestamp__gte: Optional[str] = Query(None, description="ISO-8601 inclusive"),
    timestamp__lte: Optional[str] = Query(None, description="ISO-8601 inclusive"),
    level__in: Optional[List[str]] = Query(None, description="Lista de níveis (qualquer casing)"),
    limit: int = Query(20, ge=1, le=100),
    visibility: Dict[str, Any] = Depends(enforce_visibility),
):
    return await dash_level_counts(
        project_id=project_id,
        timestamp_gte=timestamp__gte,
        timestamp_lte=timestamp__lte,
        levels=level__in,
        limit=limit,
        visibility=visibility,
    )


@router.get(
    "/top-users",
    response_model=List[DashTopUser],
    summary="Top usuários por contagem (projetos ativos + visibilidade)",
)
async def dash_top_users_view(
    request: Request,
    project_id: Optional[str] = Query(None),
    timestamp__gte: Optional[str] = Query(None),
    timestamp__lte: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    visibility: Dict[str, Any] = Depends(enforce_visibility),
):
    return await dash_top_users(
        project_id=project_id,
        timestamp_gte=timestamp__gte,
        timestamp_lte=timestamp__lte,
        limit=limit,
        visibility=visibility,
    )


@router.get(
    "/top-endpoints",
    response_model=List[DashTopEndpoint],
    summary="Top endpoints por contagem (projetos ativos + visibilidade)",
)
async def dash_top_endpoints_view(
    request: Request,
    project_id: Optional[str] = Query(None),
    timestamp__gte: Optional[str] = Query(None),
    timestamp__lte: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    visibility: Dict[str, Any] = Depends(enforce_visibility),
):
    return await dash_top_endpoints(
        project_id=project_id,
        timestamp_gte=timestamp__gte,
        timestamp_lte=timestamp__lte,
        limit=limit,
        visibility=visibility,
    )


@router.get(
    "/top-tags",
    response_model=List[DashTopTag],
    summary="Top tags (tags[]) por contagem (projetos ativos + visibilidade)",
)
async def dash_top_tags_view(
    request: Request,
    project_id: Optional[str] = Query(None),
    timestamp__gte: Optional[str] = Query(None),
    timestamp__lte: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    visibility: Dict[str, Any] = Depends(enforce_visibility),
):
    return await dash_top_tags(
        project_id=project_id,
        timestamp_gte=timestamp__gte,
        timestamp_lte=timestamp__lte,
        limit=limit,
        visibility=visibility,
    )


@router.get(
    "/top-data/keys",
    response_model=List[DashTopDataKey],
    summary="Top chaves dentro de data (projetos ativos + visibilidade)",
)
async def dash_top_data_keys_view(
    request: Request,
    project_id: Optional[str] = Query(None),
    timestamp__gte: Optional[str] = Query(None),
    timestamp__lte: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    visibility: Dict[str, Any] = Depends(enforce_visibility),
):
    return await dash_top_data_keys(
        project_id=project_id,
        timestamp_gte=timestamp__gte,
        timestamp_lte=timestamp__lte,
        limit=limit,
        visibility=visibility,
    )


@router.get(
    "/top-data/values",
    response_model=List[DashTopDataValue],
    summary="Top valores por chave de data (ou pares item+valor se 'item' não for informado)",
)
async def dash_top_data_values_view(
    request: Request,
    project_id: Optional[str] = Query(None),
    timestamp__gte: Optional[str] = Query(None),
    timestamp__lte: Optional[str] = Query(None),
    item: Optional[str] = Query(None, description="Se informado, filtra a chave e retorna contagem por valor"),
    limit: int = Query(20, ge=1, le=100),
    visibility: Dict[str, Any] = Depends(enforce_visibility),
):
    return await dash_top_data_values(
        project_id=project_id,
        timestamp_gte=timestamp__gte,
        timestamp_lte=timestamp__lte,
        limit=limit,
        visibility=visibility,
        item=item,
    )
