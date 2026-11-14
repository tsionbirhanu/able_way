"""Telegram bot using long polling (no public URL needed).

Started from this router's lifespan, so the shared entry point only needs include_router.
If TELEGRAM_BOT_TOKEN is missing the bot is skipped with a warning and the server still starts.

Privacy: message text and chat ids are never written to the logs.
"""
import asyncio
import logging
from contextlib import asynccontextmanager

import httpx
from fastapi import APIRouter

from server.teacher.question_log import log_question

from . import core_client
from .config import log as _base_log
from .config import telegram_token
from .db import get_lang, set_lang
from .strings import format_citations, norm_lang, t

log = _base_log.getChild("telegram")
# httpx logs full request URLs at INFO, and Telegram URLs contain the bot token.
logging.getLogger("httpx").setLevel(logging.WARNING)

API = "https://api.telegram.org/bot{token}/{method}"
TG_LIMIT = 4000

_state = {"client": None, "task": None, "running": False, "username": None}
_flows = {}  # chat_id -> {"name": str, "step": int, "data": dict}; in memory only
_tasks = set()

# Filled in below and by later feature blocks: "/command" -> async f(chat_id, arg, lang) -> list[str]
COMMANDS = {}
# Flow handlers: name -> async f(chat_id, text, lang, flow) -> list[str]
FLOWS = {}
# Optional interceptor for "talking to a human" mode: async f(chat_id, text, lang) -> list[str] | None
_interceptors = []


def is_running() -> bool:
    return bool(_state["running"])


async def send_message(chat_id, text: str) -> bool:
    """Send a plain-text message. Returns False if the bot is not running or Telegram refused."""
    client, token = _state["client"], telegram_token()
    if not (client and token and _state["running"]):
        return False
    try:
        resp = await client.post(
            API.format(token=token, method="sendMessage"),
            json={"chat_id": chat_id, "text": text[:TG_LIMIT], "disable_web_page_preview": True},
        )
        return resp.status_code == 200
    except httpx.HTTPError as exc:
        log.warning("sendMessage failed: %s", type(exc).__name__)
        return False


# ------------------------------------------------------------------ message handling
async def handle_message(chat_id, text: str) -> list:
    """Turn one incoming text into a list of reply texts. Pure enough to unit test."""
    chat_id = str(chat_id)
    text = (text or "").strip()
    lang = get_lang("telegram", chat_id)
    if not text:
        return [t(lang, "tg_text_only")]

    if text.startswith("/"):
        head, _, arg = text.partition(" ")
        command = head.split("@")[0].lower()
        if command == "/cancel":
            had_flow = _flows.pop(chat_id, None) is not None
            return [t(lang, "tg_cancelled" if had_flow else "tg_nothing_to_cancel")]
        handler = COMMANDS.get(command)
        if handler:
            _flows.pop(chat_id, None)  # starting another command abandons a half-done flow
            return await handler(chat_id, arg.strip(), lang)
        return [t(lang, "tg_help")]

    flow = _flows.get(chat_id)
    if flow:  # e.g. accommodation: goes to its own handler, never to ask() or the question log
        return await FLOWS[flow["name"]](chat_id, text, lang, flow)

    for interceptor in _interceptors:  # e.g. an open chat with a human tutor
        replies = await interceptor(chat_id, text, lang)
        if replies is not None:
            return replies

    result = await asyncio.to_thread(core_client.ask, text, lang, "telegram", False)
    log_question(text, lang, "telegram", result["matched"])  # no chat id is passed
    if not result["matched"]:
        return [t(lang, "dont_know") + "\n" + t(lang, "tg_offer_human")]
    reply = result["answer"]
    sources = format_citations(result["citations"], lang)
    return [reply + ("\n\n" + sources if sources else "")]


async def _cmd_start(chat_id, arg, lang):
    return [t(lang, "tg_start"), t(lang, "tg_lang_prompt")]


async def _cmd_help(chat_id, arg, lang):
    return [t(lang, "tg_help")]


async def _cmd_lang(chat_id, arg, lang):
    if arg.lower() not in ("am", "en", "amharic", "english", "አማርኛ", "እንግሊዝኛ"):
        return [t(lang, "tg_lang_prompt")]
    lang = norm_lang(arg)
    set_lang("telegram", chat_id, lang)
    return [t(lang, "tg_lang_set")]


COMMANDS.update({"/start": _cmd_start, "/help": _cmd_help, "/lang": _cmd_lang})


# ------------------------------------------------------------------ long polling
async def _handle_update(update: dict) -> None:
    message = update.get("message") or {}
    chat_id = (message.get("chat") or {}).get("id")
    if chat_id is None:
        return
    try:
        replies = await handle_message(chat_id, message.get("text") or "")
    except Exception as exc:
        log.error("handler error: %s", type(exc).__name__)
        return
    for reply in replies:
        await send_message(chat_id, reply)


async def _poll_forever(token: str) -> None:
    client = _state["client"]
    offset = None
    try:
        me = await client.get(API.format(token=token, method="getMe"))
        if me.status_code != 200:
            log.error("Telegram rejected TELEGRAM_BOT_TOKEN (HTTP %s). Bot not started.", me.status_code)
            return
        _state["username"] = me.json().get("result", {}).get("username")
        await client.post(API.format(token=token, method="deleteWebhook"))
    except httpx.HTTPError as exc:
        log.error("Cannot reach Telegram (%s). Bot not started.", type(exc).__name__)
        return
    _state["running"] = True
    log.info("Telegram bot @%s is polling.", _state["username"])
    while True:
        try:
            params = {"timeout": 25, "allowed_updates": '["message"]'}
            if offset is not None:
                params["offset"] = offset
            resp = await client.get(API.format(token=token, method="getUpdates"), params=params)
            if resp.status_code == 409:
                log.warning("Another process is polling with the same bot token. Retrying in 10s.")
                await asyncio.sleep(10)
                continue
            if resp.status_code != 200:
                await asyncio.sleep(5)
                continue
            for update in resp.json().get("result", []):
                offset = update["update_id"] + 1
                task = asyncio.create_task(_handle_update(update))
                _tasks.add(task)
                task.add_done_callback(_tasks.discard)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # network blips: keep polling
            log.warning("polling error: %s", type(exc).__name__)
            await asyncio.sleep(5)


async def start() -> None:
    token = telegram_token()
    if not token:
        log.warning("TELEGRAM_BOT_TOKEN is not set: Telegram bot skipped. Everything else still works.")
        return
    if _state["task"]:
        return
    _state["client"] = httpx.AsyncClient(timeout=40)
    _state["task"] = asyncio.create_task(_poll_forever(token))


async def stop() -> None:
    task, client = _state["task"], _state["client"]
    _state.update(task=None, client=None, running=False)
    if task:
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass
    if client:
        await client.aclose()


@asynccontextmanager
async def _lifespan(app):
    await start()
    try:
        yield
    finally:
        await stop()


router = APIRouter(prefix="/telegram", tags=["telegram"], lifespan=_lifespan)


@router.get("/status")
async def status():
    """For the demo: is the bot configured and polling?"""
    return {"configured": bool(telegram_token()), "running": is_running(), "username": _state["username"]}
