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
    dash_top_messages,
)
from core.auth import enforce_visibility
from models.dash import (
    DashLevelCount,
    DashTopUser,
    DashTopEndpoint,
    DashTopTag,
    DashTopDataKey,
    DashTopDataValue,
    DashTopMessage,
)

router = APIRouter(prefix="/dash", tags=["dash"])

EXCLUDE_FILTER_PARAMS = {
    "project_id",
    "timestamp__gte",
    "timestamp__lte",
    "limit",
    "level__in",
    "item",
}


def _build_extra_filters(request: Request, exclude: set[str]) -> Dict[str, Any] | None:
    """
    Constrói o dicionário de extra_filters a partir de query_params,
    removendo os campos de controle que já são tratados nos parâmetros
    explícitos da rota (project_id, timestamp__gte, etc.).
    Tudo que sobrar vira candidato a filtro, respeitando a semântica
    de operadores (field__gte, field__regex, data.campaign, etc.),
    que será interpretada por utils.queries.build_filter no service.
    """
    params = dict(request.query_params)
    for key in exclude:
        params.pop(key, None)
    return params or None


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
    extra_filters = _build_extra_filters(
        request,
        exclude=EXCLUDE_FILTER_PARAMS,
    )

    return await dash_level_counts(
        project_id=project_id,
        timestamp_gte=timestamp__gte,
        timestamp_lte=timestamp__lte,
        levels=level__in,
        limit=limit,
        visibility=visibility,
        extra_filters=extra_filters,
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
    extra_filters = _build_extra_filters(
        request,
        exclude=EXCLUDE_FILTER_PARAMS
    )

    return await dash_top_users(
        project_id=project_id,
        timestamp_gte=timestamp__gte,
        timestamp_lte=timestamp__lte,
        limit=limit,
        visibility=visibility,
        extra_filters=extra_filters,
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
    extra_filters = _build_extra_filters(
        request,
        exclude=EXCLUDE_FILTER_PARAMS
    )

    return await dash_top_endpoints(
        project_id=project_id,
        timestamp_gte=timestamp__gte,
        timestamp_lte=timestamp__lte,
        limit=limit,
        visibility=visibility,
        extra_filters=extra_filters,
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
    extra_filters = _build_extra_filters(
        request,
        exclude=EXCLUDE_FILTER_PARAMS
    )

    return await dash_top_tags(
        project_id=project_id,
        timestamp_gte=timestamp__gte,
        timestamp_lte=timestamp__lte,
        limit=limit,
        visibility=visibility,
        extra_filters=extra_filters,
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
    extra_filters = _build_extra_filters(
        request,
        exclude=EXCLUDE_FILTER_PARAMS
    )

    return await dash_top_data_keys(
        project_id=project_id,
        timestamp_gte=timestamp__gte,
        timestamp_lte=timestamp__lte,
        limit=limit,
        visibility=visibility,
        extra_filters=extra_filters,
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
    item: Optional[str] = Query(
        None,
        description="Se informado, filtra a chave e retorna contagem por valor",
    ),
    limit: int = Query(20, ge=1, le=100),
    visibility: Dict[str, Any] = Depends(enforce_visibility),
):
    extra_filters = _build_extra_filters(
        request,
        exclude=EXCLUDE_FILTER_PARAMS
    )

    return await dash_top_data_values(
        project_id=project_id,
        timestamp_gte=timestamp__gte,
        timestamp_lte=timestamp__lte,
        limit=limit,
        visibility=visibility,
        item=item,
        extra_filters=extra_filters,
    )


@router.get(
    "/top-messages",
    response_model=List[DashTopMessage],
    summary="Top mensagens de log por contagem (projetos ativos + visibilidade)",
)
async def dash_top_messages_view(
    request: Request,
    project_id: Optional[str] = Query(None),
    timestamp__gte: Optional[str] = Query(None),
    timestamp__lte: Optional[str] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    visibility: Dict[str, Any] = Depends(enforce_visibility),
):
    """
    Agrega as mensagens de log (campo message), permitindo filtros adicionais via query:
    ex: message__regex=timeout.
    """
    extra_filters = _build_extra_filters(
        request,
        exclude=EXCLUDE_FILTER_PARAMS
    )

    return await dash_top_messages(
        project_id=project_id,
        timestamp_gte=timestamp__gte,
        timestamp_lte=timestamp__lte,
        limit=limit,
        visibility=visibility,
        extra_filters=extra_filters,
    )
