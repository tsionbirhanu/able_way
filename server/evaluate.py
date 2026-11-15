"""How often does Mimi cite the right part of the course, and refuse what is not in it?

    python server/evaluate.py            offline answers only (free, repeatable, no internet)
    python server/evaluate.py --cloud    with the AI providers in ABLEWAY_PROVIDERS (uses quota)

Questions and expected sources: server/data/eval.json. Prints one line per question and the score.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

EVAL_FILE = HERE / "data" / "eval.json"


def judge(item: dict, result: dict) -> bool:
    cited = result.get("citations") or []
    if item.get("refuse"):
        return not cited and not result.get("grounded")
    for c in cited:
        place = f"{c.get('title', '')} {c.get('url', '')}"
        if any(word.lower() in place.lower() for word in item["expect"]):
            return True
    return False


def run(cloud: bool = False) -> tuple[int, int, list[tuple[bool, dict, dict]]]:
    from tutor import Tutor

    saved = os.environ.get("ABLEWAY_PROVIDERS")
    if not cloud:
        os.environ["ABLEWAY_PROVIDERS"] = "offline"
    try:
        tutor = Tutor()
    finally:  # leave the environment as it was (the tests run in one process)
        if saved is None:
            os.environ.pop("ABLEWAY_PROVIDERS", None)
        else:
            os.environ["ABLEWAY_PROVIDERS"] = saved
    rows = []
    for item in json.loads(EVAL_FILE.read_text(encoding="utf-8"))["questions"]:
        result = tutor.ask(item["q"], lang=item["lang"], cloud=cloud)
        rows.append((judge(item, result), item, result))
    return sum(ok for ok, _, _ in rows), len(rows), rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cloud", action="store_true", help="use the AI providers (default: offline answers only)")
    args = parser.parse_args()
    if args.cloud:
        import app  # noqa: F401  (loads .env, as the server does)
    passed, total, rows = run(cloud=args.cloud)
    for ok, item, result in rows:
        source = (result.get("citations") or [{}])[0].get("title", "(none: not in the course)")
        print(f"{'PASS' if ok else 'FAIL'}  [{item['lang']}] {item['q']}\n      -> {source}  ({result.get('provider')})")
    refusals = [r for r in rows if r[1].get("refuse")]
    print(f"\nScore: {passed}/{total}  "
          f"(right source {sum(ok for ok, i, _ in rows if not i.get('refuse'))}/{total - len(refusals)}, "
          f"refused off-topic {sum(ok for ok, _, _ in refusals)}/{len(refusals)})")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
