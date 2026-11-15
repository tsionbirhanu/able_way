"""Nothing leaves the server without the learner's consent: SMS, /lite and the tutor itself."""
import sys
from pathlib import Path

from tests.test_channels_handoff import client  # noqa: F401  (fixture: temporary databases)

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server"))


def record_cloud(monkeypatch):
    from server.channels import core_client

    calls = []
    real = core_client.ask
    monkeypatch.setattr(core_client, "ask", lambda *a: calls.append(a[-1] if len(a) > 4 else False) or real(*a))
    return calls


def sms(client, number, text):  # noqa: F811
    return client.post("/sms/inbound", json={"from": number, "text": text}).text


def test_sms_first_question_stays_offline_and_explains_ai_on_once(client, monkeypatch):  # noqa: F811
    calls = record_cloud(monkeypatch)
    sms(client, "0911000001", "What is the late policy?")
    sms(client, "0911000001", "What is the late policy?")
    assert calls == [False, False]
    info = client.get("/sms/outbox", params={"to": "+251911000001"}).json()["messages"]
    assert [m["kind"] for m in info] == ["info"]  # said once, not on every question
    assert "AI ON" in info[0]["text"] and len(info[0]["text"]) <= 160


def test_sms_ai_on_and_off(client, monkeypatch):  # noqa: F811
    calls = record_cloud(monkeypatch)
    assert sms(client, "0911000002", "AI ON").startswith("AI answers on")
    sms(client, "0911000002", "What is the late policy?")
    assert sms(client, "0911000002", "ai off").startswith("AI answers off")
    sms(client, "0911000002", "What is the late policy?")
    assert calls == [True, False]


def test_lite_cloud_only_when_ticked(client, monkeypatch):  # noqa: F811
    calls = record_cloud(monkeypatch)
    page = client.get("/lite").text
    assert 'name="cloud"' in page and "checked" not in page.split('name="cloud"')[1].split(">")[0]
    client.post("/lite", data={"question": "What is the late policy?", "lang": "en"})
    client.post("/lite", data={"question": "What is the late policy?", "lang": "en", "cloud": "1"})
    assert calls == [False, True]


def test_tutor_without_consent_skips_cloud_providers(monkeypatch):
    monkeypatch.setenv("ABLEWAY_PROVIDERS", "gemini,offline")
    monkeypatch.setenv("GEMINI_API_KEYS", "test-key-not-real")
    from tutor import Tutor

    tutor = Tutor()
    gemini = next(p for p in tutor.chain if p.name == "gemini")
    monkeypatch.setattr(gemini, "complete", lambda *a, **k: (_ for _ in ()).throw(AssertionError("question left the server")))
    result = tutor.ask("What is the late submission policy?", "en", cloud=False)
    assert result["provider"] == "offline"


def test_api_cloud_false_is_passed_to_the_tutor():
    import app

    request, _ = app.validate({"question": "Hi", "cloud": False})
    assert request["cloud"] is False
    request, _ = app.validate({"question": "Hi"})
    assert request["cloud"] is True  # API clients that already have the learner's consent
