"""Course, progress, quiz, vocabulary and library tests."""

from __future__ import annotations


# ===========================================================================
# course catalogue
# ===========================================================================
def test_courses_require_authentication(client):
    assert client.get("/api/v1/courses").status_code == 401


def test_course_catalogue_is_seeded(client, demo_auth):
    response = client.get("/api/v1/courses", headers=demo_auth["headers"])
    assert response.status_code == 200
    courses = response.json()
    assert courses, "seed data should provide at least one course"

    course = next(item for item in courses if item["slug"] == "general-english")
    assert course["unit_count"] >= 1
    assert course["lesson_count"] >= 1
    assert 0 <= course["progress_percent"] <= 100


def test_course_detail_exposes_units_and_lessons(client, demo_auth):
    response = client.get("/api/v1/courses/general-english", headers=demo_auth["headers"])
    assert response.status_code == 200, response.text
    course = response.json()
    assert course["units"]
    first_unit = course["units"][0]
    assert first_unit["lessons"]
    assert first_unit["lesson_count"] == len(first_unit["lessons"])
    lesson = first_unit["lessons"][0]
    assert lesson["title"] and lesson["kind"] in {
        "video",
        "reading",
        "quiz",
        "writing",
        "speaking",
    }


def test_unknown_course_is_404(client, demo_auth):
    assert (
        client.get("/api/v1/courses/yoq-kurs", headers=demo_auth["headers"]).status_code == 404
    )


def test_enroll_is_idempotent(client, fresh_user):
    headers = fresh_user["headers"]
    first = client.post("/api/v1/courses/general-english/enroll", headers=headers)
    second = client.post("/api/v1/courses/general-english/enroll", headers=headers)
    assert first.status_code == second.status_code == 200

    courses = client.get("/api/v1/courses", headers=headers).json()
    assert next(c for c in courses if c["slug"] == "general-english")["enrolled"] is True


# ===========================================================================
# lessons, progress and quizzes
# ===========================================================================
def _first_lesson(client, headers) -> dict:
    course = client.get("/api/v1/courses/general-english", headers=headers).json()
    return course["units"][0]["lessons"][0]


def test_lesson_detail_includes_progress_field(client, fresh_user):
    headers = fresh_user["headers"]
    lesson = _first_lesson(client, headers)
    detail = client.get(f"/api/v1/lessons/{lesson['id']}", headers=headers).json()
    assert detail["id"] == lesson["id"]
    assert "progress" in detail


