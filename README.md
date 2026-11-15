# Mimi: multilingual course tutor and live help (`<db-assistant>`)

**Track 3, Multilingual assistant and live help.** Digital Bridge Accessibility Hackathon 2026.

- **Team:** *to fill in: names and roles*
- **Co-designer:** *to fill in: first name, with their permission*

## What it does

Mimi is a tutor that sits on any learning page, introduces herself in Amharic, and helps in Amharic or
English, by voice or by text. She answers only from the course (and the job listings), shows the exact
section each answer comes from, and says plainly when something is not in the course. With one button
the learner reaches a person, can share their screen if they choose, and the same tutor answers on
Telegram, by SMS and on a no-JavaScript page.

## The main task we tested

*To fill in with the co-designer.* Our working sentence: "A blind learner on a low-cost Android phone
asks in Amharic, by voice, what the late policy of their course is, hears the answer with its source,
and reaches a tutor when the answer is not enough, with nobody helping."

## Run it

```
cp .env.example .env          # optional: AI keys, Telegram token. Everything works without them.
docker compose up --build
```

Then open:

| Address | What |
|---|---|
| http://localhost:8001/pages/concept-with-navigation.html | A Savanna lesson page with Mimi |
| http://localhost:8001/demo/blank.html | Mimi on a plain page with no Savanna or Bootstrap styles |
| http://localhost:8001/pages/jobs.html | Job board demo (schema.org JobPosting) |
| http://localhost:8001/docs | Tutor API, interactive (Swagger UI) |
| http://localhost:8000/docs | Channels API, interactive |
| http://localhost:8000/handoff/console | Tutor console: learners waiting for a person (password: `TUTOR_PASSWORD` in `.env`, or printed in the log) |
| http://localhost:8000/teacher | Teacher view: most asked questions, no names |
| http://localhost:8000/lite | Low-bandwidth page, no JavaScript |
| http://localhost:8000/sms/simulator | Pretend phone for the SMS route |

Without Docker: `python -m venv .venv`, install `requirements.txt`, then `python run.py`, which starts
both servers. Browsers block sound until the first tap or key press on a page; Mimi then shows a
"Start Mimi" button. `open-demo.bat` (Windows) opens Edge for a demo with sound allowed at once.

Use Microsoft Edge for spoken Amharic: it has a natural Amharic voice (Mekdes) built in. Chrome has
none, so in Chrome Amharic speech needs a server voice (Gemini, Azure or Google key) or is shown as text.

## Install, Level 1: one script tag

```html
<script src="https://your-server/module/db-assistant.js" defer></script>
<db-assistant lang="am" api="https://your-server" content="/content.json"></db-assistant>
```

| Attribute | Meaning | Default |
|---|---|---|
| `lang` | Language Mimi starts in (`am` or `en`); she then asks whether to switch | `am` |
| `api` | The tutor server | the server the page came from |
| `content` | A JSON file of the host's own lessons, `[{"title", "url", "text"}]`, indexed so Mimi answers from them too | none |
| `course`, `lesson` | The course and lesson on this page, so "explain this lesson" knows what "this" is | none |
| `lesson-selector` | A CSS selector whose text is the current lesson (for pages that change it) | none |
| `auto-welcome` | `false`: Mimi does not speak until the learner opens her | `true` |
| `tts`, `stt` | `browser` or `server`: force where speech is made and recognised | `auto` |

| Event (on `document`) | `detail` | When |
|---|---|---|
| `db-assistant:question` | `{ text, language }` | The learner asks something |
| `db-assistant:escalated` | `{ ticketId }` | The learner asked for a person |

