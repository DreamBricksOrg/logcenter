from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

import httpx
from core.config import settings


class LogCenterSender:
    """
    Adaptação do log_sender.py do SDK:
    - Corrige redirect (usa /logs/ + follow_redirects=True)
    - Garante campos usuais (level upper, timestamp ISO)
    - Loga corpo de erro quando não for 2xx (debug de 422)
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        project_id: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 5.0,
    ):
        self.base_url = (base_url or settings.LOGCENTER_BASE_URL or "").rstrip("/")
        self.project_id = project_id or settings.LOGCENTER_PROJECT_ID
        self.api_key = api_key or settings.LOGCENTER_API_KEY
        self.timeout = httpx.Timeout(timeout, connect=timeout)

    def _headers(self) -> Dict[str, str]:
        if not self.api_key:
            return {}
        return {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key,
            "X-Internal-LogCenter": "1",
        }

    async def send_log(
        self,
        level: str,
        message: str,
        *,
        tags: Optional[List[str]] = None,
        data: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> bool:
        if not (self.base_url and self.project_id and self.api_key):
            return False

        level = (level or "INFO").upper()
        now_iso = datetime.now(timezone.utc).isoformat()

        # se não vier explícito, inferimos
        if status is None:
            status = "ERROR" if level in ("ERROR", "CRITICAL", "FATAL") else "OK"

        payload: Dict[str, Any] = {
            "project_id": self.project_id,
            "level": level,
            "message": message,
            "timestamp": now_iso,
            "status": status,
        }
        if tags:
            payload["tags"] = tags
        if data:
            payload["data"] = data
        if request_id:
            payload["request_id"] = request_id

        url = f"{self.base_url}/logs/"

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            try:
                resp = await client.post(url, headers=self._headers(), json=payload)
            except Exception:
                return False

            if 200 <= resp.status_code < 300:
                return True

            try:
                err = resp.json()
            except Exception:
                err = {"text": resp.text}
            return False

    def send_log_sync(
        self,
        level: str,
        message: str,
        *,
        tags: Optional[List[str]] = None,
        data: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
    ) -> bool:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            loop.create_task(self.send_log(level, message, tags=tags, data=data, request_id=request_id))
            return True
        else:
            return asyncio.run(self.send_log(level, message, tags=tags, data=data, request_id=request_id))
