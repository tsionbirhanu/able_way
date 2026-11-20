"""Afaan Oromo: a complete language file, and answers in Afaan Oromo on the web, Telegram and SMS."""
import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
I18N = ROOT / "module" / "i18n"
sys.path.insert(0, str(ROOT / "server"))


def shape(value):
    """Every key, list length and {placeholder}, so a translation cannot drop or rename one."""
    if isinstance(value, dict):
        return {k: shape(v) for k, v in value.items()}
    if isinstance(value, list):
        return [shape(v) for v in value]
    return sorted(set(re.findall(r"\{\w+\}", value)))


def test_afaan_oromo_file_is_complete():
    english = json.loads((I18N / "en.json").read_text(encoding="utf-8"))
    oromo = json.loads((I18N / "om.json").read_text(encoding="utf-8"))
    english.pop("languageNames"), oromo.pop("languageNames")
    english.pop("meta"), oromo.pop("meta")
    assert shape(oromo) == shape(english)


def test_only_amharic_english_and_afaan_oromo_are_offered():
    assert sorted(p.stem for p in I18N.glob("*.json")) == ["am", "en", "om"]
    script = (ROOT / "module" / "db-assistant.js").read_text(encoding="utf-8")
    assert "code: 'om'" in script and "code: 'ti'" not in script and "code: 'ar'" not in script
    from tutor import LANGUAGES

    assert set(LANGUAGES) == {"en", "am", "om"}


@pytest.fixture()
def tutor(monkeypatch):
    monkeypatch.setenv("ABLEWAY_PROVIDERS", "offline")
    from tutor import Tutor

    return Tutor()


def test_not_in_the_course_is_said_in_afaan_oromo(tutor):
    from tutor import TEXT

    answer = tutor.ask("Who won the World Cup in football?", "om", cloud=False)
    assert answer["answer"] == TEXT["om"]["not_found"]


def test_offline_answer_says_the_quote_is_in_english(tutor):
    from tutor import TEXT

    answer = tutor.ask("What is the late submission policy?", "om", cloud=False)
    assert answer["grounded"] and answer["answer"].startswith(TEXT["om"]["offline_quote"])


def test_asking_to_switch_to_afaan_oromo(tutor):
    answer = tutor.ask("Please speak Oromo", "en", detect_switch=True, cloud=False)
    assert answer.get("switch_lang") == "om"


# ---------------------------------------------------------------- understood with no AI (word list)
@pytest.mark.parametrize("question, section", [
    ("Guyyaan galchuu hojii manaa yoom?", "Resubmission"),
    ("Qormaatni madaallii maali?", "Evaluation Quizzes"),
    ("Egereen hojii VA abdachiisaadhaa?", "Future of VA"),
])
def test_afaan_oromo_question_finds_the_right_section_offline(tutor, question, section):
    answer = tutor.ask(question, "om", cloud=False)
    assert answer["grounded"] and section in answer["citations"][0]["title"]


def test_off_topic_in_afaan_oromo_is_still_refused(tutor):
    assert tutor.ask("Eenyutu Waancaa Addunyaa mo'e?", "om", cloud=False)["grounded"] is False


def test_longer_phrase_wins_over_the_word_inside_it():
    from retrieval import expand_words, load_glossary

    words = expand_words("Guyyaan galchuu hojii manaa yoom?", load_glossary("om"), "om")
    assert "assignment" in words and "work" not in words


# ---------------------------------------------------------------- the greeting: 1, 2, 3
def test_greeting_numbers():
    script = (ROOT / "module" / "db-assistant.js").read_text(encoding="utf-8")
    assert "LANGUAGE_NUMBERS = { 1: 'am', 2: 'en', ...Object.fromEntries(MORE_LANGUAGES.map(({ code }, i) => [i + 3, code]))" in script
    assert "3" in json.loads((I18N / "om.json").read_text(encoding="utf-8"))["pressHint"]


def test_greeting_choices_are_one_sentence_in_the_greeting_language():
    """Mimi says every language's number herself, in one voice: no second speaker after the greeting."""
    am = json.loads((I18N / "am.json").read_text(encoding="utf-8"))["chooseOthers"]
    en = json.loads((I18N / "en.json").read_text(encoding="utf-8"))["chooseOthers"]
    assert "2" in am and "3" in am and "1" in en and "3" in en
    assert "4" not in am + en and "5" not in am + en
    script = (ROOT / "module" / "db-assistant.js").read_text(encoding="utf-8")
    assert "return say(greetingChoices(lang), lang," in script  # the same language, so the same voice


# ---------------------------------------------------------------- Telegram and SMS
from tests.test_channels_handoff import client  # noqa: E402,F401  (fixture: temporary databases)


def test_telegram_lang_om_then_menu_question_in_afaan_oromo(client, monkeypatch):  # noqa: F811
    import asyncio

    from server.channels import telegram_bot
    from server.channels.strings import t

    monkeypatch.setenv("CORE_ASK_IMPORT", "server.core_bridge:ask")
    monkeypatch.setattr(telegram_bot, "get_consent", lambda channel, address: False)

    async def talk():
        set_reply = await telegram_bot.handle_message(9101, "/lang om")
        answer = await telegram_bot.handle_message(9101, "/deadline")
        await telegram_bot.handle_message(9101, "Qormaatni madaallii maali?")  # Latin letters: stays om
        return set_reply, answer

    set_reply, answer = asyncio.run(talk())
    assert set_reply == [t("om", "tg_lang_set")]
    assert answer[0].startswith("❓ Guyyaan galchuu hojii manaa yoom?")
    assert "Resubmission" in answer[0]  # answered from the course, with its source
    assert telegram_bot.get_lang("telegram", "9101") == "om"


def test_telegram_lang_unknown_shows_the_choices(client):  # noqa: F811
    import asyncio

    from server.channels import telegram_bot

    reply = asyncio.run(telegram_bot.handle_message(9103, "/lang klingon"))
    assert "/lang am" in reply[0] and "/lang en" in reply[0] and "/lang om" in reply[0]
    assert "/lang ti" not in reply[0] and "/lang ar" not in reply[0]


def test_sms_lang_om(client):  # noqa: F811
    from server.channels.strings import t

    reply = client.post("/sms/inbound", headers={"Accept": "application/json"},
                        json={"from": "+251911000077", "text": "LANG OM"}).json()["reply"]
    assert reply == t("om", "sms_lang_set")


def test_telegram_voice_for_afaan_oromo_never_crashes(monkeypatch):
    from server.channels import voice

    calls = []
    monkeypatch.setattr(voice, "_get", lambda: type("S", (), {"synthesize": lambda self, text, lang: calls.append(lang) or (b"x", "audio/mpeg", "t")})())
    assert voice.speak("Akkam", "om") is None and calls == []  # no server voice: the text answer stays
    assert voice.speak("ሰላም", "am") == (b"x", "audio/mpeg")
