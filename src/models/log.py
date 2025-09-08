from datetime import datetime
from typing import Optional
from pydantic import BaseModel

class LogEntry(BaseModel):
    """Schema representando um log."""
    id: str
    uploadedData: datetime
    timePlayed: datetime
    status: str
    project: str
    additional: Optional[str] = None

    class Config:
        orm_mode = True
