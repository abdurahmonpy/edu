"""In-process pub/sub used by the chat, battle and notification WebSockets.

A single Railway instance is the expected deployment, so an in-process registry
is enough.  For multi-instance scaling, swap ``RealtimeHub.broadcast`` for a
Redis pub/sub fan-out — the call sites do not need to change.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any

from fastapi import WebSocket


class RealtimeHub:
    def __init__(self) -> None:
        self._rooms: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def join(self, room: str, websocket: WebSocket) -> None:
        async with self._lock:
            self._rooms[room].add(websocket)

    async def leave(self, room: str, websocket: WebSocket) -> None:
        async with self._lock:
            sockets = self._rooms.get(room)
            if not sockets:
                return
            sockets.discard(websocket)
            if not sockets:
                self._rooms.pop(room, None)

    async def leave_all(self, websocket: WebSocket) -> None:
        async with self._lock:
            for room in list(self._rooms):
                self._rooms[room].discard(websocket)
                if not self._rooms[room]:
                    self._rooms.pop(room, None)

    def rooms_for(self, websocket: WebSocket) -> list[str]:
        return [room for room, sockets in self._rooms.items() if websocket in sockets]

    async def broadcast(self, room: str, payload: dict[str, Any]) -> None:
        async with self._lock:
            targets = list(self._rooms.get(room, ()))
        if not targets:
            return
        dead: list[WebSocket] = []
        for websocket in targets:
            try:
                await websocket.send_json(payload)
            except Exception:  # noqa: BLE001 - a broken socket must not break the fan-out
                dead.append(websocket)
        for websocket in dead:
            await self.leave(room, websocket)

    async def send_personal(self, user_id: str, payload: dict[str, Any]) -> None:
        await self.broadcast(f"user:{user_id}", payload)

    async def room_size(self, room: str) -> int:
        async with self._lock:
            return len(self._rooms.get(room, ()))


hub = RealtimeHub()


def channel_for_conversation(conversation_id: str) -> str:
    return f"conversation:{conversation_id}"


def channel_for_battle(battle_id: str) -> str:
    return f"battle:{battle_id}"


def channel_for_user(user_id: str) -> str:
    return f"user:{user_id}"
