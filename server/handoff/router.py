"""/handoff - tickets, live chat over WebSocket, learner chat page, tutor console."""
import hashlib
import hmac
import json
import re

from fastapi import APIRouter, Form, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse

from server.channels.config import STATIC_DIR, public_base_url, tutor_password
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


# ------------------------------------------------------------------ tickets
@router.post("/tickets")
async def create_ticket(request: Request):
    """Create a ticket. Body is optional JSON: {"lang": "en"|"am", "topic": "...", "channel": "web"}.

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
    channel = re.sub(r"[^a-z0-9_-]", "", str(data.get("channel") or "web").lower()) or "web"
    lang = norm_lang(data.get("lang"))
    ticket_id = tickets.create_ticket(channel=channel, lang=lang, topic=str(data.get("topic") or ""))
    chat_path = "/handoff/chat/{}?lang={}".format(ticket_id, lang)
    return JSONResponse(
        {"ticket_id": ticket_id, "chat_url": chat_path, "ws_url": "/handoff/ws/" + ticket_id,
         "absolute_chat_url": public_base_url() + chat_path},
        status_code=201,
        headers={"Access-Control-Allow-Origin": "*"},
    )


@router.get("/start")
async def start_page(request: Request, lang: str = "en"):
    """No-JavaScript way in: a single button that creates a ticket."""
    return render(request, "handoff_start.html", lang)


@router.post("/start")
async def start_submit(lang: str = Form("en")):
    lang = norm_lang(lang)
    ticket_id = tickets.create_ticket(channel="web", lang=lang)
    return RedirectResponse("/handoff/chat/{}?lang={}".format(ticket_id, lang), status_code=303)


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


# ------------------------------------------------------------------ static files of this feature
_STATIC = {"handoff.js", "handoff_chat.js", "handoff_console.js", "handoff_screenshare.js",
           "handoff_console_screen.js"}


@router.get("/static/{name}", include_in_schema=False)
async def static_file(name: str):
    path = STATIC_DIR / name
    if name not in _STATIC or not path.is_file():
        return JSONResponse({"error": "not found"}, status_code=404)
    return FileResponse(path, media_type="text/javascript", headers={"Cache-Control": "no-cache"})
