import asyncio
import json
from typing import Dict, Set
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self._connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, channel: str):
        await websocket.accept()
        self._connections.setdefault(channel, set()).add(websocket)

    def disconnect(self, websocket: WebSocket, channel: str):
        if channel in self._connections:
            self._connections[channel].discard(websocket)
            if not self._connections[channel]:
                del self._connections[channel]

    async def broadcast(self, channel: str, data: dict):
        conns = list(self._connections.get(channel, []))
        dead = []
        for ws in conns:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws, channel)


manager = ConnectionManager()


async def redis_subscriber():
    """Try to connect to Redis pub/sub; silently skip if Redis unavailable."""
    try:
        import redis.asyncio as aioredis
        from app.core.config import settings
        client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        await client.ping()  # test connection
        pubsub = client.pubsub()
        await pubsub.psubscribe("pipeline_run:*", "dataset:*", "quality:*")
        async for message in pubsub.listen():
            if message["type"] not in ("message", "pmessage"):
                continue
            channel = message.get("channel", "")
            try:
                data = json.loads(message["data"])
            except Exception:
                continue
            await manager.broadcast(channel, data)
    except Exception as e:
        # Redis not available — WebSocket push disabled, polling still works
        print(f"[WebSocket] Redis unavailable ({e}), live updates disabled")
        while True:
            await asyncio.sleep(3600)
