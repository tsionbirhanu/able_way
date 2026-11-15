"""Tests for the channels / handoff work (Person 3 + 4).

Run from the repo root:  python -m pytest tests/test_channels_handoff.py -q
Every test uses its own temporary database files and the stub answers in core_client.
"""
import asyncio
import sqlite3

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # Import first: starting the server reads .env files (the project's and the one a folder up),
    # and the test settings below must win over whatever a developer has in them.
    from server.main import app  # noqa: F401
    monkeypatch.setenv("CHANNELS_DB_PATH", str(tmp_path / "channels.db"))
    monkeypatch.setenv("ACCOMMODATIONS_DB_PATH", str(tmp_path / "accommodations.db"))
    monkeypatch.setenv("TUTOR_PASSWORD", "test-password")
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("CORE_ASK_IMPORT", raising=False)
    monkeypatch.delenv("CORE_ASK_URL", raising=False)
    from server.main import app

    test_client = TestClient(app)
    test_client.tmp = tmp_path
    return test_client


def test_lite_post_shows_answer_and_citation(client):
    assert client.get("/lite").status_code == 200
    page = client.post("/lite", data={"question": "What skills do I need?", "lang": "en"})
    assert page.status_code == 200
    assert "communication" in page.text
    assert "What This Means for Aspiring Virtual Assistants" in page.text  # citation
    assert "<script" not in page.text  # no JavaScript at all
    assert 'dir="auto"' in page.text


def test_lite_post_unknown_question_in_amharic(client):
    page = client.post("/lite", data={"question": "የአየር ሁኔታው እንዴት ነው?", "lang": "am"})
    assert page.status_code == 200
    assert '<html lang="am">' in page.text
    assert "አላውቅም" in page.text  # "I don't know"


def test_sms_inbound_reply_is_short(client):
    reply = client.post("/sms/inbound", headers={"Accept": "application/json"}, json={"from": "+251911000001", "text": "What skills do I need?"})
    assert reply.status_code == 200
    assert reply.json()["reply"] and len(reply.json()["reply"]) <= 160
    for text in ["HELP", "JOBS", "is AI the future? " * 40, "something unknown"]:
        body = client.post("/sms/inbound", headers={"Accept": "application/json"}, json={"from": "+251911000001", "text": text}).json()
        assert 0 < len(body["reply"]) <= 160
    assert client.post("/sms/inbound", headers={"Accept": "application/json"}, json={"text": "no sender"}).status_code == 400


def test_subscribe_then_run_alerts(client):
    number = "+251911000002"
    reply = client.post("/sms/inbound", headers={"Accept": "application/json"}, json={"from": number, "text": "SUB calendar"}).json()["reply"]
    assert "calendar" in reply
    first = client.post("/jobs/run-alerts").json()
    assert first["sent"] >= 1 and first["sms"] == first["sent"]
    outbox = client.get("/sms/outbox", params={"to": number}).json()["messages"]
    assert len(outbox) == first["sent"]
    assert all(len(m["text"]) < 300 for m in outbox)
    # Jobs already sent are not sent again; the next runs only deliver what is left.
    total = first["sent"]
    for _ in range(5):
        total += client.post("/jobs/run-alerts").json()["sent"]
    assert client.post("/jobs/run-alerts").json()["sent"] == 0
    assert len(client.get("/sms/outbox", params={"to": number}).json()["messages"]) == total
    # Unsubscribing stops alerts.
    client.post("/sms/inbound", headers={"Accept": "application/json"}, json={"from": number, "text": "UNSUB"})
    assert client.post("/jobs/run-alerts").json()["subscriptions"] == 0


def test_accommodation_stays_out_of_teacher_view(client):
    secret_support, secret_contact = "ZZ-sign-language-interpreter", "zz-private@example.org"
    done = client.post(
        "/accommodation",
        data={"job_text": "ZZ-secret-interview", "support": secret_support, "contact": secret_contact, "lang": "en"},
    )
    assert done.status_code == 200 and secret_support not in done.text

    # The same through the Telegram step-by-step flow.
    from server.channels import telegram_bot

    async def flow():
        for text in ["/accommodation", "ZZ-bot-interview", "ZZ-bot-support", "ZZ-bot-contact"]:
            await telegram_bot.handle_message(555, text)

    asyncio.run(flow())
    client.post("/lite", data={"question": "What skills do I need?", "lang": "en"})  # a normal question

    # Stored in the separate file...
    rows = sqlite3.connect(str(client.tmp / "accommodations.db")).execute(
        "SELECT job, support, contact, channel FROM accommodation_requests ORDER BY id").fetchall()
    assert [r[3] for r in rows] == ["web", "telegram"]
    assert rows[0][1] == secret_support and rows[1][1] == "ZZ-bot-support"

    # ...and nowhere in the teacher view or in channels.db.
    teacher = client.get("/teacher")
    assert teacher.status_code == 200 and "What skills do I need?" in teacher.text
    assert "ZZ-" not in teacher.text and "zz-private" not in teacher.text
    assert "ZZ-" not in client.get("/teacher/stats.json").text
    assert b"ZZ-" not in (client.tmp / "channels.db").read_bytes()
    assert b"zz-private" not in (client.tmp / "channels.db").read_bytes()


