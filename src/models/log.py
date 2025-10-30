from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class LogCreate(BaseModel):
    project: str = Field(..., min_length=1, description="Project code or ID")
    level: str = Field(..., min_length=1, description="INFO|WARN|ERROR|...")
    message: str = Field(..., min_length=1)
    tags: List[str] = Field(default_factory=list)
    data: Dict = Field(default_factory=dict)
    request_id: Optional[str] = Field(default=None, alias="request_id")

class LogModel(BaseModel):
    id: str
    timestamp: str
    project: str
    level: str
    message: str
    tags: List[str] = []
    data: Dict = {}
    request_id: Optional[str] = None
