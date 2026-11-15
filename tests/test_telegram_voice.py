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


def run(coro):
    return asyncio.run(coro)


def test_voice_question_gets_heard_text_answer_and_voice(bot, monkeypatch):
    telegram_bot, voice, sent = bot
    monkeypatch.setattr(voice, "transcribe", lambda audio, mime, lang: "What is the late policy?")
    run(telegram_bot._handle_update({"message": {"chat": {"id": 42}, "voice": {"file_id": "f1", "duration": 4, "mime_type": "audio/ogg"}}}))
    kinds = [k for k, _ in sent]
    assert sent[0] == ("text", "🎤 I heard: What is the late policy?")
    assert kinds.count("text") >= 2  # what was heard, then the answer
    assert kinds[-1] == "voice"


def test_voice_with_no_words_asks_again(bot, monkeypatch):
    telegram_bot, voice, sent = bot
    monkeypatch.setattr(voice, "transcribe", lambda audio, mime, lang: "")
    run(telegram_bot._handle_update({"message": {"chat": {"id": 43}, "voice": {"file_id": "f2", "duration": 2}}}))
    assert sent == [("text", "I could not hear any words in that voice message. Please try again, or type your question.")]


def test_voice_without_speech_service_says_type_instead(bot, monkeypatch):
    telegram_bot, voice, sent = bot

    def unavailable(audio, mime, lang):
        raise voice.SpeechError("no key")

    monkeypatch.setattr(voice, "transcribe", unavailable)
    run(telegram_bot._handle_update({"message": {"chat": {"id": 44}, "voice": {"file_id": "f3", "duration": 2}}}))
    assert sent == [("text", "I cannot listen to voice messages right now. Please type your question.")]


def test_long_voice_note_is_refused(bot):
    telegram_bot, voice, sent = bot
    run(telegram_bot._handle_update({"message": {"chat": {"id": 45}, "voice": {"file_id": "f4", "duration": 300}}}))
    assert sent == [("text", "That voice message is too long. Please keep it under two minutes.")]


def text_message(chat, text):
    return {"message": {"chat": {"id": chat}, "text": text}}


def test_typed_answer_has_listen_button_that_speaks_it(bot):
    telegram_bot, voice, sent = bot
    run(telegram_bot._handle_update(text_message(50, "What is the late policy?")))
    buttons = [b for k, b in sent if k == "buttons"]
    assert buttons and buttons[0][0][0] == "🔊 Listen"
    assert "voice" not in [k for k, _ in sent]  # typed question, voice answers off: text only
    sent.clear()
    run(telegram_bot._handle_update({"callback_query": {"id": "q1", "data": buttons[0][0][1], "message": {"chat": {"id": 50}}}}))
    assert sent == [("voice", "audio/mpeg")]


def test_commands_have_no_listen_button(bot):
    telegram_bot, voice, sent = bot
    run(telegram_bot._handle_update(text_message(51, "/help")))
    assert "buttons" not in [k for k, _ in sent]


def test_voice_on_speaks_every_answer_and_off_stops(bot):
    telegram_bot, voice, sent = bot
    run(telegram_bot._handle_update(text_message(52, "/voice on")))
    assert sent[0][1].startswith("Voice answers are on")
    sent.clear()
    run(telegram_bot._handle_update(text_message(52, "What is the late policy?")))
    assert [k for k, _ in sent][-1] == "voice"
    run(telegram_bot._handle_update(text_message(52, "/voice off")))
    sent.clear()
    run(telegram_bot._handle_update(text_message(52, "What is the late policy?")))
    assert "voice" not in [k for k, _ in sent]


def test_listen_when_no_voice_says_so(bot, monkeypatch):
    telegram_bot, voice, sent = bot
    monkeypatch.setattr(voice, "speak", lambda text, lang: None)
    key = telegram_bot._remember_answer("Some answer.", "en")
    run(telegram_bot._handle_update({"callback_query": {"id": "q2", "data": "listen:" + key, "message": {"chat": {"id": 53}}}}))
    assert sent == [("text", "I cannot speak right now. The answer is in the text above.")]


def test_english_question_in_amharic_chat_gets_english_text_and_voice(bot, monkeypatch):
    telegram_bot, voice, sent = bot
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
