from pymongo import MongoClient
from core.config import settings

_client = MongoClient(settings.MONGO_URI)
_db = _client[settings.MONGO_DB]

def get_db():
    return _db
