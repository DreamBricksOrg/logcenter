from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class LogCreate(BaseModel):
    project_id: str = Field(..., min_length=24, max_length=24, description="Mongo ObjectId (hex)")
    status: str = Field(..., min_length=1, description="Status textual (ex: 200 - OK)")
    level: str = Field(..., min_length=1, description="Ex: INFO|WARN|ERROR (qualquer case)")
    message: str = Field(..., min_length=1, description="Mensagem do log")
    timestamp: Optional[str] = Field(
        default=None,
        description="Horário do evento (ISO Z). Se ausente, será preenchido no servidor."
    )
    tags: List[str] = Field(default_factory=list, description="Array genérico de tags")
    data: Dict = Field(default_factory=dict, description="Objeto genérico de dados")
    request_id: Optional[str] = Field(default=None, alias="request_id", description="Request correlation id")
    
    model_config = {
        "populate_by_name": True,
        "extra": "ignore",
    }

class LogModel(BaseModel):
    _id: str
    uploadedAt: str
    timestamp: str
    status: str
    level: str
    message: str
    tags: List[str]
    data: Dict
    request_id: Optional[str] = None
    project_id: str
