# Integration notes: channels, jobs, handoff, teacher view

For the teammate building content extraction, retrieval, AI providers and the web widget.
Branch: `feature/channels-handoff`. Nothing here edits `pages/`, `assets/`, retrieval code,
provider code or widget files.

## 1. What I need from you: the `ask()` contract

Every channel (Telegram, SMS, `/lite`) gets its answers from one function,
`server/channels/core_client.py`:

```python
ask(question: str, lang: str, channel: str, simple: bool = False) -> {
    "answer": str,                                   # plain text, no Markdown
    "citations": [{"page": str, "heading": str}],    # may be empty
    "matched": bool,                                 # False = "I don't know, ask a person"
}
```

- `lang` is `"en"` or `"am"`. The answer should be in that language.
- `channel` is `"telegram"`, `"sms"` or `"lite"`.
- `simple=True` is sent by SMS and `/lite`: please return a short, plain-language answer.
  SMS cuts the reply to under 300 characters whatever you return.
- When `matched` is false the channels ignore `answer` and show their own "I don't know" text.

Today `ask()` runs on a **stub with three canned answers**. To switch it to your code, set one
environment variable. No code change is needed.

| Variable | Meaning |
|---|---|
| `CORE_ASK_IMPORT=server.yourmodule:your_function` | Called as `your_function(question=..., lang=..., channel=..., simple=...)`. It must be a normal (not `async`) function returning the dict above. |
| `CORE_ASK_URL=http://localhost:8000/your/endpoint` | Receives `POST` JSON `{"question", "lang", "channel", "simple"}` and returns the dict above as JSON. |

If your function has a different signature, the only place to adapt is `_ask_import` /
`_ask_http` in `core_client.py`. If your code raises or times out (30 s), the learner gets
"I don't know, ask a person"; the stub is never used as a silent fallback.

## 2. "Talk to a person" button in the widget: one line

Load my script once, then call it from your button:

```html
<script src="http://localhost:8000/handoff/static/handoff.js"></script>
```

```js
talkButton.addEventListener("click", function () { AssistantHandoff.open({ lang: currentLang }); });
```

- It creates a ticket and opens the live chat page in a new tab. It works from `file://` pages,
  because the server address is taken from the script URL.
- Options are all optional: `lang` (`"en"` or `"am"`, default is the page's `<html lang>`),
  `topic` (for example the learner's last question; the tutor sees it in the ticket list).
- Call it directly inside the click handler, otherwise the browser may block the new tab.
- Without the script you can link to `/handoff/start?lang=am`, which needs no JavaScript.

When your assistant answers "I don't know", that is the moment to show this button.

## 3. Logging widget questions for the teacher view

In the endpoint that answers the widget, after you have the answer:

```python
from server.teacher.question_log import log_question

log_question(question, lang, "web", matched)   # matched = False when you answered "I don't know"
```

It stores the question text, language, channel and date only. Do not pass anything that
identifies the learner, and do not call it for accommodation requests or live-chat messages.
If you route the widget through `core_client.ask()`, you still have to call `log_question`
yourself: `ask()` does not log.

## 4. Indexing `data/jobs.json` as a second knowledge base

The file is a JSON list. Each job looks like this:

```json
{
  "id": "va-001", "title": "...", "company": "...", "location": "...", "remote": true,
  "skills": ["calendar management", "email"], "posted": "2026-11-12", "deadline": "2026-12-05",
  "link": "https://jobs.example.com/va-001",
  "description": {"en": "...", "am": "..."}
}
```

Suggested indexing:

- One document per job per language: text = title + company + location + skills +
  `description[lang]` + deadline.
- Keep `id`, `deadline` and `link` as metadata, and drop jobs whose `deadline` has passed.
- For citations, return `{"page": "jobs.json", "heading": "<title> - <company>"}`.
- `server.jobs.store.load_jobs()` already returns the list, newest first, without expired jobs.
  You may import it; please do not change it.

The jobs and companies are invented sample data.

## 5. Every line I added to shared files

The repo had no `server/` folder, entry point or requirements file, so I created minimal ones.
If you created your own, keep yours and append these lines at the end.

`server/main.py` (your file only needs `app = FastAPI(...)` above them):

```python
from server.channels.lite import router as lite_router; app.include_router(lite_router)
from server.channels.sms import router as sms_router; app.include_router(sms_router)
from server.channels.telegram_bot import router as telegram_router; app.include_router(telegram_router)
from server.jobs.router import router as jobs_router; app.include_router(jobs_router)
from server.channels.accommodation import router as accommodation_router; app.include_router(accommodation_router)
from server.handoff.router import router as handoff_router; app.include_router(handoff_router)
from server.teacher.router import router as teacher_router; app.include_router(teacher_router)
```

`requirements.txt` (the first two lines, `fastapi` and `uvicorn[standard]`, are probably
already in yours):

```
jinja2
python-multipart
httpx
python-dotenv
pytest
```

`server/__init__.py` is an empty file. I did not touch the root `.gitignore`; my ignores are in
`server/.gitignore`, `tests/.gitignore` and `data/.gitignore`.

## 6. Things that could surprise you

- **Startup hooks.** The Telegram bot and the alert scheduler start from the lifespan of my own
  routers (`/telegram` and `/jobs`). FastAPI merges these with your app's lifespan when the
  router is included, so you do not need to call anything. This needs a recent FastAPI
  (tested on 0.128).
- **URL prefixes I use:** `/lite`, `/sms`, `/jobs`, `/accommodation`, `/handoff`, `/teacher`,
  and `/telegram` (only `/telegram/status`). I did not mount `/static`; my scripts are served
  from `/handoff/static/` and `/sms/simulator.js`.
- **Templates and static files:** mine are `server/templates/{lite,accommodation,sms_simulator,
  teacher,handoff_*,_p34_*}.html` and `server/static/{handoff*,sms_simulator}.js`. Use other
  names for yours.
- **Databases:** `data/channels.db` and `data/accommodations.db` are mine and are created on
  first use. Please do not read `accommodations.db`: it is private by design.
- **Logging:** importing the bot sets the `httpx` logger to WARNING, because at INFO it prints
  request URLs and Telegram URLs contain the bot token.
- **Python:** the code runs on Python 3.9 and newer.
- **Environment variables:** see `.env.example`. A `.env` file in the repo root is loaded if
  `python-dotenv` is installed.

## 7. Nothing needed in your files

I did not need any change in the retrieval code, the provider code, the widget or the three
learner pages. The only wiring left for you is sections 1, 2 and 3 above.
