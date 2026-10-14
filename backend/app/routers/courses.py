"""Courses, units, lessons, progress and quizzes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import models, schemas, services
from ..database import get_session
from ..deps import get_current_user
from ..utils import utcnow

router = APIRouter(tags=["courses"])


# ===========================================================================
# helpers
# ===========================================================================
async def _course_counts(
    session: AsyncSession, course_ids: list[str]
) -> tuple[dict[str, int], dict[str, int]]:
    """Return (unit_count, lesson_count) keyed by course id."""
    if not course_ids:
        return {}, {}

    unit_rows = (
        await session.execute(
            select(models.Unit.course_id, func.count(models.Unit.id))
            .where(models.Unit.course_id.in_(course_ids))
            .group_by(models.Unit.course_id)
        )
    ).all()
    units = {course_id: int(count) for course_id, count in unit_rows}

    lesson_rows = (
        await session.execute(
            select(models.Unit.course_id, func.count(models.Lesson.id))
            .join(models.Lesson, models.Lesson.unit_id == models.Unit.id)
            .where(models.Unit.course_id.in_(course_ids))
            .group_by(models.Unit.course_id)
        )
    ).all()
    lessons = {course_id: int(count) for course_id, count in lesson_rows}
    return units, lessons


async def _completed_lesson_ids(session: AsyncSession, user_id: str) -> set[str]:
    rows = (
        await session.execute(
            select(models.LessonProgress.lesson_id).where(
                models.LessonProgress.user_id == user_id,
                models.LessonProgress.status == "completed",
            )
        )
    ).all()
    return {lesson_id for (lesson_id,) in rows}


def _lesson_brief(lesson: models.Lesson) -> schemas.LessonBrief:
    return schemas.LessonBrief.model_validate(lesson)


def _unit_out(unit: models.Unit, lessons: list[schemas.LessonBrief]) -> schemas.UnitOut:
    """Build a UnitOut explicitly.

    Accessing ``unit.lessons`` would trigger a lazy load, which is illegal on an
    async session — the lessons are already fetched and passed in instead.
    """
    return schemas.UnitOut(
        id=unit.id,
        slug=unit.slug,
        code=unit.code,
        title=unit.title,
        description=unit.description,
        emoji=unit.emoji,
        order_index=unit.order_index,
        lessons=lessons,
        lesson_count=len(lessons),
    )


def _course_out(
    course: models.Course,
    *,
    units: list[schemas.UnitOut] | None = None,
    unit_count: int = 0,
    lesson_count: int = 0,
    enrolled: bool = False,
    progress_percent: float = 0.0,
) -> schemas.CourseOut:
    payload = {
        "id": course.id,
        "slug": course.slug,
        "title": course.title,
        "subtitle": course.subtitle,
        "description": course.description,
        "level": course.level,
        "cover_url": course.cover_url,
        "emoji": course.emoji,
        "color": course.color,
        "order_index": course.order_index,
        "unit_count": unit_count,
        "lesson_count": lesson_count,
        "enrolled": enrolled,
        "progress_percent": progress_percent,
    }
    if units is None:
        return schemas.CourseOut(**payload)
    return schemas.CourseDetail(**payload, units=units)


# ===========================================================================
# courses
# ===========================================================================
@router.get("/courses", response_model=list[schemas.CourseOut])
async def list_courses(
    level: str | None = Query(default=None),
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[schemas.CourseOut]:
    query = select(models.Course).where(models.Course.is_published.is_(True))
    if level:
        query = query.where(models.Course.level == level)
    courses = (await session.execute(query.order_by(models.Course.order_index))).scalars().all()

    course_ids = [course.id for course in courses]
    unit_counts, lesson_counts = await _course_counts(session, course_ids)

    enrollments = (
        await session.execute(
            select(models.Enrollment).where(models.Enrollment.user_id == user.id)
        )
    ).scalars().all()
    enrolled_ids = {row.course_id for row in enrollments}

    # Lessons the user completed, grouped per course.
    completed_rows = (
        await session.execute(
            select(models.Unit.course_id, models.LessonProgress.lesson_id)
            .join(models.Lesson, models.Lesson.id == models.LessonProgress.lesson_id)
            .join(models.Unit, models.Unit.id == models.Lesson.unit_id)
            .where(
                models.LessonProgress.user_id == user.id,
                models.LessonProgress.status == "completed",
                models.Unit.course_id.in_(course_ids or [""]),
            )
        )
    ).all()
    done_per_course: dict[str, int] = {}
    for course_id, _lesson_id in completed_rows:
        done_per_course[course_id] = done_per_course.get(course_id, 0) + 1

    result: list[schemas.CourseOut] = []
    for course in courses:
        total = lesson_counts.get(course.id, 0)
        done = done_per_course.get(course.id, 0)
        result.append(
            _course_out(
                course,
                unit_count=unit_counts.get(course.id, 0),
                lesson_count=total,
                enrolled=course.id in enrolled_ids,
                progress_percent=round(done / total * 100, 1) if total else 0.0,
            )
        )
    return result


@router.get("/courses/{slug}", response_model=schemas.CourseDetail)
async def get_course(
    slug: str,
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> schemas.CourseDetail:
    course = await session.scalar(select(models.Course).where(models.Course.slug == slug))
    if course is None or not course.is_published:
        raise HTTPException(status_code=404, detail="Kurs topilmadi.")

    units = (
        await session.execute(
            select(models.Unit)
            .where(models.Unit.course_id == course.id, models.Unit.is_published.is_(True))
            .order_by(models.Unit.order_index)
        )
    ).scalars().all()

    lessons = (
        await session.execute(
            select(models.Lesson)
            .join(models.Unit, models.Unit.id == models.Lesson.unit_id)
            .where(
                models.Unit.course_id == course.id,
                models.Lesson.is_published.is_(True),
            )
            .order_by(models.Unit.order_index, models.Lesson.order_index)
        )
    ).scalars().all()

    done = await _completed_lesson_ids(session, user.id)
    by_unit: dict[str, list[schemas.LessonBrief]] = {}
    for lesson in lessons:
        by_unit.setdefault(lesson.unit_id, []).append(_lesson_brief(lesson))

    unit_models = [_unit_out(unit, by_unit.get(unit.id, [])) for unit in units]

    enrollment = await session.scalar(
        select(models.Enrollment).where(
            models.Enrollment.user_id == user.id, models.Enrollment.course_id == course.id
        )
    )
    total = len(lessons)
    completed = len([lesson for lesson in lessons if lesson.id in done])

    return _course_out(
        course,
        units=unit_models,
        unit_count=len(units),
        lesson_count=total,
        enrolled=enrollment is not None,
        progress_percent=round(completed / total * 100, 1) if total else 0.0,
    )


@router.post("/courses/{slug}/enroll", response_model=schemas.Message)
async def enroll(
    slug: str,
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> schemas.Message:
    course = await session.scalar(select(models.Course).where(models.Course.slug == slug))
    if course is None:
        raise HTTPException(status_code=404, detail="Kurs topilmadi.")
    existing = await session.scalar(
        select(models.Enrollment).where(
            models.Enrollment.user_id == user.id, models.Enrollment.course_id == course.id
        )
    )
    if existing is None:
        session.add(models.Enrollment(user_id=user.id, course_id=course.id))
        await services.notify(
            session,
            user.id,
            kind="lesson",
            title=f"«{course.title}» kursiga yozildingiz",
            body="Birinchi darsni bugun boshlang!",
            link="/dashboard#darslar",
            icon="📚",
        )
        await session.commit()
    return schemas.Message(detail="Kursga yozildingiz.")


# ===========================================================================
# lessons
# ===========================================================================
@router.get("/lessons/{lesson_id}", response_model=schemas.LessonDetail)
async def get_lesson(
    lesson_id: str,
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> schemas.LessonDetail:
    lesson = await session.get(models.Lesson, lesson_id)
    if lesson is None or not lesson.is_published:
        raise HTTPException(status_code=404, detail="Dars topilmadi.")

    question_count = await session.scalar(
        select(func.count(models.QuizQuestion.id)).where(
            models.QuizQuestion.lesson_id == lesson.id
        )
    )
    progress = await session.scalar(
        select(models.LessonProgress).where(
            models.LessonProgress.user_id == user.id,
            models.LessonProgress.lesson_id == lesson.id,
        )
    )

    detail = schemas.LessonDetail.model_validate(lesson)
    detail.question_count = int(question_count or 0)
    if progress is not None:
        detail.progress = schemas.ProgressOut.model_validate(progress).model_dump()
    return detail


@router.get("/lessons/{lesson_id}/quiz", response_model=list[schemas.QuizQuestionPublic])
async def get_quiz(
    lesson_id: str,
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[schemas.QuizQuestionPublic]:
    """Questions without the answer key (safe to send to the client)."""
    await _require_lesson(session, lesson_id)
    rows = (
        await session.execute(
            select(models.QuizQuestion)
            .where(models.QuizQuestion.lesson_id == lesson_id)
            .order_by(models.QuizQuestion.order_index)
        )
    ).scalars().all()
    return [
        schemas.QuizQuestionPublic(
            id=row.id,
            prompt=row.prompt,
            options=list(row.options or []),
            order_index=row.order_index,
            points=row.points,
        )
        for row in rows
    ]


@router.post(
    "/lessons/{lesson_id}/progress",
    response_model=schemas.ProgressOut,
)
async def update_progress(
    lesson_id: str,
    payload: schemas.ProgressUpdate,
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> schemas.ProgressOut:
    lesson = await _require_lesson(session, lesson_id)
    progress = await session.scalar(
        select(models.LessonProgress).where(
            models.LessonProgress.user_id == user.id,
            models.LessonProgress.lesson_id == lesson.id,
        )
    )
    if progress is None:
        progress = models.LessonProgress(
            user_id=user.id,
            lesson_id=lesson.id,
            status="in_progress",
            video_percent=0.0,
            homework_percent=0.0,
            watch_seconds=0,
        )
        session.add(progress)

    data = payload.model_dump(exclude_unset=True)
    first_completion = False

    for field in ("video_percent", "homework_percent", "watch_seconds", "score"):
        if field in data and data[field] is not None:
            setattr(progress, field, data[field])

    if "status" in data and data["status"]:
        progress.status = data["status"]
    elif (
        (progress.video_percent or 0.0) >= 100
        and (progress.homework_percent or 0.0) >= 100
        and progress.status != "completed"
    ):
        progress.status = "completed"

    if progress.status == "completed" and progress.completed_at is None:
        progress.completed_at = utcnow()
        first_completion = True
    if progress.status != "completed":
        progress.completed_at = None

    if first_completion:
        await services.award_points(
            session,
            user,
            lesson.xp_reward,
            minutes=max(lesson.duration_sec // 60, 1),
            lessons_completed=1,
        )
        await services.bump_skill(session, user.id, _skill_for(lesson), 5)
        await _advance_enrollment(session, user.id, lesson)

    await session.commit()
    await session.refresh(progress)
    return schemas.ProgressOut.model_validate(progress)


@router.post("/lessons/{lesson_id}/quiz", response_model=schemas.QuizSubmitResponse)
async def submit_quiz(
    lesson_id: str,
    payload: schemas.QuizSubmitRequest,
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> schemas.QuizSubmitResponse:
    lesson = await _require_lesson(session, lesson_id)
    questions = (
        await session.execute(
            select(models.QuizQuestion)
            .where(models.QuizQuestion.lesson_id == lesson.id)
            .order_by(models.QuizQuestion.order_index)
        )
    ).scalars().all()
    if not questions:
        raise HTTPException(status_code=400, detail="Bu darsda test savollari yo'q.")

    results: list[dict] = []
    points = 0
    correct_count = 0
    for index, question in enumerate(questions):
        given = payload.answers[index] if index < len(payload.answers) else None
        is_correct = given is not None and int(given) == int(question.correct_index)
        if is_correct:
            correct_count += 1
            points += question.points
        results.append(
            {
                "question_id": question.id,
                "given_index": given,
                "correct_index": question.correct_index,
                "is_correct": is_correct,
                "explanation": question.explanation,
            }
        )

    total = len(questions)
    score = round(correct_count / total * 100, 1)

    session.add(
        models.QuizAttempt(
            user_id=user.id,
            lesson_id=lesson.id,
            correct_count=correct_count,
            total=total,
            score=score,
            points_earned=points,
            answers=payload.answers,
        )
    )

    if points:
        await services.award_points(session, user, points)
    await services.bump_skill(session, user.id, _skill_for(lesson), score / 20)

    # Feed the quiz result back into lesson progress (homework side).
    progress = await session.scalar(
        select(models.LessonProgress).where(
            models.LessonProgress.user_id == user.id,
            models.LessonProgress.lesson_id == lesson.id,
        )
    )
    if progress is None:
        progress = models.LessonProgress(
            user_id=user.id,
            lesson_id=lesson.id,
            status="in_progress",
            video_percent=0.0,
            homework_percent=0.0,
            watch_seconds=0,
        )
        session.add(progress)
    progress.score = score
    progress.homework_percent = max(progress.homework_percent or 0.0, score)
    if (progress.video_percent or 0.0) >= 100 and (progress.homework_percent or 0.0) >= 100:
        progress.status = "completed"
        progress.completed_at = progress.completed_at or utcnow()

    await session.commit()
    return schemas.QuizSubmitResponse(
        correct_count=correct_count,
        total=total,
        score=score,
        points_earned=points,
        total_points=user.points,
        results=results,
    )


# ===========================================================================
# progress overview
# ===========================================================================
@router.get("/progress", response_model=list[schemas.ProgressOut])
async def my_progress(
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[schemas.ProgressOut]:
    rows = (
        await session.execute(
            select(models.LessonProgress)
            .where(models.LessonProgress.user_id == user.id)
            .order_by(models.LessonProgress.updated_at.desc())
        )
    ).scalars().all()
    return [schemas.ProgressOut.model_validate(row) for row in rows]


@router.get("/progress/continue")
async def continue_lesson(
    user: models.User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """The lesson the «Darsni davom ettirish» button should open."""
    row = await session.scalar(
        select(models.LessonProgress)
        .where(
            models.LessonProgress.user_id == user.id,
            models.LessonProgress.status != "completed",
        )
        .order_by(models.LessonProgress.updated_at.desc())
    )
    if row is not None:
        lesson = await session.get(models.Lesson, row.lesson_id)
        if lesson is not None:
            return {
                "lesson_id": lesson.id,
                "title": lesson.title,
                "url": f"dars.html?lesson={lesson.id}",
                "progress": schemas.ProgressOut.model_validate(row).model_dump(),
            }

    # No history yet -> first published lesson in the catalogue.
    lesson = await session.scalar(
        select(models.Lesson)
        .join(models.Unit, models.Unit.id == models.Lesson.unit_id)
        .where(models.Lesson.is_published.is_(True), models.Unit.is_published.is_(True))
        .order_by(models.Unit.order_index, models.Lesson.order_index)
    )
    if lesson is None:
        return {"lesson_id": None, "title": None, "url": None, "progress": None}
    return {
        "lesson_id": lesson.id,
        "title": lesson.title,
        "url": f"dars.html?lesson={lesson.id}",
        "progress": None,
    }


# ===========================================================================
# internals
# ===========================================================================
async def _require_lesson(session: AsyncSession, lesson_id: str) -> models.Lesson:
    lesson = await session.get(models.Lesson, lesson_id)
    if lesson is None:
        raise HTTPException(status_code=404, detail="Dars topilmadi.")
    return lesson


def _skill_for(lesson: models.Lesson) -> str:
    return {
        "video": "listening",
        "reading": "reading",
        "quiz": "grammar",
        "writing": "writing",
        "speaking": "listening",
    }.get(lesson.kind, "grammar")


async def _advance_enrollment(
    session: AsyncSession, user_id: str, lesson: models.Lesson
) -> None:
    unit = await session.get(models.Unit, lesson.unit_id)
    if unit is None:
        return
    enrollment = await session.scalar(
        select(models.Enrollment).where(
            models.Enrollment.user_id == user_id,
            models.Enrollment.course_id == unit.course_id,
        )
    )
    if enrollment is None:
        enrollment = models.Enrollment(user_id=user_id, course_id=unit.course_id)
        session.add(enrollment)

    next_lesson = await session.scalar(
        select(models.Lesson)
        .join(models.Unit, models.Unit.id == models.Lesson.unit_id)
        .where(
            models.Unit.course_id == unit.course_id,
            models.Lesson.is_published.is_(True),
            models.Lesson.order_index > lesson.order_index,
        )
        .order_by(models.Unit.order_index, models.Lesson.order_index)
        .limit(1)
    )
    enrollment.current_lesson_id = next_lesson.id if next_lesson else None
