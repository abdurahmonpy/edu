"""Idempotent database seeding.

Every catalogue row is keyed by a natural slug, so calling ``seed_all`` on each
boot only inserts what is missing and never duplicates or overwrites data that
real users have produced.
"""

from __future__ import annotations

import copy
import logging
from datetime import datetime, time, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from . import models, seed_data
from .config import settings
from .database import SessionLocal
from .security import hash_password
from .utils import SKILLS, normalize_level, random_token, utcnow

logger = logging.getLogger("englify.seed")


# --------------------------------------------------------------------- helpers
async def _exists(session: AsyncSession, model, **filters) -> bool:
    found = await session.scalar(select(func.count()).select_from(model).filter_by(**filters))
    return bool(found)


def _aware(day_offset: int, hour: int, minute: int = 0) -> datetime:
    base = utcnow() + timedelta(days=day_offset)
    return datetime.combine(base.date(), time(hour=hour, minute=minute), tzinfo=timezone.utc)


def _parse_clock(value: object, default_hour: int = 18) -> tuple[int, int]:
    """Accepts ``18``, ``"18"`` or ``"18:00"`` and returns ``(hour, minute)``."""
    if value is None:
        return default_hour, 0
    if isinstance(value, int):
        return value, 0
    text = str(value).strip().replace(".", ":")
    if ":" in text:
        hours, _, minutes = text.partition(":")
        try:
            return int(hours), int(minutes or 0)
        except ValueError:
            return default_hour, 0
    try:
        return int(text), 0
    except ValueError:
        return default_hour, 0


# ===========================================================================
# catalogs
# ===========================================================================
async def _seed_achievements(session: AsyncSession) -> None:
    for entry in seed_data.ACHIEVEMENTS:
        if await _exists(session, models.Achievement, slug=entry["slug"]):
            continue
        session.add(models.Achievement(**entry))


async def _seed_books(session: AsyncSession) -> None:
    for entry in seed_data.BOOKS:
        if await _exists(session, models.Book, slug=entry["slug"]):
            continue
        session.add(models.Book(**entry))


async def _seed_podcasts(session: AsyncSession) -> None:
    for entry in seed_data.PODCASTS:
        if await _exists(session, models.Podcast, slug=entry["slug"]):
            continue
        session.add(models.Podcast(**entry))


async def _seed_games(session: AsyncSession) -> None:
    for entry in seed_data.GAMES:
        if await _exists(session, models.Game, slug=entry["slug"]):
            continue
        session.add(models.Game(**entry))


async def _seed_battle_questions(session: AsyncSession) -> None:
    existing = await session.scalar(
        select(func.count()).select_from(models.BattleQuestionBank)
    )
    if existing:
        return
    for entry in seed_data.BATTLE_QUESTIONS:
        session.add(
            models.BattleQuestionBank(
                topic=entry["topic"],
                level=normalize_level(entry.get("level")),
                prompt=entry["prompt"],
                options=list(entry["options"]),
                correct_index=int(entry["correct_index"]),
                explanation=entry.get("explanation"),
                points=int(entry.get("points", 20)),
            )
        )


async def _seed_courses(session: AsyncSession) -> None:
    for entry in seed_data.COURSES:
        if await _exists(session, models.Course, slug=entry["slug"]):
            continue

        # deepcopy: seeding must never mutate the shared seed_data module.
        course_data = copy.deepcopy(entry)
        units = course_data.pop("units", [])
        course = models.Course(**course_data)
        session.add(course)
        await session.flush()

        for unit_data in units:
            lessons = unit_data.pop("lessons", [])
            unit = models.Unit(course_id=course.id, **unit_data)
            session.add(unit)
            await session.flush()

            for lesson_data in lessons:
                questions = lesson_data.pop("questions", [])
                lesson = models.Lesson(unit_id=unit.id, **lesson_data)
                session.add(lesson)
                await session.flush()

                for index, question in enumerate(questions):
                    session.add(
                        models.QuizQuestion(
                            lesson_id=lesson.id,
                            prompt=question["prompt"],
                            options=list(question["options"]),
                            correct_index=int(question["correct_index"]),
                            explanation=question.get("explanation"),
                            points=int(question.get("points", 10)),
                            order_index=index,
                        )
                    )
        logger.info("Seeded course %s", entry["slug"])


