# Track 3 implementation and verification guide

This guide compares the project with the Track 3 brief shown in the supplied hackathon materials. The screenshot says the build should be a web and Telegram assistant with one-click escalation to a person. Required capabilities include an Amharic and English voice/text tutor grounded only in course content with citations, a web embed / Telegram bot / low-bandwidth text route, accessible chat announcements and right-to-left support, learner-controlled screen sharing, a pluggable AI layer, and a career gateway with job alerts, interview accommodation requests, and job questions. The brief also calls out simple mode and a teacher view of common questions without learner names.

The source project is under `able_way/`. This document distinguishes the brief's requirements from what code is present; it does not claim that an implemented demo route is a production integration.

## What is implemented

| Track 3 capability | Evidence in this project | Assessment |
|---|---|---|
| Web tutor | `module/db-assistant.js` and `/api/ask` in `server/app.py`; course pages load the widget | Implemented for the included pages. |
| Amharic and English text answers | `server/tutor.py`, Amharic glossary, bilingual FAQ and UI strings | Implemented; test Amharic accuracy and script rendering with fluent speakers. |
| Answers only from course material, with citations | `server/retrieval.py` searches extracted chunks; `tutor.py` passes sources to the model and validates citation numbers; widget makes citations links | Implemented as a retrieval-grounded flow. It is not a formal guarantee against every model hallucination. |
| Voice | Widget uses browser speech recognition and speech synthesis where available | Partial/browser-dependent. Amharic voices and recognition vary by device; voice output is not the same as a server voice tutor. |
| Simple mode | Widget sends `simple`; tutor prompt and offline FAQ shorten responses; `/lite` requests simple answers | Implemented. |
| Telegram bot | `server/channels/telegram_bot.py` uses Telegram long polling and shared channel core | Code implemented; requires a bot token and outbound network access. |
| Low-bandwidth route | `/lite` is a no-JavaScript form; `/sms` has an inbound webhook and browser simulator | Lite is a real text route. SMS is a webhook/simulator, not a connected carrier gateway. |
| New-message announcements | Web assistant transcript uses accessible live-region behavior; SMS/Telegram provide messages in their native interfaces | Present in the web widget; verify with screen readers and actual Telegram. |
| Right-to-left handling | UI uses language direction and `dir="auto"` in selected chat/form elements | Partial. Amharic is left-to-right; Arabic RTL is not an explicit Track 3 language requirement. Audit every mixed-script control before claiming full RTL support. |
| One-click human help | Handoff ticket/chat routes and widget handoff script; Telegram human-help flow | Implemented as a demo handoff path. A staffed support operation is not included. |
| Learner-controlled screen sharing | Handoff chat's Share my screen uses browser capture; tutor console displays view-only stream | Implemented on supported browsers over localhost/HTTPS; the learner initiates and can stop sharing. |
| Pluggable AI | Gemini, optional local Ollama, and offline FAQ/course quote provider share a provider interface | Implemented. Gemini is now first in the default chain; credentials are server-side. |
| Teacher view of frequent questions without names | `server/teacher/` question log and dashboard | Implemented; records question text, language, channel and date, not learner identity. Check data retention/privacy before deployment. |
| Job alerts by Telegram and SMS | `server/jobs/`, sample `data/jobs.json`, subscription/alert delivery | Implemented against invented sample jobs. SMS delivery is simulated until a gateway is connected. |
| Request interview accommodations | `server/channels/accommodation.py` stores requests | Implemented as a request capture flow; no employer/interview-system integration is present. |
| Answer questions about jobs | Jobs list, keyword matching and alert routes exist | Partial / gap: jobs are not included in the tutor retrieval index, so the grounded AI tutor does not yet answer arbitrary job questions from the listings. |

## Gemini setup

The key is read by the Python server. Do not put it in the browser widget or commit `server/.env`.

