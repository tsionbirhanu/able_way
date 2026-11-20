"""/handoff - tickets, live chat over WebSocket, learner chat page, tutor console."""
import hashlib
import hmac
import json
import re

from server.channels import webhook
from fastapi import APIRouter, Form, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse

from server.channels.config import STATIC_DIR, public_base_url, tutor_password
from server.channels.db import connect
from server.channels.strings import STRINGS, norm_lang
from server.channels.web import render

from . import hub, tickets

router = APIRouter(prefix="/handoff", tags=["handoff"])

COOKIE = "tutor_session"
# Strings the learner chat page needs in JavaScript.
CHAT_JS_KEYS = [k for k in STRINGS if k.startswith(("chat_", "share_"))]


# ------------------------------------------------------------------ tutor auth (one shared password)
def _session_value() -> str:
    return hmac.new(tutor_password().encode(), b"tutor-console", hashlib.sha256).hexdigest()


def is_tutor(cookies) -> bool:
    return hmac.compare_digest(cookies.get(COOKIE) or "", _session_value())


def conversation_summary(conversation, limit: int = 12) -> str:
    """The learner's chat with Mimi before asking for a person, as one readable message."""
    if not isinstance(conversation, list):
        return ""
    lines = []
    for turn in conversation[-limit:]:
        if not isinstance(turn, dict):
            continue
        text = " ".join(str(turn.get("text") or turn.get("content") or "").split())[:600]
        if text:
            who = "Learner" if turn.get("role") in ("user", "learner") else "Mimi"
            lines.append(f"{who}: {text}")
    return ("Conversation with Mimi before asking for help:\n" + "\n".join(lines)) if lines else ""


def page_line(page) -> str:
    """'Learner is on: <page> > <section> (<link>)', so the tutor can open the same place. Only an
    http(s) link is shown; anything else is dropped."""
    if not isinstance(page, dict):
        return ""
    clean = lambda v, n: " ".join(str(v or "").split())[:n]  # noqa: E731
    title, section, url = clean(page.get("title"), 160), clean(page.get("section"), 160), clean(page.get("url"), 400)
    if not re.match(r"https?://", url):
        url = ""
    where = " > ".join(p for p in (title, section) if p)
    if not where and not url:
        return ""
    return "Learner is on: " + (where or url) + (f" ({url})" if url and where else "")


# ------------------------------------------------------------------ tickets
@router.post("/tickets")
async def create_ticket(request: Request):
    """Create a ticket. Body is optional JSON: {"lang": "en"|"am", "topic": "...", "channel": "web",
    "conversation": [{"role": "user"|"assistant", "text": "..."}]}. The conversation so far is stored on
    the ticket, so the tutor sees what the learner already asked and was told.

    Sent as a "simple" cross-origin request by handoff.js, so the response allows any origin.
    """
    data = {}
    try:
        raw = await request.body()
        if raw:
            parsed = json.loads(raw)
            if isinstance(parsed, dict):
                data = parsed
    except ValueError:
        pass
    return JSONResponse(open_ticket(data), status_code=201, headers={"Access-Control-Allow-Origin": "*"})


def open_ticket(data: dict, base_url: str | None = None) -> dict:
    """Create a ticket from {"lang", "topic", "channel", "conversation", "summary", "page"} and return
    {"ticket_id", "chat_url", "ws_url", "absolute_chat_url"}. Used by POST /handoff/tickets and, in the
    same process, by the tutor's POST /api/v1/escalations ("Talk to a person" in the widget)."""
    channel = re.sub(r"[^a-z0-9_-]", "", str(data.get("channel") or "web").lower()) or "web"
    lang = norm_lang(data.get("lang"))
    ticket_id = tickets.create_ticket(channel=channel, lang=lang, topic=str(data.get("topic") or ""))
    summary = conversation_summary(data.get("conversation"))
    in_short = " ".join(str(data.get("summary") or "").split())[:300]
    if in_short:
        summary = f"In short: {in_short}\n\n{summary}" if summary else f"In short: {in_short}"
    where = page_line(data.get("page"))
    if where:
        summary = f"{where}\n\n{summary}" if summary else where
    if summary:
        tickets.add_message(ticket_id, "mimi", summary)
    webhook.send("ticket.opened", {"ticketId": ticket_id, "channel": channel, "lang": lang})
    chat_path = "/handoff/chat/{}?lang={}".format(ticket_id, lang)
    return {"ticket_id": ticket_id, "chat_url": chat_path, "ws_url": "/handoff/ws/" + ticket_id,
            "absolute_chat_url": (base_url or public_base_url()).rstrip("/") + chat_path}


