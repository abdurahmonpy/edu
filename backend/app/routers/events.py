"""Zoom-style live events."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models, schemas, services
from ..database import get_session
from ..deps import get_current_user, require_staff
from ..utils import utcnow

router = APIRouter(prefix="/events", tags=["events"])


async def _registered_ids(session: AsyncSession, user_id: str) -> set[str]:
    rows = (
        await session.execute(
            select(models.EventRegistration.event_id).where(
                models.EventRegistration.user_id == user_id
            )
        )
    ).all()
    return {event_id for (event_id,) in rows}


async def _counts(session: AsyncSession, event_ids: list[str]) -> dict[str, int]:
    if not event_ids:
        return {}
    rows = (
        await session.execute(
            select(models.EventRegistration.event_id, func.count(models.EventRegistration.id))
            .where(models.EventRegistration.event_id.in_(event_ids))
            .group_by(models.EventRegistration.event_id)
        )
    ).all()
    return {event_id: int(count) for event_id, count in rows}


def _to_out(
    event: models.Event,
    *,
    registered: bool,
    count: int,
    reveal_links: bool,
) -> schemas.EventOut:
    now = utcnow()
    is_past = event.starts_at < now
    out = schemas.EventOut.model_validate(event)
    out.is_past = is_past
    out.is_registered = registered
    out.registered_count = count
    # Meeting links are only handed out to registered users (or once it's over).
    out.join_url = event.join_url if (reveal_links or is_past) else None
    out.recording_url = event.recording_url if is_past else None
    return out


@router.get("", response_model=list[schemas.EventOut])
async def list_events(
    when: str = Query(default="upcoming", pattern="^(upcoming|past|all)$"),
    level: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[schemas.EventOut]:
    now = utcnow()
    query = select(models.Event).where(models.Event.is_published.is_(True))
    if when == "upcoming":
        query = query.where(models.Event.starts_at >= now).order_by(models.Event.starts_at.asc())
    elif when == "past":
        query = query.where(models.Event.starts_at < now).order_by(models.Event.starts_at.desc())
    else:
        query = query.order_by(models.Event.starts_at.desc())
    if level:
        query = query.where(models.Event.level == level)

    events = (await session.execute(query.limit(limit))).scalars().all()
    registered = await _registered_ids(session, user.id)
    counts = await _counts(session, [event.id for event in events])

    return [
        _to_out(
            event,
            registered=event.id in registered,
            count=counts.get(event.id, 0),
            reveal_links=event.id in registered,
        )
        for event in events
    ]


@router.get("/week")
async def week_overview(
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Data for the day-strip at the top of zoom.html."""
    from datetime import timedelta

    now = utcnow()
    start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=7)

    events = (
        await session.execute(
            select(models.Event)
            .where(
                models.Event.is_published.is_(True),
                models.Event.starts_at >= start,
                models.Event.starts_at < end,
            )
            .order_by(models.Event.starts_at)
        )
    ).scalars().all()

    registered = await _registered_ids(session, user.id)
    by_day: dict[str, int] = {}
    for event in events:
        key = event.starts_at.date().isoformat()
        by_day[key] = by_day.get(key, 0) + 1

    return {
        "week_start": start.date().isoformat(),
        "today": now.date().isoformat(),
        "counts": by_day,
        "registered_today": sum(
            1
            for event in events
            if event.starts_at.date() == now.date() and event.id in registered
        ),
    }


