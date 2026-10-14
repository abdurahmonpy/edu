"""«Jang» — AI, duel and group quiz battles with matchmaking."""

from __future__ import annotations

import random

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models, schemas, services
from ..database import get_session
from ..deps import get_current_user
from ..realtime import channel_for_battle, hub
from ..utils import normalize_level, utcnow

router = APIRouter(prefix="/battles", tags=["battles"])

DEFAULT_ROUNDS = 5
DEFAULT_SECONDS = 15
DEFAULT_POINTS = 20


# ------------------------------------------------------------------- helpers
def _brief(user: models.User | None) -> schemas.ChatUserBrief | None:
    if user is None:
        return None
    return schemas.ChatUserBrief(
        id=user.id,
        name=user.display_name,
        avatar_url=user.avatar_url,
        emoji=user.avatar_emoji,
    )


async def _battle_out(
    session: AsyncSession, battle: models.Battle, viewer: models.User
) -> schemas.BattleOut:
    host = await session.get(models.User, battle.host_id)
    guest = await session.get(models.User, battle.guest_id) if battle.guest_id else None

    questions = [
        schemas.BattleQuestion(
            id=item["id"],
            prompt=item["prompt"],
            options=item["options"],
            order_index=index,
        )
        for index, item in enumerate(battle.questions or [])
    ]

    return schemas.BattleOut(
        id=battle.id,
        mode=battle.mode,
        topic=battle.topic,
        level=battle.level,
        status=battle.status,
        rounds=battle.rounds,
        seconds_per_round=battle.seconds_per_round,
        host_score=battle.host_score,
        guest_score=battle.guest_score,
        points_per_correct=battle.points_per_correct,
        host=_brief(host) or schemas.ChatUserBrief(name="Host"),
        guest=_brief(guest) or (
            schemas.ChatUserBrief(name="AI Bot", emoji="🤖", is_bot=True)
            if battle.mode == "ai"
            else None
        ),
        winner_id=battle.winner_id,
        created_at=battle.created_at,
        started_at=battle.started_at,
        finished_at=battle.finished_at,
        is_host=battle.host_id == viewer.id,
        questions=questions,
    )


async def _pick_questions(
    session: AsyncSession, topic: str, level: str, rounds: int
) -> list[dict]:
    filters = [models.BattleQuestionBank.is_active.is_(True)]
    if topic != "mixed":
        filters.append(models.BattleQuestionBank.topic == topic)

    rows = (
        await session.execute(select(models.BattleQuestionBank).where(*filters))
    ).scalars().all()

    # Prefer questions tagged with the battle level, then top up from the pool.
    on_level = [row for row in rows if row.level == level]
    pool = on_level or list(rows)
    if not pool:
        raise HTTPException(
            status_code=503,
            detail="Jang savollari hali yuklanmagan. Keyinroq urinib ko'ring.",
        )

    random.shuffle(pool)
    chosen = pool[:rounds]
    while len(chosen) < rounds:  # repeat-safe fill for tiny banks
        chosen.append(random.choice(pool))

    return [
        {
            "id": row.id,
            "prompt": row.prompt,
            "options": list(row.options or []),
            "correct_index": row.correct_index,
            "points": row.points,
        }
        for row in chosen
    ]


async def _require_member(
    session: AsyncSession, battle_id: str, user: models.User
) -> models.Battle:
    battle = await session.get(models.Battle, battle_id)
    if battle is None:
        raise HTTPException(status_code=404, detail="Jang topilmadi.")
    if user.id not in {battle.host_id, battle.guest_id}:
        raise HTTPException(status_code=403, detail="Bu jangda siz qatnashmadingiz.")
    return battle


async def _log(
    session: AsyncSession, battle_id: str, kind: str, user_id: str | None, payload: dict
) -> None:
    session.add(
        models.BattleEvent(
            battle_id=battle_id, kind=kind, user_id=user_id, payload=payload
        )
    )


