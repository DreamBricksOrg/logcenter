from datetime import datetime
from db import db

def create_project(name: str, owner: str):
    created_at = datetime.utcnow().replace(microsecond=0)
    project_doc = {
        "name": name,
        "owner": owner,
        "createdAt": created_at
    }
    result = db["project"].insert_one(project_doc)
    return result.inserted_id

def get_all_projects():
    docs = list(db["project"].find())
    for doc in docs:
        doc["_id"] = str(doc["_id"])
        if "createdAt" in doc and hasattr(doc["createdAt"], "strftime"):
            doc["createdAt"] = doc["createdAt"].strftime("%Y-%m-%dT%H:%M:%SZ")
    return docs
