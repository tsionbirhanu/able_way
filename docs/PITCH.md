# Mimi: pitch deck

Digital Bridge Accessibility Hackathon 2026 · Track 3, Multilingual assistant and live help.
15 slides, about 6–7 minutes. Each slide has what goes **on the slide** and what to **say**.
Fill in everything in [square brackets] before presenting; nothing there is invented.

---

## Slide 1 · Cover

**On the slide**

- Eyebrow: Digital Bridge Accessibility Hackathon 2026 · Track 3
- Title: **Mimi**
- Subtitle: A course tutor in your language, on the app you already use, with a person one click away.
- ሰላም፣ እኔ ሚሚ ነኝ፣ የኮርስ አስጠኚዎ።
- [Team name] · [Team members] · with our co-designer [first name]

**Say**

Mimi is a tutor that speaks Amharic and English, answers only from the course, lives inside the
platforms learners already use, and hands over to a person in one click. Introduce the team and, with
their permission, our co-designer by name.

---

## Slide 2 · The problem

**On the slide**

Title: Learners get stuck in English, with no tutor in their language and no one to see their screen

| | |
|---|---|
| **15 million** | Ethiopians live with a disability: 17.6 per cent of the country |
| **27%** | of students with disabilities who reach university drop out before they finish |
| **“Help was in English only”** | On 21 October, more than 40 people tried to follow a lesson and get help. Most could not finish |

Sources: WHO and World Bank, World Report on Disability, 2011; university drop-out study, September
2024; Digital Bridge co-design session, 21 October 2026.

**Say**

The talent is there; the access is not. On 21 October, more than forty people tried to register, follow
a lesson, get help and apply for a job. Most could not finish, and one reason was simple: help was in
English only. That is the gap Track 3 asks us to close, and it is the gap Mimi closes.

---

## Slide 3 · Built with, not for

**On the slide**

> “I do not need a special app. I need the one everyone uses to work with my phone.”
> A participant at the co-design session, 21 October 2026

**The main task our co-designer tested:** “A blind learner on a low-cost Android phone asks in Amharic,
by voice, what the late policy of their course is, hears the answer with its source, and reaches a
tutor when the answer is not enough, with nobody helping.”

[Co-designer’s first name], [device and screen reader]: [result of the final test]

**Say**

This sentence drove every decision. Our co-designer [name] tested on their own phone with [TalkBack].
Say honestly what they finished alone and what we changed because of them: the listening that showed
“Listening” but did not listen, the greeting that mixed two languages, the settings that disappeared.
Each of those is fixed.

---

## Slide 4 · Meet Mimi

**On the slide**

Title: One tutor, everywhere the learner already is

| On the course page | On Telegram | By SMS | With a person |
|---|---|---|---|
| One script tag on Savanna or any site. Voice and text. | Type or send a voice message. Hear the answer back. | Any phone, no data. Plain answers in 160 characters. | One click to a tutor, who already sees the conversation. |

In Amharic and English. Answers only from the course, with the source every time.

**Say**

Mimi is not a new app. She is one module that plugs into the platform the learner already uses, plus
Telegram and SMS, which every learner already has. Same tutor, same answers, same sources, on every
channel, and a real person whenever the learner needs one.

---

## Slide 5 · Live demo: the main task in 60 seconds

**On the slide**

Title: A blind learner, by voice, in Amharic, with nobody helping

1. **Mimi asks first.** In Amharic and English: may she use online AI and voice? The learner taps
   “Allow and start”.
2. **She asks by voice:** “ዘግይቶ ማስገባት ይቻላል?” Her words appear as she speaks.
3. **Mimi answers aloud and in text,** in Amharic, and links the lesson section it came from.
4. **Not enough? “Talk to a person.”** A tutor sees the whole conversation and answers live.

**Say**

Show it live, ideally on the co-designer’s own phone over the HTTPS tunnel, with TalkBack on. Keep a
recorded video as backup. Point out: nothing is spoken before the consent tap; the live caption of her
words; the source link that highlights the lesson section; and the tutor console receiving the full
conversation.

---

## Slide 6 · Answers you can check

**On the slide**

Title: Mimi never invents an answer, and she shows where each one comes from

| 1. Find | 2. Check | 3. Answer and cite |
|---|---|---|
| The course is split by its own headings. Each question is matched to the right sections (retrieval, RAG). | Not in the course? Mimi says so and offers a person, and the AI is never even called. | The AI sees only those sections. Every answer links its source; one click lights it up on the page. |

- 30 / 30 on our evaluation set, offline
- 5 / 5 off-topic questions refused
- No medical, legal or immigration advice