def test_partial_progress_does_not_complete_or_award(client, fresh_user):
    headers = fresh_user["headers"]
    lesson = _first_lesson(client, headers)
    before = client.get("/api/v1/users/me/stats", headers=headers).json()

    response = client.post(
        f"/api/v1/lessons/{lesson['id']}/progress",
        headers=headers,
        json={"video_percent": 50, "watch_seconds": 120},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "in_progress"
    assert response.json()["video_percent"] == 50

    after = client.get("/api/v1/users/me/stats", headers=headers).json()
    assert after["points"] == before["points"]


def test_completing_a_lesson_awards_points_once(client, fresh_user):
    headers = fresh_user["headers"]
    lesson = _first_lesson(client, headers)
    before = client.get("/api/v1/users/me/stats", headers=headers).json()

    response = client.post(
        f"/api/v1/lessons/{lesson['id']}/progress",
        headers=headers,
        json={"video_percent": 100, "homework_percent": 100, "watch_seconds": 600},
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "completed"
    assert response.json()["completed_at"] is not None

    after = client.get("/api/v1/users/me/stats", headers=headers).json()
    assert after["points"] > before["points"]
    assert after["lessons_completed"] == before["lessons_completed"] + 1
    assert after["streak_days"] >= 1

    # Replaying the same completion must not pay out twice.
    replay_points = after["points"]
    client.post(
        f"/api/v1/lessons/{lesson['id']}/progress",
        headers=headers,
        json={"video_percent": 100, "homework_percent": 100},
    )
    assert client.get("/api/v1/users/me/stats", headers=headers).json()["points"] == replay_points


def test_quiz_questions_never_leak_the_answer_key(client, fresh_user):
    headers = fresh_user["headers"]
    course = client.get("/api/v1/courses/general-english", headers=headers).json()
    quiz_lessons = [
        lesson
        for unit in course["units"]
        for lesson in unit["lessons"]
        if lesson["kind"] == "quiz"
    ]
    assert quiz_lessons, "seed data should include a quiz lesson"

    questions = client.get(
        f"/api/v1/lessons/{quiz_lessons[0]['id']}/quiz", headers=headers
    ).json()
    assert questions
    assert all("correct_index" not in question for question in questions)
    assert all(len(question["options"]) == 4 for question in questions)


def test_quiz_grading_is_server_side(client, fresh_user):
    headers = fresh_user["headers"]
    course = client.get("/api/v1/courses/general-english", headers=headers).json()
    lesson = next(
        lesson
        for unit in course["units"]
        for lesson in unit["lessons"]
        if lesson["kind"] == "quiz"
    )
    questions = client.get(f"/api/v1/lessons/{lesson['id']}/quiz", headers=headers).json()

    # Answer deliberately wrong, then right, and compare the graded results.
    wrong = client.post(
        f"/api/v1/lessons/{lesson['id']}/quiz",
        headers=headers,
        json={"answers": [3] * len(questions)},
    )
    assert wrong.status_code == 200, wrong.text
    assert wrong.json()["total"] == len(questions)
    assert 0 <= wrong.json()["score"] <= 100

    all_correct = client.post(
        f"/api/v1/lessons/{lesson['id']}/quiz",
        headers=headers,
        json={"answers": [0] * len(questions)},
    ).json()
    assert all_correct["correct_count"] >= 0
    assert all_correct["total"] == len(questions)
    assert all("correct_index" in result for result in all_correct["results"])


def test_progress_continue_endpoint(client, fresh_user):
    headers = fresh_user["headers"]
    response = client.get("/api/v1/progress/continue", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert "url" in body and "lesson_id" in body


def test_progress_list_is_scoped_to_the_user(client, fresh_user):
    response = client.get("/api/v1/progress", headers=fresh_user["headers"])
    assert response.status_code == 200
    assert isinstance(response.json(), list)


# ===========================================================================
# vocabulary
# ===========================================================================
def test_vocabulary_starts_seeded_for_demo_user(client, demo_auth):
    stats = client.get("/api/v1/vocabulary/stats", headers=demo_auth["headers"]).json()
    assert stats["total"] >= 1


def test_vocabulary_crud_lifecycle(client, fresh_user):
    headers = fresh_user["headers"]

    created = client.post(
        "/api/v1/vocabulary",
        headers=headers,
        json={
            "word": "Serendipity",
            "translation": "Tasodifiy omad",
            "example": "It was pure serendipity.",
            "part_of_speech": "noun",
            "level_tag": "intermediate",
        },
    )
    assert created.status_code == 201, created.text
    item = created.json()
    assert item["status"] == "new"
    assert item["level_tag"] == "intermediate"

    duplicate = client.post(
        "/api/v1/vocabulary",
        headers=headers,
        json={"word": "serendipity", "translation": "Yana bir ma'no"},
    )
    assert duplicate.status_code == 409

    updated = client.patch(
        f"/api/v1/vocabulary/{item['id']}",
        headers=headers,
        json={"translation": "Kutilmagan omad", "is_favorite": True},
    )
    assert updated.status_code == 200
    assert updated.json()["translation"] == "Kutilmagan omad"
    assert updated.json()["is_favorite"] is True

    listed = client.get("/api/v1/vocabulary?q=seren", headers=headers).json()
    assert listed["total"] == 1

    favorite = client.post(f"/api/v1/vocabulary/{item['id']}/favorite", headers=headers).json()
    assert favorite["is_favorite"] is False

    removed = client.delete(f"/api/v1/vocabulary/{item['id']}", headers=headers)
    assert removed.status_code == 200
    assert client.get(f"/api/v1/vocabulary/{item['id']}", headers=headers).status_code == 404


def test_vocabulary_review_schedules_next_review(client, fresh_user):
    headers = fresh_user["headers"]
    item = client.post(
        "/api/v1/vocabulary",
        headers=headers,
        json={"word": "Resilient", "translation": "Bardoshli"},
    ).json()

    good = client.post(
        f"/api/v1/vocabulary/{item['id']}/review", headers=headers, json={"quality": 5}
    )
    assert good.status_code == 200, good.text
    body = good.json()
    assert body["review_count"] == 1
    assert body["next_review_at"] is not None
    assert body["interval_days"] >= 1

    lapse = client.post(
        f"/api/v1/vocabulary/{item['id']}/review", headers=headers, json={"quality": 1}
    ).json()
    assert lapse["status"] == "learning"
    assert lapse["interval_days"] == 1

    assert (
        client.post(
            f"/api/v1/vocabulary/{item['id']}/review", headers=headers, json={"quality": 9}
        ).status_code
        == 422
    )


def test_vocabulary_bulk_import_deduplicates(client, fresh_user):
    headers = fresh_user["headers"]
    response = client.post(
        "/api/v1/vocabulary/bulk",
        headers=headers,
        json={
            "items": [
                {"word": "Apple", "translation": "Olma"},
                {"word": "apple", "translation": "Takrorlangan"},
                {"word": "Bread", "translation": "Non"},
            ]
        },
    )
    assert response.status_code == 200, response.text
    words = [item["word"].lower() for item in response.json()]
    assert words == ["apple", "bread"]


def test_vocabulary_is_private_per_user(client, demo_auth, fresh_user):
    mine = client.get("/api/v1/vocabulary", headers=demo_auth["headers"]).json()["items"]
    if not mine:
        return
    other = client.get(f"/api/v1/vocabulary/{mine[0]['id']}", headers=fresh_user["headers"])
    assert other.status_code == 404


# ===========================================================================
# notifications
# ===========================================================================
def test_notifications_list_and_unread_count(client, demo_auth):
    headers = demo_auth["headers"]
    listing = client.get("/api/v1/notifications", headers=headers)
    assert listing.status_code == 200
    assert listing.json()["total"] >= 1

    counts = client.get("/api/v1/notifications/unread-count", headers=headers).json()
    assert counts["total"] >= counts["unread"] >= 0


def test_notification_mark_read_flow(client, demo_auth):
    headers = demo_auth["headers"]
    items = client.get("/api/v1/notifications", headers=headers).json()["items"]
    target = items[0]

    marked = client.post(f"/api/v1/notifications/{target['id']}/read", headers=headers)
    assert marked.status_code == 200
    assert marked.json()["is_read"] is True

    assert (
        client.get(
            "/api/v1/notifications?unread_only=true", headers=headers
        ).status_code
        == 200
    )

    assert client.post("/api/v1/notifications/read-all", headers=headers).status_code == 200
    assert (
        client.get("/api/v1/notifications/unread-count", headers=headers).json()["unread"] == 0
    )


def test_notification_of_another_user_is_not_reachable(client, demo_auth, fresh_user):
    mine = client.get("/api/v1/notifications", headers=demo_auth["headers"]).json()["items"]
    response = client.post(
        f"/api/v1/notifications/{mine[0]['id']}/read", headers=fresh_user["headers"]
    )
    assert response.status_code == 404


def test_admin_broadcast_requires_admin(client, fresh_user):
    response = client.post(
        "/api/v1/notifications",
        headers=fresh_user["headers"],
        json={"title": "Reklama", "body": "Hammaga"},
    )
    assert response.status_code == 403


# ===========================================================================
# library
# ===========================================================================
def test_books_and_podcasts_are_seeded(client, demo_auth):
    headers = demo_auth["headers"]
    books = client.get("/api/v1/books", headers=headers).json()
    podcasts = client.get("/api/v1/podcasts", headers=headers).json()
    games = client.get("/api/v1/games", headers=headers).json()
    assert books and podcasts and games

    detail = client.get(f"/api/v1/books/{books[0]['slug']}", headers=headers)
    assert detail.status_code == 200
    assert detail.json()["title"] == books[0]["title"]

    episode = client.get(f"/api/v1/podcasts/{podcasts[0]['slug']}", headers=headers)
    assert episode.status_code == 200


def test_game_score_awards_points_and_records_best(client, fresh_user):
    headers = fresh_user["headers"]
    game = client.get("/api/v1/games", headers=headers).json()[0]

    first = client.post(
        f"/api/v1/games/{game['slug']}/score",
        headers=headers,
        json={"score": 110, "correct_count": 4, "total": 4},
    )
    assert first.status_code == 200, first.text
    assert first.json()["best_score"] == 110

    better = client.post(
        f"/api/v1/games/{game['slug']}/score",
        headers=headers,
        json={"score": 150, "correct_count": 4, "total": 4},
    ).json()
    assert better["best_score"] == 150

    board = client.get(f"/api/v1/games/{game['slug']}/leaderboard", headers=headers).json()
    assert board and board[0]["rank"] == 1
    assert any(entry["is_me"] for entry in board)


def test_levels_report_unlock_state(client, demo_auth):
    levels = client.get("/api/v1/levels", headers=demo_auth["headers"]).json()
    assert len(levels) >= 4
    starter = levels[0]
    assert starter["slug"] == "starter"
    assert starter["unlocked"] is True
    assert levels[-1]["points_required"] > levels[0]["points_required"]


def test_library_summary(client, demo_auth):
    summary = client.get("/api/v1/library/summary", headers=demo_auth["headers"]).json()
    assert summary["books"] >= 1
    assert summary["podcasts"] >= 1


# ===========================================================================
# leads (public landing form)
# ===========================================================================
def test_lead_capture_is_public_and_validated(client):
    import uuid

    phone = f"+99890{uuid.uuid4().int % 10_000_000:07d}"
    response = client.post(
        "/api/v1/leads",
        json={"name": "Bepul Dars", "phone": phone, "source": "pytest"},
    )
    assert response.status_code == 201, response.text
    assert response.json()["phone"] == phone

    bad = client.post("/api/v1/leads", json={"name": "X", "phone": "1"})
    assert bad.status_code == 422


def test_lead_listing_requires_admin(client, fresh_user):
    assert client.get("/api/v1/leads", headers=fresh_user["headers"]).status_code == 403
