"""Leaderboard across global / weekly scopes and CEFR levels."""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models, schemas
from ..database import get_session
from ..deps import get_current_user
from ..utils import LEVEL_TITLES, today_utc

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


@router.get("", response_model=schemas.LeaderboardOut)
async def leaderboard(
    period: str = Query(default="all", pattern="^(all|week)$"),
    level: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> schemas.LeaderboardOut:
    if period == "week":
        week_start = today_utc() - timedelta(days=6)
        totals = (
            select(
                models.DailyActivity.user_id.label("user_id"),
                func.sum(models.DailyActivity.points).label("points"),
            )
            .where(models.DailyActivity.day >= week_start)
            .group_by(models.DailyActivity.user_id)
            .subquery()
        )
        query = (
            select(models.User, func.coalesce(totals.c.points, 0).label("points"))
            .join(totals, totals.c.user_id == models.User.id)
            .where(models.User.is_active.is_(True))
        )
        if level:
            query = query.where(models.User.level == level)
        query = query.order_by(func.coalesce(totals.c.points, 0).desc()).limit(limit)
        rows = (await session.execute(query)).all()
    else:
        query = select(models.User, models.User.points.label("points")).where(
            models.User.is_active.is_(True)
        )
        if level:
            query = query.where(models.User.level == level)
        query = query.order_by(models.User.points.desc(), models.User.created_at.asc()).limit(limit)
        rows = (await session.execute(query)).all()

    entries: list[schemas.LeaderboardEntry] = []
    me_entry: schemas.LeaderboardEntry | None = None
    for index, (row_user, points) in enumerate(rows, start=1):
        entry = schemas.LeaderboardEntry(
            rank=index,
            user_id=row_user.id,
            name=row_user.display_name,
            avatar_url=row_user.avatar_url,
            avatar_emoji=row_user.avatar_emoji,
            points=int(points or 0),
            level=row_user.level,
            level_title=LEVEL_TITLES.get(row_user.level, row_user.level.title()),
            is_me=row_user.id == user.id,
            streak_days=row_user.streak_days,
        )
        entries.append(entry)
        if entry.is_me:
            me_entry = entry

    if me_entry is None:
        my_points = user.points
        if period == "week":
            week_start = today_utc() - timedelta(days=6)
            my_points = int(
                await session.scalar(
                    select(func.coalesce(func.sum(models.DailyActivity.points), 0)).where(
                        models.DailyActivity.user_id == user.id,
                        models.DailyActivity.day >= week_start,
                    )
                )
                or 0
            )
        higher = await session.scalar(
            select(func.count(models.User.id)).where(
                models.User.is_active.is_(True),
                models.User.points > (my_points if period == "week" else user.points),
            )
        )
        me_entry = schemas.LeaderboardEntry(
            rank=int(higher or 0) + 1,
            user_id=user.id,
            name=user.display_name,
            avatar_url=user.avatar_url,
            avatar_emoji=user.avatar_emoji,
            points=my_points,
            level=user.level,
            level_title=LEVEL_TITLES.get(user.level, user.level.title()),
            is_me=True,
            streak_days=user.streak_days,
        )

    return schemas.LeaderboardOut(
        scope="global", period=period, level=level, entries=entries, me=me_entry
    )
