"""Anonymous question log.

Stores ONLY: question text, language, channel, date. Never a user id, chat id, phone number or IP.
Accommodation requests must never be passed to this function.
"""
import datetime
import re
import unicodedata

from server.channels.db import connect


def normalise(question: str) -> str:
    """Lower-case, strip punctuation and extra spaces so near-identical questions group together."""
    text = unicodedata.normalize("NFKC", question or "").lower()
    text = "".join(" " if unicodedata.category(ch)[0] in "PSZC" else ch for ch in text)
    return re.sub(r"\s+", " ", text).strip()


def log_question(question: str, lang: str, channel: str, matched: bool) -> None:
    question = (question or "").strip()[:500]
    if not question:
        return
    with connect() as c:
        c.execute(
            "INSERT INTO question_log (question, normalised, lang, channel, matched, asked_on) "
            "VALUES (?,?,?,?,?,?)",
            (question, normalise(question), lang or "en", channel or "unknown", 1 if matched else 0,
             datetime.date.today().isoformat()),
        )
