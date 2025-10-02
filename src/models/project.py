from pydantic import BaseModel, Field
from typing import Optional

class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1)
    code: str = Field(..., min_length=1)
    api_key: Optional[str] = None

class ProjectModel(BaseModel):
    id: str = Field(..., alias="_id")
    name: str
    code: str
    api_key: Optional[str] = None

    class Config:
        allow_population_by_field_name = True
