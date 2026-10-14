"""In-app notifications."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models, schemas
from ..database import get_session
from ..deps import get_current_user, require_admin

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=schemas.Page[schemas.NotificationOut])
async def list_notifications(
    unread_only: bool = False,
    kind: str | None = None,
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> schemas.Page[schemas.NotificationOut]:
    filters = [models.Notification.user_id == user.id]
    if unread_only:
        filters.append(models.Notification.is_read.is_(False))
    if kind:
        filters.append(models.Notification.kind == kind)

    total = await session.scalar(select(func.count(models.Notification.id)).where(*filters))
    rows = (
        await session.execute(
            select(models.Notification)
            .where(*filters)
            .order_by(models.Notification.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    ).scalars().all()

    return schemas.Page(
        items=[schemas.NotificationOut.model_validate(row) for row in rows],
        total=int(total or 0),
        limit=limit,
        offset=offset,
    )


@router.get("/unread-count", response_model=schemas.UnreadCount)
async def unread_count(
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> schemas.UnreadCount:
    unread = await session.scalar(
        select(func.count(models.Notification.id)).where(
            models.Notification.user_id == user.id,
            models.Notification.is_read.is_(False),
        )
    )
    total = await session.scalar(
        select(func.count(models.Notification.id)).where(
            models.Notification.user_id == user.id
        )
    )
    return schemas.UnreadCount(unread=int(unread or 0), total=int(total or 0))


@router.post("/read-all", response_model=schemas.Message)
async def mark_all_read(
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> schemas.Message:
    await session.execute(
        update(models.Notification)
        .where(
            models.Notification.user_id == user.id,
            models.Notification.is_read.is_(False),
        )
        .values(is_read=True)
    )
    await session.commit()
    return schemas.Message(detail="Barcha bildirishnomalar o'qilgan deb belgilandi.")


@router.post("/{notification_id}/read", response_model=schemas.NotificationOut)
async def mark_read(
    notification_id: str,
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> schemas.NotificationOut:
    notification = await session.get(models.Notification, notification_id)
    if notification is None or notification.user_id != user.id:
        raise HTTPException(status_code=404, detail="Bildirishnoma topilmadi.")
    notification.is_read = True
    await session.commit()
    await session.refresh(notification)
    return schemas.NotificationOut.model_validate(notification)


@router.delete("/{notification_id}", response_model=schemas.Message)
async def delete_notification(
    notification_id: str,
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> schemas.Message:
    notification = await session.get(models.Notification, notification_id)
    if notification is None or notification.user_id != user.id:
        raise HTTPException(status_code=404, detail="Bildirishnoma topilmadi.")
    await session.delete(notification)
    await session.commit()
    return schemas.Message(detail="Bildirishnoma o'chirildi.")


@router.post(
    "",
    response_model=schemas.NotificationOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
async def create_notification(
    payload: schemas.NotificationCreate,
    session: AsyncSession = Depends(get_session),
) -> schemas.NotificationOut:
    """Admin broadcast. Without ``user_id`` the notification goes to everyone."""
    targets: list[str]
    if payload.user_id:
        if await session.get(models.User, payload.user_id) is None:
            raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi.")
        targets = [payload.user_id]
    else:
        targets = [
            user_id
            for (user_id,) in (
                await session.execute(
                    select(models.User.id).where(models.User.is_active.is_(True))
                )
            ).all()
        ]

    created: list[models.Notification] = []
    for user_id in targets:
        created.append(
            models.Notification(
                user_id=user_id,
                kind=payload.kind,
                title=payload.title,
                body=payload.body,
                banner=payload.banner,
                link=payload.link,
                cta_label=payload.cta_label,
                icon=payload.icon,
            )
        )
    session.add_all(created)
    await session.commit()
    return schemas.NotificationOut.model_validate(created[0])
