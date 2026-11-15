"""SQLite access for data/channels.db (owned by the channels / handoff work only).

Accommodation requests are deliberately NOT here: see server/channels/accommodation.py.
"""
import sqlite3
from contextlib import contextmanager

from .config import channels_db_path

SCHEMA = """
CREATE TABLE IF NOT EXISTS chat_prefs (
    channel TEXT NOT NULL, address TEXT NOT NULL, lang TEXT NOT NULL,
    PRIMARY KEY (channel, address)
);
CREATE TABLE IF NOT EXISTS sms_outbox (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    to_number TEXT NOT NULL, text TEXT NOT NULL, kind TEXT NOT NULL DEFAULT 'alert',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE IF NOT EXISTS subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel TEXT NOT NULL, address TEXT NOT NULL, keyword TEXT NOT NULL, language TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (channel, address, keyword)
);
CREATE TABLE IF NOT EXISTS sent_alerts (
    subscription_id INTEGER NOT NULL, job_id TEXT NOT NULL,
    sent_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (subscription_id, job_id)
);
CREATE TABLE IF NOT EXISTS tickets (
    id TEXT PRIMARY KEY,
    channel TEXT NOT NULL, lang TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'open',
    topic TEXT NOT NULL DEFAULT '', external_address TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')), closed_at TEXT
);
CREATE TABLE IF NOT EXISTS ticket_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id TEXT NOT NULL, role TEXT NOT NULL, text TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
-- "Always answer me with voice too" (Telegram /voice on). Only the choice is kept.
CREATE TABLE IF NOT EXISTS voice_prefs (
    channel TEXT NOT NULL, address TEXT NOT NULL, voice INTEGER NOT NULL,
    PRIMARY KEY (channel, address)
);
-- Anonymous on purpose: no user id, chat id, phone number or IP. Date only, no time.
CREATE TABLE IF NOT EXISTS question_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT NOT NULL, normalised TEXT NOT NULL,
    lang TEXT NOT NULL, channel TEXT NOT NULL, matched INTEGER NOT NULL,
    asked_on TEXT NOT NULL
);
"""

_initialised = set()


@contextmanager
def connect():
    """Open data/channels.db, creating the tables on first use. Commits on success."""
    path = channels_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        if str(path) not in _initialised or not path.exists():
            conn.executescript(SCHEMA)
            _initialised.add(str(path))
        yield conn
        conn.commit()
    finally:
        conn.close()


def get_lang(channel: str, address: str, default: str = "en") -> str:
    with connect() as c:
        row = c.execute(
            "SELECT lang FROM chat_prefs WHERE channel=? AND address=?", (channel, str(address))
        ).fetchone()
    return row["lang"] if row else default


def get_voice(channel: str, address: str) -> bool:
    with connect() as c:
        row = c.execute(
            "SELECT voice FROM voice_prefs WHERE channel=? AND address=?", (channel, str(address))
        ).fetchone()
    return bool(row and row["voice"])


def set_voice(channel: str, address: str, on: bool) -> None:
    with connect() as c:
        c.execute(
            "INSERT INTO voice_prefs (channel, address, voice) VALUES (?,?,?) "
            "ON CONFLICT(channel, address) DO UPDATE SET voice=excluded.voice",
            (channel, str(address), int(on)),
        )


def set_lang(channel: str, address: str, lang: str) -> None:
    with connect() as c:
        c.execute(
            "INSERT INTO chat_prefs (channel, address, lang) VALUES (?,?,?) "
            "ON CONFLICT(channel, address) DO UPDATE SET lang=excluded.lang",
            (channel, str(address), lang),
        )
