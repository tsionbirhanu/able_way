"""The pluggable AI layer.

Three back ends answer the same request, tried in the order set by ABLEWAY_PROVIDERS
(default "cloud,local,offline"):

  cloud    Claude through the Anthropic API. Needs internet and credentials.
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
from pathlib import Path


class ProviderError(Exception):
    """This back end cannot answer right now; the tutor moves on to the next one."""


class Provider:
    name = ""
    label = ""
    uses_model = True

    def status(self) -> dict:
        raise NotImplementedError

    def complete(self, system: str, messages: list[dict], max_tokens: int = 16000) -> str:
        raise NotImplementedError


# ------------------------------------------------------------------ cloud: Claude


class ClaudeProvider(Provider):
    name = "cloud"
    label = "Cloud AI (Claude)"

    # Models that accept the server-side refusal fallback parameter.
    FALLBACK_MODELS = {"claude-fable-5-2", "claude-fable-5-1", "claude-opus-5-5", "claude-opus-5", "claude-sonnet-5-5"}
    COOLDOWN = 60  # seconds to skip the cloud after a network failure, so offline use stays fast

    def __init__(self):
        self.model = os.environ.get("ABLEWAY_CLAUDE_MODEL", "claude-opus-5-5")
        # Tutoring answers are short and read from supplied text, so low effort keeps the
        # chat responsive. Raise it here if answers start missing nuance.
        self.effort = os.environ.get("ABLEWAY_CLAUDE_EFFORT", "low")
        self._client = None
        self._down_until = 0.0
        self._down_reason = ""

    def _configured(self) -> bool:
        if any(os.environ.get(k) for k in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN", "ANTHROPIC_PROFILE")):
            return True
        return (Path.home() / ".config" / "anthropic").exists()  # an `ant auth login` profile

    def status(self) -> dict:
        try:
            import anthropic  # noqa: F401
        except ImportError:
            return {"available": False, "detail": "The 'anthropic' package is not installed (pip install anthropic)."}
        if not self._configured():
            return {"available": False, "detail": "No credentials. Set ANTHROPIC_API_KEY in server/.env."}
        if time.time() < self._down_until:
            return {"available": False, "detail": f"Paused after an error: {self._down_reason}"}
        return {"available": True, "detail": f"model {self.model}, effort {self.effort}"}

    def complete(self, system: str, messages: list[dict], max_tokens: int = 16000) -> str:
        import anthropic

        if self._client is None:
            self._client = anthropic.Anthropic(timeout=45.0, max_retries=1)
        request = dict(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
            output_config={"effort": self.effort},
        )
        try:
            if self.model in self.FALLBACK_MODELS:
                # If a safety classifier declines the request, the API re-runs it on a
                # fallback model inside the same call instead of returning nothing.
                response = self._client.beta.messages.create(
                    betas=["server-side-fallback-2026-07-01"], fallbacks="default", **request
                )
            else:
                response = self._client.messages.create(**request)
        except anthropic.AuthenticationError as e:
            raise self._pause("the API key was rejected", 600) from e
        except anthropic.PermissionDeniedError as e:
            raise self._pause("the API key lacks permission for this model", 600) from e
        except anthropic.NotFoundError as e:
            raise self._pause(f"model '{self.model}' was not found", 600) from e
        except anthropic.RateLimitError as e:
            raise self._pause("rate limited", 20) from e
        except anthropic.APIStatusError as e:
            raise self._pause(f"API error {e.status_code}", self.COOLDOWN if e.status_code >= 500 else 0) from e
        except anthropic.APIConnectionError as e:
            raise self._pause("no connection to the Anthropic API", self.COOLDOWN) from e

        if response.stop_reason == "refusal":
            raise ProviderError("Claude declined to answer this request.")
        text = "".join(block.text for block in response.content if block.type == "text").strip()
        if not text:
            raise ProviderError(f"Claude returned no text (stop reason: {response.stop_reason}).")
        return text

    def _pause(self, reason: str, seconds: int) -> ProviderError:
        if seconds:
            self._down_until = time.time() + seconds
            self._down_reason = reason
        return ProviderError(f"Cloud AI unavailable: {reason}.")


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


REGISTRY = {"cloud": ClaudeProvider, "local": OllamaProvider, "offline": OfflineProvider}


def build_chain() -> list[Provider]:
    """Providers in the order they are tried. Offline is always last so there is always an answer."""
    names = [n.strip() for n in os.environ.get("ABLEWAY_PROVIDERS", "cloud,local,offline").split(",")]
    chain = [REGISTRY[n]() for n in names if n in REGISTRY and n != "offline"]
    chain.append(OfflineProvider())
    return chain