def test_question_log_is_anonymous(client):
    client.post("/sms/inbound", headers={"Accept": "application/json"}, json={"from": "+251911000003", "text": "Where is the cafeteria?"})
    conn = sqlite3.connect(str(client.tmp / "channels.db"))
    columns = [r[1] for r in conn.execute("PRAGMA table_info(question_log)")]
    assert columns == ["id", "question", "normalised", "lang", "channel", "matched", "asked_on"]
    row = conn.execute("SELECT question, channel, matched, asked_on FROM question_log").fetchone()
    assert row[:3] == ("Where is the cafeteria?", "sms", 0) and len(row[3]) == 10  # date only
    assert "Where is the cafeteria?" in client.get("/teacher").text  # listed under "I don't know"


def test_ticket_creation_and_chat(client):
    created = client.post("/handoff/tickets", json={"lang": "am", "topic": "help"})
    assert created.status_code == 201
    ticket_id = created.json()["ticket_id"]
    assert ticket_id and created.json()["chat_url"].startswith("/handoff/chat/" + ticket_id)
    chat = client.get(created.json()["chat_url"])
    assert chat.status_code == 200 and 'role="log"' in chat.text and 'aria-live="polite"' in chat.text
    assert client.get("/handoff/chat/does-not-exist").status_code == 404

    with client.websocket_connect("/handoff/ws/{}?role=learner".format(ticket_id)) as ws:
        assert ws.receive_json()["type"] == "history"
        assert ws.receive_json()["type"] == "presence"
        ws.send_json({"type": "chat", "text": "ሰላም"})
        message = ws.receive_json()
        assert (message["type"], message["role"], message["text"]) == ("chat", "learner", "ሰላም")

    # The tutor console needs the shared password.
    assert client.get("/handoff/api/tickets").status_code == 401
    assert client.post("/handoff/tickets/{}/close".format(ticket_id)).status_code == 401
    assert client.post("/handoff/console/login", data={"password": "wrong"}).status_code == 401
    client.post("/handoff/console/login", data={"password": "test-password"})
    assert [t["id"] for t in client.get("/handoff/api/tickets").json()["tickets"]] == [ticket_id]
    assert client.post("/handoff/tickets/{}/close".format(ticket_id)).json() == {"closed": True}
    assert client.get("/handoff/api/tickets").json()["tickets"] == []


def test_telegram_unknown_offers_human_and_remembers_language(client):
    from server.channels import telegram_bot

    async def talk():
        await telegram_bot.handle_message(777, "/lang am")
        unknown = await telegram_bot.handle_message(777, "የአየር ሁኔታው እንዴት ነው?")
        jobs = await telegram_bot.handle_message(777, "/jobs")
        return unknown, jobs

    unknown, jobs = asyncio.run(talk())
    assert "አላውቅም" in unknown[0] and "/human" in unknown[0]
    assert len(jobs) > 1


def test_server_starts_without_telegram_token(client):
    with client:  # runs startup and shutdown
        status = client.get("/telegram/status").json()
    assert status == {"configured": False, "running": False, "username": None, "mode": "polling"}


def test_sms_reply_is_plain_text_by_default(client):
    """The Track 3 brief: POST /sms/inbound {from, text} returns the reply as plain text, at most 160."""
    resp = client.post("/sms/inbound", json={"from": "0911000009", "text": "is AI the future? " * 30})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
    assert 0 < len(resp.text) <= 160


def test_sms_sender_is_stored_in_one_format(client):
    number = client.post("/sms/inbound", headers={"Accept": "application/json"}, json={"from": "0911 00 00 10", "text": "HELP"}).json()["to"]
    assert number == "+251911000010"


def test_ticket_carries_the_conversation(client):
    convo = [{"role": "user", "text": "When is the deadline?"}, {"role": "assistant", "text": "Seven days after it is assigned."}]
    ticket = client.post("/handoff/tickets", json={"lang": "en", "topic": "deadline", "conversation": convo}).json()
    from server.handoff import tickets
    saved = tickets.messages(ticket["ticket_id"])
    assert saved and saved[0]["role"] == "mimi"
    assert "When is the deadline?" in saved[0]["text"] and "Seven days" in saved[0]["text"]


def test_job_deadline_in_ethiopian_calendar_for_amharic():
    from server.channels.ethiopian import format_date
    assert format_date("2026-11-14", "am") == "5 ኅዳር 2019 ዓ.ም."
    assert format_date("2026-11-14", "en") == "14 November 2026"
