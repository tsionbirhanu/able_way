"""Telegram bot using long polling (no public URL needed).

Started from this router's lifespan, so the shared entry point only needs include_router.
If TELEGRAM_BOT_TOKEN is missing the bot is skipped with a warning and the server still starts.

Privacy: message text and chat ids are never written to the logs.
"""
import asyncio
import logging
import re
import secrets
from collections import OrderedDict
from contextlib import asynccontextmanager

import httpx
from fastapi import APIRouter

from server.teacher.question_log import log_question

from . import core_client, voice
from .config import log as _base_log
from .config import telegram_token
from .db import forget, get_consent, get_lang, get_voice, set_consent, set_lang, set_voice
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


_ETHIOPIC = re.compile(r"[ሀ-፿]")
_LATIN = re.compile(r"[A-Za-z]")


def question_lang(text: str) -> str | None:
    """'am' for a question in Ge'ez script, 'en' for one in Latin letters, None when unclear
    (numbers, emoji, a single letter)."""
    if _ETHIOPIC.search(text):
        return "am"
    if len(_LATIN.findall(text)) >= 3:
        return "en"
    return None


def is_running() -> bool:
    return bool(_state["running"])


async def send_message(chat_id, text: str, buttons: list | None = None) -> bool:
    """Send a plain-text message, optionally with one row of inline buttons [(label, data)].
    Returns False if the bot is not running or Telegram refused."""
    client, token = _state["client"], telegram_token()
    if not (client and token and _state["running"]):
        return False
    body = {"chat_id": chat_id, "text": text[:TG_LIMIT], "disable_web_page_preview": True}
    if buttons:
        body["reply_markup"] = {"inline_keyboard": [[{"text": label, "callback_data": data} for label, data in buttons]]}
    try:
        resp = await client.post(API.format(token=token, method="sendMessage"), json=body)
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

    # Answer in the language the question is in, as the web widget does: an English question in
    # an Amharic chat gets an English answer (and voice), and the chat now continues in English.
    asked_in = question_lang(text)
    if asked_in and asked_in != lang:
        lang = asked_in
        set_lang("telegram", chat_id, lang)

    cloud = get_consent("telegram", chat_id) is True  # not asked yet, or said no: nothing is sent out
    result = await asyncio.to_thread(core_client.ask, text, lang, "telegram", False, cloud)
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


async def _cmd_voice(chat_id, arg, lang):
    """/voice on | off: every answer also as a voice message, even for typed questions."""
    choice = arg.strip().lower()
    on = choice in ("on", "yes", "1", "አዎ") if choice else not get_voice("telegram", chat_id)
    set_voice("telegram", chat_id, on)
    return [t(lang, "tg_voice_on" if on else "tg_voice_off")]


async def _cmd_privacy(chat_id, arg, lang):
    """/privacy: the current choice and the question again (the buttons are added when sent)."""
    status = {True: "tg_consent_status_yes", False: "tg_consent_status_no"}.get(get_consent("telegram", chat_id))
    return ([t(lang, status)] if status else []) + [t(lang, "tg_consent_ask")]


async def _cmd_forget(chat_id, arg, lang):
    """/forget: delete everything kept about this chat (the learner can delete their data)."""
    forget("telegram", chat_id)
    _flows.pop(str(chat_id), None)
    _pending_voice.pop(str(chat_id), None)
    return [t(lang, "tg_forgotten")]


COMMANDS.update({"/start": _cmd_start, "/help": _cmd_help, "/lang": _cmd_lang, "/voice": _cmd_voice,
                 "/privacy": _cmd_privacy, "/forget": _cmd_forget})


# ------------------------------------------------------------------ consent
# Nothing leaves this server until the learner agrees: questions are answered from the course
# text (or a local model), and voice is off. Asked once, after the first answer, with two buttons.
_pending_voice = {}  # chat_id -> a voice note waiting for the learner's answer; in memory only


def _consent_buttons(lang: str) -> list:
    return [(t(lang, "tg_consent_yes_button"), "consent:yes"), (t(lang, "tg_consent_no_button"), "consent:no")]


async def _ask_consent(chat_id, lang: str) -> None:
    await send_message(chat_id, t(lang, "tg_consent_ask"), _consent_buttons(lang))


# ------------------------------------------------------------------ long polling
async def _handle_update(update: dict) -> None:
    if update.get("callback_query"):
        return await _handle_callback(update["callback_query"])
    message = update.get("message") or {}
    chat_id = (message.get("chat") or {}).get("id")
    if chat_id is None:
        return
    note = message.get("voice") or message.get("audio")
    if note and not message.get("text"):
        return await _handle_voice(chat_id, note)
    text = message.get("text") or ""
    try:
        replies = await handle_message(chat_id, text)
    except Exception as exc:
        log.error("handler error: %s", type(exc).__name__)
        return
    is_command = text.strip().startswith("/")
    if is_command and text.strip().split()[0].split("@")[0].lower() == "/privacy" and replies:
        # The last reply is the question: send it with its two buttons.
        lang = get_lang("telegram", str(chat_id))
        for reply in replies[:-1]:
            await send_message(chat_id, reply)
        return await _ask_consent(chat_id, lang)
    question = bool(text.strip()) and not is_command
    await _deliver(chat_id, replies, question=question, spoken_input=False)
    if question and get_consent("telegram", str(chat_id)) is None:
        await _ask_consent(chat_id, get_lang("telegram", str(chat_id)))


