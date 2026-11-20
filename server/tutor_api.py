"""The tutor's web API and the site's pages, as part of the one FastAPI server (server/main.py).

    POST /api/ask, /api/v1/ask  {"question", "lang"|"language", "simple", "level", "history", "session_id",
                                 "context": {"page", "course", "lesson", "section"}, "intent",
                                 "voice", "detect_switch", "cloud"}
    POST /api/v1/content        the host's lessons to index ({"chunks": [{title, url, text}]})
    POST /api/v1/escalations    {conversation, language, page} -> {ticketId, chatUrl}: a help-desk ticket
    POST /api/session           {"session_id"?, "lang"?} -> {"session_id", "lang"}
    POST /api/tts               {"text", "lang": "en"|"am", "cache"} -> audio (503: use the browser voice)
    POST /api/transcribe        raw audio/wav body, ?lang=am|en&purpose=language_choice -> {"text"}
    GET  /api/health            providers, indexed content, speech status
    GET  /openapi.yaml, /docs   the API contract and its interactive page
    GET  /<file>                the site: index.html, pages/, assets/, module/, demo/, data/jobs.json

Until November 2026 this was a separate standard-library server (server/app.py, port 8001); the
behaviour, limits and responses are the same. `python server/app.py` still starts everything.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))  # tutor.py and its neighbours import each other as top-level modules


def load_env(path: Path) -> None:
    """Read KEY=VALUE lines without overriding the real environment (the first file read wins)."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))


load_env(ROOT / ".env")  # the one settings file
load_env(HERE / ".env")  # older location, still read
load_env(ROOT.parent / ".env")  # or one folder up, outside the project (and so outside git entirely)

from sessions import Sessions  # noqa: E402
from speech import MAX_AUDIO_BYTES, MAX_TTS_TEXT, Speech, SpeechError  # noqa: E402
from tutor import LANGUAGES, Tutor  # noqa: E402  (after .env so providers see the settings)

# Only the site itself is served; server code, .env and .git are never reachable.
PUBLIC = ("index.html", "pages", "assets", "module", "demo")
# Single files from otherwise private folders. data/ also holds the channel and accommodation
# databases (learners' personal data), so the folder itself is never served.
PUBLIC_FILES = ("data/jobs.json",)
MAX_BODY = 20_000
MAX_QUESTION = 1_000
INTENTS = ("lesson_intro", "explain")

mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("font/woff2", ".woff2")

# One tutor for everything: the web widget here, and Telegram, SMS and /lite through core_bridge.
tutor = Tutor()
speech = Speech()
sessions = Sessions()

router = APIRouter()


def validate(body: dict) -> tuple[dict | None, str]:
    intent = body.get("intent") if body.get("intent") in INTENTS else None
    question = body.get("question") or ""
    if not isinstance(question, str) or not (question.strip() or intent):
        return None, "'question' must be a non-empty string."
    if len(question) > MAX_QUESTION:
        return None, f"'question' is longer than {MAX_QUESTION} characters."
    history = []
    for turn in (body.get("history") or [])[-8:]:
        if (
            isinstance(turn, dict)
            and turn.get("role") in ("user", "assistant")
            and isinstance(turn.get("content"), str)
            and turn["content"].strip()
        ):
            history.append({"role": turn["role"], "content": turn["content"][:2000]})
    context = body.get("context") if isinstance(body.get("context"), dict) else None
    return {
        "question": question,
        # "language" is the API contract's name for it; "lang" is what the widget sends.
        "lang": next((v for v in (body.get("language"), body.get("lang")) if v in LANGUAGES), None),
        # The answer level: "simple", "standard" or "detailed" ("simple": true still means simple).
        "simple": body.get("simple") is True or body.get("level") == "simple",
        "detailed": body.get("level") == "detailed" and body.get("simple") is not True,
        "history": history,
        "context": context,
        "intent": intent,
        "voice": body.get("voice") is True,
        "detect_switch": body.get("detect_switch") is True,
        # false: the learner has not agreed to their question going to a cloud AI (see openapi.yaml).
        "cloud": body.get("cloud") is not False,
    }, ""


def resolve_language(request: dict, session_id) -> tuple[str, str | None]:
    """The reply language: the request's if it names a valid one, else the session's, else English.
    The server keeps the session's language in step, so it never depends on the browser alone."""
    session = sessions.get(session_id)
    lang = request["lang"] or (session or {}).get("lang") or "en"
    if session:
        sessions.touch(session_id, lang)
    return lang, session_id if session else None


