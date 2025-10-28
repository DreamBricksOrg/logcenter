from __future__ import annotations
from typing import Optional
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
