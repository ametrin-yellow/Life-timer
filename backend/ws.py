from fastapi import WebSocket
from collections import defaultdict


class ConnectionManager:
    def __init__(self):
        self._connections: dict[int, list[WebSocket]] = defaultdict(list)

    async def connect(self, user_id: int, ws: WebSocket):
        await ws.accept()
        self._connections[user_id].append(ws)

    def disconnect(self, user_id: int, ws: WebSocket):
        conns = self._connections[user_id]
        if ws in conns:
            conns.remove(ws)
        if not conns:
            del self._connections[user_id]

    async def broadcast_to_user(self, user_id: int, data: dict):
        for ws in self._connections.get(user_id, []):
            try:
                await ws.send_json(data)
            except Exception:
                pass


manager = ConnectionManager()
