"""Voice messages on Telegram: what Mimi heard, the answer in text, and the answer in voice.

Telegram and the speech services are replaced by fakes, so nothing leaves the machine.
"""
import asyncio

import pytest

from tests.test_channels_handoff import client  # noqa: F401  (fixture: temporary databases)


@pytest.fixture()
def bot(client, monkeypatch):  # noqa: F811
    from server.channels import telegram_bot, voice

    sent = []

    async def fake_send(chat_id, text, buttons=None):
        sent.append(("text", text))
        if buttons:
            sent.append(("buttons", buttons))
        return True

    async def fake_voice(chat_id, audio, mime):
        sent.append(("voice", mime))
        return True

    async def fake_download(file_id):
        return b"OggS fake voice note"

    async def no_action(chat_id, action):
        return None

    monkeypatch.setattr(telegram_bot, "send_message", fake_send)
    monkeypatch.setattr(telegram_bot, "send_voice", fake_voice)
    monkeypatch.setattr(telegram_bot, "_download", fake_download)
    monkeypatch.setattr(telegram_bot, "_chat_action", no_action)
    monkeypatch.setattr(voice, "speak", lambda text, lang: (b"mp3", "audio/mpeg") if text else None)
    return telegram_bot, voice, sent


@pytest.fixture()
def bot_allowed(bot, monkeypatch):
    """The learner already agreed to the online services (consent is tested separately below)."""
    telegram_bot = bot[0]
    monkeypatch.setattr(telegram_bot, "get_consent", lambda channel, address: True)
    return bot


def run(coro):
    return asyncio.run(coro)


def test_voice_question_gets_heard_text_answer_and_voice(bot_allowed, monkeypatch):
    telegram_bot, voice, sent = bot_allowed
    monkeypatch.setattr(voice, "transcribe", lambda audio, mime, lang: "What is the late policy?")
    run(telegram_bot._handle_update({"message": {"chat": {"id": 42}, "voice": {"file_id": "f1", "duration": 4, "mime_type": "audio/ogg"}}}))
    kinds = [k for k, _ in sent]
    assert sent[0] == ("text", "🎤 I heard: What is the late policy?")
    assert kinds.count("text") >= 2  # what was heard, then the answer
    assert kinds[-1] == "voice"


def test_voice_with_no_words_asks_again(bot_allowed, monkeypatch):
    telegram_bot, voice, sent = bot_allowed
    monkeypatch.setattr(voice, "transcribe", lambda audio, mime, lang: "")
    run(telegram_bot._handle_update({"message": {"chat": {"id": 43}, "voice": {"file_id": "f2", "duration": 2}}}))
    assert sent == [("text", "I could not hear any words in that voice message. Please try again, or type your question.")]


def test_voice_without_speech_service_says_type_instead(bot_allowed, monkeypatch):
    telegram_bot, voice, sent = bot_allowed

    def unavailable(audio, mime, lang):
        raise voice.SpeechError("no key")

    monkeypatch.setattr(voice, "transcribe", unavailable)
    run(telegram_bot._handle_update({"message": {"chat": {"id": 44}, "voice": {"file_id": "f3", "duration": 2}}}))
    assert sent == [("text", "I cannot listen to voice messages right now. Please type your question.")]


def test_long_voice_note_is_refused(bot_allowed):
    telegram_bot, voice, sent = bot_allowed
    run(telegram_bot._handle_update({"message": {"chat": {"id": 45}, "voice": {"file_id": "f4", "duration": 300}}}))
    assert sent == [("text", "That voice message is too long. Please keep it under two minutes.")]


def text_message(chat, text):
    return {"message": {"chat": {"id": chat}, "text": text}}


def test_typed_answer_has_listen_button_that_speaks_it(bot_allowed):
    telegram_bot, voice, sent = bot_allowed
    run(telegram_bot._handle_update(text_message(50, "What is the late policy?")))
    buttons = [b for k, b in sent if k == "buttons"]
    assert buttons and buttons[0][0][0][0] == "🔊 Listen"  # first row, first button
    assert "voice" not in [k for k, _ in sent]  # typed question, voice answers off: text only
    sent.clear()
    run(telegram_bot._handle_update({"callback_query": {"id": "q1", "data": buttons[0][0][0][1], "message": {"chat": {"id": 50}}}}))
    assert sent == [("voice", "audio/mpeg")]


def test_commands_have_no_listen_button(bot_allowed):
    telegram_bot, voice, sent = bot_allowed
    run(telegram_bot._handle_update(text_message(51, "/help")))
    assert "buttons" not in [k for k, _ in sent]