@router.get("/registrations", response_model=list[schemas.EventOut])
async def my_registrations(
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[schemas.EventOut]:
    events = (
        await session.execute(
            select(models.Event)
            .join(
                models.EventRegistration,
                models.EventRegistration.event_id == models.Event.id,
            )
            .where(models.EventRegistration.user_id == user.id)
            .order_by(models.Event.starts_at.desc())
        )
    ).scalars().all()
    counts = await _counts(session, [event.id for event in events])
    return [
        _to_out(event, registered=True, count=counts.get(event.id, 0), reveal_links=True)
        for event in events
    ]


@router.get("/{slug}", response_model=schemas.EventOut)
async def get_event(
    slug: str,
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> schemas.EventOut:
    event = await session.scalar(
        select(models.Event).where(
            (models.Event.slug == slug) | (models.Event.id == slug)
        )
    )
    if event is None or not event.is_published:
        raise HTTPException(status_code=404, detail="Tadbir topilmadi.")
    registered = await _registered_ids(session, user.id)
    counts = await _counts(session, [event.id])
    return _to_out(
        event,
        registered=event.id in registered,
        count=counts.get(event.id, 0),
        reveal_links=event.id in registered,
    )


@router.post("/{slug}/register", response_model=schemas.EventRegistrationOut)
async def register_for_event(
    slug: str,
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> schemas.EventRegistrationOut:
    event = await session.scalar(
        select(models.Event).where(
            (models.Event.slug == slug) | (models.Event.id == slug)
        )
    )
    if event is None or not event.is_published:
        raise HTTPException(status_code=404, detail="Tadbir topilmadi.")
    if event.starts_at < utcnow():
        raise HTTPException(status_code=409, detail="Bu tadbir allaqachon o'tkazilgan.")

    existing = await session.scalar(
        select(models.EventRegistration).where(
            models.EventRegistration.event_id == event.id,
            models.EventRegistration.user_id == user.id,
        )
    )
    if existing is None:
        count = await session.scalar(
            select(func.count(models.EventRegistration.id)).where(
                models.EventRegistration.event_id == event.id
            )
        )
        if event.seats and int(count or 0) >= event.seats:
            raise HTTPException(status_code=409, detail="Tadbirda joy qolmagan.")
        session.add(models.EventRegistration(event_id=event.id, user_id=user.id))
        await services.notify(
            session,
            user.id,
            kind="event",
            title=f"«{event.title}» tadbiriga yozildingiz",
            body=event.description,
            link="zoom.html",
            cta_label="Tadbirni ko'rish",
            icon="📅",
        )
        await session.commit()

    total = await session.scalar(
        select(func.count(models.EventRegistration.id)).where(
            models.EventRegistration.event_id == event.id
        )
    )
    return schemas.EventRegistrationOut(
        event_id=event.id, status="registered", registered_count=int(total or 0)
    )


@router.delete("/{slug}/register", response_model=schemas.Message)
async def unregister_from_event(
    slug: str,
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> schemas.Message:
    event = await session.scalar(
        select(models.Event).where(
            (models.Event.slug == slug) | (models.Event.id == slug)
        )
    )
    if event is None:
        raise HTTPException(status_code=404, detail="Tadbir topilmadi.")
    registration = await session.scalar(
        select(models.EventRegistration).where(
            models.EventRegistration.event_id == event.id,
            models.EventRegistration.user_id == user.id,
        )
    )
    if registration is None:
        raise HTTPException(status_code=404, detail="Siz bu tadbirga yozilmagansiz.")
    await session.delete(registration)
    await session.commit()
    return schemas.Message(detail="Ro'yxatdan chiqdingiz.")


@router.post("", response_model=schemas.EventOut, dependencies=[Depends(require_staff)])
async def create_event(
    payload: dict,
    session: AsyncSession = Depends(get_session),
    user: models.User = Depends(get_current_user),
) -> schemas.EventOut:
    """Minimal staff-side event creation (teacher/admin)."""
    required = {"title", "starts_at"}
    missing = required - set(payload)
    if missing:
        raise HTTPException(status_code=422, detail=f"Yetishmayotgan maydonlar: {', '.join(sorted(missing))}")

    from datetime import datetime

    from ..utils import new_id, normalize_level

    try:
        starts_at = datetime.fromisoformat(str(payload["starts_at"]).replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="starts_at ISO formatida bo'lishi kerak.") from exc
    if starts_at.tzinfo is None:
        starts_at = starts_at.replace(tzinfo=utcnow().tzinfo)

    slug = str(payload.get("slug") or f"event-{new_id()[:8]}")
    event = models.Event(
        slug=slug,
        title=str(payload["title"])[:200],
        description=payload.get("description"),
        host_name=payload.get("host_name") or user.display_name,
        host_avatar_url=payload.get("host_avatar_url"),
        level=normalize_level(payload.get("level")),
        kind=str(payload.get("kind", "lesson")),
        starts_at=starts_at,
        duration_minutes=int(payload.get("duration_minutes", 60)),
        join_url=payload.get("join_url"),
        meeting_id=payload.get("meeting_id"),
        seats=int(payload.get("seats", 100)),
        color=payload.get("color"),
        emoji=payload.get("emoji"),
    )
    session.add(event)
    await session.commit()
    await session.refresh(event)
    return _to_out(event, registered=False, count=0, reveal_links=True)
