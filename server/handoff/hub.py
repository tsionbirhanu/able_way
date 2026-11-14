"""In-memory hub that connects the WebSockets of one ticket (learner <-> tutor).

Also relays to learners who are on an external channel (Telegram) through `external_senders`.
"""
from server.channels.strings import t

from . import tickets

_connections = {}  # ticket_id -> list of (websocket, role)

# channel -> async f(address, text). Registered by the channel itself (e.g. the Telegram bot).
external_senders = {}


def join(ticket_id, ws, role):
    _connections.setdefault(ticket_id, []).append((ws, role))


def leave(ticket_id, ws):
    conns = [c for c in _connections.get(ticket_id, []) if c[0] is not ws]
    if conns:
        _connections[ticket_id] = conns
    else:
        _connections.pop(ticket_id, None)


def presence(ticket_id) -> dict:
    roles = {role for _, role in _connections.get(ticket_id, [])}
    ticket = tickets.get_ticket(ticket_id) or {}
    return {"type": "presence", "tutor": "tutor" in roles,
            "learner": "learner" in roles or bool(ticket.get("external_address"))}


async def broadcast(ticket_id, payload, only_role=None, exclude=None):
    for ws, role in list(_connections.get(ticket_id, [])):
        if ws is exclude or (only_role and role != only_role):
            continue
        try:
            await ws.send_json(payload)
        except Exception:
            leave(ticket_id, ws)


async def post_message(ticket_id: str, role: str, text: str) -> bool:
    """Store a chat message and deliver it to everyone on the ticket. False if the ticket is not open."""
    text = (text or "").strip()[:2000]
    ticket = tickets.get_ticket(ticket_id)
    if not text or not ticket or ticket["status"] != "open":
        return False
    message = tickets.add_message(ticket_id, role, text)
    await broadcast(ticket_id, dict(message, type="chat"))
    if role == "tutor" and ticket["external_address"]:
        sender = external_senders.get(ticket["channel"])
        if sender:
            await sender(ticket["external_address"], t(ticket["lang"], "tg_tutor_prefix") + ": " + text)
    return True


async def close(ticket_id: str, notify_external: bool = True) -> bool:
    ticket = tickets.get_ticket(ticket_id)
    if not ticket or not tickets.close_ticket(ticket_id):
        return False
    await broadcast(ticket_id, {"type": "closed"})
    if notify_external and ticket["external_address"]:
        sender = external_senders.get(ticket["channel"])
        if sender:
            await sender(ticket["external_address"], t(ticket["lang"], "tg_human_ended"))
    return True