**Say**

This answers the guide’s question: how do you show a judge an answer was not invented? Click the source
and the lesson section is outlined on the page. Then ask “Who won the World Cup?”: Mimi refuses and
offers a person. Our evaluation set has 30 questions in English and Amharic, including a misspelled one
and five off-topic ones; offline, Mimi cites the right section for all 25 course and job questions and
refuses all 5 off-topic ones. Anyone can rerun it with `python server/evaluate.py`.

---

## Slide 7 · Built for Ethiopia

**On the slide**

Title: Amharic is built in, not bolted on

| | |
|---|---|
| **Spelling-proof search** | Same-sound letters count as one (ሥራ = ስራ). A misheard vowel (ማሰረከቢያ) still finds the lesson. |
| **Natural, consistent speech** | One Amharic word per course term. “AI” is read ኤ አይ, “85%” 85 በመቶ. |
| **Ethiopian by default** | Job deadlines in the Ethiopian calendar (26 ኅዳር 2019). Any phone format stored as +251. |
| **Ready for more languages** | Every sentence is in one language file. Afaan Oromo, Tigrinya or Arabic is one new file. |

**Say**

Most assistants treat Amharic as English with a translator bolted on. We did not. Amharic letters are a
consonant plus a vowel, and several letters sound the same, so people and speech recognisers spell the
same word differently. Mimi treats those spellings as one word and can even match on consonants, so a
misheard vowel still finds the right lesson. Answers also follow the language of each question.
[Ask a native speaker on the team to confirm the Amharic on this slide.]

---

## Slide 8 · Accessible first

**On the slide**

Title: Every feature works by voice and by text

| Blind learners | Deaf learners | Low vision, keyboard |
|---|---|---|
| Talk and listen. New messages announced once. Silent until the first tap, so Mimi never talks over TalkBack. | Everything Mimi says is also written. Your own words appear as you speak. Text chat everywhere. | 18 px text, 44 px buttons, works at 200% zoom and 320 px. Keyboard only, no traps. |

axe-core: 0 issues · WCAG 2.2 AA report · Simple words mode · Right-to-left ready

**Say**

The guide warns: a voice tutor is useless to a Deaf learner, and a silent chat is useless to a blind
one. So every feature has both forms. For screen reader users, new messages are announced once without
stealing focus, and on a phone Mimi stays silent until the first tap. For low vision, conversation text
is 18 pixels even on hosts that shrink their text, and Mimi steps aside if she would hide what the
keyboard is focused on. axe-core finds zero issues on every page, and our conformance report covers
every WCAG 2.2 A and AA criterion.

---

## Slide 9 · The app everyone uses

**On the slide**

Title: Telegram, SMS and slow connections, not a special app

| Telegram | SMS | No signal |
|---|---|---|
| Typed or voice questions. Mimi shows what she heard, answers in text, and speaks it with “🔊 Listen”. | Plain answers in 160 characters, job alerts, AI ON / OFF. Real SMS through a phone gateway. | “Saved on this phone. It will send when you are online.” A no-JavaScript page for the oldest phones. |

**Say**

This is the 21 October quote made real: “I need the one everyone uses to work with my phone.” Telegram
is that app for many learners: Mimi answers voice messages there in Amharic and can reply by voice. SMS
reaches any phone with no data, and for development we connected free gateways, including an Android
phone with a local SIM. When the signal drops, the question is kept on the phone and sent when it comes
back.

---

## Slide 10 · Live help

**On the slide**

Title: A person, one click away, who already knows the question

| For the learner | For the tutor |
|---|---|
| Always in the same place. No repeating: the tutor sees the conversation. Screen sharing only if the learner starts it. | One console: who is waiting, live chat, the shared screen. On Android, the page the learner is on. |

**No one online at 23:00?** Mimi says so honestly: “A tutor will answer here. It may take until
morning.” The chat stays open, and the learner can keep asking Mimi meanwhile.

**Say**

One click opens a help chat in a new tab, and the tutor already sees the whole conversation, so the
learner never has to explain twice. The learner is in control of screen sharing. For the guide’s
question about 23:00: Mimi tells the learner the truth, keeps the chat open, and the webhook can alert
the platform’s staff that someone is waiting.

---

## Slide 11 · Career gateway

**On the slide**

Title: From the lesson to the job, in the same conversation

| Answers about jobs | Job alerts | Interview support |
|---|---|---|
| “What jobs are open?” or “ስራ እፈልጋለሁ”: answers from the job listings, with links. | Subscribe by Telegram or SMS with a keyword. Deadlines in the Ethiopian calendar. | Ask for an interpreter or extra time. A person handles it. Never shown to the employer. |

