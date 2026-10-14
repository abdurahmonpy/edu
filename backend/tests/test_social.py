"""Chat, leaderboard, battles, live events and realtime tests."""

from __future__ import annotations

import uuid

import pytest
from starlette.websockets import WebSocketDisconnect


# ===========================================================================
# chat
# ===========================================================================
def test_seeded_conversations_for_demo_user(client, demo_auth):
    response = client.get("/api/v1/chat/conversations", headers=demo_auth["headers"])
    assert response.status_code == 200
    titles = {item["title"] for item in response.json()}
    assert "Support Service" in titles
    assert any("Alomat" in title for title in titles)


def test_direct_conversation_roundtrip(client, fresh_user, demo_auth):
    headers = fresh_user["headers"]

    created = client.post(
        "/api/v1/chat/conversations",
        headers=headers,
        json={"kind": "direct", "member_ids": [demo_auth["user"]["id"]]},
    )
    assert created.status_code == 201, created.text
    conversation_id = created.json()["id"]

    # A 1:1 conversation must be reused, not duplicated.
    again = client.post(
        "/api/v1/chat/conversations",
        headers=headers,
        json={"kind": "direct", "member_ids": [demo_auth["user"]["id"]]},
    )
    assert again.json()["id"] == conversation_id

    sent = client.post(
        f"/api/v1/chat/conversations/{conversation_id}/messages",
        headers=headers,
        json={"body": "Salom! Darslar qanday ketyapti?"},
    )
    assert sent.status_code == 201, sent.text
    assert sent.json()["is_mine"] is True
    assert sent.json()["body"] == "Salom! Darslar qanday ketyapti?"

    history = client.get(
        f"/api/v1/chat/conversations/{conversation_id}/messages", headers=headers
    ).json()
    assert len(history) >= 1
    assert history[-1]["id"] == sent.json()["id"]


def test_direct_conversation_requires_exactly_one_peer(client, fresh_user):
    response = client.post(
        "/api/v1/chat/conversations",
        headers=fresh_user["headers"],
        json={"kind": "direct", "member_ids": []},
    )
    assert response.status_code == 422


def test_bot_conversation_replies_automatically(client, fresh_user):
    headers = fresh_user["headers"]
    conversations = client.get("/api/v1/chat/conversations", headers=headers).json()
    bot = next(item for item in conversations if "Alomat" in item["title"])

    client.post(
        f"/api/v1/chat/conversations/{bot['id']}/messages",
        headers=headers,
        json={"body": "Present Perfect nima?"},
    )
    history = client.get(
        f"/api/v1/chat/conversations/{bot['id']}/messages", headers=headers
    ).json()
    assert len(history) >= 2
    assert history[-1]["sender_id"] is None  # bot message
    assert "Alomat" in (history[-1]["sender_name"] or "")


def test_unread_count_and_mark_read(client, fresh_user, demo_auth):
    headers = fresh_user["headers"]
    conversation = client.post(
        "/api/v1/chat/conversations",
        headers=headers,
        json={"kind": "direct", "member_ids": [demo_auth["user"]["id"]]},
    ).json()

    # The peer writes; our unread counter must move.
    client.post(
        f"/api/v1/chat/conversations/{conversation['id']}/messages",
        headers=demo_auth["headers"],
        json={"body": "Javob yozing"},
    )

    unread = client.get("/api/v1/chat/unread-count", headers=headers).json()
    assert unread["unread"] >= 1

    client.post(f"/api/v1/chat/conversations/{conversation['id']}/read", headers=headers)
    listing = client.get("/api/v1/chat/conversations", headers=headers).json()
    mine = next(item for item in listing if item["id"] == conversation["id"])
    assert mine["unread_count"] == 0


def test_chat_requires_authentication(client):
    assert client.get("/api/v1/chat/conversations").status_code == 401


def test_message_validation(client, fresh_user):
    headers = fresh_user["headers"]
    conversation = client.get("/api/v1/chat/conversations", headers=headers).json()[0]
    empty = client.post(
        f"/api/v1/chat/conversations/{conversation['id']}/messages",
        headers=headers,
        json={"body": ""},
    )
    assert empty.status_code == 422


# ===========================================================================
# leaderboard
# ===========================================================================
def test_leaderboard_is_ranked_and_includes_me(client, demo_auth):
    response = client.get("/api/v1/leaderboard", headers=demo_auth["headers"])
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["entries"], "demo accounts should populate the leaderboard"
    scores = [entry["points"] for entry in body["entries"]]
    assert scores == sorted(scores, reverse=True)
    assert [entry["rank"] for entry in body["entries"]] == list(
        range(1, len(body["entries"]) + 1)
    )
    assert body["me"] is not None
    assert body["me"]["is_me"] is True


