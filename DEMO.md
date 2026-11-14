# Demo: one learner story through every channel

Selam is a learner on the Virtual Assistant course. She reads Amharic and English, has a slow
connection at home, and wants a remote job. The story below touches every feature of the
channels and handoff work. The number in brackets is the requirement it shows.

## Setup (once)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:

- `TUTOR_PASSWORD=demo123`
- `TELEGRAM_BOT_TOKEN=<token from @BotFather>` (optional: without it, skip the Telegram steps)
- `ALERTS_INTERVAL_MINUTES=3`

Start the server from the repo root and leave it running:

```bash
python -m uvicorn server.main:app --port 8000
```

The log shows either `Telegram bot @<name> is polling.` or a warning that the bot was skipped.
Check with <http://localhost:8000/telegram/status>.

Answers come from the stub in `server/channels/core_client.py` until the real assistant is
connected. The stub knows three topics: **skills**, **the future of the VA industry / AI**, and
**the 70% graduation threshold**. Anything else gets "I don't know".

Use Chrome or Edge for the screen-share step, and open pages on `localhost` (browsers only
allow screen capture on `localhost` or HTTPS).

## The story

### 1. Slow connection: the lite page [2, 11, 12]

1. Open <http://localhost:8000/lite>.
2. Choose **አማርኛ**, type `ለመመረቅ ምን ያስፈልጋል?` and press **Ask**.
3. The page comes back in Amharic with the answer and its source
   (`homepage-v1-self-paced.html — Course progression`).
4. Show: view the page source. There is no `<script>` tag; the answer has `lang="am"` and
   `dir="auto"`. Tab through the form: every field has a label and a visible focus ring.

### 2. No internet at all: SMS [3, 4, 5]

1. Open <http://localhost:8000/sms/simulator>. It is a pretend phone with the number
   `+251911000001`.
2. Send `What skills do I need?`. The reply is short (the character count is under each bubble,
   always under 300).
3. Send `LANG AM`, then `ለመመረቅ ምን ያስፈልጋል?`. The reply is in Amharic.
4. Send `JOBS`. The three newest jobs come back in one message.
5. Send `SUB calendar`. She is now subscribed to job alerts for "calendar".
6. Trigger the alert run by hand instead of waiting for the scheduler:

   ```bash
   curl -X POST http://localhost:8000/jobs/run-alerts
   ```

   Within four seconds, yellow alert bubbles appear on the phone: the matching jobs, read from
   the outbox table. Run the command again: `"sent": 0`, because nothing is sent twice.
7. The same webhook without the simulator:

   ```bash
   curl -X POST http://localhost:8000/sms/inbound \
     -H 'Content-Type: application/json' \
     -d '{"from": "+251911000001", "text": "HELP"}'
   ```

### 3. On her phone: Telegram [1, 4, 5, 12]

Open the bot in Telegram and send, in order:

| Send | What happens |
|---|---|
| `/start` | Greeting, and how to choose a language. |
| `/lang am` | "ቋንቋ ወደ አማርኛ ተቀይሯል።" The choice is remembered for this chat. |
| `ክህሎቶች ምንድን ናቸው?` | Answer in Amharic, followed by "ምንጮች: …" (the citation). |
| `የአየር ሁኔታው እንዴት ነው?` | "አላውቅም፣ እባክዎ ሰው ይጠይቁ።" and an offer to send `/human`. |
| `/lang en` | Back to English. |
| `/help` | The list of commands. |
| `/jobs` | The five newest jobs with description, skills, deadline and link. |
| `/subscribe support` | Subscribed. Then run `curl -X POST http://localhost:8000/jobs/run-alerts`: the matching jobs arrive as bot messages. |
| `/unsubscribe` | Alerts stop. |

### 4. A private request: interview accommodation [6]

1. In Telegram send `/accommodation`. The bot asks three questions, one at a time: which job or
   interview, what support, how to contact her. Answer, for example:
   `Abay Online Market interview`, `Sign language interpreter`, `Telegram @selam`.
2. The web version of the same form, with no JavaScript:
   <http://localhost:8000/accommodation?lang=am>. Fill it in and send it.
3. Show that the requests are stored in their own file:

   ```bash
   sqlite3 data/accommodations.db "SELECT id, job, channel, created_at FROM accommodation_requests;"
   ```

   and that they are nowhere else (both commands print nothing):

   ```bash
   sqlite3 data/channels.db "SELECT question FROM question_log;" | grep -i interpreter
   curl -s http://localhost:8000/teacher | grep -i interpreter
   ```

### 5. The assistant does not know: talk to a person [7, 8, 11]

1. Tutor: open <http://localhost:8000/handoff/console> in one window and sign in with
   `demo123`.
2. Learner: on <http://localhost:8000/lite> ask `Where is the cafeteria?`. The answer is
   "I don't know, ask a person." Follow the **Talk to a person** link and press
   **Start a chat with a tutor**. (The widget will do the same with
   `AssistantHandoff.open()`. To create a ticket by hand:
   `curl -X POST http://localhost:8000/handoff/tickets`, then open the `chat_url` it returns.)
3. Tutor: within five seconds the ticket appears under **Open tickets**. Click it.
4. Chat in both directions. Type a message in Amharic and one in Arabic, for example
   `مرحبا، أحتاج مساعدة`: the Arabic message is laid out right to left.
5. Telegram does the same: send `/human` in the bot, then a message. A second ticket (channel
   `telegram`) appears in the console; the tutor's replies arrive in Telegram as
   "Tutor: …". `/end` in Telegram, or **Close ticket** in the console, ends it.

### 6. "Let me show you": screen share [9]

1. Learner chat page: press **Share my screen** and pick a screen, window or tab in the
   browser's dialog.
2. A red banner, **You are sharing your screen**, with a **Stop** button stays at the top of
   the learner's page.
3. Tutor console: the learner's screen appears above the messages. The tutor can only watch.
4. Stop it in either way: the **Stop** button in the banner, or the browser's own
   "Stop sharing" control. The banner disappears and the tutor's video goes away.
5. Show that the tutor has no button to start a share: it can only start from the learner's
   click.
6. Tutor: press **Close ticket**. The learner's page says the chat is closed.

### 7. What the teacher sees [10]

Open <http://localhost:8000/teacher>.

- **Most asked questions**: the questions from steps 1 to 3 and 5, grouped ("What skills do I
  need?" and "what skills do i need" count as one).
- **By language** and **By channel**: counts for `lite`, `sms` and `telegram`.
- **Questions that got "I don't know"**: the cafeteria and weather questions. These are the
  content gaps.
- There are no names, phone numbers or chat ids on the page, and no accommodation requests.
  The table behind it has only these columns:

  ```bash
  sqlite3 data/channels.db "PRAGMA table_info(question_log);"
  ```

## Tests

```bash
python -m pytest tests/test_channels_handoff.py -q
```

## Start again from a clean state

Stop the server, then:

```bash
rm -f data/channels.db data/accommodations.db
```