Every job is published as schema.org JobPosting, so any job board can read it.

**Say**

The career gateway reuses everything: the same tutor answers about jobs from a second content source,
the same Telegram and SMS channels carry job alerts, and an accommodation request goes privately to a
person, stored apart from everything else and deleted once it is handled. Employers never see a
disability; they see a support need arranged by staff.

---

## Slide 12 · It plugs in

**On the slide**

Title: Any platform adds Mimi in minutes, at all three levels

| Level 1 · One script tag | Level 2 · A REST API | Level 3 · Open standard |
|---|---|---|
| `<db-assistant lang="am">` Works on Savanna and on a blank page. Changes nothing on the host. | OpenAPI with live docs at `/docs`, a webhook, and a curl example for every call. | schema.org JobPosting on every job. LTI 1.3 path documented. |

`docker compose up` · 44 KB on first load · 7.4 s on Slow 3G

**Say**

The guide’s test is a judge installing the module in one hour from the README alone. Our README walks a
stranger from `git clone` to a running demo in one command, on Windows, macOS or Linux, with or without
Docker, and has a troubleshooting table. Mimi lives in a shadow root, so the host’s styles and hers
never touch. The whole module is 44 kilobytes compressed and appears in 7.4 seconds on Slow 3G on a
plain page.

---

## Slide 13 · Privacy and running costs

**On the slide**

Title: Nothing leaves the platform without the learner’s yes

| The learner decides | The platform can afford it |
|---|---|
| Asked once, before anything is sent | About $30–60 a month for 3,000 learners |
| “No” keeps every question on the host | Off-topic questions cost nothing |
| Download the chat, or delete it all | Works with no AI budget: offline mode |
| Telegram `/forget`, SMS `FORGET` | Any AI, voice or SMS service swaps out |

**Say**

The guide says nothing may leave the host for a third party unless the host configured it and the
learner agreed. Mimi asks first, in Amharic and English, and “No, text only” keeps every question on the
platform’s own server. The same choice exists on Telegram, SMS and the low-bandwidth page, and the
learner can export or delete their data on every channel. On cost: off-topic questions never reach the
AI, repeated questions come from a cache, and with no budget at all Mimi still answers from the course
text. No feature is locked to a paid service.

---

## Slide 14 · Measured, not claimed

**On the slide**

| | |
|---|---|
| **30/30** | Evaluation questions answered from the right section, or refused, offline |
| **0** | axe-core issues on every page, chat open or closed |
| **96** | Automated tests, from Amharic spelling to consent |
| **44 KB** | Module size on first load (7.4 s on Slow 3G) |
| **160** | Characters at most in every SMS answer |
| **[✓]** | [Co-designer’s final test: completed unaided with TalkBack] |

**Say**

Every number here can be rerun by a judge: `python server/evaluate.py` for the 30 questions,
`python -m pytest server/tests tests` for the 96 tests, and `tests/a11y/axe.mjs` for axe-core. The
last line is the one that matters most: fill it in with the co-designer’s real result at the gate,
honestly, including anything they could not do.

---

## Slide 15 · Close

**On the slide**

- Eyebrow: Not a special app. The one everyone uses.
- **Mimi gives every learner a tutor in their language, and a person when it matters.**
- በቋንቋዎ፣ በስልክዎ፣ ከሰው እርዳታ ጋር።
- Ready for Savanna today, and for the eight job platforms and two training institutions next.
- [Team name] · github.com/tsionbirhanu/able_way

**Say**

Close on the promise and the ask. Mimi is ready to go live on Savanna, and because it is one script tag
plus an open API, the same module serves the eight job-matching platforms and the two regional training
institutions next. Thank the co-designer by name, and invite the panel to try it on their own phone.

---

## Presenting tips

1. Do slide 5 **live, on the co-designer’s own phone** with TalkBack. Keep a recorded video as backup.
2. On slide 6, click a source, then ask “Who won the World Cup?”: the strongest proof that answers are
   not invented.
3. Let the co-designer say one sentence themselves. Co-designers on the panel score that.
4. Keep to 6–7 minutes. Rehearse once with a timer.

**Design, if you build the slides in PowerPoint, Google Slides or Canva:** navy `#10233F` and paper
`#F7F5EF` backgrounds, one green accent `#0A7A4A` (on dark slides `#3EE08F`), headings in Space
Grotesk, text in Inter, Amharic in Noto Sans Ethiopic. One idea per slide, text at least 24 pt.
