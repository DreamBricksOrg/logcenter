from __future__ import annotations
from typing import Any, Dict, List, Optional

from core.config import settings
from core.adapter import LogCenterSender

# instância única
_sender = LogCenterSender()

async def sdk_log(
    level: str,
    message: str,
    *,
    tags: Optional[List[str]] = None,
    data: Optional[Dict[str, Any]] = None,
    request_id: Optional[str] = None,
    status: str | None = None,
) -> bool:
    """
    Função única p/ o projeto. Não importa o SDK oficial ainda.
    """
    if not settings.LOGCENTER_SDK_ENABLED:
        return False
    return await _sender.send_log(level, message, tags=tags, data=data, request_id=request_id, status=status)
