"""Start the one Mimi server (the same as `python run.py`).

    python server/app.py            then open http://localhost:8000/pages/concept-with-navigation.html

Kept so existing start commands keep working, for example on Render:
    ABLEWAY_HOST=0.0.0.0 ABLEWAY_PORT=$PORT python server/app.py

The tutor itself is now server/tutor_api.py, part of the FastAPI app in server/main.py. Its helpers
are re-exported here for older code and tests that `import app`.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from server.tutor_api import resolve_language, validate  # noqa: E402,F401


def main() -> None:
    import uvicorn

    from server.main import app
    from server.tutor_api import startup_report

    port = int(os.environ.get("ABLEWAY_PORT") or os.environ.get("PORT") or "8000")
    host = os.environ.get("ABLEWAY_HOST", "127.0.0.1")
    startup_report()
    print(f"Open http://{host if host != '0.0.0.0' else 'localhost'}:{port}/pages/concept-with-navigation.html  (Ctrl+C to stop)", flush=True)
    uvicorn.run(app, host=host, port=port, proxy_headers=True, forwarded_allow_ips="*")


if __name__ == "__main__":
    main()
