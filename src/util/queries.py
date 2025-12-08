from __future__ import annotations

from typing import Any, Dict, Mapping, Optional, Set
from datetime import datetime

from bson import ObjectId

from db.utils import get_db


async def _active_project_ids() -> list[str]:
    """
    Retorna a lista de IDs (string) de projetos ATIVOS.
    """
    db = await get_db()
    cur = db["projects"].find({"status": "active"}, {"_id": 1})
    return [str(doc["_id"]) async for doc in cur]


async def restrict_to_active_and_visibility(
    visibility: Optional[Dict[str, Any]],
    project_id: Optional[str],
) -> Dict[str, Any]:
    """
    Wrapper fino em cima de build_visibility_match para manter
    compatibilidade com o dashboard_service.

    - Garante apenas projetos ATIVOS.
    - Aplica visibilidade (project_id permitido).
    - Aplica, se vier, o project_id explícito da rota.
    """
    return await build_visibility_match(visibility=visibility, project_id=project_id)


async def build_visibility_match(
    visibility: Optional[Dict[str, Any]],
    project_id: Optional[str],
) -> Dict[str, Any]:
    """
    Constrói o filtro base de visibilidade para logs/projetos, garantindo:
    - Apenas projetos com status "active".
    - Respeita restrições de visibilidade (ex.: visibility["project_id"] = {...}).
    - Aplica, se informado, um project_id explícito da rota.
    - Sempre retorna "project_id" com ObjectId (não string).
    Regras:
      - Se não houver nenhum projeto ativo, retorna {"project_id": {"$in": []}}.
      - Se visibility.project_id estiver fora da lista de ativos, retorna lista vazia.
      - Se project_id da rota não for ativo, retorna lista vazia.
      - Se já existir um "$in", fazemos interseção com o project_id fornecido.
    """
    active_ids = await _active_project_ids()
    if not active_ids:
        return {"project_id": {"$in": []}}

    match: Dict[str, Any] = {"project_id": {"$in": [ObjectId(x) for x in active_ids]}}

    if visibility and "project_id" in visibility:
        vis_val = visibility["project_id"]
        if isinstance(vis_val, dict) and "$in" in vis_val:
            raw_ids = [str(x) for x in vis_val["$in"]]
            allowed = [ObjectId(x) for x in raw_ids if x in active_ids]
            match["project_id"] = {"$in": allowed}
        else:
            single = str(vis_val)
            if single not in active_ids:
                return {"project_id": {"$in": []}}
            match["project_id"] = ObjectId(single)

    if project_id:
        if project_id not in active_ids:
            return {"project_id": {"$in": []}}
        proj_oid = ObjectId(project_id)
        current = match.get("project_id")
        if isinstance(current, dict) and "$in" in current:
            inter = [oid for oid in current["$in"] if oid == proj_oid]
            match["project_id"] = {"$in": inter}
        else:
            match["project_id"] = proj_oid

    return match


