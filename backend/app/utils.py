"""Shared helpers: id generation, timestamps, constant vocabularies."""

from __future__ import annotations

import secrets
import string
import uuid
from datetime import date, datetime, timedelta, timezone


def utcnow() -> datetime:
    """Timezone-aware UTC now (safe for both SQLite and Postgres)."""
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid.uuid4())


def random_token(length: int = 48) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def today_utc() -> date:
    return utcnow().date()


def days_ago(days: int) -> datetime:
    return utcnow() - timedelta(days=days)


# --------------------------------------------------------------------- enums
# Kept as plain string constants so the schema stays portable across databases.


class UserRole:
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"
    ALL = (STUDENT, TEACHER, ADMIN)


class LessonKind:
    VIDEO = "video"
    READING = "reading"
    QUIZ = "quiz"
    SPEAKING = "speaking"
    WRITING = "writing"
    ALL = (VIDEO, READING, QUIZ, SPEAKING, WRITING)


class ProgressStatus:
    LOCKED = "locked"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ALL = (LOCKED, IN_PROGRESS, COMPLETED)


class VocabStatus:
    NEW = "new"
    LEARNING = "learning"
    MASTERED = "mastered"
    ALL = (NEW, LEARNING, MASTERED)


class BattleStatus:
    WAITING = "waiting"
    ACTIVE = "active"
    FINISHED = "finished"
    CANCELLED = "cancelled"
    ALL = (WAITING, ACTIVE, FINISHED, CANCELLED)


class BattleMode:
    AI = "ai"
    DUEL = "duel"
    GROUP = "group"
    ALL = (AI, DUEL, GROUP)


class ConversationKind:
    DIRECT = "direct"
    GROUP = "group"
    SUPPORT = "support"
    BOT = "bot"
    ALL = (DIRECT, GROUP, SUPPORT, BOT)


class NotificationKind:
    SYSTEM = "system"
    LESSON = "lesson"
    CHAT = "chat"
    BATTLE = "battle"
    EVENT = "event"
    ACHIEVEMENT = "achievement"
    PROMO = "promo"
    ALL = (SYSTEM, LESSON, CHAT, BATTLE, EVENT, ACHIEVEMENT, PROMO)


SKILLS = ("vocabulary", "writing", "reading", "listening", "grammar")

CEFR_LEVELS = (
    "starter",
    "beginner",
    "elementary",
    "pre-intermediate",
    "intermediate",
    "upper-intermediate",
    "advanced",
)

LEVEL_TITLES = {
    "starter": "Starter",
    "beginner": "Beginner",
    "elementary": "Elementary",
    "pre-intermediate": "Pre-Intermediate",
    "intermediate": "Intermediate",
    "upper-intermediate": "Upper-Intermediate",
    "advanced": "Advanced",
}


def normalize_level(value: str | None, default: str = "starter") -> str:
    if not value:
        return default
    value = value.strip().lower().replace("_", "-")
    return value if value in CEFR_LEVELS else default