@router.get("/start")
async def start_page(request: Request, lang: str = "en"):
    """No-JavaScript way in: a single button that creates a ticket."""
    return render(request, "handoff_start.html", lang)


@router.post("/start")
async def start_submit(lang: str = Form("en")):
    lang = norm_lang(lang)
    ticket_id = tickets.create_ticket(channel="web", lang=lang)
    return RedirectResponse("/handoff/chat/{}?lang={}".format(ticket_id, lang), status_code=303)


@router.get("/chat")
@router.get("/chat/")
async def chat_direct(request: Request, lang: str = "en", topic: str = ""):
    """Direct URL navigation or assistant redirection to live chat without an existing ticket ID."""
    lang = norm_lang(lang)
    ticket_id = tickets.create_ticket(channel="web", lang=lang, topic=topic)
    return RedirectResponse(f"/handoff/chat/{ticket_id}?lang={lang}", status_code=303)


@router.get("/chat/{ticket_id}")
async def chat_page(request: Request, ticket_id: str, lang: str = ""):
    ticket = tickets.get_ticket(ticket_id)
    lang = norm_lang(lang or (ticket or {}).get("lang"))
    if not ticket:
        return render(request, "handoff_chat.html", lang, status_code=404, ticket=None, js_config=None)
    js_config = {
        "ticketId": ticket_id,
        "lang": lang,
        "strings": {k: STRINGS[k].get(lang) or STRINGS[k]["en"] for k in CHAT_JS_KEYS},
    }
    return render(request, "handoff_chat.html", lang, ticket=ticket, js_config=js_config)


@router.post("/tickets/{ticket_id}/close")
async def close_ticket(request: Request, ticket_id: str):
    if not is_tutor(request.cookies):
        return JSONResponse({"error": "tutor login required"}, status_code=401)
    return {"closed": await hub.close(ticket_id)}


# ------------------------------------------------------------------ live chat + signaling
@router.websocket("/ws/{ticket_id}")
async def ticket_ws(ws: WebSocket, ticket_id: str, role: str = "learner"):
    role = "tutor" if role == "tutor" else "learner"
    ticket = tickets.get_ticket(ticket_id)
    await ws.accept()
    if not ticket or (role == "tutor" and not is_tutor(ws.cookies)):
        await ws.close(code=4404 if not ticket else 4401)
        return
    await ws.send_json({"type": "history", "messages": tickets.messages(ticket_id), "status": ticket["status"]})
    if ticket["status"] != "open":
        await ws.send_json({"type": "closed"})
        await ws.close()
        return
    hub.join(ticket_id, ws, role)
    await hub.broadcast(ticket_id, hub.presence(ticket_id))
    other = "learner" if role == "tutor" else "tutor"
    try:
        while True:
            try:
                msg = json.loads(await ws.receive_text())
            except ValueError:
                continue
            if not isinstance(msg, dict):
                continue
            kind = msg.get("type")
            if kind == "chat":
                await hub.post_message(ticket_id, role, str(msg.get("text") or ""))
            elif kind == "signal":
                # WebRTC signaling is relayed to the other side only and never stored.
                await hub.broadcast(ticket_id, {"type": "signal", "data": msg.get("data")}, only_role=other)
            elif kind == "share" and role == "learner":
                # Only the learner can announce that screen sharing started or stopped.
                state = "started" if msg.get("state") == "started" else "stopped"
                await hub.broadcast(ticket_id, {"type": "share", "state": state}, only_role="tutor")
    except WebSocketDisconnect:
        pass
    finally:
        hub.leave(ticket_id, ws)
        if role == "learner":
            await hub.broadcast(ticket_id, {"type": "share", "state": "stopped"}, only_role="tutor")
        await hub.broadcast(ticket_id, hub.presence(ticket_id))


# ------------------------------------------------------------------ tutor console
@router.get("/console")
async def console(request: Request):
    if not is_tutor(request.cookies):
        return render(request, "handoff_login.html", "en", error=False)
    return render(request, "handoff_console.html", "en")


@router.post("/console/login")
async def console_login(request: Request, password: str = Form("")):
    if not hmac.compare_digest(password.encode(), tutor_password().encode()):
        return render(request, "handoff_login.html", "en", status_code=401, error=True)
    resp = RedirectResponse("/handoff/console", status_code=303)
    resp.set_cookie(COOKIE, _session_value(), httponly=True, samesite="strict", max_age=12 * 3600)
    return resp


@router.post("/console/logout")
async def console_logout():
    resp = RedirectResponse("/handoff/console", status_code=303)
    resp.delete_cookie(COOKIE)
    return resp