Mimi lives in a shadow root (the host's CSS cannot change her, hers cannot change the host), sets no
global variables and changes no host element. She uses the host's font (`--bs-body-font-family`)
when there is one. The module is 38 KB compressed.

## Install, Level 2: the API

The full specification is [openapi.yaml](openapi.yaml); try every call at `/docs`.

```bash
# Ask (answers only from the course, with sources)
curl -X POST http://localhost:8001/api/v1/ask -H "Content-Type: application/json" \
  -d '{"question":"Can I resubmit an assignment?","language":"en"}'

# Send the host's lessons to be indexed
curl -X POST http://localhost:8001/api/v1/content -H "Content-Type: application/json" \
  --data-binary @demo/data/content.json

# Ask for a person, with the conversation so far
curl -X POST http://localhost:8001/api/v1/escalations -H "Content-Type: application/json" \
  -d '{"language":"en","conversation":[{"role":"user","text":"When is the deadline?"}]}'

# The text route: an SMS gateway posts here and sends back the plain-text reply (at most 160 characters)
curl -X POST http://localhost:8000/sms/inbound -H "Content-Type: application/json" \
  -d '{"from":"0911000000","text":"What is the late policy?"}'

# Which AI and voices are available
curl http://localhost:8001/api/health
```

**Webhook.** Set `WEBHOOK_URL` in `.env`: when a learner asks for a person, the server posts
`{"event": "ticket.opened", "at": "...", "data": {"ticketId", "channel", "lang"}}` to it. No name,
phone number or message text is sent.

**AI providers.** One switch in `.env`, `ABLEWAY_PROVIDERS`, in order of preference: `gemini` (cloud),
`cloud` (Claude), `local` (an open model through Ollama, no internet) and `offline` (keyword search and a
hand-written FAQ, no AI). Missing keys are skipped, and offline is always last, so Mimi is useful with
no AI budget at all.

## Install, Level 3: open standards

- **schema.org JobPosting:** every job on `pages/jobs.html` is described in JSON-LD, so job boards and
  search engines can read it.
- **LTI 1.3:** not done. Mimi would connect as an LTI tool whose launch page loads the same script tag;
  the LMS would pass the course and lesson as launch claims, which map to the `course` and `lesson`
  attributes. No learner identity is needed for answers.

## Languages and how to add one

Every sentence Mimi says or shows is in [module/i18n/en.json](module/i18n/en.json) and
[module/i18n/am.json](module/i18n/am.json); none is written in the code. To add a language (for
example Tigrinya, Afaan Oromo, Somali or Arabic):

1. Copy `en.json` to `module/i18n/<code>.json` and translate it. Set `meta.speech` (for example
   `ti-ET`) and `meta.dir` (`rtl` for Arabic: the layout uses logical CSS properties, so it mirrors).
2. Add the code to `LANGUAGE_CODES` in `module/db-assistant.js`.
3. On the server, add the language name in `LANGUAGES` in `server/tutor.py`, so AI answers come in it.

Right-to-left text already works in any language: every message has `dir="auto"`. Job deadlines are
shown in the Ethiopian calendar in Amharic (`server/channels/ethiopian.py`).

## Offline and slow connection

- Measured on Chrome's "Slow 3G" setting (2 s latency, about 400 kbit/s), cache off: Mimi appears after
  **7.2 s** on the plain page. On the Savanna lesson page it is about 21 s, because the browser first
  loads Savanna's own 1.5 MB of stylesheets.
- The module is **38 KB** compressed (script 26 KB, stylesheet 6 KB, language files 6 KB).
- With no internet on the server, answers still come from the offline search and FAQ. Mimi's greeting
  and menu are recorded once and replay without any voice service.
- `/lite` is a plain HTML form for the slowest phones, and SMS works with no data at all.

## Data and privacy

| What | Where | Kept |
|---|---|---|
| The conversation | The learner's browser tab only (`sessionStorage`); the server keeps nothing between questions | Until the tab closes |
| Language and display preferences | The learner's browser (`localStorage`) | Until the learner clears it |
| Questions for the teacher view | `channels.db`: text, language, channel and date. No name, phone number, IP or time | Delete the database file |
| Help tickets and live chat | `channels.db` | Closed tickets can be deleted by the platform |
| Interview accommodation requests | A separate database, `accommodations.db`, never shown to employers | Delete the file |
| SMS and Telegram alert subscriptions | `channels.db`: the number or chat id and the keywords | `UNSUB` deletes it |

- The microphone and screen sharing are off until the learner starts them, and clearly shown while on.
- What leaves the server: the question and the matching course text go to the AI provider the host
  configured (Gemini's free tier may use them to improve Google's products; use a paid tier or the
  local or offline provider to avoid that). In Edge, spoken text goes to Microsoft's online voices.
- Keys stay on the server in `.env`, which is not in git; the browser never sees them.
- Only test data is included: the jobs and learners are invented.

## Cost to run per month

For 3,000 learners, assuming 5 questions each per week (about 65,000 questions a month):

| Item | Cost |
|---|---|
| Server: one small virtual machine (2 GB) running both containers | about $6–12 |
| AI answers: about half come from the answer cache or the offline FAQ; the other ~32,000 go to a "flash-lite" class model at about 2,500 tokens in and 250 out | about $25–45 (check current prices) |
| Voices: browser voices (Edge) and recorded phrases | $0 |
| Optional: Azure Speech free tier (0.5 M characters of speech, 5 hours of recognition) | $0 within the free tier |
| **Total** | **about $30–60**, or the server cost only with the offline provider |

No feature depends on a paid service: every AI and voice provider can be swapped or removed.

## Finished and not finished

**Finished and tested:** the tutor in Amharic and English with sources and refusals; voice in and out,
with captions; one-click help with the conversation passed on; screen sharing with a visible stop
control; Telegram (typed questions and voice messages: Mimi shows what she heard, answers in text with a "🔊 Listen" button, or always in voice too with `/voice on`, and
replies with a voice message), SMS (plain text, 160 characters) and `/lite`; job answers, job alerts and interview
accommodation requests; simple mode; teacher view; the pluggable AI layer with an offline mode; the
API with `/docs`, OpenAPI and a webhook; schema.org JobPosting; Docker Compose; 74 automated tests
(`pytest server/tests tests`) and an axe-core check (`tests/a11y`), currently clean.

**Not finished or not yet verified:**

- Not yet tested by our co-designer, or with NVDA and TalkBack (see [CONFORMANCE.md](CONFORMANCE.md)).
- Amharic speech recognition in Chrome is good but not perfect; names and places are often wrong. Mimi
  always shows what she heard, so the learner can type instead.
- Only Amharic and English language files; the mechanism for more is in place.
- Telegram needs a bot token in `.env`; SMS has no real gateway (the route and a simulator are ready).
- The Amharic text should be read once more by a native speaker on the team.

## Libraries and their licences

| Library | Used for | Licence |
|---|---|---|
| FastAPI, Uvicorn | Channels server | MIT, BSD-3-Clause |
| Jinja2, python-multipart, httpx, python-dotenv | Channels server | BSD-3-Clause, Apache-2.0, BSD-3-Clause, BSD-3-Clause |
| pytest | Tests | MIT |
| anthropic (optional) | Claude provider | MIT |
| Swagger UI 5.17.14 (from jsDelivr, on `/docs` only) | API documentation page | Apache-2.0 |
| axe-core 4.10.2 (tests only) | Accessibility check | MPL-2.0 |

The tutor server and the module itself use only the Python standard library and plain JavaScript.
The Savanna starter pages and assets belong to ALX (see [docs/SAVANNA_STARTER.md](docs/SAVANNA_STARTER.md)).
Our code: see [LICENSE](LICENSE).
