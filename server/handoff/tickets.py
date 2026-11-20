"""Handoff tickets and their chat messages (tables in data/channels.db)."""
import secrets

from server.channels.db import connect
from server.channels.strings import norm_lang


def create_ticket(channel: str = "web", lang: str = "en", topic: str = "", external_address=None) -> str:
    """Create an open ticket. The id is random and unguessable: it is the learner's key to the chat."""
    ticket_id = secrets.token_urlsafe(9)
    with connect() as c:
        c.execute(
            "INSERT INTO tickets (id, channel, lang, topic, external_address) VALUES (?,?,?,?,?)",
            (ticket_id, (channel or "web")[:20], norm_lang(lang), (topic or "").strip()[:200],
             str(external_address) if external_address is not None else None),
        )
    return ticket_id


def get_ticket(ticket_id: str):
    with connect() as c:
        row = c.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone()
    return dict(row) if row else None


def find_open_external(channel: str, address) -> str:
    with connect() as c:
        row = c.execute(
            "SELECT id FROM tickets WHERE channel=? AND external_address=? AND status='open' "
            "ORDER BY created_at DESC LIMIT 1", (channel, str(address))).fetchone()
    return row["id"] if row else None


def list_open() -> list:
    with connect() as c:
        rows = c.execute(
            "SELECT t.id, t.channel, t.lang, t.topic, t.created_at, t.tutor_name, "
            "(SELECT COUNT(*) FROM ticket_messages m WHERE m.ticket_id=t.id) AS message_count, "
            "(SELECT text FROM ticket_messages m WHERE m.ticket_id=t.id ORDER BY m.id DESC LIMIT 1) AS last_message "
            "FROM tickets t WHERE t.status='open' ORDER BY t.created_at").fetchall()
    return [dict(r) for r in rows]


def claim(ticket_id: str, tutor_name: str) -> None:
    """This tutor is now helping on this request."""
    with connect() as c:
        c.execute("UPDATE tickets SET tutor_name=? WHERE id=? AND status='open'", (tutor_name[:40], ticket_id))


def close_ticket(ticket_id: str) -> bool:
    with connect() as c:
        cur = c.execute(
            "UPDATE tickets SET status='closed', closed_at=datetime('now') WHERE id=? AND status='open'",
            (ticket_id,))
        return cur.rowcount > 0


def add_message(ticket_id: str, role: str, text: str) -> dict:
    with connect() as c:
        cur = c.execute(
            "INSERT INTO ticket_messages (ticket_id, role, text) VALUES (?,?,?)", (ticket_id, role, text))
        row = c.execute("SELECT role, text, created_at FROM ticket_messages WHERE id=?", (cur.lastrowid,)).fetchone()
    return {"role": row["role"], "text": row["text"], "at": row["created_at"]}


def messages(ticket_id: str) -> list:
    with connect() as c:
        rows = c.execute(
            "SELECT role, text, created_at FROM ticket_messages WHERE ticket_id=? ORDER BY id", (ticket_id,)
        ).fetchall()
    return [{"role": r["role"], "text": r["text"], "at": r["created_at"]} for r in rows]
