"""Vocabulary notebook with spaced-repetition review."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models, schemas, services
from ..database import get_session
from ..deps import get_current_user
from ..utils import normalize_level, utcnow

router = APIRouter(prefix="/vocabulary", tags=["vocabulary"])

XP_PER_WORD = 2


def _to_out(item: models.VocabularyItem) -> schemas.VocabularyOut:
    return schemas.VocabularyOut.model_validate(item)


@router.get("", response_model=schemas.Page[schemas.VocabularyOut])
async def list_vocabulary(
    q: str | None = Query(default=None, max_length=80),
    status_filter: str | None = Query(default=None, alias="status"),
    favorite: bool | None = None,
    due_only: bool = False,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> schemas.Page[schemas.VocabularyOut]:
    filters = [models.VocabularyItem.user_id == user.id]
    if q:
        needle = f"%{q.strip().lower()}%"
        filters.append(
            or_(
                func.lower(models.VocabularyItem.word).like(needle),
                func.lower(models.VocabularyItem.translation).like(needle),
            )
        )
    if status_filter:
        filters.append(models.VocabularyItem.status == status_filter)
    if favorite is not None:
        filters.append(models.VocabularyItem.is_favorite.is_(favorite))
    if due_only:
        filters.append(
            or_(
                models.VocabularyItem.next_review_at.is_(None),
                models.VocabularyItem.next_review_at <= utcnow(),
            )
        )

    total = await session.scalar(
        select(func.count(models.VocabularyItem.id)).where(*filters)
    )
    rows = (
        await session.execute(
            select(models.VocabularyItem)
            .where(*filters)
            .order_by(models.VocabularyItem.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
    ).scalars().all()

    return schemas.Page(
        items=[_to_out(row) for row in rows],
        total=int(total or 0),
        limit=limit,
        offset=offset,
    )


@router.get("/stats", response_model=schemas.VocabularyStats)
async def vocabulary_stats(
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> schemas.VocabularyStats:
    rows = (
        await session.execute(
            select(models.VocabularyItem.status, func.count(models.VocabularyItem.id))
            .where(models.VocabularyItem.user_id == user.id)
            .group_by(models.VocabularyItem.status)
        )
    ).all()
    counts = {status: int(count) for status, count in rows}
    due = await session.scalar(
        select(func.count(models.VocabularyItem.id)).where(
            models.VocabularyItem.user_id == user.id,
            or_(
                models.VocabularyItem.next_review_at.is_(None),
                models.VocabularyItem.next_review_at <= utcnow(),
            ),
        )
    )
    favorites = await session.scalar(
        select(func.count(models.VocabularyItem.id)).where(
            models.VocabularyItem.user_id == user.id,
            models.VocabularyItem.is_favorite.is_(True),
        )
    )
    return schemas.VocabularyStats(
        total=sum(counts.values()),
        new=counts.get("new", 0),
        learning=counts.get("learning", 0),
        mastered=counts.get("mastered", 0),
        due_today=int(due or 0),
        favorites=int(favorites or 0),
    )


@router.get("/due", response_model=list[schemas.VocabularyOut])
async def due_vocabulary(
    limit: int = Query(default=20, ge=1, le=100),
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[schemas.VocabularyOut]:
    rows = (
        await session.execute(
            select(models.VocabularyItem)
            .where(
                models.VocabularyItem.user_id == user.id,
                or_(
                    models.VocabularyItem.next_review_at.is_(None),
                    models.VocabularyItem.next_review_at <= utcnow(),
                ),
            )
            .order_by(models.VocabularyItem.next_review_at.asc().nullsfirst())
            .limit(limit)
        )
    ).scalars().all()
    return [_to_out(row) for row in rows]


@router.post(
    "",
    response_model=schemas.VocabularyOut,
    status_code=status.HTTP_201_CREATED,
)
async def create_vocabulary(
    payload: schemas.VocabularyCreate,
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> schemas.VocabularyOut:
    word = payload.word.strip()
    duplicate = await session.scalar(
        select(models.VocabularyItem).where(
            models.VocabularyItem.user_id == user.id,
            func.lower(models.VocabularyItem.word) == word.lower(),
        )
    )
    if duplicate is not None:
        raise HTTPException(status_code=409, detail="Bu so'z lug'atingizda mavjud.")

    item = models.VocabularyItem(
        user_id=user.id,
        word=word,
        translation=payload.translation.strip(),
        example=(payload.example or "").strip() or None,
        part_of_speech=payload.part_of_speech,
        level_tag=normalize_level(payload.level_tag, user.level),
        is_favorite=payload.is_favorite,
        next_review_at=utcnow(),
    )
    session.add(item)
    await services.award_points(session, user, XP_PER_WORD, words_reviewed=0)
    await services.bump_skill(session, user.id, "vocabulary", 1)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Bu so'z allaqachon qo'shilgan.") from exc
    await session.refresh(item)
    return _to_out(item)


@router.post("/bulk", response_model=list[schemas.VocabularyOut])
async def bulk_create(
    payload: schemas.VocabularyBulkCreate,
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[schemas.VocabularyOut]:
    existing = {
        word.lower()
        for (word,) in (
            await session.execute(
                select(models.VocabularyItem.word).where(
                    models.VocabularyItem.user_id == user.id
                )
            )
        ).all()
    }
    created: list[models.VocabularyItem] = []
    seen: set[str] = set()
    for entry in payload.items:
        key = entry.word.strip().lower()
        if not key or key in existing or key in seen:
            continue
        seen.add(key)
        item = models.VocabularyItem(
            user_id=user.id,
            word=entry.word.strip(),
            translation=entry.translation.strip(),
            example=(entry.example or "").strip() or None,
            part_of_speech=entry.part_of_speech,
            level_tag=normalize_level(entry.level_tag, user.level),
            next_review_at=utcnow(),
        )
        session.add(item)
        created.append(item)

    if created:
        await services.award_points(session, user, XP_PER_WORD * len(created))
        await services.bump_skill(session, user.id, "vocabulary", float(len(created)))
        await session.commit()
        for item in created:
            await session.refresh(item)
    return [_to_out(item) for item in created]


@router.get("/{item_id}", response_model=schemas.VocabularyOut)
async def get_vocabulary(
    item_id: str,
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> schemas.VocabularyOut:
    item = await _owned(session, user, item_id)
    return _to_out(item)


@router.patch("/{item_id}", response_model=schemas.VocabularyOut)
async def update_vocabulary(
    item_id: str,
    payload: schemas.VocabularyUpdate,
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> schemas.VocabularyOut:
    item = await _owned(session, user, item_id)
    data = payload.model_dump(exclude_unset=True)

    new_word = data.pop("word", None)
    if new_word:
        clash = await session.scalar(
            select(models.VocabularyItem).where(
                models.VocabularyItem.user_id == user.id,
                func.lower(models.VocabularyItem.word) == new_word.strip().lower(),
                models.VocabularyItem.id != item.id,
            )
        )
        if clash is not None:
            raise HTTPException(status_code=409, detail="Bu so'z lug'atingizda mavjud.")
        item.word = new_word.strip()

    if "level_tag" in data and data["level_tag"]:
        data["level_tag"] = normalize_level(data["level_tag"], user.level)

    for field, value in data.items():
        setattr(item, field, value)

    await session.commit()
    await session.refresh(item)
    return _to_out(item)


@router.delete("/{item_id}", response_model=schemas.Message)
async def delete_vocabulary(
    item_id: str,
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> schemas.Message:
    item = await _owned(session, user, item_id)
    await session.delete(item)
    await session.commit()
    return schemas.Message(detail="So'z o'chirildi.")


@router.post("/{item_id}/favorite", response_model=schemas.VocabularyOut)
async def toggle_favorite(
    item_id: str,
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> schemas.VocabularyOut:
    item = await _owned(session, user, item_id)
    item.is_favorite = not item.is_favorite
    await session.commit()
    await session.refresh(item)
    return _to_out(item)


@router.post("/{item_id}/review", response_model=schemas.VocabularyOut)
async def review_vocabulary(
    item_id: str,
    payload: schemas.VocabularyReview,
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> schemas.VocabularyOut:
    item = await _owned(session, user, item_id)
    was_new = item.status == "new"
    services.apply_review(item, payload.quality, user)
    points = 5 if payload.quality >= 4 else (3 if payload.quality == 3 else 1)
    await services.award_points(session, user, points, words_reviewed=1)
    if was_new:
        await services.bump_skill(session, user.id, "vocabulary", 2)
    await session.commit()
    await session.refresh(item)
    return _to_out(item)


async def _owned(
    session: AsyncSession, user: models.User, item_id: str
) -> models.VocabularyItem:
    item = await session.get(models.VocabularyItem, item_id)
    if item is None or item.user_id != user.id:
        raise HTTPException(status_code=404, detail="So'z topilmadi.")
    return item
