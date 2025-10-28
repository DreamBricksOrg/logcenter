from __future__ import annotations
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Literal


UserRole = Literal["admin", "client"]


class UnifiedLoginRequest(BaseModel):
    email: EmailStr = Field(..., description="User email (admin or client)")
    password: str = Field(..., min_length=3)


class UnifiedLoginResponse(BaseModel):
    api_key: str = Field(..., description="User-scoped API key (persisted/rotated on login)")
    role: UserRole
    name: str
    user_id: str
    project_ids: List[str] = Field(default_factory=list, description="Projects the user can access (only ACTIVE)")
    project_codes: List[str] = Field(default_factory=list, description="Codes of active projects")


class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=3)


class AdminLoginResponse(BaseModel):
    api_key: str


class ProjectLoginRequest(BaseModel):
    api_key: str


class ProjectLoginResponse(BaseModel):
    project_id: str
    project_code: str
    role: str = "client"
