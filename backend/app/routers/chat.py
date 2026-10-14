"""Chat: conversation list, history and message sending."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models, schemas
from ..database import get_session
from ..deps import get_current_user
from ..realtime import channel_for_conversation, hub
from ..utils import utcnow

router = APIRouter(prefix="/chat", tags=["chat"])


# ------------------------------------------------------------------- helpers
async def _membership(
    session: AsyncSession, user: models.User, conversation_id: str
) -> models.Conversation:
    conversation = await session.get(models.Conversation, conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Suhbat topilmadi.")
    member = await session.scalar(
        select(models.ConversationMember).where(
            models.ConversationMember.conversation_id == conversation_id,
            models.ConversationMember.user_id == user.id,
        )
    )
    if member is None and not conversation.is_system:
        raise HTTPException(status_code=403, detail="Bu suhbatga ruxsat yo'q.")
    return conversation


async def _unread_for(
    session: AsyncSession, user_id: str, conversation_id: str, last_read_at
) -> int:
    filters = [
        models.Message.conversation_id == conversation_id,
        models.Message.sender_id != user_id,
    ]
    if last_read_at is not None:
        filters.append(models.Message.created_at > last_read_at)
    return int(await session.scalar(select(func.count(models.Message.id)).where(*filters)) or 0)


def _message_out(message: models.Message, user_id: str) -> schemas.MessageOut:
    return schemas.MessageOut(
        id=message.id,
        conversation_id=message.conversation_id,
        sender_id=message.sender_id,
        sender_name=message.sender_name or ("Siz" if message.sender_id == user_id else None),
        body=message.body,
        kind=message.kind,
        attachment_url=message.attachment_url,
        created_at=message.created_at,
        is_mine=message.sender_id == user_id,
    )


async def _conversation_out(
    session: AsyncSession, user: models.User, conversation: models.Conversation
) -> schemas.ConversationOut:
    member = await session.scalar(
        select(models.ConversationMember).where(
            models.ConversationMember.conversation_id == conversation.id,
            models.ConversationMember.user_id == user.id,
        )
    )
    last_read_at = member.last_read_at if member else None

    last_message = await session.scalar(
        select(models.Message)
        .where(models.Message.conversation_id == conversation.id)
        .order_by(models.Message.created_at.desc())
        .limit(1)
    )

    members_rows = (
        await session.execute(
            select(models.ConversationMember).where(
                models.ConversationMember.conversation_id == conversation.id
            )
        )
    ).scalars().all()

    member_ids = [row.user_id for row in members_rows if row.user_id]
    users: dict[str, models.User] = {}
    if member_ids:
        for row_user in (
            await session.execute(select(models.User).where(models.User.id.in_(member_ids)))
        ).scalars().all():
            users[row_user.id] = row_user

    members: list[schemas.ChatUserBrief] = []
    for row in members_rows:
        if row.bot_name:
            members.append(schemas.ChatUserBrief(name=row.bot_name, emoji="🤖", is_bot=True))
        elif row.user_id and row.user_id in users:
            row_user = users[row.user_id]
            members.append(
                schemas.ChatUserBrief(
                    id=row_user.id,
                    name=row_user.display_name,
                    avatar_url=row_user.avatar_url,
                    emoji=row_user.avatar_emoji,
                )
            )

    others = [m for m in members if m.id != user.id]
    title = conversation.title or (others[0].name if others else "Suhbat")

    return schemas.ConversationOut(
        id=conversation.id,
        kind=conversation.kind,
        title=title,
        emoji=conversation.emoji,
        color=conversation.color,
        is_system=conversation.is_system,
        unread_count=await _unread_for(session, user.id, conversation.id, last_read_at),
        last_message=_message_out(last_message, user.id) if last_message else None,
        last_message_at=conversation.last_message_at or (last_message.created_at if last_message else None),
        members=members,
    )


# ------------------------------------------------------------- conversations
@router.get("/conversations", response_model=list[schemas.ConversationOut])
async def list_conversations(
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[schemas.ConversationOut]:
    conversation_ids = [
        row[0]
        for row in (
            await session.execute(
                select(models.ConversationMember.conversation_id).where(
                    models.ConversationMember.user_id == user.id
                )
            )
        ).all()
    ]
    if not conversation_ids:
        return []

    conversations = (
        await session.execute(
            select(models.Conversation)
            .where(models.Conversation.id.in_(conversation_ids))
            .order_by(
                models.Conversation.last_message_at.desc().nullslast(),
                models.Conversation.created_at.desc(),
            )
        )
    ).scalars().all()

    return [await _conversation_out(session, user, item) for item in conversations]


@router.post(
    "/conversations",
    response_model=schemas.ConversationOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_conversation(
    payload: schemas.ConversationCreate,
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> schemas.ConversationOut:
    member_ids = [mid for mid in dict.fromkeys(payload.member_ids) if mid != user.id]
    if member_ids:
        found = (
            await session.execute(
                select(models.User.id).where(models.User.id.in_(member_ids))
            )
        ).all()
        member_ids = [row[0] for row in found]

    if payload.kind == "direct" and len(member_ids) != 1:
        raise HTTPException(
            status_code=422, detail="Shaxsiy suhbat uchun aynan bitta qatnashchi kerak."
        )

    if payload.kind == "direct" and member_ids:
        # Reuse the existing 1:1 conversation when there is one.
        existing = (
            await session.execute(
                select(models.Conversation.id)
                .join(
                    models.ConversationMember,
                    models.ConversationMember.conversation_id == models.Conversation.id,
                )
                .where(
                    models.Conversation.kind == "direct",
                    models.ConversationMember.user_id.in_([user.id, member_ids[0]]),
                )
                .group_by(models.Conversation.id)
                .having(func.count(models.ConversationMember.id) == 2)
            )
        ).first()
        if existing:
            conversation = await session.get(models.Conversation, existing[0])
            return await _conversation_out(session, user, conversation)

    conversation = models.Conversation(
        kind=payload.kind,
        title=payload.title,
        emoji=payload.emoji,
    )
    session.add(conversation)
    await session.flush()

    session.add(
        models.ConversationMember(
            conversation_id=conversation.id, user_id=user.id, role="owner"
        )
    )
    for member_id in member_ids:
        session.add(
            models.ConversationMember(conversation_id=conversation.id, user_id=member_id)
        )

    await session.commit()
    await session.refresh(conversation)

    for member_id in member_ids:
        await hub.send_personal(
            member_id,
            {
                "type": "conversation.created",
                "data": {"conversation_id": conversation.id},
            },
        )
    return await _conversation_out(session, user, conversation)


@router.get("/conversations/{conversation_id}", response_model=schemas.ConversationOut)
async def get_conversation(
    conversation_id: str,
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> schemas.ConversationOut:
    conversation = await _membership(session, user, conversation_id)
    return await _conversation_out(session, user, conversation)


# -------------------------------------------------------------------- messages
@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[schemas.MessageOut],
)
async def list_messages(
    conversation_id: str,
    limit: int = Query(default=50, ge=1, le=200),
    before: str | None = Query(default=None, description="Message id (cursor)"),
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[schemas.MessageOut]:
    await _membership(session, user, conversation_id)

    query = select(models.Message).where(models.Message.conversation_id == conversation_id)
    if before:
        cursor = await session.get(models.Message, before)
        if cursor is not None:
            query = query.where(models.Message.created_at < cursor.created_at)
    rows = (
        await session.execute(query.order_by(models.Message.created_at.desc()).limit(limit))
    ).scalars().all()
    rows.reverse()
    return [_message_out(row, user.id) for row in rows]


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=schemas.MessageOut,
    status_code=status.HTTP_201_CREATED,
)
async def send_message(
    conversation_id: str,
    payload: schemas.MessageCreate,
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> schemas.MessageOut:
    conversation = await _membership(session, user, conversation_id)

    message = models.Message(
        conversation_id=conversation.id,
        sender_id=user.id,
        sender_name=user.display_name,
        body=payload.body.strip(),
        kind=payload.kind,
        attachment_url=payload.attachment_url,
    )
    session.add(message)
    conversation.last_message_at = utcnow()
    await session.flush()

    # The sender has obviously read their own message.
    member = await session.scalar(
        select(models.ConversationMember).where(
            models.ConversationMember.conversation_id == conversation.id,
            models.ConversationMember.user_id == user.id,
        )
    )
    if member is not None:
        member.last_read_at = utcnow()

    await session.commit()
    await session.refresh(message)

    out = _message_out(message, user.id)
    await hub.broadcast(
        channel_for_conversation(conversation.id),
        {"type": "message.created", "data": out.model_dump(mode="json")},
    )

    # Notify the other human members so their badge updates without a refresh.
    others = (
        await session.execute(
            select(models.ConversationMember.user_id).where(
                models.ConversationMember.conversation_id == conversation.id,
                models.ConversationMember.user_id.is_not(None),
                models.ConversationMember.user_id != user.id,
            )
        )
    ).all()
    for (member_id,) in others:
        await hub.send_personal(
            member_id,
            {
                "type": "message.notification",
                "data": {
                    "conversation_id": conversation.id,
                    "title": conversation.title or user.display_name,
                    "body": message.body[:120],
                },
            },
        )

    await _maybe_bot_reply(session, conversation, message, user)
    return out


@router.post("/conversations/{conversation_id}/read", response_model=schemas.Message)
async def mark_read(
    conversation_id: str,
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> schemas.Message:
    conversation = await _membership(session, user, conversation_id)
    member = await session.scalar(
        select(models.ConversationMember).where(
            models.ConversationMember.conversation_id == conversation.id,
            models.ConversationMember.user_id == user.id,
        )
    )
    if member is not None:
        member.last_read_at = utcnow()
        await session.commit()
    await hub.broadcast(
        channel_for_conversation(conversation.id),
        {"type": "conversation.read", "data": {"user_id": user.id}},
    )
    return schemas.Message(detail="O'qilgan deb belgilandi.")


@router.get("/unread-count", response_model=schemas.UnreadCount)
async def chat_unread(
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> schemas.UnreadCount:
    memberships = (
        await session.execute(
            select(models.ConversationMember).where(
                models.ConversationMember.user_id == user.id
            )
        )
    ).scalars().all()

    unread = 0
    for membership in memberships:
        unread += await _unread_for(
            session, user.id, membership.conversation_id, membership.last_read_at
        )
    return schemas.UnreadCount(unread=unread, total=len(memberships))


# ------------------------------------------------------------------ bot reply
BOT_REPLIES = {
    "support": (
        "Xabaringiz uchun rahmat! Operatorimiz tez orada javob beradi. "
        "Shoshilinch bo'lsa: +998 90 000 00 00"
    ),
    "bot": (
        "Men Alomat botman 🤖 Savolingizni yozing — grammatika, so'z boyligi "
        "yoki darslar bo'yicha yordam beraman."
    ),
}


async def _maybe_bot_reply(
    session: AsyncSession,
    conversation: models.Conversation,
    message: models.Message,
    user: models.User,
) -> None:
    """Auto-answer inside system support/bot conversations."""
    if conversation.kind not in BOT_REPLIES:
        return
    if message.sender_id is None:  # already a bot message
        return

    reply = models.Message(
        conversation_id=conversation.id,
        sender_id=None,
        sender_name=conversation.title or "Alomat",
        body=BOT_REPLIES[conversation.kind],
        kind="text",
    )
    session.add(reply)
    conversation.last_message_at = utcnow()
    await session.commit()
    await session.refresh(reply)

    await hub.broadcast(
        channel_for_conversation(conversation.id),
        {
            "type": "message.created",
            "data": _message_out(reply, user.id).model_dump(mode="json"),
        },
    )
