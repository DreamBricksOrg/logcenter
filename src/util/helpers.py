import uuid
from datetime import datetime

def generate_uuid() -> str:
    return str(uuid.uuid4())

def format_datetime(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")
