"""The judges' feedback of 19 November 2026, as tests:

1. "Talk to a person" works end to end, and /api/health says when the help desk cannot take learners.
3. With no Gemini key at all, Mimi still answers from the course, with sources.
"""
import sys
from pathlib import Path

import pytest

from tests.test_channels_handoff import client  # noqa: F401  (fixture: temporary databases)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server"))


@pytest.fixture()
def keyless(monkeypatch):
    """No AI key anywhere, and the settings a fresh install has (gemini first, then offline)."""
    for name in ("GEMINI_API_KEYS", "GEMINI_API_KEY", "GOOGLE_API_KEY"):
        monkeypatch.setenv(name, "")
    monkeypatch.setenv("ABLEWAY_PROVIDERS", "gemini,local,offline")
    monkeypatch.setenv("ABLEWAY_OLLAMA_URL", "http://127.0.0.1:9")  # no local model either
    from tutor import Tutor

    return Tutor()


# ---------------------------------------------------------------- 1. the hand-over, end to end
def test_hand_over_to_a_person_end_to_end(client, monkeypatch):  # noqa: F811
    """The widget asks for a person; the tutor sees the ticket and the conversation; they talk live."""
    monkeypatch.delenv("CHANNELS_URL", raising=False)
    convo = [{"role": "user", "text": "Can I submit late?"}, {"role": "assistant", "text": "Within 5 days [1]."}]
    reply = client.post("/api/v1/escalations", json={"conversation": convo, "language": "en", "cloud": False,
                                                      "page": {"title": "Lesson", "url": "https://x.org/p.html#a"}})
    assert reply.status_code == 201, reply.text
    ticket = reply.json()["ticketId"]
    assert "/handoff/chat/" + ticket in reply.json()["chatUrl"]

    # The learner's chat page opens.
    assert client.get(f"/handoff/chat/{ticket}?lang=en").status_code == 200

    # The tutor signs in and sees the ticket with the conversation and where the learner is.
    client.post("/handoff/console/login", data={"password": "test-password"})
    assert ticket in [t["id"] for t in client.get("/handoff/api/tickets").json()["tickets"]]

    # They talk live: the learner writes, the tutor answers, both see both messages.
    with client.websocket_connect(f"/handoff/ws/{ticket}?role=learner") as learner:
        history = learner.receive_json()
        assert history["type"] == "history" and "Can I submit late?" in str(history)
        assert learner.receive_json()["type"] == "presence"
        with client.websocket_connect(f"/handoff/ws/{ticket}?role=tutor") as tutor:  # signed in above
            assert tutor.receive_json()["type"] == "history"
            assert tutor.receive_json() == {"type": "presence", "tutor": True, "learner": True}
            assert learner.receive_json()["tutor"] is True  # the learner sees that a tutor is here
            learner.send_json({"type": "chat", "text": "Hello, I need help"})
            assert learner.receive_json()["text"] == "Hello, I need help"
            assert tutor.receive_json()["text"] == "Hello, I need help"
            tutor.send_json({"type": "chat", "text": "Hi, I am your tutor"})
            # (The test client runs each connection on its own loop: the sender's copy is read first.)
            assert tutor.receive_json()["text"] == "Hi, I am your tutor"
            answer = learner.receive_json()
            assert (answer["role"], answer["text"]) == ("tutor", "Hi, I am your tutor")


def test_health_reports_the_help_desk(client):  # noqa: F811
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["help_desk"]["ok"] is True and health.json()["help_desk"]["waiting"] == 0


def test_health_fails_when_the_help_desk_cannot_take_learners(client, monkeypatch):  # noqa: F811
    from server.handoff import tickets

    def broken():
        raise OSError("database is locked")

    monkeypatch.setattr(tickets, "list_open", broken)
    health = client.get("/api/health")
    assert health.status_code == 503  # a health check restarts the service
    assert health.json()["help_desk"] == {"ok": False, "waiting": None, "telegram": "off", "error": "OSError"}


def test_try_again_after_a_failed_hand_over_tries_the_person_again():
    script = (Path(__file__).resolve().parents[1] / "module" / "db-assistant.js").read_text(encoding="utf-8")
    assert "retry: 'escalate'" in script and "if (failed && failed.retry === 'escalate')" in script


# ---------------------------------------------------------------- 3. no Gemini key
@pytest.mark.parametrize("question, lang, section", [
    ("What is the late submission policy?", "en", "Late Policy"),
    ("ዘግይቶ ማስገባት ይቻላል?", "am", "Course Overview"),
    ("Guyyaan galchuu hojii manaa yoom?", "om", "Resubmission"),
])
def test_without_a_gemini_key_answers_come_from_the_course(keyless, question, lang, section):
    answer = keyless.ask(question, lang)
    assert answer["provider"] == "offline"
    assert answer["grounded"] and section in answer["citations"][0]["title"]


def test_without_a_gemini_key_off_topic_is_still_refused(keyless):
    from tutor import TEXT

    answer = keyless.ask("Who won the World Cup?", "en")
    assert answer["grounded"] is False and answer["answer"] == TEXT["en"]["not_found"]


def test_without_a_gemini_key_the_web_api_works(keyless, monkeypatch):
    from fastapi.testclient import TestClient

    import server.main
    from server import tutor_api

    monkeypatch.setattr(tutor_api, "tutor", keyless)
    reply = TestClient(server.main.app).post("/api/v1/ask", json={"question": "Can I resubmit an assignment?", "language": "en"})
    assert reply.status_code == 200
    assert reply.json()["provider"] == "offline" and reply.json()["sources"]


# ---------------------------------------------------------------- 6. answers at the learner's level
def _fake_model(reply):
    from providers import Provider

    class Fake(Provider):
        name, label = "fake", "Fake model"

        def __init__(self):
            self.calls = []

        def status(self):
            return {"available": True, "detail": ""}

        def complete(self, system, messages, max_tokens=16000):
            self.calls.append(system)
            return reply

    return Fake()


@pytest.mark.parametrize("level, expected", [("simple", "simple mode"), ("detailed", "detailed answers"), ("standard", None)])
def test_answer_level_reaches_the_ai_with_the_same_sources(level, expected):
    from tutor import Tutor

    model = _fake_model("You may resubmit once within 5 days [1].")
    tutor = Tutor(chain=[model])
    answer = tutor.ask("Can I resubmit an assignment?", "en", simple=level == "simple", detailed=level == "detailed")
    assert answer["grounded"] and answer["citations"]  # every level cites the course
    system = model.calls[-1]
    for note in ("simple mode", "detailed answers"):
        assert (note in system) == (note == expected)


def test_detailed_offline_answer_quotes_more_of_the_section(keyless):
    short = keyless.ask("What is the late submission policy?", "en")
    long = keyless.ask("What is the late submission policy?", "en", detailed=True)
    assert long["citations"][0]["title"] == short["citations"][0]["title"]
    assert len(long["answer"]) >= len(short["answer"])


def test_the_api_takes_the_level():
    from server.tutor_api import validate

    assert validate({"question": "Hi", "level": "detailed"})[0]["detailed"] is True
    assert validate({"question": "Hi", "level": "simple"})[0]["simple"] is True
    plain = validate({"question": "Hi"})[0]
    assert plain["simple"] is False and plain["detailed"] is False
    assert validate({"question": "Hi", "simple": True})[0]["simple"] is True  # older clients still work
