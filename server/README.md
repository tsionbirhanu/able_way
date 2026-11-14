# Ableway tutor: backend, web widget and shared channel core

A course tutor for the Savanna pages that answers in Amharic and English, only from the course
content, with a link to the page each answer came from.

## Run it

```
python server/app.py
```

Then open <http://localhost:8000/> and press **Ask the tutor** on any of the three pages.
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
| `ABLEWAY_GEMINI_MODEL` | `gemini-2.5-flash` | Gemini model name. |
| `ABLEWAY_OLLAMA_MODEL` | `gemma3:4b` | Local model name. |
| `ABLEWAY_OLLAMA_URL` | `http://127.0.0.1:11434` | Where Ollama listens. |
| `ABLEWAY_PORT` / `ABLEWAY_HOST` | `8000` / `127.0.0.1` | Where this server listens. |

## The API

`POST /api/ask`

```json
{ "question": "Can I resubmit an assignment?", "lang": "en", "simple": false, "history": [] }
```

- `lang`: `"en"` or `"am"`, the language of the answer.
- `simple`: `true` for short sentences and everyday words.
- `history`: earlier turns as `[{"role": "user" | "assistant", "content": "..."}]`. The client keeps
  the conversation; the server stores nothing and does not log questions.

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
| `data/faq.json` | Hand-written offline answers in both languages. |
| `data/glossary_am.json` | Amharic words mapped to English search terms, for offline search. |
| `tests/` | `python -m unittest discover -s server/tests` |
| `../assistant/` | The web chat widget (`assistant.js`, `assistant.css`). |

To add more content (for example job listings), drop a `data/chunks_jobs.json` file with the same
fields as `chunks.json` and `"corpus": "jobs"`. It is loaded automatically.

## Add the widget to a page

```html
<script src="../assistant/assistant.js" defer></script>
```

Add `data-api="https://your-server"` when the API is not on `http://localhost:8000`.
