// Mimi: the Ableway course tutor. A bilingual (Amharic / English), voice-first classroom tutor
// with a text chat that always works.
//
// Add it to any page with one tag:
//
//   <script src="../assistant/assistant.js" defer></script>
//
// Optional attributes:
//   data-api="https://host:port"     tutor API (server/app.py) when it is not on http://localhost:8000
//   data-lang="am"                   language of the spoken greeting (default am)
//   data-auto-welcome="false"        do not greet by voice when the page opens
//   data-course / data-lesson        the course and lesson this page shows
//   data-lesson-selector="css"       read the lesson name from the page each time (e.g. the active week)
//   data-tts="auto|server|browser"   Mimi's voice: the server voice (speech.py), else the browser's
//   data-stt="auto|browser|server"   who hears the learner: the browser's recogniser where it knows the
//                                    language, else a recording transcribed on the server
//
// The conversation is a small state machine (see ALLOWED below):
//
//   initializing -> greeting -> language_selection -> speaking -> listening -> processing -> speaking ...
//
// with text_mode (voice off, or no microphone), paused (panel closed, quiet for a minute, learner
// typing, tab hidden) and error. Mimi never listens while she speaks: the recogniser is stopped on
// every transition out of listening, and started again only once her speech has ended.
//
// Unlike assets/js/static-page.js, which deliberately keeps the application's accessibility
// defects, this widget is new work and is built to be accessible on its own: it lives in a shadow
// root so the page's styles cannot break it, every control is a real button with a name, new
// messages are announced through a live region, and each message sets its own language.

