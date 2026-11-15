"""Real SMS gateways (with fake HTTP), deleting a learner's data, and the accommodation staff page."""
import hashlib
import hmac
import json
import time

import pytest

from tests.test_channels_handoff import client  # noqa: F401  (fixture: temporary databases)


@pytest.fixture()
def gateway(monkeypatch):
    from server.channels import sms_gateway

    posts = []

    class Response:
        status_code = 200

    def fake_post(url, **kwargs):
        posts.append({"url": url, **kwargs})
        return Response()

    monkeypatch.setattr(sms_gateway.httpx, "post", fake_post)
    return posts


def test_android_gateway_receives_and_replies(client, gateway, monkeypatch):  # noqa: F811
    monkeypatch.setenv("SMS_PROVIDER", "android")
    monkeypatch.setenv("SMS_GATEWAY_URL", "http://192.168.1.20:8080")
    monkeypatch.setenv("SMS_GATEWAY_USER", "sms")
    monkeypatch.setenv("SMS_GATEWAY_PASSWORD", "secret")
    event = {"event": "sms:received", "payload": {"sender": "0911000010", "message": "What is the late policy?"}}
    assert client.post("/sms/webhook/android", json=event).json()["ok"] is True
    replies = [p for p in gateway if p["url"] == "http://192.168.1.20:8080/message"]
    assert replies and replies[-1]["json"]["phoneNumbers"] == ["+251911000010"]
    assert len(replies[-1]["json"]["textMessage"]["text"]) <= 160
    assert replies[-1]["auth"] == ("sms", "secret")


def test_android_cloud_mode_uses_messages_path(client, gateway, monkeypatch):  # noqa: F811
    monkeypatch.setenv("SMS_PROVIDER", "android")
    monkeypatch.setenv("SMS_GATEWAY_URL", "https://api.sms-gate.app/3rdparty/v1")
    from server.channels import sms_gateway

    assert sms_gateway.send("+251911000011", "hi")
    assert gateway[-1]["url"] == "https://api.sms-gate.app/3rdparty/v1/messages"


def test_android_signature_is_checked_when_a_key_is_set(client, gateway, monkeypatch):  # noqa: F811
    monkeypatch.setenv("SMS_PROVIDER", "android")
    monkeypatch.setenv("SMS_GATEWAY_URL", "http://phone:8080")
    monkeypatch.setenv("SMS_GATEWAY_SIGNING_KEY", "k3y")
    body = json.dumps({"event": "sms:received", "payload": {"sender": "0911000012", "message": "HELP"}}).encode()
    assert client.post("/sms/webhook/android", content=body).status_code == 401
    ts = str(int(time.time()))
    sig = hmac.new(b"k3y", body + ts.encode(), hashlib.sha256).hexdigest()
    ok = client.post("/sms/webhook/android", content=body, headers={"X-Signature": sig, "X-Timestamp": ts})
    assert ok.status_code == 200


def test_africastalking_sandbox(client, gateway, monkeypatch):  # noqa: F811
    monkeypatch.setenv("SMS_PROVIDER", "africastalking")
    monkeypatch.setenv("AT_USERNAME", "sandbox")
    monkeypatch.setenv("AT_API_KEY", "test")
    client.post("/sms/webhook/africastalking", data={"from": "+251911000013", "text": "HELP", "to": "12345"})
    sent = gateway[-1]
    assert sent["url"] == "https://api.sandbox.africastalking.com/version1/messaging"
    assert sent["data"]["to"] == "+251911000013" and sent["headers"]["apiKey"] == "test"


def test_no_provider_sends_nothing(client, gateway, monkeypatch):  # noqa: F811
    monkeypatch.delenv("SMS_PROVIDER", raising=False)
    assert client.post("/sms/inbound", json={"from": "0911000014", "text": "HELP"}).status_code == 200
    assert gateway == []


def test_sms_forget_deletes_the_number(client):  # noqa: F811
    from server.channels.db import connect, get_consent

    client.post("/sms/inbound", json={"from": "0911000015", "text": "AI ON"})
    client.post("/sms/inbound", json={"from": "0911000015", "text": "SUB calendar"})
    assert client.post("/sms/inbound", json={"from": "0911000015", "text": "FORGET"}).text.startswith("Deleted")
    assert get_consent("sms", "+251911000015") is None
    with connect() as c:
        assert c.execute("SELECT COUNT(*) FROM subscriptions WHERE address=?", ("+251911000015",)).fetchone()[0] == 0


def test_telegram_forget(client):  # noqa: F811
    import asyncio

    from server.channels import telegram_bot
    from server.channels.db import get_consent, get_lang, set_consent

    set_consent("telegram", "700", True)
    asyncio.run(telegram_bot.handle_message(700, "/lang am"))
    replies = asyncio.run(telegram_bot.handle_message(700, "/forget"))
    assert "ተሰርዟል" in replies[0]
    assert get_consent("telegram", "700") is None and get_lang("telegram", "700") == "en"


def test_accommodation_requests_reach_a_person(client):  # noqa: F811
    client.post("/accommodation", data={"job_text": "Test job", "support": "Sign language interpreter", "contact": "0911000016", "lang": "en"})
    assert "/handoff/console" in str(client.get("/accommodation/requests", follow_redirects=False).headers.get("location"))
    client.post("/handoff/console/login", data={"password": "test-password"})
    page = client.get("/accommodation/requests").text
    assert "Sign language interpreter" in page
    request_id = page.split("/accommodation/requests/")[1].split("/")[0]
    client.post(f"/accommodation/requests/{request_id}/done")
    assert "Sign language interpreter" not in client.get("/accommodation/requests").text
