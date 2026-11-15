"""Interview accommodation requests - PRIVATE.

Stored in a SEPARATE database file (data/accommodations.db), never in data/channels.db.
Nothing in this module may call log_question, ask(), or write request content to a logger.
The teacher view has no access to this file.
"""
import sqlite3
from contextlib import contextmanager

from fastapi import APIRouter, Form, Request

from .config import accommodations_db_path
from .strings import norm_lang, t
from .web import render

router = APIRouter(prefix="/accommodation", tags=["accommodation"])

_SCHEMA = """
CREATE TABLE IF NOT EXISTS accommodation_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job TEXT NOT NULL, support TEXT NOT NULL, contact TEXT NOT NULL,
    lang TEXT NOT NULL, channel TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


@contextmanager
def _connect():
    path = accommodations_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), timeout=10)
    try:
        conn.executescript(_SCHEMA)
        yield conn
        conn.commit()
    finally:
        conn.close()


def save_request(job: str, support: str, contact: str, lang: str, channel: str) -> None:
    with _connect() as c:
        c.execute(
            "INSERT INTO accommodation_requests (job, support, contact, lang, channel) VALUES (?,?,?,?,?)",
            (job.strip()[:300], support.strip()[:2000], contact.strip()[:300], norm_lang(lang), channel),
        )
    # Tell the platform's staff that a request is waiting: the event only, never its content.
    from . import webhook

    webhook.send("accommodation.requested", {"channel": channel, "lang": norm_lang(lang)})


def list_requests() -> list[dict]:
    with _connect() as c:
        c.row_factory = sqlite3.Row
        rows = c.execute("SELECT * FROM accommodation_requests ORDER BY id DESC").fetchall()
    return [dict(r) for r in rows]


def delete_request(request_id: int) -> None:
    with _connect() as c:
        c.execute("DELETE FROM accommodation_requests WHERE id=?", (request_id,))


def _job_options():
    from server.jobs.store import load_jobs

    return ["{} - {}".format(j["title"], j["company"]) for j in load_jobs()]


# ------------------------------------------------------------------ staff page: a person handles each request
# Behind the tutor console's password. Requests are deleted once handled (keep no more than needed).
@router.get("/requests")
async def staff_list(request: Request):
    from fastapi.responses import RedirectResponse

    from server.handoff.router import is_tutor

    if not is_tutor(request.cookies):
        return RedirectResponse("/handoff/console", status_code=303)
    return render(request, "accommodation_requests.html", "en", requests=list_requests())


@router.post("/requests/{request_id}/done")
async def staff_done(request: Request, request_id: int):
    from fastapi.responses import JSONResponse, RedirectResponse

    from server.handoff.router import is_tutor

    if not is_tutor(request.cookies):
        return JSONResponse({"error": "tutor login required"}, status_code=401)
    delete_request(request_id)
    return RedirectResponse("/accommodation/requests", status_code=303)


# ------------------------------------------------------------------ web form (no JavaScript)
@router.get("")
async def form(request: Request, lang: str = "en"):
    return render(request, "accommodation.html", lang, jobs=_job_options(), done=False, error=None, values={})


@router.post("")
async def submit(
    request: Request,
    job: str = Form(""),
    job_text: str = Form(""),
    support: str = Form(""),
    contact: str = Form(""),
    lang: str = Form("en"),
):
    lang = norm_lang(lang)
    chosen = job_text.strip() or job.strip()
    if not (chosen and support.strip() and contact.strip()):
        values = {"job": job, "job_text": job_text, "support": support, "contact": contact}
        return render(request, "accommodation.html", lang, status_code=400, jobs=_job_options(),
                      done=False, error="acc_missing", values=values)
    save_request(chosen, support, contact, lang, "web")
    # The confirmation page does not repeat what was submitted.
    return render(request, "accommodation.html", lang, jobs=[], done=True, error=None, values={})


# ------------------------------------------------------------------ Telegram step-by-step flow
async def telegram_start(chat_id, arg, lang):
    from . import telegram_bot

    telegram_bot._flows[str(chat_id)] = {"name": "accommodation", "step": 1, "data": {}}
    return [t(lang, "acc_tg_step1")]


async def telegram_step(chat_id, text, lang, flow):
    from . import telegram_bot

    if flow["step"] == 1:
        flow["data"]["job"] = text
        flow["step"] = 2
        return [t(lang, "acc_tg_step2")]
    if flow["step"] == 2:
        flow["data"]["support"] = text
        flow["step"] = 3
        return [t(lang, "acc_tg_step3")]
    telegram_bot._flows.pop(str(chat_id), None)
    save_request(flow["data"]["job"], flow["data"]["support"], text, lang, "telegram")
    return [t(lang, "acc_thanks")]
