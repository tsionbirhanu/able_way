"""SMS channel without a real provider.

POST /sms/inbound  {from, text} -> the reply as plain text, at most 160 characters
                                    (JSON {"to", "reply"} instead when the caller sends Accept: application/json)
GET  /sms/simulator             -> a fake phone that talks to the webhook
GET  /sms/outbox?to=...         -> outbound messages (job alerts) for the simulator
"""
import asyncio
import json

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse

from server.teacher.question_log import log_question

from . import core_client, sms_gateway
from .config import STATIC_DIR
from .ethiopian import normalize_phone
from .db import connect, forget, get_consent, get_lang, set_consent, set_lang
from .strings import norm_lang, t
from .web import render

router = APIRouter(prefix="/sms", tags=["sms"])

SMS_LIMIT = 160  # one SMS, as the Track 3 brief requires: replies are at most this long


def fit_sms(text: str, limit: int = SMS_LIMIT) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def queue_sms(to_number: str, text: str, kind: str = "alert") -> None:
    """Send an SMS that is not a direct reply (job alerts, notices): through the real gateway when
    SMS_PROVIDER is set, and always into the outbox table, which the phone simulator shows."""
    with connect() as c:
        c.execute(
            "INSERT INTO sms_outbox (to_number, text, kind) VALUES (?,?,?)",
            (to_number, fit_sms(text), kind),
        )
    if sms_gateway.provider():
        sms_gateway.send(to_number, fit_sms(text))


# Extra keyword commands (JOBS, SUB, ...) register themselves here: word -> f(sender, arg, lang) -> str
COMMANDS = {}


async def handle_sms(sender: str, text: str) -> str:
    text = (text or "").strip()
    lang = get_lang("sms", sender)
    word, _, arg = text.partition(" ")
    word, arg = word.upper(), arg.strip()
    if not text or word == "HELP":
        return fit_sms(t(lang, "sms_help"))
    if word == "LANG":
        if arg.lower() not in ("am", "en", "amharic", "english"):
            return fit_sms(t(lang, "sms_lang_usage"))
        lang = norm_lang(arg)
        set_lang("sms", sender, lang)
        return fit_sms(t(lang, "sms_lang_set"))
    if word in ("FORGET", "DELETE"):
        forget("sms", sender)
        return fit_sms(t(lang, "sms_forgotten"))
    if word == "AI" and arg.upper() in ("ON", "OFF", ""):
        allowed = arg.upper() != "OFF"
        set_consent("sms", sender, allowed)
        return fit_sms(t(lang, "sms_consent_on" if allowed else "sms_consent_off"))
    if word in COMMANDS:
        return fit_sms(COMMANDS[word](sender, arg, lang))
    consent = get_consent("sms", sender)
    if consent is None:
        # First question from this number: answer from the course text (nothing leaves the server)
        # and say once, in a second SMS, how to allow AI answers. Not asked again after that.
        set_consent("sms", sender, False)
        queue_sms(sender, t(lang, "sms_consent_info"), kind="info")
    result = await asyncio.to_thread(core_client.ask, text, lang, "sms", True, consent is True)
    log_question(text, lang, "sms", result["matched"])  # no phone number is passed
    if not result["matched"]:
        return fit_sms(t(lang, "sms_dont_know"))
    reply = result["answer"]
    if result["citations"]:
        c = result["citations"][0]
        source = " (" + (c["heading"] or c["page"]) + ")"
        if len(reply) + len(source) <= SMS_LIMIT:
            reply += source
    return fit_sms(reply)


# ------------------------------------------------------------------ real gateways (free for development)
@router.post("/webhook/android")
async def webhook_android(request: Request):
    """SMS Gateway for Android posts {"event": "sms:received", "payload": {"sender", "message"}}.
    The reply goes back through the phone as a normal SMS."""
    raw = await request.body()
    if not sms_gateway.android_signature_ok(raw, request.headers.get("x-signature"), request.headers.get("x-timestamp")):
        return JSONResponse({"error": "bad signature"}, status_code=401)
    try:
        data = json.loads(raw or b"{}")
    except ValueError:
        return JSONResponse({"error": "expected JSON"}, status_code=400)
    payload = data.get("payload") or {}
    if data.get("event") != "sms:received" or not payload.get("message"):
        return {"ok": True, "ignored": data.get("event")}  # delivery reports and other events
    sender = normalize_phone(str(payload.get("sender") or payload.get("phoneNumber") or ""))
    if not sender:
        return JSONResponse({"error": "missing sender"}, status_code=400)
    reply = await handle_sms(sender, str(payload["message"])[:1000])
    sent = await asyncio.to_thread(sms_gateway.send, sender, reply)
    return {"ok": True, "sent": sent}


@router.post("/webhook/africastalking")
async def webhook_africastalking(request: Request):
    """Africa's Talking posts the incoming SMS form-encoded (from, to, text, date, id). The reply is
    sent with their messaging API (free in the sandbox)."""
    form = dict(await request.form())
    sender = normalize_phone(str(form.get("from") or ""))
    if not sender:
        return JSONResponse({"error": "missing 'from'"}, status_code=400)
    reply = await handle_sms(sender, str(form.get("text") or "")[:1000])
    await asyncio.to_thread(sms_gateway.send, sender, reply)
    return PlainTextResponse("")


@router.post("/inbound")
async def inbound(request: Request):
    """Webhook. Accepts JSON {from, text} (or the same fields form-encoded)."""
    try:
        if "json" in request.headers.get("content-type", ""):
            data = await request.json()
        else:
            data = dict(await request.form())
    except Exception:
        data = None
    if not isinstance(data, dict):
        return JSONResponse({"error": "expected {from, text}"}, status_code=400)
    sender = normalize_phone(str(data.get("from") or ""))  # 09..., +251... -> one format
    if not sender:
        return JSONResponse({"error": "missing 'from'"}, status_code=400)
    reply = await handle_sms(sender, str(data.get("text") or "")[:1000])
    if "application/json" in request.headers.get("accept", ""):
        return {"to": sender, "reply": reply}
    # A gateway posts the learner's text and sends back whatever comes back: plain text.
    return PlainTextResponse(reply)


@router.get("/outbox")
async def outbox(to: str, after: int = 0):
    with connect() as c:
        rows = c.execute(
            "SELECT id, text, kind, created_at FROM sms_outbox WHERE to_number=? AND id>? ORDER BY id",
            (to, after),
        ).fetchall()
    return {"messages": [dict(r) for r in rows]}


@router.get("/simulator")
async def simulator(request: Request):
    return render(request, "sms_simulator.html", "en")


@router.get("/simulator.js", include_in_schema=False)
async def simulator_js():
    return FileResponse(STATIC_DIR / "sms_simulator.js", media_type="text/javascript")


# ------------------------------------------------------------------ jobs keywords
def _sms_jobs(sender, arg, lang):
    from server.jobs.store import jobs_list_sms

    return jobs_list_sms(lang)


def _sms_sub(sender, arg, lang):
    from server.jobs import alerts

    if not arg:
        return t(lang, "sms_sub_usage")
    return alerts.confirmation(alerts.subscribe("sms", sender, arg, lang), lang)


def _sms_unsub(sender, arg, lang):
    from server.jobs import alerts

    return t(lang, "unsubscribed" if alerts.unsubscribe("sms", sender) else "not_subscribed")


COMMANDS.update({"JOBS": _sms_jobs, "SUB": _sms_sub, "SUBSCRIBE": _sms_sub, "UNSUB": _sms_unsub,
                 "UNSUBSCRIBE": _sms_unsub})
