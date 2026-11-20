"""Start Mimi: one server for everything.

    .venv\\Scripts\\python run.py          (Windows)
    .venv/bin/python run.py              (macOS, Linux)

    http://localhost:8000/pages/concept-with-navigation.html   the Savanna pages with Mimi
    http://localhost:8000/handoff/console                      tutor console (talk to a person)
    http://localhost:8000/teacher, /lite, /sms/simulator        teacher view, low-bandwidth page, SMS

Press Ctrl+C to stop. RUN_PORT=9000 python run.py uses another port.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PORT = int(os.environ.get("RUN_PORT", "8000"))


def main() -> int:
    os.chdir(ROOT)
    sys.path.insert(0, str(ROOT))
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        import uvicorn
    except ImportError:
        print("FastAPI and uvicorn are not installed here. Run:  pip install -r requirements.txt")
        return 1

    from server.main import app
    from server.tutor_api import startup_report

    startup_report()
    print(
        "\n"
        f"  Pages and Mimi:    http://localhost:{PORT}/pages/concept-with-navigation.html\n"
        f"  Tutor console:     http://localhost:{PORT}/handoff/console\n"
        f"  Teacher view:      http://localhost:{PORT}/teacher\n"
        f"  Low-bandwidth:     http://localhost:{PORT}/lite\n"
        f"  SMS simulator:     http://localhost:{PORT}/sms/simulator\n"
        f"  API contract:      http://localhost:{PORT}/docs\n"
        "  Press Ctrl+C to stop.\n",
        flush=True,
    )
    try:
        uvicorn.run(app, host=os.environ.get("RUN_HOST", "127.0.0.1"), port=PORT)
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