# ------------------------------------------------------------------ answers in voice
# The text of recent answers, so "🔊 Listen" can speak one later. In memory only, never stored.
_answers: "OrderedDict[str, tuple[str, str]]" = OrderedDict()
_ANSWERS_KEPT = 300


def _remember_answer(text: str, lang: str) -> str:
    key = secrets.token_urlsafe(8)
    _answers[key] = (text, lang)
    while len(_answers) > _ANSWERS_KEPT:
        _answers.popitem(last=False)
    return key


async def _deliver(chat_id, replies: list, question: bool, spoken_input: bool) -> None:
    """Send the replies. For an answer to a question: a "🔊 Listen" button under it, and the
    answer in voice straight away when the learner spoke, or turned voice answers on (/voice on)."""
    lang = get_lang("telegram", str(chat_id))  # after the reply: "/lang am" said aloud changes it
    for i, reply in enumerate(replies):
        buttons = None
        if question and i == 0:
            buttons = [(t(lang, "tg_listen_button"), "listen:" + _remember_answer(reply, lang))]
        await send_message(chat_id, reply, buttons)
    allowed = get_consent("telegram", str(chat_id)) is True
    if question and replies and allowed and (spoken_input or get_voice("telegram", str(chat_id))):
        await _say(chat_id, replies[0], lang)


async def _say(chat_id, text: str, lang: str) -> bool:
    if get_consent("telegram", str(chat_id)) is not True:  # voice is made by a cloud service
        await send_message(chat_id, t(lang, "tg_voice_needs_consent"))
        return False
    await _chat_action(chat_id, "record_voice")
    spoken = await asyncio.to_thread(voice.speak, voice.spoken_part(text, lang), lang)
    if spoken and await send_voice(chat_id, *spoken):
        return True
    await send_message(chat_id, t(lang, "tg_voice_unavailable"))
    return False


async def _handle_callback(query: dict) -> None:
    client, token = _state["client"], telegram_token()
    chat_id = ((query.get("message") or {}).get("chat") or {}).get("id")
    data = query.get("data") or ""
    if client and token:
        try:  # stop the button's loading spinner at once
            await client.post(API.format(token=token, method="answerCallbackQuery"), json={"callback_query_id": query.get("id")})
        except httpx.HTTPError:
            pass
    if chat_id is None:
        return
    if data in ("consent:yes", "consent:no"):
        allowed = data == "consent:yes"
        set_consent("telegram", str(chat_id), allowed)
        lang = get_lang("telegram", str(chat_id))
        await send_message(chat_id, t(lang, "tg_consent_yes" if allowed else "tg_consent_no"))
        note = _pending_voice.pop(str(chat_id), None)
        if note and allowed:
            await _handle_voice(chat_id, note)  # the voice message they sent before choosing
        return
    if not data.startswith("listen:"):
        return
    found = _answers.get(data.split(":", 1)[1])
    if not found:
        await send_message(chat_id, t(get_lang("telegram", str(chat_id)), "tg_listen_expired"))
        return
    await _say(chat_id, *found)


# ------------------------------------------------------------------ voice messages
async def _chat_action(chat_id, action: str) -> None:
    client, token = _state["client"], telegram_token()
    if client and token:
        try:
            await client.post(API.format(token=token, method="sendChatAction"), json={"chat_id": chat_id, "action": action})
        except httpx.HTTPError:
            pass


async def _download(file_id: str) -> bytes | None:
    client, token = _state["client"], telegram_token()
    try:
        resp = await client.get(API.format(token=token, method="getFile"), params={"file_id": file_id})
        path = resp.json().get("result", {}).get("file_path")
        if not path:
            return None
        resp = await client.get(f"https://api.telegram.org/file/bot{token}/{path}")
        return resp.content if resp.status_code == 200 and len(resp.content) <= voice.MAX_BYTES else None
    except (httpx.HTTPError, ValueError) as exc:
        log.warning("voice download failed: %s", type(exc).__name__)
        return None