(() => {
  'use strict';

  const script = document.currentScript;
  const siteRoot = new URL('..', script.src); // citations are paths from the site root
  const API = (
    script.dataset.api ||
    (location.protocol.startsWith('http') && location.port === '8000' ? location.origin : 'http://localhost:8000')
  ).replace(/\/$/, '');
  const config = {
    greetLang: script.dataset.lang === 'en' ? 'en' : 'am',
    autoWelcome: script.dataset.autoWelcome !== 'false',
    course: script.dataset.course || '',
    lesson: script.dataset.lesson || '',
    lessonSelector: script.dataset.lessonSelector || '',
    tts: ['server', 'browser'].includes(script.dataset.tts) ? script.dataset.tts : 'auto',
    stt: ['server', 'browser'].includes(script.dataset.stt) ? script.dataset.stt : 'auto',
  };
  const PAGE = location.href.startsWith(siteRoot.href) ? location.href.slice(siteRoot.href.length).split(/[?#]/)[0] : '';

  const END_OF_TURN_MS = { en: 1500, am: 1900 }; // silence that ends the learner's turn; shorter pauses are kept
  const MAX_QUIET_RESTARTS = 8; // recogniser restarts without hearing anything before listening pauses (~1 min)
  const QUIET_LIMIT_MS = 60000;
  const ECHO_GAP_MS = 300; // after Mimi stops talking, before the microphone opens
  const SPEECH_LANG = { en: 'en-US', am: 'am-ET' };

  // ------------------------------------------------------------ text in both languages

  const GREETING = {
    am: 'ሰላም! ወደ ትምህርት ክፍልህ እንኳን በደህና መጣህ። ዛሬ ትምህርቱን በአማርኛ ወይስ በእንግሊዝኛ መማር ትፈልጋለህ?',
    en: 'Hello! Welcome to your classroom. Would you like to learn in Amharic or English today?',
  };

  const STRINGS = {
    en: {
      langName: 'English',
      launcher: 'Talk to Mimi',
      title: 'Mimi, your course tutor',
      subtitle: 'Your bilingual course tutor. Answers come from your course pages.',
      close: 'Close Mimi',
      language: 'Change language',
      currentLang: 'Current language',
      simple: 'Simple words',
      clear: 'Clear chat',
      talkToPerson: 'Talk to a person',
      screenShare: 'Share screen',
      screenSharingActive: 'Sharing screen (click to stop)',
      escalating: 'Connecting to live tutor…',
      screenShareAndroid: 'Screen sharing is not supported in Chrome on Android. Your current lesson page is shared with the tutor.',
      transcript: 'Conversation with Mimi',
      inputLabel: 'Your message',
      placeholder: 'Type your message…',
      send: 'Send',
      voiceOff: 'Turn off voice',
      voiceOn: 'Turn on voice',
      thinking: 'Mimi is writing an answer…',
      you: 'You',
      tutor: 'Mimi',
      sources: 'Sources',
      source: 'Source',
      sourceCount: (n) => (n === 1 ? '1 source is listed below.' : `${n} sources are listed below.`),
      newTab: 'opens in a new tab',
      replay: 'Replay',
      replayLabel: 'Replay this message',
      stopReplay: 'Stop',
      offline: 'Answered offline, without AI.',
      local: 'Answered by the local model on this computer.',
      error: 'I could not reach the tutor service. Check that it is running, then try again.',
      retry: 'Try again',
      cleared: 'Chat cleared.',
      chooseLabel: 'Choose a language',
      confirm: "Great! I'll assist you in English from now on. Let's start learning!",
      chooseRetry: 'Sorry, I didn\'t catch that. Say "Amharic" or "English", or press one of the buttons.',
      langInferred: 'I will reply in English. You can change this at any time.',
      introChip: 'Introduce this lesson',
      sInit: 'Getting ready…',
      sSpeaking: 'Mimi is speaking',
      sChoose: 'Listening: say "Amharic" or "English", or choose below',
      sChooseNoMic: 'Choose a language below',
      sListening: 'Listening… speak when you are ready',
      sProcessing: 'Thinking…',
      sText: 'Voice is off: type your message',
      sTextNoMic: 'The microphone is not available: type your reply',
      sPaused: 'Listening is paused',
      sTyping: 'Listening is paused while you type',
      sError: 'Something went wrong',
      aSkip: 'Stop speaking',
      aPause: 'Pause listening',
      aResume: 'Resume listening',
      aUnlock: 'Start talking with Mimi',
      voiceTurnedOff: 'Voice is off. Keep typing: your conversation and language are kept.',
      voiceTurnedOn: 'Voice is on.',
      quiet: 'It has been quiet for a while, so I paused listening. Press Resume listening when you are ready.',
      micDenied: "The microphone is blocked, so I can't hear you. Allow it in your browser settings, or type your reply.",
      micNone: 'No microphone was found. Please type your reply.',
      micLang: 'This browser cannot recognise speech in this language. Please type your reply.',
      micNetwork: 'Speech recognition is not reachable right now. Please type your reply.',
      noVoice: (lang) => `No ${lang === 'am' ? 'Amharic' : 'English'} voice is available on this device right now, so please read my reply on screen.`,
      speechBlocked: 'Your browser needs a click or a key press before Mimi can speak.',
      speechUnavailable: 'Speech output is not available in this browser. You can still read and type here.',
      welcome:
        "Hi, I'm Mimi, your course tutor. Talk to me or type: I can explain this lesson, answer questions about your course, and quiz you. I answer from your course pages and show you the sources.",
      suggestions: [
        'What is the late policy for WR 100?',
        'Is the future of VA work promising?',
        'Give me a practice question on this lesson.',
      ],
    },
    am: {
      langName: 'አማርኛ',
      launcher: 'ከሚሚ ጋር ይነጋገሩ',
      title: 'ሚሚ፣ የኮርስ አስጠኚዎ',
      subtitle: 'በሁለት ቋንቋ የምታግዝ የኮርስ አስጠኚ። መልሶቼ ከኮርስ ገጾችዎ ይመጣሉ።',
      close: 'ሚሚን ዝጋ',
      language: 'ቋንቋ ቀይር',
      currentLang: 'የአሁኑ ቋንቋ',
      simple: 'ቀላል ቃላት',
      clear: 'ውይይቱን አጽዳ',
      talkToPerson: 'ረዳት ሰው ያነጋግሩ',
      screenShare: 'ማያ ገጽ አጋራ',
      screenSharingActive: 'ማያ ገጽ እየተጋራ ነው (ለማቆም ይጫኑ)',
      escalating: 'ከሰው ረዳት ጋር በመገናኘት ላይ…',
      screenShareAndroid: 'በAndroid Chrome ላይ ማያ ገጽ ማጋራት አይሰራም። የያዙት የትምህርት ገጽ ለአስተማሪው ተልኳል።',
      transcript: 'ከሚሚ ጋር ያለ ውይይት',
      inputLabel: 'መልእክትዎ',
      placeholder: 'መልእክትዎን ይጻፉ…',
      send: 'ላክ',
      voiceOff: 'ድምፅን አጥፋ',
      voiceOn: 'ድምፅን አብራ',
      thinking: 'ሚሚ መልስ እየጻፈች ነው…',
      you: 'እርስዎ',
      tutor: 'ሚሚ',
      sources: 'ምንጮች',
      source: 'ምንጭ',
      sourceCount: (n) => `${n} ምንጭ ከታች ተዘርዝሯል።`,
      newTab: 'በአዲስ ትር ይከፈታል',
      replay: 'እንደገና አጫውት',
      replayLabel: 'ይህን መልእክት እንደገና አጫውት',
      stopReplay: 'አቁም',
      offline: 'ያለ AI፣ ያለ ኢንተርኔት የተመለሰ።',
      local: 'በዚህ ኮምፒውተር ላይ ባለው ሞዴል የተመለሰ።',
      error: 'ከረዳት አስተማሪው አገልግሎት ጋር መገናኘት አልተቻለም። አገልግሎቱ መሥራቱን አረጋግጠው እንደገና ይሞክሩ።',
      retry: 'እንደገና ሞክር',
      cleared: 'ውይይቱ ጸድቷል።',
      chooseLabel: 'ቋንቋ ይምረጡ',
      confirm: 'ጥሩ! ከአሁን በኋላ በአማርኛ አግዝሃለሁ። ትምህርቱን እንጀምር!',
      chooseRetry: 'ይቅርታ፣ በደንብ አልሰማሁም። “አማርኛ” ወይም “English” ይበሉ፣ ወይም ከቁልፎቹ አንዱን ይጫኑ።',
      langInferred: 'በአማርኛ እመልሳለሁ። በማንኛውም ጊዜ መቀየር ይችላሉ።',
      introChip: 'ይህን ትምህርት አስተዋውቂኝ',
      sInit: 'በመዘጋጀት ላይ…',
      sSpeaking: 'ሚሚ እየተናገረች ነው',
      sChoose: 'እያዳመጥኩ ነው፦ “አማርኛ” ወይም “English” ይበሉ፣ ወይም ከታች ይምረጡ',
      sChooseNoMic: 'ከታች ቋንቋ ይምረጡ',
      sListening: 'እያዳመጥኩ ነው… ሲዘጋጁ ይናገሩ',
      sProcessing: 'እያሰብኩ ነው…',
      sText: 'ድምፅ ጠፍቷል፦ መልእክትዎን ይጻፉ',
      sTextNoMic: 'ማይክሮፎኑ አይገኝም፦ መልስዎን ይጻፉ',
      sPaused: 'ማዳመጥ ቆሟል',
      sTyping: 'እየጻፉ ስለሆነ ማዳመጥ ቆሟል',
      sError: 'ችግር ተፈጥሯል',
      aSkip: 'ንግግሩን አቁም',
      aPause: 'ማዳመጥ አቁም',
      aResume: 'ማዳመጥ ቀጥል',
      aUnlock: 'ከሚሚ ጋር ማውራት ጀምር',
      voiceTurnedOff: 'ድምፅ ጠፍቷል። መጻፍ ይቀጥሉ፤ ውይይቱና ቋንቋው አይጠፉም።',
      voiceTurnedOn: 'ድምፅ በርቷል።',
      quiet: 'ለተወሰነ ጊዜ ፀጥታ ስለነበር ማዳመጥ አቁሜያለሁ። ሲዘጋጁ “ማዳመጥ ቀጥል” ይጫኑ።',
      micDenied: 'ማይክሮፎኑ ስለተከለከለ ልሰማዎት አልችልም። በብራውዘርዎ ቅንብር ይፍቀዱት፣ ወይም መልስዎን ይጻፉ።',
      micNone: 'ማይክሮፎን አልተገኘም። እባክዎ መልስዎን ይጻፉ።',
      micLang: 'ይህ ብራውዘር በዚህ ቋንቋ ንግግርን መለየት አይችልም። እባክዎ መልስዎን ይጻፉ።',
      micNetwork: 'የንግግር መለያው አሁን አይገኝም። እባክዎ መልስዎን ይጻፉ።',
      noVoice: (lang) => `በዚህ መሣሪያ ላይ አሁን የ${lang === 'am' ? 'አማርኛ' : 'እንግሊዝኛ'} ድምፅ ስለሌለ እባክዎ መልሴን በገጹ ላይ ያንብቡ።`,
      speechBlocked: 'ሚሚ እንድትናገር ብራውዘሩ መጀመሪያ አንድ ጠቅታ ወይም ቁልፍ መጫን ይፈልጋል።',
      speechUnavailable: 'በዚህ ብራውዘር የድምፅ ውጤት አይገኝም። እዚህ ማንበብና መጻፍ ይችላሉ።',
      welcome:
        'ሰላም፣ እኔ ሚሚ የኮርስ አስጠኚዎ ነኝ። ይናገሩኝ ወይም ይጻፉልኝ፦ ይህን ትምህርት ማብራራት፣ ስለ ኮርስዎ ጥያቄዎችን መመለስና በጥያቄ መለማመድ እችላለሁ። መልሶቼን ከኮርስ ገጾችዎ እወስዳለሁ፣ ምንጮቹንም አሳያለሁ።',
      suggestions: [
        'የWR 100 የመዘግየት ፖሊሲ ምንድን ነው?',
        'የምናባዊ ረዳት ሥራ የወደፊት ተስፋ አለው?',
        'ስለዚህ ትምህርት የመለማመጃ ጥያቄ ጠይቂኝ።',
      ],
    },
  };

  const ICONS = {
    chat: '<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z"/>',
    close: '<path d="M6 6l12 12M18 6L6 18"/>',
    send: '<path d="M4 12l16-8-6 16-3-7-7-1z"/>',
    mic: '<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/>',
    micOff: '<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3M3 3l18 18"/>',
    speaker: '<path d="M4 9v6h4l5 4V5L8 9H4z"/><path d="M16.5 8.5a5 5 0 0 1 0 7"/>',
    stop: '<rect x="6" y="6" width="12" height="12" rx="2"/>',
    dots: '<circle cx="6" cy="12" r="1.5"/><circle cx="12" cy="12" r="1.5"/><circle cx="18" cy="12" r="1.5"/>',
    keyboard: '<rect x="3" y="6" width="18" height="12" rx="2"/><path d="M7 10h.01M11 10h.01M15 10h.01M7 14h10"/>',
    pause: '<path d="M9 6v12M15 6v12"/>',
    alert: '<path d="M12 4l9 16H3z"/><path d="M12 10v4M12 17h.01"/>',
    person: '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
    share: '<rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>',
  };

  // ------------------------------------------------------------ small helpers

  function el(tag, props = {}, ...children) {
    const node = document.createElement(tag);
    for (const [key, value] of Object.entries(props)) {
      if (value === false || value == null) continue;
      if (key === 'class') node.className = value;
      else if (key === 'text') node.textContent = value;
      else if (key.startsWith('on')) node.addEventListener(key.slice(2), value);
      else node.setAttribute(key, value === true ? '' : value);
    }
    node.append(...children.filter((c) => c != null && c !== false));
    return node;
  }

  function icon(name) {
    const span = document.createElement('span');
    // Static markup from the ICONS table above, never user or server text.
    span.innerHTML = `<svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">${ICONS[name]}</svg>`;
    return span.firstChild;
  }

  function store(area, key, value) {
    try {
      if (value === undefined) return JSON.parse(area.getItem(key));
      area.setItem(key, JSON.stringify(value));
    } catch {
      /* private window or blocked storage: the widget works, it just forgets on reload */
    }
    return null;
  }
  const session = {
    get: (key) => store(sessionStorage, `ableway-${key}`),
    set: (key, value) => store(sessionStorage, `ableway-${key}`, value),
  };

  const scriptLang = (text) => (/[ሀ-፿]/.test(text) ? 'am' : 'en');

  // Mirrors language_choice() in server/tutor.py; used while the server may not be reachable yet.
  const LANGUAGE_NAMES = {
    am: ['amharic', 'amarigna', 'amharigna', 'amarinya', 'ማርኛ', 'ማረኛ'],
    en: ['english', 'inglish', 'እንግሊ', 'ኢንግሊ'],
  };
  function languageChoice(text) {
    const lower = text.toLowerCase();
    const named = Object.keys(LANGUAGE_NAMES).filter((code) => LANGUAGE_NAMES[code].some((s) => lower.includes(s)));
    return named.length === 1 ? named[0] : null;
  }

  async function request(path, options = {}, timeoutMs = 30000) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
      return await fetch(`${API}${path}`, { ...options, signal: controller.signal });
    } finally {
      clearTimeout(timer);
    }
  }
  async function postJSON(path, body, timeoutMs) {
    const response = await request(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }, timeoutMs);
    const data = await response.json();
    if (!response.ok) throw Object.assign(new Error(data.error || response.statusText), { status: response.status });
    return data;
  }

  // ------------------------------------------------------------ state

  const state = {
    lang: session.get('lang') === 'en' || session.get('lang') === 'am' ? session.get('lang') : config.greetLang,
    langChosen: session.get('lang-chosen') === true,
    greeted: session.get('greeted') === true,
    voiceOn: session.get('voice') == null ? config.autoWelcome : session.get('voice') === true,
    sessionId: session.get('session-id'),
    simple: store(localStorage, 'ableway-simple') === true,
    open: config.autoWelcome || session.get('open') !== false,
    messages: session.get('messages') || [], // {role, text, lang, citations, provider, error, kind, translation}
    busy: false,
  };
  const t = () => STRINGS[state.lang];
  const caps = { server: false, tts: false, ttsCache: false, stt: false };

  // ------------------------------------------------------------ build the widget

  const host = el('div', { id: 'ableway-assistant' });
  const shadow = host.attachShadow({ mode: 'open' });
  const css = el('link', { rel: 'stylesheet', href: new URL('assistant.css', script.src).href });

  const launcher = el('button', { type: 'button', class: 'launcher', 'aria-expanded': 'false', onclick: () => setOpen(true) });
  const launcherText = el('span');
  launcher.append(icon('chat'), launcherText);

  const title = el('h2', { class: 'title', id: 'ableway-title' });
  const subtitle = el('p', { class: 'subtitle' });
  const langBadge = el('span', { class: 'lang-badge' });
  const voiceToggleIcon = el('span', { class: 'toggle-icon' });
  const voiceToggleText = el('span');
  const voiceToggle = el('button', { type: 'button', class: 'voice-toggle', onclick: () => setVoice(!state.voiceOn) }, voiceToggleIcon, voiceToggleText);
  const closeButton = el('button', { type: 'button', class: 'icon-button', onclick: () => setOpen(false) }, icon('close'));

  const langButtons = {
    en: el('button', { type: 'button', lang: 'en', text: 'English', onclick: () => chooseLanguage('en') }),
    am: el('button', { type: 'button', lang: 'am', text: 'አማርኛ', onclick: () => chooseLanguage('am') }),
  };
  const langGroup = el('div', { class: 'segmented', role: 'group' }, langButtons.en, langButtons.am);
  const simpleText = el('span');
  const simpleSwitch = el(
    'button',
    { type: 'button', class: 'switch', role: 'switch', onclick: () => setSimple(!state.simple) },
    el('span', { class: 'track', 'aria-hidden': 'true' }),
    simpleText,
  );
  const clearButton = el('button', { type: 'button', class: 'link-button', onclick: clearChat });

  let screenStream = null;
  const talkText = el('span');
  const talkButton = el('button', { type: 'button', class: 'btn-help', onclick: escalateToHuman }, icon('person'), talkText);
  const shareText = el('span');
  const shareButton = el('button', { type: 'button', class: 'btn-help', onclick: toggleScreenShare }, icon('share'), shareText);
  const helpStrip = el('div', { class: 'help-strip' }, talkButton, shareButton);

  const list = el('ol', { class: 'messages' });
  const suggestions = el('div', { class: 'suggestions' });
  const scroller = el('div', { class: 'scroller', tabindex: '0', role: 'group' }, list, suggestions);

  // Screen readers hear new messages from this hidden log, where we control the wording
  // (no citation markers, no button labels). The visible transcript is not itself live.
  const announcer = el('div', { class: 'sr-only', role: 'log', 'aria-live': 'polite', 'aria-relevant': 'additions' });

  // What Mimi is doing now, in words and an icon (never colour alone), plus the one action that fits.
  const voiceIcon = el('span', { class: 'voice-icon', 'aria-hidden': 'true' });
  const voiceState = el('span', { class: 'voice-state' });
  const voiceStatus = el('div', { class: 'voice-status', role: 'status' }, voiceIcon, voiceState);
  const voiceActionText = el('span');
  const voiceAction = el('button', { type: 'button', class: 'voice-action', onclick: onVoiceAction, hidden: true }, voiceActionText);
  const voiceBar = el('div', { class: 'voicebar' }, voiceStatus, voiceAction);
  // Longer notices: microphone blocked, no Amharic voice, and so on. Visible, and announced.
  const status = el('div', { class: 'status', role: 'status' });

  const inputLabel = el('label', { class: 'sr-only', for: 'ableway-input' });
  const input = el('textarea', { id: 'ableway-input', rows: '1', dir: 'auto', autocomplete: 'off', enterkeyhint: 'send' });
  const sendButton = el('button', { type: 'submit', class: 'icon-button send' }, icon('send'));
  const form = el('form', { class: 'composer', onsubmit: onSubmit }, inputLabel, input, sendButton);

  const panel = el(
    'section',
    { class: 'panel', role: 'dialog', 'aria-modal': 'false', 'aria-labelledby': 'ableway-title', hidden: true },
    el('div', { class: 'header' }, el('div', { class: 'header-text' }, title, subtitle, langBadge), voiceToggle, closeButton),
    el('div', { class: 'settings' }, langGroup, simpleSwitch, clearButton),
    helpStrip,
    scroller,
    announcer,
    voiceBar,
    status,
    form,
  );

  // <aside> gives screen-reader users a landmark to jump to from anywhere on the page.
  const root = el('aside', { class: 'root', hidden: true }, launcher, panel);
  shadow.append(css, root);

  // ------------------------------------------------------------ rendering

  function applyLanguage() {
    const s = t();
    root.lang = state.lang;
    root.setAttribute('aria-label', s.title);
    launcherText.textContent = s.launcher;
    title.textContent = s.title;
    subtitle.textContent = s.subtitle;
    langBadge.textContent = `${s.currentLang}: ${s.langName}`;
    closeButton.setAttribute('aria-label', s.close);
    langGroup.setAttribute('aria-label', s.language);
    for (const [code, button] of Object.entries(langButtons)) button.setAttribute('aria-pressed', String(state.langChosen && code === state.lang));
    simpleText.textContent = s.simple;
    simpleSwitch.setAttribute('aria-checked', String(state.simple));
    clearButton.textContent = s.clear;
    talkText.textContent = s.talkToPerson;
    talkButton.setAttribute('aria-label', s.talkToPerson);
    shareText.textContent = screenStream ? s.screenSharingActive : s.screenShare;
    shareButton.setAttribute('aria-label', screenStream ? s.screenSharingActive : s.screenShare);
    scroller.setAttribute('aria-label', s.transcript);
    inputLabel.textContent = s.inputLabel;
    input.placeholder = s.placeholder;
    sendButton.setAttribute('aria-label', s.send);
    renderVoiceToggle();
    renderVoiceBar();
    renderMessages();
  }

  function renderVoiceToggle() {
    voiceToggleText.textContent = state.voiceOn ? t().voiceOff : t().voiceOn;
    voiceToggleIcon.replaceChildren(icon(state.voiceOn ? 'mic' : 'micOff'));
    voiceToggle.dataset.on = String(state.voiceOn);
  }

  function renderMessages() {
    const items = state.messages.length
      ? state.messages
      : [{ role: 'assistant', text: t().welcome, lang: state.lang, citations: [], kind: 'welcome' }];
    list.replaceChildren(...items.map(renderMessage));
    renderSuggestions();
    scrollToEnd();
  }

  function lessonKey() {
    const c = pageContext();
    return `${PAGE}|${c.lesson}`;
  }

  function renderSuggestions() {
    const chips = [];
    if (state.langChosen && !state.messages.some((m) => m.kind === 'intro' && m.lessonKey === lessonKey())) {
      chips.push(el('button', { type: 'button', class: 'chip', lang: state.lang, text: t().introChip, onclick: () => askTutor('', { intent: 'lesson_intro' }) }));
    }
    if (!state.messages.some((m) => m.role === 'user')) {
      chips.push(...t().suggestions.map((q) => el('button', { type: 'button', class: 'chip', lang: state.lang, text: q, onclick: () => takeTurn(q, 'text') })));
    }
    suggestions.replaceChildren(...chips);
  }

  function renderMessage(message) {
    const s = t();
    const isUser = message.role === 'user';
    const bubble = el('div', { class: 'bubble' });
    for (const paragraph of message.text.split(/\n{2,}/)) {
      if (paragraph.trim()) bubble.append(renderParagraph(paragraph.trim(), message.citations || []));
    }
    if (message.translation) bubble.append(el('p', { class: 'translation', lang: 'en', dir: 'ltr', text: message.translation }));
    const item = el(
      'li',
      { class: `msg ${isUser ? 'msg-user' : 'msg-bot'}${message.error ? ' msg-error' : ''}`, lang: message.lang },
      el('span', { class: 'who', lang: state.lang, text: isUser ? s.you : s.tutor }),
      bubble,
    );
    if (message.kind === 'greeting' && !state.langChosen) {
      item.append(
        el(
          'div',
          { class: 'choices', role: 'group', 'aria-label': `${STRINGS.am.chooseLabel} / ${STRINGS.en.chooseLabel}` },
          el('button', { type: 'button', class: 'choice', lang: 'am', text: 'አማርኛ', onclick: () => chooseLanguage('am') }),
          el('button', { type: 'button', class: 'choice', lang: 'en', text: 'English', onclick: () => chooseLanguage('en') }),
        ),
      );
    }
    if (message.citations && message.citations.length) {
      const sources = el('ol');
      for (const c of message.citations) sources.append(el('li', {}, sourceLink(c, c.title)));
      item.append(el('div', { class: 'sources', lang: 'en' }, el('p', { class: 'sources-title', lang: state.lang, text: s.sources }), sources));
    }
    if ((message.provider === 'offline' || message.provider === 'local') && message.citations && message.citations.length) {
      item.append(el('p', { class: 'note', lang: state.lang, text: s[message.provider] }));
    }
    const actions = el('div', { class: 'actions' });
    if (message.error) actions.append(el('button', { type: 'button', class: 'chip', lang: state.lang, text: s.retry, onclick: retry }));
    if (!isUser && !message.error && canSpeak()) {
      const button = el('button', { type: 'button', class: 'chip replay', lang: state.lang, 'aria-pressed': 'false', 'aria-label': s.replayLabel }, icon('speaker'), el('span', { text: s.replay }));
      button.addEventListener('click', () => replay(message, button));
      actions.append(button);
    }
    if (actions.children.length) item.append(actions);
    return item;
  }

  // Text is always inserted with textContent, so nothing a model or a learner writes is
  // ever interpreted as HTML. "[2]" becomes a link to source 2.
  function renderParagraph(text, citations) {
    const p = el('p', { dir: 'auto' });
    for (const part of text.split(/(\[\d+\])/)) {
      const match = /^\[(\d+)\]$/.exec(part);
      const citation = match && citations.find((c) => c.n === Number(match[1]));
      if (citation) p.append(sourceLink(citation, part, true));
      else if (part) p.append(part);
    }
    return p;
  }

  function sourceLink(citation, text, isMarker = false) {
    const url = new URL(citation.url, siteRoot);
    const samePage = url.pathname === location.pathname;
    const link = el('a', { href: samePage ? url.hash || '#' : url.href, text, lang: isMarker ? null : 'en' });
    if (isMarker) {
      link.className = 'cite';
      link.setAttribute('aria-label', `${t().source} ${citation.n}: ${citation.title}`);
    }
    if (!samePage) {
      link.target = '_blank';
      link.rel = 'noopener';
      if (!isMarker) link.append(el('span', { class: 'sr-only', lang: state.lang, text: ` (${t().newTab})` }));
    }
    return link;
  }

  function scrollToEnd() {
    scroller.scrollTop = scroller.scrollHeight;
  }

  function announce(message) {
    const s = STRINGS[state.lang];
    const who = message.role === 'user' ? s.you : s.tutor;
    const count = message.citations && message.citations.length ? ` ${s.sourceCount(message.citations.length)}` : '';
    const line = el('p', { lang: message.lang, text: `${who}: ${message.text.replace(/\[\d+\]/g, '')}${count}` });
    announcer.append(line);
    while (announcer.children.length > 4) announcer.firstChild.remove();
  }

  function setStatus(text) {
    status.textContent = text || '';
  }

  function addMessage(message) {
    state.messages.push(message);
    session.set('messages', state.messages.filter((m) => !m.error));
    list.replaceChildren(...state.messages.map(renderMessage));
    renderSuggestions();
    announce(message);
    scrollToEnd();
  }

  // ------------------------------------------------------------ Mimi's voice (text to speech)

  // One speaker for the whole widget, so two answers can never be heard at once: every speak()
  // first stops whatever is playing. It prefers the server voice (one female voice for both
  // languages, see server/speech.py) and falls back to the browser's best female-sounding voice.
  const Speaker = (() => {
    const synth = 'speechSynthesis' in window ? window.speechSynthesis : null;
    const audio = new Audio();
    const SILENCE = 'data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAIA+AAACABAAZGF0YQAAAAA=';
    let token = 0;
    let cancelCurrent = null;
    let serverDownUntil = 0;

    // Feminine voice names on Windows, macOS, iOS, Android, Chrome and Edge. Browsers do not expose
    // a voice's gender, so names are the only signal; male names are pushed to the bottom.
    const FEMALE = /female|woman|mekdes|samantha|victoria|karen|moira|tessa|fiona|serena|susan|allison|\bava\b|zira|aria|jenny|michelle|sonia|libby|natasha|emma|clara|salli|joanna|kendra|kimberly|ivy|google us english|google uk english female/i;
    const MALE = /\bmale\b|\bman\b|ameha|david|mark|guy|daniel|\balex\b|fred|rishi|george|ryan|thomas|aaron|arthur|oliver|james|christopher|eric|roger|brian|google uk english male/i;

    function unlock() {
      // Called from a click or key press: lets later, programmatic playback through.
      try {
        audio.src = SILENCE;
        const p = audio.play();
        if (p) p.catch(() => {});
      } catch {
        /* nothing to unlock */
      }
    }

    // Fixed phrases are recorded on the server, so they are worth asking for even when its voice is paused.
    const serverReady = (cache = false) =>
      config.tts !== 'browser' && ((caps.tts && Date.now() > serverDownUntil) || (cache && caps.ttsCache));
    const available = () => serverReady() || !!synth;

    function sentences(text) {
      return (text.match(/[^.!?።\n]+[.!?።]*/g) || [text]).map((s) => s.trim()).filter(Boolean);
    }

    // The first sentence alone, so the voice starts quickly; the rest in as few requests as possible.
    function chunks(text) {
      if (text.length <= 160) return [text]; // a confirmation or a one-line reply: one request
      const parts = sentences(text);
      const out = [];
      let current = '';
      for (const sentence of parts) {
        const limit = out.length === 0 ? 200 : 900;
        if (current && (current + ' ' + sentence).length > limit) {
          out.push(current);
          current = sentence;
        } else current = current ? `${current} ${sentence}` : sentence;
        if (out.length === 0 && current.length > 40) {
          out.push(current);
          current = '';
        }
      }
      if (current) out.push(current);
      return out;
    }

    async function fetchAudio(text, lang, cache) {
      const response = await request('/api/tts', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ text, lang, cache }) }, 60000);
      if (!response.ok) throw Object.assign(new Error('tts'), { status: response.status });
      return URL.createObjectURL(await response.blob());
    }

    function play(url) {
      return new Promise((resolve, reject) => {
        let done = false;
        const finish = (fn, value) => {
          if (done) return;
          done = true;
          cancelCurrent = null;
          audio.onended = audio.onerror = null;
          fn(value);
        };
        cancelCurrent = () => {
          audio.pause();
          finish(resolve, 'stopped');
        };
        audio.onended = () => finish(resolve, 'done');
        audio.onerror = () => finish(reject, new Error('audio'));
        audio.src = url;
        const p = audio.play();
        if (p) p.catch((e) => finish(reject, e));
      });
    }

    async function speakServer(text, lang, cache, my) {
      const parts = chunks(text);
      let next = fetchAudio(parts[0], lang, cache);
      for (let i = 0; i < parts.length; i++) {
        let url;
        try {
          url = await next;
        } catch (e) {
          if (i === 0) throw e;
          return 'partial'; // the rest is on screen; do not switch to another voice mid-answer
        }
        if (my !== token) {
          URL.revokeObjectURL(url);
          return 'stopped';
        }
        next = i + 1 < parts.length ? fetchAudio(parts[i + 1], lang, cache) : null;
        if (next) next.catch(() => {}); // handled when awaited
        try {
          if ((await play(url)) === 'stopped') return 'stopped';
        } finally {
          URL.revokeObjectURL(url);
        }
        if (my !== token) return 'stopped';
      }
      return 'done';
    }

    function voices() {
      if (!synth) return Promise.resolve([]);
      const now = synth.getVoices();
      if (now.length) return Promise.resolve(now);
      return new Promise((resolve) => {
        const timer = setTimeout(() => resolve(synth.getVoices()), 1200);
        synth.addEventListener('voiceschanged', () => { clearTimeout(timer); resolve(synth.getVoices()); }, { once: true });
      });
    }

    function pickVoice(all, lang) {
      const candidates = all.filter((v) => v.lang.toLowerCase().replace('_', '-').startsWith(lang));
      const score = (v) =>
        (FEMALE.test(v.name) ? 4 : 0) - (MALE.test(v.name) ? 6 : 0) + (/natural|neural|online|premium|enhanced/i.test(v.name) ? 2 : 0) +
        (v.lang.toLowerCase().replace('_', '-') === SPEECH_LANG[lang].toLowerCase() ? 1 : 0);
      return candidates.sort((a, b) => score(b) - score(a))[0] || null;
    }

    async function speakBrowser(text, lang, my) {
      const voice = pickVoice(await voices(), lang);
      if (my !== token) return 'stopped';
      if (!voice) throw Object.assign(new Error('no voice'), { code: 'novoice' });
      return new Promise((resolve, reject) => {
        const parts = sentences(text);
        let i = 0;
        let settled = false;
        const settle = (fn, value) => {
          if (settled) return;
          settled = true;
          cancelCurrent = null;
          fn(value);
        };
        cancelCurrent = () => {
          synth.cancel();
          settle(resolve, 'stopped');
        };
        const next = () => {
          if (my !== token) return settle(resolve, 'stopped');
          if (i >= parts.length) return settle(resolve, 'done');
          const utterance = new SpeechSynthesisUtterance(parts[i++]);
          utterance.voice = voice;
          utterance.lang = voice.lang;
          utterance.rate = 0.95;
          utterance.pitch = 1.05;
          utterance.onend = next;
          utterance.onerror = (event) => {
            if (event.error === 'not-allowed') settle(reject, Object.assign(new Error('blocked'), { code: 'blocked' }));
            else if (event.error === 'interrupted' || event.error === 'canceled') settle(resolve, 'stopped');
            else next();
          };
          synth.speak(utterance);
        };
        synth.cancel();
        next();
      });
    }

    function spoken(text) {
      return text.replace(/\s*\[\d+\]/g, '').replace(/\s+/g, ' ').trim();
    }

    // Resolves 'done' | 'partial' | 'stopped'; rejects with code 'blocked' | 'novoice' | 'unavailable'.
    async function speak(text, lang, { cache = false } = {}) {
      stop();
      const my = ++token;
      const say = spoken(text);
      if (!say) return 'done';
      if (serverReady(cache)) {
        try {
          return await speakServer(say, lang, cache, my);
        } catch (e) {
          if (e && e.name === 'NotAllowedError') throw Object.assign(new Error('blocked'), { code: 'blocked' });
          if (my !== token) return 'stopped';
          if (!cache) serverDownUntil = Date.now() + 120000; // quota or network: use the browser voice for a while
        }
      }
      if (!synth || config.tts === 'server') throw Object.assign(new Error('unavailable'), { code: 'unavailable' });
      return speakBrowser(say, lang, my);
    }

    function stop() {
      token++;
      if (cancelCurrent) cancelCurrent();
      audio.pause();
      if (synth) synth.cancel();
    }

    return { speak, stop, unlock, available, busy: () => cancelCurrent !== null };
  })();

  // ------------------------------------------------------------ hearing the learner (speech to text)

  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  // Chrome and Edge send speech to Google's or Microsoft's recognisers, which know Amharic.
  // Safari's and others' do not reliably, so Amharic goes to the server there.
  const isChromium = /Chrome\/|Edg\//.test(navigator.userAgent) && !/OPR\//.test(navigator.userAgent);
  const canRecord = !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia && (window.AudioContext || window.webkitAudioContext));
  const failedEngines = new Set();

  function engineFor(lang) {
    const server = caps.stt && canRecord && !failedEngines.has('server');
    const browser = !!Recognition && !failedEngines.has(`browser-${lang}`);
    if (config.stt === 'server') return server ? 'server' : null;
    if (config.stt === 'browser') return browser ? 'browser' : null;
    if (browser && (lang === 'en' || isChromium)) return 'browser';
    if (server) return 'server';
    return browser ? 'browser' : null;
  }

  // The browser's own recogniser, kept running across its automatic stops. A turn ends after
  // END_OF_TURN_MS of silence, not at the recogniser's first "final" result, so a learner can pause
  // to think mid-sentence without being cut off.
  function webSpeechEngine() {
    let rec = null;
    let active = false;
    let generation = 0;
    let timer = null;
    let carried = '';
    let current = '';
    let quietRestarts = 0;
    let networkErrors = 0;
    let lastError = '';
    let handlers = null;
    let lang = 'en';
    const text = () => `${carried} ${current}`.replace(/\s+/g, ' ').trim();

    function start(l, h) {
      if (active) return;
      active = true;
      handlers = h;
      lang = l;
      carried = current = '';
      quietRestarts = networkErrors = 0;
      open();
    }

    function open() {
      const my = ++generation;
      lastError = '';
      rec = new Recognition();
      rec.lang = SPEECH_LANG[lang];
      rec.continuous = true;
      rec.interimResults = true;
      rec.maxAlternatives = 1;
      rec.onresult = (event) => {
        if (my !== generation) return;
        current = Array.from(event.results, (r) => r[0].transcript).join(' ');
        quietRestarts = networkErrors = 0;
        handlers.onInterim(text());
        clearTimeout(timer);
        timer = setTimeout(finish, END_OF_TURN_MS[lang]);
      };
      rec.onerror = (event) => {
        if (my === generation) lastError = event.error;
      };
      rec.onend = () => {
        if (my !== generation || !active) return;
        carried = text();
        current = '';
        const error = lastError;
        if (error === 'not-allowed' || error === 'service-not-allowed') return fail('denied');
        if (error === 'audio-capture') return fail('no-mic');
        if (error === 'language-not-supported' || error === 'bad-grammar') return fail('unsupported');
        if (error === 'network' && ++networkErrors > 2) return fail('network');
        if (!carried && ++quietRestarts > MAX_QUIET_RESTARTS) {
          stop();
          return handlers.onIdle();
        }
        setTimeout(() => {
          if (active && my === generation) open();
        }, error === 'network' ? 1000 * networkErrors : 250);
      };
      try {
        rec.start();
      } catch {
        fail('failed');
      }
    }

    function finish() {
      const said = text();
      if (!active || !said) return;
      stop();
      handlers.onFinal(said);
    }

    function fail(code) {
      stop();
      handlers.onError(code);
    }

    function stop() {
      active = false;
      generation++;
      clearTimeout(timer);
      const r = rec;
      rec = null;
      if (r) {
        r.onresult = r.onerror = r.onend = null;
        try {
          r.abort();
        } catch {
          /* already stopped */
        }
      }
    }

    return { kind: 'browser', start, stop, get active() { return active; } };
  }

  // Fallback: record the microphone, find the end of the learner's turn from the sound level, and
  // send that one turn as a WAV to /api/transcribe. Nothing is recorded while Mimi is speaking.
  const mic = { stream: null, ctx: null, source: null, node: null, sink: null };

  async function openMic() {
    if (mic.stream && mic.stream.getAudioTracks().some((track) => track.readyState === 'live')) return;
    mic.stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1 } });
    const Context = window.AudioContext || window.webkitAudioContext;
    mic.ctx = new Context();
    mic.source = mic.ctx.createMediaStreamSource(mic.stream);
    mic.node = mic.ctx.createScriptProcessor(4096, 1, 1);
    mic.sink = mic.ctx.createGain();
    mic.sink.gain.value = 0;
    mic.source.connect(mic.node);
    mic.node.connect(mic.sink);
    mic.sink.connect(mic.ctx.destination);
  }

  function releaseMic() {
    if (mic.node) mic.node.onaudioprocess = null;
    if (mic.stream) mic.stream.getTracks().forEach((track) => track.stop());
    if (mic.ctx) mic.ctx.close().catch(() => {});
    for (const key of Object.keys(mic)) mic[key] = null;
  }

  function encodeWav(frames, rate) {
    const target = 16000;
    const ratio = Math.max(rate / target, 1);
    const total = frames.reduce((n, f) => n + f.length, 0);
    const flat = new Float32Array(total);
    let offset = 0;
    for (const f of frames) {
      flat.set(f, offset);
      offset += f.length;
    }
    const length = Math.floor(total / ratio);
    const pcm = new Int16Array(length);
    for (let i = 0; i < length; i++) {
      const from = Math.floor(i * ratio);
      const to = Math.min(Math.max(Math.floor((i + 1) * ratio), from + 1), total);
      let sum = 0;
      for (let j = from; j < to; j++) sum += flat[j];
      pcm[i] = Math.max(-1, Math.min(1, sum / (to - from))) * 0x7fff;
    }
    const buffer = new ArrayBuffer(44 + pcm.length * 2);
    const view = new DataView(buffer);
    const ascii = (at, s) => [...s].forEach((c, i) => view.setUint8(at + i, c.charCodeAt(0)));
    ascii(0, 'RIFF');
    view.setUint32(4, 36 + pcm.length * 2, true);
    ascii(8, 'WAVE');
    ascii(12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, 1, true);
    view.setUint32(24, rate >= target ? target : rate, true);
    view.setUint32(28, (rate >= target ? target : rate) * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    ascii(36, 'data');
    view.setUint32(40, pcm.length * 2, true);
    new Int16Array(buffer, 44).set(pcm);
    return new Blob([buffer], { type: 'audio/wav' });
  }

  function recorderEngine() {
    let active = false;
    let generation = 0;

    async function start(lang, handlers) {
      if (active) return;
      active = true;
      const my = ++generation;
      try {
        await openMic();
      } catch (e) {
        if (my !== generation) return;
        active = false;
        return handlers.onError(e && (e.name === 'NotAllowedError' || e.name === 'SecurityError') ? 'denied' : 'no-mic');
      }
      if (my !== generation) return;
      if (mic.ctx.state === 'suspended') mic.ctx.resume().catch(() => {});
      const rate = mic.ctx.sampleRate;
      const frameMs = (4096 / rate) * 1000;
      let calibrated = 0;
      let noise = 0;
      let speaking = false;
      let loudMs = 0;
      let silentMs = 0;
      let speechMs = 0;
      let quietMs = 0;
      const preRoll = [];
      const frames = [];
      mic.node.onaudioprocess = (event) => {
        if (!active || my !== generation) return;
        const data = new Float32Array(event.inputBuffer.getChannelData(0));
        let sum = 0;
        for (let i = 0; i < data.length; i++) sum += data[i] * data[i];
        const rms = Math.sqrt(sum / data.length);
        if (calibrated < 300) {
          noise = noise ? noise * 0.7 + rms * 0.3 : rms;
          calibrated += frameMs;
          return;
        }
        const threshold = Math.max(0.012, noise * 3);
        if (!speaking) {
          preRoll.push(data); // keep the start of the first word
          if (preRoll.length * frameMs > 500) preRoll.shift();
          if (rms > threshold) {
            loudMs += frameMs;
            if (loudMs >= 150) {
              speaking = true;
              frames.push(...preRoll);
              preRoll.length = 0;
              handlers.onInterim('…');
            }
          } else {
            loudMs = 0;
            noise = noise * 0.95 + rms * 0.05;
            quietMs += frameMs;
            if (quietMs > QUIET_LIMIT_MS) {
              stop();
              handlers.onIdle();
            }
          }
          return;
        }
        frames.push(data);
        if (rms > threshold * 0.7) {
          silentMs = 0;
          speechMs += frameMs;
        } else silentMs += frameMs;
        const total = frames.length * frameMs;
        if ((silentMs >= END_OF_TURN_MS[lang] && speechMs >= 350) || total > 25000) {
          const wav = encodeWav(frames, rate);
          stop();
          handlers.onAudio(wav);
        } else if (silentMs >= END_OF_TURN_MS[lang]) {
          speaking = false; // a cough or a click, not a turn
          frames.length = 0;
          silentMs = speechMs = loudMs = 0;
        }
      };
    }

    function stop() {
      active = false;
      generation++;
      if (mic.node) mic.node.onaudioprocess = null;
    }

    return { kind: 'server', start, stop, get active() { return active; } };
  }

  // ------------------------------------------------------------ the conversation (state machine)

  const INIT = 'initializing';
  const GREETING_STATE = 'greeting';
  const CHOOSING = 'language_selection';
  const LISTENING = 'listening';
  const PROCESSING = 'processing';
  const SPEAKING = 'speaking';
  const TEXT = 'text_mode';
  const PAUSED = 'paused';
  const ERROR = 'error';

  // Valid transitions. Notably absent: anything back into "greeting" once a language is being used
  // (no repeated welcome), and greeting -> listening (a language must be chosen first).
  const ALLOWED = {
    [INIT]: [GREETING_STATE, CHOOSING, LISTENING, PROCESSING, SPEAKING, TEXT, PAUSED, ERROR],
    [GREETING_STATE]: [CHOOSING, SPEAKING, PROCESSING, TEXT, PAUSED, ERROR],
    [CHOOSING]: [GREETING_STATE, SPEAKING, PROCESSING, LISTENING, TEXT, PAUSED, ERROR],
    [LISTENING]: [PROCESSING, SPEAKING, CHOOSING, TEXT, PAUSED, ERROR],
    [PROCESSING]: [SPEAKING, LISTENING, CHOOSING, TEXT, PAUSED, ERROR],
    [SPEAKING]: [LISTENING, CHOOSING, PROCESSING, GREETING_STATE, TEXT, PAUSED, ERROR],
    [TEXT]: [PROCESSING, SPEAKING, LISTENING, CHOOSING, GREETING_STATE, PAUSED, ERROR],
    [PAUSED]: [GREETING_STATE, CHOOSING, LISTENING, PROCESSING, SPEAKING, TEXT, ERROR],
    [ERROR]: [LISTENING, CHOOSING, PROCESSING, SPEAKING, TEXT, PAUSED],
  };

  const ctl = {
    state: INIT,
    listener: null,
    canListen: true,
    turn: 0, // one per learner turn: a late answer to an older turn is dropped
    speech: 0, // one per say(): a superseded speech does not move the state on
    speakingButton: null,
    choiceAttempts: 0,
    errors: 0,
    sttErrors: 0,
    needsUnlock: false,
    greetPending: false,
    pauseReason: '',
    booted: false,
    unlockedAt: 0,
  };

  function go(next) {
    const prev = ctl.state;
    if (prev !== next) {
      if (!ALLOWED[prev].includes(next)) {
        console.warn(`[Mimi] refused transition ${prev} -> ${next}`);
        return false;
      }
      ctl.state = next;
    }
    if (next !== LISTENING && next !== CHOOSING) stopListener();
    if (next !== PAUSED) ctl.pauseReason = '';
    host.dataset.state = next; // for tests and debugging; not read by the page
    renderVoiceBar();
    return true;
  }

  const listeningState = () => ctl.state === LISTENING || ctl.state === CHOOSING;

  function renderVoiceBar() {
    const s = t();
    let label;
    let iconName;
    let action = null;
    switch (ctl.state) {
      case INIT: label = s.sInit; iconName = 'dots'; break;
      case GREETING_STATE:
      case SPEAKING: label = s.sSpeaking; iconName = 'speaker'; action = ['skip', s.aSkip]; break;
      case CHOOSING:
        label = ctl.listener && ctl.listener.active ? s.sChoose : s.sChooseNoMic;
        iconName = ctl.listener && ctl.listener.active ? 'mic' : 'keyboard';
        break;
      case LISTENING: label = s.sListening; iconName = 'mic'; action = ['pause', s.aPause]; break;
      case PROCESSING: label = s.sProcessing; iconName = 'dots'; break;
      case TEXT:
        label = state.voiceOn ? s.sTextNoMic : s.sText;
        iconName = 'keyboard';
        action = state.voiceOn ? ['resume', s.aResume] : ['voice', s.voiceOn];
        break;
      case PAUSED: label = ctl.pauseReason === 'typing' ? s.sTyping : s.sPaused; iconName = 'pause'; action = ['resume', s.aResume]; break;
      default: label = s.sError; iconName = 'alert'; action = ['resume', s.retry];
    }
    if (ctl.needsUnlock) action = ['unlock', s.aUnlock];
    voiceBar.dataset.state = ctl.state;
    voiceState.textContent = label;
    voiceIcon.replaceChildren(icon(iconName));
    voiceAction.hidden = !action;
    if (action) {
      voiceAction.dataset.action = action[0];
      voiceActionText.textContent = action[1];
    }
  }

  function onVoiceAction() {
    // The press that unlocked sound already acted; its click must not also hit the next action.
    if (Date.now() - ctl.unlockedAt < 700) return;
    switch (voiceAction.dataset.action) {
      case 'skip':
        Speaker.stop(); // the say() in progress resolves 'stopped' and the conversation moves on
        break;
      case 'pause':
        go(PAUSED);
        break;
      case 'resume':
        ctl.canListen = true;
        ctl.choiceAttempts = 0;
        resume();
        break;
      case 'voice':
        setVoice(true);
        break;
      default:
    }
  }

  const handlers = {
    onInterim(text) {
      if (listeningState() && ctl.pauseReason !== 'typing') {
        input.value = text;
        resizeInput();
      }
    },
    onFinal(text) {
      if (!listeningState()) return;
      input.value = '';
      resizeInput();
      takeTurn(text, 'voice');
    },
    async onAudio(wav) {
      if (!listeningState()) return;
      input.value = '';
      go(PROCESSING);
      let text = '';
      try {
        const purpose = state.langChosen ? '' : '&purpose=language_choice';
        const response = await request(`/api/transcribe?lang=${state.lang}${purpose}`, { method: 'POST', headers: { 'Content-Type': 'audio/wav' }, body: wav }, 30000);
        if (!response.ok) throw new Error(String(response.status));
        text = ((await response.json()).text || '').trim();
        ctl.sttErrors = 0;
      } catch {
        if (++ctl.sttErrors >= 2) failedEngines.add('server');
      }
      if (ctl.state !== PROCESSING || state.busy) return; // voice turned off, or the learner typed
      if (text) return takeTurn(text, 'voice');
      go(state.langChosen ? LISTENING : CHOOSING);
      listen();
    },
    onError(code) {
      if (code === 'unsupported' || code === 'network') failedEngines.add(`browser-${state.lang}`);
      if (code !== 'denied' && code !== 'no-mic' && engineFor(state.lang)) return listen(); // try the other engine
      ctl.canListen = false;
      const s = t();
      setStatus({ denied: s.micDenied, 'no-mic': s.micNone, unsupported: s.micLang }[code] || s.micNetwork);
      go(state.langChosen ? TEXT : CHOOSING);
    },
    onIdle() {
      if (!listeningState()) return;
      go(PAUSED);
      setStatus(t().quiet);
    },
  };

  function listen() {
    if (!listeningState()) return;
    if (!state.voiceOn || !ctl.canListen || !state.open || document.hidden || state.busy || Speaker.busy()) return;
    const kind = engineFor(state.lang);
    if (!kind) {
      ctl.canListen = false;
      setStatus(t().micLang);
      if (state.langChosen) go(TEXT);
      else renderVoiceBar();
      return;
    }
    if (!ctl.listener || ctl.listener.kind !== kind) {
      stopListener();
      ctl.listener = kind === 'browser' ? webSpeechEngine() : recorderEngine();
    }
    ctl.listener.start(state.lang, handlers);
    renderVoiceBar();
  }

  function stopListener() {
    if (ctl.listener) ctl.listener.stop();
  }

  const canSpeak = () => Speaker.available();

  // Speak, moving the state to "speaking" (or "greeting") for exactly as long as Mimi is heard.
  async function say(text, lang, { cache = false, speakState = SPEAKING, button = null } = {}) {
    const my = ++ctl.speech;
    if (!canSpeak() || !go(speakState)) return 'skipped';
    markButton(button);
    let result;
    try {
      result = await Speaker.speak(text, lang, { cache });
    } catch (e) {
      result = (e && e.code) || 'failed';
      if (result === 'blocked') {
        ctl.needsUnlock = true;
        setStatus(t().speechBlocked);
      } else if (result === 'novoice') setStatus(t().noVoice(lang));
      else setStatus(t().speechUnavailable);
    }
    if (my !== ctl.speech) return 'superseded';
    markButton(null);
    return result;
  }

  function markButton(button) {
    const old = ctl.speakingButton;
    if (old && old !== button) {
      old.setAttribute('aria-pressed', 'false');
      old.lastChild.textContent = t().replay;
    }
    ctl.speakingButton = button;
    if (button) {
      button.setAttribute('aria-pressed', 'true');
      button.lastChild.textContent = t().stopReplay;
    }
  }

  // Where to go once Mimi has finished talking: listen again, or wait for typing.
  function afterSpeech() {
    if (state.busy) return; // a new turn is already on its way
    if (!state.open) return go(PAUSED);
    if (!state.langChosen) go(CHOOSING);
    else if (state.voiceOn && ctl.canListen) go(LISTENING);
    else return go(TEXT);
    setTimeout(listen, ECHO_GAP_MS);
  }

  function resume() {
    if (state.busy) return;
    if (!state.voiceOn) return go(state.langChosen ? TEXT : CHOOSING);
    go(state.langChosen ? LISTENING : CHOOSING);
    listen();
  }

  // ------------------------------------------------------------ greeting and language

  async function greet() {
    if (!state.greeted) {
      state.greeted = true;
      session.set('greeted', true);
      const other = config.greetLang === 'am' ? 'en' : 'am';
      addMessage({ role: 'assistant', kind: 'greeting', text: GREETING[config.greetLang], lang: config.greetLang, translation: config.greetLang === 'am' ? GREETING[other] : null, citations: [] });
    }
    if (!state.voiceOn || !canSpeak()) {
      go(CHOOSING);
      listen();
      return;
    }
    const result = await say(GREETING[config.greetLang], config.greetLang, { cache: true, speakState: GREETING_STATE });
    if (result === 'superseded' || state.langChosen) return;
    if (result === 'blocked') ctl.greetPending = true;
    go(CHOOSING);
    setTimeout(listen, ECHO_GAP_MS);
  }

  // The first click or key press anywhere on the page lets the browser play sound; if the
  // greeting was held back, it is spoken then.
  function onGesture() {
    Speaker.unlock();
    if (mic.ctx && mic.ctx.state === 'suspended') mic.ctx.resume().catch(() => {});
    const wasBlocked = ctl.needsUnlock;
    if (wasBlocked) ctl.unlockedAt = Date.now();
    ctl.needsUnlock = false;
    renderVoiceBar();
    if (wasBlocked) setStatus('');
    if (ctl.greetPending && !state.langChosen && state.voiceOn) {
      ctl.greetPending = false;
      setTimeout(async () => {
        if (state.langChosen || state.busy) return;
        const result = await say(GREETING[config.greetLang], config.greetLang, { cache: true, speakState: GREETING_STATE });
        if (result !== 'superseded' && !state.langChosen) {
          go(CHOOSING);
          setTimeout(listen, ECHO_GAP_MS);
        }
      }, 250);
    }
  }
  document.addEventListener('pointerdown', onGesture, true);
  document.addEventListener('keydown', onGesture, true);

  async function syncSession(lang) {
    try {
      const data = await postJSON('/api/session', { session_id: state.sessionId, lang: lang || undefined }, 5000);
      state.sessionId = data.session_id;
      session.set('session-id', data.session_id);
    } catch {
      /* the server is not reachable: the browser keeps the language until it is */
    }
  }

  function setLanguage(lang) {
    state.lang = lang;
    state.langChosen = true;
    session.set('lang', lang);
    session.set('lang-chosen', true);
    ctl.choiceAttempts = 0;
    syncSession(lang);
    applyLanguage();
  }

  async function chooseLanguage(lang) {
    const first = !state.langChosen;
    const focusedChoice = shadow.activeElement && shadow.activeElement.classList.contains('choice');
    setLanguage(lang);
    if (focusedChoice || shadow.activeElement === langButtons[lang]) (first ? input : langButtons[lang]).focus();
    const confirm = STRINGS[lang].confirm;
    addMessage({ role: 'assistant', kind: 'confirm', text: confirm, lang, citations: [] });
    if (!first || state.busy) {
      if (state.voiceOn && !state.busy) {
        const result = await say(confirm, lang, { cache: true });
        if (result !== 'superseded') afterSpeech();
      } else if (!state.busy) afterSpeech();
      return;
    }
    // First choice: confirm, then introduce the lesson. The introduction is fetched while the
    // confirmation is being spoken.
    state.busy = true;
    setBusy(true);
    const my = ++ctl.turn;
    const intro = fetchReply('', { intent: 'lesson_intro', history: [] });
    if (state.voiceOn) await say(confirm, lang, { cache: true });
    if (my !== ctl.turn) return;
    go(PROCESSING);
    const reply = await intro;
    finishTurn();
    if (my === ctl.turn) await deliver(reply);
  }

  async function retryChoice() {
    if (++ctl.choiceAttempts > 2) {
      go(PAUSED);
      setStatus(STRINGS[state.lang].chooseRetry);
      return;
    }
    const text = STRINGS[state.lang].chooseRetry;
    setStatus(text);
    const result = await say(text, state.lang);
    if (result !== 'superseded') afterSpeech();
  }

  // ------------------------------------------------------------ turns

  function takeTurn(text, source) {
    const said = text.trim();
    if (!said || state.busy) return;
    if (!state.langChosen) {
      const choice = languageChoice(said);
      if (choice) {
        addMessage({ role: 'user', text: said, lang: scriptLang(said) });
        input.value = '';
        resizeInput();
        return chooseLanguage(choice);
      }
      if (source === 'voice') return retryChoice();
      // A typed question before choosing: answer in the language it is written in.
      setLanguage(scriptLang(said));
      setStatus(t().langInferred);
    }
    return askTutor(said);
  }

  function pageContext() {
    let lesson = config.lesson;
    if (config.lessonSelector) {
      const node = document.querySelector(config.lessonSelector);
      const found = node && node.textContent.replace(/\s+/g, ' ').trim().slice(0, 160);
      if (found) lesson = found;
    }
    return { page: PAGE, course: config.course, lesson };
  }

  async function fetchReply(question, { intent = null, history = [] } = {}) {
    const typing = el('li', { class: 'msg msg-bot', 'aria-hidden': 'true' }, el('div', { class: 'bubble typing' }, el('span'), el('span'), el('span')));
    list.append(typing);
    scrollToEnd();
    try {
      const data = await postJSON(
        '/api/ask',
        { question, lang: state.lang, simple: state.simple, history, session_id: state.sessionId, context: pageContext(), intent, voice: state.voiceOn, detect_switch: !intent },
        90000,
      );
      if (!data.session_id && state.sessionId) {
        state.sessionId = null; // the server restarted and forgot the session; make a new one
        syncSession(state.lang);
      }
      ctl.errors = 0;
      return {
        role: 'assistant', text: data.answer, lang: data.lang, citations: data.citations || [], provider: data.provider,
        switchLang: data.switch_lang || null, kind: intent === 'lesson_intro' ? 'intro' : data.switch_lang ? 'confirm' : undefined,
        lessonKey: intent === 'lesson_intro' ? lessonKey() : undefined,
      };
    } catch {
      ctl.errors++;
      return { role: 'assistant', text: t().error, lang: state.lang, citations: [], error: true };
    } finally {
      typing.remove();
    }
  }

  async function askTutor(question, { intent = null } = {}) {
    if (state.busy) return;
    state.busy = true;
    setBusy(true);
    const my = ++ctl.turn;
    Speaker.stop();
    go(PROCESSING);
    const history = state.messages
      .filter((m) => !m.error && !['greeting', 'confirm', 'welcome'].includes(m.kind))
      .slice(-6)
      .map((m) => ({ role: m.role, content: m.text }));
    if (question) {
      // Host contract event, for pages that embed the assistant.
      document.dispatchEvent(new CustomEvent('db-assistant:question', {
        bubbles: true, composed: true, detail: { text: question, language: state.lang },
      }));
      addMessage({ role: 'user', text: question, lang: scriptLang(question) });
    }
    input.value = '';
    resizeInput();
    const reply = await fetchReply(question, { intent, history });
    finishTurn();
    if (my === ctl.turn) await deliver(reply);
  }

  function finishTurn() {
    state.busy = false;
    setBusy(false);
  }

  async function deliver(reply) {
    if (reply.switchLang) {
      state.lang = reply.switchLang; // the server already moved the session to this language
      session.set('lang', reply.switchLang);
      applyLanguage();
    }
    addMessage(reply);
    if (reply.error && ctl.errors >= 2) {
      go(ERROR); // the service is down: do not keep listening and failing
      return;
    }
    if (state.voiceOn) {
      const result = await say(reply.text, reply.lang || state.lang, { cache: !!reply.switchLang });
      if (result === 'superseded') return;
    } else input.focus();
    afterSpeech();
  }

  function retry() {
    const lastQuestion = [...state.messages].reverse().find((m) => m.role === 'user');
    state.messages = state.messages.filter((m) => !m.error);
    if (lastQuestion) {
      state.messages.splice(state.messages.lastIndexOf(lastQuestion), 1);
      renderMessages();
      askTutor(lastQuestion.text);
    }
  }

  async function replay(message, button) {
    if (state.busy) return;
    if (button.getAttribute('aria-pressed') === 'true') {
      Speaker.stop();
      return;
    }
    stopListener();
    const result = await say(message.text, message.lang || state.lang, { button, cache: ['greeting', 'confirm'].includes(message.kind) });
    if (result !== 'superseded') afterSpeech();
  }

  // ------------------------------------------------------------ live escalation & screen sharing

  async function escalateToHuman() {
    const s = t();
    setStatus(s.escalating);
    const lastTopic = state.messages.length ? state.messages[state.messages.length - 1].text : (location.pathname + location.hash);
    try {
      const res = await fetch('http://localhost:8000/handoff/tickets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lang: state.lang, topic: lastTopic, channel: 'web' }),
      });
      const data = await res.json();
      setStatus('');
      document.dispatchEvent(new CustomEvent('db-assistant:escalated', {
        bubbles: true, composed: true, detail: { ticketId: data.ticket_id },
      }));
      if (data.chat_url) window.open(`http://localhost:8000${data.chat_url}`, '_blank', 'noopener');
    } catch {
      window.open(`http://localhost:8000/handoff/start?lang=${state.lang}`, '_blank', 'noopener');
    }
  }

  async function toggleScreenShare() {
    const s = t();
    if (screenStream) {
      screenStream.getTracks().forEach((track) => track.stop());
      screenStream = null;
      shareButton.classList.remove('active');
      shareText.textContent = s.screenShare;
      setStatus('');
      return;
    }
    // Chrome on Android does not support getDisplayMedia.
    if (!navigator.mediaDevices || !navigator.mediaDevices.getDisplayMedia) {
      setStatus(s.screenShareAndroid);
      return;
    }
    try {
      screenStream = await navigator.mediaDevices.getDisplayMedia({ video: true });
      shareButton.classList.add('active');
      shareText.textContent = s.screenSharingActive;
      setStatus(s.screenSharingActive);
      screenStream.getVideoTracks()[0].onended = () => {
        screenStream = null;
        shareButton.classList.remove('active');
        shareText.textContent = t().screenShare;
        setStatus('');
      };
    } catch {
      setStatus('');
    }
  }

  // ------------------------------------------------------------ settings and open/close

  function setVoice(on) {
    state.voiceOn = on;
    session.set('voice', on);
    renderVoiceToggle();
    if (!on) {
      ctl.greetPending = false;
      Speaker.stop();
      stopListener();
      releaseMic();
      if (!state.busy) go(state.langChosen ? TEXT : CHOOSING);
      setStatus(t().voiceTurnedOff);
      input.focus();
      return;
    }
    Speaker.unlock();
    ctl.canListen = true;
    ctl.choiceAttempts = 0;
    setStatus(t().voiceTurnedOn);
    if (state.busy) return renderVoiceBar(); // the answer on its way will be spoken
    if (!state.greeted) return greet();
    resume();
  }

  function setOpen(open) {
    state.open = open;
    session.set('open', open);
    root.classList.toggle('open', open);
    panel.hidden = !open;
    launcher.hidden = open;
    launcher.setAttribute('aria-expanded', String(open));
    if (open) {
      scrollToEnd();
      input.focus();
      if (!state.greeted) greet();
      else resume();
    } else {
      Speaker.stop();
      stopListener();
      releaseMic();
      if (!state.busy) go(PAUSED);
      launcher.focus();
    }
  }

  function setSimple(on) {
    state.simple = on;
    store(localStorage, 'ableway-simple', on);
    simpleSwitch.setAttribute('aria-checked', String(on));
  }

  function clearChat() {
    state.messages = [];
    session.set('messages', state.messages);
    renderMessages();
    setStatus(t().cleared);
    input.focus();
  }

  function setBusy(busy) {
    // aria-disabled keeps the button focusable, so focus is not lost while waiting.
    sendButton.setAttribute('aria-disabled', String(busy));
    if (busy) setStatus('');
  }

  function onSubmit(event) {
    event.preventDefault();
    takeTurn(input.value, 'text');
  }

  function resizeInput() {
    input.style.height = 'auto';
    input.style.height = `${Math.min(input.scrollHeight + 4, 120)}px`;
  }

  input.addEventListener('input', (event) => {
    resizeInput();
    // The learner started typing while Mimi was listening: stop listening for this turn.
    if (event.isTrusted && listeningState()) {
      go(PAUSED);
      ctl.pauseReason = 'typing';
      renderVoiceBar();
    }
  });
  input.addEventListener('keydown', (event) => {
    // Enter sends; Shift+Enter makes a new line. Not while an input method is composing.
    if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
      event.preventDefault();
      form.requestSubmit();
    }
  });
  panel.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') {
      event.stopPropagation();
      setOpen(false);
    }
  });

  document.addEventListener('visibilitychange', () => {
    if (document.hidden && listeningState()) {
      go(PAUSED);
      ctl.pauseReason = 'hidden';
    } else if (!document.hidden && ctl.state === PAUSED && ctl.pauseReason === 'hidden') resume();
  });
  window.addEventListener('pagehide', () => {
    Speaker.stop();
    stopListener();
    releaseMic();
  });

  // ------------------------------------------------------------ start

  async function loadCapabilities() {
    try {
      const response = await request('/api/health', {}, 3000);
      const health = await response.json();
      caps.server = true;
      caps.tts = !!(health.speech && health.speech.tts);
      caps.stt = !!(health.speech && health.speech.stt);
      caps.ttsCache = !!(health.speech && health.speech.tts_cache);
    } catch {
      caps.server = false; // text still works offline only through the server; the widget says so on send
    }
  }

  async function boot() {
    if (ctl.booted) return;
    ctl.booted = true;
    await loadCapabilities();
    if (!state.sessionId || state.langChosen) syncSession(state.langChosen ? state.lang : null);
    if (!canSpeak() && !Recognition && !(caps.stt && canRecord)) state.voiceOn = false; // no voice at all here
    applyLanguage();
    if (!state.open) return go(PAUSED);
    if (!state.greeted) return greet();
    resume();
  }

  function revealWidget() {
    root.hidden = false;
    boot();
  }
  css.addEventListener('load', revealWidget);
  css.addEventListener('error', revealWidget);

  applyLanguage();
  document.body.append(host);
  if (state.open) {
    root.classList.add('open');
    panel.hidden = false;
    launcher.hidden = true;
    launcher.setAttribute('aria-expanded', 'true');
  }

  // Register <db-assistant> custom element for declarative placement.
  if (typeof customElements !== 'undefined' && !customElements.get('db-assistant')) {
    class DbAssistantElement extends HTMLElement {
      connectedCallback() {
        const lang = this.getAttribute('lang');
        if (lang === 'am' || lang === 'en') setLanguage(lang);
        if (this.hasAttribute('simple')) setSimple(this.getAttribute('simple') === 'true');
      }
    }
    customElements.define('db-assistant', DbAssistantElement);
  }
})();
