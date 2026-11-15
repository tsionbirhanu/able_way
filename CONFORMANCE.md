# WCAG 2.2 AA conformance report: Mimi (`<db-assistant>`)

**Scope.** The Track 3 module only: `module/db-assistant.js`, its stylesheet and language files, as it
runs on the three Savanna starter pages, `pages/jobs.html` and the plain page `demo/blank.html`. Also
the learner pages of the help desk (`/handoff/chat`) and the no-JavaScript `/lite` page. The Savanna
starter pages themselves are out of scope; their own defects are listed at the end because some
affect learners reaching Mimi.

**Version.** 15 November 2026. **Standard.** WCAG 2.2, levels A and AA.

**How it was checked** (details under "Who tested" at the end):

- axe-core 4.10.2, WCAG 2.0/2.1/2.2 A and AA rules, run by `tests/a11y/axe.mjs`: **0 critical, 0
  serious, 0 moderate, 0 minor** issues in Mimi on the Savanna lesson page and on the blank page,
  with the chat open, and **0 for the whole blank page**.
- Scripted keyboard runs in Microsoft Edge (Enter, Escape, Tab, number keys) with focus checked after
  each step.
- 320 px wide and the 200 % zoom equivalent (640 px), with and without the WCAG 1.4.12 text spacing.
- Not yet done: NVDA, TalkBack and the co-designer's own device. Statuses that depend on them say so.

| WCAG 2.2 criterion | Level | Status | Notes |
|---|---|---|---|
| 1.1.1 Non-text content | A | Supports | Every icon is decorative (`aria-hidden`) next to visible text, or its button has a name (close, send, minimise). |
| 1.2.1 Audio-only and video-only (prerecorded) | A | Supports | Everything Mimi says is also written in the chat and in the captions, before or while she says it. |
| 1.2.2 Captions (prerecorded) | A | Not applicable | No video. |
| 1.2.3 Audio description or media alternative | A | Not applicable | No video. |
| 1.2.4 Captions (live) | AA | Not applicable | No live media. Screen sharing goes from learner to tutor; the tutor answers in text. |
| 1.2.5 Audio description (prerecorded) | AA | Not applicable | No video. |
| 1.3.1 Info and relationships | A | Supports | Real headings, an ordered list of messages, a labelled message box, `role="group"` with names for button groups, an `<aside>` landmark. |
| 1.3.2 Meaningful sequence | A | Supports | Reading order follows the visual order: header, conversation, voice status, talk button, message box. |
| 1.3.3 Sensory characteristics | A | Supports | Instructions name the control in words ("Press to talk", "say 2 or press 2"), never by shape, colour or place alone. |
| 1.3.4 Orientation | AA | Supports | Works in portrait and landscape. |
| 1.3.5 Identify input purpose | AA | Not applicable | Mimi asks for no personal data. |
| 1.4.1 Use of colour | A | Supports | Every state is in words with an icon: "Listening…", "Mimi is speaking", "Sharing screen". |
| 1.4.2 Audio control | A | Supports | On a first visit Mimi says nothing until the learner answers the consent question. On a phone she never speaks before the learner's first tap, so she does not talk over TalkBack or VoiceOver. On a computer, on later visits, the greeting (about 5 seconds) plays only if the browser allows sound, with "Stop speaking" and "Turn off voice" on screen at once. A host can set `auto-welcome="false"`. **Still to confirm with an NVDA user** on a computer. |
| 1.4.3 Contrast (minimum) | AA | Supports | axe-core finds no contrast issue. Main text is 14:1 or more, buttons 7:1 or more. |
| 1.4.4 Resize text | AA | Supports | Works at 200 % zoom; Mimi starts as a small button there. Conversation text is 18 px and no text is under 15 px, even on hosts that shrink their base size (Savanna uses 14 px); every size still grows with the browser's text size. A text size choice (Normal, Large, Extra large) adds 25 % or 50 %, and Mimi stays fully on screen at each size. |
| 1.4.5 Images of text | AA | Supports | No images of text. |
| 1.4.10 Reflow | AA | Supports | At 320 px wide, no part of Mimi goes off screen and the blank page never scrolls sideways (button, card or chat). The Savanna starter page itself is wider than a phone (481 px on a 390 px screen; see the end): Mimi measures the visible area and stays inside it, so her card is fully on screen there too (tested at 390 px). |
| 1.4.11 Non-text contrast | AA | Supports | Control borders and the focus ring are navy (#0f2a47) on white, 14:1. |
| 1.4.12 Text spacing | AA | Supports | With line height 1.5, letter spacing 0.12 em, word spacing 0.16 em and paragraph spacing 2 em, no text is cut off or overlaps (tested at 320 px). |
| 1.4.13 Content on hover or focus | AA | Supports | No tooltips or hover-only content. |
| 2.1.1 Keyboard | A | Supports | Every action is a real button or link. Number keys also choose from the menu. |
| 2.1.2 No keyboard trap | A | Supports | The chat is not modal; Tab leaves it, Escape closes it and focus returns to the button that opens it. |
| 2.1.4 Character key shortcuts | A | Supports | Single-key shortcuts (0–6) only work while Mimi has focus, or before anything on the page has focus. Typing elsewhere on the page never triggers them. |
| 2.2.1 Timing adjustable | A | Supports | No time limits. After a long silence Mimi pauses listening and says so; "Resume listening" brings it back. |
| 2.2.2 Pause, stop, hide | A | Supports | The only movement is a pulse on the listening and speaking icons, off with "reduce motion"; listening can be paused. |
| 2.3.1 Three flashes or below | A | Supports | Nothing flashes. |
| 2.4.1 Bypass blocks | A | Supports | Mimi is one `<aside>` landmark, so a screen reader can jump to or past it. |
| 2.4.2 Page titled | A | Not applicable | The host page's title. |
| 2.4.3 Focus order | A | Supports | Logical order; focus moves to the message box when the chat opens and back to the button when it closes. |
| 2.4.4 Link purpose (in context) | A | Supports | Source links are named "Source 1: <section title>" and say when they open a new tab. |
| 2.4.5 Multiple ways | AA | Not applicable | A component, not a set of pages. |
| 2.4.6 Headings and labels | AA | Supports | Descriptive headings and button names in Amharic and English. |
| 2.4.7 Focus visible | AA | Supports | Two-tone ring (navy and yellow) on every control, visible on light and dark backgrounds; Windows high contrast uses the system colour. |
| 2.4.11 Focus not obscured (minimum) | AA | Supports | When keyboard focus moves to a page element that the open chat (or the card) completely covers, Mimi shrinks to her small "Open Mimi" button, without taking focus, and announces that she moved aside. She starts as that small button on narrow and zoomed screens. |
| 2.5.1 Pointer gestures | A | Supports | Single taps only. |
| 2.5.2 Pointer cancellation | A | Supports | Actions run on click (release). |
| 2.5.3 Label in name | A | Supports | Each button's name starts with its visible label; menu buttons include their number ("2 English"). |
| 2.5.4 Motion actuation | A | Not applicable | Nothing reacts to device motion. |
| 2.5.7 Dragging movements | AA | Supports | Nothing needs dragging. |
| 2.5.8 Target size (minimum) | AA | Supports | Targets are at least 44 px high, except the small source-number links inside text (inline, exempt). |
| 3.1.1 Language of page | A | Not applicable | The host page's language. |
| 3.1.2 Language of parts | AA | Supports | `lang="am"` or `lang="en"` on the widget and on every message, so screen readers switch voice. |
| 3.2.1 On focus | A | Supports | Focus never starts an action. |
| 3.2.2 On input | A | Supports | Changing language happens only by a button or by saying it, and Mimi confirms the change in words. |
| 3.2.3 Consistent navigation | AA | Supports | The same widget in the same place on every page. |
| 3.2.4 Consistent identification | AA | Supports | The same names and icons for the same actions everywhere. |
| 3.2.6 Consistent help | A | Supports | "Talk to a person" is in the same place in every view of the chat. |
| 3.3.1 Error identification | A | Supports | Errors are words in the chat and in a status line: microphone blocked, service unreachable, no voice for this language. |
| 3.3.2 Labels or instructions | A | Supports | The message box has a visible label ("Your message") tied to it with `for`, plus a hint inside it. |
| 3.3.3 Error suggestion | AA | Supports | Each error says what to do next (allow the microphone, type instead, try again). |
| 3.3.4 Error prevention (legal, financial, data) | AA | Not applicable | No such submissions in Mimi. |
| 3.3.7 Redundant entry | A | Supports | "Talk to a person" sends the conversation so far; the learner is not asked to repeat it. |
| 3.3.8 Accessible authentication (minimum) | AA | Not applicable | Learners do not sign in to Mimi. |
| 4.1.2 Name, role, value | A | Supports | Real buttons, `role="switch"` with `aria-checked`, `aria-pressed`, `aria-expanded`; axe-core finds no issue. |
| 4.1.3 Status messages | AA | Supports | New messages go to a hidden `role="log"` live region (announced once, without stealing focus); states and notices use `role="status"`. |

## Beyond WCAG

- **Dark mode.** Mimi follows the device's dark setting, with the same contrast rules (every text pair
  measured at 6.9:1 or more). Listening is shown in green with words and a ring; red is kept for errors.