async def send_voice(chat_id, audio: bytes, mime: str) -> bool:
    """A voice reply. Telegram plays MP3 and OGG/Opus as a voice message; other audio as a file."""
    client, token = _state["client"], telegram_token()
    if not (client and token and _state["running"]):
        return False
    if mime in ("audio/mpeg", "audio/ogg"):
        attempts = [("sendVoice", "voice", "mimi.ogg" if mime == "audio/ogg" else "mimi.mp3")]
    else:  # WAV: not a voice message; try as audio, then as a file the learner can still play
        attempts = [("sendAudio", "audio", "mimi.wav"), ("sendDocument", "document", "mimi.wav")]
    for method, field, name in attempts:
        try:
            resp = await client.post(API.format(token=token, method=method), data={"chat_id": str(chat_id)}, files={field: (name, audio, mime)})
        except httpx.HTTPError as exc:
            log.warning("%s failed: %s", method, type(exc).__name__)
            continue
        if resp.status_code == 200:
            return True
        log.warning("%s refused (HTTP %s)", method, resp.status_code)
    return False


async def _handle_voice(chat_id, note: dict) -> None:
    """Voice in, text and voice out: the learner sees what Mimi heard, reads the answer and hears it."""
    lang = get_lang("telegram", str(chat_id))
    consent = get_consent("telegram", str(chat_id))
    if consent is None:  # hearing a voice note needs a cloud service: ask first, keep the note
        _pending_voice[str(chat_id)] = note
        return await _ask_consent(chat_id, lang)
    if consent is False:
        await send_message(chat_id, t(lang, "tg_voice_needs_consent"))
        return
    if voice.too_long(note):
        await send_message(chat_id, t(lang, "tg_voice_too_long"))
        return
    await _chat_action(chat_id, "typing")
    audio = await _download(note.get("file_id", ""))
    if not audio:
        await send_message(chat_id, t(lang, "tg_voice_failed"))
        return
    try:
        heard = await asyncio.to_thread(voice.transcribe, audio, note.get("mime_type") or "audio/ogg", lang)
    except voice.SpeechError as exc:
        log.warning("voice transcription unavailable: %s", type(exc).__name__)
        await send_message(chat_id, t(lang, "tg_voice_failed"))
        return
    if not heard:
        await send_message(chat_id, t(lang, "tg_voice_empty"))
        return
    await send_message(chat_id, t(question_lang(heard) or lang, "tg_voice_heard", text=heard))
    try:
        replies = await handle_message(chat_id, heard)
    except Exception as exc:
        log.error("handler error: %s", type(exc).__name__)
        return
    await _deliver(chat_id, replies, question=True, spoken_input=True)


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
            params = {"timeout": 25, "allowed_updates": '["message", "callback_query"]'}
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


# ------------------------------------------------------------------ jobs commands
async def _cmd_jobs(chat_id, arg, lang):
    from server.jobs.store import format_job, load_jobs, matches

    jobs = [j for j in load_jobs() if matches(j, arg)][:5]
    if not jobs:
        return [t(lang, "jobs_none")]
    return [t(lang, "jobs_header")] + [format_job(j, lang) for j in jobs]


async def _cmd_subscribe(chat_id, arg, lang):
    from server.jobs import alerts

    return [alerts.confirmation(alerts.subscribe("telegram", chat_id, arg, lang), lang)]


async def _cmd_unsubscribe(chat_id, arg, lang):
    from server.jobs import alerts

    return [t(lang, "unsubscribed" if alerts.unsubscribe("telegram", chat_id) else "not_subscribed")]


COMMANDS.update({"/jobs": _cmd_jobs, "/subscribe": _cmd_subscribe, "/unsubscribe": _cmd_unsubscribe})


# ------------------------------------------------------------------ accommodation flow (private)
from . import accommodation as _accommodation  # noqa: E402

COMMANDS["/accommodation"] = _accommodation.telegram_start
FLOWS["accommodation"] = _accommodation.telegram_step


# ------------------------------------------------------------------ /human: chat with a tutor
async def _cmd_human(chat_id, arg, lang):
    from server.handoff import tickets

    if not tickets.find_open_external("telegram", chat_id):
        tickets.create_ticket(channel="telegram", lang=lang, topic=arg, external_address=chat_id)
    return [t(lang, "tg_human_started")]


async def _cmd_end(chat_id, arg, lang):
    from server.handoff import hub, tickets

    ticket_id = tickets.find_open_external("telegram", chat_id)
    if not ticket_id:
        return [t(lang, "tg_nothing_to_cancel")]
    await hub.close(ticket_id, notify_external=False)
    return [t(lang, "tg_human_ended")]


async def _relay_to_tutor(chat_id, text, lang):
    """While a ticket is open, the learner's messages go to the tutor, not to the assistant."""
    from server.handoff import hub, tickets

    ticket_id = tickets.find_open_external("telegram", chat_id)
    if not ticket_id:
        return None
    await hub.post_message(ticket_id, "learner", text)
    return []


def _register_handoff():
    from server.handoff import hub

    hub.external_senders["telegram"] = send_message


COMMANDS.update({"/human": _cmd_human, "/end": _cmd_end})
_interceptors.append(_relay_to_tutor)
_register_handoff()
