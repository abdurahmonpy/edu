"""Registration, login, token rotation and password recovery."""

from __future__ import annotations

import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models, schemas, services
from ..config import settings
from ..database import get_session
from ..deps import auth_rate_limit, get_current_user
from ..email import send_password_reset_email
from ..security import (
    TokenError,
    create_access_token,
    create_refresh_token,
    create_reset_token,
    decode_refresh_token,
    decode_reset_token,
    hash_password,
    hash_token,
    password_problems,
    verify_password,
)
from ..utils import SKILLS, normalize_level, utcnow

router = APIRouter(prefix="/auth", tags=["auth"])
logger = logging.getLogger(__name__)


# --------------------------------------------------------------------- helpers
def _issue_tokens(
    session: AsyncSession,
    user: models.User,
    *,
    user_agent: str | None = None,
) -> schemas.TokenPair:
    access, expires_in = create_access_token(user.id, role=user.role)
    refresh, refresh_expires = create_refresh_token(user.id)
    session.add(
        models.RefreshToken(
            user_id=user.id,
            token_hash=hash_token(refresh),
            expires_at=refresh_expires,
            user_agent=(user_agent or "")[:255] or None,
        )
    )
    return schemas.TokenPair(
        access_token=access,
        refresh_token=refresh,
        expires_in=expires_in,
    )


async def _bootstrap_user(session: AsyncSession, user: models.User) -> None:
    """Give a brand-new account its starting state: skills, chats, welcome note."""
    for skill in SKILLS:
        session.add(models.SkillProgress(user_id=user.id, skill=skill, percent=0.0))

    await services.notify(
        session,
        user.id,
        kind="system",
        title="Englify'ga xush kelibsiz! 🎉",
        body=(
            f"Salom, {user.full_name}! Birinchi darsingizni boshlang va kunlik "
            f"{user.daily_goal_minutes} daqiqa maqsadiga erishing."
        ),
        banner={"badge": "START", "emoji": "👋"},
        link="app.html#darslar",
        cta_label="Darsni boshlash",
        icon="👋",
    )

    # Support conversation with the platform + the Alomat assistant bot.
    support = models.Conversation(
        kind="support", title="Support Service", emoji="S", color="#0A93F5", is_system=True
    )
    session.add(support)
    await session.flush()
    session.add(
        models.ConversationMember(
            conversation_id=support.id, user_id=user.id, role="member", last_read_at=utcnow()
        )
    )
    session.add(
        models.Message(
            conversation_id=support.id,
            sender_name="Support Service",
            body="Assalom alaykum! Sizni ENGLIFY jamoasi safida ko'rishdan mamnunmiz.",
            kind="text",
        )
    )
    support.last_message_at = utcnow()

    bot = models.Conversation(
        kind="bot", title="Alomat (Bot)", emoji="A", color="#2ED573", is_system=True
    )
    session.add(bot)
    await session.flush()
    session.add(
        models.ConversationMember(
            conversation_id=bot.id, user_id=user.id, role="member", last_read_at=utcnow()
        )
    )
    session.add(
        models.ConversationMember(conversation_id=bot.id, bot_name="Alomat", role="bot")
    )
    session.add(
        models.Message(
            conversation_id=bot.id,
            sender_name="Alomat",
            body="Savollaringiz bo'lsa marhamat, men yordam beraman!",
            kind="text",
        )
    )
    bot.last_message_at = utcnow()


# -------------------------------------------------------------------- register
@router.post(
    "/register",
    response_model=schemas.AuthResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(auth_rate_limit)],
)
async def register(
    payload: schemas.RegisterRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> schemas.AuthResponse:
    problems = password_problems(payload.password)
    if problems:
        raise HTTPException(status_code=422, detail=" ".join(problems))

    email = payload.email.lower().strip()
    existing = await session.scalar(select(models.User).where(models.User.email == email))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu email allaqachon ro'yxatdan o'tgan. Tizimga kiring.",
        )

    user = models.User(
        email=email,
        phone=payload.phone,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        level=normalize_level(payload.level),
        daily_goal_minutes=settings.default_daily_goal_minutes,
        is_verified=False,
    )
    session.add(user)
    try:
        await session.flush()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu email yoki telefon raqami band.",
        ) from exc

    await _bootstrap_user(session, user)
    tokens = _issue_tokens(session, user, user_agent=request.headers.get("user-agent"))
    user.last_login_at = utcnow()
    await session.commit()
    await session.refresh(user)

    return schemas.AuthResponse(
        **tokens.model_dump(), user=services.user_public(user)
    )


