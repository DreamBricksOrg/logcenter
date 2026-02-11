from pydantic import BaseModel, Field
from typing import Optional, List, Literal

PROJECT_CODE_PATTERN = r"^[a-z0-9\-_.]+$"
ProjectStatus = Literal["active", "inactive"]


class ProjectConfigIn(BaseModel):
    defaultTags: Optional[List[str]] = Field(default=None, description="Tags padrão a serem aplicadas")
    separator: Optional[str] = Field(default=None, description="Separador para exportação (ex: ';')")
    exportFields: Optional[List[str]] = Field(default=None, description="Campos exportados no CSV (ex: 'data.userId')")


class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., pattern=PROJECT_CODE_PATTERN)
    description: Optional[str] = Field(default=None, max_length=300)
    config: Optional[ProjectConfigIn] = None
    api_key_plain: Optional[str] = Field(default=None, min_length=8)
    status: Optional[ProjectStatus] = Field(default="active")


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    code: Optional[str] = Field(default=None, pattern=PROJECT_CODE_PATTERN)
    description: Optional[str] = Field(default=None, max_length=300)
    config: Optional[ProjectConfigIn] = None
    api_key_plain: Optional[str] = Field(default=None, min_length=8)
    status: Optional[ProjectStatus] = None


class ProjectOut(BaseModel):
    id: str = Field(alias="_id")
    name: str
    code: str
    has_api_key: bool
    description: Optional[str] = None
    config: Optional[dict] = None
    createdAt: str
    status: ProjectStatus

    model_config = {
        "populate_by_name": True,
        "extra": "ignore",
    }

class ProjectListFilters(BaseModel):
    name: Optional[str] = Field(default=None, description="Filtro por nome (contém, case-insensitive)")
    code: Optional[str] = Field(default=None, description="Filtro por code (contém, case-insensitive)")
    status: Optional[ProjectStatus] = Field(default=None, description="Filtro por status exato")
    has_api_key: Optional[bool] = Field(default=None, description="Filtra por presença de api key (hash)")

class ProjectListResponse(BaseModel):
    items: List["ProjectOut"]
    total: int
    page: int
    page_size: int