async def _seed_placement_test(session: AsyncSession) -> None:
    """Expose the level.html placement test as a real, graded lesson."""
    slug = "placement-test"
    if await _exists(session, models.Course, slug=slug):
        return

    course = models.Course(
        slug=slug,
        title="Darajani aniqlash testi",
        subtitle="3 savol — 1 daqiqa",
        description=(
            "Qaysi darajadan boshlashni bilmayapsizmi? Qisqa testni yechib, "
            "o'zingizga mos kursni tanlang."
        ),
        level="starter",
        emoji="🎯",
        color="#35F59A",
        order_index=99,
    )
    session.add(course)
    await session.flush()

    unit = models.Unit(
        course_id=course.id,
        slug="placement",
        code="Test",
        title="Placement test",
        description="A1 yoki A2 ekanini aniqlaymiz.",
        emoji="🎯",
        order_index=0,
    )
    session.add(unit)
    await session.flush()

    lesson = models.Lesson(
        unit_id=unit.id,
        slug="placement-quiz",
        title="Darajani aniqlash",
        description="3 ta savolga javob bering.",
        kind="quiz",
        duration_sec=60,
        xp_reward=20,
        order_index=0,
    )
    session.add(lesson)
    await session.flush()

    for index, question in enumerate(seed_data.PLACEMENT_QUESTIONS):
        session.add(
            models.QuizQuestion(
                lesson_id=lesson.id,
                prompt=question["prompt"],
                options=list(question["options"]),
                correct_index=int(question["correct_index"]),
                explanation=question.get("explanation"),
                order_index=index,
            )
        )


async def _seed_events(session: AsyncSession) -> None:
    for entry in seed_data.EVENTS:
        if await _exists(session, models.Event, slug=entry["slug"]):
            continue
        data = dict(entry)
        starts_in_days = int(data.pop("starts_in_days", 0))
        hour, minute = _parse_clock(data.pop("start_hour", 18))
        session.add(
            models.Event(starts_at=_aware(starts_in_days, hour, minute), **data)
        )


# ===========================================================================
# users
# ===========================================================================
async def _seed_demo_users(session: AsyncSession) -> dict[str, models.User]:
    """Create the leaderboard/demo accounts. Returns ``{email: User}``."""
    created: dict[str, models.User] = {}

    for entry in seed_data.DEMO_USERS:
        email = entry["email"].lower()
        user = await session.scalar(select(models.User).where(models.User.email == email))
        if user is None:
            user = models.User(
                email=email,
                full_name=entry["full_name"],
                password_hash=hash_password(entry["password"]),
                role=entry.get("role", "student"),
                level=normalize_level(entry.get("level")),
                points=int(entry.get("points", 0)),
                xp=int(entry.get("points", 0)),
                streak_days=int(entry.get("streak_days", 0)),
                longest_streak=int(entry.get("streak_days", 0)),
                avatar_emoji=entry.get("avatar_emoji"),
                is_verified=True,
                last_active_on=utcnow().date(),
            )
            session.add(user)
            await session.flush()

            # Skills scaled from the account's points so the app bars look real.
            base = min(92.0, 18.0 + user.points / 45.0)
            for offset, skill in enumerate(SKILLS):
                percent = round(max(4.0, min(98.0, base - offset * 6 + (offset % 2) * 4)), 1)
                session.add(
                    models.SkillProgress(user_id=user.id, skill=skill, percent=percent)
                )

            # Weekly activity so the "week" leaderboard has something to show.
            for days_back in range(7):
                day = (utcnow() - timedelta(days=days_back)).date()
                session.add(
                    models.DailyActivity(
                        user_id=user.id,
                        day=day,
                        minutes=15 + (days_back * 7) % 40,
                        points=max(int(user.points / 12) - days_back * 5, 0),
                        lessons_completed=(days_back + 1) % 3,
                        words_reviewed=(days_back * 4) % 15,
                    )
                )

        created[email] = user

    return created


