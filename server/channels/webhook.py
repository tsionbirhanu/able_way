"""One outgoing webhook (Level 2): the host registers an address, and this server posts to it when
something happens. Today that is "ticket.opened", when a learner asks for a person.

    WEBHOOK_URL=https://host.example/hooks/assistant      (in .env; empty = off)

The body is JSON {"event": "ticket.opened", "at": "<UTC time>", "data": {...}}. No learner name,
phone number or message text is sent: only the ticket id, channel and language.
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import os
import threading
import urllib.request

log = logging.getLogger("channels.webhook")


def send(event: str, data: dict) -> bool:
    """Post the event in the background; never slows down or breaks the learner's request."""
    url = (os.environ.get("WEBHOOK_URL") or "").strip()
    if not url:
        return False
    body = json.dumps({"event": event, "at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                       "data": data}).encode("utf-8")

    def post():
        try:
            request = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json",
                                                                       "User-Agent": "ableway-webhook"})
            with urllib.request.urlopen(request, timeout=10):
                pass
        except Exception as exc:  # a host that is down must not affect the learner
            log.warning("webhook %s failed: %s", event, type(exc).__name__)

    threading.Thread(target=post, daemon=True).start()
    return True
