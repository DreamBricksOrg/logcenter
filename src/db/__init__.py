import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
MONGO_DB = os.getenv("MONGO_DB", "logcenter")

client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
db = client[MONGO_DB]

if os.getenv("MONGO_DEBUG", "false").lower() == "true":
    try:
        print(f"[DB] Connected to {MONGODB_URI}, using database '{MONGO_DB}'")
        print(f"[DB] Server info: {client.server_info()}")
    except Exception as e:
        print(f"[DB] Unable to connect to database: {e}")
