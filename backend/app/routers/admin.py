"""Administrator endpoints for platform operations."""

from __future__ import annotations

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models, schemas
from ..database import get_session
from ..deps import require_admin
from ..utils import UserRole, utcnow

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/overview", response_model=schemas.AdminOverview)
async def overview(
    _: models.User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> schemas.AdminOverview:
    week_ago = utcnow() - timedelta(days=7)
    users_total = await session.scalar(select(func.count(models.User.id))) or 0
    users_active = await session.scalar(
        select(func.count(models.User.id)).where(models.User.is_active.is_(True))
    ) or 0
    users_new = await session.scalar(
        select(func.count(models.User.id)).where(models.User.created_at >= week_ago)
    ) or 0
    leads_total = await session.scalar(select(func.count(models.Lead.id))) or 0
    leads_new = await session.scalar(
        select(func.count(models.Lead.id)).where(models.Lead.status == "new")
    ) or 0
    return schemas.AdminOverview(
        users_total=int(users_total),
        users_active=int(users_active),
        users_new_7d=int(users_new),
        leads_total=int(leads_total),
        leads_new=int(leads_new),
    )


@router.get("/users", response_model=schemas.Page[schemas.AdminUserOut])
async def list_users(
    q: str | None = Query(default=None, max_length=255),
    role: str | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: models.User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> schemas.Page[schemas.AdminUserOut]:
    filters = []
    if q:
        term = f"%{q.strip()}%"
        filters.append((models.User.email.ilike(term)) | (models.User.full_name.ilike(term)))
    if role:
        if role not in UserRole.ALL:
            raise HTTPException(status_code=422, detail="Foydalanuvchi roli noto'g'ri.")
        filters.append(models.User.role == role)
    if is_active is not None:
        filters.append(models.User.is_active.is_(is_active))

    total = await session.scalar(select(func.count(models.User.id)).where(*filters)) or 0
    users = (
        await session.execute(
            select(models.User)
            .where(*filters)
            .order_by(models.User.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    ).scalars().all()
    return schemas.Page(
        items=[schemas.AdminUserOut.model_validate(user) for user in users],
        total=int(total),
        limit=limit,
        offset=offset,
    )


@router.patch("/users/{user_id}", response_model=schemas.AdminUserOut)
async def update_user(
    user_id: str,
    payload: schemas.AdminUserUpdate,
    actor: models.User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> schemas.AdminUserOut:
    target = await session.get(models.User, user_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Foydalanuvchi topilmadi.")

    changes = payload.model_dump(exclude_unset=True)
    next_role = changes.get("role", target.role)
    next_active = changes.get("is_active", target.is_active)
    if target.id == actor.id and (next_role != UserRole.ADMIN or not next_active):
        raise HTTPException(
            status_code=409,
            detail="O'zingizning admin huquqingizni olib tashlay olmaysiz yoki hisobingizni bloklay olmaysiz.",
        )

    removing_active_admin = (
        target.role == UserRole.ADMIN
        and target.is_active
        and (next_role != UserRole.ADMIN or not next_active)
    )
    if removing_active_admin:
        active_admins = await session.scalar(
            select(func.count(models.User.id)).where(
                models.User.role == UserRole.ADMIN,
                models.User.is_active.is_(True),
            )
        ) or 0
        if active_admins <= 1:
            raise HTTPException(
                status_code=409,
                detail="Oxirgi faol admin hisobini o'zgartirib bo'lmaydi.",
            )

    for field, value in changes.items():
        setattr(target, field, value)

    if changes.get("is_active") is False:
        tokens = (
            await session.execute(
                select(models.RefreshToken).where(
                    models.RefreshToken.user_id == target.id,
                    models.RefreshToken.revoked.is_(False),
                )
            )
        ).scalars().all()
        for token in tokens:
            token.revoked = True

    await session.commit()
    await session.refresh(target)
    return schemas.AdminUserOut.model_validate(target)


@router.get("/leads", response_model=schemas.Page[schemas.LeadOut])
async def list_leads(
    status: str | None = Query(default=None),
    q: str | None = Query(default=None, max_length=255),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: models.User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> schemas.Page[schemas.LeadOut]:
    filters = []
    if status:
        if status not in {"new", "contacted", "converted", "closed"}:
            raise HTTPException(status_code=422, detail="Lead holati noto'g'ri.")
        filters.append(models.Lead.status == status)
    if q and q.strip():
        term = f"%{q.strip()}%"
        filters.append(
            models.Lead.name.ilike(term)
            | models.Lead.phone.ilike(term)
            | models.Lead.email.ilike(term)
        )
    total = await session.scalar(select(func.count(models.Lead.id)).where(*filters)) or 0
    leads = (
        await session.execute(
            select(models.Lead)
            .where(*filters)
            .order_by(models.Lead.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    ).scalars().all()
    return schemas.Page(
        items=[schemas.LeadOut.model_validate(lead) for lead in leads],
        total=int(total),
        limit=limit,
        offset=offset,
    )


@router.patch("/leads/{lead_id}", response_model=schemas.LeadOut)
async def update_lead(
    lead_id: str,
    payload: schemas.LeadStatusUpdate,
    _: models.User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> schemas.LeadOut:
    lead = await session.get(models.Lead, lead_id)
    if lead is None:
        raise HTTPException(status_code=404, detail="Lead topilmadi.")
    lead.status = payload.status
    await session.commit()
    await session.refresh(lead)
    return schemas.LeadOut.model_validate(lead)