# Interactive API documentation (Swagger UI) for openapi.yaml, so a judge can try every call here.
DOCS_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Ableway tutor API</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14/swagger-ui.css">
</head><body><main><h1 style="font-family:system-ui;margin:16px">Ableway tutor API</h1><div id="api"></div></main>
<script src="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5.17.14/swagger-ui-bundle.js"></script>
<script>SwaggerUIBundle({ url: '/openapi.yaml', dom_id: '#api' });</script>
</body></html>"""


# ------------------------------------------------------------------ responses
def send(request: Request, status: int, body: bytes, content_type: str, headers: dict | None = None) -> Response:
    out = {"Content-Type": content_type, **(headers or {})}
    # Text is compressed for slow, expensive connections (3G): the widget shrinks about four times.
    compressible = content_type.startswith(("text/", "application/json", "application/javascript", "application/yaml"))
    if compressible and len(body) > 1024 and "gzip" in (request.headers.get("accept-encoding") or ""):
        body = gzip.compress(body, compresslevel=6)
        out["Content-Encoding"] = "gzip"
        out["Vary"] = "Accept-Encoding"
    out["Content-Length"] = str(len(body))
    # Any website can load Mimi (and pages opened straight from disk have the origin "null"), so the
    # tutor API accepts any origin. It holds no cookies or per-user state.
    out["Access-Control-Allow-Origin"] = "*"
    out["Access-Control-Allow-Headers"] = "Content-Type"
    out["Access-Control-Expose-Headers"] = "X-Mimi-Voice"
    out["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    return Response(content=b"" if request.method == "HEAD" else body, status_code=status, headers=out)


def send_json(request: Request, status: int, payload: dict) -> Response:
    return send(request, status, json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")


async def read_json(request: Request, limit: int = MAX_BODY):
    """(body, None) or (None, an error response)."""
    length = int(request.headers.get("content-length") or 0)
    if not 0 < length <= limit:
        return None, send_json(request, 413, {"error": "Request body is missing or too large."})
    try:
        body = json.loads((await request.body()).decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None, send_json(request, 400, {"error": "Body must be JSON."})
    if not isinstance(body, dict):
        return None, send_json(request, 400, {"error": "Body must be a JSON object."})
    return body, None


@router.options("/api/{rest:path}", include_in_schema=False)
async def preflight(request: Request, rest: str):
    return send(request, 204, b"", "text/plain")


# ------------------------------------------------------------------ the tutor
@router.post("/api/ask")
@router.post("/api/v1/ask")
async def ask(request: Request):
    body, error = await read_json(request)
    if error:
        return error
    question, problem = validate(body)
    if question is None:
        return send_json(request, 400, {"error": problem})
    question["lang"], session_id = resolve_language(question, body.get("session_id"))
    try:
        result = await run_in_threadpool(lambda: tutor.ask(**question))
    except Exception as e:  # the learner should get a clear failure, not a hung chat
        print(f"[tutor] /api/ask failed: {e!r}", file=sys.stderr)  # the error, never the question
        return send_json(request, 500, {"error": "The tutor could not answer. Please try again."})
    if session_id and result.get("switch_lang"):
        sessions.touch(session_id, result["switch_lang"])
    result["sources"] = [{"title": c["title"], "url": c["url"]} for c in result["citations"]]
    return send_json(request, 200, {**result, "session_id": session_id})


@router.post("/api/v1/content")
async def add_content(request: Request):
    """The host sends its own lessons ({"chunks": [...]}); each becomes a citable section."""
    body, error = await read_json(request)
    if error:
        return error
    items = body.get("chunks") or body.get("lessons") or []
    if not isinstance(items, list) or len(items) > 500:
        return send_json(request, 400, {"error": "Send 'chunks': a list of up to 500 {title, url, text} items."})
    from retrieval import Index

    # Pages send their content on every visit, so the same item twice is kept once.
    known = {c["id"] for c in tutor.index.chunks}
    added = []
    for item in items:
        if not isinstance(item, dict) or not str(item.get("text") or "").strip():
            continue
        title, url, text = str(item.get("title") or "Lesson")[:200], str(item.get("url") or "")[:300], str(item["text"])[:6000]
        chunk_id = "host-" + hashlib.sha1(f"{url}|{title}|{text}".encode("utf-8")).hexdigest()[:12]
        if chunk_id in known:
            continue
        known.add(chunk_id)
        added.append({"id": chunk_id, "corpus": "course", "kind": "lesson", "lang": "en",
                      "course": str(item.get("course") or "")[:200], "title": title, "url": url, "page": url, "text": text})
    if added:
        tutor.index = Index(tutor.index.chunks + added)
    return send_json(request, 201 if added else 200, {"status": "indexed", "added": len(added), "total_chunks": len(tutor.index.chunks)})


@router.post("/api/v1/escalations")
async def escalation(request: Request):
    """{conversation, language, page} -> {ticketId, chatUrl}: a ticket on the help desk (/handoff), with
    the conversation so far, so the tutor in the console sees what the learner already asked.

    The help desk is part of this server, so the ticket is opened directly. Only when CHANNELS_URL
    names another server (a help desk run separately) is the ticket sent there over HTTP."""
    body, error = await read_json(request)
    if error:
        return error
    conversation = body.get("conversation") if isinstance(body.get("conversation"), list) else []
    lang = next((v for v in (body.get("language"), body.get("lang")) if v in ("en", "am")), "en")
    topic = next((str(t.get("text") or t.get("content") or "") for t in reversed(conversation)
                  if isinstance(t, dict) and t.get("role") in ("user", "learner")), "")
    # One English sentence on top of the ticket, so the tutor knows the problem at a glance. A cloud
    # AI writes it only if the learner allowed online AI ("cloud": false keeps it on this server).
    try:
        summary = await run_in_threadpool(lambda: tutor.summarise(conversation, cloud=body.get("cloud") is not False))
    except Exception:  # never block the learner from reaching a person
        summary = ""
    page = body.get("page") if isinstance(body.get("page"), dict) else {}
    data = {"lang": lang, "topic": (summary or topic)[:200], "summary": summary,
            "channel": "web", "conversation": conversation[-12:], "page": page}
    own = (os.environ.get("PUBLIC_BASE_URL") or str(request.base_url)).rstrip("/")
    remote = (os.environ.get("CHANNELS_URL") or "").rstrip("/")
    if remote and remote != own:
        try:
            ticket = await run_in_threadpool(_post_ticket, remote, data)
        except (urllib.error.URLError, OSError, ValueError):
            return send_json(request, 503, {"error": "The help desk is not reachable right now. Please try again in a minute."})
        chat_url = ticket.get("absolute_chat_url") or f"{remote}{ticket['chat_url']}"
    else:
        from server.handoff.router import open_ticket

        ticket = await run_in_threadpool(open_ticket, data, own)
        chat_url = ticket["absolute_chat_url"]
    return send_json(request, 201, {
        "ticketId": ticket["ticket_id"],
        "chatUrl": chat_url,
        "message": "A tutor will answer in this chat. If nobody is online now, it may take until morning.",
    })


def _post_ticket(base: str, data: dict) -> dict:
    request = urllib.request.Request(f"{base}/handoff/tickets", data=json.dumps(data).encode("utf-8"),
                                     headers={"Content-Type": "application/json"})
    # A help desk on a free hosting plan sleeps when idle; waking takes up to about a minute.
    with urllib.request.urlopen(request, timeout=75) as response:
        return json.load(response)


@router.post("/api/session")
async def session(request: Request):
    body, error = await read_json(request)
    if error:
        return error
    return send_json(request, 200, sessions.touch(body.get("session_id"), body.get("lang")))


# ------------------------------------------------------------------ voice
@router.post("/api/tts")
async def tts(request: Request):
    body, error = await read_json(request)
    if error:
        return error
    text, lang = body.get("text"), body.get("lang")
    if not isinstance(text, str) or not text.strip() or len(text) > MAX_TTS_TEXT or lang not in ("en", "am"):
        return send_json(request, 400, {"error": f"'text' (up to {MAX_TTS_TEXT} characters) and 'lang' (en or am) are required."})
    try:
        audio, content_type, provider = await run_in_threadpool(lambda: speech.synthesize(text, lang, cache=body.get("cache") is True))
    except SpeechError as e:
        return send_json(request, 503, {"error": "No server voice is available right now.", "detail": str(e)})
    return send(request, 200, audio, content_type, {"X-Mimi-Voice": provider, "Cache-Control": "no-store"})


@router.post("/api/transcribe")
async def transcribe(request: Request, lang: str = "", purpose: str = ""):
    length = int(request.headers.get("content-length") or 0)
    content_type = (request.headers.get("content-type") or "").split(";")[0].strip().lower()
    if not 0 < length <= MAX_AUDIO_BYTES:
        return send_json(request, 413, {"error": "Audio is missing or too long."})
    if content_type not in ("audio/wav", "audio/x-wav", "audio/wave"):
        return send_json(request, 415, {"error": "Send the recording as audio/wav."})
    audio = await request.body()
    try:
        text = await run_in_threadpool(lambda: speech.transcribe(audio, "audio/wav", lang if lang in ("en", "am") else None, purpose or None))
    except SpeechError as e:
        return send_json(request, 503, {"error": "Speech recognition is not available right now.", "detail": str(e)})
    return send_json(request, 200, {"text": text})


# ------------------------------------------------------------------ health, contract, docs
def help_desk_status() -> dict:
    """Can a learner reach a person right now? The ticket database must open and answer; Telegram is
    reported but optional. A monitor (Render's health check, Docker, an uptime service) reads this."""
    from server.channels.config import telegram_token
    from server.channels.telegram_bot import is_running
    from server.handoff import tickets

    status = {"ok": True, "waiting": None, "telegram": "off"}
    try:
        status["waiting"] = len(tickets.list_open())
    except Exception as e:  # the database file is missing, locked or unwritable
        status.update(ok=False, error=type(e).__name__)
    if telegram_token():
        status["telegram"] = "running" if is_running() else "not running"
    return status


@router.api_route("/api/health", methods=["GET", "HEAD"])
async def health(request: Request):
    """200 when Mimi can answer and the help desk can take learners; 503 when the help desk cannot, so
    a health check restarts the service (see render.yaml and docker-compose.yml)."""
    desk = await run_in_threadpool(help_desk_status)
    return send_json(request, 200 if desk["ok"] else 503, {**tutor.health(), "speech": speech.status(), "help_desk": desk})


@router.api_route("/openapi.yaml", methods=["GET", "HEAD"], include_in_schema=False)
async def contract(request: Request):
    spec = ROOT / "openapi.yaml"
    if not spec.is_file():
        return send_json(request, 404, {"error": "openapi.yaml is missing from this installation."})
    return send(request, 200, spec.read_bytes(), "application/yaml; charset=utf-8")


@router.api_route("/docs", methods=["GET", "HEAD"], include_in_schema=False)
@router.api_route("/docs/", methods=["GET", "HEAD"], include_in_schema=False)
async def docs(request: Request):
    return send(request, 200, DOCS_PAGE.encode("utf-8"), "text/html; charset=utf-8")


# ------------------------------------------------------------------ the site's files
# Registered last in server/main.py, after every other route, so it only answers what nothing else does.
site_router = APIRouter()


@site_router.api_route("/{path:path}", methods=["GET", "HEAD"], include_in_schema=False)
async def site_file(request: Request, path: str):
    relative = path.lstrip("/") or "index.html"
    target = (ROOT / relative).resolve()
    # Judge the resolved path, not the requested one, so "pages/../server/.env" is refused.
    try:
        relative_path = target.relative_to(ROOT)
        allowed = relative_path.parts[0] in PUBLIC or relative_path.as_posix() in PUBLIC_FILES
    except (ValueError, IndexError):
        allowed = False
    if not allowed or not target.is_file():
        return send_json(request, 404, {"error": "Not found."})
    content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
    if content_type.startswith("text/") or content_type == "application/json":
        content_type += "; charset=utf-8"
    # no-cache: the browser re-checks each file, so after an update it never runs an old widget.
    return send(request, 200, target.read_bytes(), content_type, {"Cache-Control": "no-cache"})


def startup_report() -> None:
    """What is ready, printed once when the server starts."""
    health = tutor.health()
    print(f"Mimi tutor: {health['chunks']} course chunks, {health['faq_entries']} FAQ entries", flush=True)
    for p in health["providers"]:
        print(f"  {'ready  ' if p['available'] else 'skipped'} {p['label']}: {p['detail']}", flush=True)
    voice = speech.status()
    for p in voice["tts_providers"]:
        print(f"  {'ready  ' if p['available'] else 'skipped'} Mimi's voice ({p['name']}): {p['detail']}", flush=True)
    print(f"  {'ready  ' if voice['stt'] else 'skipped'} Server speech recognition: {voice['stt_detail']}", flush=True)
