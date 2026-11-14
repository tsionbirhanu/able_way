"""Server entry point (shared file).

Run with:  uvicorn server.main:app --reload
Keep this file append-only: one include_router line per router.
"""
from fastapi import FastAPI  # type: ignore[reportMissingImports]

app = FastAPI(title="ALX multilingual assistant")

# --- appended by feature/channels-handoff (Person 3 + 4) ---
from server.channels.lite import router as lite_router; app.include_router(lite_router)
from server.channels.sms import router as sms_router; app.include_router(sms_router)
from server.channels.telegram_bot import router as telegram_router; app.include_router(telegram_router)
from server.jobs.router import router as jobs_router; app.include_router(jobs_router)
from server.channels.accommodation import router as accommodation_router; app.include_router(accommodation_router)
from server.handoff.router import router as handoff_router; app.include_router(handoff_router)
from server.teacher.router import router as teacher_router; app.include_router(teacher_router)
