"""The tutor's one-line summary on a new ticket, and that it respects the learner's consent."""
import sys
from pathlib import Path

from tests.test_channels_handoff import client  # noqa: F401  (fixture: temporary databases)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server"))

CONVERSATION = [
    {"role": "user", "text": "Who won the World Cup?"},
    {"role": "assistant", "text": "I could not find that in the course material I can see. You can rephrase the question, or ask a person for help."},
    {"role": "user", "text": "Can I get an extension on my week 3 test?"},
]


def offline_tutor(monkeypatch):
    monkeypatch.setenv("ABLEWAY_PROVIDERS", "offline")
    from tutor import Tutor

    return Tutor()


def test_summary_without_ai_names_the_last_question(monkeypatch):
    summary = offline_tutor(monkeypatch).summarise(CONVERSATION, cloud=True)
    assert summary.startswith("The learner asked: “Can I get an extension on my week 3 test?”")


def test_summary_says_when_mimi_could_not_answer(monkeypatch):
    summary = offline_tutor(monkeypatch).summarise(CONVERSATION[:2], cloud=True)
    assert "could not find it in the course" in summary


def test_cloud_ai_writes_the_summary_only_with_consent(monkeypatch):
    monkeypatch.setenv("ABLEWAY_PROVIDERS", "gemini,offline")
    monkeypatch.setenv("GEMINI_API_KEYS", "test-key-not-real")
    from tutor import Tutor

    tutor = Tutor()
    gemini = next(p for p in tutor.chain if p.name == "gemini")
    monkeypatch.setattr(gemini, "status", lambda: {"available": True, "detail": ""})
    monkeypatch.setattr(gemini, "complete", lambda *a, **k: "Learner wants an extension on the week 3 test; not in the course.")
    assert tutor.summarise(CONVERSATION, cloud=True).startswith("Learner wants an extension")
    assert tutor.summarise(CONVERSATION, cloud=False).startswith("The learner asked:")


def test_ticket_starts_with_the_summary(client):  # noqa: F811
    from server.handoff import tickets

    created = client.post("/handoff/tickets", json={"lang": "en", "summary": "Learner needs an extension.", "conversation": CONVERSATION}).json()
    first = tickets.messages(created["ticket_id"])[0]
    assert first["text"].startswith("In short: Learner needs an extension.")
    assert "Learner: Can I get an extension" in first["text"]


def test_ticket_shows_the_page_and_section_the_learner_is_on(client):  # noqa: F811
    """On Chrome for Android there is no screen sharing: the tutor sees where the learner is instead."""
    from server.handoff import tickets

    page = {"title": "The Future of the VA Industry", "section": "Artificial Intelligence and the Future of VA Work",
            "url": "https://example.org/pages/concept-with-navigation.html#artificial-intelligence-and-the-future-of-va-work"}
    ticket = client.post("/handoff/tickets", json={"lang": "en", "conversation": CONVERSATION, "page": page}).json()
    first = tickets.messages(ticket["ticket_id"])[0]["text"]
    assert first.startswith("Learner is on: The Future of the VA Industry > Artificial Intelligence")
    assert page["url"] in first

    bad = client.post("/handoff/tickets", json={"lang": "en", "page": {"title": "X", "url": "javascript:alert(1)"}}).json()
    assert "javascript:" not in tickets.messages(bad["ticket_id"])[0]["text"]