def test_leaderboard_weekly_scope(client, demo_auth):
    response = client.get(
        "/api/v1/leaderboard?period=week", headers=demo_auth["headers"]
    )
    assert response.status_code == 200
    assert response.json()["period"] == "week"


def test_leaderboard_level_filter(client, demo_auth):
    response = client.get(
        "/api/v1/leaderboard?level=starter", headers=demo_auth["headers"]
    )
    assert response.status_code == 200
    assert all(entry["level"] == "starter" for entry in response.json()["entries"])


# ===========================================================================
# battles
# ===========================================================================
def test_ai_battle_full_flow(client, fresh_user):
    headers = fresh_user["headers"]

    created = client.post(
        "/api/v1/battles", headers=headers, json={"mode": "ai", "topic": "grammar"}
    )
    assert created.status_code == 201, created.text
    battle = created.json()
    assert battle["status"] == "active"
    assert battle["is_host"] is True
    assert len(battle["questions"]) == battle["rounds"]
    assert all("correct_index" not in q for q in battle["questions"])

    stats_before = client.get("/api/v1/battles/stats", headers=headers).json()

    # Answer every round correctly using the server's grading.
    for index in range(battle["rounds"]):
        response = client.post(
            f"/api/v1/battles/{battle['id']}/answer",
            headers=headers,
            json={"round_index": index, "correct": True, "answer_index": 0},
        )
        assert response.status_code == 200, response.text

    finished = client.post(f"/api/v1/battles/{battle['id']}/finish", headers=headers)
    assert finished.status_code == 200, finished.text
    result = finished.json()
    assert result["status"] == "finished"
    assert result["finished_at"] is not None

    stats_after = client.get("/api/v1/battles/stats", headers=headers).json()
    assert stats_after["played"] == stats_before["played"] + 1
    assert stats_after["won"] + stats_after["lost"] + stats_after["drawn"] == stats_after["played"]


def test_duel_matchmaking_pairs_two_players(client, fresh_user, demo_auth):
    host = fresh_user["headers"]
    guest = demo_auth["headers"]

    created = client.post(
        "/api/v1/battles", headers=host, json={"mode": "duel", "topic": "vocabulary"}
    )
    assert created.status_code == 201, created.text
    battle = created.json()
    assert battle["status"] == "waiting"
    assert battle["guest"] is None

    joined = client.post(f"/api/v1/battles/{battle['id']}/join", headers=guest)
    assert joined.status_code == 200, joined.text
    assert joined.json()["status"] == "active"
    assert joined.json()["guest"]["id"] == demo_auth["user"]["id"]
    assert joined.json()["is_host"] is False

    # The host sees the pairing too.
    as_host = client.get(f"/api/v1/battles/{battle['id']}", headers=host).json()
    assert as_host["guest"]["id"] == demo_auth["user"]["id"]

    # Second joiner is rejected.
    third = client.post(f"/api/v1/battles/{battle['id']}/join", headers=host)
    assert third.status_code in {200, 409}


def test_battle_answer_updates_score_and_rejects_outsiders(client, fresh_user, demo_auth):
    headers = fresh_user["headers"]
    created = client.post(
        "/api/v1/battles", headers=headers, json={"mode": "ai", "topic": "mixed"}
    ).json()

    response = client.post(
        f"/api/v1/battles/{created['id']}/answer",
        headers=headers,
        json={"round_index": 0, "correct": True, "answer_index": 1},
    )
    assert response.status_code == 200
    assert response.json()["host_score"] >= 0

    blocked = client.post(
        f"/api/v1/battles/{created['id']}/answer",
        headers=demo_auth["headers"],
        json={"round_index": 0, "correct": True, "answer_index": 1},
    )
    assert blocked.status_code == 403

    out_of_range = client.post(
        f"/api/v1/battles/{created['id']}/answer",
        headers=headers,
        json={"round_index": 99, "correct": True, "answer_index": 0},
    )
    assert out_of_range.status_code == 422


def test_battle_history_and_result(client, fresh_user):
    headers = fresh_user["headers"]
    battle = client.post(
        "/api/v1/battles", headers=headers, json={"mode": "ai", "topic": "grammar"}
    ).json()
    client.post(f"/api/v1/battles/{battle['id']}/finish", headers=headers)

    history = client.get("/api/v1/battles/history", headers=headers)
    assert history.status_code == 200
    assert any(item["id"] == battle["id"] for item in history.json())

    result = client.get(f"/api/v1/battles/{battle['id']}/result", headers=headers)
    assert result.status_code == 200
    assert result.json()["status"] == "finished"


