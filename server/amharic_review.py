"""Build docs/amharic_review.csv: every Amharic text Mimi uses, next to its English, for a native speaker.

    python server/amharic_review.py

Open the file in Google Sheets or Excel. For each row, mark "Natural?" yes or no and write a better
Amharic version when needed. Then update the file named in the "Where" column (module/i18n/am.json,
server/tutor.py, server/channels/strings.py, server/data/glossary_am.json).
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT))


def flatten(value, prefix=""):
    """{"menu": {"intro": "..."}} -> {"menu.intro": "..."}; lists get [n]."""
    if isinstance(value, dict):
        for key, item in value.items():
            yield from flatten(item, f"{prefix}.{key}" if prefix else key)
    elif isinstance(value, list):
        for n, item in enumerate(value):
            yield from flatten(item, f"{prefix}[{n}]")
    else:
        yield prefix, str(value)


def rows():
    # 1. The fixed course terms the AI must use in every Amharic answer (the most likely odd word).
    from tutor import AMHARIC_NOTE, TEXT

    for english, amharic in re.findall(r"([a-z][a-z ]+?) = ([^;.]+?)(?=;|\. )", AMHARIC_NOTE):
        yield ("AI course terms", "server/tutor.py (AMHARIC_NOTE)", english.strip(), english.strip(), amharic.strip())
    # 2. Fixed replies of the tutor ("not in the course", "working offline", ...).
    for key, english in TEXT["en"].items():
        yield ("Tutor replies", "server/tutor.py (TEXT)", key, english, TEXT["am"].get(key, ""))
    # 3. Everything the web widget shows or says.
    en = dict(flatten(json.loads((ROOT / "module/i18n/en.json").read_text(encoding="utf-8"))))
    am = dict(flatten(json.loads((ROOT / "module/i18n/am.json").read_text(encoding="utf-8"))))
    for key, english in en.items():
        if key.startswith(("meta.", "pronounce.")):
            continue
        yield ("Web widget", "module/i18n/am.json", key, english, am.get(key, ""))
    for key, said in am.items():
        if key.startswith("pronounce."):
            yield ("Voice: how words are read aloud", "module/i18n/am.json (pronounce)", key[10:], key[10:], said)
    # 4. Telegram, SMS, the help chat and the accommodation form.
    from server.channels.strings import STRINGS

    for key, entry in STRINGS.items():
        if "am" in entry:
            yield ("Telegram, SMS, help chat", "server/channels/strings.py", key, entry["en"], entry["am"])
    # 5. The word list that turns Amharic questions into English search words.
    glossary = json.loads((HERE / "data/glossary_am.json").read_text(encoding="utf-8"))
    for amharic, english in glossary.items():
        yield ("Search word list (Amharic -> English)", "server/data/glossary_am.json", amharic, english, amharic)


def main() -> None:
    out = ROOT / "docs" / "amharic_review.csv"
    out.parent.mkdir(exist_ok=True)
    count = 0
    # utf-8-sig: Excel then shows the Ge'ez letters correctly.
    with out.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Area", "Where", "Key", "English", "Amharic now", "Natural? (yes/no)", "Better Amharic", "Notes"])
        for area, where, key, english, amharic in rows():
            writer.writerow([area, where, key, english, amharic, "", "", ""])
            count += 1
    print(f"Wrote {count} rows to {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