- **Consent before anything leaves the site.** On the first visit Mimi asks, in Amharic and English,
  whether online AI and voice may be used. The question is the third Tab stop inside Mimi, has real
  buttons with visible names, and is announced once. "No, text only" keeps every question on the
  host (answers from the course text) and turns listening off; it can be changed in the chat
  settings. The same choice exists on Telegram (`/privacy`), SMS (`AI ON` / `AI OFF`) and `/lite`.

- **Every feature in both forms.** Voice and text everywhere, so a Deaf learner and a blind learner can
  both do everything: every spoken word is written, and every written reply has a "Replay" button.
- **Right-to-left.** Every message has `dir="auto"`; an Arabic question displays right-to-left.
- **Amharic.** Ethiopic fonts, a line height of 1.7 for Amharic, no capitals or letter spacing. Job
  deadlines are shown in the Ethiopian calendar in Amharic.
- **Screen sharing on Android.** Chrome on Android cannot share the screen; Mimi says so and shares the
  current page with the tutor instead.

## Defects in the Savanna starter that affect learners

Not fixed, because the guide says not to change the host's files. Listed so the platform can fix them:

- At 320 px wide the lesson page scrolls sideways even without Mimi.
- The menu button and the course switcher are `<div>` elements with click handlers: not reachable by
  keyboard and not announced by screen readers.
- No "skip to content" link; some images have a file name as their text alternative.
- The page loads about 1.5 MB of stylesheets: on Slow 3G Mimi appears after about 21 seconds on the
  lesson page, against about 7 seconds on the plain page, because the browser loads the host's styles first.

## Who tested, on what, and what they could not do

| Who | Device and assistive technology | Result |
|---|---|---|
| Team, automated | Windows 11, Microsoft Edge (headless): axe-core 4.10.2, scripted keyboard runs, 320 px and 640 px widths, text spacing, Slow 3G | As in the table above |
| Team, by hand | *To fill in: device, browser, keyboard only / screen reader* | *To fill in* |
| Co-designer | *To fill in: their own phone and screen reader (for example Android, TalkBack)* | *To fill in: what they completed alone, and what they could not do* |
| NVDA | *To fill in after testing* | *To fill in* |
