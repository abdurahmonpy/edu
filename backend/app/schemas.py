"""Pydantic request/response schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

T = TypeVar("T")


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class Message(BaseModel):
    detail: str


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int

    @property
    def has_more(self) -> bool:
        return self.offset + len(self.items) < self.total


# ===========================================================================
# Auth
# ===========================================================================
class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)
    full_name: str = Field(min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=32)
    level: str | None = None

    @field_validator("full_name")
    @classmethod
    def _clean_name(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if len(cleaned) < 2:
            raise ValueError("Ism kamida 2 ta belgidan iborat bo'lishi kerak.")
        return cleaned

    @field_validator("phone")
    @classmethod
    def _clean_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = "".join(ch for ch in value if ch.isdigit() or ch == "+")
        return cleaned or None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str | None = None
    all_devices: bool = False


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=1, max_length=256)


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=1, max_length=256)


class UserPublic(ORMModel):
    id: str
    email: EmailStr
    full_name: str
    phone: str | None = None
    role: str
    avatar_url: str | None = None
    avatar_emoji: str | None = None
    bio: str | None = None
    level: str
    level_title: str | None = None
    points: int
    xp: int
    streak_days: int
    longest_streak: int
    daily_goal_minutes: int
    is_verified: bool
    created_at: datetime


class UserUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=32)
    avatar_url: str | None = Field(default=None, max_length=512)
    avatar_emoji: str | None = Field(default=None, max_length=8)
    bio: str | None = Field(default=None, max_length=1000)
    level: str | None = None
    daily_goal_minutes: int | None = Field(default=None, ge=5, le=600)


class AdminUserOut(UserPublic):
    is_active: bool
    failed_logins: int
    locked_until: datetime | None = None
    last_login_at: datetime | None = None


class AdminUserUpdate(BaseModel):
    role: Literal["student", "teacher", "admin"] | None = None
    is_active: bool | None = None


class AdminOverview(BaseModel):
    users_total: int
    users_active: int
    users_new_7d: int
    leads_total: int
    leads_new: int


class LeadStatusUpdate(BaseModel):
    status: Literal["new", "contacted", "converted", "closed"]


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class AuthResponse(TokenPair):
    user: UserPublic


class PasswordResetResponse(BaseModel):
    detail: str
    # Only populated when settings.expose_reset_token is true (local/dev).
    reset_token: str | None = None
    expires_at: datetime | None = None


# ===========================================================================
# Stats / profile
# ===========================================================================
class SkillStat(BaseModel):
    skill: str
    percent: float


class UserStats(BaseModel):
    points: int
    xp: int
    level: str
    level_title: str
    streak_days: int
    longest_streak: int
    rank: int | None = None
    lessons_completed: int
    words_learned: int
    minutes_this_week: int
    skills: list[SkillStat]
    battles_played: int = 0
    battles_won: int = 0
    battles_lost: int = 0
    coins: int = 0


class ActivityDay(BaseModel):
    day: date
    minutes: int
    points: int
    lessons_completed: int
    words_reviewed: int


class AchievementOut(ORMModel):
    id: str
    slug: str
    title: str
    description: str | None = None
    icon: str | None = None
    points: int
    threshold: int


class UserAchievementOut(AchievementOut):
    earned_at: datetime | None = None
    earned: bool = False


# ===========================================================================
# Courses
# ===========================================================================
class LessonBrief(ORMModel):
    id: str
    slug: str
    title: str
    description: str | None = None
    kind: str
    duration_sec: int
    order_index: int
    xp_reward: int
    video_url: str | None = None
    audio_url: str | None = None


class LessonDetail(LessonBrief):
    unit_id: str
    content: dict | None = None
    homework: dict | None = None
    question_count: int = 0
    progress: dict | None = None


class UnitOut(ORMModel):
    id: str
    slug: str
    code: str | None = None
    title: str
    description: str | None = None
    emoji: str | None = None
    order_index: int
    lessons: list[LessonBrief] = []
    lesson_count: int = 0


class CourseOut(ORMModel):
    id: str
    slug: str
    title: str
    subtitle: str | None = None
    description: str | None = None
    level: str
    cover_url: str | None = None
    emoji: str | None = None
    color: str | None = None
    order_index: int
    unit_count: int = 0
    lesson_count: int = 0
    enrolled: bool = False
    progress_percent: float = 0.0


class CourseDetail(CourseOut):
    units: list[UnitOut] = []


class ProgressUpdate(BaseModel):
    video_percent: float | None = Field(default=None, ge=0, le=100)
    homework_percent: float | None = Field(default=None, ge=0, le=100)
    watch_seconds: int | None = Field(default=None, ge=0, le=60 * 60 * 12)
    status: Literal["locked", "in_progress", "completed"] | None = None
    score: float | None = Field(default=None, ge=0, le=100)


class ProgressOut(ORMModel):
    lesson_id: str
    status: str
    video_percent: float
    homework_percent: float
    watch_seconds: int
    score: float | None = None
    completed_at: datetime | None = None


class QuizQuestionPublic(BaseModel):
    id: str
    prompt: str
    options: list[str]
    order_index: int
    points: int


class QuizQuestionAnswer(QuizQuestionPublic):
    correct_index: int
    explanation: str | None = None


class QuizSubmitRequest(BaseModel):
    answers: list[int] = Field(min_length=1, max_length=100)


class QuizSubmitResponse(BaseModel):
    correct_count: int
    total: int
    score: float
    points_earned: int
    total_points: int
    results: list[dict[str, Any]]


# ===========================================================================
# Vocabulary
# ===========================================================================
class VocabularyBase(BaseModel):
    word: str = Field(min_length=1, max_length=120)
    translation: str = Field(min_length=1, max_length=240)
    example: str | None = Field(default=None, max_length=1000)
    part_of_speech: str | None = Field(default=None, max_length=24)
    level_tag: str | None = None
    is_favorite: bool = False


class VocabularyCreate(VocabularyBase):
    pass


class VocabularyUpdate(BaseModel):
    word: str | None = Field(default=None, min_length=1, max_length=120)
    translation: str | None = Field(default=None, min_length=1, max_length=240)
    example: str | None = None
    part_of_speech: str | None = None
    level_tag: str | None = None
    status: Literal["new", "learning", "mastered"] | None = None
    is_favorite: bool | None = None


class VocabularyOut(ORMModel):
    id: str
    word: str
    translation: str
    example: str | None = None
    part_of_speech: str | None = None
    level_tag: str
    status: str
    ease: float
    interval_days: int
    review_count: int
    correct_count: int
    is_favorite: bool
    last_reviewed_at: datetime | None = None
    next_review_at: datetime | None = None
    created_at: datetime


class VocabularyBulkCreate(BaseModel):
    items: list[VocabularyCreate] = Field(min_length=1, max_length=500)


class VocabularyReview(BaseModel):
    """SM-2 style grade: 0 = forgot, 5 = perfect."""

    quality: int = Field(ge=0, le=5)


class VocabularyStats(BaseModel):
    total: int
    new: int
    learning: int
    mastered: int
    due_today: int
    favorites: int


# ===========================================================================
# Notifications
# ===========================================================================
class NotificationOut(ORMModel):
    id: str
    kind: str
    title: str
    body: str | None = None
    banner: dict[str, Any] | None = None
    link: str | None = None
    cta_label: str | None = None
    icon: str | None = None
    is_read: bool
    created_at: datetime


class NotificationCreate(BaseModel):
    user_id: str | None = None
    kind: str = "system"
    title: str = Field(min_length=1, max_length=200)
    body: str | None = None
    banner: dict[str, Any] | None = None
    link: str | None = None
    cta_label: str | None = Field(default=None, max_length=80)
    icon: str | None = None


class UnreadCount(BaseModel):
    unread: int
    total: int


# ===========================================================================
# Chat
# ===========================================================================
class ChatUserBrief(BaseModel):
    id: str | None = None
    name: str
    avatar_url: str | None = None
    emoji: str | None = None
    is_bot: bool = False


class MessageOut(BaseModel):
    id: str
    conversation_id: str
    sender_id: str | None = None
    sender_name: str | None = None
    body: str
    kind: str
    attachment_url: str | None = None
    created_at: datetime
    is_mine: bool = False


class ConversationOut(BaseModel):
    id: str
    kind: str
    title: str
    emoji: str | None = None
    color: str | None = None
    is_system: bool = False
    unread_count: int = 0
    last_message: MessageOut | None = None
    last_message_at: datetime | None = None
    members: list[ChatUserBrief] = []


class ConversationCreate(BaseModel):
    title: str | None = Field(default=None, max_length=160)
    kind: Literal["direct", "group"] = "direct"
    member_ids: list[str] = Field(default_factory=list, max_length=50)
    emoji: str | None = Field(default=None, max_length=8)


class MessageCreate(BaseModel):
    body: str = Field(min_length=1, max_length=4000)
    kind: Literal["text", "image", "file", "system"] = "text"
    attachment_url: str | None = Field(default=None, max_length=512)


class MarkReadRequest(BaseModel):
    pass


# ===========================================================================
# Leaderboard
# ===========================================================================
class LeaderboardEntry(BaseModel):
    rank: int
    user_id: str
    name: str
    avatar_url: str | None = None
    avatar_emoji: str | None = None
    points: int
    level: str
    level_title: str
    is_me: bool = False
    streak_days: int = 0


class LeaderboardOut(BaseModel):
    scope: str
    period: str
    level: str | None = None
    entries: list[LeaderboardEntry]
    me: LeaderboardEntry | None = None


# ===========================================================================
# Battles
# ===========================================================================
class BattleCreate(BaseModel):
    mode: Literal["ai", "duel", "group"] = "duel"
    topic: Literal["grammar", "vocabulary", "mixed"] = "grammar"
    level: str | None = None


class BattleScoreRequest(BaseModel):
    round_index: int = Field(ge=0, le=100)
    correct: bool
    answer_index: int | None = None


class BattleQuestion(BaseModel):
    id: str
    prompt: str
    options: list[str]
    order_index: int


class BattleOut(BaseModel):
    id: str
    mode: str
    topic: str
    level: str
    status: str
    rounds: int
    seconds_per_round: int
    host_score: int
    guest_score: int
    points_per_correct: int
    host: ChatUserBrief
    guest: ChatUserBrief | None = None
    winner_id: str | None = None
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    is_host: bool = False
    questions: list[BattleQuestion] = []


class BattleStats(BaseModel):
    played: int
    won: int
    lost: int
    drawn: int
    total_points: int


# ===========================================================================
# Events (Zoom)
# ===========================================================================
class EventOut(ORMModel):
    id: str
    slug: str
    title: str
    description: str | None = None
    host_name: str | None = None
    host_avatar_url: str | None = None
    level: str
    kind: str
    starts_at: datetime
    duration_minutes: int
    meeting_id: str | None = None
    seats: int
    color: str | None = None
    emoji: str | None = None
    is_past: bool = False
    is_registered: bool = False
    registered_count: int = 0
    join_url: str | None = None
    recording_url: str | None = None


class EventRegistrationOut(BaseModel):
    event_id: str
    status: str
    registered_count: int


# ===========================================================================
# Library
# ===========================================================================
class BookOut(ORMModel):
    id: str
    slug: str
    title: str
    author: str | None = None
    level: str
    description: str | None = None
    cover_url: str | None = None
    file_url: str | None = None
    pages: int
    category: str | None = None
    tags: list[str] | None = None


class PodcastOut(ORMModel):
    id: str
    slug: str
    title: str
    host: str | None = None
    level: str
    episode_number: int
    description: str | None = None
    audio_url: str | None = None
    cover_url: str | None = None
    duration_sec: int
    transcript: str | None = None
    tags: list[str] | None = None


class GameOut(ORMModel):
    id: str
    slug: str
    title: str
    kind: str
    description: str | None = None
    emoji: str | None = None
    color: str | None = None
    play_url: str | None = None
    config: dict | None = None


class GameScoreCreate(BaseModel):
    score: int = Field(ge=0, le=1_000_000)
    correct_count: int = Field(default=0, ge=0, le=1000)
    total: int = Field(default=0, ge=0, le=1000)


class GameScoreOut(BaseModel):
    game_id: str
    score: int
    points_earned: int
    best_score: int


class LevelOut(BaseModel):
    slug: str
    title: str
    order: int
    points_required: int
    unlocked: bool
    progress_percent: float
    lessons: int
    description: str | None = None


# ===========================================================================
# Marketing / leads
# ===========================================================================
class LeadCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=5, max_length=32)
    email: EmailStr | None = None
    source: str | None = Field(default=None, max_length=80)
    message: str | None = Field(default=None, max_length=2000)

    @field_validator("phone")
    @classmethod
    def _clean_phone(cls, value: str) -> str:
        cleaned = "".join(ch for ch in value if ch.isdigit() or ch == "+")
        if len(cleaned) < 5:
            raise ValueError("Telefon raqami noto'g'ri.")
        return cleaned


class LeadOut(ORMModel):
    id: str
    name: str
    phone: str
    email: str | None = None
    source: str | None = None
    status: str
    created_at: datetime


# ===========================================================================
# WebSocket envelopes
# ===========================================================================
class WsEnvelope(BaseModel):
    type: str
    data: dict[str, Any] = {}


class HealthOut(BaseModel):
    status: str
    app: str
    version: str
    environment: str
    database: str
    time: datetime
