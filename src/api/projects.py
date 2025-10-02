from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from db.utils import get_db
from models.project import ProjectCreate, ProjectModel

router = APIRouter(prefix="/projects", tags=["projects"])
db = get_db()

@router.post("/", response_model=ProjectModel, status_code=201)
def create_project(payload: ProjectCreate):
    doc = {"name": payload.name, "code": payload.code, "api_key": payload.api_key}
    res = db["projects"].insert_one(doc)
    doc["_id"] = str(res.inserted_id)
    return doc

@router.get("/", response_model=List[ProjectModel])
def list_projects():
    docs = list(db["projects"].find().limit(1000))
    for d in docs:
        d["_id"] = str(d["_id"])
    return docs
