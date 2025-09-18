from datetime import datetime
from typing import List, Optional, Dict
from pydantic import BaseModel

class LogCreate(BaseModel):
    project: str
    level: str
    message: str
    tags: Optional[List[str]] = []
    data: Optional[Dict] = {}
    request_id: Optional[str] = None