async def _seed_student_content(
    session: AsyncSession, student: models.User
) -> None:
    """Notifications, chats and starter vocabulary for the demo student."""
    if not await _exists(session, models.Notification, user_id=student.id):
        for index, entry in enumerate(seed_data.NOTIFICATIONS):
            data = dict(entry)
            days_ago = int(data.pop("days_ago", index))
            session.add(
                models.Notification(
                    user_id=student.id,
                    is_read=index >= 2,
                    created_at=utcnow() - timedelta(days=days_ago, hours=3),
                    **data,
                )
            )

    # Vocabulary
    if not await _exists(session, models.VocabularyItem, user_id=student.id):
        for entry in seed_data.STARTING_VOCABULARY:
            session.add(
                models.VocabularyItem(
                    user_id=student.id,
                    next_review_at=utcnow(),
                    status="new",
                    **entry,
                )
            )

    # Chat conversations
    for index, entry in enumerate(seed_data.CHAT_SEED):
        data = dict(entry)
        messages = data.pop("messages", [])
        existing = await session.scalar(
            select(models.Conversation).where(
                models.Conversation.title == data["title"],
                models.Conversation.is_system.is_(True),
            )
        )
        if existing is not None:
            continue

        conversation = models.Conversation(is_system=True, **data)
        session.add(conversation)
        await session.flush()

        session.add(
            models.ConversationMember(
                conversation_id=conversation.id,
                user_id=student.id,
                role="member",
                last_read_at=utcnow() - timedelta(days=1),
            )
        )
        if conversation.kind in {"bot", "support"}:
            session.add(
                models.ConversationMember(
                    conversation_id=conversation.id,
                    bot_name=data.get("title", "Bot"),
                    role="bot",
                )
            )

        latest = None
        for message in messages:
            created_at = utcnow() - timedelta(days=int(message.get("days_ago", 0)), minutes=5)
            is_bot = message.get("from") == "bot"
            session.add(
                models.Message(
                    conversation_id=conversation.id,
                    sender_id=None if is_bot else student.id,
                    sender_name=message.get("sender_name") or data.get("title"),
                    body=message["body"],
                    created_at=created_at,
                )
            )
            latest = created_at
        conversation.last_message_at = latest or (utcnow() - timedelta(days=index + 1))


# ===========================================================================
# entrypoint
# ===========================================================================
async def seed_all() -> None:
    if not settings.seed_demo_data:
        return

    async with SessionLocal() as session:
        try:
            await _seed_achievements(session)
            await _seed_books(session)
            await _seed_podcasts(session)
            await _seed_games(session)
            await _seed_battle_questions(session)
            await _seed_courses(session)
            await _seed_placement_test(session)
            await _seed_events(session)

            users: dict[str, models.User] = {}
            if settings.seed_demo_accounts:
                users = await _seed_demo_users(session)
                await session.flush()

                student = users.get("abdurahmon@englify.uz") or next(iter(users.values()), None)
                if student is not None:
                    await _seed_student_content(session, student)

            await session.commit()
            logger.info(
                "Seed complete (demo accounts: %s).",
                len(users) if settings.seed_demo_accounts else "disabled",
            )
        except Exception:
            await session.rollback()
            logger.exception("Seeding failed; continuing with the existing data.")


async def reset_demo_passwords() -> None:
    """Utility used by ``scripts/reset_demo.py``."""
    async with SessionLocal() as session:
        for entry in seed_data.DEMO_USERS:
            user = await session.scalar(
                select(models.User).where(models.User.email == entry["email"].lower())
            )
            if user is not None:
                user.password_hash = hash_password(entry["password"])
                user.failed_logins = 0
                user.locked_until = None
        await session.commit()


def random_demo_password() -> str:
    return f"Egl-{random_token(10)}"
