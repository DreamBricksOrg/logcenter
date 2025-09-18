from fastapi import APIRouter, HTTPException, Response, Form
from typing import Optional
from services import log_service
from models.log import LogCreate

router = APIRouter(prefix="/logs", tags=["logs"])

@router.post("/", status_code=200)
def create_log(log: LogCreate):
    """Recebe um novo log padronizado e insere no MongoDB."""
    try:
        log_id = log_service.create_log(
            project=log.project,
            level=log.level,
            message=log.message,
            tags=log.tags,
            data=log.data,
            request_id=log.request_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"id": log_id}

@router.get("/")
def list_logs(project: Optional[str] = None):
    """Lista logs, opcionalmente filtrando por projeto (id ou nome)."""
    return log_service.get_logs(project)

@router.get("/latest")
def get_latest_log(project: Optional[str] = None):
    """Retorna o último uploadedData em ISO (ou 404 se não houver)."""
    latest_time = log_service.get_latest_log_time(project)
    if latest_time is None:
        raise HTTPException(status_code=404, detail="No log data found.")
    return {"latestUploadedData": latest_time}

@router.get("/status/count")
def get_status_count(project: Optional[str] = None):
    """Agrega contagem de logs por status."""
    return log_service.get_status_counts(project)

@router.get("/download")
def download_logs(project: Optional[str] = None):
    """Exporta os logs em CSV dentro de um ZIP (streaming)."""
    csv_bytes_io, zip_filename = log_service.generate_logs_csv(project)
    from fastapi.responses import StreamingResponse
    headers = {'Content-Disposition': f'attachment; filename={zip_filename}'}
    return StreamingResponse(csv_bytes_io, media_type='application/zip', headers=headers)
