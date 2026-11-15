"""Real SMS, free for development. Choose one with SMS_PROVIDER in .env:

    (empty)          no real SMS: replies are returned by POST /sms/inbound, alerts go to the outbox,
                     and the phone simulator at /sms/simulator shows both. The default.
    android          "SMS Gateway for Android" (open source, https://sms-gate.app): an Android phone
                     with a SIM card sends and receives the SMS. Free; each SMS costs what the SIM
                     plan charges (Ethio Telecom and Safaricom SMS packages are cheap).
    africastalking   Africa's Talking. Its sandbox is free, with a phone simulator in their dashboard.

Only the SMS text goes to the gateway. Nothing is logged here except the outcome (no number, no text).
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import time

import httpx

log = logging.getLogger("channels.sms_gateway")


def provider() -> str:
    return (os.environ.get("SMS_PROVIDER") or "").strip().lower()


def send(to: str, text: str) -> bool:
    """Send one SMS through the configured gateway. Never raises: False when not sent."""
    name = provider()
    try:
        if name == "android":
            return _send_android(to, text)
        if name == "africastalking":
            return _send_africastalking(to, text)
    except httpx.HTTPError as exc:
        log.warning("SMS not sent through %s: %s", name, type(exc).__name__)
    return False


# ------------------------------------------------------------------ SMS Gateway for Android
def _android_base() -> str:
    # Local mode: the phone's own address, for example http://192.168.1.20:8080.
    # Cloud mode: https://api.sms-gate.app/3rdparty/v1 (the phone connects to it; no network setup).
    return (os.environ.get("SMS_GATEWAY_URL") or "").strip().rstrip("/")


def _send_android(to: str, text: str) -> bool:
    base = _android_base()
    if not base:
        log.warning("SMS_PROVIDER=android but SMS_GATEWAY_URL is empty")
        return False
    path = "/messages" if "/3rdparty/" in base else "/message"  # cloud API vs the phone's local server
    resp = httpx.post(
        base + path,
        json={"textMessage": {"text": text}, "phoneNumbers": [to]},
        auth=(os.environ.get("SMS_GATEWAY_USER", ""), os.environ.get("SMS_GATEWAY_PASSWORD", "")),
        timeout=20,
    )
    ok = resp.status_code < 300
    if not ok:
        log.warning("SMS gateway refused the message (HTTP %s)", resp.status_code)
    return ok


def android_signature_ok(raw: bytes, signature: str | None, timestamp: str | None) -> bool:
    """Webhooks from the phone are signed (HMAC-SHA256 of the raw body followed by X-Timestamp)
    when a signing key is set in the app. With SMS_GATEWAY_SIGNING_KEY empty, nothing is checked."""
    key = (os.environ.get("SMS_GATEWAY_SIGNING_KEY") or "").strip()
    if not key:
        return True
    if not (signature and timestamp and timestamp.isdigit()) or abs(time.time() - int(timestamp)) > 300:
        return False
    expected = hmac.new(key.encode(), raw + timestamp.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature.lower())


# ------------------------------------------------------------------ Africa's Talking
def _send_africastalking(to: str, text: str) -> bool:
    username = (os.environ.get("AT_USERNAME") or "sandbox").strip()
    host = "api.sandbox.africastalking.com" if username == "sandbox" else "api.africastalking.com"
    data = {"username": username, "to": to, "message": text}
    sender = (os.environ.get("AT_SENDER_ID") or "").strip()
    if sender:
        data["from"] = sender
    resp = httpx.post(
        f"https://{host}/version1/messaging",
        data=data,
        headers={"apiKey": os.environ.get("AT_API_KEY", ""), "Accept": "application/json"},
        timeout=20,
    )
    ok = resp.status_code < 300
    if not ok:
        log.warning("Africa's Talking refused the message (HTTP %s)", resp.status_code)
    return ok
