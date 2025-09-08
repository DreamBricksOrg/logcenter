from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class ProjectBase(BaseModel):
    name: str
    owner: str

class Project(ProjectBase):
    id: str
    createdAt: datetime
    separator: Optional[str] = None
    addHeaders: Optional[str] = None
    pkeyIndex: Optional[int] = None

    class Config:
        orm_mode = True
