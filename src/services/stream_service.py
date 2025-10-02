import asyncio
from typing import Dict, Set, Any

class BroadcastManager:
    """
    Broadcast in-memory por "canal" (ex.: project_code).
    Cada canal tem um set de websockets conectados.
    """
    def __init__(self) -> None:
        self._channels: Dict[str, Set[Any]] = {}
        self._lock = asyncio.Lock()

    async def join(self, channel: str, ws) -> None:
        async with self._lock:
            self._channels.setdefault(channel, set()).add(ws)

    async def leave(self, channel: str, ws) -> None:
        async with self._lock:
            conns = self._channels.get(channel, set())
            conns.discard(ws)
            if not conns and channel in self._channels:
                del self._channels[channel]

    async def broadcast(self, channel: str, message: str) -> None:
        # envia para todos do canal; remove desconectados
        targets = list(self._channels.get(channel, set()))
        to_remove = []
        for ws in targets:
            try:
                await ws.send_text(message)
            except Exception:
                to_remove.append(ws)
        if to_remove:
            async with self._lock:
                for ws in to_remove:
                    self._channels.get(channel, set()).discard(ws)

manager = BroadcastManager()
