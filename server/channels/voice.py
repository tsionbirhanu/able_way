"""Voice messages for the Telegram bot: the learner speaks, Mimi answers in text and in voice.

Uses the same speech layer as the web widget (server/speech.py): Azure Speech when
AZURE_SPEECH_KEY is set, otherwise Gemini. Audio is handled in memory only and never stored;
like text messages, it is never logged.
"""
from __future__ import annotations

import re

from server.speech import Speech, SpeechError

from .strings import t

MAX_SECONDS = 120
MAX_BYTES = 2_000_000
MAX_SPOKEN = 900  # characters read aloud; the full answer is always in the text message

_speech: Speech | None = None


def _get() -> Speech:
    global _speech
    if _speech is None:
        _speech = Speech()
    return _speech


def too_long(voice: dict) -> bool:
    return (voice.get("duration") or 0) > MAX_SECONDS or (voice.get("file_size") or 0) > MAX_BYTES


def transcribe(audio: bytes, mime: str, lang: str) -> str:
    """The words in a voice note ('' when there are none). Raises SpeechError when no
    recogniser is available (no key, quota used up, no connection)."""
    speech = _get()
    # Azure must be told the language. Gemini can hear either, so it gets no "most likely ..."
    # hint: with one, an English question in an Amharic chat could be written down as Amharic.
    hint = lang if speech._azure_stt() else None
    return speech.transcribe(audio, mime or "audio/ogg", hint)


def spoken_part(reply: str, lang: str) -> str:
    """What to read aloud from a text reply: not the sources line, not links."""
    label = t(lang, "sources") + ":"
    keep = [p for p in reply.split("\n\n") if not p.strip().startswith(label)]
    text = re.sub(r"https?://\S+", "", "\n".join(keep))
    text = re.sub(r"\s*\[\d+\]", "", text)
    return " ".join(text.split())[:MAX_SPOKEN]


def speak(text: str, lang: str) -> tuple[bytes, str] | None:
    """(audio, content type) for a reply, or None when no voice is available."""
    if not text:
        return None
    try:
        audio, mime, _provider = _get().synthesize(text, lang)
    except SpeechError:
        return None
    return to_mp3(audio, mime)


def to_mp3(audio: bytes, mime: str) -> tuple[bytes, str]:
    """Telegram shows MP3 or OGG/Opus as a voice message, WAV only as a file. Azure already gives
    MP3; Gemini gives WAV, which is converted when the optional `lameenc` package is installed."""
    if mime != "audio/wav":
        return audio, mime
    try:
        import io
        import wave

        import lameenc
    except ImportError:
        return audio, mime
    try:
        with wave.open(io.BytesIO(audio)) as w:
            rate, channels, pcm = w.getframerate(), w.getnchannels(), w.readframes(w.getnframes())
        encoder = lameenc.Encoder()
        encoder.set_bit_rate(48)
        encoder.set_in_sample_rate(rate)
        encoder.set_channels(channels)
        encoder.set_quality(5)
        return bytes(encoder.encode(pcm) + encoder.flush()), "audio/mpeg"
    except Exception:  # an odd WAV: send it as it is
        return audio, mime