# ===========================================================================
# live events
# ===========================================================================
def test_events_upcoming_and_past(client, demo_auth):
    headers = demo_auth["headers"]

    upcoming = client.get("/api/v1/events?when=upcoming", headers=headers).json()
    past = client.get("/api/v1/events?when=past", headers=headers).json()
    assert upcoming, "seed data should provide upcoming events"
    assert past, "seed data should provide past events"
    assert all(event["is_past"] is False for event in upcoming)
    assert all(event["is_past"] is True for event in past)

    # Meeting links are hidden until the user registers.
    assert upcoming[0]["join_url"] is None
    assert upcoming[0]["meeting_id"]


def test_event_registration_reveals_join_url(client, fresh_user):
    headers = fresh_user["headers"]
    event = client.get("/api/v1/events?when=upcoming", headers=headers).json()[0]

    registered = client.post(f"/api/v1/events/{event['slug']}/register", headers=headers)
    assert registered.status_code == 200, registered.text
    assert registered.json()["status"] == "registered"
    assert registered.json()["registered_count"] >= 1

    refreshed = client.get(f"/api/v1/events/{event['slug']}", headers=headers).json()
    assert refreshed["is_registered"] is True
    assert refreshed["join_url"] is not None

    again = client.post(f"/api/v1/events/{event['slug']}/register", headers=headers)
    assert again.status_code == 200
    assert again.json()["registered_count"] == registered.json()["registered_count"]

    cancelled = client.delete(f"/api/v1/events/{event['slug']}/register", headers=headers)
    assert cancelled.status_code == 200


def test_cannot_register_for_past_event(client, fresh_user):
    headers = fresh_user["headers"]
    past = client.get("/api/v1/events?when=past", headers=headers).json()[0]
    response = client.post(f"/api/v1/events/{past['slug']}/register", headers=headers)
    assert response.status_code == 409


def test_event_week_overview(client, demo_auth):
    response = client.get("/api/v1/events/week", headers=demo_auth["headers"])
    assert response.status_code == 200
    assert "counts" in response.json()


# ===========================================================================
# realtime
# ===========================================================================
def test_notification_websocket_requires_a_token(client):
    with pytest.raises(WebSocketDisconnect), client.websocket_connect(
        "/api/v1/ws/notifications"
    ):
        pass


def test_notification_websocket_connects_and_pings(client, fresh_user):
    token = fresh_user["tokens"]["access_token"]
    with client.websocket_connect(f"/api/v1/ws/notifications?token={token}") as socket:
        hello = socket.receive_json()
        assert hello["type"] == "connected"
        assert hello["data"]["channel"].startswith("user:")

        socket.send_json({"type": "ping"})
        assert socket.receive_json()["type"] == "pong"


def test_chat_websocket_rejects_non_members(client, fresh_user, demo_auth):
    stranger = client.post(
        "/api/v1/auth/register",
        json={
            "email": f"stranger-{uuid.uuid4().hex[:8]}@englify.uz",
            "password": "TestParol123",
            "full_name": "Strange Person",
        },
    ).json()

    conversation = client.get(
        "/api/v1/chat/conversations", headers=demo_auth["headers"]
    ).json()[0]

    with pytest.raises(WebSocketDisconnect), client.websocket_connect(
        f"/api/v1/ws/chat/{conversation['id']}?token={stranger['access_token']}"
    ) as socket:
        socket.receive_json()


def test_chat_websocket_broadcasts_typing(client, fresh_user):
    token = fresh_user["tokens"]["access_token"]
    headers = fresh_user["headers"]
    conversation = client.get("/api/v1/chat/conversations", headers=headers).json()[0]

    with client.websocket_connect(
        f"/api/v1/ws/chat/{conversation['id']}?token={token}"
    ) as socket:
        assert socket.receive_json()["type"] == "connected"
        socket.send_json({"type": "typing", "data": {"user_id": fresh_user["user"]["id"]}})
        frame = socket.receive_json()
        assert frame["type"] == "typing"


def test_battle_websocket_streams_scores(client, fresh_user):
    headers = fresh_user["headers"]
    token = fresh_user["tokens"]["access_token"]
    battle = client.post(
        "/api/v1/battles", headers=headers, json={"mode": "ai", "topic": "grammar"}
    ).json()

    with client.websocket_connect(
        f"/api/v1/ws/battles/{battle['id']}?token={token}"
    ) as socket:
        assert socket.receive_json()["type"] == "connected"
        client.post(
            f"/api/v1/battles/{battle['id']}/answer",
            headers=headers,
            json={"round_index": 0, "correct": True, "answer_index": 0},
        )
        frame = socket.receive_json()
        assert frame["type"] == "battle.score"
        assert frame["data"]["battle_id"] == battle["id"]
