"""User profile, statistics and achievements."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models, schemas, services
from ..database import get_session
from ..deps import get_current_user, require_admin
from ..utils import today_utc

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me/stats", response_model=schemas.UserStats)
async def my_stats(
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> schemas.UserStats:
    return await services.collect_stats(session, user)


@router.get("/me/activity", response_model=list[schemas.ActivityDay])
async def my_activity(
    days: int = Query(default=7, ge=1, le=90),
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[schemas.ActivityDay]:
    wanted = services.activity_range(days)
    rows = (
        await session.execute(
            select(models.DailyActivity).where(
                models.DailyActivity.user_id == user.id,
                models.DailyActivity.day >= wanted[0],
            )
        )
    ).scalars().all()
    by_day = {row.day: row for row in rows}
    result: list[schemas.ActivityDay] = []
    for day in wanted:
        row = by_day.get(day)
        result.append(
            schemas.ActivityDay(
                day=day,
                minutes=row.minutes if row else 0,
                points=row.points if row else 0,
                lessons_completed=row.lessons_completed if row else 0,
                words_reviewed=row.words_reviewed if row else 0,
            )
        )
    return result


@router.get("/me/achievements", response_model=list[schemas.UserAchievementOut])
async def my_achievements(
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[schemas.UserAchievementOut]:
    achievements = (
        await session.execute(select(models.Achievement).order_by(models.Achievement.threshold))
    ).scalars().all()
    earned = (
        await session.execute(
            select(models.UserAchievement).where(models.UserAchievement.user_id == user.id)
        )
    ).scalars().all()
    earned_at = {row.achievement_id: row.earned_at for row in earned}

    return [
        schemas.UserAchievementOut(
            **schemas.AchievementOut.model_validate(item).model_dump(),
            earned=item.id in earned_at,
            earned_at=earned_at.get(item.id),
        )
        for item in achievements
    ]


@router.get("/me/streak")
async def my_streak(
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    today = today_utc()
    active_today = user.last_active_on == today
    return {
        "streak_days": user.streak_days,
        "longest_streak": user.longest_streak,
        "last_active_on": user.last_active_on,
        "active_today": active_today,
        "daily_goal_minutes": user.daily_goal_minutes,
    }


@router.get("/{user_id}", response_model=schemas.UserPublic)
async def public_profile(
    user_id: str,
    _: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> schemas.UserPublic:
    target = await session.get(models.User, user_id)
    if target is None or not target.is_active:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi.")
    return services.user_public(target)


@router.get("", response_model=schemas.Page[schemas.UserPublic], dependencies=[Depends(require_admin)])
async def list_users(
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> schemas.Page[schemas.UserPublic]:
    from sqlalchemy import func

    total = await session.scalar(select(func.count(models.User.id))) or 0
    rows = (
        await session.execute(
            select(models.User)
            .order_by(models.User.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    ).scalars().all()
    return schemas.Page(
        items=[services.user_public(row) for row in rows],
        total=int(total),
        limit=limit,
        offset=offset,
    )
