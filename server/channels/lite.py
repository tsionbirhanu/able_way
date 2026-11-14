"""/lite - a no-JavaScript, low-bandwidth page: one form, one answer."""
import asyncio

from fastapi import APIRouter, Form, Request

from . import core_client
from .strings import norm_lang
from .web import render

router = APIRouter(prefix="/lite", tags=["lite"])


def _log(question, lang, matched):
    try:
        from server.teacher.question_log import log_question

        log_question(question, lang, "lite", matched)
    except ImportError:  # teacher module not merged yet
        pass


@router.get("")
@router.get("/", include_in_schema=False)
async def lite_form(request: Request, lang: str = "en"):
    return render(request, "lite.html", lang, question="", result=None, error=None)


@router.post("")
@router.post("/", include_in_schema=False)
async def lite_ask(request: Request, question: str = Form(""), lang: str = Form("en")):
    lang = norm_lang(lang)
    question = question.strip()[:1000]
    if not question:
        return render(request, "lite.html", lang, question="", result=None, error="empty_question")
    result = await asyncio.to_thread(core_client.ask, question, lang, "lite", True)
    _log(question, lang, result["matched"])
    return render(request, "lite.html", lang, question=question, result=result, error=None)
