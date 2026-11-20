# Mimi: full test guide (hosted version)

**Site:** https://able-way.onrender.com
**Start page:** https://able-way.onrender.com/pages/concept-with-navigation.html

Use **Microsoft Edge** on a computer (it has the natural Amharic voice). For the phone tests, use
Chrome on Android. Tick each box as you go; write what went wrong next to any box you cannot tick.

> The free server sleeps after 15 minutes without visits. Open https://able-way.onrender.com/api/health
> first and wait until it loads (up to about a minute). Then everything else is fast.

---

## 0. The server is up (2 minutes)

| | Open | Expected |
|---|---|---|
| ☐ | https://able-way.onrender.com/api/health | JSON with `"chunks": 81`, a `"providers"` list where **Gemini** says `"available": true`, and `"help_desk": {"ok": true, "waiting": …, "telegram": "running"}` |
| ☐ | https://able-way.onrender.com/telegram/status | `"configured": true, "running": true, "username": "mimi_tutor_liveBot", "mode": "webhook"` |
| ☐ | https://able-way.onrender.com/docs | The API contract page (Swagger) opens |
| ☐ | https://able-way.onrender.com/api-docs | The list of every route opens |
| ☐ | https://able-way.onrender.com/server/.env | **Not found** (private files are never served) |

If `help_desk` says `"ok": false`, or the page shows error 503: open Render → mimi-tutor → **Logs**,
and check `PUBLIC_BASE_URL`, `CHANNELS_DB_PATH` and that `CHANNELS_URL` is deleted.

---

## 1. First visit, consent and greeting (3 minutes)

Open the start page in a **new InPrivate window** (Ctrl+Shift+N), so Mimi treats you as new.

- ☐ Mimi's card appears at the side. Nothing is spoken yet.
- ☐ The question **"Before Mimi starts"** is shown in Amharic and English, with **"Allow and start"** and **"No, text only"**.
- ☐ Press **Allow and start**. Mimi greets you **in Amharic, in one voice (መቅደስ)**, and ends with
  *"ለእንግሊዝኛ 2፣ ለአፋን ኦሮሞ 3 ይጫኑ።"*
- ☐ The greeting shows the same words on screen, word by word, and buttons **አማርኛ · English · Afaan Oromoo**.
- ☐ Press the key **2** (the cursor is in the message box): Mimi says *"Great! I will help you in English…"* in an English voice.

Repeat in a new InPrivate window with **1** (Amharic) and **3** (Afaan Oromo, read by a Somali voice).

---

## 2. The judges' test: one question in English, the same in Amharic (3 minutes)

The judges will do exactly this. In English:

- ☐ Type or say **"What is the late submission policy?"**
  - The answer is written by the AI, says "7 days", "85%" and "5 days", and has a number like **[1]**.
  - **Sources** below it links to *Course Overview: Late Policy for WR 100*. Clicking it opens the lesson at that section.
  - Mimi reads the answer aloud, and the words appear as she speaks.

Switch to Amharic (Settings → **አማርኛ**, or say "Amharic"):

- ☐ Ask **"ዘግይቶ ማስገባት ይቻላል?"** The answer is in Amharic, with the same kind of source link, spoken by መቅደስ.
- ☐ Ask **"Who won the World Cup?"** Mimi says it is not in the course and offers a person ("say 4").

---

## 3. Keyboard only, for one minute (the judges' second test)

Put the mouse away. Start on the lesson page.

- ☐ **Tab** moves through the page and reaches Mimi. The focus ring (yellow) is always visible.
- ☐ At the greeting, **1**, **2** or **3** chooses the language.
- ☐ Type a question and press **Enter**: it is sent.
- ☐ After an answer, the menu numbers work: **4** = talk to a person, **0** = hear the choices again.
- ☐ **Escape** closes Mimi, and focus goes back to the button that opens her.
- ☐ Every button (Talk to a person, Share screen, Telegram, Settings, Replay) can be reached and pressed with Tab and Enter.

---

## 4. Talk to a person, end to end (5 minutes, two people)

**Person A (learner)**, on the lesson page:
- ☐ Ask any question first, then press **Talk to a person** (or say **4**).
- ☐ The help chat opens in a new tab. If the browser blocks the new tab, Mimi shows a focused button
  **"Open the help chat"**; press it.
- ☐ The help chat says a tutor will answer, and stays open.

