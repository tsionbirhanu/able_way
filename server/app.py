"""HTTP API for the tutor, plus a static server for the Savanna pages.

    python server/app.py            then open http://localhost:8001/

Endpoints
    POST /api/ask         {"question": str, "lang": "en"|"am", "simple": bool, "history": [...],
                           "session_id": str, "context": {"page", "course", "lesson"},
                           "intent": "lesson_intro"|null, "voice": bool, "detect_switch": bool}
    POST /api/session     {"session_id"?: str, "lang"?: "en"|"am"} -> {"session_id", "lang"}
    POST /api/tts         {"text": str, "lang": "en"|"am", "cache": bool} -> audio (503: use the browser voice)
    POST /api/transcribe  raw audio/wav body, ?lang=am|en&purpose=language_choice -> {"text": str}
    GET  /api/health      which providers are available, how much content is indexed, speech status

Standard library only. The Claude provider additionally needs `pip install anthropic`.
"""

from __future__ import annotations

import gzip
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))


def load_env(path: Path) -> None:
    """Read KEY=VALUE lines from server/.env without overriding the real environment."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip("'\""))


load_env(ROOT / ".env")  # the one settings file, shared with the channels server
load_env(HERE / ".env")  # older location, still read
# Or one folder up, outside the project (and so outside git entirely). Read last: a setting in the
# project's own .env wins.
load_env(ROOT.parent / ".env")

from sessions import Sessions  # noqa: E402
from speech import MAX_AUDIO_BYTES, MAX_TTS_TEXT, Speech, SpeechError  # noqa: E402
from tutor import Tutor  # noqa: E402  (after .env so providers see the settings)

# Only the site itself is served; server code, .env and .git are never reachable.
PUBLIC = ("index.html", "pages", "assets", "module", "demo")
# Single files from otherwise private folders. data/ also holds the channel and accommodation
# databases (learners' personal data), so the folder itself is never served.
PUBLIC_FILES = ("data/jobs.json",)
MAX_BODY = 20_000
MAX_QUESTION = 1_000

mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("font/woff2", ".woff2")

tutor = Tutor()
speech = Speech()
sessions = Sessions()
INTENTS = ("lesson_intro", "explain")


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
        # "language" is the Track 3 contract's name for it; "lang" is what the widget sends.
        "lang": next((v for v in (body.get("language"), body.get("lang")) if v in ("en", "am")), None),
        "simple": body.get("simple") is True,
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


class Handler(BaseHTTPRequestHandler):
    server_version = "Ableway/0.1"

    def _send(self, status: int, body: bytes, content_type: str, headers: dict | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        # Text is compressed for slow, expensive connections (3G): the widget shrinks about four times.
        compressible = content_type.startswith(("text/", "application/json", "application/javascript", "application/yaml"))
        if compressible and len(body) > 1024 and "gzip" in (self.headers.get("Accept-Encoding") or ""):
            body = gzip.compress(body, compresslevel=6)
            self.send_header("Content-Encoding", "gzip")
            self.send_header("Vary", "Accept-Encoding")
        self.send_header("Content-Length", str(len(body)))
        # The pages are also opened straight from disk (file://), whose origin is "null",
        # so the API accepts any origin. It holds no cookies or per-user state.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Expose-Headers", "X-Mimi-Voice")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, status: int, payload: dict) -> None:
        self._send(status, json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def do_OPTIONS(self):
        self._send(204, b"", "text/plain")

    def _read_json(self, limit: int = MAX_BODY):
        length = int(self.headers.get("Content-Length") or 0)
        if not 0 < length <= limit:
            self._json(413, {"error": "Request body is missing or too large."})
            return None
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            self._json(400, {"error": "Body must be JSON."})
            return None
        if not isinstance(body, dict):
            self._json(400, {"error": "Body must be a JSON object."})
            return None
        return body

    def do_POST(self):
        route = urlparse(self.path).path
        if route in ("/api/ask", "/api/v1/ask"):
            return self._ask()
        if route == "/api/v1/content":
            return self._add_content()
        if route == "/api/v1/escalations":
            return self._escalation()
        if route == "/api/session":
            body = self._read_json()
            if body is not None:
                self._json(200, sessions.touch(body.get("session_id"), body.get("lang")))
            return None
        if route == "/api/tts":
            return self._tts()
        if route == "/api/transcribe":
            return self._transcribe()
        return self._json(404, {"error": "Not found."})

    def _ask(self):
        body = self._read_json()
        if body is None:
            return None
        request, error = validate(body)
        if request is None:
            return self._json(400, {"error": error})
        request["lang"], session_id = resolve_language(request, body.get("session_id"))
        try:
            result = tutor.ask(**request)
        except Exception as e:  # the learner should get a clear failure, not a hung chat
            print(f"[app] /api/ask failed: {e!r}", file=sys.stderr)
            return self._json(500, {"error": "The tutor could not answer. Please try again."})
        if session_id and result.get("switch_lang"):
            sessions.touch(session_id, result["switch_lang"])
        result["sources"] = [{"title": c["title"], "url": c["url"]} for c in result["citations"]]
        self._json(200, {**result, "session_id": session_id})

    def _add_content(self):
        """Track 3 data contract: POST /api/v1/content indexes extra lessons ({"chunks": [...]})."""
        body = self._read_json()
        if body is None:
            return None
        items = body.get("chunks") or body.get("lessons") or []
        if not isinstance(items, list) or len(items) > 500:
            return self._json(400, {"error": "Send 'chunks': a list of up to 500 {title, url, text} items."})
        import hashlib

        from retrieval import Index

        # Each item becomes a citable chunk. Pages send their content on every visit, so the same
        # item twice is kept once.
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
        self._json(201 if added else 200, {"status": "indexed", "added": len(added), "total_chunks": len(tutor.index.chunks)})

    def _escalation(self):
        """Track 3 data contract: POST /api/v1/escalations {conversation, language} -> {ticketId}.

        Opens a real ticket on the help desk (server/main.py, /handoff), with the conversation so far,
        so the tutor in the console sees what the learner already asked."""
        body = self._read_json()
        if body is None:
            return None
        conversation = body.get("conversation") if isinstance(body.get("conversation"), list) else []
        lang = next((v for v in (body.get("language"), body.get("lang")) if v in ("en", "am")), "en")
        topic = next((str(t.get("text") or t.get("content") or "") for t in reversed(conversation)
                      if isinstance(t, dict) and t.get("role") in ("user", "learner")), "")
        # One English sentence on top of the ticket, so the tutor knows the problem at a glance. A cloud
        # AI writes it only if the learner allowed online AI ("cloud": false keeps it on this server).
        try:
            summary = tutor.summarise(conversation, cloud=body.get("cloud") is not False)
        except Exception:  # never block the learner from reaching a person
            summary = ""
        payload = json.dumps({"lang": lang, "topic": (summary or topic)[:200], "summary": summary,
                              "channel": "web", "conversation": conversation[-12:]})
        base = os.environ.get("CHANNELS_URL", "http://localhost:8000").rstrip("/")
        try:
            request = urllib.request.Request(f"{base}/handoff/tickets", data=payload.encode("utf-8"),
                                             headers={"Content-Type": "application/json"})
            # A free hosting plan puts the help desk to sleep when idle; waking takes up to about a minute.
            with urllib.request.urlopen(request, timeout=75) as response:
                ticket = json.load(response)
        except (urllib.error.URLError, OSError, ValueError):
            return self._json(503, {"error": "The help desk is not reachable right now. Please try again in a minute."})
        self._json(201, {
            "ticketId": ticket["ticket_id"],
            "chatUrl": ticket.get("absolute_chat_url") or f"{base}{ticket['chat_url']}",
            "message": "A tutor will answer in this chat. If nobody is online now, it may take until morning.",
        })

    def _tts(self):
        body = self._read_json()
        if body is None:
            return None
        text, lang = body.get("text"), body.get("lang")
        if not isinstance(text, str) or not text.strip() or len(text) > MAX_TTS_TEXT or lang not in ("en", "am"):
            return self._json(400, {"error": f"'text' (up to {MAX_TTS_TEXT} characters) and 'lang' (en or am) are required."})
        try:
            audio, content_type, provider = speech.synthesize(text, lang, cache=body.get("cache") is True)
        except SpeechError as e:
            return self._json(503, {"error": "No server voice is available right now.", "detail": str(e)})
        self._send(200, audio, content_type, {"X-Mimi-Voice": provider, "Cache-Control": "no-store"})

    def _transcribe(self):
        length = int(self.headers.get("Content-Length") or 0)
        content_type = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        if not 0 < length <= MAX_AUDIO_BYTES:
            return self._json(413, {"error": "Audio is missing or too long."})
        if content_type not in ("audio/wav", "audio/x-wav", "audio/wave"):
            return self._json(415, {"error": "Send the recording as audio/wav."})
        audio = self.rfile.read(length)
        query = parse_qs(urlparse(self.path).query)
        lang = (query.get("lang") or [""])[0]
        purpose = (query.get("purpose") or [""])[0]
        try:
            text = speech.transcribe(audio, "audio/wav", lang if lang in ("en", "am") else None, purpose or None)
        except SpeechError as e:
            return self._json(503, {"error": "Speech recognition is not available right now.", "detail": str(e)})
        self._json(200, {"text": text})

    def do_GET(self):
        path = unquote(urlparse(self.path).path)
        if path == "/api/health":
            return self._json(200, {**tutor.health(), "speech": speech.status()})
        if path == "/openapi.yaml":
            spec = ROOT / "openapi.yaml"
            if not spec.is_file():
                return self._json(404, {"error": "openapi.yaml is missing from this installation."})
            return self._send(200, spec.read_bytes(), "application/yaml; charset=utf-8")
        if path in ("/docs", "/docs/"):
            return self._send(200, DOCS_PAGE.encode("utf-8"), "text/html; charset=utf-8")
        relative = path.lstrip("/") or "index.html"
        target = (ROOT / relative).resolve()
        # Judge the resolved path, not the requested one, so "pages/../server/.env" is refused.
        try:
            relative_path = target.relative_to(ROOT)
            allowed = relative_path.parts[0] in PUBLIC or relative_path.as_posix() in PUBLIC_FILES
        except (ValueError, IndexError):
            allowed = False
        if not allowed or not target.is_file():
            return self._json(404, {"error": "Not found."})
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type == "application/json":
            content_type += "; charset=utf-8"
        # no-cache: the browser re-checks each file, so after an update it never runs an old widget.
        self._send(200, target.read_bytes(), content_type, {"Cache-Control": "no-cache"})

    do_HEAD = do_GET

    def log_message(self, fmt, *args):
        # Log API calls only, and never the question text: questions can be personal.
        if "/api/" in self.path:
            sys.stderr.write(f"[app] {self.command} {urlparse(self.path).path} -> {args[1] if len(args) > 1 else ''}\n")


def main() -> None:
    port = int(os.environ.get("ABLEWAY_PORT", "8001"))
    host = os.environ.get("ABLEWAY_HOST", "127.0.0.1")
    health = tutor.health()
    print(f"Ableway tutor: {health['chunks']} course chunks, {health['faq_entries']} FAQ entries")
    for p in health["providers"]:
        print(f"  {'ready  ' if p['available'] else 'skipped'} {p['label']}: {p['detail']}")
    voice = speech.status()
    for p in voice["tts_providers"]:
        print(f"  {'ready  ' if p['available'] else 'skipped'} Mimi's voice ({p['name']}): {p['detail']}")
    print(f"  {'ready  ' if voice['stt'] else 'skipped'} Server speech recognition: {voice['stt_detail']}")
    # On Windows, address reuse lets a second server bind a port that is already in use, and the
    # old one keeps answering. Without it, a second start fails at once with a clear error.
    ThreadingHTTPServer.allow_reuse_address = os.name != "nt"
    try:
        server = ThreadingHTTPServer((host, port), Handler)
    except OSError:
        sys.exit(f"Port {port} is already in use. Stop the other server (Ctrl+C in its window) or set ABLEWAY_PORT.")
    print(f"Open http://{host if host != '0.0.0.0' else 'localhost'}:{port}/  (Ctrl+C to stop)")
    server.serve_forever()


if __name__ == "__main__":
    main()
