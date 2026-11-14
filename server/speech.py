"""Mimi's voice on the server: text to speech, and speech to text for browsers that cannot hear Amharic.

Gemini (providers.py) still writes every answer; this module only turns text into audio and
audio into text, so the voice can be swapped without touching the tutor.

Text to speech, tried in the order of ABLEWAY_TTS (default "gemini"; "none" turns it off):

  gemini   Gemini TTS models (ABLEWAY_TTS_MODELS, tried in order) with one prebuilt female voice
           (ABLEWAY_TTS_VOICE, default Sulafat) for both languages, so Mimi sounds like the same
           person in Amharic and English. Uses the GEMINI_API_KEYS the tutor already has.
  google   Google Cloud Text-to-Speech (GOOGLE_TTS_API_KEY): am-ET-Wavenet-A and en-US-Neural2-F,
           both female, configurable with ABLEWAY_TTS_VOICE_AM / ABLEWAY_TTS_VOICE_EN.

When no provider can speak (no key, quota used up), /api/tts answers 503 and the browser falls
back to its own voices.

Speech to text uses Gemini models (ABLEWAY_STT_MODELS, tried in order) on a short WAV recorded in
the browser. gemini-3-flash-preview transcribed short Amharic answers correctly in testing where the
flash-lite models did not, so it comes first.
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request
import wave
from collections import OrderedDict
from pathlib import Path

try:
    from .providers import gemini_keys
except ImportError:  # pragma: no cover - standalone app entry point
    from providers import gemini_keys

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "data" / "tts_cache"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
MAX_TTS_TEXT = 1500
MAX_AUDIO_BYTES = 3_000_000


class SpeechError(Exception):
    pass


def spoken_text(text: str) -> str:
    """What should be heard: no citation markers, no stray whitespace."""
    text = re.sub(r"\s*\[\d+\]", "", text or "")
    return re.sub(r"\s+", " ", text).strip()


def pcm_to_wav(pcm: bytes, rate: int = 24000) -> bytes:
    out = io.BytesIO()
    with wave.open(out, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
    return out.getvalue()


def _post_json(url: str, body: dict, headers: dict, timeout: int) -> dict:
    request = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def _retry_after(error: urllib.error.HTTPError) -> int:
    """Seconds Google asks us to wait after a 429 (its retryDelay), capped at six hours."""
    try:
        details = json.loads(error.read().decode("utf-8")).get("error", {}).get("details", [])
        delay = next(d["retryDelay"] for d in details if "retryDelay" in d)
        return min(int(float(delay.rstrip("s"))) + 1, 6 * 3600)
    except Exception:
        return 300


class _Cooldowns:
    """Skip a model for a while after quota or server errors, so each request does not retry it."""

    def __init__(self):
        self._until: dict[str, float] = {}
        self._why: dict[str, str] = {}

    def ready(self, name: str) -> bool:
        return time.time() >= self._until.get(name, 0)

    def pause(self, name: str, seconds: int, why: str) -> None:
        self._until[name] = time.time() + seconds
        self._why[name] = why

    def detail(self, name: str) -> str:
        return "" if self.ready(name) else f"paused for {int(self._until[name] - time.time())}s: {self._why[name]}"


# ------------------------------------------------------------------ text to speech


class GeminiTTS:
    name = "gemini"
    STYLE = {
        "am": (
            "Read the following Amharic text aloud exactly as written, with natural Amharic pronunciation, "
            "in a warm, friendly and patient female teacher's voice, at a calm, clear pace:"
        ),
        "en": (
            "Read the following text aloud exactly as written, in a warm, friendly and patient female "
            "teacher's voice, at a calm, clear pace:"
        ),
    }

    def __init__(self):
        self.keys = gemini_keys()
        default = "gemini-3.8-flash-lite-tts,gemini-3.1-flash-tts-preview,gemini-2.5-flash-preview-tts"
        self.models = [m.strip() for m in os.environ.get("ABLEWAY_TTS_MODELS", default).split(",") if m.strip()]
        self.voice = os.environ.get("ABLEWAY_TTS_VOICE", "Sulafat").strip() or "Sulafat"
        self.cooldowns = _Cooldowns()

    def voice_id(self, lang: str) -> str:
        return f"gemini:{self.voice}"

    def status(self) -> dict:
        if not self.keys:
            return {"available": False, "detail": "no GEMINI_API_KEYS"}
        ready = [m for m in self.models if self.cooldowns.ready(m)]
        if not ready:
            return {"available": False, "detail": "; ".join(f"{m} {self.cooldowns.detail(m)}" for m in self.models)}
        return {"available": True, "detail": f"voice {self.voice}, model {ready[0]}"}

    def synthesize(self, text: str, lang: str) -> tuple[bytes, str]:
        body = {
            "contents": [{"role": "user", "parts": [{"text": f"{self.STYLE[lang]}\n\n{text}"}]}],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": self.voice}}},
            },
        }
        last = "no model available"
        for model in self.models:
            if not self.cooldowns.ready(model):
                continue
            for key in self.keys:
                try:
                    payload = _post_json(GEMINI_URL.format(model=model), body, {"x-goog-api-key": key}, timeout=60)
                except urllib.error.HTTPError as e:
                    last = f"{model}: API error {e.code}"
                    if e.code in (401, 403):
                        continue  # key-specific; try the next key
                    if e.code == 429:
                        self.cooldowns.pause(model, _retry_after(e), "quota")
                    else:
                        self.cooldowns.pause(model, 60 if e.code >= 500 else 600, f"API error {e.code}")
                    break
                except (urllib.error.URLError, OSError, ValueError) as e:
                    raise SpeechError(f"no connection to the Gemini API: {e}") from e
                parts = (payload.get("candidates") or [{}])[0].get("content", {}).get("parts", [])
                audio = next((p["inlineData"] for p in parts if "inlineData" in p), None)
                if not audio:
                    last = f"{model}: no audio in the reply"
                    break
                data, mime = base64.b64decode(audio["data"]), audio.get("mimeType", "")
                if data[:4] == b"RIFF":
                    return data, "audio/wav"
                rate = int((re.search(r"rate=(\d+)", mime) or [0, 24000])[1])
                return pcm_to_wav(data, rate), "audio/wav"
        raise SpeechError(last)


class GoogleCloudTTS:
    """Google Cloud Text-to-Speech. Its am-ET voices are listed by Google as female (A) and male (B)."""

    name = "google"

    def __init__(self):
        self.key = os.environ.get("GOOGLE_TTS_API_KEY", "").strip()
        self.voices = {
            "am": os.environ.get("ABLEWAY_TTS_VOICE_AM", "am-ET-Wavenet-A"),
            "en": os.environ.get("ABLEWAY_TTS_VOICE_EN", "en-US-Neural2-F"),
        }
        self.cooldowns = _Cooldowns()

    def voice_id(self, lang: str) -> str:
        return f"google:{self.voices[lang]}"

    def status(self) -> dict:
        if not self.key:
            return {"available": False, "detail": "no GOOGLE_TTS_API_KEY"}
        if not self.cooldowns.ready("google"):
            return {"available": False, "detail": self.cooldowns.detail("google")}
        return {"available": True, "detail": f"voices {self.voices['am']}, {self.voices['en']}"}

    def synthesize(self, text: str, lang: str) -> tuple[bytes, str]:
        voice = self.voices[lang]
        body = {
            "input": {"text": text},
            "voice": {"languageCode": "-".join(voice.split("-")[:2]), "name": voice},
            "audioConfig": {"audioEncoding": "MP3", "speakingRate": 0.95},
        }
        try:
            payload = _post_json("https://texttospeech.googleapis.com/v1/text:synthesize", body, {"x-goog-api-key": self.key}, timeout=30)
        except urllib.error.HTTPError as e:
            self.cooldowns.pause("google", _retry_after(e) if e.code == 429 else 120, f"API error {e.code}")
            raise SpeechError(f"Google TTS error {e.code}") from e
        except (urllib.error.URLError, OSError, ValueError) as e:
            raise SpeechError(f"no connection to Google TTS: {e}") from e
        return base64.b64decode(payload["audioContent"]), "audio/mpeg"


TTS_REGISTRY = {"gemini": GeminiTTS, "google": GoogleCloudTTS}


class Speech:
    MEMORY_ITEMS = 48  # recent answers, so "Replay" does not cost another request

    def __init__(self):
        names = [n.strip() for n in os.environ.get("ABLEWAY_TTS", "gemini").split(",") if n.strip()]
        self.tts = [TTS_REGISTRY[n]() for n in names if n in TTS_REGISTRY]
        self.stt_models = [
            m.strip() for m in os.environ.get("ABLEWAY_STT_MODELS", "gemini-3-flash-preview,gemini-3.5-flash-lite,gemini-2.5-flash-lite").split(",") if m.strip()
        ]
        self.stt_keys = gemini_keys() if os.environ.get("ABLEWAY_STT", "gemini") == "gemini" else []
        self.stt_cooldowns = _Cooldowns()
        self._memory: OrderedDict[str, tuple[bytes, str]] = OrderedDict()
        self._lock = threading.Lock()

    def status(self) -> dict:
        tts = [{"name": p.name, **p.status()} for p in self.tts]
        stt_ready = bool(self.stt_keys) and any(self.stt_cooldowns.ready(m) for m in self.stt_models)
        return {
            "tts": any(p["available"] for p in tts),
            "tts_cache": bool(self.tts),  # recorded fixed phrases (greeting, confirmations) can still play
            "tts_providers": tts,
            "stt": stt_ready,
            "stt_detail": f"models {', '.join(self.stt_models)}" if self.stt_keys else "no GEMINI_API_KEYS",
        }

    # ------------------------------------------------------------ text to speech

    def synthesize(self, text: str, lang: str, cache: bool = False) -> tuple[bytes, str, str]:
        """(audio bytes, content type, provider name). `cache` keeps fixed phrases such as the
        greeting on disk; other text is kept only in memory, never written out."""
        text = spoken_text(text)[:MAX_TTS_TEXT]
        if not text:
            raise SpeechError("nothing to say")
        errors = []
        for provider in self.tts:
            # A recorded phrase is served even while the provider is paused (quota used up).
            key = hashlib.sha256(f"{provider.voice_id(lang)}|{lang}|{text}".encode("utf-8")).hexdigest()
            hit = self._recall(key)
            if hit:
                return (*hit, provider.name)
            if not provider.status()["available"]:
                continue
            try:
                audio, mime = provider.synthesize(text, lang)
            except SpeechError as e:
                errors.append(f"{provider.name}: {e}")
                print(f"[speech] {provider.name} could not speak: {e}", file=sys.stderr)
                continue
            self._remember(key, audio, mime, to_disk=cache)
            return audio, mime, provider.name
        raise SpeechError("; ".join(errors) or "no text-to-speech provider is available")

    def _recall(self, key: str):
        with self._lock:
            if key in self._memory:
                self._memory.move_to_end(key)
                return self._memory[key]
        for suffix, mime in ((".wav", "audio/wav"), (".mp3", "audio/mpeg")):
            path = CACHE_DIR / f"{key}{suffix}"
            if path.exists():
                return path.read_bytes(), mime
        return None

    def _remember(self, key: str, audio: bytes, mime: str, to_disk: bool) -> None:
        with self._lock:
            self._memory[key] = (audio, mime)
            while len(self._memory) > self.MEMORY_ITEMS:
                self._memory.popitem(last=False)
        if to_disk:
            CACHE_DIR.mkdir(parents=True, exist_ok=True)
            (CACHE_DIR / f"{key}{'.wav' if mime == 'audio/wav' else '.mp3'}").write_bytes(audio)

    # ------------------------------------------------------------ speech to text

    STT_PROMPT = (
        "Transcribe what the learner says in this recording, word for word. They speak Amharic or "
        "English{hint}.{purpose} Write Amharic in Ge'ez (Ethiopic) script and English in Latin script, "
        "exactly as spoken, without translating, and never in any other script. Reply with the transcript "
        "only. If there is no clear speech, reply with exactly [[EMPTY]]."
    )
    # Short answers are hard to hear without context; when the question is known, say so.
    PURPOSES = {
        "language_choice": " They are answering whether they want to learn in Amharic (አማርኛ) or English (እንግሊዝኛ).",
    }

    def transcribe(self, audio: bytes, mime: str, lang: str | None = None, purpose: str | None = None) -> str:
        if not self.stt_keys:
            raise SpeechError("speech to text is not configured")
        hint = {"am": ", most likely Amharic", "en": ", most likely English"}.get(lang or "", "")
        body = {
            "contents": [{"role": "user", "parts": [
                {"inlineData": {"mimeType": mime, "data": base64.b64encode(audio).decode("ascii")}},
                {"text": self.STT_PROMPT.format(hint=hint, purpose=self.PURPOSES.get(purpose or "", ""))},
            ]}],
            "generationConfig": {"temperature": 0},
        }
        last = "no model available"
        for model in self.stt_models:
            if not self.stt_cooldowns.ready(model):
                continue
            for key in self.stt_keys:
                try:
                    payload = _post_json(GEMINI_URL.format(model=model), body, {"x-goog-api-key": key}, timeout=30)
                except urllib.error.HTTPError as e:
                    last = f"{model}: API error {e.code}"
                    if e.code in (401, 403):
                        continue
                    self.stt_cooldowns.pause(model, _retry_after(e) if e.code == 429 else 60, f"API error {e.code}")
                    break
                except (urllib.error.URLError, OSError, ValueError) as e:
                    raise SpeechError(f"no connection to the Gemini API: {e}") from e
                parts = (payload.get("candidates") or [{}])[0].get("content", {}).get("parts", [])
                text = "".join(p.get("text", "") for p in parts).strip()
                return "" if "[[EMPTY]]" in text else text
        raise SpeechError(last)
