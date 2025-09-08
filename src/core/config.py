import os
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/logcenter")
MONGO_DB = os.getenv("MONGO_DB", "logcenter")
SECRET_KEY = os.getenv("SECRET_KEY", "CHANGE_THIS_SECRET")
