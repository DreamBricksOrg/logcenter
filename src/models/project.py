from pydantic import BaseModel, Field
from typing import Optional

PROJECT_CODE_PATTERN = r"^[a-z0-9\-_.]+$"

class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    code: str = Field(pattern=PROJECT_CODE_PATTERN)
    api_key_plain: Optional[str] = Field(default=None, min_length=8)

class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    code: Optional[str] = Field(default=None, pattern=PROJECT_CODE_PATTERN)
    api_key_plain: Optional[str] = Field(default=None, min_length=8)

class ProjectOut(BaseModel):
    _id: str
    name: str
    code: str
    has_api_key: bool

class ProjectModel(BaseModel):
    id: str = Field(..., alias="_id")
    name: str
    code: str
    has_api_key: bool = True

    class Config:
        allow_population_by_field_name = True
