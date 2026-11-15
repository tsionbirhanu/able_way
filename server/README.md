# Ableway tutor: backend, web widget and shared channel core

A course tutor for the Savanna pages that answers in Amharic and English, only from the course
content, with a link to the page each answer came from.

## Run it

```
python server/app.py
```

Then open <http://localhost:8000/>. On each classroom page Mimi greets the learner by voice in Amharic,
asks whether they want Amharic or English, and then holds a hands-free spoken conversation (or a
typed one: **Turn off voice** at any time). See [Mimi's voice](#mimis-voice) below.
Nothing needs installing for this: with no AI configured the tutor runs in offline mode.
The pages also work opened straight from disk, as long as the server is running.

## Turn on the AI providers

The tutor tries the providers in order and uses the first one that works.

| Provider | What it needs | How to turn it on |
|---|---|---|
| `gemini` (Google Gemini) | Internet, a Gemini API key | Copy `server/.env.example` to `server/.env` and set `GEMINI_API_KEY` |
| `local` (Ollama) | [Ollama](https://ollama.com) running on this computer | `ollama pull gemma3:4b` |
| `offline` | Nothing | Always on, always last |

`GET /api/health` shows which providers are ready and why the others were skipped. The Gemini API key stays on the server and is never sent to the browser. Google AI Studio offers free-tier use subject to the selected model's current quota, availability and terms; check its dashboard before a demo.

Settings (in `server/.env` or the environment):

| Name | Default | Meaning |
|---|---|---|
| `ABLEWAY_PROVIDERS` | `gemini,local,offline` | Order to try. `offline` alone forces offline mode. |
| `ABLEWAY_GEMINI_MODEL` | `gemini-3.5-flash-lite` | Gemini model name. For voice, a fast model matters: in testing `gemini-3.5-flash-lite` answered in 1.5–4 s with natural Amharic, `gemini-3.5-flash` took 20–40 s. |
| `ABLEWAY_OLLAMA_MODEL` | `gemma3:4b` | Local model name. |
| `ABLEWAY_OLLAMA_URL` | `http://127.0.0.1:11434` | Where Ollama listens. |
| `ABLEWAY_PORT` / `ABLEWAY_HOST` | `8000` / `127.0.0.1` | Where this server listens. |

## The API

`POST /api/ask`

```json
{ "question": "Can I resubmit an assignment?", "lang": "en", "simple": false, "history": [],
  "session_id": "…", "context": { "page": "pages/homepage-v1-paced.html", "course": "WR 100", "lesson": "Week 10" },
  "intent": null, "voice": false, "detect_switch": false }
```

- `lang`: `"en"` or `"am"`, the language of the answer.
- `simple`: `true` for short sentences and everyday words.
- `history`: earlier turns as `[{"role": "user" | "assistant", "content": "..."}]`. The client keeps
  the conversation; the server stores nothing and does not log questions.
- `session_id`: from `POST /api/session`. When `lang` is missing, the session's language is used, and
  the server keeps the session's language up to date (only the language is stored, in memory).
- `context`: the page the learner is on. "This lesson" then means that lesson, its sources rank first,
  and the course name is filled in from the index.
- `intent: "lesson_intro"`: no question needed; Mimi welcomes the learner to the lesson in `context`.
- `voice: true`: shorter replies that end with a question, for the spoken conversation.
- `detect_switch: true`: "English please" or "ወደ አማርኛ ቀይሪ" switches language (response has
  `switch_lang`) without calling the model. Telegram and `/lite` leave it off; they have their own.

Response:

```json
{
  "answer": "Resubmission applies only to ... [1]",
  "grounded": true,
  "citations": [{ "n": 1, "title": "Course Overview: Resubmission (Second Deadline)", "url": "pages/homepage-v1-paced.html", "course": "...", "snippet": "..." }],
  "lang": "en",
  "provider": "offline",
  "provider_label": "Offline answers (no AI model)"
}
```

Other endpoints: `POST /api/session` (`{"session_id"?, "lang"?}`), `POST /api/tts` (`{"text", "lang",
"cache"}` → audio, or 503 so the browser uses its own voice), `POST /api/transcribe?lang=am` (a WAV
recording → `{"text"}`).

`[1]` in the answer refers to citation `n: 1`. `grounded` is `false` when the tutor could not find
the answer in the course content; a channel can use that to offer "talk to a person".

Telegram, SMS and `/lite` use `server/channels/core_client.py`, which now calls this same tutor by default. Set `CORE_ASK_IMPORT` or `CORE_ASK_URL` only when replacing the shared tutor with another core.

## Files

| File | What it does |
|---|---|
| `extract.py` | Reads `pages/*.html` and writes `data/chunks.json`. Re-run it when the pages change. |
| `retrieval.py` | Keyword search over the chunks. |
| `providers.py` | The three AI back ends behind one interface. Add a new one here. |
| `tutor.py` | Search, prompt, citation checking, offline answers. |
| `app.py` | HTTP API and static file server. |
| `sessions.py` | The language each classroom session chose. |
| `speech.py` | Mimi's voice (text to speech) and server speech recognition, behind one interface. |
| `data/faq.json` | Hand-written offline answers in both languages. |
| `data/glossary_am.json` | Amharic words mapped to English search terms, for offline search. |
| `tests/` | `python -m unittest discover -s server/tests` |
| `../module/` | The web module: `db-assistant.js`, `db-assistant.css` and the language files in `i18n/`. |

To add more content (for example job listings), drop a `data/chunks_jobs.json` file with the same
fields as `chunks.json` and `"corpus": "jobs"`. It is loaded automatically.

## Add the widget to a page

```html
<script src="../module/db-assistant.js" defer></script>
```

Add `data-api="https://your-server"` when the API is not on `http://localhost:8000`. Other options:
`data-course`, `data-lesson` and `data-lesson-selector` (CSS selector read at question time, e.g. the
active week) give Mimi the lesson context; `data-lang` sets the greeting language (default `am`);
`data-auto-welcome="false"` disables the spoken greeting; `data-tts` / `data-stt` (`auto`, `server`,
`browser`) force where speech comes from.

## Mimi's voice

Gemini writes every answer; speech is a separate, swappable layer (`speech.py`).

**Speaking (text to speech).** By default the server asks Gemini TTS for audio in one female prebuilt
voice, **Sulafat**, for both languages, so Mimi sounds like the same person in Amharic and English.
Tested: Amharic and English audio were generated and transcribed back almost word for word; median
pitch was 189–212 Hz (typical female range). Whether it *sounds* right to an Amharic listener still
needs a person to listen. If the server voice is unavailable, the browser speaks with its most
female-sounding voice for the language (browsers do not report gender, so this goes by voice name,
e.g. Microsoft Edge's "Mekdes" for Amharic). Most browsers have **no Amharic voice**; then Mimi says
so on screen and the conversation continues in text and listening.

**Quota.** The Gemini free tier allows only **10 TTS requests per day per model, per project**
(several keys in one project share it). Models in `ABLEWAY_TTS_MODELS` are tried in order and skipped
while their quota is used up. Fixed phrases (greeting, confirmations) are recorded once to
`data/tts_cache/` and then cost nothing. For real classroom use, enable billing or use Google Cloud
Text-to-Speech, whose `am-ET-Wavenet-A` voice Google lists as female (not tested here: no key).

**Listening (speech to text).** Chrome and Edge use their own recogniser (Amharic `am-ET` included).
Other browsers, or when the browser's recogniser fails, record the learner's turn and send it to
`/api/transcribe` (Gemini). A turn ends after about 1.5 s (English) or 1.9 s (Amharic) of silence.

| Name | Default | Meaning |
|---|---|---|
| `ABLEWAY_TTS` | `gemini` | Voice providers in order: `gemini`, `google`, or `none` (browser voice only). |
| `ABLEWAY_TTS_VOICE` | `Sulafat` | Gemini prebuilt voice (female options include Sulafat, Aoede, Kore, Leda). |
| `ABLEWAY_TTS_MODELS` | `gemini-3.8-flash-lite-tts,gemini-3.1-flash-tts-preview,gemini-2.5-flash-preview-tts` | Gemini TTS models, tried in order. |
| `GOOGLE_TTS_API_KEY` | – | Google Cloud Text-to-Speech key, for `ABLEWAY_TTS=google`. |
| `ABLEWAY_TTS_VOICE_AM` / `ABLEWAY_TTS_VOICE_EN` | `am-ET-Wavenet-A` / `en-US-Neural2-F` | Google Cloud voices. |
| `ABLEWAY_STT` | `gemini` | Server speech recognition; anything else turns it off. |
| `ABLEWAY_STT_MODELS` | `gemini-3-flash-preview,gemini-3.5-flash-lite,gemini-2.5-flash-lite` | Transcription models, tried in order (the lite models misheard short Amharic answers in testing). |