def test_voice_on_speaks_every_answer_and_off_stops(bot_allowed):
    telegram_bot, voice, sent = bot_allowed
    run(telegram_bot._handle_update(text_message(52, "/voice on")))
    assert sent[0][1].startswith("Voice answers are on")
    sent.clear()
    run(telegram_bot._handle_update(text_message(52, "What is the late policy?")))
    assert [k for k, _ in sent][-1] == "voice"
    run(telegram_bot._handle_update(text_message(52, "/voice off")))
    sent.clear()
    run(telegram_bot._handle_update(text_message(52, "What is the late policy?")))
    assert "voice" not in [k for k, _ in sent]


def test_listen_when_no_voice_says_so(bot_allowed, monkeypatch):
    telegram_bot, voice, sent = bot_allowed
    monkeypatch.setattr(voice, "speak", lambda text, lang: None)
    key = telegram_bot._remember_answer("Some answer.", "en")
    run(telegram_bot._handle_update({"callback_query": {"id": "q2", "data": "listen:" + key, "message": {"chat": {"id": 53}}}}))
    assert sent == [("text", "I cannot speak right now. The answer is in the text above.")]


def test_english_question_in_amharic_chat_gets_english_text_and_voice(bot_allowed, monkeypatch):
    telegram_bot, voice, sent = bot_allowed
    spoken_langs = []
    monkeypatch.setattr(voice, "speak", lambda text, lang: spoken_langs.append(lang) or (b"mp3", "audio/mpeg"))
    monkeypatch.setattr(voice, "transcribe", lambda audio, mime, lang: "What is the late policy?")
    run(telegram_bot._handle_update(text_message(54, "/lang am")))
    sent.clear()
    run(telegram_bot._handle_update({"message": {"chat": {"id": 54}, "voice": {"file_id": "f5", "duration": 3}}}))
    assert sent[0] == ("text", "🎤 I heard: What is the late policy?")
    assert spoken_langs == ["en"]
    assert telegram_bot.get_lang("telegram", "54") == "en"
    # And back: an Amharic question switches the chat to Amharic again.
    run(telegram_bot._handle_update(text_message(54, "ዘግይቶ ማስገባት ይቻላል?")))
    assert telegram_bot.get_lang("telegram", "54") == "am"


def test_question_lang():
    from server.channels.telegram_bot import question_lang

    assert question_lang("ዘግይቶ ማስገባት ይቻላል?") == "am"
    assert question_lang("What is the late policy?") == "en"
    assert question_lang("4") is None
    assert question_lang("ok") is None


def test_spoken_part_drops_sources_and_markers():
    from server.channels import voice

    reply = "Late work gets one resubmission [1].\n\nSources: pages/x.html - Late policy"
    assert voice.spoken_part(reply, "en") == "Late work gets one resubmission."


# ---------------------------------------------------------------- consent
def test_first_question_is_answered_offline_then_consent_is_asked(bot, monkeypatch):
    telegram_bot, voice, sent = bot
    calls = []
    real_ask = telegram_bot.core_client.ask
    monkeypatch.setattr(telegram_bot.core_client, "ask", lambda *a: calls.append(a) or real_ask(*a))
    run(telegram_bot._handle_update(text_message(60, "What is the late policy?")))
    assert calls[0][-1] is False  # not asked yet: nothing may leave the server
    buttons = [b for k, b in sent if k == "buttons"]
    assert [d for _, d in buttons[-1]] == ["consent:yes", "consent:no"]
    assert "voice" not in [k for k, _ in sent]


def test_consent_yes_allows_cloud_and_no_keeps_it_off(bot, monkeypatch):
    telegram_bot, voice, sent = bot
    calls = []
    real_ask = telegram_bot.core_client.ask
    monkeypatch.setattr(telegram_bot.core_client, "ask", lambda *a: calls.append(a) or real_ask(*a))
    run(telegram_bot._handle_update({"callback_query": {"id": "c1", "data": "consent:yes", "message": {"chat": {"id": 61}}}}))
    assert sent[-1][1].startswith("Thank you. AI answers and voice are on")
    run(telegram_bot._handle_update(text_message(61, "What is the late policy?")))
    assert calls[-1][-1] is True
    assert "consent:yes" not in str(sent[2:])  # not asked again
    run(telegram_bot._handle_update({"callback_query": {"id": "c2", "data": "consent:no", "message": {"chat": {"id": 61}}}}))
    run(telegram_bot._handle_update(text_message(61, "What is the late policy?")))
    assert calls[-1][-1] is False


def test_voice_note_waits_for_consent_and_is_answered_after_yes(bot, monkeypatch):
    telegram_bot, voice, sent = bot
    heard = []
    monkeypatch.setattr(voice, "transcribe", lambda audio, mime, lang: heard.append(1) or "What is the late policy?")
    run(telegram_bot._handle_update({"message": {"chat": {"id": 62}, "voice": {"file_id": "v", "duration": 3}}}))
    assert heard == []  # not sent to any speech service before the learner agrees
    assert [d for _, d in [b for k, b in sent if k == "buttons"][-1]] == ["consent:yes", "consent:no"]
    sent.clear()
    run(telegram_bot._handle_update({"callback_query": {"id": "c3", "data": "consent:yes", "message": {"chat": {"id": 62}}}}))
    assert heard == [1]
    assert ("text", "🎤 I heard: What is the late policy?") in sent and sent[-1] == ("voice", "audio/mpeg")


