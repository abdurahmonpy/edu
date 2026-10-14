"""Reusable business logic shared by the routers."""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from . import models, schemas
from .utils import LEVEL_TITLES, SKILLS, normalize_level, today_utc, utcnow


# ===========================================================================
# Users
# ===========================================================================
def user_public(user: models.User) -> schemas.UserPublic:
    data = schemas.UserPublic.model_validate(user)
    data.level_title = LEVEL_TITLES.get(user.level, user.level.title())
    return data


async def get_rank(session: AsyncSession, user: models.User) -> int | None:
    """1-based global rank by points (None when the user has no points yet)."""
    if user.points <= 0:
        return None
    higher = await session.scalar(
        select(func.count(models.User.id)).where(
            models.User.points > user.points,
            models.User.is_active.is_(True),
        )
    )
    return int(higher or 0) + 1


async def battle_stats(session: AsyncSession, user_id: str) -> schemas.BattleStats:
    played = await session.scalar(
        select(func.count(models.Battle.id)).where(
            models.Battle.status == "finished",
            (models.Battle.host_id == user_id) | (models.Battle.guest_id == user_id),
        )
    )
    won = await session.scalar(
        select(func.count(models.Battle.id)).where(
            models.Battle.status == "finished", models.Battle.winner_id == user_id
        )
    )
    drawn = await session.scalar(
        select(func.count(models.Battle.id)).where(
            models.Battle.status == "finished",
            models.Battle.winner_id.is_(None),
            (models.Battle.host_id == user_id) | (models.Battle.guest_id == user_id),
        )
    )
    points = await session.scalar(
        select(func.coalesce(func.sum(models.Battle.host_score), 0)).where(
            models.Battle.host_id == user_id, models.Battle.status == "finished"
        )
    )
    played = int(played or 0)
    won = int(won or 0)
    drawn = int(drawn or 0)
    return schemas.BattleStats(
        played=played,
        won=won,
        lost=max(played - won - drawn, 0),
        drawn=drawn,
        total_points=int(points or 0),
    )


async def collect_stats(session: AsyncSession, user: models.User) -> schemas.UserStats:
    lessons_completed = await session.scalar(
        select(func.count(models.LessonProgress.id)).where(
            models.LessonProgress.user_id == user.id,
            models.LessonProgress.status == "completed",
        )
    )
    words_learned = await session.scalar(
        select(func.count(models.VocabularyItem.id)).where(
            models.VocabularyItem.user_id == user.id
        )
    )
    week_start = today_utc() - timedelta(days=6)
    minutes_week = await session.scalar(
        select(func.coalesce(func.sum(models.DailyActivity.minutes), 0)).where(
            models.DailyActivity.user_id == user.id,
            models.DailyActivity.day >= week_start,
        )
    )

    rows = (
        await session.execute(
            select(models.SkillProgress).where(models.SkillProgress.user_id == user.id)
        )
    ).scalars().all()
    by_skill = {row.skill: row.percent for row in rows}
    skills = [
        schemas.SkillStat(skill=skill, percent=round(float(by_skill.get(skill, 0.0)), 1))
        for skill in SKILLS
    ]

    battles = await battle_stats(session, user.id)
    rank = await get_rank(session, user)

    return schemas.UserStats(
        points=user.points,
        xp=user.xp,
        level=user.level,
        level_title=LEVEL_TITLES.get(user.level, user.level.title()),
        streak_days=user.streak_days,
        longest_streak=user.longest_streak,
        rank=rank,
        lessons_completed=int(lessons_completed or 0),
        words_learned=int(words_learned or 0),
        minutes_this_week=int(minutes_week or 0),
        skills=skills,
        battles_played=battles.played,
        battles_won=battles.won,
        battles_lost=battles.lost,
        coins=user.points,
    )


# ===========================================================================
# Gamification
# ===========================================================================
async def award_points(
    session: AsyncSession,
    user: models.User,
    points: int,
    *,
    minutes: int = 0,
    lessons_completed: int = 0,
    words_reviewed: int = 0,
) -> None:
    """Add points/xp, bump today's activity row and keep the streak fresh."""
    if points:
        user.points = max(user.points + points, 0)
        user.xp = max(user.xp + points, 0)
    touch_streak(user)
    await record_activity(
        session,
        user,
        minutes=minutes,
        points=points,
        lessons_completed=lessons_completed,
        words_reviewed=words_reviewed,
    )
    await maybe_promote_level(session, user)


def touch_streak(user: models.User) -> None:
    today = today_utc()
    if user.last_active_on == today:
        return
    if user.last_active_on == today - timedelta(days=1):
        user.streak_days += 1
    else:
        user.streak_days = 1
    user.last_active_on = today
    user.longest_streak = max(user.longest_streak, user.streak_days)


