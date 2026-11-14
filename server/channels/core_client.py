"""The ONE place where channels get their answers.

    ask(question, lang, channel, simple=False)
        -> {"answer": str, "citations": [{"page": str, "heading": str}], "matched": bool}

REAL / STUB SWITCH (kept in this file only)
-------------------------------------------
1. CORE_ASK_IMPORT="package.module:function"  -> calls that Python function
2. CORE_ASK_URL="http://host/path"            -> POSTs {question, lang, channel, simple} as JSON
3. neither set                                -> STUB below (canned answers, for the demo only)

If the real core is configured but fails, ask() returns matched=False so the learner is told to
ask a person. It never silently falls back to canned answers.
"""
import importlib
import logging
import os
import re

log = logging.getLogger("channels.core_client")

UNMATCHED = {"answer": "", "citations": [], "matched": False}
_tutor = None


def ask(question: str, lang: str, channel: str, simple: bool = False) -> dict:
    question = (question or "").strip()
    if not question:
        return dict(UNMATCHED)
    import_path = (os.environ.get("CORE_ASK_IMPORT") or "").strip()
    url = (os.environ.get("CORE_ASK_URL") or "").strip()
    try:
        if import_path:
            raw = _ask_import(import_path, question, lang, channel, simple)
        elif url:
            raw = _ask_http(url, question, lang, channel, simple)
        else:
            raw = _ask_stub(question, lang, channel, simple)
        return _normalise(raw)
    except Exception as exc:  # never crash a channel because the core is down
        # Log the error type only, not the question text.
        log.error("core answer call failed: %s", type(exc).__name__)
        return dict(UNMATCHED)


def using_stub() -> bool:
    return not (os.environ.get("CORE_ASK_IMPORT") or os.environ.get("CORE_ASK_URL"))


def _ask_tutor(question, lang, simple):
    """Use the same retrieval and configured AI provider as the web assistant."""
    global _tutor
    if _tutor is None:
        from server.tutor import Tutor
        _tutor = Tutor()
    result = _tutor.ask(question, lang=lang, simple=simple)
    return {
        "answer": result["answer"],
        "matched": result.get("grounded", False),
        "citations": [
            {"page": c.get("url", ""), "heading": c.get("title", "")}
            for c in result.get("citations", [])
        ],
    }


def _normalise(raw) -> dict:
    if not isinstance(raw, dict):
        return dict(UNMATCHED)
    answer = str(raw.get("answer") or "").strip()
    citations = []
    for c in raw.get("citations") or []:
        if isinstance(c, dict):
            citations.append({"page": str(c.get("page") or ""), "heading": str(c.get("heading") or "")})
    matched = bool(raw.get("matched", bool(answer))) and bool(answer)
    return {"answer": answer if matched else "", "citations": citations if matched else [], "matched": matched}


# ---------------------------------------------------------------- real: Python import
def _ask_import(path, question, lang, channel, simple):
    module_name, _, func_name = path.partition(":")
    func = getattr(importlib.import_module(module_name), func_name or "ask")
    return func(question=question, lang=lang, channel=channel, simple=simple)


# ---------------------------------------------------------------- real: HTTP endpoint
def _ask_http(url, question, lang, channel, simple):
    import httpx

    resp = httpx.post(
        url, json={"question": question, "lang": lang, "channel": channel, "simple": simple}, timeout=30
    )
    resp.raise_for_status()
    return resp.json()


# ================================================================ STUB ===============
# STUB - NOT THE REAL ASSISTANT. Three canned answers so every channel can be demoed
# before the retrieval / AI provider work is merged. Delete nothing here when the real
# core arrives: just set CORE_ASK_IMPORT or CORE_ASK_URL.
_STUB_KB = [
    {
        "keywords": ["future", "ai", "replace", "industry", "ኤአይ", "ወደፊት", "ኢንዱስትሪ"],
        "citation": {"page": "concept-with-navigation.html", "heading": "The Future of the VA Industry"},
        "en": "The Virtual Assistant profession is not shrinking, it is evolving. AI tools take over routine drafting and summarising, while human assistants add the most value through judgement, communication and trust.",
        "am": "የቨርቹዋል ረዳት ሙያ እየቀነሰ አይደለም፤ እየተለወጠ ነው። የኤአይ መሣሪያዎች መደበኛ የጽሑፍና የማጠቃለያ ስራዎችን ይረዳሉ፤ ሰው የሆኑ ረዳቶች ግን በማመዛዘን፣ በተግባቦትና በታማኝነት የላቀ ዋጋ ይጨምራሉ።",
        "en_simple": "VA work is changing, not ending. AI helps with simple tasks. People are still needed for judgement and communication.",
        "am_simple": "የቨርቹዋል ረዳት ስራ እየተለወጠ ነው እንጂ አያበቃም። ኤአይ ቀላል ስራዎችን ያግዛል። ለማመዛዘንና ለተግባቦት ሰው አሁንም ያስፈልጋል።",
    },
    {
        "keywords": ["skill", "skills", "aspiring", "learn", "ክህሎት", "ክህሎቶች"],
        "citation": {
            "page": "concept-with-navigation.html",
            "heading": "What This Means for Aspiring Virtual Assistants",
        },
        "en": "Aspiring Virtual Assistants should build strong communication, organisation and digital skills, and learn to work with AI tools rather than compete with them.",
        "am": "ቨርቹዋል ረዳት መሆን የሚፈልጉ ሰዎች ጠንካራ የተግባቦት፣ የአደረጃጀትና የዲጂታል ክህሎቶችን ማዳበር እንዲሁም ከኤአይ መሣሪያዎች ጋር አብሮ መስራትን መማር አለባቸው።",
        "en_simple": "Build communication, organisation and digital skills. Learn to use AI tools.",
        "am_simple": "የተግባቦት፣ የአደረጃጀትና የዲጂታል ክህሎቶችን ያዳብሩ። የኤአይ መሣሪያዎችን መጠቀም ይማሩ።",
    },
    {
        "keywords": ["graduate", "graduation", "threshold", "pass", "70", "መመረቅ", "ለመመረቅ", "ምረቃ"],
        "citation": {"page": "homepage-v1-self-paced.html", "heading": "Course progression"},
        "en": "You need to reach the 70% course progression threshold to graduate. Your homepage gauge shows how far you are.",
        "am": "ለመመረቅ የትምህርት ሂደትዎ 70% መድረስ አለበት። በመነሻ ገጽዎ ላይ ያለው መለኪያ የደረሱበትን ያሳያል።",
        "en_simple": "You need 70% course progress to graduate.",
        "am_simple": "ለመመረቅ 70% የትምህርት ሂደት ያስፈልግዎታል።",
    },
]


def _ask_stub(question, lang, channel, simple):
    text = question.lower()
    words = set(re.findall(r"\w+", text))
    for entry in _STUB_KB:
        if any((k in words) or (not k.isascii() and k in text) for k in entry["keywords"]):
            key = ("am" if lang == "am" else "en") + ("_simple" if simple else "")
            return {"answer": entry[key], "citations": [entry["citation"]], "matched": True}
    return dict(UNMATCHED)
