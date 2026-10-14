"""Library: books, podcasts, games and CEFR levels."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models, schemas, services
from ..database import get_session
from ..deps import get_current_user
from ..utils import LEVEL_TITLES, normalize_level

router = APIRouter(tags=["library"])

#: Points required to unlock each CEFR band (mirrors level.html copy).
LEVEL_THRESHOLDS = {
    "starter": 0,
    "beginner": 500,
    "elementary": 1500,
    "pre-intermediate": 3000,
    "intermediate": 5000,
    "upper-intermediate": 8000,
    "advanced": 12000,
}

LEVEL_DESCRIPTIONS = {
    "starter": "Alifbo, tovushlar va eng kerakli so'zlar.",
    "beginner": "Oddiy suhbatlar, hozirgi zamon, kundalik so'zlar.",
    "elementary": "O'tgan zamon, savol-javob, qisqa matnlar.",
    "pre-intermediate": "Murakkab gaplar, tinglab tushunish, esse.",
    "intermediate": "Erkin suhbat, idiomalar, akademik o'qish.",
    "upper-intermediate": "Nuanslar, IELTS 6.5+ ko'nikmalari.",
    "advanced": "Akademik va professional daraja.",
}


# ===========================================================================
# progress helper (shared with the levels endpoint)
# ===========================================================================
async def _completed_count(session: AsyncSession, user_id: str) -> int:
    return int(
        await session.scalar(
            select(func.count(models.LessonProgress.id)).where(
                models.LessonProgress.user_id == user_id,
                models.LessonProgress.status == "completed",
            )
        )
        or 0
    )


# ===========================================================================
# books
# ===========================================================================
@router.get("/books", response_model=list[schemas.BookOut])
async def list_books(
    level: str | None = None,
    category: str | None = None,
    q: str | None = Query(default=None, max_length=80),
    limit: int = Query(default=50, ge=1, le=200),
    _: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[schemas.BookOut]:
    query = select(models.Book)
    if level:
        query = query.where(models.Book.level == level)
    if category:
        query = query.where(models.Book.category == category)
    if q:
        query = query.where(models.Book.title.ilike(f"%{q.strip()}%"))
    rows = (
        await session.execute(query.order_by(models.Book.order_index).limit(limit))
    ).scalars().all()
    return [schemas.BookOut.model_validate(row) for row in rows]


@router.get("/books/{slug}", response_model=schemas.BookOut)
async def get_book(
    slug: str,
    _: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> schemas.BookOut:
    book = await session.scalar(
        select(models.Book).where((models.Book.slug == slug) | (models.Book.id == slug))
    )
    if book is None:
        raise HTTPException(status_code=404, detail="Kitob topilmadi.")
    return schemas.BookOut.model_validate(book)


# ===========================================================================
# podcasts
# ===========================================================================
@router.get("/podcasts", response_model=list[schemas.PodcastOut])
async def list_podcasts(
    level: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    _: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[schemas.PodcastOut]:
    query = select(models.Podcast)
    if level:
        query = query.where(models.Podcast.level == level)
    rows = (
        await session.execute(
            query.order_by(models.Podcast.episode_number.desc()).limit(limit)
        )
    ).scalars().all()
    return [schemas.PodcastOut.model_validate(row) for row in rows]


@router.get("/podcasts/{slug}", response_model=schemas.PodcastOut)
async def get_podcast(
    slug: str,
    _: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> schemas.PodcastOut:
    podcast = await session.scalar(
        select(models.Podcast).where(
            (models.Podcast.slug == slug) | (models.Podcast.id == slug)
        )
    )
    if podcast is None:
        raise HTTPException(status_code=404, detail="Podkast topilmadi.")
    return schemas.PodcastOut.model_validate(podcast)


# ===========================================================================
# games
# ===========================================================================
@router.get("/games", response_model=list[schemas.GameOut])
async def list_games(
    _: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[schemas.GameOut]:
    rows = (
        await session.execute(
            select(models.Game)
            .where(models.Game.is_active.is_(True))
            .order_by(models.Game.order_index)
        )
    ).scalars().all()
    return [schemas.GameOut.model_validate(row) for row in rows]


@router.get("/games/{slug}", response_model=schemas.GameOut)
async def get_game(
    slug: str,
    _: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> schemas.GameOut:
    game = await _game_by_slug(session, slug)
    return schemas.GameOut.model_validate(game)


@router.post("/games/{slug}/score", response_model=schemas.GameScoreOut)
async def submit_game_score(
    slug: str,
    payload: schemas.GameScoreCreate,
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> schemas.GameScoreOut:
    game = await _game_by_slug(session, slug)
    session.add(
        models.GameScore(
            user_id=user.id,
            game_id=game.id,
            score=payload.score,
            correct_count=payload.correct_count,
            total=payload.total,
        )
    )

    # Points are capped so a single game cannot be farmed for the leaderboard.
    config = game.config or {}
    cap = int(config.get("max_points_per_session", 200))
    points = min(payload.score, cap)
    if points:
        await services.award_points(session, user, points, minutes=3)
    await services.bump_skill(session, user.id, "vocabulary", points / 50)
    await session.commit()

    best = await session.scalar(
        select(func.coalesce(func.max(models.GameScore.score), 0)).where(
            models.GameScore.user_id == user.id, models.GameScore.game_id == game.id
        )
    )
    return schemas.GameScoreOut(
        game_id=game.id,
        score=payload.score,
        points_earned=points,
        best_score=int(best or 0),
    )


@router.get("/games/{slug}/leaderboard", response_model=list[dict])
async def game_leaderboard(
    slug: str,
    limit: int = Query(default=10, ge=1, le=100),
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    game = await _game_by_slug(session, slug)
    rows = (
        await session.execute(
            select(
                models.User.id,
                models.User.full_name,
                models.User.avatar_url,
                func.max(models.GameScore.score).label("best"),
            )
            .join(models.GameScore, models.GameScore.user_id == models.User.id)
            .where(models.GameScore.game_id == game.id)
            .group_by(models.User.id, models.User.full_name, models.User.avatar_url)
            .order_by(func.max(models.GameScore.score).desc())
            .limit(limit)
        )
    ).all()
    return [
        {
            "rank": index,
            "user_id": row.id,
            "name": row.full_name,
            "avatar_url": row.avatar_url,
            "score": int(row.best or 0),
            "is_me": row.id == user.id,
        }
        for index, row in enumerate(rows, start=1)
    ]


async def _game_by_slug(session: AsyncSession, slug: str) -> models.Game:
    game = await session.scalar(
        select(models.Game).where((models.Game.slug == slug) | (models.Game.id == slug))
    )
    if game is None or not game.is_active:
        raise HTTPException(status_code=404, detail="O'yin topilmadi.")
    return game


# ===========================================================================
# levels
# ===========================================================================
@router.get("/levels", response_model=list[schemas.LevelOut])
async def list_levels(
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[schemas.LevelOut]:
    order = list(LEVEL_THRESHOLDS)
    lessons_per_level: dict[str, int] = {}
    rows = (
        await session.execute(
            select(models.Course.level, func.count(models.Lesson.id))
            .join(models.Unit, models.Unit.course_id == models.Course.id)
            .join(models.Lesson, models.Lesson.unit_id == models.Unit.id)
            .group_by(models.Course.level)
        )
    ).all()
    for level, count in rows:
        lessons_per_level[level] = int(count)

    current_index = order.index(normalize_level(user.level))
    result: list[schemas.LevelOut] = []
    for index, level in enumerate(order):
        threshold = LEVEL_THRESHOLDS[level]
        unlocked = index <= current_index or user.points >= threshold
        if unlocked:
            # ``level_progress_percent`` walks the same threshold table, so the
            # next band's ceiling does not need to be computed here.
            progress = (
                100.0
                if index < current_index
                else services.level_progress_percent(user.points, level)
            )
        else:
            progress = 0.0
        result.append(
            schemas.LevelOut(
                slug=level,
                title=LEVEL_TITLES.get(level, level.title()),
                order=index + 1,
                points_required=threshold,
                unlocked=unlocked,
                progress_percent=round(progress, 1),
                lessons=lessons_per_level.get(level, 0),
                description=LEVEL_DESCRIPTIONS.get(level),
            )
        )
    return result


@router.get("/library/summary")
async def library_summary(
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Counts used by the «Resurslar» tab of the student app."""
    books = await session.scalar(select(func.count(models.Book.id)))
    podcasts = await session.scalar(select(func.count(models.Podcast.id)))
    games = await session.scalar(
        select(func.count(models.Game.id)).where(models.Game.is_active.is_(True))
    )

    from datetime import timedelta

    from ..utils import utcnow

    events = await session.scalar(
        select(func.count(models.Event.id)).where(
            models.Event.is_published.is_(True),
            models.Event.starts_at >= utcnow(),
            models.Event.starts_at <= utcnow() + timedelta(days=7),
        )
    )
    return {
        "books": int(books or 0),
        "podcasts": int(podcasts or 0),
        "games": int(games or 0),
        "upcoming_events": int(events or 0),
        "lessons_completed": await _completed_count(session, user.id),
        "points": user.points,
        "level": user.level,
        "level_title": LEVEL_TITLES.get(user.level, user.level.title()),
    }
