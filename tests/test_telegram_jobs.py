"""Telegram: buttons under answers, jobs that fit the learner's skills (/match), "Apply with Mimi",
and interview support started from a job. Telegram itself is replaced by a fake: nothing is sent."""
import asyncio

import pytest

from tests.test_channels_handoff import client  # noqa: F401  (fixture: temporary databases)


def run(coro):
    return asyncio.run(coro)


@pytest.fixture()
def bot(client, monkeypatch):  # noqa: F811
    from server.channels import telegram_bot

    sent, edits = [], []

    async def fake_send(chat_id, text, buttons=None):
        sent.append((str(text), buttons))
        return True

    async def fake_edit(chat_id, message_id, buttons):
        edits.append(buttons)

    monkeypatch.setattr(telegram_bot, "send_message", fake_send)
    monkeypatch.setattr(telegram_bot, "_edit_buttons", fake_edit)
    monkeypatch.setattr(telegram_bot, "get_consent", lambda channel, address: False)
    return telegram_bot, sent, edits


def tap(telegram_bot, chat, data, message_id=1):
    run(telegram_bot._handle_update({"callback_query": {"id": "q", "data": data,
                                                         "message": {"chat": {"id": chat}, "message_id": message_id}}}))


def flat(buttons):
    rows = buttons if buttons and isinstance(buttons[0], list) else [buttons or []]
    return [b for row in rows for b in row]


# ---------------------------------------------------------------- buttons under an answer
def test_answer_has_listen_lesson_and_person_buttons(bot, monkeypatch):
    telegram_bot, sent, _ = bot
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://mimi.example.org")
    monkeypatch.setenv("CORE_ASK_IMPORT", "server.core_bridge:ask")  # the real course search, no online AI
    run(telegram_bot._handle_update({"message": {"chat": {"id": 300}, "text": "What is the late policy?"}}))
    labels = {label: data for label, data in flat(sent[0][1])}
    assert labels["🔊 Listen"].startswith("listen:")
    lesson = labels["📖 Show in lesson"]
    assert lesson.startswith("https://mimi.example.org/pages/") and "?mimi_source=" in lesson
    assert labels["🙋 Ask a person"] == "human:"


def test_no_lesson_link_for_a_local_site(bot, monkeypatch):
    """Telegram refuses link buttons to a local address, so none is offered there."""
    telegram_bot, sent, _ = bot
    monkeypatch.setenv("PUBLIC_BASE_URL", "http://localhost:8000")
    run(telegram_bot._handle_update({"message": {"chat": {"id": 301}, "text": "What is the late policy?"}}))
    assert "📖 Show in lesson" not in [label for label, _ in flat(sent[0][1])]


def test_ask_a_person_button_opens_a_ticket(bot):
    telegram_bot, sent, _ = bot
    tap(telegram_bot, 302, "human:")
    assert "tutor" in sent[-1][0].lower()
    from server.handoff import tickets
    assert tickets.find_open_external("telegram", "302")


# ---------------------------------------------------------------- jobs that fit (/match)
def test_match_ticks_kinds_of_work_then_shows_fitting_jobs_and_turns_on_alerts(bot):
    telegram_bot, sent, edits = bot
    run(telegram_bot._handle_update({"message": {"chat": {"id": 310}, "text": "/match"}}))
    picker = flat(sent[-1][1])
    assert ("☐ 📅 Scheduling and calendars", "area:sched") in picker and picker[-1][1] == "area:done"

    tap(telegram_bot, 310, "area:sched")
    assert ("☑ 📅 Scheduling and calendars", "area:sched") in flat(edits[-1])  # ticked in place
    sent.clear()
    tap(telegram_bot, 310, "area:done")
    texts = [text for text, _ in sent]
    assert texts[0].startswith("Jobs that fit you")
    assert all("✅ Why it fits you:" in text for text in texts[1:]) and len(texts) > 1
    assert ("📝 Apply with Mimi", "apply:" + sent[1][1][0][1].split(":")[1]) in flat(sent[1][1])

    from server.channels.db import connect
    with connect() as c:
        keywords = [r["keyword"] for r in c.execute("SELECT keyword FROM subscriptions WHERE address='310'")]
    assert keywords == ["areas:sched"]


def test_match_needs_a_choice(bot):
    telegram_bot, sent, _ = bot
    run(telegram_bot._handle_update({"message": {"chat": {"id": 311}, "text": "/match"}}))
    tap(telegram_bot, 311, "area:done")
    assert sent[-1][0] == "Tap at least one kind of work first."


def test_alerts_for_kinds_of_work_send_only_fitting_jobs():
    from server.jobs.matching import best_jobs, fitting_skills
    from server.jobs.store import load_jobs, matches

    jobs = load_jobs()
    fits = [j for j in jobs if matches(j, "areas:books")]
    assert fits and all(fitting_skills(j, ["books"]) for j in fits)
    assert len(fits) < len(jobs)  # not every job
    ranked = best_jobs(jobs, ["sched", "admin"])
    assert len(ranked[0][1]) >= len(ranked[-1][1])  # most fitting skills first


def test_jobs_list_offers_apply_and_match(bot):
    telegram_bot, sent, _ = bot
    run(telegram_bot._handle_update({"message": {"chat": {"id": 312}, "text": "/jobs"}}))
    assert ("🎯 Jobs for my skills", "area:start") in flat(sent[0][1])
    assert all(any(data.startswith("apply:") for _, data in flat(buttons)) for _, buttons in sent[1:])


# ---------------------------------------------------------------- apply with Mimi, interview support
def test_apply_with_mimi_gives_steps_with_link_and_deadline(bot):
    from server.jobs.store import load_jobs

    telegram_bot, sent, _ = bot
    job = load_jobs()[0]
    tap(telegram_bot, 320, "apply:" + job["id"])
    text, buttons = sent[-1]
    assert text.startswith("📝 Applying for " + job["title"])
    assert job["link"] in text and "never to the employer" in text
    assert [label for label, _ in flat(buttons)] == ["🔊 Listen", "♿ Interview support"]


def test_interview_support_from_a_job_is_private_and_skips_the_job_question(bot, client):  # noqa: F811
    from server.jobs.store import load_jobs

    telegram_bot, sent, _ = bot
    job = load_jobs()[0]
    tap(telegram_bot, 321, "support:" + job["id"])
    assert sent[-1][0].startswith("Interview support for " + job["title"])  # step 2: the job is known
    run(telegram_bot._handle_update({"message": {"chat": {"id": 321}, "text": "Questions in writing, please"}}))
    run(telegram_bot._handle_update({"message": {"chat": {"id": 321}, "text": "@learner_handle"}}))
    assert sent[-1][0].startswith("Thank you. Your request was received.")


def test_amharic_apply_steps(bot, monkeypatch):
    from server.jobs.store import load_jobs

    telegram_bot, sent, _ = bot
    monkeypatch.setattr(telegram_bot, "get_lang", lambda channel, address: "am")
    tap(telegram_bot, 322, "apply:" + load_jobs()[0]["id"])
    assert "ማመልከት" in sent[-1][0] and "ለአሠሪው ፈጽሞ አይደርስም" in sent[-1][0]
