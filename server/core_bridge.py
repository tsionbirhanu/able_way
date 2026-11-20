"""Connects the Telegram, SMS and /lite channels to the real tutor.

Set in .env:   CORE_ASK_IMPORT=server.core_bridge:ask

server/channels/core_client.py then calls ask() below instead of its canned stub. This file only
translates between the two shapes; the answers come from tutor.py, the same as the web widget.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))  # tutor.py imports its neighbours as top-level modules

from tutor import Tutor  # noqa: E402

_tutor: Tutor | None = None


def ask(question: str, lang: str, channel: str, simple: bool = False, cloud: bool = False) -> dict:
    """The core_client contract: {"answer", "citations": [{"page", "heading"}], "matched"}."""
    global _tutor
    # In the one server, the same tutor as the web page (so lessons a host sent are known here too).
    api = sys.modules.get("server.tutor_api")
    if api is not None:
        tutor = api.tutor
    else:
        if _tutor is None:
            _tutor = Tutor()
        tutor = _tutor
    result = tutor.ask(question, lang=lang, simple=simple, cloud=cloud)
    citations = [{"page": c["url"], "heading": c["title"]} for c in result["citations"]]
    answer = result["answer"]
    if channel in ("sms", "telegram", "lite"):
        # The channels list the source themselves: drop the [n] markers and the space they leave.
        answer = re.sub(r"\s*\[\d+\]", "", answer)
        answer = re.sub(r"\s+([.,;:!?።፣፤])", r"\1", " ".join(answer.split()))
    return {"answer": answer, "citations": citations, "matched": bool(result["grounded"])}
