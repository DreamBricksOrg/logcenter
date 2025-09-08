from fastapi import APIRouter, HTTPException, Form
from services import project_service

router = APIRouter(prefix="/projects", tags=["projects"])

@router.post("/", status_code=201)
def create_project(name: str = Form(...), owner: str = Form(...)):
    """Cria um projeto para agrupar logs."""
    if not name or not owner:
        raise HTTPException(status_code=400, detail="Name and owner are required fields.")
    project_service.create_project(name, owner)
    return {"detail": "Project created."}

@router.get("/")
def list_projects():
    """Lista todos os projetos."""
    return project_service.get_all_projects()
