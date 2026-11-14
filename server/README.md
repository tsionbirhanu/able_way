# Ableway tutor: backend and web widget

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
| `cloud` (Claude) | Internet, an Anthropic API key | `pip install -r server/requirements.txt`, then copy `server/.env.example` to `server/.env` and put the key in it |
| `local` (Ollama) | [Ollama](https://ollama.com) running on this computer | `ollama pull gemma3:4b` |
| `offline` | Nothing | Always on, always last |

`GET /api/health` shows which providers are ready and why the others were skipped.

Settings (in `server/.env` or the environment):

| Name | Default | Meaning |
|---|---|---|
| `ABLEWAY_PROVIDERS` | `cloud,local,offline` | Order to try. `offline` alone forces offline mode. |
| `ABLEWAY_CLAUDE_MODEL` | `claude-opus-5-5` | Claude model. |
| `ABLEWAY_CLAUDE_EFFORT` | `low` | How hard Claude thinks; `medium` is slower and more careful. |
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

Telegram, SMS and other channels should call this endpoint (or `Tutor().ask(...)` from Python)
so that every channel gives the same answers.

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
