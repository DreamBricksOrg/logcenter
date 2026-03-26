import os

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates


router = APIRouter(prefix="/pages")

BASE_DIR = os.path.dirname(__file__) 
TEMPLATES_DIR = os.path.normpath(os.path.join(BASE_DIR, "..", "static", "templates"))
templates = Jinja2Templates(directory=TEMPLATES_DIR)

@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def page_home(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@router.get("/admin", include_in_schema=False)
async def page_admin(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})

@router.get("/form", include_in_schema=False)
async def page_form(request: Request):
    return templates.TemplateResponse("form.html", {"request": request})

@router.get("/clients", include_in_schema=False)
async def page_clients(request: Request):
    return templates.TemplateResponse("clients.html", {"request": request})

@router.get("/clients/form", include_in_schema=False)
async def page_clients_form(request: Request):
    return templates.TemplateResponse("clients_form.html", {"request": request})