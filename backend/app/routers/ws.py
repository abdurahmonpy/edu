"""WebSocket endpoints: chat rooms, battles and per-user notifications.

Authentication uses the access token either as ``?token=`` or via the standard
``Authorization: Bearer`` header, since browsers cannot set headers on
``new WebSocket()``.
"""

from __future__ import annotations

import asyncio
import contextlib

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from .. import models
from ..database import SessionLocal
from ..deps import user_from_ws
from ..realtime import (
    channel_for_battle,
    channel_for_conversation,
    channel_for_user,
    hub,
)
from ..utils import utcnow

router = APIRouter(tags=["realtime"])

HEARTBEAT_SECONDS = 25


async def _close(websocket: WebSocket, code: int, reason: str) -> None:
    with contextlib.suppress(Exception):
        await websocket.close(code=code, reason=reason)


async def _keepalive(websocket: WebSocket, stop: asyncio.Event) -> None:
    """Ping the client so idle proxies (Railway/Cloudflare) don't drop the socket."""
    while not stop.is_set():
        try:
            await asyncio.wait_for(stop.wait(), timeout=HEARTBEAT_SECONDS)
            return
        except TimeoutError:
            try:
                await websocket.send_json({"type": "ping", "data": {"ts": utcnow().isoformat()}})
            except Exception:  # noqa: BLE001
                return


async def _serve(websocket: WebSocket, channel: str, on_message=None) -> None:
    await websocket.accept()
    await hub.join(channel, websocket)

    stop = asyncio.Event()
    keepalive = asyncio.create_task(_keepalive(websocket, stop))

    try:
        await websocket.send_json({"type": "connected", "data": {"channel": channel}})
        while True:
            payload = await websocket.receive_json()
            if not isinstance(payload, dict):
                continue
            kind = payload.get("type")
            if kind == "ping":
                await websocket.send_json({"type": "pong", "data": {}})
                continue
            if kind == "typing":
                await hub.broadcast(
                    channel,
                    {"type": "typing", "data": payload.get("data") or {}},
                )
                continue
            if on_message is not None:
                await on_message(payload)
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001 - never let a bad frame kill the worker
        pass
    finally:
        stop.set()
        keepalive.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await keepalive
        await hub.leave(channel, websocket)


# ===========================================================================
# chat
# ===========================================================================
@router.websocket("/ws/chat/{conversation_id}")
async def chat_socket(websocket: WebSocket, conversation_id: str) -> None:
    async with SessionLocal() as session:
        user = await user_from_ws(websocket, session)
        if user is None:
            await _close(websocket, 4401, "unauthorized")
            return

        conversation = await session.get(models.Conversation, conversation_id)
        if conversation is None:
            await _close(websocket, 4404, "conversation not found")
            return

        member = await session.scalar(
            select(models.ConversationMember).where(
                models.ConversationMember.conversation_id == conversation_id,
                models.ConversationMember.user_id == user.id,
            )
        )
        if member is None and not conversation.is_system:
            await _close(websocket, 4403, "forbidden")
            return

        channel = channel_for_conversation(conversation_id)
        await _serve(websocket, channel)


# ===========================================================================
# battles
# ===========================================================================
@router.websocket("/ws/battles/{battle_id}")
async def battle_socket(websocket: WebSocket, battle_id: str) -> None:
    async with SessionLocal() as session:
        user = await user_from_ws(websocket, session)
        if user is None:
            await _close(websocket, 4401, "unauthorized")
            return

        battle = await session.get(models.Battle, battle_id)
        if battle is None:
            await _close(websocket, 4404, "battle not found")
            return
        if user.id not in {battle.host_id, battle.guest_id} and battle.status == "waiting":
            # A waiting battle accepts one more player; announce them.
            await hub.broadcast(
                channel_for_battle(battle_id),
                {"type": "battle.spectator", "data": {"user_id": user.id}},
            )
        elif user.id not in {battle.host_id, battle.guest_id}:
            await _close(websocket, 4403, "forbidden")
            return

        await _serve(websocket, channel_for_battle(battle_id))


# ===========================================================================
# notifications
# ===========================================================================
@router.websocket("/ws/notifications")
async def notifications_socket(websocket: WebSocket) -> None:
    async with SessionLocal() as session:
        user = await user_from_ws(websocket, session)
        if user is None:
            await _close(websocket, 4401, "unauthorized")
            return
        await _serve(websocket, channel_for_user(user.id))