# ----------------------------------------------------------------------- login
@router.post(
    "/login",
    response_model=schemas.AuthResponse,
    dependencies=[Depends(auth_rate_limit)],
)
async def login(
    payload: schemas.LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> schemas.AuthResponse:
    email = payload.email.lower().strip()
    user = await session.scalar(select(models.User).where(models.User.email == email))

    # Same message for "no such user" and "wrong password" (no user enumeration).
    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Email yoki parol noto'g'ri."
    )
    if user is None:
        raise invalid
    if user.locked_until and user.locked_until > utcnow():
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail="Hisob vaqtincha bloklangan. Keyinroq qayta urinib ko'ring.",
        )
    if not verify_password(payload.password, user.password_hash):
        user.failed_logins += 1
        if user.failed_logins >= settings.max_failed_logins:
            user.locked_until = utcnow() + timedelta(minutes=settings.login_lockout_minutes)
            user.failed_logins = 0
        await session.commit()
        raise invalid
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Hisob bloklangan.")

    user.failed_logins = 0
    user.locked_until = None
    user.last_login_at = utcnow()
    services.touch_streak(user)

    tokens = _issue_tokens(session, user, user_agent=request.headers.get("user-agent"))
    await session.commit()
    await session.refresh(user)

    return schemas.AuthResponse(**tokens.model_dump(), user=services.user_public(user))


@router.post(
    "/token",
    response_model=schemas.AuthResponse,
    dependencies=[Depends(auth_rate_limit)],
    summary="Swagger OAuth2 login",
    description="Swagger Authorize oynasida username maydoniga email kiriting.",
)
async def swagger_token(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session),
) -> schemas.AuthResponse:
    """OAuth2 password-form endpoint used by Swagger's Authorize button."""
    return await login(
        schemas.LoginRequest(email=form.username, password=form.password), request, session
    )


