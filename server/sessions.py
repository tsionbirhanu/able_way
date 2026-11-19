"""Classroom sessions: the language a learner chose, kept on the server.

The browser remembers the language too, but the server does not take its word for it: every
/api/ask carries a session id, and when the request names no valid language the session's is
used. A switch request ("English please") updates the session, so the language stays the same
across lessons, voice and text, and page reloads.

Only the language and two timestamps are stored, in memory: no questions, no answers, no names.
"""

from __future__ import annotations

import secrets
import threading
import time

LANGS = ("en", "am")


class Sessions:
    TTL = 12 * 3600  # a classroom day
    MAX = 10_000  # oldest sessions are dropped first beyond this

    def __init__(self):
        self._data: dict[str, dict] = {}
        self._lock = threading.Lock()

    @staticmethod
    def valid_id(session_id) -> bool:
        return isinstance(session_id, str) and 16 <= len(session_id) <= 64 and session_id.replace("-", "").replace("_", "").isalnum()

    def get(self, session_id) -> dict | None:
        if not self.valid_id(session_id):
            return None
        with self._lock:
            session = self._data.get(session_id)
            if session and time.time() - session["seen"] > self.TTL:
                del self._data[session_id]
                return None
            if session:
                session["seen"] = time.time()
            return dict(session) if session else None

    def touch(self, session_id=None, lang=None) -> dict:
        """Create or update a session; returns {"session_id", "lang"} (lang may be None: not chosen yet).
        An unknown or malformed id gets a fresh one, so ids are always server-issued."""
        with self._lock:
            now = time.time()
            session = self._data.get(session_id) if self.valid_id(session_id) else None
            if session is None or now - session["seen"] > self.TTL:
                session_id = secrets.token_urlsafe(18)
                session = {"lang": None, "created": now, "seen": now}
                self._data[session_id] = session
                if len(self._data) > self.MAX:
                    for old in sorted(self._data, key=lambda k: self._data[k]["seen"])[: len(self._data) - self.MAX]:
                        del self._data[old]
            if lang in LANGS:
                session["lang"] = lang
            session["seen"] = now
            return {"session_id": session_id, "lang": session["lang"]}