@router.get("/api/tickets")
async def api_tickets(request: Request):
    if not is_tutor(request.cookies):
        return JSONResponse({"error": "tutor login required"}, status_code=401)
    return {"tickets": tickets.list_open()}


@router.get("/api/dashboard")
async def api_dashboard(request: Request):
    """Return questions log + open help-request tickets + teacher analytics + accommodation requests."""
    if not is_tutor(request.cookies):
        return JSONResponse({"error": "tutor login required"}, status_code=401)

    from server.channels.accommodation import list_requests as list_accommodations
    from server.teacher.router import stats as teacher_stats

    with connect() as c:
        c.executescript("""
            CREATE TABLE IF NOT EXISTS question_tutor_status (
                question_id INTEGER PRIMARY KEY,
                answered INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS ticket_schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id TEXT NOT NULL UNIQUE,
                method TEXT NOT NULL DEFAULT 'chat',
                note TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
        """)
        questions = c.execute(
            "SELECT q.id, q.question, q.lang, q.channel, q.matched, q.asked_on, "
            "COALESCE(s.answered, q.matched) AS answered "
            "FROM question_log q "
            "LEFT JOIN question_tutor_status s ON s.question_id = q.id "
            "ORDER BY q.id DESC LIMIT 100"
        ).fetchall()
        open_tickets = c.execute(
            "SELECT t.id, t.channel, t.lang, t.topic, t.created_at, "
            "(SELECT COUNT(*) FROM ticket_messages m WHERE m.ticket_id=t.id) AS message_count, "
            "(SELECT text FROM ticket_messages m WHERE m.ticket_id=t.id ORDER BY m.id DESC LIMIT 1) AS last_message, "
            "s.method AS schedule_method, s.note AS schedule_note "
            "FROM tickets t "
            "LEFT JOIN ticket_schedules s ON s.ticket_id = t.id "
            "WHERE t.status='open' ORDER BY t.created_at"
        ).fetchall()
        total_q = c.execute("SELECT COUNT(*) AS n FROM question_log").fetchone()["n"]
        ans_count = c.execute(
            "SELECT COUNT(*) AS n FROM question_log q "
            "LEFT JOIN question_tutor_status s ON s.question_id = q.id "
            "WHERE COALESCE(s.answered, q.matched) = 1"
        ).fetchone()["n"]
        stats = {
            "total_questions": total_q,
            "answered": ans_count,
            "unanswered": total_q - ans_count,
            "open_tickets": c.execute("SELECT COUNT(*) AS n FROM tickets WHERE status='open'").fetchone()["n"],
        }
    return {
        "stats": stats,
        "questions": [dict(q) for q in questions],
        "tickets": [dict(t) for t in open_tickets],
        "teacher": teacher_stats(),
        "accommodations": list_accommodations(),
    }


@router.post("/api/questions/{question_id}/mark")
async def mark_question(request: Request, question_id: int, answered: int = Form(1)):
    """Toggle answered/unanswered on a question log entry."""
    if not is_tutor(request.cookies):
        return JSONResponse({"error": "tutor login required"}, status_code=401)
    with connect() as c:
        c.execute(
            "INSERT INTO question_tutor_status (question_id, answered) VALUES (?, ?) "
            "ON CONFLICT(question_id) DO UPDATE SET answered=excluded.answered",
            (question_id, answered),
        )
    return {"ok": True, "id": question_id, "answered": answered}


@router.post("/api/tickets/{ticket_id}/schedule")
async def schedule_help(request: Request, ticket_id: str,
                        method: str = Form("chat"), note: str = Form("")):
    """Record how the tutor plans to help: chat / telegram / phone / other."""
    if not is_tutor(request.cookies):
        return JSONResponse({"error": "tutor login required"}, status_code=401)
    with connect() as c:
        c.execute(
            "INSERT INTO ticket_schedules (ticket_id, method, note) VALUES (?,?,?) "
            "ON CONFLICT(ticket_id) DO UPDATE SET method=excluded.method, note=excluded.note",
            (ticket_id, method[:20], note[:300])
        )
    return {"ok": True}


# ------------------------------------------------------------------ static files of this feature
_STATIC = {"handoff.js", "handoff_chat.js", "handoff_console.js", "handoff_screenshare.js",
           "handoff_console_screen.js"}


@router.get("/static/{name}", include_in_schema=False)
async def static_file(name: str):
    path = STATIC_DIR / name
    if name not in _STATIC or not path.is_file():
        return JSONResponse({"error": "not found"}, status_code=404)
    return FileResponse(path, media_type="text/javascript", headers={"Cache-Control": "no-cache"})