# --------------------------------------------------------------------- refresh
@router.post("/refresh", response_model=schemas.AuthResponse)
async def refresh_tokens(
    payload: schemas.RefreshRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> schemas.AuthResponse:
    try:
        claims = decode_refresh_token(payload.refresh_token)
    except TokenError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc

    stored = await session.scalar(
        select(models.RefreshToken).where(
            models.RefreshToken.token_hash == hash_token(payload.refresh_token)
        )
    )
    if stored is None or stored.revoked or stored.expires_at <= utcnow():
        raise HTTPException(
            status_code=401, detail="Sessiya muddati tugagan. Qaytadan kiring."
        )

    user = await session.get(models.User, claims.get("sub"))
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Foydalanuvchi topilmadi.")

    # Rotate: the old refresh token is burned immediately.
    stored.revoked = True
    tokens = _issue_tokens(session, user, user_agent=request.headers.get("user-agent"))
    await session.commit()
    await session.refresh(user)

    return schemas.AuthResponse(**tokens.model_dump(), user=services.user_public(user))


# ---------------------------------------------------------------------- logout
@router.post("/logout", response_model=schemas.Message)
async def logout(
    payload: schemas.LogoutRequest,
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> schemas.Message:
    query = select(models.RefreshToken).where(
        models.RefreshToken.user_id == user.id, models.RefreshToken.revoked.is_(False)
    )
    if not payload.all_devices and payload.refresh_token:
        query = query.where(
            models.RefreshToken.token_hash == hash_token(payload.refresh_token)
        )
    tokens = (await session.execute(query)).scalars().all()
    for token in tokens:
        token.revoked = True
    await session.commit()
    return schemas.Message(
        detail="Barcha qurilmalardan chiqdingiz."
        if payload.all_devices
        else "Tizimdan chiqdingiz."
    )


# -------------------------------------------------------------------------- me
@router.get("/me", response_model=schemas.UserPublic)
async def read_me(user: models.User = Depends(get_current_user)) -> schemas.UserPublic:
    return services.user_public(user)


@router.patch("/me", response_model=schemas.UserPublic)
async def update_me(
    payload: schemas.UserUpdate,
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> schemas.UserPublic:
    data = payload.model_dump(exclude_unset=True)
    if "level" in data and data["level"]:
        data["level"] = normalize_level(data["level"])
    if "phone" in data and data["phone"] is not None:
        data["phone"] = "".join(ch for ch in data["phone"] if ch.isdigit() or ch == "+") or None
    for field, value in data.items():
        setattr(user, field, value)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Bu telefon raqami band.") from exc
    await session.refresh(user)
    return services.user_public(user)


# ----------------------------------------------------------- password changes
@router.post("/change-password", response_model=schemas.Message)
async def change_password(
    payload: schemas.ChangePasswordRequest,
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> schemas.Message:
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Joriy parol noto'g'ri.")
    problems = password_problems(payload.new_password)
    if problems:
        raise HTTPException(status_code=422, detail=" ".join(problems))
    if verify_password(payload.new_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Yangi parol eskisidan farq qilishi kerak.")

    user.password_hash = hash_password(payload.new_password)
    tokens = (
        await session.execute(
            select(models.RefreshToken).where(
                models.RefreshToken.user_id == user.id,
                models.RefreshToken.revoked.is_(False),
            )
        )
    ).scalars().all()
    for token in tokens:
        token.revoked = True
    await session.commit()
    return schemas.Message(detail="Parol yangilandi. Boshqa qurilmalardan chiqdingiz.")


@router.post(
    "/forgot-password",
    response_model=schemas.PasswordResetResponse,
    dependencies=[Depends(auth_rate_limit)],
)
async def forgot_password(
    payload: schemas.ForgotPasswordRequest,
    session: AsyncSession = Depends(get_session),
) -> schemas.PasswordResetResponse:
    email = payload.email.lower().strip()
    user = await session.scalar(select(models.User).where(models.User.email == email))

    # Always answer the same way so the endpoint cannot be used to probe emails.
    generic = "Agar bu email ro'yxatdan o'tgan bo'lsa, tiklash havolasi yuborildi."

    if user is None or not user.is_active:
        return schemas.PasswordResetResponse(detail=generic)

    token, expires_at = create_reset_token(user.id)
    session.add(
        models.PasswordResetToken(
            user_id=user.id, token_hash=hash_token(token), expires_at=expires_at
        )
    )
    await session.commit()

    if settings.smtp_is_configured:
        try:
            await send_password_reset_email(email, token)
        except Exception:  # noqa: BLE001 - keep the response generic to avoid account probing
            logger.exception("Password reset email delivery failed")
    elif settings.is_production:
        logger.error("Password reset requested but SMTP is not configured")

    # No SMTP provider is configured in this deployment, so the token surfaces
    # in the response only when EXPLICITLY enabled for local development.
    return schemas.PasswordResetResponse(
        detail=generic,
        reset_token=token if settings.expose_reset_token else None,
        expires_at=expires_at if settings.expose_reset_token else None,
    )


@router.post("/reset-password", response_model=schemas.Message)
async def reset_password(
    payload: schemas.ResetPasswordRequest,
    session: AsyncSession = Depends(get_session),
) -> schemas.Message:
    try:
        claims = decode_reset_token(payload.token)
    except TokenError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    stored = await session.scalar(
        select(models.PasswordResetToken).where(
            models.PasswordResetToken.token_hash == hash_token(payload.token)
        )
    )
    if stored is None or stored.used or stored.expires_at <= utcnow():
        raise HTTPException(status_code=400, detail="Tiklash havolasi yaroqsiz yoki muddati o'tgan.")

    problems = password_problems(payload.new_password)
    if problems:
        raise HTTPException(status_code=422, detail=" ".join(problems))

    user = await session.get(models.User, claims.get("sub"))
    if user is None:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi.")

    user.password_hash = hash_password(payload.new_password)
    user.failed_logins = 0
    user.locked_until = None
    stored.used = True

    tokens = (
        await session.execute(
            select(models.RefreshToken).where(
                models.RefreshToken.user_id == user.id,
                models.RefreshToken.revoked.is_(False),
            )
        )
    ).scalars().all()
    for token in tokens:
        token.revoked = True

    await session.commit()
    return schemas.Message(detail="Parol tiklandi. Endi yangi parol bilan kiring.")
