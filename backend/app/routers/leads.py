"""Landing-page lead capture (index.html hero form)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models, schemas
from ..database import get_session
from ..deps import rate_limit, require_admin
from ..utils import today_utc

router = APIRouter(prefix="/leads", tags=["leads"])

lead_rate_limit = rate_limit("leads", limit=5, window=300)

MAX_LEADS_PER_PHONE_PER_DAY = 3


@router.post(
    "",
    response_model=schemas.LeadOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(lead_rate_limit)],
)
async def create_lead(
    payload: schemas.LeadCreate,
    session: AsyncSession = Depends(get_session),
) -> schemas.LeadOut:
    """Public endpoint — «Bepul darsga yozilish» on the landing page."""
    existing = await session.scalar(
        select(models.Lead)
        .where(models.Lead.phone == payload.phone)
        .order_by(models.Lead.created_at.desc())
    )
    if existing is not None and existing.created_at.date() == today_utc():
        if existing.submissions >= MAX_LEADS_PER_PHONE_PER_DAY:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Bu raqam bilan bugun allaqachon murojaat qilingan. Tez orada bog'lanamiz!",
            )
        existing.submissions += 1
        existing.name = payload.name
        existing.message = payload.message or existing.message
        await session.commit()
        await session.refresh(existing)
        return schemas.LeadOut.model_validate(existing)

    lead = models.Lead(
        name=payload.name.strip(),
        phone=payload.phone,
        email=(payload.email.lower() if payload.email else None),
        source=payload.source or "index-hero",
        message=payload.message,
    )
    session.add(lead)
    await session.commit()
    await session.refresh(lead)
    return schemas.LeadOut.model_validate(lead)


@router.get(
    "",
    response_model=schemas.Page[schemas.LeadOut],
    dependencies=[Depends(require_admin)],
)
async def list_leads(
    status_filter: str | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
) -> schemas.Page[schemas.LeadOut]:
    filters = []
    if status_filter:
        filters.append(models.Lead.status == status_filter)
    total = await session.scalar(select(func.count(models.Lead.id)).where(*filters))
    rows = (
        await session.execute(
            select(models.Lead)
            .where(*filters)
            .order_by(models.Lead.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    ).scalars().all()
    return schemas.Page(
        items=[schemas.LeadOut.model_validate(row) for row in rows],
        total=int(total or 0),
        limit=limit,
        offset=offset,
    )