**Person B (tutor)**, on another computer or window:
- ☐ Open https://able-way.onrender.com/handoff/console and sign in with **your name and password** from
  `TUTORS` (for example Hana). The header says "Signed in as Hana (tutor)"; only **Live Chat** and
  **Questions Log** are in the menu.
- ☐ The new request says **"Waiting for a tutor"**. Press **"Take this request →"**: the learner's chat
  shows **"Hana, a tutor, has joined and will help you."**
- ☐ Its first message shows **where the learner is** (lesson and section) and the **conversation with Mimi so far**.
- ☐ Write a reply. **Person A sees it at once**, and A's answer appears for B.
- ☐ **Share screen** (A, on a computer): A starts it, sees "You are sharing your screen", B sees the
  screen, and A's **Stop** ends it.
- ☐ **Talk by voice** (A): A presses it and allows the microphone; B hears A. B presses **"Turn on my
  microphone"**: A hears B. A's **Mute** and **End voice call** work.

**Person C (a second tutor)** signs in as Abel: the request shows **"Hana is helping"** and cannot be
opened. **The coordinator** signs in with `ADMIN_PASSWORD`: the menu also has **Teacher Analytics** and
**Accommodations**, and the request offers **"Watch or take over"**.
- ☐ B presses **Close ticket**: A's chat says it has ended.

If anything fails, open https://able-way.onrender.com/api/health: `"help_desk"` must say `"ok": true`.

---

## 5. Works without AI (the judges' third fix, 2 minutes)

- ☐ In a new InPrivate window, choose **"No, text only"** at the first question.
- ☐ Ask "What is the late submission policy?" The answer quotes the course text, says
  **"Answered offline, without AI."**, and still has its source.
- ☐ Ask "Who won the World Cup?" It is still refused, with the offer of a person.
- ☐ Settings → turn **Online AI and voice** back on: answers are written by the AI again.

---

## 6. Answers at the learner's level (2 minutes)

- ☐ Settings → **Answer level: Simple · Standard · Detailed**.
- ☐ Ask the same question three times, once per level: Simple is short, Detailed is longer with an
  example, and **all three show the same source**.
- ☐ Reload the page: your level is remembered.

---

## 7. The lesson, read and explained (3 minutes)

- ☐ Select a sentence of the lesson with the mouse: an **"Explain this"** button appears next to it.
  Press it: Mimi explains that exact part, citing its section.
- ☐ Press **Read the lesson to me**: Mimi outlines a section on the page, explains it, and waits for
  **Next section / Repeat / Stop reading** (buttons, or say "next", "repeat", "stop").
- ☐ **Explain what I am reading**: scroll to a section, press it, and Mimi explains that section.

---

## 8. Voice (3 minutes, with a microphone)

- ☐ Press **Press to talk** (it turns green), ask a question aloud. Your words appear as you speak, on the right.
- ☐ Mimi answers aloud; **Stop speaking** stops her; **Replay** repeats an answer.
- ☐ **Turn off voice**: Mimi stays silent and you can keep typing; the conversation is kept.
- ☐ In Amharic, ask aloud **"ዘግይቶ ማስገባት ይቻላል?"** and check what Mimi heard (shown on screen).

---

## 9. Settings and display (2 minutes)

- ☐ **Text size**: Normal / Large / Extra large. Nothing is cut off; Mimi stays on screen.
- ☐ **Ctrl and +** to 200% zoom: Mimi still fits, nothing is hidden behind her.
- ☐ **Download chat** saves the conversation as a file; **Clear chat** empties it.
- ☐ **Telegram** button (in the help row) opens @mimi_tutor_liveBot.
- ☐ Turn on dark mode in Windows (Settings → Personalisation → Colours → Dark): Mimi turns dark and stays readable.

---

## 10. Phone (5 minutes, Android with Chrome)

- ☐ Open the start page on the phone. Mimi is a small button at the bottom; it does **not** start talking by itself.
- ☐ Tap it: the chat fills the screen; text is large, buttons are easy to press.
- ☐ Turn on **TalkBack**: swipe through Mimi; every button is read with its name; a new answer is read out.
- ☐ Press **Share screen**: Mimi says screen sharing is not possible on Android and that the lesson page
  is shared with the tutor instead.
- ☐ Turn on aeroplane mode, ask a question: Mimi says **"Saved on this phone. It will send when you are
  online."** Turn the internet back on: it is sent by itself.

---

## 11. Telegram (5 minutes)