def test_voice_note_after_no_is_not_sent_anywhere(bot, monkeypatch):
    telegram_bot, voice, sent = bot
    monkeypatch.setattr(voice, "transcribe", lambda *a: pytest.fail("audio left the server"))
    run(telegram_bot._handle_update({"callback_query": {"id": "c4", "data": "consent:no", "message": {"chat": {"id": 63}}}}))
    sent.clear()
    run(telegram_bot._handle_update({"message": {"chat": {"id": 63}, "voice": {"file_id": "v", "duration": 3}}}))
    assert sent[0][1].startswith("Voice needs the online services")


def test_privacy_command_shows_choice_with_buttons(bot):
    telegram_bot, voice, sent = bot
    run(telegram_bot._handle_update(text_message(64, "/privacy")))
    assert [d for _, d in [b for k, b in sent if k == "buttons"][-1]] == ["consent:yes", "consent:no"]


# ---------------------------------------------------------------- webhook mode (hosted servers)
def test_webhook_accepts_only_telegram(client, monkeypatch):  # noqa: F811
    import time as _time

    from server.channels import telegram_bot
    from server.channels.config import telegram_webhook_secret

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123:test-token")
    handled = []

    async def fake_handle(update):
        handled.append(update)

    monkeypatch.setattr(telegram_bot, "_handle_update", fake_handle)
    update = {"update_id": 1, "message": {"chat": {"id": 70}, "text": "/help"}}
    assert client.post("/telegram/webhook", json=update).status_code == 403
    assert client.post("/telegram/webhook", json=update, headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"}).status_code == 403
    ok = client.post("/telegram/webhook", json=update, headers={"X-Telegram-Bot-Api-Secret-Token": telegram_webhook_secret()})
    assert ok.status_code == 200
    for _ in range(20):
        if handled:
            break
        _time.sleep(0.05)
    assert handled == [update]


def test_mode_defaults_to_polling(monkeypatch):
    from server.channels.config import telegram_mode

    monkeypatch.delenv("TELEGRAM_MODE", raising=False)
    assert telegram_mode() == "polling"
    monkeypatch.setenv("TELEGRAM_MODE", "webhook")
    assert telegram_mode() == "webhook"


# ---------------------------------------------------------------- the Menu button
def test_menu_question_is_answered_from_the_course_with_listen(bot_allowed, monkeypatch):
    telegram_bot, voice, sent = bot_allowed
    # The real tutor (as on the servers), kept on this machine: no online AI.
    monkeypatch.setenv("CORE_ASK_IMPORT", "server.core_bridge:ask")
    monkeypatch.setattr(telegram_bot, "get_consent", lambda channel, address: False)
    run(telegram_bot._handle_update(text_message(80, "/deadline")))
    texts = [x for k, x in sent if k == "text"]
    assert texts[0].startswith("❓ When is the assignment deadline?")
    assert "pages/" in texts[0]  # with its source
    assert [b for k, b in sent if k == "buttons"][0][0][0][0] == "🔊 Listen"


def test_menu_question_follows_the_chat_language(bot_allowed):
    telegram_bot, voice, sent = bot_allowed
    run(telegram_bot._handle_update(text_message(81, "/lang am")))
    sent.clear()
    run(telegram_bot._handle_update(text_message(81, "/late")))
    assert sent[0][1].startswith("❓ የዘገየ ማስረከቢያ ደንብ ምንድን ነው?")


def test_every_menu_entry_is_a_working_command():
    from server.channels.telegram_bot import COMMANDS, MENU, QUICK_QUESTIONS

    for command, english, amharic in MENU:
        assert "/" + command in COMMANDS or "/" + command in QUICK_QUESTIONS, command
        assert 0 < len(english) <= 256 and 0 < len(amharic) <= 256
        assert command.islower() and len(command) <= 32


def test_menu_is_sent_to_telegram_in_both_languages():
    import asyncio as _asyncio

    from server.channels import telegram_bot

    calls = []

    class FakeClient:
        async def post(self, url, json=None):
            calls.append((url.rsplit("/", 1)[-1], json))

    _asyncio.run(telegram_bot._set_menu(FakeClient(), "123:abc"))
    assert [c[0] for c in calls] == ["setMyCommands", "setMyCommands"]
    assert "language_code" not in calls[0][1] and calls[1][1]["language_code"] == "am"
    assert calls[0][1]["commands"][0] == {"command": "deadline", "description": "📅 When is my assignment due?"}
