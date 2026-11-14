"""HTTP API for the tutor, plus a static server for the Savanna pages.

    python server/app.py            then open http://localhost:8000/

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

import json
import mimetypes
import os
import sys
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


load_env(HERE / ".env")

from sessions import Sessions  # noqa: E402
from speech import MAX_AUDIO_BYTES, MAX_TTS_TEXT, Speech, SpeechError  # noqa: E402
from tutor import Tutor  # noqa: E402  (after .env so providers see the settings)

# Only the site itself is served; server code, .env and .git are never reachable.
PUBLIC = ("index.html", "pages", "assets", "assistant")
MAX_BODY = 20_000
MAX_QUESTION = 1_000

mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("font/woff2", ".woff2")

tutor = Tutor()
speech = Speech()
sessions = Sessions()
INTENTS = ("lesson_intro",)


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
        "lang": body.get("lang") if body.get("lang") in ("en", "am") else None,
        "simple": body.get("simple") is True,
        "history": history,
        "context": context,
        "intent": intent,
        "voice": body.get("voice") is True,
        "detect_switch": body.get("detect_switch") is True,
    }, ""


def resolve_language(request: dict, session_id) -> tuple[str, str | None]:
    """The reply language: the request's if it names a valid one, else the session's, else English.
    The server keeps the session's language in step, so it never depends on the browser alone."""
    session = sessions.get(session_id)
    lang = request["lang"] or (session or {}).get("lang") or "en"
    if session:
        sessions.touch(session_id, lang)
    return lang, session_id if session else None


class Handler(BaseHTTPRequestHandler):
    server_version = "Ableway/0.1"

    def _send(self, status: int, body: bytes, content_type: str, headers: dict | None = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        for name, value in (headers or {}).items():
            self.send_header(name, value)
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
        if route == "/api/ask":
            return self._ask()
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
        self._json(200, {**result, "session_id": session_id})

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
        relative = path.lstrip("/") or "index.html"
        target = (ROOT / relative).resolve()
        # Judge the resolved path, not the requested one, so "pages/../server/.env" is refused.
        try:
            allowed = target.relative_to(ROOT).parts[0] in PUBLIC
        except (ValueError, IndexError):
            allowed = False
        if not allowed or not target.is_file():
            return self._json(404, {"error": "Not found."})
        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        if content_type.startswith("text/") or content_type == "application/json":
            content_type += "; charset=utf-8"
        self._send(200, target.read_bytes(), content_type)

    do_HEAD = do_GET

    def log_message(self, fmt, *args):
        # Log API calls only, and never the question text: questions can be personal.
        if "/api/" in self.path:
            sys.stderr.write(f"[app] {self.command} {urlparse(self.path).path} -> {args[1] if len(args) > 1 else ''}\n")


def main() -> None:
    port = int(os.environ.get("ABLEWAY_PORT", "8000"))
    host = os.environ.get("ABLEWAY_HOST", "127.0.0.1")
    health = tutor.health()
    print(f"Ableway tutor: {health['chunks']} course chunks, {health['faq_entries']} FAQ entries")
    for p in health["providers"]:
        print(f"  {'ready  ' if p['available'] else 'skipped'} {p['label']}: {p['detail']}")
    voice = speech.status()
    for p in voice["tts_providers"]:
        print(f"  {'ready  ' if p['available'] else 'skipped'} Mimi's voice ({p['name']}): {p['detail']}")
    print(f"  {'ready  ' if voice['stt'] else 'skipped'} Server speech recognition: {voice['stt_detail']}")
    print(f"Open http://{host if host != '0.0.0.0' else 'localhost'}:{port}/  (Ctrl+C to stop)")
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    main()