def build_filter(
    params: Mapping[str, Any],
    reserved_keys: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """
    Constrói um filtro MongoDB a partir de parâmetros de query genéricos.
    Sintaxe suportada (estilo "field__op"):

      - field=value          ->  {"field": value}
      - field__in=a,b,c      ->  {"field": {"$in": ["a","b","c"]}}
      - field__gte=value     ->  {"field": {"$gte": value}}
      - field__lte=value     ->  {"field": {"$lte": value}}
      - field__regex=pattern ->  {"field": {"$regex": pattern}}
    Regras:
      - Ignora chaves que começam com "_" (ex.: _internal).
      - Ignora chaves em reserved_keys (project_id, limit, etc).
      - Ignora valores vazios (None, "").
      - Acumula múltiplos operadores por campo (ex.: gte + lte).
    """
    reserved = reserved_keys or set()

    filt: Dict[str, Any] = {}
    accum: Dict[str, Dict[str, Any]] = {}

    for key, value in params.items():
        if key.startswith("_"):
            continue
        if key in reserved:
            continue
        if value in (None, ""):
            continue
        if "__" in key:
            field, op = key.split("__", 1)
        else:
            field, op = key, None
        if op == "in":
            if isinstance(value, list):
                vals = [v for v in value if v not in ("", None)]
            else:
                vals = [v for v in str(value).split(",") if v != ""]
            filt[field] = {"$in": vals}
        elif op in ("gte", "lte"):
            accum.setdefault(field, {})
            accum[field][f"${op}"] = value
        elif op == "regex":
            accum.setdefault(field, {})
            accum[field]["$regex"] = value
        else:
            filt[field] = value

    for field, cond in accum.items():
        if field in filt and isinstance(filt[field], dict):
            filt[field].update(cond)
        else:
            filt[field] = cond

    return filt


def apply_extra_filters(
    match: Dict[str, Any],
    extra_filters: Optional[Dict[str, Any]],
    reserved_keys: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """
    Constrói filtros adicionais via build_filter e faz merge no 'match'.
    - 'match' é o filtro base (visibilidade, project_id, janela temporal, etc).
    - 'extra_filters' são os query params crus vindos da API (sem os params de controle).
    - 'reserved_keys' opcional para impedir que certos campos virem filtros.
    """
    if not extra_filters:
        return match

    built = build_filter(extra_filters, reserved_keys=reserved_keys)
    if not built:
        return match

    return merge_filters(match, built)


def apply_time_window(
    match: Dict[str, Any],
    gte: Optional[str],
    lte: Optional[str],
) -> Dict[str, Any]:
    """
    Aplica janela temporal em 'timestamp' usando comparação de string ISO.
    Regras:
      - Se já existir 'timestamp' como igualdade simples (ex.: "timestamp": "X").
      - Se já existir um dict em "timestamp", faz merge com $gte / $lte.
      - Se não existir, cria um dict com os operadores informados.
    """
    if not gte and not lte:
        return match

    if "timestamp" in match and not isinstance(match["timestamp"], dict):
        return match

    if "timestamp" in match and isinstance(match["timestamp"], dict):
        cond = dict(match["timestamp"])
    else:
        cond: Dict[str, Any] = {}

    if gte:
        cond["$gte"] = gte
    if lte:
        cond["$lte"] = lte

    if cond:
        match["timestamp"] = cond

    return match


def merge_filters(base: Dict[str, Any], extra: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Faz merge de dois filtros MongoDB simples, campo a campo.
    Regras:
      - Se 'extra' for None ou vazio, retorna 'base' como está.
      - Se ambos tiverem o mesmo campo com dicts, faz update() no dict do base.
      - Caso contrário, 'extra' sobrescreve o valor de 'base' para aquele campo.
    """
    if not extra:
        return base

    merged = dict(base)
    for k, v in extra.items():
        if k in merged and isinstance(merged[k], dict) and isinstance(v, dict):
            merged[k].update(v)
        else:
            merged[k] = v
    return merged


def convert_timestamp_filters(query: Dict[str, Any]) -> Dict[str, Any]:
    """
    Converte filtros de timestamp.
    - Se 'timestamp' não for um dict, não faz nada (igualdade simples).
    - Se 'timestamp' for dict mas sem $gte/$lte válidos, não faz nada.
    - Quando converte, REMOVE o campo 'timestamp' literal e adiciona
      um bloco $expr dentro de um $and.
    """
    if not query or not isinstance(query, dict):
        return query

    ts_filter = query.get("timestamp")
    if not isinstance(ts_filter, dict):
        return query

    gte = ts_filter.get("$gte")
    lte = ts_filter.get("$lte")
    if not (gte or lte):
        return query

    expr_parts = []

    if gte:
        try:
            datetime.fromisoformat(str(gte).replace("Z", "+00:00"))
            expr_parts.append(
                {"$gte": [{"$toDate": "$timestamp"}, {"$toDate": gte}]}
            )
        except Exception:
            pass

    if lte:
        try:
            datetime.fromisoformat(str(lte).replace("Z", "+00:00"))
            expr_parts.append(
                {"$lte": [{"$toDate": "$timestamp"}, {"$toDate": lte}]}
            )
        except Exception:
            pass

    if not expr_parts:
        return query

    new_query = dict(query)
    new_query.pop("timestamp", None)

    expr_block = {"$expr": {"$and": expr_parts}}

    if "$and" in new_query and isinstance(new_query["$and"], list):
        new_query["$and"].append(expr_block)
    else:
        new_query = {"$and": [new_query, expr_block]}

    return new_query


def cap_limit(limit: Optional[int], default: int, maximum: int) -> int:
    """
    Normaliza o parâmetro 'limit' com um valor padrão e um teto máximo.
    - Se limit for None ou não for inteiro, aplica 'default'.
    - Garante 1 <= limit <= maximum.
    """
    if limit is None:
        return default
    
    try:
        n = int(limit)
    except Exception:
        return default

    if n < 1:
        return 1
    if n > maximum:
        return maximum
    return n
