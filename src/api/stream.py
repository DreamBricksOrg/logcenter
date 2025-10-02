from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from typing import Optional
import json
from core.auth import require_principal
from services.stream_service import manager

router = APIRouter(prefix="/ws", tags=["realtime"])

@router.websocket("/logs")
async def logs_ws(
    websocket: WebSocket,
    project: Optional[str] = Query(default=None),
    principal = Depends(require_principal),
):
    """
    Conecta no canal de logs.
    - admin: se 'project' omitido, rejeita (obrigue a escolher um canal), ou decida unir em vários.
    - client: força ao(s) projeto(s) que ele tem permissão (se mandar outro, ignora e usa o permitido).
    """
    await websocket.accept()

    if principal["role"] == "client":
        channel = principal["project_codes"][0]
    else:
        channel = project or None

    if not channel:
        await websocket.send_text(json.dumps({"error": "project required"}))
        await websocket.close()
        return

    await manager.join(channel, websocket)
    try:
        while True:
            _ = await websocket.receive_text()
            await websocket.send_text(json.dumps({"ok": True, "channel": channel}))
    except WebSocketDisconnect:
        await manager.leave(channel, websocket)
