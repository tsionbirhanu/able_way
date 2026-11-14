"""Connects the Telegram, SMS and /lite channels to the real tutor.

Set in .env:   CORE_ASK_IMPORT=server.core_bridge:ask

server/channels/core_client.py then calls ask() below instead of its canned stub. This file only
translates between the two shapes; the answers come from tutor.py, the same as the web widget.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))  # tutor.py imports its neighbours as top-level modules

from tutor import Tutor  # noqa: E402

_tutor: Tutor | None = None


def ask(question: str, lang: str, channel: str, simple: bool = False) -> dict:
    """The core_client contract: {"answer", "citations": [{"page", "heading"}], "matched"}."""
    global _tutor
    if _tutor is None:
        _tutor = Tutor()
    result = _tutor.ask(question, lang=lang, simple=simple)
    citations = [{"page": c["url"], "heading": c["title"]} for c in result["citations"]]
    answer = result["answer"]
    if channel in ("sms", "telegram", "lite"):
        # These channels list the sources themselves, so the [1] markers would be noise.
        answer = " ".join(answer.replace("[1]", "").replace("[2]", "").replace("[3]", "").split())
    return {"answer": answer, "citations": citations, "matched": bool(result["grounded"])}