1. Create a Gemini API key in Google AI Studio. Free usage depends on the model, account, region and current quota; confirm the current limits in AI Studio.
2. From `able_way/`, copy `server/.env.example` to `server/.env` and replace the placeholder `GEMINI_API_KEY` value.
3. Keep `ABLEWAY_PROVIDERS=gemini,local,offline`. If Gemini is unavailable or out of quota, the tutor tries local Ollama if installed, then offline FAQ/course-text answers.
4. `ABLEWAY_GEMINI_MODEL` defaults to `gemini-3.5-flash-lite` (the largest free daily allowance). Change it only to a model available to your API key.
5. Start the web tutor with `python server/app.py`, then open `http://localhost:8000/`.
6. Check `http://localhost:8000/api/health`. Gemini should report `available: true` and the expected model. The key itself should never appear in the response or browser source.

Official Google references: [Gemini API key setup](https://ai.google.dev/gemini-api/docs/api-key) and [GenerateContent REST API](https://ai.google.dev/api/generate-content).

## Test the implementation

### Core web tutor

1. Open one of the learner pages through `http://localhost:8000/`, then open the tutor.
2. Ask a question whose answer is in the visible course content. Check that the answer is in the selected language and includes a numbered source link that opens the relevant course page.
3. Switch to Amharic and ask about a known course topic. Check Ge'ez rendering, language choice and linked citation with a fluent Amharic reviewer.
4. Enable Simple words and ask the same question. Check that the answer is shorter and uses everyday wording without losing the source.
5. Ask an unrelated question (for example, the capital of a country). The tutor should say it cannot find the answer in the course and offer human help; it should not invent a course citation.
6. Ask in Amharic about a topic covered only in English. Confirm whether the search retrieves the right English source; record misses as glossary/retrieval issues.
7. Use keyboard-only navigation and a screen reader. Verify focus order, accessible labels, new-answer announcement, citation links, and the button that starts human help. Test browser voice separately on supported browsers/devices.

### Telegram and low-bandwidth routes

1. For Telegram, configure `TELEGRAM_BOT_TOKEN`, start the FastAPI app with `uvicorn server.main:app --port 8001`, and check `http://localhost:8001/telegram/status`. Send a course question and verify a cited reply. Without a token, the web tutor still works, but the Telegram bot cannot be tested live.
2. Open `http://localhost:8001/lite?lang=am` to check the no-JavaScript low-bandwidth route.
3. Open `http://localhost:8001/sms/simulator` and try `HELP`, `LANG AM`, `JOBS`, and a course question. This verifies the simulator/webhook behavior only; connect and test a real SMS gateway separately.
4. Make sure questions sent through Telegram and lite use the same grounded tutor as the web page. SMS questions should also use the shared core; canned demo replies are no longer the default.

### Human help, screen sharing, jobs and teacher view

Use `DEMO.md` for the detailed scripted walkthrough. In brief: open the handoff console, create a learner ticket, start the learner's screen share from the learner chat, verify the tutor only sees the stream and cannot start it, then stop sharing. Screen capture requires a supported browser on localhost or HTTPS and an explicit learner action.

Check job routes and alert subscriptions using the sample records in `data/jobs.json`. Verify expired records are excluded, keyword subscriptions receive matching alerts, and unsubscribe works. These records are fabricated; replace them with approved live listings before presenting the gateway as real. Submit an accommodation request and confirm it appears in the request flow. Open the teacher view and verify aggregate question counts do not expose learner names.

The repo includes tests in `server/tests/` and `tests/`; run them from `able_way/` with `python -m pytest server/tests tests -q` after installing the project requirements. This guide describes test steps; it does not certify that the tests or external services have passed.

## Track 3 acceptance checklist

- [ ] Answer only from relevant course sources, cite each course answer, and hand off when no match exists.
- [ ] Amharic and English text work; simple mode gives short plain-language answers.
- [ ] Web, Telegram, and low-bandwidth text routes use the same tutor.
- [ ] Screen reader announces new messages; keyboard navigation and language/script direction are usable.
- [ ] Learner starts and stops screen sharing; tutor has view-only access.
- [ ] AI provider can be changed by configuration; Gemini key remains server-side; offline behavior remains available.
- [ ] Human help creates a usable ticket and reaches a staffed person in the judged deployment.
- [ ] Job alerts reach Telegram and real SMS channels; job questions cite current, unexpired listings.
- [ ] Accommodation requests are captured and routed to a responsible person.
- [ ] Teacher view shows common questions without names or unnecessary learner identifiers.
- [ ] Replace sample job data and simulator-only integrations with approved, deployable services before claiming production readiness.
