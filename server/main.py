"""The one Mimi server: the site and the tutor, and the help desk with its channels.

Run with:   python run.py                         (or: uvicorn server.main:app --port 8000)
Then open:  http://localhost:8000/pages/concept-with-navigation.html

    server/tutor_api.py       the pages, Mimi's answers, voice, /api/..., /docs (the API contract)
    server/channels/, handoff/, jobs/, teacher/
                              Telegram, SMS, /lite, talk to a person, job alerts, teacher view
"""
import os

from fastapi import FastAPI  # type: ignore[reportMissingImports]

# Telegram, SMS and /lite answer with the same tutor as the web page (server/core_bridge.py).
os.environ.setdefault("CORE_ASK_IMPORT", "server.core_bridge:ask")

# The generated documentation of every route is at /api-docs; /docs is the hand-written API contract
# (openapi.yaml), the page a host or a judge starts from.
app = FastAPI(title="Mimi: multilingual tutor and live help", docs_url="/api-docs", redoc_url=None)

# --- the tutor: answers, voice, the API contract ---
from server.tutor_api import router as tutor_router; app.include_router(tutor_router)  # noqa: E402

# --- the help desk and channels ---
from server.channels.lite import router as lite_router; app.include_router(lite_router)  # noqa: E402
from server.channels.sms import router as sms_router; app.include_router(sms_router)  # noqa: E402
from server.channels.telegram_bot import router as telegram_router; app.include_router(telegram_router)  # noqa: E402
from server.jobs.router import router as jobs_router; app.include_router(jobs_router)  # noqa: E402
from server.channels.accommodation import router as accommodation_router; app.include_router(accommodation_router)  # noqa: E402
from server.handoff.router import router as handoff_router; app.include_router(handoff_router)  # noqa: E402
from server.teacher.router import router as teacher_router; app.include_router(teacher_router)  # noqa: E402

# --- the site's files (index.html, pages/, assets/, module/, demo/): last, so every route above wins ---
from server.tutor_api import site_router; app.include_router(site_router)  # noqa: E402
