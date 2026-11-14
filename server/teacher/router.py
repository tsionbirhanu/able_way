"""/teacher - anonymous overview of what learners ask.

Reads ONLY the question_log table in data/channels.db. It has no access to accommodation
requests (separate database file) or to tickets, chat messages, subscriptions or phone numbers.
"""
from fastapi import APIRouter, Request

from server.channels.db import connect
from server.channels.web import render

router = APIRouter(prefix="/teacher", tags=["teacher"])


def stats() -> dict:
    with connect() as c:
        total = c.execute("SELECT COUNT(*) AS n FROM question_log").fetchone()["n"]
        top = c.execute(
            "SELECT normalised, MIN(question) AS example, COUNT(*) AS n, "
            "SUM(CASE WHEN matched=0 THEN 1 ELSE 0 END) AS unknown, MAX(asked_on) AS last_asked "
            "FROM question_log GROUP BY normalised ORDER BY n DESC, last_asked DESC LIMIT 20").fetchall()
        by_lang = c.execute(
            "SELECT lang, COUNT(*) AS n FROM question_log GROUP BY lang ORDER BY n DESC").fetchall()
        by_channel = c.execute(
            "SELECT channel, COUNT(*) AS n FROM question_log GROUP BY channel ORDER BY n DESC").fetchall()
        unknown = c.execute(
            "SELECT normalised, MIN(question) AS example, lang, COUNT(*) AS n, MAX(asked_on) AS last_asked "
            "FROM question_log WHERE matched=0 GROUP BY normalised, lang "
            "ORDER BY n DESC, last_asked DESC LIMIT 50").fetchall()
    return {
        "total": total,
        "top": [dict(r) for r in top],
        "by_lang": [dict(r) for r in by_lang],
        "by_channel": [dict(r) for r in by_channel],
        "unknown": [dict(r) for r in unknown],
    }


@router.get("")
async def teacher_view(request: Request):
    return render(request, "teacher.html", "en", s=stats())


@router.get("/stats.json")
async def teacher_json():
    return stats()
