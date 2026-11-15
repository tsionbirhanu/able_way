# Mimi: multilingual course tutor and live help (`<db-assistant>`)

**Track 3, Multilingual assistant and live help.** Digital Bridge Accessibility Hackathon 2026.

- **Team:** *to fill in: names and roles*
- **Co-designer:** *to fill in: first name, with their permission*

## What it does

Mimi is a tutor that any learning platform adds with one script tag. She helps in Amharic or English,
by voice or by text, answers only from the course (and the job listings), shows the exact section each
answer comes from, and says plainly when something is not in the course. One button connects the
learner to a person (with screen sharing the learner controls), and the same tutor answers on
Telegram, by SMS and on a no-JavaScript page.

## The main task we tested

*To fill in with the co-designer.* Our working sentence: "A blind learner on a low-cost Android phone
asks in Amharic, by voice, what the late policy of their course is, hears the answer with its source,
and reaches a tutor when the answer is not enough, with nobody helping."

## Run it

### Quick start with Docker (one command)

You need [Git](https://git-scm.com/downloads) and [Docker Desktop](https://www.docker.com/products/docker-desktop/) (running).

```bash
git clone https://github.com/tsionbirhanu/able_way.git
cd able_way
cp .env.example .env          # Windows PowerShell: copy .env.example .env
docker compose up --build
```

No key is needed: with an empty `.env`, Mimi answers from the course text (offline mode). Then open:

| Address | What |
|---|---|
| http://localhost:8001/pages/concept-with-navigation.html | **Start here:** a Savanna lesson page with Mimi |
| http://localhost:8001/demo/blank.html | Mimi on a plain page with no Savanna or Bootstrap styles (the "works anywhere" proof) |
| http://localhost:8001/pages/jobs.html | Job board demo (schema.org JobPosting) |
| http://localhost:8001/docs | Tutor API, interactive (Swagger UI) |
| http://localhost:8000/docs | Channels API, interactive |
| http://localhost:8000/handoff/console | Tutor console: learners waiting for a person, and accommodation requests |
| http://localhost:8000/teacher | Teacher view: most asked questions, no names |
| http://localhost:8000/lite | Low-bandwidth page, no JavaScript |
| http://localhost:8000/sms/simulator | Pretend phone for the SMS route |

The console password is `TUTOR_PASSWORD` in `.env`; if you leave it empty, a random one is printed in
the log when the server starts. Stop everything with `Ctrl+C`, then `docker compose down`.

### Without Docker

You need **Python 3.11 or newer** ([python.org](https://www.python.org/downloads/); on Windows tick
"Add Python to PATH").

```bash
git clone https://github.com/tsionbirhanu/able_way.git
cd able_way
python -m venv .venv
# Windows:      .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # Windows PowerShell: copy .env.example .env
python run.py
```

`run.py` starts both servers in one terminal: the **tutor** on port 8001 (the pages, Mimi, the AI
answers and voice) and the **channels** server on port 8000 (talk to a person, Telegram, SMS, `/lite`,
jobs, teacher view). The addresses are the same as above.

### First visit: what to expect

1. Mimi asks once, in Amharic and English, whether she may use online AI and voice. Choose
   **"Allow and start"** to hear her, or **"No, text only"** to keep everything on this computer.
2. She introduces herself in Amharic and asks if you want English: say or press **2** for English.
3. Ask a question by voice (the big "Press to talk" button) or by typing. Try *"What is the late
   submission policy?"*, then *"Who won the World Cup?"* (she says it is not in the course and offers
   a person).

Use **Microsoft Edge** for spoken Amharic: it has a natural Amharic voice (Mekdes) built in. **Chrome**
recognises spoken Amharic best. On Windows, `open-demo.bat` opens Edge with sound allowed at once.

### Turn on the extras (all optional, all free to start)

Edit `.env`, then restart (`Ctrl+C`, then `python run.py` or `docker compose up` again). The `.env` can
live in the project folder or one folder up, outside the project (then it can never reach git);
both are read, and the project's own `.env` wins where both set the same thing.

| Feature | What to set in `.env` | Where to get it |
|---|---|---|
| AI answers (better wording, Amharic explanations) | `GEMINI_API_KEY=...` | Free key: https://aistudio.google.com/apikey . One key is enough. |
| Natural Amharic and English voice, and listening, on every device | `AZURE_SPEECH_KEY=...` and `AZURE_SPEECH_REGION=...` | Azure portal: create a "Speech" resource on the free F0 tier |
| AI with no internet | `ABLEWAY_PROVIDERS=local,offline` | Install [Ollama](https://ollama.com), then `ollama pull gemma3:4b` |
| Telegram bot | `TELEGRAM_BOT_TOKEN=...` | In Telegram, message @BotFather, send `/newbot` |
| Real SMS | `SMS_PROVIDER=...` | See "Real SMS, free for development" below |

### Test on a real phone (needed for the microphone)

Phones only allow the microphone on HTTPS. With the servers running, open a second terminal:

```bash
cloudflared tunnel --url http://localhost:8001
```

Open the `https://….trycloudflare.com` address it prints, adding `/pages/concept-with-navigation.html`.
For "Talk to a person" on the phone, run a second tunnel for port 8000 and put its address in `.env` as
`PUBLIC_BASE_URL`. Install cloudflared with `winget install --id Cloudflare.cloudflared` (Windows) or
`brew install cloudflared` (macOS).

### Real SMS, free for development

There is no SMS gateway at the hackathon, so `POST /sms/inbound` returns the reply as plain text (at
most 160 characters) and `/sms/simulator` plays the phone. To send and receive real SMS:

- **SMS Gateway for Android** (free, open source): install the app from https://sms-gate.app on an
  Android phone with a SIM card. Each SMS costs only what the SIM plan charges. In `.env`:
  `SMS_PROVIDER=android`, `SMS_GATEWAY_URL` (the address the app shows, for example
  `http://192.168.1.20:8080`, or `https://api.sms-gate.app/3rdparty/v1` for its cloud mode),
  `SMS_GATEWAY_USER`, `SMS_GATEWAY_PASSWORD`. In the app, add a webhook for `sms:received` pointing
  to `https://<your tunnel>/sms/webhook/android`.
- **Africa's Talking sandbox** (free, with a phone simulator in their dashboard): `SMS_PROVIDER=africastalking`,
  `AT_USERNAME=sandbox`, `AT_API_KEY` from the sandbox app. Set the incoming SMS callback to
  `https://<your tunnel>/sms/webhook/africastalking`.

Job alerts then go out as real SMS too. Commands a learner can text: `JOBS`, `SUB <word>`, `UNSUB`,
`LANG AM`, `LANG EN`, `AI ON`, `AI OFF`, `FORGET`, `HELP`.

### Run the tests

```bash
pip install -r requirements.txt
python -m pytest server/tests tests     # 96 tests
python server/evaluate.py               # answer quality: 30 questions, see "Quality" below
cd tests/a11y && npm install && node axe.mjs http://localhost:8001/demo/blank.html page open
```

### If something goes wrong

| Problem | Fix |
|---|---|
| `Port 8001 is already in use` | Another copy is running. Close its window, or press `Ctrl+C` there. |
| `No module named fastapi` / `uvicorn` | The virtual environment is not active, or `pip install -r requirements.txt` was not run. |
| `python` is not recognised (Windows) | Reinstall Python and tick "Add Python to PATH", or use `py` instead of `python`. |
| Mimi is silent | Browsers hold sound until the first tap or key press: press "Start Mimi". In Chrome there is no Amharic voice without an Azure key; use Edge. |
| "Listening" but nothing is written | Allow the microphone (the icon in the address bar). On a phone, use the HTTPS tunnel. |
| Answers say "working offline" | No AI key, or the free Gemini quota is used up for today (`API error 429` in the log). It resets at midnight Pacific time. |
| Telegram shows `"configured": false` at http://localhost:8000/telegram/status | `TELEGRAM_BOT_TOKEN` is missing from `.env`, or the servers were not restarted after adding it. |
| `cloudflared` / `ollama` not recognised | Close and reopen the terminal after installing (or VS Code entirely). |

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
| `consent` | `given`: the platform already asked this learner (for example at sign-up) and they agreed to online AI and voice, so Mimi does not ask again. Use it only if the platform really asked. | not set: Mimi asks |
| `theme` | `light`, `dark`, or `auto`: follow the phone or computer's dark setting | `auto` |
| `tts`, `stt` | `browser` or `server`: force where speech is made and recognised | `auto` |

| Event (on `document`) | `detail` | When |
|---|---|---|
| `db-assistant:question` | `{ text, language }` | The learner asks something |
| `db-assistant:escalated` | `{ ticketId }` | The learner asked for a person |

Mimi lives in a shadow root (the host's CSS cannot change her, hers cannot change the host), sets no
global variables and changes no host element. She uses the host's font (`--bs-body-font-family`) when
there is one, and keeps herself on screen even on a host page that is wider than the phone.

## Install, Level 2: the API

The full specification is [openapi.yaml](openapi.yaml); try every call at `/docs`.

```bash
# Ask (answers only from the course, with sources). "cloud": false if the learner did not agree to a cloud AI.
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

**Webhook.** Set `WEBHOOK_URL` in `.env`: the server posts `{"event", "at", "data"}` to it when a
learner asks for a person (`ticket.opened`) or sends an interview accommodation request
(`accommodation.requested`). No name, phone number or message text is sent.

**AI providers.** One switch in `.env`, `ABLEWAY_PROVIDERS`, in order of preference: `gemini` (cloud),
`local` (an open model through Ollama, no internet) and `offline` (keyword search and a hand-written
FAQ, no AI). Missing keys are skipped, and offline is always last, so Mimi is useful with no AI budget
at all. A new provider is one class in `server/providers.py`.

## Install, Level 3: open standards

- **schema.org JobPosting:** every job on `pages/jobs.html` is described in JSON-LD, so job boards and
  search engines can read it.
- **LTI 1.3:** not done. Mimi would connect as an LTI tool whose launch page loads the same script tag;
  the LMS would pass the course and lesson as launch claims, which map to the `course` and `lesson`
  attributes. No learner identity is needed for answers.

## How Mimi answers (RAG) and its quality

Mimi is a retrieval-augmented tutor:

1. **Retrieve.** The course pages are split by their headings (`server/extract.py`), and each question
   is matched against them with BM25 keyword search (`server/retrieval.py`). Amharic questions are
   turned into English search words with a word list (`server/data/glossary_am.json`) and, with AI,
   a translation.
2. **Check.** If more than half of the question's words are not in the matched course text, it is not
   a course question: Mimi says so and offers a person, **without calling the AI at all**.
3. **Generate.** Only the matched sections go to the AI, which must answer from them in the learner's
   language and cite them `[1]`. An answer without a real citation is not shown as sourced.
4. **No AI:** the matched course text is quoted directly, with the same sources.

**Built for Amharic.** Letters that sound the same are treated as one (ሥራ = ስራ, ፀ = ጸ, ሐ = ኀ = ሀ,
ዐ = አ), and words are also compared by their consonants only, so a vowel that speech recognition gets
wrong (ማሰረከቢያ for ማስረከቢያ) still finds the right section. The AI uses a fixed list of Amharic
course terms, so the learner always hears the same word for "deadline" or "assignment", and the
voice reads abbreviations correctly (AI → ኤ አይ, 85% → 85 በመቶ).

**Measured.** `python server/evaluate.py` asks 30 questions (15 English, 10 Amharic including a
misspelled one, 5 off-topic) and checks the cited section:

| Mode | Right source | Refused off-topic | Total |
|---|---|---|---|
| Offline (no AI), measured 15 November 2026 | 25 / 25 | 5 / 5 | **30 / 30** |
| With Gemini (`--cloud`) | *not measured yet: the free daily quota was used up during testing; run it after the reset* | | |

## Languages and how to add one

Every sentence Mimi says or shows is in [module/i18n/en.json](module/i18n/en.json) and
[module/i18n/am.json](module/i18n/am.json); none is written in the code. To add a language (for
example Tigrinya, Afaan Oromo, Somali or Arabic):

1. Copy `en.json` to `module/i18n/<code>.json` and translate it. Set `meta.speech` (for example
   `ti-ET`) and `meta.dir` (`rtl` for Arabic: the layout uses logical CSS properties, so it mirrors).
   Add the words that language's voice mispronounces to `pronounce`.
2. Add the code to `LANGUAGE_CODES` in `module/db-assistant.js`.
3. On the server, add the language name in `LANGUAGES` in `server/tutor.py`, so AI answers come in it.

Right-to-left text already works in any language: every message has `dir="auto"`. Job deadlines are
shown in the Ethiopian calendar in Amharic (`server/channels/ethiopian.py`), and phone numbers in any
form (`09…`, `07…`, `+251…`) are stored as `+251…`.

## Offline and slow connection

- Measured on Chrome's "Slow 3G" setting (2 s latency, about 400 kbit/s), cache off: Mimi appears after
  **7.4 s** on the plain page. On the Savanna lesson page it is about 21 s, because the browser first
  loads Savanna's own 1.5 MB of stylesheets.
- The module is **44 KB** compressed (script 30 KB, stylesheet 7 KB, two language files 7 KB).
- **No signal on the phone:** a question is kept on the phone, Mimi says "Saved on this phone. It will
  send when you are online.", and sends it by itself when the connection is back.
- With no internet on the server, answers still come from the offline search and FAQ.
- `/lite` is a plain HTML form for the slowest phones, and SMS works with no data at all.

## Data and privacy

| What | Where | Kept | How to delete |
|---|---|---|---|
| The conversation | The learner's browser tab only (`sessionStorage`); the server keeps nothing between questions | Until the tab closes | "Clear chat"; "Download chat" gives the learner a copy |
| Language, display and consent choices | The learner's browser (`localStorage`) | Until the learner clears it | The browser's "clear site data" |
| Questions saved while offline | The learner's browser (`localStorage`) | Until sent | Sent and removed automatically |
| Questions for the teacher view | `channels.db`: text, language, channel and date. No name, phone number, IP or time | Kept for the teacher view | Delete the database file |
| Help tickets and live chat | `channels.db` | Until closed | Telegram `/forget` and SMS `FORGET` remove the link to the learner |
| Telegram and SMS choices, job alert subscriptions | `channels.db`: the chat id or number, language, consent, keywords | Until deleted | Telegram `/forget`, SMS `FORGET` (everything), `UNSUB` (alerts only) |
| Interview accommodation requests | A separate database, `accommodations.db`, seen only by signed-in staff at `/accommodation/requests`, never by employers | Until a person handles it | "Mark as handled" deletes it |

- **Nothing leaves the host without the learner's consent.** Before Mimi speaks or sends anything, she
  asks once, in Amharic and English: online AI and voice (Google, Microsoft), or text from the course
  only. Until the learner answers, nothing is spoken, sent or recorded. With "No", questions are
  answered from the course text on the host (or a local model), only voices built into the device are
  used, and there is no listening. The choice can be changed at any time ("Online AI and voice" in the
  chat settings, `/privacy` on Telegram, `AI ON` / `AI OFF` by SMS, a tick box on `/lite`, unticked by
  default). API clients send `"cloud": false` when the learner has not agreed.
- What leaves the server after consent: the question and the matching course text go to the AI
  provider the host configured (Gemini's free tier may use them to improve Google's products; use a
  paid tier or the local or offline provider to avoid that). Voice goes to the speech service (Azure or
  Gemini on the server; in Edge, Microsoft's online voices).
- On a phone, Mimi does not start talking until the learner's first tap, so she never talks over
  TalkBack or VoiceOver reading the page.
- The microphone and screen sharing are off until the learner starts them, and clearly shown while on.
- Keys stay on the server in `.env`, which is not in git; the browser never sees them.
- Only test data is included: the jobs and learners are invented.

## Cost to run per month

For 3,000 learners, assuming 5 questions each per week (about 65,000 questions a month):

| Item | Cost |
|---|---|
| Server: one small virtual machine (2 GB) running both containers | about $6–12 |
| AI answers: off-topic questions never reach the AI, repeated questions come from the answer cache, and the rest (roughly 30,000) go to a Flash-Lite class model at about 2,500 tokens in and 250 out | about $25–45 (check current prices) |
| Voices: browser voices (Edge) and recorded phrases | $0 |
| Optional: Azure Speech free tier (0.5 M characters of speech, 5 hours of recognition a month) | $0 within the free tier |
| SMS: SMS Gateway for Android on a phone with a local SIM package | the SIM plan only |
| **Total** | **about $30–60**, or the server cost only with the offline provider |

No feature depends on a paid service: every AI, voice and SMS provider can be swapped or removed.

## Finished and not finished

**Finished and tested:**

- The tutor in Amharic and English: sources on every answer, refusals for off-topic questions, no AI
  call when the course has nothing, 30/30 on the evaluation set offline.
- Voice in and out, with captions. Consent before anything leaves the host. Silence until the first
  tap on phones.
- One-click help with the conversation passed on; screen sharing with a visible stop control.
- Telegram: typed questions and voice messages, "🔊 Listen", `/voice on`, `/privacy`, `/forget`.
- SMS (plain text, 160 characters) with real gateways for development; `/lite`.
- Job answers, job alerts, interview accommodation requests handled by a person.
- Simple mode, teacher view, offline question queue, "Download chat".
- The pluggable AI layer with an offline mode; the API with `/docs`, OpenAPI and a webhook;
  schema.org JobPosting; Docker Compose.
- 96 automated tests (`python -m pytest server/tests tests`) and an axe-core check (`tests/a11y`):
  0 issues on every page, with the chat open and closed.

**Not finished or not yet verified:**

- Not yet tested by our co-designer with NVDA and TalkBack (see [CONFORMANCE.md](CONFORMANCE.md)).
- The local model (Ollama) path is built and covered by tests, but not yet run with Ollama installed.
- Amharic speech recognition is good but not perfect; names and places are often wrong. Mimi always
  shows what she heard, so the learner can correct it or type instead.
- Only Amharic and English language files; the mechanism for more is in place.
- The real SMS gateways are tested with simulated requests only, not yet with a real phone and SIM.
- The Amharic text should be read once more by a native speaker on the team.

## Libraries and their licences

| Library | Used for | Licence |
|---|---|---|
| FastAPI, Uvicorn | Channels server | MIT, BSD-3-Clause |
| Jinja2, python-multipart, httpx, python-dotenv | Channels server | BSD-3-Clause, Apache-2.0, BSD-3-Clause, BSD-3-Clause |
| pytest | Tests | MIT |
| Swagger UI 5.17.14 (from jsDelivr, on `/docs` only) | API documentation page | Apache-2.0 |
| axe-core 4.10.2 (tests only) | Accessibility check | MPL-2.0 |
| lameenc (optional, not installed by default) | Converts Gemini's voice to MP3 for Telegram voice messages | LGPL-3.0 |

The tutor server and the module itself use only the Python standard library and plain JavaScript.
The Savanna starter pages and assets belong to ALX (see [docs/SAVANNA_STARTER.md](docs/SAVANNA_STARTER.md));
we added only the two lines that load Mimi to each page. Our code: see [LICENSE](LICENSE).
