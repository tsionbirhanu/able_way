"""Start the whole project from one terminal.

    server\\.venv\\Scripts\\python run.py          (Windows)
    server/.venv/bin/python run.py              (macOS, Linux)

It starts the two servers side by side and stops both on Ctrl+C:

    tutor     http://localhost:8001   the Savanna pages, Mimi (AI answers, voice), /api/...
    channels  http://localhost:8000   talk to a person, Telegram, SMS, /lite, jobs, teacher view

Open the pages on the tutor: http://localhost:8001/pages/concept-with-navigation.html
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TUTOR_PORT = int(os.environ.get("RUN_TUTOR_PORT", "8001"))  # override only for testing
CHANNELS_PORT = int(os.environ.get("RUN_CHANNELS_PORT", "8000"))


def main() -> int:
    python = sys.executable
    base = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1"}
    # The widget expects the tutor on 8001 and the channels server on 8000, whatever .env says.
    tutor_env = {**base, "ABLEWAY_PORT": str(TUTOR_PORT)}
    channels_env = {**base, "CORE_ASK_IMPORT": base.get("CORE_ASK_IMPORT") or "server.core_bridge:ask"}

    processes = [
        ("tutor", subprocess.Popen([python, "server/app.py"], cwd=ROOT, env=tutor_env)),
        ("channels", subprocess.Popen(
            [python, "-m", "uvicorn", "server.main:app", "--port", str(CHANNELS_PORT)], cwd=ROOT, env=channels_env)),
    ]
    time.sleep(3)
    print(
        "\n"
        f"  Pages and Mimi:    http://localhost:{TUTOR_PORT}/pages/concept-with-navigation.html\n"
        f"  Tutor console:     http://localhost:{CHANNELS_PORT}/handoff/console\n"
        f"  Teacher view:      http://localhost:{CHANNELS_PORT}/teacher\n"
        f"  Low-bandwidth:     http://localhost:{CHANNELS_PORT}/lite\n"
        f"  SMS simulator:     http://localhost:{CHANNELS_PORT}/sms/simulator\n"
        "  Press Ctrl+C to stop both servers.\n",
        flush=True,
    )
    try:
        while True:
            for name, process in processes:
                if process.poll() is not None:
                    print(f"\nThe {name} server stopped (exit code {process.returncode}). Stopping the other one.")
                    return process.returncode or 1
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping…")
        return 0
    finally:
        for _, process in processes:
            if process.poll() is None:
                if os.name == "nt":
                    process.terminate()
                else:
                    process.send_signal(signal.SIGINT)
        for _, process in processes:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()


if __name__ == "__main__":
    sys.exit(main())
