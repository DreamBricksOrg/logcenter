from __future__ import annotations
from typing import Optional, Any
from pydantic import BaseModel, Field

class DashLevelCount(BaseModel):
    level: str = Field(..., description="Nível do log (UPPER).")
    count: int = Field(..., ge=0)

class DashTopUser(BaseModel):
    userId: Optional[str] = Field(None, description="Identificador do usuário (pode ser nulo se não informado).")
    count: int = Field(..., ge=0)

class DashTopEndpoint(BaseModel):
    endpoint: Optional[str] = Field(None, description="Endpoint/rota agregada (pode ser nulo se não informado).")
    count: int = Field(..., ge=0)

class DashTopTag(BaseModel):
    tag: Optional[str] = Field(None, description="Tag agregada (elemento de tags[]).")
    count: int = Field(..., ge=0)

class DashTopDataKey(BaseModel):
    key: str = Field(..., description="Nome da chave encontrada em data.")
    count: int = Field(..., ge=0)

class DashTopDataValue(BaseModel):
    item: str = Field(..., description="Nome do item (chave em data) analisado.")
    value: Optional[Any] = Field(None, description="Valor agregado de data.<item>.")
    count: int = Field(..., ge=0)
