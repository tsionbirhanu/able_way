// Ableway course tutor: a chat widget in Amharic and English, with voice in and out.
//
// Add it to any page with one tag:
//
//   <script src="../assistant/assistant.js" defer></script>
//
// Optional attribute: data-api="https://host:port" when the tutor API (server/app.py) is not on
// http://localhost:8000.
//
// Unlike assets/js/static-page.js, which deliberately keeps the application's accessibility
// defects, this widget is new work and is built to be accessible on its own: it lives in a
// shadow root so the page's styles cannot break it, every control is a real button with a name,
// new messages are announced through a live region, and each message sets its own language and
// text direction.

(() => {
  'use strict';

  const script = document.currentScript;
  const siteRoot = new URL('..', script.src); // citations are paths from the site root
  const API = (
    script.dataset.api ||
    (location.protocol.startsWith('http') && location.port === '8000' ? location.origin : 'http://localhost:8000')
  ).replace(/\/$/, '');

  // ------------------------------------------------------------ text in both languages

  const STRINGS = {
    en: {
      launcher: 'Ask the tutor',
      title: 'Course tutor',
      subtitle: 'Answers come only from your course pages.',
      close: 'Close tutor',
      language: 'Language',
      simple: 'Simple words',
      clear: 'Clear chat',
      transcript: 'Conversation with the tutor',
      inputLabel: 'Your question',
      placeholder: 'Type your question…',
      send: 'Send',
      mic: 'Speak your question',
      micStop: 'Stop listening',
      listening: 'Listening… speak now.',
      heard: 'Stopped listening. Check your question, then press Send.',
      thinking: 'The tutor is writing an answer…',
      you: 'You',
      tutor: 'Tutor',
      sources: 'Sources',
      source: 'Source',
      sourceCount: (n) => (n === 1 ? '1 source is listed below.' : `${n} sources are listed below.`),
      newTab: 'opens in a new tab',
      read: 'Read aloud',
      stopRead: 'Stop reading',
      noVoice: 'This device has no Amharic voice installed, so the answer cannot be read aloud in Amharic.',
      offline: 'Answered offline, without AI.',
      local: 'Answered by the local model on this computer.',
      error: 'I could not reach the tutor service. Check that it is running, then try again.',
      retry: 'Try again',
      micDenied: 'The microphone is blocked. Allow it in your browser settings to speak your question.',
      micLang: 'This browser cannot recognise speech in this language. Please type your question.',
      micError: 'I could not hear you. Try again, or type your question.',
      cleared: 'Chat cleared.',
      welcome:
        'Hello! Ask me about your course: lessons, deadlines, scores or upcoming events. I answer only from your course pages and show you where each answer comes from.',
      suggestions: [
        'What is the late policy for WR 100?',
        'Is the future of VA work promising?',
        'What will clients value more and more?',
      ],
    },
    am: {
      launcher: 'ረዳት አስተማሪውን ይጠይቁ',
      title: 'የኮርስ ረዳት አስተማሪ',
      subtitle: 'መልሶቹ የሚመጡት ከኮርስ ገጾችዎ ብቻ ነው።',
      close: 'ረዳት አስተማሪውን ዝጋ',
      language: 'ቋንቋ',
      simple: 'ቀላል ቃላት',
      clear: 'ውይይቱን አጽዳ',
      transcript: 'ከረዳት አስተማሪው ጋር ያለ ውይይት',
      inputLabel: 'ጥያቄዎ',
      placeholder: 'ጥያቄዎን ይጻፉ…',
      send: 'ላክ',
      mic: 'ጥያቄዎን በድምፅ ይናገሩ',
      micStop: 'ማዳመጥ አቁም',
      listening: 'እያዳመጥኩ ነው… አሁን ይናገሩ።',
      heard: 'ማዳመጥ ቆሟል። ጥያቄዎን አረጋግጠው “ላክ” ይጫኑ።',
      thinking: 'ረዳት አስተማሪው መልስ እየጻፈ ነው…',
      you: 'እርስዎ',
      tutor: 'ረዳት አስተማሪ',
      sources: 'ምንጮች',
      source: 'ምንጭ',
      sourceCount: (n) => `${n} ምንጭ ከታች ተዘርዝሯል።`,
      newTab: 'በአዲስ ትር ይከፈታል',
      read: 'በድምፅ አንብብ',
      stopRead: 'ማንበብ አቁም',
      noVoice: 'በዚህ መሣሪያ ላይ የአማርኛ ድምፅ ስላልተጫነ መልሱን በአማርኛ ማንበብ አይቻልም።',
      offline: 'ያለ AI፣ ያለ ኢንተርኔት የተመለሰ።',
      local: 'በዚህ ኮምፒውተር ላይ ባለው ሞዴል የተመለሰ።',
      error: 'ከረዳት አስተማሪው አገልግሎት ጋር መገናኘት አልተቻለም። አገልግሎቱ መሥራቱን አረጋግጠው እንደገና ይሞክሩ።',
      retry: 'እንደገና ሞክር',
      micDenied: 'ማይክሮፎኑ ተከልክሏል። ጥያቄዎን በድምፅ ለመናገር በብራውዘርዎ ቅንብር ውስጥ ይፍቀዱ።',
      micLang: 'ይህ ብራውዘር በዚህ ቋንቋ ንግግርን መለየት አይችልም። እባክዎ ጥያቄዎን ይጻፉ።',
      micError: 'ድምፅዎን መስማት አልቻልኩም። እንደገና ይሞክሩ ወይም ጥያቄዎን ይጻፉ።',
      cleared: 'ውይይቱ ጸድቷል።',
      welcome:
        'ሰላም! ስለ ኮርስዎ ይጠይቁኝ፦ ትምህርቶች፣ የጊዜ ገደቦች፣ ውጤቶች ወይም መጪ ዝግጅቶች። የምመልሰው ከኮርስ ገጾችዎ ብቻ ነው፤ እያንዳንዱ መልስ ከየት እንደመጣም አሳያለሁ።',
      suggestions: [
        'የWR 100 የመዘግየት ፖሊሲ ምንድን ነው?',
        'የምናባዊ ረዳት ሥራ የወደፊት ተስፋ አለው?',
        'ደንበኞች ይበልጥ ዋጋ የሚሰጡት ምንድን ነው?',
      ],
    },
  };
  const SPEECH_LANG = { en: 'en-US', am: 'am-ET' };

  const ICONS = {
    chat: '<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z"/>',
    close: '<path d="M6 6l12 12M18 6L6 18"/>',
    send: '<path d="M4 12l16-8-6 16-3-7-7-1z"/>',
    mic: '<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/>',
    speaker: '<path d="M4 9v6h4l5 4V5L8 9H4z"/><path d="M16.5 8.5a5 5 0 0 1 0 7"/>',
    stop: '<rect x="6" y="6" width="12" height="12" rx="2"/>',
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

  // ------------------------------------------------------------ state

  const state = {
    lang: (navigator.language || '').startsWith('am') ? 'am' : 'en', // a saved choice below wins
    simple: store(localStorage, 'ableway-simple') === true,
    open: store(sessionStorage, 'ableway-open') === true,
    messages: store(sessionStorage, 'ableway-messages') || [], // {role, text, lang, citations, provider, error}
    busy: false,
    listening: false,
    speakingFor: null, // the button of the message being read aloud
  };
  const savedLang = store(localStorage, 'ableway-lang');
  if (savedLang === 'en' || savedLang === 'am') state.lang = savedLang;
  const t = () => STRINGS[state.lang];

  // ------------------------------------------------------------ build the widget

  const host = el('div', { id: 'ableway-assistant' });
  const shadow = host.attachShadow({ mode: 'open' });
  const css = el('link', { rel: 'stylesheet', href: new URL('assistant.css', script.src).href });

  const launcher = el('button', { type: 'button', class: 'launcher', 'aria-expanded': 'false', onclick: () => setOpen(true) });
  const launcherText = el('span');
  launcher.append(icon('chat'), launcherText);

  const title = el('h2', { class: 'title', id: 'ableway-title' });
  const subtitle = el('p', { class: 'subtitle' });
  const closeButton = el('button', { type: 'button', class: 'icon-button', onclick: () => setOpen(false) }, icon('close'));

  const langButtons = {
    en: el('button', { type: 'button', lang: 'en', text: 'English', onclick: () => setLang('en') }),
    am: el('button', { type: 'button', lang: 'am', text: 'አማርኛ', onclick: () => setLang('am') }),
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

  const list = el('ol', { class: 'messages' });
  const suggestions = el('div', { class: 'suggestions' });
  const scroller = el('div', { class: 'scroller', tabindex: '0', role: 'group' }, list, suggestions);

  // Screen readers hear new messages from this hidden log, where we control the wording
  // (no citation markers, no button labels). The visible transcript is not itself live.
  const announcer = el('div', { class: 'sr-only', role: 'log', 'aria-live': 'polite', 'aria-relevant': 'additions' });
  // Short state changes: thinking, listening, errors. Visible, and announced.
  const status = el('div', { class: 'status', role: 'status' });

  const inputLabel = el('label', { class: 'sr-only', for: 'ableway-input' });
  const input = el('textarea', { id: 'ableway-input', rows: '1', dir: 'auto', autocomplete: 'off', enterkeyhint: 'send' });
  const micButton = el('button', { type: 'button', class: 'icon-button mic', 'aria-pressed': 'false', onclick: toggleMic }, icon('mic'));
  const sendButton = el('button', { type: 'submit', class: 'icon-button send' }, icon('send'));
  const form = el('form', { class: 'composer', onsubmit: onSubmit }, inputLabel, input, micButton, sendButton);

  const panel = el(
    'section',
    { class: 'panel', role: 'dialog', 'aria-modal': 'false', 'aria-labelledby': 'ableway-title', hidden: true },
    el('div', { class: 'header' }, el('div', { class: 'header-text' }, title, subtitle), closeButton),
    el('div', { class: 'settings' }, langGroup, simpleSwitch, clearButton),
    scroller,
    announcer,
    status,
    form,
  );

  // <aside> gives screen-reader users a landmark to jump to from anywhere on the page.
  const root = el('aside', { class: 'root', hidden: true }, launcher, panel);
  shadow.append(css, root);
  css.addEventListener('load', () => (root.hidden = false));
  css.addEventListener('error', () => (root.hidden = false));

  // ------------------------------------------------------------ rendering

  function applyLanguage() {
    const s = t();
    root.lang = state.lang;
    root.setAttribute('aria-label', s.title);
    launcherText.textContent = s.launcher;
    title.textContent = s.title;
    subtitle.textContent = s.subtitle;
    closeButton.setAttribute('aria-label', s.close);
    langGroup.setAttribute('aria-label', s.language);
    for (const [code, button] of Object.entries(langButtons)) button.setAttribute('aria-pressed', String(code === state.lang));
    simpleText.textContent = s.simple;
    simpleSwitch.setAttribute('aria-checked', String(state.simple));
    clearButton.textContent = s.clear;
    scroller.setAttribute('aria-label', s.transcript);
    inputLabel.textContent = s.inputLabel;
    input.placeholder = s.placeholder;
    sendButton.setAttribute('aria-label', s.send);
    micButton.setAttribute('aria-label', state.listening ? s.micStop : s.mic);
    renderMessages();
  }

  function renderMessages() {
    stopSpeaking();
    const welcome = { role: 'assistant', text: t().welcome, lang: state.lang, citations: [], welcome: true };
    list.replaceChildren(...[welcome, ...state.messages].map(renderMessage));
    suggestions.replaceChildren(
      ...(state.messages.length
        ? []
        : t().suggestions.map((q) => el('button', { type: 'button', class: 'chip', lang: state.lang, text: q, onclick: () => ask(q) }))),
    );
    scrollToEnd();
  }

  function renderMessage(message) {
    const s = t();
    const isUser = message.role === 'user';
    const bubble = el('div', { class: 'bubble' });
    for (const paragraph of message.text.split(/\n{2,}/)) {
      if (paragraph.trim()) bubble.append(renderParagraph(paragraph.trim(), message.citations || []));
    }
    const item = el(
      'li',
      { class: `msg ${isUser ? 'msg-user' : 'msg-bot'}${message.error ? ' msg-error' : ''}`, lang: message.lang },
      el('span', { class: 'who', lang: state.lang, text: isUser ? s.you : s.tutor }),
      bubble,
    );
    if (message.citations && message.citations.length) {
      const sources = el('ol');
      for (const c of message.citations) sources.append(el('li', {}, sourceLink(c, c.title)));
      item.append(el('div', { class: 'sources', lang: 'en' }, el('p', { class: 'sources-title', lang: state.lang, text: s.sources }), sources));
    }
    if (message.provider === 'offline' || message.provider === 'local') {
      if (message.citations && message.citations.length) item.append(el('p', { class: 'note', lang: state.lang, text: s[message.provider] }));
    }
    const actions = el('div', { class: 'actions' });
    if (message.error) actions.append(el('button', { type: 'button', class: 'chip', lang: state.lang, text: s.retry, onclick: retry }));
    if (!isUser && !message.error && 'speechSynthesis' in window) {
      const label = el('span', { text: s.read });
      const button = el('button', { type: 'button', class: 'chip', lang: state.lang, 'aria-pressed': 'false' }, icon('speaker'), label);
      button.addEventListener('click', () => toggleSpeak(button, label, message));
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

  // ------------------------------------------------------------ settings and open/close

  function setOpen(open) {
    state.open = open;
    store(sessionStorage, 'ableway-open', open);
    root.classList.toggle('open', open);
    panel.hidden = !open;
    launcher.hidden = open;
    launcher.setAttribute('aria-expanded', String(open));
    if (open) {
      scrollToEnd();
      input.focus();
    } else {
      stopSpeaking();
      stopListening();
      launcher.focus();
    }
  }

  function setLang(lang) {
    state.lang = lang;
    store(localStorage, 'ableway-lang', lang);
    stopListening();
    applyLanguage();
    langButtons[lang].focus(); // re-rendering must not drop keyboard focus
  }

  function setSimple(on) {
    state.simple = on;
    store(localStorage, 'ableway-simple', on);
    simpleSwitch.setAttribute('aria-checked', String(on));
  }

  function clearChat() {
    state.messages = [];
    store(sessionStorage, 'ableway-messages', state.messages);
    renderMessages();
    setStatus(t().cleared);
    input.focus();
  }

  // ------------------------------------------------------------ asking

  function addMessage(message) {
    state.messages.push(message);
    store(sessionStorage, 'ableway-messages', state.messages.filter((m) => !m.error));
    list.append(renderMessage(message));
    suggestions.replaceChildren();
    announce(message);
    scrollToEnd();
  }

  function onSubmit(event) {
    event.preventDefault();
    ask(input.value);
  }

  function retry() {
    const lastQuestion = [...state.messages].reverse().find((m) => m.role === 'user');
    state.messages = state.messages.filter((m) => !m.error);
    if (lastQuestion) {
      state.messages.splice(state.messages.lastIndexOf(lastQuestion), 1);
      renderMessages();
      ask(lastQuestion.text);
    }
  }

  async function ask(text) {
    const question = text.trim();
    if (!question || state.busy) return;
    stopListening();
    stopSpeaking();
    const history = state.messages.filter((m) => !m.error).slice(-6).map((m) => ({ role: m.role, content: m.text }));
    addMessage({ role: 'user', text: question, lang: state.lang });
    input.value = '';
    resizeInput();
    setBusy(true);

    const typing = el('li', { class: 'msg msg-bot', 'aria-hidden': 'true' }, el('div', { class: 'bubble typing' }, el('span'), el('span'), el('span')));
    list.append(typing);
    scrollToEnd();

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 90000);
    let reply;
    try {
      const response = await fetch(`${API}/api/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, lang: state.lang, simple: state.simple, history }),
        signal: controller.signal,
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || response.statusText);
      reply = { role: 'assistant', text: data.answer, lang: data.lang, citations: data.citations, provider: data.provider };
    } catch {
      reply = { role: 'assistant', text: t().error, lang: state.lang, citations: [], error: true };
    } finally {
      clearTimeout(timeout);
      typing.remove();
      setBusy(false);
    }
    addMessage(reply);
    input.focus();
  }

  function setBusy(busy) {
    state.busy = busy;
    // aria-disabled keeps the button focusable, so focus is not lost while waiting.
    sendButton.setAttribute('aria-disabled', String(busy));
    setStatus(busy ? t().thinking : '');
  }

  function resizeInput() {
    input.style.height = 'auto';
    input.style.height = `${Math.min(input.scrollHeight + 4, 120)}px`;
  }

  input.addEventListener('input', resizeInput);
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

  // ------------------------------------------------------------ voice in (speech to text)

  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  let recognition = null;
  if (!Recognition) micButton.hidden = true;

  function toggleMic() {
    if (state.listening) return stopListening();
    const s = t();
    const before = input.value ? `${input.value.trim()} ` : '';
    let failed = false;
    recognition = new Recognition();
    recognition.lang = SPEECH_LANG[state.lang];
    recognition.interimResults = true;
    recognition.onresult = (event) => {
      input.value = before + Array.from(event.results, (r) => r[0].transcript).join('');
      resizeInput();
    };
    recognition.onerror = (event) => {
      failed = true;
      const denied = event.error === 'not-allowed' || event.error === 'service-not-allowed';
      setStatus(denied ? s.micDenied : event.error === 'language-not-supported' ? s.micLang : s.micError);
    };
    recognition.onend = () => {
      state.listening = false;
      micButton.setAttribute('aria-pressed', 'false');
      micButton.setAttribute('aria-label', t().mic);
      if (!failed) setStatus(input.value.trim() ? s.heard : '');
    };
    try {
      recognition.start();
    } catch {
      return setStatus(s.micError);
    }
    stopSpeaking();
    state.listening = true;
    micButton.setAttribute('aria-pressed', 'true');
    micButton.setAttribute('aria-label', s.micStop);
    setStatus(s.listening);
  }

  function stopListening() {
    if (state.listening && recognition) recognition.stop();
  }

  // ------------------------------------------------------------ voice out (text to speech)

  function voiceFor(lang) {
    return speechSynthesis.getVoices().find((v) => v.lang.toLowerCase().replace('_', '-').startsWith(lang));
  }

  function toggleSpeak(button, label, message) {
    const wasThisOne = state.speakingFor === button;
    stopSpeaking();
    if (wasThisOne) return;

    const voice = voiceFor(message.lang);
    if (message.lang === 'am' && !voice) return setStatus(t().noVoice);

    // Read sentence by sentence: some browsers cut off a single long utterance.
    const text = message.text.replace(/\[\d+\]/g, '');
    const sentences = text.match(/[^.!?።\n]+[.!?።]*/g) || [text];
    const parts = sentences.map((s) => s.trim()).filter(Boolean);
    parts.forEach((sentence, i) => {
      const utterance = new SpeechSynthesisUtterance(sentence);
      utterance.lang = SPEECH_LANG[message.lang] || message.lang;
      if (voice) utterance.voice = voice;
      if (i === parts.length - 1) {
        utterance.onend = () => state.speakingFor === button && stopSpeaking();
        utterance.onerror = utterance.onend;
      }
      speechSynthesis.speak(utterance);
    });
    state.speakingFor = button;
    state.speakingLabel = label;
    button.setAttribute('aria-pressed', 'true');
    label.textContent = t().stopRead;
    button.replaceChild(icon('stop'), button.firstChild);
  }

  function stopSpeaking() {
    if (!('speechSynthesis' in window)) return;
    const button = state.speakingFor;
    state.speakingFor = null;
    speechSynthesis.cancel();
    if (button) {
      button.setAttribute('aria-pressed', 'false');
      state.speakingLabel.textContent = t().read;
      button.replaceChild(icon('speaker'), button.firstChild);
    }
  }

  if ('speechSynthesis' in window) speechSynthesis.getVoices(); // voices load lazily; ask early
  window.addEventListener('pagehide', stopSpeaking);

  // ------------------------------------------------------------ start

  applyLanguage();
  document.body.append(host);
  if (state.open) {
    root.classList.add('open');
    panel.hidden = false;
    launcher.hidden = true;
    launcher.setAttribute('aria-expanded', 'true');
  }
})();