Open **@mimi_tutor_liveBot** (https://t.me/mimi_tutor_liveBot).

- ☐ `/start` answers. The **Menu** button (bottom left) lists the quick questions (📅 deadline, ⏰ late policy, …).
- ☐ Tap **/deadline**: the question is shown, then the answer with its source and a **🔊 Listen** button.
- ☐ The first time, Mimi asks whether AI and voice may be used: press **✅ Allow**.
- ☐ Send a **voice message** asking about the late policy: Mimi shows "🎤 I heard: …", answers in text,
  and replies with a voice message.
- ☐ `/lang am`, then ask in Amharic: the answer is in Amharic. `/lang om`: Afaan Oromo.
- ☐ `/human`, write a message: it appears in the tutor console; the tutor's reply arrives in Telegram. `/end` finishes.
- ☐ `/jobs` lists jobs; `/subscribe calendar` subscribes to alerts.

---

## 12. SMS and the low-bandwidth page (3 minutes)

- ☐ https://able-way.onrender.com/sms/simulator: send **HELP**, then **What is the late policy?**
  Every reply is **160 characters or less**.
- ☐ Send **LANG AM**, then an Amharic question: the reply is in Amharic.
- ☐ https://able-way.onrender.com/lite: a plain form with no JavaScript. Ask a question: the answer and
  its source appear.
- ☐ From a computer terminal (optional):
  ```
  curl -X POST https://able-way.onrender.com/sms/inbound -H "Content-Type: application/json" -d "{\"from\":\"0911000000\",\"text\":\"What is the late policy?\"}"
  ```
  The reply is plain text, at most 160 characters.

---

## 13. Jobs, accommodation and the teacher view (3 minutes)

- ☐ https://able-way.onrender.com/pages/jobs.html: jobs in English and Amharic, **Listen to summary** works.
- ☐ Open Mimi on the job board: she offers **"Ask for support in a job interview"** (also after any answer
  about a job). It opens the same private form, in the learner's language.
- ☐ **Request accommodation** opens the private form; send one (test data only).
- ☐ Signed in as the **coordinator**, **Accommodations** shows it; **Mark as handled** deletes it. A **tutor**
  cannot see it (not in the menu, and /accommodation/requests sends them back to the console).
- ☐ https://able-way.onrender.com/teacher: the most-asked questions and the **questions that got
  "I don't know"** (the gaps in the course). No names, no phone numbers.
- ☐ The tutor console **dashboard** shows questions, open tickets and statistics.

---

## 14. Works on any website (1 minute)

- ☐ https://able-way.onrender.com/demo/blank.html: Mimi on a plain page with no Savanna styles. She looks
  the same and works the same, and the events log on the page shows her events.

---

## 15. Privacy (2 minutes)

- ☐ In a new InPrivate window, before answering the first question: open the browser's developer tools
  (F12) → **Network**. Nothing is sent to `/api/ask` and nothing is spoken until you choose.
- ☐ In Telegram, `/forget`: everything kept about the chat is deleted.
- ☐ The teacher view and the logs never show a name, phone number or Telegram account.

---

## Before the pitch (on the day)

1. Open https://able-way.onrender.com/api/health 5 minutes before presenting, so the server is awake.
2. Demo on the **hosted link inside the Savanna page**, not localhost.
3. Show: the same question in English and in Amharic; one minute by keyboard only; "Talk to a person"
   with a teammate answering in the console; "No, text only" (works without AI).
4. Keep a **screen recording** of sections 1–5 as a backup in case the internet drops.

## If something fails

| Problem | Fix |
|---|---|
| The page takes a minute to load | The free server was asleep. Wait; it stays awake while in use. |
| "Talk to a person" says the help desk is not reachable | Render → Environment: `CHANNELS_URL` must be deleted; `PUBLIC_BASE_URL` must be `https://able-way.onrender.com`. Then Manual Deploy. |
| The help chat link opens `localhost` | `PUBLIC_BASE_URL` is wrong (see above). |
| Telegram does not answer | https://able-way.onrender.com/telegram/status must say `"running": true, "mode": "webhook"`. Check `TELEGRAM_BOT_TOKEN` (the live bot's token) and `TELEGRAM_MODE=webhook`; make sure your laptop is not running with the same token. |
| Answers say "Answered offline, without AI" when you allowed AI | The Gemini key is missing or its free daily quota is used up (Render → Logs shows `429`). It still answers from the course; the quota resets at midnight Pacific time. |
| Mimi is silent | Click once on the page (browsers block sound until then) and use Edge. |