async def record_activity(
    session: AsyncSession,
    user: models.User,
    *,
    minutes: int = 0,
    points: int = 0,
    lessons_completed: int = 0,
    words_reviewed: int = 0,
) -> None:
    today = today_utc()
    row = await session.scalar(
        select(models.DailyActivity).where(
            models.DailyActivity.user_id == user.id, models.DailyActivity.day == today
        )
    )
    if row is None:
        # Values are set explicitly: Python-side column defaults are only applied
        # at flush time, and this row is mutated before it is flushed.
        row = models.DailyActivity(
            user_id=user.id,
            day=today,
            minutes=0,
            points=0,
            lessons_completed=0,
            words_reviewed=0,
        )
        session.add(row)
    row.minutes += max(minutes, 0)
    row.points += max(points, 0)
    row.lessons_completed += max(lessons_completed, 0)
    row.words_reviewed += max(words_reviewed, 0)


async def set_skill(session: AsyncSession, user_id: str, skill: str, percent: float) -> None:
    if skill not in SKILLS:
        return
    percent = max(0.0, min(100.0, percent))
    row = await session.scalar(
        select(models.SkillProgress).where(
            models.SkillProgress.user_id == user_id, models.SkillProgress.skill == skill
        )
    )
    if row is None:
        session.add(models.SkillProgress(user_id=user_id, skill=skill, percent=percent))
    else:
        row.percent = round(percent, 1)


async def bump_skill(session: AsyncSession, user_id: str, skill: str, delta: float) -> None:
    row = await session.scalar(
        select(models.SkillProgress).where(
            models.SkillProgress.user_id == user_id, models.SkillProgress.skill == skill
        )
    )
    current = row.percent if row else 0.0
    await set_skill(session, user_id, skill, current + delta)


LEVEL_POINT_THRESHOLDS = {
    "starter": 0,
    "beginner": 500,
    "elementary": 1500,
    "pre-intermediate": 3000,
    "intermediate": 5000,
    "upper-intermediate": 8000,
    "advanced": 12000,
}


def level_progress_percent(points: int, level: str) -> float:
    level = normalize_level(level)
    order = list(LEVEL_POINT_THRESHOLDS)
    index = order.index(level)
    floor = LEVEL_POINT_THRESHOLDS[level]
    if index + 1 >= len(order):
        return 100.0
    ceiling = LEVEL_POINT_THRESHOLDS[order[index + 1]]
    if ceiling <= floor:
        return 100.0
    return round(max(0.0, min(1.0, (points - floor) / (ceiling - floor))) * 100, 1)


async def maybe_promote_level(session: AsyncSession, user: models.User) -> str | None:
    """Move the user up a CEFR band once they pass the points threshold."""
    order = list(LEVEL_POINT_THRESHOLDS)
    current = normalize_level(user.level)
    index = order.index(current)
    while index + 1 < len(order):
        nxt = order[index + 1]
        if user.points >= LEVEL_POINT_THRESHOLDS[nxt]:
            index += 1
        else:
            break
    if order[index] != user.level:
        user.level = order[index]
        await notify(
            session,
            user.id,
            kind="achievement",
            title=f"Yangi daraja: {LEVEL_TITLES.get(user.level, user.level)}",
            body="Tabriklaymiz! Siz keyingi darajaga ko'tarildingiz.",
            icon="🎉",
            link="app.html#darslar",
        )
        return user.level
    return None


# ===========================================================================
# Notifications
# ===========================================================================
async def notify(
    session: AsyncSession,
    user_id: str,
    *,
    title: str,
    body: str | None = None,
    kind: str = "system",
    banner: str | None = None,
    link: str | None = None,
    cta_label: str | None = None,
    icon: str | None = None,
) -> models.Notification:
    notification = models.Notification(
        user_id=user_id,
        kind=kind,
        title=title,
        body=body,
        banner=banner,
        link=link,
        cta_label=cta_label,
        icon=icon,
    )
    session.add(notification)
    await session.flush()
    return notification


# ===========================================================================
# Vocabulary spaced repetition (SM-2 flavoured)
# ===========================================================================
def apply_review(item: models.VocabularyItem, quality: int, user: models.User | None = None) -> None:
    quality = max(0, min(5, quality))
    item.review_count += 1
    item.last_reviewed_at = utcnow()

    if quality < 3:
        # Lapse: back to the beginning of the queue.
        item.interval_days = 1
        item.ease = max(1.3, item.ease - 0.2)
        item.status = "learning"
    else:
        if quality == 5:
            item.correct_count += 1
        item.ease = min(3.2, max(1.3, item.ease + (0.1 - (5 - quality) * 0.08)))
        if item.interval_days <= 0:
            item.interval_days = 1
        elif item.interval_days == 1:
            item.interval_days = 3
        else:
            item.interval_days = int(round(item.interval_days * item.ease))
        item.interval_days = min(item.interval_days, 365)
        if item.interval_days >= 21 and item.review_count >= 4:
            item.status = "mastered"
        else:
            item.status = "learning"

    item.next_review_at = utcnow() + timedelta(days=item.interval_days)


# ===========================================================================
# Misc helpers
# ===========================================================================
def activity_range(days: int) -> list[date]:
    today = today_utc()
    return [today - timedelta(days=offset) for offset in range(days - 1, -1, -1)]
