"""Does Mimi give the same answer in Amharic, English and Afaan Oromo? Uses the real AI (your key).

    python server/consistency.py

The same questions are asked in the three languages. For each, it shows the source Mimi cited and
whether the facts (the numbers the course gives) are all in the answer, and flags Latin-letter words
inside an Amharic answer (words that should have been Amharic). Each run uses about 20 AI calls.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "server"))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import server.tutor_api  # noqa: E402  (reads .env and builds the tutor exactly as the server does)

QUESTIONS = [
    {"en": "What is the late submission policy?", "am": "የዘገየ ማስረከቢያ ደንብ ምንድን ነው?",
     "om": "Imaammanni yeroo darbee galchuu maali?", "facts": ["7", "85", "5"]},
    {"en": "Can I resubmit an assignment?", "am": "የቤት ሥራን እንደገና ማስገባት እችላለሁ?",
     "om": "Hojii manaa irra deebi'ee galchuu nan danda'aa?", "facts": ["85", "5"]},
    {"en": "What are the evaluation quizzes?", "am": "የግምገማ ፈተናዎች ምንድን ናቸው?",
     "om": "Qormaatni madaallii maali?", "facts": []},
    {"en": "Who won the World Cup?", "am": "የዓለም ዋንጫን ማን አሸነፈ?", "om": "Eenyutu Waancaa Addunyaa mo'e?",
     "facts": None},  # None: must be refused in every language
]
ALLOWED_LATIN = {"WR", "VA", "AI"}


def main() -> int:
    tutor = server.tutor_api.tutor
    problems = 0
    for row in QUESTIONS:
        print(f"\n{row['en']}")
        sources = set()
        for lang in ("en", "am", "om"):
            r = tutor.ask(row[lang], lang, cloud=True)
            source = r["citations"][0]["title"] if r["citations"] else "-"
            digits = set(re.findall(r"\d+", r["answer"]))
            notes = []
            if row["facts"] is None:
                ok = not r["grounded"]
                notes.append("refused" if ok else "ANSWERED (should be refused)")
            else:
                missing = [f for f in row["facts"] if f not in digits]
                ok = r["grounded"] and not missing
                notes.append("facts ok" if ok else f"MISSING {missing or 'answer'}")
                sources.add(source)
            if lang == "am":
                inside = re.sub(r"\([^)]*\)", " ", r["answer"])  # an English term in brackets is fine
                latin = [w for w in re.findall(r"[A-Za-z]{3,}", inside) if w not in ALLOWED_LATIN]
                if latin:
                    ok = False
                    notes.append(f"LATIN WORDS {latin[:5]}")
            problems += not ok
            print(f"  {lang}  {r.get('provider', '?'):8s} {source[:50]:50s} {'; '.join(notes)}")
        if row["facts"] is not None and len(sources) > 1:
            print("  NOTE: the languages cited different first sources")
    print(f"\n{problems} problem(s).")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