# -------------------------------------------------------------------- actions
@router.get("/stats", response_model=schemas.BattleStats)
async def my_battle_stats(
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> schemas.BattleStats:
    return await services.battle_stats(session, user.id)


@router.get("/history", response_model=list[schemas.BattleOut])
async def my_history(
    limit: int = Query(default=20, ge=1, le=100),
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[schemas.BattleOut]:
    rows = (
        await session.execute(
            select(models.Battle)
            .where(
                or_(
                    models.Battle.host_id == user.id,
                    models.Battle.guest_id == user.id,
                )
            )
            .order_by(models.Battle.created_at.desc())
            .limit(limit)
        )
    ).scalars().all()
    return [await _battle_out(session, row, user) for row in rows]


@router.post("", response_model=schemas.BattleOut, status_code=status.HTTP_201_CREATED)
async def create_or_join_battle(
    payload: schemas.BattleCreate,
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> schemas.BattleOut:
    level = normalize_level(payload.level, user.level)

    # Duel/group: first try to pair up with somebody already waiting.
    if payload.mode in {"duel", "group"}:
        waiting = await session.scalar(
            select(models.Battle)
            .where(
                models.Battle.status == "waiting",
                models.Battle.mode == payload.mode,
                models.Battle.topic == payload.topic,
                models.Battle.host_id != user.id,
            )
            .order_by(models.Battle.created_at.asc())
        )
        if waiting is not None:
            waiting.guest_id = user.id
            waiting.status = "active"
            waiting.started_at = utcnow()
            await _log(session, waiting.id, "joined", user.id, {})
            await services.notify(
                session,
                waiting.host_id,
                kind="battle",
                title="Raqib topildi! ⚔️",
                body=f"{user.display_name} siz bilan jang qilmoqchi.",
                link=f"jang.html?battle={waiting.id}",
                icon="⚔️",
            )
            await session.commit()
            await session.refresh(waiting)
            out = await _battle_out(session, waiting, user)
            await hub.broadcast(
                channel_for_battle(waiting.id),
                {"type": "battle.started", "data": out.model_dump(mode="json")},
            )
            return out

    questions = await _pick_questions(session, payload.topic, level, DEFAULT_ROUNDS)
    battle = models.Battle(
        host_id=user.id,
        mode=payload.mode,
        topic=payload.topic,
        level=level,
        rounds=DEFAULT_ROUNDS,
        seconds_per_round=DEFAULT_SECONDS,
        points_per_correct=DEFAULT_POINTS,
        questions=questions,
        status="active" if payload.mode == "ai" else "waiting",
        started_at=utcnow() if payload.mode == "ai" else None,
    )
    session.add(battle)
    await session.flush()
    await _log(session, battle.id, "created", user.id, {"mode": payload.mode})
    await session.commit()
    await session.refresh(battle)
    return await _battle_out(session, battle, user)


@router.get("/{battle_id}", response_model=schemas.BattleOut)
async def get_battle(
    battle_id: str,
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> schemas.BattleOut:
    battle = await _require_member(session, battle_id, user)
    return await _battle_out(session, battle, user)


@router.post("/{battle_id}/join", response_model=schemas.BattleOut)
async def join_battle(
    battle_id: str,
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> schemas.BattleOut:
    battle = await session.get(models.Battle, battle_id)
    if battle is None:
        raise HTTPException(status_code=404, detail="Jang topilmadi.")
    if battle.host_id == user.id or battle.guest_id == user.id:
        return await _battle_out(session, battle, user)
    if battle.status != "waiting" or battle.guest_id is not None:
        raise HTTPException(status_code=409, detail="Bu jang allaqachon boshlangan.")

    battle.guest_id = user.id
    battle.status = "active"
    battle.started_at = utcnow()
    await _log(session, battle.id, "joined", user.id, {})
    await services.notify(
        session,
        battle.host_id,
        kind="battle",
        title="Raqib topildi! ⚔️",
        body=f"{user.display_name} jangni qabul qildi.",
        link=f"jang.html?battle={battle.id}",
        icon="⚔️",
    )
    await session.commit()
    await session.refresh(battle)
    out = await _battle_out(session, battle, user)
    await hub.broadcast(
        channel_for_battle(battle.id),
        {"type": "battle.started", "data": out.model_dump(mode="json")},
    )
    return out


@router.post("/{battle_id}/answer", response_model=schemas.BattleOut)
async def submit_answer(
    battle_id: str,
    payload: schemas.BattleScoreRequest,
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> schemas.BattleOut:
    battle = await _require_member(session, battle_id, user)
    if battle.status == "finished":
        raise HTTPException(status_code=409, detail="Jang tugagan.")

    questions = battle.questions or []
    if payload.round_index >= len(questions):
        raise HTTPException(status_code=422, detail="Bunday raund yo'q.")

    is_host = battle.host_id == user.id
    question = questions[payload.round_index]
    correct = (
        payload.answer_index is not None
        and int(payload.answer_index) == int(question["correct_index"])
    )

    if correct:
        if is_host:
            battle.host_score += battle.points_per_correct
        else:
            battle.guest_score += battle.points_per_correct

    await _log(
        session,
        battle.id,
        "answer",
        user.id,
        {
            "round": payload.round_index,
            "answer_index": payload.answer_index,
            "correct": correct,
        },
    )

    # AI opponent answers a round as soon as the human submits one.
    if battle.mode == "ai" and correct and random.random() > 0.35:
        battle.guest_score += battle.points_per_correct

    await session.commit()
    await session.refresh(battle)

    out = await _battle_out(session, battle, user)
    await hub.broadcast(
        channel_for_battle(battle.id),
        {
            "type": "battle.score",
            "data": {
                "battle_id": battle.id,
                "user_id": user.id,
                "host_score": battle.host_score,
                "guest_score": battle.guest_score,
                "round_index": payload.round_index,
                "correct": correct,
            },
        },
    )
    return out


@router.post("/{battle_id}/finish", response_model=schemas.BattleOut)
async def finish_battle(
    battle_id: str,
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> schemas.BattleOut:
    battle = await _require_member(session, battle_id, user)
    if battle.status == "finished":
        return await _battle_out(session, battle, user)

    if battle.host_score > battle.guest_score:
        battle.winner_id = battle.host_id
    elif battle.guest_score > battle.host_score:
        battle.winner_id = battle.guest_id
    else:
        battle.winner_id = None  # draw

    battle.status = "finished"
    battle.finished_at = utcnow()

    winner_id = battle.winner_id
    if winner_id:
        winner = await session.get(models.User, winner_id)
        if winner is not None:
            bonus = 50
            await services.award_points(session, winner, bonus, minutes=3)
            await services.notify(
                session,
                winner.id,
                kind="battle",
                title="G'alaba! 🏆",
                body=f"Siz jangda yutdingiz va {bonus} ball qo'lga kiritdingiz.",
                link="peshqadam.html",
                icon="🏆",
            )
    for player_id in (battle.host_id, battle.guest_id):
        if player_id:
            await services.bump_skill(session, player_id, "vocabulary", 2)

    await _log(
        session,
        battle.id,
        "finished",
        user.id,
        {"host_score": battle.host_score, "guest_score": battle.guest_score},
    )
    await session.commit()
    await session.refresh(battle)

    out = await _battle_out(session, battle, user)
    await hub.broadcast(
        channel_for_battle(battle.id),
        {"type": "battle.finished", "data": out.model_dump(mode="json")},
    )
    return out


@router.post("/{battle_id}/cancel", response_model=schemas.Message)
async def cancel_battle(
    battle_id: str,
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> schemas.Message:
    battle = await _require_member(session, battle_id, user)
    if battle.status == "finished":
        raise HTTPException(status_code=409, detail="Jang allaqachon tugagan.")
    battle.status = "cancelled"
    battle.finished_at = utcnow()
    await session.commit()
    await hub.broadcast(
        channel_for_battle(battle.id),
        {"type": "battle.cancelled", "data": {"battle_id": battle.id}},
    )
    return schemas.Message(detail="Jang bekor qilindi.")


@router.get("/{battle_id}/result")
async def battle_result(
    battle_id: str,
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    battle = await _require_member(session, battle_id, user)
    total_host = await session.scalar(
        select(func.count(models.BattleEvent.id)).where(
            models.BattleEvent.battle_id == battle.id,
            models.BattleEvent.kind == "answer",
            models.BattleEvent.user_id == battle.host_id,
        )
    )
    return {
        "battle_id": battle.id,
        "status": battle.status,
        "host_score": battle.host_score,
        "guest_score": battle.guest_score,
        "winner_id": battle.winner_id,
        "rounds_played": int(total_host or 0),
        "won": battle.winner_id == user.id,
        "draw": battle.status == "finished" and battle.winner_id is None,
    }
