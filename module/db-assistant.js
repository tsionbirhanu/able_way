// Mimi: the Ableway course tutor. A bilingual (Amharic / English), voice-first classroom tutor
// with a text chat that always works.
//
// Add it to any page with one tag:
//
//   <script src="../assistant/assistant.js" defer></script>
//
// Optional attributes:
//   data-api="https://host:port"     tutor API (server/app.py). Default: the server that serves this page,
//                                    or http://localhost:8001 when the page is opened from disk
//   data-handoff="https://host:port" channels server with /handoff (server/main.py). Default: http://localhost:8000
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
  // Settings come from the host's <db-assistant> tag:
  //   <db-assistant lang="am" api="https://tutor.example" content="/content.json"></db-assistant>
  // and, for older pages, from data- attributes on the script tag (data-lang, data-api, ...).
  const tag = document.querySelector('db-assistant');
  const setting = (name) => {
    if (tag && tag.hasAttribute(name)) return tag.getAttribute(name);
    const key = name.replace(/-([a-z])/g, (_, c) => c.toUpperCase());
    return script.dataset[key] !== undefined ? script.dataset[key] : null;
  };
  const moduleBase = new URL('.', script.src); // where db-assistant.css and i18n/ live
  const siteRoot = new URL('..', script.src); // citations are paths from the site root
  const API = (
    setting('api') ||
    (location.protocol.startsWith('http') ? location.origin : 'http://localhost:8001')
  ).replace(/\/$/, '');
  const config = {
    greetLang: setting('lang') === 'en' ? 'en' : 'am',
    autoWelcome: setting('auto-welcome') !== 'false',
    course: setting('course') || '',
    lesson: setting('lesson') || '',
    lessonSelector: setting('lesson-selector') || '',
    content: setting('content') || '',
    tts: ['server', 'browser'].includes(setting('tts')) ? setting('tts') : 'auto',
    stt: ['server', 'browser'].includes(setting('stt')) ? setting('stt') : 'auto',
  };
  const LANGUAGE_CODES = ['am', 'en']; // one i18n/<code>.json file each
  // Room for the chat beside the page: at 200% zoom or on a phone there is not, so Mimi starts small.
  const WIDE = () => window.innerWidth >= 1100;
  const PAGE = location.href.startsWith(siteRoot.href) ? location.href.slice(siteRoot.href.length).split(/[?#]/)[0] : '';

  const END_OF_TURN_MS = { en: 1500, am: 1900 }; // silence that ends the learner's turn; shorter pauses are kept
  const MAX_QUIET_RESTARTS = 8; // recogniser restarts without hearing anything before listening pauses (~1 min)
  const QUIET_LIMIT_MS = 60000;
  const ECHO_GAP_MS = 700; // after Mimi stops talking, before the microphone opens
  const SPEECH_LANG = { en: 'en-US', am: 'am-ET' };

  // ------------------------------------------------------------ text in both languages

  // ---- menu table start (server/warm_voice.mjs reads this block)
  //
  // THE MENU: one line per choice. Its words (what Mimi says, the button label) are in
  // module/i18n/<lang>.json under "menu.items.<action>". Add, remove or reorder lines here.
  //   action: lesson | language | question | person | jobs | chat
  const MENU = [
    { n: 1, action: 'lesson', icon: 'book' },
    { n: 2, action: 'language', icon: 'globe' },
    { n: 3, action: 'question', icon: 'chat' },
    { n: 4, action: 'person', icon: 'person' },
    { n: 5, action: 'jobs', icon: 'briefcase' },
    { n: 6, action: 'chat', icon: 'list' },
  ];

  // Fills {placeholders} in a sentence from a language file.
  const fmt = (template, values = {}) => String(template || '').replace(/\{(\w+)\}/g, (_, key) => (key in values ? values[key] : ''));

  // The whole menu as Mimi says it, from the language file.
  const MENU_TEXT = (lang) => {
    const m = STRINGS[lang].menu;
    const lines = MENU.map((item) => fmt(m.line, { say: m.items[item.action].say, n: item.n }));
    return [m.intro, ...lines, m.repeat].join(' ');
  };

  // The full introduction (shown) and the short one (spoken).
  const GREETING_TEXT = (lang) => STRINGS[lang].introSpoken; // spoken and shown: the same words
  // ---- menu table end

  // Every sentence the widget says or shows lives in module/i18n/<lang>.json (see loadLanguages).
  // Adding a language is one new file there, plus its code in LANGUAGE_CODES.
  const STRINGS = {};

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
    minus: '<path d="M5 12h14"/>',
    repeat: '<path d="M4 12a8 8 0 0 1 14-5.3L20 9"/><path d="M20 4v5h-5"/><path d="M20 12a8 8 0 0 1-14 5.3L4 15"/><path d="M4 20v-5h5"/>',
    book: '<path d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2z"/><path d="M4 19V5"/><path d="M9 7h6"/>',
    briefcase: '<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M9 7V5a2 2 0 0 1 2-2h2a2 2 0 0 1 2 2v2M3 13h18"/>',
    list: '<path d="M9 6h11M9 12h11M9 18h11"/><circle cx="4.5" cy="6" r="1"/><circle cx="4.5" cy="12" r="1"/><circle cx="4.5" cy="18" r="1"/>',
    globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/>',
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

  // A menu number said or typed on its own: "2", "two", "number two", "ሁለት", "ቁጥር ሁለት", "፪".
  // Only a whole short reply counts, so a question that merely contains "two" is still a question.
  const NUMBER_WORDS = [
    [0, /^(0|zero|oh|menu|ዜሮ|ሜኑ|ምርጫ|ምርጫዎች)$/],
    [1, /^(1|one|won|first|አንድ|አንደኛ|፩)$/],
    [2, /^(2|two|second|ሁለት|ሁለተኛ|፪)$/],
    [3, /^(3|three|third|ሶስት|ሦስት|ሶስተኛ|ሦስተኛ|፫)$/],
    [4, /^(4|four|fourth|አራት|አራተኛ|፬)$/],
    [5, /^(5|five|fifth|አምስት|አምስተኛ|፭)$/],
    [6, /^(6|six|sixth|ስድስት|ስድስተኛ|፮)$/],
  ];
  const NUMBER_FILLER = new Set(['number', 'press', 'say', 'option', 'choose', 'please', 'ቁጥር', 'እባክዎ']);
  function spokenNumber(text) {
    const words = text
      .toLowerCase()
      .replace(/[.,!?;:"“”'።፣፤፦]/g, ' ')
      .split(/\s+/)
      .filter((w) => w && !NUMBER_FILLER.has(w));
    if (words.length !== 1) return null;
    const match = NUMBER_WORDS.find(([, pattern]) => pattern.test(words[0]));
    return match ? match[0] : null;
  }

  // Under two letters and not a menu number: a cough, a click or the recogniser guessing.
  const isNoise = (text) => spokenNumber(text) === null && text.replace(/[^\p{L}\p{N}]/gu, '').length < 2;
  // Words that Mimi herself just said, picked up from the speakers: not the learner's turn.
  const plain = (text) => text.toLowerCase().replace(/[^\p{L}\p{N}]+/gu, ' ').trim();
  const isEcho = (text) => {
    const heard = plain(text);
    return heard.length >= 6 && spokenNumber(text) === null && plain(ctl.lastSpoken || '').includes(heard);
  };

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
    langChosen: session.get('lang-chosen') === true, // answered after the introduction
    greeted: session.get('greeted') === true,
    voiceOn: session.get('voice') == null ? config.autoWelcome : session.get('voice') === true,
    sessionId: session.get('session-id'),
    simple: store(localStorage, 'ableway-simple') === true,
    handsFree: store(localStorage, 'ableway-hands-free') !== false, // listen again after each answer
    bigText: store(localStorage, 'ableway-big-text') === true,
    minimized: session.get('minimized') == null ? !WIDE() : session.get('minimized') === true,
    open: session.get('open') == null ? WIDE() : session.get('open') === true,
    messages: session.get('messages') || [], // {role, text, lang, citations, provider, error, kind, translation}
    busy: false,
  };
  const t = () => STRINGS[state.lang];
  const caps = { server: false, tts: false, ttsCache: false, stt: false, sttAzure: false };

  // ------------------------------------------------------------ build the widget

  const host = el('div', { id: 'ableway-assistant' });
  const shadow = host.attachShadow({ mode: 'open' });
  const css = el('link', { rel: 'stylesheet', href: new URL('db-assistant.css', moduleBase).href });

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
  const settings = el('div', { class: 'settings' }, langGroup, simpleSwitch, clearButton);

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

  const inputLabel = el('label', { class: 'composer-label', for: 'ableway-input' }); // visible: a placeholder is not a label
  const input = el('textarea', { id: 'ableway-input', rows: '1', dir: 'auto', autocomplete: 'off', enterkeyhint: 'send' });
  const sendButton = el('button', { type: 'submit', class: 'icon-button send' }, icon('send'));
  const form = el('form', { class: 'composer', onsubmit: onSubmit }, inputLabel, input, sendButton);

  const panel = el(
    'section',
    { class: 'panel', role: 'dialog', 'aria-modal': 'false', 'aria-labelledby': 'ableway-title', hidden: true },
    el('div', { class: 'header' }, el('div', { class: 'header-text' }, title, subtitle, langBadge), voiceToggle, closeButton),
    settings,
    helpStrip,
    scroller,
    announcer,
    voiceBar,
    status,
    form,
  );

  // ------------------------------------------------------------ Mimi's card (the chat panel closed)
  //
  // Mimi talks and listens with the chat closed. The card shows, top to bottom: who she is, what
  // she and the learner just said (captions, so nothing is voice-only), what she is doing now, a
  // big "Press to talk" button, the numbered menu as real buttons, and the way into the full chat.
  // Every control is a real button with a visible name; nothing depends on colour, sound or a mouse.

  function switchButton(onclick) {
    const text = el('span');
    const button = el('button', { type: 'button', class: 'switch', role: 'switch', onclick }, el('span', { class: 'track', 'aria-hidden': 'true' }), text);
    return [button, text];
  }

  const avatar = el('span', { class: 'avatar', 'aria-hidden': 'true', text: 'M' });
  const miniTitle = el('h2', { class: 'mini-title', id: 'ableway-mini-title' });
  const [bigTextSwitch, bigTextText] = switchButton(() => setBigText(!state.bigText));
  const minimizeButton = el('button', { type: 'button', class: 'icon-button mini-min', onclick: () => setMinimized(true) }, icon('minus'));
  const miniHeader = el('div', { class: 'mini-header' }, avatar, miniTitle, minimizeButton);
  const miniOptions = el('div', { class: 'mini-options' }, bigTextSwitch);

  const capMimiWho = el('span', { class: 'cap-who' });
  const capMimiText = el('span', { class: 'cap-text', dir: 'auto' });
  const capMimi = el('p', { class: 'cap cap-mimi', hidden: true }, capMimiWho, capMimiText);
  const capUserWho = el('span', { class: 'cap-who' });
  const capUserText = el('span', { class: 'cap-text', dir: 'auto' });
  const capUser = el('p', { class: 'cap cap-user', hidden: true }, capUserWho, capUserText);
  // Not a live region: the hidden log already announces every message once.
  const captions = el('div', { class: 'captions' }, capUser, capMimi);

  // Press to talk: the learner decides when Mimi listens. "Listen automatically" keeps the
  // hands-free conversation for learners who cannot easily press a button.
  const talkLabel = el('span');
  const talkMic = el('span', { class: 'talk-mic', 'aria-hidden': 'true' });
  const talkMain = el('button', { type: 'button', class: 'talk', 'aria-pressed': 'false', onclick: onTalk }, talkMic, talkLabel);
  const [handsFreeSwitch, handsFreeText] = switchButton(() => setHandsFree(!state.handsFree));
  const talkRow = el('div', { class: 'talk-row' }, talkMain, handsFreeSwitch);

  // The menu as buttons: the same numbers Mimi says, for learners who cannot speak or be heard.
  const menuTitle = el('h3', { class: 'menu-title', id: 'ableway-menu-title' });
  const menuGrid = el('div', { class: 'menu-grid', role: 'group', 'aria-labelledby': 'ableway-menu-title' });
  const menuBox = el('div', { class: 'menu' }, menuTitle, menuGrid);
  const MENU_ICONS = ['book', 'chat', 'briefcase', 'person', 'list', 'globe'];

  // Voice bar, notices, talk button and menu move together between the card and the chat panel.
  const controls = el('div', { class: 'controls' }, voiceBar, status, talkRow, menuBox);

  const miniVoiceText = el('span');
  const miniVoice = el('button', { type: 'button', class: 'mini-voice', 'aria-pressed': 'false', onclick: () => setVoice(!state.voiceOn) }, miniVoiceText);
  const mini = el(
    'div',
    { class: 'mini', role: 'group', 'aria-labelledby': 'ableway-mini-title' },
    miniHeader,
    captions,
    miniOptions,
    el('div', { class: 'mini-actions' }, miniVoice, launcher),
  );

  // Minimised: one button, so the card never covers the page (at 200% zoom, on a small phone).
  const pillState = el('span', { class: 'pill-state' });
  const pillText = el('span');
  const pill = el('button', { type: 'button', class: 'pill', onclick: () => setMinimized(false) }, el('span', { class: 'avatar small', 'aria-hidden': 'true', text: 'M' }), pillText, pillState);

  function caption(who, text, lang) {
    const [line, whoEl, textEl] = who === 'user' ? [capUser, capUserWho, capUserText] : [capMimi, capMimiWho, capMimiText];
    const clean = (text || '').replace(/\s*\[\d+\]/g, '').trim();
    line.hidden = !clean;
    whoEl.textContent = `${who === 'user' ? t().you : t().tutor}: `;
    textEl.textContent = clean;
    textEl.lang = lang || scriptLang(clean);
    captions.scrollTop = captions.scrollHeight;
  }

  // <aside> gives screen-reader users a landmark to jump to from anywhere on the page.
  const root = el('aside', { class: 'root', hidden: true }, pill, mini, panel);

  // The controls sit wherever the learner is looking: in the chat when it is open, else the card.
  function placeVoiceBar() {
    // "Larger text" and "Listen automatically" go with the learner too: the co-designer could not
    // find them once the chat was open, because they stayed on the (hidden) card.
    if (state.open) {
      panel.insertBefore(controls, form);
      settings.insertBefore(bigTextSwitch, clearButton);
      settings.insertBefore(handsFreeSwitch, clearButton);
    } else {
      mini.insertBefore(controls, miniOptions);
      miniOptions.append(bigTextSwitch);
      talkRow.append(handsFreeSwitch);
    }
    mini.hidden = state.open || state.minimized;
    pill.hidden = state.open || !state.minimized;
    root.classList.toggle('big', state.bigText);
  }

  function renderMenu() {
    const s = t();
    menuTitle.textContent = s.menuTitle;
    const item = (n, label, iconName, lang) =>
      el('button', { type: 'button', class: 'menu-item', lang, onclick: () => pickFromMenu(n) },
        el('span', { class: 'num', text: String(n) }),
        el('span', { class: 'menu-icon', 'aria-hidden': 'true' }, icon(iconName)),
        el('span', { class: 'menu-label', text: label }));
    menuGrid.replaceChildren(
      ...MENU.map((m) => item(m.n, t().menu.items[m.action].button, m.icon, m.action === 'language' ? (state.lang === 'am' ? 'en' : 'am') : state.lang)),
      item(0, s.repeatMenu, 'repeat', state.lang),
    );
  }

  function renderTalk() {
    const s = t();
    const on = (ctl.state === LISTENING || ctl.state === CHOOSING) && !!ctl.listener && ctl.listener.active;
    talkMain.setAttribute('aria-pressed', String(on));
    talkMain.dataset.on = String(on);
    talkLabel.textContent = on ? s.talkStop : s.talk;
    talkMic.replaceChildren(icon('mic'));
    talkMain.hidden = !state.voiceOn || !ctl.canListen;
    handsFreeSwitch.hidden = !state.voiceOn;
    handsFreeText.textContent = s.handsFree;
    handsFreeSwitch.setAttribute('aria-checked', String(state.handsFree));
    bigTextText.textContent = s.bigText;
    bigTextSwitch.setAttribute('aria-checked', String(state.bigText));
    minimizeButton.setAttribute('aria-label', s.minimize);
    pillText.textContent = s.restore;
    pillState.textContent = voiceState.textContent ? ` · ${voiceState.textContent}` : '';
  }
  // The ring that marks a cited lesson section (see showInLesson).
  const ring = el('div', { class: 'source-ring', 'aria-hidden': 'true', hidden: true });
  shadow.append(css, root, ring);

  // ------------------------------------------------------------ rendering

  function applyLanguage() {
    const s = t();
    root.lang = state.lang;
    root.setAttribute('aria-label', s.title);
    launcherText.textContent = s.showPanel;
    miniTitle.textContent = s.miniLabel;
    renderMenu();
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
    miniVoiceText.textContent = state.voiceOn ? t().voiceOff : t().voiceOn;
    miniVoice.setAttribute('aria-pressed', String(!state.voiceOn));
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
    // Sample questions only once the language is settled: before that, the introduction and its two
    // language buttons are the only thing to look at.
    if (state.langChosen && !state.messages.some((m) => m.role === 'user' && m.kind !== 'choice')) {
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
    if (message.translation) bubble.append(el('p', { class: 'translation', lang: scriptLang(message.translation), dir: 'auto', text: message.translation }));
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
    if (message.offerPerson) actions.append(el('button', { type: 'button', class: 'chip', lang: state.lang, text: s.talkToPerson, onclick: () => escalateToHuman() }));
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
    } else if (url.hash) {
      link.addEventListener('click', (event) => {
        if (showInLesson(decodeURIComponent(url.hash.slice(1)), citation.title)) event.preventDefault();
      });
    }
    return link;
  }

  // "Where did this answer come from?" A source on this page: scroll the lesson to that section and
  // ring it, so the learner (and a judge) can read the exact words the answer is based on. The ring
  // is drawn by the widget over the page; the host's own elements are not changed.
  let ringTimer = null;
  function sectionRect(anchor) {
    const heading = anchor.closest('h1, h2, h3, h4, h5, h6') || anchor;
    let rect = heading.getBoundingClientRect();
    let top = rect.top, left = rect.left, right = rect.right, bottom = rect.bottom;
    // The heading and what follows it, up to the next heading of the same or a higher level.
    const level = /^H(\d)$/.test(heading.tagName) ? Number(heading.tagName[1]) : 7;
    for (let node = heading.nextElementSibling; node; node = node.nextElementSibling) {
      const tag = /^H(\d)$/.exec(node.tagName);
      if (tag && Number(tag[1]) <= level) break;
      rect = node.getBoundingClientRect();
      if (!rect.height) continue;
      top = Math.min(top, rect.top); left = Math.min(left, rect.left);
      right = Math.max(right, rect.right); bottom = Math.max(bottom, rect.bottom);
      if (bottom - top > window.innerHeight * 0.8) break;
    }
    return { top, left, width: right - left, height: bottom - top };
  }
  function showInLesson(id, title) {
    const anchor = document.getElementById(id);
    if (!anchor) return false;
    const heading = anchor.closest('h1, h2, h3, h4, h5, h6') || anchor;
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    heading.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' });
    const place = () => {
      const r = sectionRect(anchor);
      Object.assign(ring.style, { top: `${r.top - 8}px`, left: `${r.left - 8}px`, width: `${r.width + 16}px`, height: `${r.height + 16}px` });
    };
    ring.hidden = false;
    place();
    clearInterval(ringTimer);
    let ticks = 0;
    ringTimer = setInterval(() => {
      place();
      if (++ticks > 80) { // about eight seconds
        clearInterval(ringTimer);
        ring.hidden = true;
      }
    }, 100);
    announcer.append(el('p', { lang: state.lang, text: `${t().shownInLesson}: ${title}` }));
    return true;
  }

  function scrollToEnd() {
    scroller.scrollTop = scroller.scrollHeight;
  }

  function announce(message) {
    const s = STRINGS[state.lang];
    const who = message.role === 'user' ? s.you : s.tutor;
    const count = message.citations && message.citations.length ? ` ${fmt(message.citations.length === 1 ? s.sourceCountOne : s.sourceCount, { n: message.citations.length })}` : '';
    const line = el('p', { lang: message.lang, text: `${who}: ${message.text.replace(/\[\d+\]/g, '')}${count}` });
    announcer.append(line);
    while (announcer.children.length > 4) announcer.firstChild.remove();
  }

  function setStatus(text) {
    status.textContent = text || '';
  }

  // While the learner speaks, their words so far, as the last bubble of the chat. Hidden from screen
  // readers (it changes with every word); the finished sentence is announced as a message.
  const liveWho = el('span', { class: 'who' });
  const liveText = el('p', { dir: 'auto' });
  const liveBubble = el('li', { class: 'msg msg-user msg-live', 'aria-hidden': 'true' }, liveWho, el('div', { class: 'bubble' }, liveText));
  function showLive(text) {
    if (!text) return liveBubble.remove();
    liveWho.textContent = `${t().you} …`;
    liveText.textContent = text;
    liveText.lang = scriptLang(text);
    if (liveBubble.parentNode !== list) list.append(liveBubble);
    scrollToEnd();
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
    const FEMALE = /female|woman|mekdes|መቅደስ|samantha|victoria|karen|moira|tessa|fiona|serena|susan|allison|\bava\b|zira|aria|jenny|michelle|sonia|libby|natasha|emma|clara|salli|joanna|kendra|kimberly|ivy|google us english|google uk english female/i;
    const MALE = /\bmale\b|\bman\b|ameha|አምሀ|david|mark|guy|daniel|\balex\b|fred|rishi|george|ryan|thomas|aaron|arthur|oliver|james|christopher|eric|roger|brian|google uk english male/i;

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
        let finish = (fn, value) => {
          if (done) return;
          done = true;
          cancelCurrent = null;
          audio.onended = audio.onerror = audio.onloadedmetadata = null;
          fn(value);
        };
        // If the clip never reports its end (seen on some phones), stop waiting a little after its length.
        let guard = setTimeout(() => finish(resolve, 'done'), 30000);
        const settleOnce = finish;
        finish = (fn, value) => { clearTimeout(guard); settleOnce(fn, value); };
        audio.onloadedmetadata = () => {
          if (Number.isFinite(audio.duration) && audio.duration > 0) {
            clearTimeout(guard);
            guard = setTimeout(() => finish(resolve, 'done'), audio.duration * 1000 + 3000);
          }
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
      // A fixed phrase (greeting, menu, confirmation) is one request, so the server records it
      // whole and replays it with no quota and no browser voice. Splitting it once made Mimi start
      // the greeting, then stop when the second piece needed a new request the quota refused.
      const parts = cache ? [text] : chunks(text);
      let next = fetchAudio(parts[0], lang, cache);
      for (let i = 0; i < parts.length; i++) {
        let url;
        try {
          url = await next;
        } catch (e) {
          if (i === 0) throw e;
          // The server voice ran out mid-answer (usually its quota). Finish with the browser's voice
          // for this language rather than stopping; if it has none, the rest is on screen.
          serverDownUntil = Date.now() + 120000;
          if (my !== token) return 'stopped';
          try {
            return await speakBrowser(parts.slice(i).join(' '), lang, my);
          } catch {
            return 'partial';
          }
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
        // Browsers sometimes drop an utterance without any event (Chrome right after cancel(), Android
        // with an online voice), which left Mimi "speaking" in silence and never listening. A watchdog
        // per sentence: if nothing is playing after a moment, or the sentence runs far past its
        // length, move on as if it had ended.
        let watchdog = null;
        let anyStarted = false;
        const clearWatch = () => clearInterval(watchdog);
        const next = () => {
          clearWatch();
          if (my !== token) return settle(resolve, 'stopped');
          if (i >= parts.length) return settle(resolve, 'done');
          const sentence = parts[i++];
          const utterance = new SpeechSynthesisUtterance(sentence);
          utterance.voice = voice;
          utterance.lang = voice.lang;
          utterance.rate = 0.95;
          utterance.pitch = 1.05;
          let ended = false;
          const end = () => {
            if (ended) return;
            ended = true;
            next();
          };
          utterance.onstart = () => { anyStarted = true; };
          utterance.onend = end;
          utterance.onerror = (event) => {
            if (ended) return; // the watchdog already moved on (its cancel() fires this)
            ended = true;
            clearWatch();
            if (event.error === 'not-allowed') settle(reject, Object.assign(new Error('blocked'), { code: 'blocked' }));
            else if (event.error === 'interrupted' || event.error === 'canceled') settle(resolve, 'stopped');
            else next();
          };
          const begun = Date.now();
          const longest = 4000 + sentence.length * 150;
          watchdog = setInterval(() => {
            if (ended || my !== token) return clearWatch();
            const idle = !synth.speaking && !synth.pending;
            if ((idle && Date.now() - begun > 1500) || Date.now() - begun > longest) {
              synth.cancel();
              ended = true;
              clearWatch();
              // Nothing has played at all: this voice is not working, so do not wait on every sentence.
              if (!anyStarted) return settle(resolve, 'done');
              next();
            }
          }, 500);
          synth.speak(utterance);
        };
        synth.cancel();
        setTimeout(next, 60); // speak() straight after cancel() is sometimes dropped
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
      // A natural (online, neural) voice in the browser for this language, such as Edge's Amharic
      // መቅደስ (Mekdes) and English Ava: use it first. No quota, starts at once, and the same voice for
      // every answer. Otherwise the server voice, then any browser voice.
      if (synth && config.tts !== 'server') {
        const natural = pickVoice(await voices(), lang);
        if (my !== token) return 'stopped';
        if (natural && /natural|neural|online/i.test(natural.name)) return speakBrowser(say, lang, my);
      }
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
    if (browser && (lang === 'en' || isChromium)) return 'browser'; // live words on screen
    if (server) return 'server';
    return browser ? 'browser' : null;
  }

  // The browser's own recogniser, kept running across its automatic stops. A turn ends after
  // END_OF_TURN_MS of silence, not at the recogniser's first "final" result, so a learner can pause
  // to think mid-sentence without being cut off.
  function bestAlternative(result) {
    for (let i = 0; i < result.length; i++) {
      if (spokenNumber(result[i].transcript) !== null) return result[i].transcript;
    }
    return result[0].transcript;
  }

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
      rec.maxAlternatives = 3;
      rec.onresult = (event) => {
        if (my !== generation) return;
        current = Array.from(event.results, bestAlternative).join(' ');
        quietRestarts = networkErrors = 0;
        handlers.onInterim(text());
        clearTimeout(timer);
        timer = setTimeout(finish, END_OF_TURN_MS[lang]);
      };
      rec.onerror = (event) => {
        if (my === generation) lastError = event.error;
      };
      // A recogniser that never starts (no event at all) used to leave "Listening…" on screen with
      // nothing listening. Give it a few seconds, then switch to the other way of listening.
      let started = false;
      rec.onstart = () => { started = true; };
      setTimeout(() => {
        if (my === generation && active && !started) fail('failed');
      }, 5000);
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
    [GREETING_STATE]: [CHOOSING, LISTENING, SPEAKING, PROCESSING, TEXT, PAUSED, ERROR], // the greeting ends by listening
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
      case PAUSED:
        if (ctl.pauseReason === 'press') { label = s.sPress; iconName = 'mic'; break; } // the big button starts listening
        if (ctl.pauseReason === 'blocked') { label = s.speechBlocked; iconName = 'speaker'; break; } // the browser holds sound until a tap
        label = ctl.pauseReason === 'typing' ? s.sTyping : s.sPaused; iconName = 'pause'; action = ['resume', s.aResume]; break;
      default: label = s.sError; iconName = 'alert'; action = ['resume', s.retry];
    }
    if (ctl.needsUnlock) action = ['unlock', s.aUnlock];
    voiceBar.dataset.state = ctl.state;
    voiceState.textContent = label;
    voiceIcon.replaceChildren(icon(iconName));
    voiceAction.hidden = !action;
    renderTalk();
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
        caption('user', text);
        showLive(text);
      }
    },
    onFinal(text) {
      if (!listeningState()) return;
      input.value = '';
      resizeInput();
      if (isNoise(text) || isEcho(text)) {
        caption('user', '');
        showLive('');
        return listen();
      }
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
      if (text && !isNoise(text) && !isEcho(text)) return takeTurn(text, 'voice');
      go(state.langChosen ? LISTENING : CHOOSING);
      listen();
    },
    onError(code) {
      if (code === 'unsupported' || code === 'network' || code === 'failed') failedEngines.add(`browser-${state.lang}`);
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
    if (!state.voiceOn || !ctl.canListen || document.hidden || state.busy) return;
    // The screen says "listening" from here on, so the microphone must really open. A speech that
    // never reported its end must not keep it shut.
    if (Speaker.busy()) Speaker.stop();
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
  async function say(text, lang, { cache = false, speakState = SPEAKING, button = null, captionText = null } = {}) {
    const my = ++ctl.speech;
    ctl.lastSpoken = `${ctl.lastSpoken || ''} ${text}`.slice(-1500); // for the echo check
    caption('mimi', captionText || text, captionText ? null : lang);
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
      } else if (result === 'novoice') setStatus(fmt(t().noVoice, { voice: t().languageNames[lang] }));
      else setStatus(t().speechUnavailable);
    }
    if (my !== ctl.speech) return 'superseded';
    if (result === 'partial') setStatus(STRINGS[lang] ? STRINGS[lang].partialSpoken : t().partialSpoken);
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
    if (state.voiceOn && ctl.canListen && !state.handsFree) {
      // Press-to-talk mode: wait for the learner to press the button (or a number key).
      go(PAUSED);
      ctl.pauseReason = 'press';
      return renderVoiceBar();
    }
    if (!state.langChosen) go(CHOOSING);
    else if (state.voiceOn && ctl.canListen) go(LISTENING);
    else return go(TEXT);
    setTimeout(listen, ECHO_GAP_MS);
  }

  // The big button: start listening now (stopping Mimi if she is talking), or stop listening.
  function onTalk() {
    Speaker.unlock();
    if ((ctl.state === LISTENING || ctl.state === CHOOSING) && ctl.listener && ctl.listener.active) {
      go(PAUSED);
      ctl.pauseReason = 'press';
      return renderVoiceBar();
    }
    if (state.busy) return;
    ++ctl.speech; // any speech in progress no longer moves the conversation on
    Speaker.stop();
    ctl.canListen = true;
    go(state.langChosen ? LISTENING : CHOOSING);
    listen();
    renderVoiceBar();
  }

  function pickFromMenu(number) {
    Speaker.unlock();
    if (state.busy) return;
    caption('user', String(number));
    ++ctl.speech;
    Speaker.stop();
    if (!state.langChosen) return chooseLanguage(number === 1 ? 'am' : 'en');
    runMenu(number);
  }

  function setHandsFree(on) {
    state.handsFree = on;
    store(localStorage, 'ableway-hands-free', on);
    renderTalk();
    if (on && ctl.state === PAUSED && ctl.pauseReason === 'press') resume();
  }

  function setBigText(on) {
    state.bigText = on;
    store(localStorage, 'ableway-big-text', on);
    root.classList.toggle('big', on);
    renderTalk();
  }

  function setMinimized(on) {
    state.minimized = on;
    session.set('minimized', on);
    placeVoiceBar();
    (on ? pill : talkMain.hidden ? launcher : talkMain).focus();
  }

  function resume() {
    if (state.busy) return;
    if (!state.voiceOn) return go(state.langChosen ? TEXT : CHOOSING);
    go(state.langChosen ? LISTENING : CHOOSING);
    listen();
  }

  // ------------------------------------------------------------ greeting and language

  // What Mimi says first: welcome and the whole menu in the page language, then (on an Amharic page)
  // one sentence in English, so a learner who does not understand Amharic still knows what to press.
  // Spoken: a short introduction (about five seconds, so it does not talk over a screen reader for
  // long), then one sentence in the other language. Shown in the chat: the full introduction.
  // Co-designer test: hearing one text and reading another was confusing, and so was a greeting that
  // switched voice and language halfway. Mimi now says the greeting in one language, and the chat
  // shows exactly the words she says (which already tell the learner how to change language).
  async function sayGreeting() {
    const lang = state.lang;
    return say(GREETING_TEXT(lang), lang, { cache: true, speakState: GREETING_STATE });
  }

  async function greet() {
    if (!state.greeted) {
      state.greeted = true;
      session.set('greeted', true);
      addMessage({ role: 'assistant', kind: 'greeting', text: GREETING_TEXT(state.lang), lang: state.lang, citations: [] });
    }
    if (!state.voiceOn || !canSpeak()) return afterSpeech();
    const result = await sayGreeting();
    if (result === 'superseded') return;
    if (result === 'blocked') {
      // The browser refused sound until the learner taps or presses a key (autoplay rules). Say so
      // plainly; the first tap or key press anywhere plays the greeting (onGesture), then she listens.
      ctl.greetPending = true;
      ctl.needsUnlock = true;
      go(PAUSED);
      ctl.pauseReason = 'blocked';
      setStatus('');
      return renderVoiceBar();
    }
    afterSpeech();
  }

  // The first click or key press anywhere on the page lets the browser play sound; if the
  // greeting was held back, it is spoken then.
  function onGesture(event) {
    Speaker.unlock();
    if (mic.ctx && mic.ctx.state === 'suspended') mic.ctx.resume().catch(() => {});
    const wasBlocked = ctl.needsUnlock;
    if (wasBlocked) ctl.unlockedAt = Date.now();
    ctl.needsUnlock = false;
    renderVoiceBar();
    if (wasBlocked) setStatus('');
    if (ctl.greetPending && state.voiceOn) {
      ctl.greetPending = false;
      setTimeout(async () => {
        // A menu number or button pressed as the first gesture already chose what to do.
        if (state.busy || ctl.state !== PAUSED || ctl.pauseReason !== 'blocked') return;
        const result = await sayGreeting();
        if (result !== 'superseded') afterSpeech();
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
    setLanguage(lang);
    const confirm = STRINGS[lang].confirm;
    addMessage({ role: 'assistant', kind: 'confirm', text: confirm, lang, citations: [] });
    if (state.busy) return;
    const my = ++ctl.turn;
    if (state.voiceOn) {
      const result = await say(confirm, lang, { cache: true });
      if (result === 'superseded' || my !== ctl.turn) return;
    }
    afterSpeech();
  }

  // ------------------------------------------------------------ turns

  const menuItem = (number) => MENU.find((m) => m.n === number);
  // "Yes, continue" to "Shall we continue in Amharic?"
  const YES = /^(yes|yeah|ok|okay|sure|አዎ|እሺ|አዎን|ይሁን|ቀጥል|ቀጥዪ|እንቀጥል)[.!። ]*$/i;

  function takeTurn(text, source) {
    const said = text.trim();
    if (!said || state.busy) return;
    ctl.lastSpoken = '';
    caption('user', said);
    const number = spokenNumber(said);
    if (!state.langChosen) {
      const choice = number === 1 ? 'am' : number === 2 ? 'en' : languageChoice(said) || (YES.test(said) ? state.lang : null);
      // The answer to the language question is shown, but not sent to the AI as part of the conversation.
      addMessage({ role: 'user', text: said, lang: scriptLang(said), kind: choice ? 'choice' : undefined });
      input.value = '';
      resizeInput();
      if (choice) return chooseLanguage(choice);
      setLanguage(scriptLang(said)); // a question straight away: help in the language it was asked in
      return askTutor(said, { shown: true });
    }
    if (number !== null && (number === 0 || menuItem(number))) {
      addMessage({ role: 'user', text: said, lang: scriptLang(said) });
      input.value = '';
      resizeInput();
      return runMenu(number);
    }
    return askTutor(said);
  }

  // ------------------------------------------------------------ the services menu

  async function speakMenu() {
    if (state.busy) return;
    const text = MENU_TEXT(state.lang);
    addMessage({ role: 'assistant', kind: 'menu', text, lang: state.lang, citations: [] });
    if (state.voiceOn) {
      const result = await say(text, state.lang, { cache: true });
      if (result === 'superseded') return;
    }
    afterSpeech();
  }

  async function promptQuestion() {
    const text = t().askNow;
    addMessage({ role: 'assistant', kind: 'menu', text, lang: state.lang, citations: [] });
    if (state.voiceOn) {
      const result = await say(text, state.lang, { cache: true });
      if (result === 'superseded') return;
    } else if (state.open) input.focus();
    afterSpeech();
  }

  function runMenu(number) {
    if (state.busy) return;
    const item = menuItem(number);
    switch (item && item.action) {
      case 'lesson': return askTutor('', { intent: 'lesson_intro' });
      case 'language': return chooseLanguage(state.lang === 'am' ? 'en' : 'am');
      case 'question': return promptQuestion();
      case 'person': return escalateToHuman();
      case 'jobs': return askTutor(t().jobsQuestion);
      case 'chat': return setOpen(true); // the conversation carries on; the learner now also sees it
      default: return speakMenu(); // 0, or a number no longer on the menu
    }
  }

  // Number keys choose from the menu, from anywhere on the page, as long as Mimi is in use and the
  // learner is not typing in a field. (A screen reader in browse mode keeps these keys for itself;
  // its users press them after switching to focus mode, or simply say the number.)
  document.addEventListener('keydown', (event) => {
    if (event.ctrlKey || event.altKey || event.metaKey || event.isComposing || !/^[0-9]$/.test(event.key)) return;
    const target = event.composedPath()[0];
    if (target && (target.isContentEditable || /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName))) return;
    if (!state.greeted || state.busy || (!state.voiceOn && !state.open)) return;
    // WCAG 2.1.4: single-key shortcuts only while Mimi has focus, or before anything on the page has
    // focus (just after it opens). Typing elsewhere on the host page never triggers them.
    const active = document.activeElement;
    if (!event.composedPath().includes(host) && active && active !== document.body) return;
    const number = Number(event.key);
    if (!state.langChosen) {
      if (number !== 1 && number !== 2) return;
      event.preventDefault();
      caption('user', event.key);
      chooseLanguage(number === 1 ? 'am' : 'en');
      return;
    }
    if (number !== 0 && !menuItem(number)) return;
    event.preventDefault();
    Speaker.stop();
    caption('user', event.key);
    runMenu(number);
  });

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
        // Not found in the course: offer a person straight away, in words and as a button.
        offerPerson: data.grounded === false && !data.switch_lang && intent !== 'lesson_intro',
      };
    } catch {
      ctl.errors++;
      return { role: 'assistant', text: t().error, lang: state.lang, citations: [], error: true };
    } finally {
      typing.remove();
    }
  }

  async function askTutor(question, { intent = null, shown = false } = {}) {
    if (state.busy) return;
    state.busy = true;
    setBusy(true);
    const my = ++ctl.turn;
    Speaker.stop();
    go(PROCESSING);
    const history = state.messages
      .filter((m) => !m.error && !['greeting', 'confirm', 'welcome', 'menu', 'choice'].includes(m.kind))
      .slice(-6)
      .map((m) => ({ role: m.role, content: m.text }));
    if (question) {
      // Host contract event, for pages that embed the assistant.
      document.dispatchEvent(new CustomEvent('db-assistant:question', {
        bubbles: true, composed: true, detail: { text: question, language: state.lang },
      }));
      if (!shown) addMessage({ role: 'user', text: question, lang: scriptLang(question) });
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
    if (reply.offerPerson) {
      const person = MENU.find((m) => m.action === 'person');
      reply.text = `${reply.text}\n\n${fmt(STRINGS[reply.lang || state.lang].offerPerson, { n: person ? person.n : '' })}`;
    }
    addMessage(reply);
    if (!state.voiceOn) caption('mimi', reply.text, reply.lang || state.lang);
    if (reply.error && ctl.errors >= 2) {
      go(ERROR); // the service is down: do not keep listening and failing
      return;
    }
    if (state.voiceOn) {
      const hint = !state.open && reply.citations && reply.citations.length ? ` ${fmt(STRINGS[reply.lang || state.lang].sourcesHint, { n: (MENU.find((m) => m.action === 'chat') || { n: 0 }).n })}` : '';
      const result = await say(reply.text + hint, reply.lang || state.lang, { cache: !!reply.switchLang });
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
    // Open the tab now, while the click still counts as the learner's action; browsers block a tab
    // opened later. After a spoken "talk to a person" there is no click: the link is in the chat.
    let tab = null;
    try {
      tab = window.open('', '_blank');
    } catch {
      tab = null;
    }
    // The conversation so far goes with the ticket, so the tutor does not ask the learner to repeat it.
    const conversation = state.messages
      .filter((m) => !m.error && m.kind !== 'choice')
      .slice(-12)
      .map((m) => ({ role: m.role, text: m.text }));
    try {
      const data = await postJSON('/api/v1/escalations', { conversation, language: state.lang }, 15000);
      if (!data.chatUrl) throw new Error('no chat');
      setStatus('');
      document.dispatchEvent(new CustomEvent('db-assistant:escalated', {
        bubbles: true, composed: true, detail: { ticketId: data.ticketId },
      }));
      if (tab) {
        tab.opener = null;
        tab.location.href = data.chatUrl;
      }
      const message = { role: 'assistant', kind: 'menu', text: s.escalated, lang: state.lang, citations: [{ n: 1, title: s.escalateLink, url: data.chatUrl }] };
      addMessage(message);
      if (state.voiceOn) {
        const result = await say(message.text, state.lang);
        if (result === 'superseded') return;
      }
      afterSpeech();
    } catch {
      if (tab) tab.close();
      setStatus(s.escalateFailed);
      addMessage({ role: 'assistant', text: s.escalateFailed, lang: state.lang, citations: [], error: true });
      if (state.voiceOn) await say(s.escalateFailed, state.lang);
      afterSpeech();
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
    launcher.setAttribute('aria-expanded', String(open));
    placeVoiceBar();
    if (open) {
      scrollToEnd();
      input.focus();
      if (!state.greeted) greet();
      else if (!Speaker.busy() && !state.busy && !listeningState()) resume();
    } else {
      // Closing the chat only hides it: Mimi keeps talking and listening unless her voice is off.
      if (!state.voiceOn && !state.busy) go(PAUSED);
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
      caps.sttAzure = !!(health.speech && /azure/i.test(health.speech.stt_detail || ''));
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
    if (!state.open && !config.autoWelcome && !state.greeted) return go(PAUSED);
    if (!state.greeted) return greet();
    resume();
  }

  function revealWidget() {
    root.hidden = false;
    boot();
  }
  // Shown once both the stylesheet and the language files have arrived (see the start, below).
  const cssReady = new Promise((resolve) => {
    css.addEventListener('load', resolve);
    css.addEventListener('error', resolve);
  });

  // Language files: next to this script, or from the tutor server when the page is opened from disk
  // (browsers do not let file:// pages fetch neighbouring files).
  async function loadLanguages() {
    await Promise.all(LANGUAGE_CODES.map(async (code) => {
      for (const url of [new URL(`i18n/${code}.json`, moduleBase).href, `${API}/module/i18n/${code}.json`]) {
        try {
          const response = await fetch(url);
          if (response.ok) {
            STRINGS[code] = await response.json();
            return;
          }
        } catch {
          /* try the next place */
        }
      }
      throw new Error(`Mimi: could not load the ${code} language file`);
    }));
  }

  // The host's own lessons (the content="" attribute): sent once to the tutor to be indexed, so Mimi
  // answers from them too. Format: [{ "title", "url", "text" }] or { "chunks": [...] }.
  async function sendHostContent() {
    if (!config.content) return;
    try {
      const data = await (await fetch(new URL(config.content, location.href))).json();
      const chunks = Array.isArray(data) ? data : data.chunks || data.lessons || [];
      if (chunks.length) await postJSON('/api/v1/content', { chunks }, 15000);
    } catch {
      /* the course pages are still indexed; the host's extra content is optional */
    }
  }

  // <db-assistant> is the tag a host places. Its attributes are read above; changing lang later
  // switches Mimi's language.
  if (typeof customElements !== 'undefined' && !customElements.get('db-assistant')) {
    customElements.define('db-assistant', class extends HTMLElement {
      static get observedAttributes() {
        return ['lang'];
      }

      attributeChangedCallback(name, before, after) {
        if (ctl.booted && before !== null && after !== before && STRINGS[after]) chooseLanguage(after);
      }
    });
  }

  // Start: the (still hidden) widget goes on the page at once, so its stylesheet downloads at the same
  // time as the language files. On a slow connection each round trip counts.
  document.body.append(host);
  Promise.all([loadLanguages(), cssReady]).then(() => {
    applyLanguage();
    placeVoiceBar();
    if (state.open) {
      root.classList.add('open');
      panel.hidden = false;
      launcher.setAttribute('aria-expanded', 'true');
    }
    revealWidget();
    sendHostContent();
  }, (error) => console.error(error));
})();
