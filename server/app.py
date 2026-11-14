"""HTTP API for the tutor, plus a static server for the Savanna pages.

    python server/app.py            then open http://localhost:8000/

Endpoints
    POST /api/ask      {"question": str, "lang": "en"|"am", "simple": bool, "history": [...]}
    GET  /api/health   which providers are available, how much content is indexed

Standard library only. The Claude provider additionally needs `pip install anthropic`.
"""

from __future__ import annotations

import json
import mimetypes
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse

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

from tutor import Tutor  # noqa: E402  (after .env so providers see the settings)

# Only the site itself is served; server code, .env and .git are never reachable.
PUBLIC = ("index.html", "pages", "assets", "assistant", "module", "demo", "data")
MAX_BODY = 20_000
MAX_QUESTION = 1_000

mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("font/woff2", ".woff2")

tutor = Tutor()


def validate(body: dict) -> tuple[dict | None, str]:
    question = body.get("question")
    if not isinstance(question, str) or not question.strip():
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
    return {
        "question": question,
        "lang": body.get("lang") if body.get("lang") in ("en", "am") else "en",
        "simple": body.get("simple") is True,
        "history": history,
    }, ""


class Handler(BaseHTTPRequestHandler):
    server_version = "Ableway/0.1"

    def _send(self, status: int, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        # The pages are also opened straight from disk (file://), whose origin is "null",
        # so the API accepts any origin. It holds no cookies or per-user state.
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _json(self, status: int, payload: dict) -> None:
        self._send(status, json.dumps(payload, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

    def do_OPTIONS(self):
        self._send(204, b"", "text/plain")

    def do_POST(self):
        req_path = urlparse(self.path).path
        if req_path not in ("/api/ask", "/api/v1/ask", "/api/v1/content", "/api/v1/escalations"):
            return self._json(404, {"error": "Not found."})
        length = int(self.headers.get("Content-Length") or 0)
        if not 0 < length <= MAX_BODY:
            return self._json(413, {"error": "Request body is missing or too large."})
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return self._json(400, {"error": "Body must be JSON."})
        if not isinstance(body, dict):
            return self._json(400, {"error": "Body must be a JSON object."})

        # Track 3 Data Contract: POST /api/v1/content (index custom lessons)
        if req_path == "/api/v1/content":
            items = body.get("chunks") or body.get("lessons") or []
            if isinstance(items, list):
                from retrieval import Index
                tutor.index.chunks.extend(items)
                tutor.index = Index(tutor.index.chunks)
                return self._json(200, {"status": "indexed", "total_chunks": len(tutor.index.chunks)})
            return self._json(400, {"error": "Expected 'chunks' list."})

        # Track 3 Data Contract: POST /api/v1/escalations (create human ticket)
        if req_path == "/api/v1/escalations":
            import uuid
            ticket_id = f"esc-{uuid.uuid4().hex[:6]}"
            return self._json(201, {
                "ticketId": ticket_id,
                "status": "queued",
                "message": "A human tutor will review your question. It may take until morning."
            })

        request, error = validate(body)
        if request is None:
            return self._json(400, {"error": error})
        try:
            result = tutor.ask(**request)
            result["sources"] = [{"title": c["title"], "url": c["url"]} for c in result["citations"]]
            self._json(200, result)
        except Exception as e:  # the learner should get a clear failure, not a hung chat
            print(f"[app] /api/ask failed: {e!r}", file=sys.stderr)
            self._json(500, {"error": "The tutor could not answer. Please try again."})

    def do_GET(self):
        path = unquote(urlparse(self.path).path)
        if path == "/api/health":
            return self._json(200, tutor.health())
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
    print(f"Open http://{host if host != '0.0.0.0' else 'localhost'}:{port}/  (Ctrl+C to stop)")
    ThreadingHTTPServer((host, port), Handler).serve_forever()


if __name__ == "__main__":
    main()
