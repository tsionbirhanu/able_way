"""The pluggable AI layer.

Three back ends answer the same request, tried in the order set by ABLEWAY_PROVIDERS
(default "gemini,local,offline"):

  gemini   Gemini through Google's API. Needs internet and a Gemini API key.
  local    An open model served by Ollama on this machine. Needs no internet.
  offline  No model at all: a hand-written FAQ plus quotes from the course text (tutor.py).

The two model back ends expose one method, complete(system, messages, max_tokens) -> str,
so adding another (a different cloud, a different local runtime) means one small class here.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request


class ProviderError(Exception):
    """This back end cannot answer right now; the tutor moves on to the next one."""


def gemini_keys() -> list[str]:
    """The configured Gemini API keys, server-side only (shared by the tutor and speech.py)."""
    configured = os.environ.get("GEMINI_API_KEYS") or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY", "")
    return list(dict.fromkeys(k.strip() for k in configured.replace("\n", ",").split(",") if k.strip()))


class Provider:
    name = ""
    label = ""
    uses_model = True

    def status(self) -> dict:
        raise NotImplementedError

    def complete(self, system: str, messages: list[dict], max_tokens: int = 16000) -> str:
        raise NotImplementedError


# ------------------------------------------------------------------ cloud: Gemini


class GeminiProvider(Provider):
    name = "gemini"
    label = "Gemini AI"
    COOLDOWN = 60  # seconds to skip the cloud after a network failure, so offline use stays fast

    def __init__(self):
        self.model = os.environ.get("ABLEWAY_GEMINI_MODEL", "gemini-2.5-flash")
        self.api_keys = gemini_keys()
        self._next_key = 0
        self._down_until = 0.0
        self._down_reason = ""

    def _configured(self) -> bool:
        return bool(self.api_keys)

    def status(self) -> dict:
        if not self._configured():
            return {"available": False, "detail": "No credentials. Set GEMINI_API_KEYS in server/.env."}
        if time.time() < self._down_until:
            return {"available": False, "detail": f"Paused after an error: {self._down_reason}"}
        return {"available": True, "detail": f"model {self.model}"}

    def complete(self, system: str, messages: list[dict], max_tokens: int = 16000) -> str:
        contents = []
        for message in messages:
            role = "model" if message["role"] == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": message["content"]}]})
        body = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": contents,
            "generationConfig": {"maxOutputTokens": min(max_tokens, 2048), "temperature": 0.2},
        }
        if "flash" in self.model and self.model.startswith("gemini-2.5"):
            # Answering from supplied sources needs no long reasoning; thinking made spoken replies
            # take 20 seconds or more. A budget of 0 turns it off on the 2.5 Flash models.
            body["generationConfig"]["thinkingConfig"] = {"thinkingBudget": 0}
        payload = None
        start = self._next_key % len(self.api_keys)
        last_error = None
        for offset in range(len(self.api_keys)):
            key_index = (start + offset) % len(self.api_keys)
            request = urllib.request.Request(
                f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent",
                data=json.dumps(body).encode("utf-8"),
                headers={"Content-Type": "application/json", "x-goog-api-key": self.api_keys[key_index]},
            )
            try:
                # A learner is waiting: after 20 seconds the next key, then the offline answers.
                with urllib.request.urlopen(request, timeout=20) as response:
                    payload = json.load(response)
                self._next_key = key_index
                break
            except urllib.error.HTTPError as e:
                last_error = e
                # Quota, invalid-key, and permission errors are key-specific; try the next key.
                if e.code not in (401, 403, 429):
                    seconds = self.COOLDOWN if e.code >= 500 else 0
                    raise self._pause(f"Gemini API error {e.code}", seconds) from e
            except (urllib.error.URLError, OSError, ValueError) as e:
                raise self._pause("no connection to the Gemini API", self.COOLDOWN) from e
        if payload is None:
            code = last_error.code if isinstance(last_error, urllib.error.HTTPError) else "unknown"
            # Fail over to another provider instead of retrying exhausted keys on every request.
            raise self._pause(f"all Gemini keys failed (last API error {code})", self.COOLDOWN)

        candidates = payload.get("candidates") or []
        text = "".join(
            part.get("text", "")
            for part in (candidates[0].get("content", {}).get("parts", []) if candidates else [])
        ).strip()
        if not text:
            raise ProviderError("Gemini returned no text (the request may have been blocked).")
        return text

    def _pause(self, reason: str, seconds: int) -> ProviderError:
        if seconds:
            self._down_until = time.time() + seconds
            self._down_reason = reason
        return ProviderError(f"Gemini unavailable: {reason}.")


# ------------------------------------------------------------------ local: Ollama


class OllamaProvider(Provider):
    name = "local"
    label = "Local open model (Ollama)"

    def __init__(self):
        self.base = os.environ.get("ABLEWAY_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
        self.model = os.environ.get("ABLEWAY_OLLAMA_MODEL", "gemma3:4b")
        self._checked_at = 0.0
        self._status = {"available": False, "detail": "not checked yet"}

    def status(self) -> dict:
        if time.time() - self._checked_at < 30:
            return self._status
        self._checked_at = time.time()
        try:
            with urllib.request.urlopen(f"{self.base}/api/tags", timeout=0.8) as r:
                names = [m.get("name", "") for m in json.load(r).get("models", [])]
        except (urllib.error.URLError, OSError, ValueError):
            self._status = {"available": False, "detail": f"Ollama is not running at {self.base}."}
            return self._status
        if any(n == self.model or n.split(":")[0] == self.model for n in names):
            self._status = {"available": True, "detail": f"model {self.model}"}
        else:
            self._status = {
                "available": False,
                "detail": f"Ollama is running but '{self.model}' is not pulled (ollama pull {self.model}).",
            }
        return self._status

    def complete(self, system: str, messages: list[dict], max_tokens: int = 16000) -> str:
        body = {
            "model": self.model,
            "stream": False,
            "messages": [{"role": "system", "content": system}, *messages],
            "options": {"temperature": 0.2, "num_predict": min(max_tokens, 1024)},
        }
        request = urllib.request.Request(
            f"{self.base}/api/chat",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as r:
                text = json.load(r).get("message", {}).get("content", "").strip()
        except (urllib.error.URLError, OSError, ValueError) as e:
            self._checked_at = 0.0  # re-check on the next request
            raise ProviderError(f"Local model unavailable: {e}.") from e
        if not text:
            raise ProviderError("The local model returned no text.")
        return text


# ------------------------------------------------------------------ offline: no model


class OfflineProvider(Provider):
    """A marker: the tutor answers from the FAQ file and quoted course text itself."""

    name = "offline"
    label = "Offline answers (no AI model)"
    uses_model = False

    def status(self) -> dict:
        return {"available": True, "detail": "FAQ and course text search; always available"}


REGISTRY = {"gemini": GeminiProvider, "local": OllamaProvider, "offline": OfflineProvider}


def build_chain() -> list[Provider]:
    """Providers in the order they are tried. Offline is always last so there is always an answer."""
    names = [n.strip() for n in os.environ.get("ABLEWAY_PROVIDERS", "gemini,local,offline").split(",")]
    chain = [REGISTRY[n]() for n in names if n in REGISTRY and n != "offline"]
    chain.append(OfflineProvider())
    return chain
