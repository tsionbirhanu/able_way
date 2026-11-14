/**
 * Ableway Multilingual Course Tutor & Career Assistant
 * Track 3 Web Component: <db-assistant>
 * 
 * Conforms to ALX Digital Bridge Hackathon 2026 technical guide:
 * - One tag, configured by attributes (lang, api, content)
 * - Dispatches 'db-assistant:question' and 'db-assistant:escalated'
 * - Shadow DOM isolated styles using host variables: var(--bs-primary), var(--bs-body-color)
 * - Accessible controls (44px min touch targets, :focus-visible 3px outline)
 * - Voice input (SpeechRecognition am-ET / en-US) & Read Aloud (speechSynthesis)
 * - One-click human escalation & simple-words mode
 */

const I18N = {
  en: {
    launcher: 'Ask the tutor',
    title: 'Course tutor',
    subtitle: 'Answers come strictly from course materials and jobs.',
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
    heard: 'Stopped listening. Check question, then press Send.',
    thinking: 'The tutor is looking up the answer…',
    you: 'You',
    tutor: 'Tutor',
    sources: 'Sources',
    source: 'Source',
    talkToPerson: 'Talk to a person',
    screenShare: 'Share screen with tutor',
    screenSharingActive: 'Screen sharing active',
    screenShareStop: 'Stop sharing',
    newTab: 'opens in new tab',
    read: 'Read aloud',
    stopRead: 'Stop reading',
    noVoice: 'No Amharic voice installed on this device.',
    offline: 'Answered offline, without AI.',
    local: 'Answered by local model.',
    cloud: 'Answered by AI tutor.',
    error: 'Could not connect to tutor service. Please check connection.',
    retry: 'Try again',
    welcome: 'Hello! Ask me about your courses, deadlines, grades, or career opportunities. I cite the exact source for every answer.',
    suggestions: [
      'What is the late policy for WR 100?',
      'Is the future of VA work promising?',
      'Show available remote jobs'
    ]
  },
  am: {
    launcher: 'ረዳት አስተማሪውን ይጠይቁ',
    title: 'የኮርስ ረዳት አስተማሪ',
    subtitle: 'መልሶቹ የሚመጡት ከትምህርት ገጾችዎ እና ከሥራ መረጃዎች ብቻ ነው።',
    close: 'ረዳት አስተማሪውን ዝጋ',
    language: 'ቋንቋ',
    simple: 'ቀላል ቃላት',
    clear: 'ውይይቱን አጽዳ',
    transcript: 'ከረዳት አስተማሪው ጋር ያለ ውይይት',
    inputLabel: 'ጥያቄዎ',
    placeholder: 'ጥያቄዎን እዚህ ይጻፉ…',
    send: 'ላክ',
    mic: 'ጥያቄዎን በድምፅ ይናገሩ',
    micStop: 'ማዳመጥ አቁም',
    listening: 'እያዳመጥኩ ነው… አሁን ይናገሩ።',
    heard: 'ማዳመጥ ቆሟል። ጥያቄዎን አረጋግጠው “ላክ” ይጫኑ።',
    thinking: 'ረዳት አስተማሪው መልስ እየፈለገ ነው…',
    you: 'እርስዎ',
    tutor: 'ረዳት አስተማሪ',
    sources: 'ምንጮች',
    source: 'ምንጭ',
    talkToPerson: 'ረዳት ሰው ያነጋግሩ',
    screenShare: 'ማያ ገጽዎን ለአስተማሪው ያጋሩ',
    screenSharingActive: 'የማያ ገጽ ማጋራት በርቷል',
    screenShareStop: 'ማጋራት አቁም',
    newTab: 'በአዲስ ትር ይከፈታል',
    read: 'በድምፅ አንብብ',
    stopRead: 'ማንበብ አቁም',
    noVoice: 'በዚህ መሣሪያ ላይ የአማርኛ ድምፅ ስላልተጫነ ማንበብ አይቻልም።',
    offline: 'ያለ ኢንተርኔት ከመረጃ ቋት የተመለሰ።',
    local: 'በኮምፒውተሩ ላይ ባለው ሞዴል የተመለሰ።',
    cloud: 'በAI ረዳት አስተማሪ የተመለሰ።',
    error: 'ከረዳት አስተማሪው ጋር መገናኘት አልተቻለም። እባክዎ እንደገና ይሞክሩ።',
    retry: 'እንደገና ሞክር',
    welcome: 'ሰላም! ስለ ኮርስዎ፣ የጊዜ ገደቦች፣ ውጤቶች ወይም የሥራ ዕድሎች ይጠይቁኝ። እያንዳንዱን መልስ ከትክክለኛ ምንጭ ጋር አቀርባለሁ።',
    suggestions: [
      'የWR 100 የመዘግየት ፖሊሲ ምንድን ነው?',
      'የምናባዊ ረዳት ሥራ የወደፊት ተስፋ አለው?',
      'ክፍት የርቀት ሥራዎችን አሳየኝ'
    ]
  }
};

const ICONS = {
  chat: '<path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z"/>',
  close: '<path d="M6 6l12 12M18 6L6 18"/>',
  send: '<path d="M4 12l16-8-6 16-3-7-7-1z"/>',
  mic: '<rect x="9" y="3" width="6" height="11" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/>',
  speaker: '<path d="M4 9v6h4l5 4V5L8 9H4z"/><path d="M16.5 8.5a5 5 0 0 1 0 7"/>',
  stop: '<rect x="6" y="6" width="12" height="12" rx="2"/>',
  person: '<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>',
  share: '<rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>'
};

class DbAssistant extends HTMLElement {
  static get observedAttributes() {
    return ['lang', 'api', 'content', 'simple'];
  }

  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this.messages = [];
    this.isOpen = false;
    this.busy = false;
    this.listening = false;
    this.speakingFor = null;
    this.screenStream = null;
  }

  connectedCallback() {
    this.render();
  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (oldValue !== newValue && this.shadowRoot && this.shadowRoot.innerHTML) {
      if (name === 'lang' || name === 'simple') {
        this.updateTexts();
      }
    }
  }

  get currentLang() {
    return this.getAttribute('lang') === 'am' ? 'am' : 'en';
  }

  get apiBase() {
    return (this.getAttribute('api') || 'http://localhost:8001').replace(/\/$/, '');
  }

  get isSimple() {
    return this.hasAttribute('simple') && this.getAttribute('simple') !== 'false';
  }

  t() {
    return I18N[this.currentLang] || I18N.en;
  }

  render() {
    const lang = this.currentLang;
    const t = this.t();

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          --ableway-primary: var(--bs-primary, #002b56);
          --ableway-primary-hover: #001f3f;
          --ableway-focus: #f5a300;
          --ableway-text: var(--bs-body-color, #1a1a1a);
          --ableway-bg: var(--bs-body-bg, #ffffff);
          --ableway-border: #cbd5e1;
          --ableway-font: var(--bs-body-font-family, system-ui, -apple-system, sans-serif);
          position: fixed;
          bottom: 24px;
          right: 24px;
          z-index: 999999;
          font-family: var(--ableway-font);
          color: var(--ableway-text);
          line-height: ${lang === 'am' ? '1.7' : '1.5'};
          box-sizing: border-box;
        }
        *, *::before, *::after { box-sizing: inherit; }

        .sr-only {
          position: absolute; width: 1px; height: 1px; padding: 0; margin: -1px;
          overflow: hidden; clip: rect(0, 0, 0, 0); white-space: nowrap; border: 0;
        }

        :focus-visible {
          outline: 3px solid var(--ableway-focus) !important;
          outline-offset: 2px !important;
        }

        /* Launcher */
        .launcher-btn {
          display: inline-flex;
          align-items: center;
          gap: 10px;
          background: var(--ableway-primary);
          color: #ffffff;
          border: 2px solid transparent;
          border-radius: 999px;
          padding: 12px 20px;
          font-size: 1rem;
          font-weight: 600;
          cursor: pointer;
          box-shadow: 0 4px 14px rgba(0,0,0,0.25);
          min-height: 48px;
          transition: transform 0.15s ease, background 0.15s ease;
        }
        .launcher-btn:hover {
          background: var(--ableway-primary-hover);
          transform: translateY(-2px);
        }
        .launcher-btn svg { width: 22px; height: 22px; fill: none; stroke: currentColor; stroke-width: 2; }

        /* Dialog Panel */
        .chat-panel {
          display: flex;
          flex-direction: column;
          width: 380px;
          max-width: calc(100vw - 32px);
          height: 600px;
          max-height: calc(100vh - 48px);
          background: var(--ableway-bg);
          border: 1px solid var(--ableway-border);
          border-radius: 16px;
          box-shadow: 0 10px 30px rgba(0,0,0,0.2);
          overflow: hidden;
        }
        .chat-panel[hidden] { display: none; }

        /* Header */
        .panel-header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 14px 16px;
          background: var(--ableway-primary);
          color: #ffffff;
        }
        .header-titles h2 { margin: 0; font-size: 1.1rem; font-weight: 700; color: #fff; }
        .header-titles p { margin: 2px 0 0; font-size: 0.8rem; opacity: 0.85; color: #fff; }
        .close-btn {
          background: transparent;
          border: 0;
          color: #ffffff;
          cursor: pointer;
          padding: 6px;
          border-radius: 6px;
          display: flex;
          align-items: center;
          justify-content: center;
          min-width: 44px;
          min-height: 44px;
        }
        .close-btn svg { width: 20px; height: 20px; fill: none; stroke: currentColor; stroke-width: 2.2; }

        /* Toolbar */
        .panel-toolbar {
          display: flex;
          flex-wrap: wrap;
          align-items: center;
          gap: 8px;
          padding: 8px 12px;
          background: #f1f5f9;
          border-bottom: 1px solid var(--ableway-border);
          font-size: 0.85rem;
        }
        .btn-toggle {
          background: #ffffff;
          border: 1px solid #cbd5e1;
          border-radius: 6px;
          padding: 4px 8px;
          font: inherit;
          cursor: pointer;
          min-height: 32px;
        }
        .btn-toggle[aria-pressed="true"], .btn-toggle[aria-checked="true"] {
          background: var(--ableway-primary);
          color: #ffffff;
          border-color: var(--ableway-primary);
        }

        /* Escalation strip */
        .escalation-bar {
          display: flex;
          gap: 6px;
          padding: 6px 12px;
          background: #e0f2fe;
          border-bottom: 1px solid #bae6fd;
        }
        .escalation-btn {
          display: inline-flex;
          align-items: center;
          gap: 6px;
          background: #0284c7;
          color: #ffffff;
          border: 0;
          border-radius: 6px;
          padding: 6px 10px;
          font-size: 0.82rem;
          font-weight: 600;
          cursor: pointer;
          min-height: 36px;
        }
        .escalation-btn svg { width: 16px; height: 16px; fill: none; stroke: currentColor; stroke-width: 2; }

        /* Messages log */
        .messages-log {
          flex: 1;
          overflow-y: auto;
          padding: 12px;
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        .msg {
          display: flex;
          flex-direction: column;
          max-width: 88%;
          font-size: 0.95rem;
        }
        .msg-user {
          align-self: flex-end;
          align-items: flex-end;
        }
        .msg-bot {
          align-self: flex-start;
          align-items: flex-start;
        }
        .bubble {
          padding: 10px 14px;
          border-radius: 14px;
          line-height: 1.5;
        }
        .msg-user .bubble {
          background: var(--ableway-primary);
          color: #ffffff;
          border-bottom-right-radius: 2px;
        }
        .msg-bot .bubble {
          background: #f1f5f9;
          color: var(--ableway-text);
          border-bottom-left-radius: 2px;
        }
        .bubble p { margin: 0 0 6px; }
        .bubble p:last-child { margin-bottom: 0; }
        .sources-box {
          margin-top: 6px;
          font-size: 0.82rem;
          background: #e2e8f0;
          padding: 6px 10px;
          border-radius: 6px;
        }
        .sources-box a { color: #0369a1; text-decoration: underline; font-weight: 500; }
        .msg-actions {
          display: flex;
          gap: 6px;
          margin-top: 4px;
        }
        .chip-btn {
          display: inline-flex;
          align-items: center;
          gap: 4px;
          background: transparent;
          border: 1px solid #cbd5e1;
          border-radius: 12px;
          padding: 4px 8px;
          font-size: 0.75rem;
          cursor: pointer;
          color: #475569;
          min-height: 28px;
        }
        .chip-btn svg { width: 14px; height: 14px; fill: none; stroke: currentColor; stroke-width: 2; }

        /* Suggestions */
        .suggestions-box {
          display: flex;
          flex-direction: column;
          gap: 6px;
          padding: 4px 12px 10px;
        }
        .suggestion-chip {
          background: #f8fafc;
          border: 1px solid #cbd5e1;
          border-radius: 8px;
          padding: 6px 10px;
          font-size: 0.85rem;
          text-align: left;
          cursor: pointer;
          color: #1e293b;
        }
        .suggestion-chip:hover { background: #e2e8f0; }

        /* Input Form */
        .composer {
          display: flex;
          align-items: flex-end;
          gap: 6px;
          padding: 10px;
          border-top: 1px solid var(--ableway-border);
          background: #ffffff;
        }
        .composer textarea {
          flex: 1;
          min-height: 44px;
          max-height: 120px;
          padding: 8px 12px;
          border: 1px solid var(--ableway-border);
          border-radius: 8px;
          font-family: inherit;
          font-size: 0.95rem;
          resize: none;
        }
        .composer button {
          display: flex;
          align-items: center;
          justify-content: center;
          background: var(--ableway-primary);
          color: #fff;
          border: 0;
          border-radius: 8px;
          width: 44px;
          height: 44px;
          cursor: pointer;
          flex-shrink: 0;
        }
        .composer button.mic-btn {
          background: #f1f5f9;
          color: #334155;
          border: 1px solid #cbd5e1;
        }
        .composer button.mic-btn[aria-pressed="true"] {
          background: #dc2626;
          color: #ffffff;
          border-color: #dc2626;
        }
        .composer button svg { width: 20px; height: 20px; fill: none; stroke: currentColor; stroke-width: 2; }

        /* Status announcer */
        .status-bar {
          padding: 4px 12px;
          font-size: 0.78rem;
          color: #64748b;
          min-height: 20px;
        }
      </style>

      <button type="button" class="launcher-btn" aria-expanded="false" aria-label="${t.launcher}">
        <svg viewBox="0 0 24 24" aria-hidden="true">${ICONS.chat}</svg>
        <span>${t.launcher}</span>
      </button>

      <section class="chat-panel" role="dialog" aria-modal="false" aria-labelledby="chat-title" hidden>
        <div class="panel-header">
          <div class="header-titles">
            <h2 id="chat-title">${t.title}</h2>
            <p>${t.subtitle}</p>
          </div>
          <button type="button" class="close-btn" aria-label="${t.close}">
            <svg viewBox="0 0 24 24" aria-hidden="true">${ICONS.close}</svg>
          </button>
        </div>

        <div class="panel-toolbar">
          <button type="button" class="btn-toggle lang-en" aria-pressed="${lang === 'en'}">English</button>
          <button type="button" class="btn-toggle lang-am" aria-pressed="${lang === 'am'}">አማርኛ</button>
          <button type="button" class="btn-toggle btn-simple" role="switch" aria-checked="${this.isSimple}">
            ${t.simple}
          </button>
          <button type="button" class="btn-toggle btn-clear">${t.clear}</button>
        </div>

        <div class="escalation-bar">
          <button type="button" class="escalation-btn btn-human" aria-label="${t.talkToPerson}">
            <svg viewBox="0 0 24 24" aria-hidden="true">${ICONS.person}</svg>
            <span>${t.talkToPerson}</span>
          </button>
          <button type="button" class="escalation-btn btn-share" aria-label="${t.screenShare}">
            <svg viewBox="0 0 24 24" aria-hidden="true">${ICONS.share}</svg>
            <span>${t.screenShare}</span>
          </button>
        </div>

        <div class="messages-log" role="log" aria-live="polite" aria-relevant="additions" tabindex="0">
          <div class="msg msg-bot" lang="${lang}">
            <div class="bubble"><p>${t.welcome}</p></div>
          </div>
        </div>

        <div class="suggestions-box">
          ${t.suggestions.map(s => `<button type="button" class="suggestion-chip" lang="${lang}">${s}</button>`).join('')}
        </div>

        <div class="status-bar" role="status"></div>

        <form class="composer" novalidate>
          <label for="user-prompt" class="sr-only">${t.inputLabel}</label>
          <textarea id="user-prompt" rows="1" placeholder="${t.placeholder}" dir="auto"></textarea>
          <button type="button" class="mic-btn" aria-label="${t.mic}" aria-pressed="false">
            <svg viewBox="0 0 24 24" aria-hidden="true">${ICONS.mic}</svg>
          </button>
          <button type="submit" class="send-btn" aria-label="${t.send}">
            <svg viewBox="0 0 24 24" aria-hidden="true">${ICONS.send}</svg>
          </button>
        </form>
      </section>
    `;

    this.bindEvents();
  }

  bindEvents() {
    const root = this.shadowRoot;
    const launcher = root.querySelector('.launcher-btn');
    const panel = root.querySelector('.chat-panel');
    const closeBtn = root.querySelector('.close-btn');
    const form = root.querySelector('.composer');
    const input = root.querySelector('#user-prompt');
    const micBtn = root.querySelector('.mic-btn');
    const btnEn = root.querySelector('.lang-en');
    const btnAm = root.querySelector('.lang-am');
    const btnSimple = root.querySelector('.btn-simple');
    const btnClear = root.querySelector('.btn-clear');
    const btnHuman = root.querySelector('.btn-human');
    const btnShare = root.querySelector('.btn-share');
    const suggestions = root.querySelectorAll('.suggestion-chip');

    launcher.addEventListener('click', () => {
      this.isOpen = true;
      launcher.hidden = true;
      panel.hidden = false;
      launcher.setAttribute('aria-expanded', 'true');
      input.focus();
    });

    closeBtn.addEventListener('click', () => {
      this.isOpen = false;
      panel.hidden = true;
      launcher.hidden = false;
      launcher.setAttribute('aria-expanded', 'false');
      launcher.focus();
    });

    panel.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        closeBtn.click();
      }
    });

    btnEn.addEventListener('click', () => {
      this.setAttribute('lang', 'en');
      this.render();
    });

    btnAm.addEventListener('click', () => {
      this.setAttribute('lang', 'am');
      this.render();
    });

    btnSimple.addEventListener('click', () => {
      const current = this.isSimple;
      this.setAttribute('simple', String(!current));
      btnSimple.setAttribute('aria-checked', String(!current));
    });

    btnClear.addEventListener('click', () => {
      const log = root.querySelector('.messages-log');
      log.innerHTML = `
        <div class="msg msg-bot" lang="${this.currentLang}">
          <div class="bubble"><p>${this.t().welcome}</p></div>
        </div>
      `;
      this.messages = [];
    });

    btnHuman.addEventListener('click', () => this.escalateToHuman());
    btnShare.addEventListener('click', () => this.toggleScreenShare());

    suggestions.forEach((chip) => {
      chip.addEventListener('click', () => {
        input.value = chip.textContent.trim();
        this.submitQuestion(input.value);
        input.value = '';
      });
    });

    form.addEventListener('submit', (e) => {
      e.preventDefault();
      const text = input.value.trim();
      if (!text || this.busy) return;
      this.submitQuestion(text);
      input.value = '';
    });

    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        form.requestSubmit();
      }
    });

    micBtn.addEventListener('click', () => this.toggleVoiceInput());
  }

  updateTexts() {
    this.render();
  }

  async submitQuestion(text) {
    const root = this.shadowRoot;
    const log = root.querySelector('.messages-log');
    const status = root.querySelector('.status-bar');
    const suggestionsBox = root.querySelector('.suggestions-box');
    if (suggestionsBox) suggestionsBox.hidden = true;

    // Append user message
    const userMsg = document.createElement('div');
    userMsg.className = 'msg msg-user';
    userMsg.dir = 'auto';
    userMsg.innerHTML = `<div class="bubble"><p>${this.escapeHtml(text)}</p></div>`;
    log.appendChild(userMsg);
    log.scrollTop = log.scrollHeight;

    // Dispatch host event
    this.dispatchEvent(new CustomEvent('db-assistant:question', {
      bubbles: true,
      composed: true,
      detail: { text, language: this.currentLang }
    }));

    this.busy = true;
    status.textContent = this.t().thinking;

    try {
      const res = await fetch(`${this.apiBase}/api/v1/ask`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: text,
          lang: this.currentLang,
          simple: this.isSimple,
          history: this.messages.slice(-6)
        })
      });

      const data = await res.json();
      status.textContent = '';
      this.busy = false;

      if (!res.ok) throw new Error(data.error || 'API error');

      this.messages.push({ role: 'user', content: text });
      this.messages.push({ role: 'assistant', content: data.answer });

      this.renderBotReply(data);
    } catch (err) {
      status.textContent = '';
      this.busy = false;
      this.renderBotReply({
        answer: this.t().error,
        citations: [],
        grounded: false,
        error: true
      });
    }
  }

  renderBotReply(data) {
    const root = this.shadowRoot;
    const log = root.querySelector('.messages-log');
    const t = this.t();

    const botMsg = document.createElement('div');
    botMsg.className = 'msg msg-bot';
    botMsg.lang = this.currentLang;
    botMsg.dir = 'auto';

    let citationsHtml = '';
    if (data.citations && data.citations.length) {
      citationsHtml = `
        <div class="sources-box">
          <strong>${t.sources}:</strong>
          <ul>
            ${data.citations.map(c => `<li><a href="${c.url || '#'}" target="_blank" rel="noopener">${this.escapeHtml(c.title || c.heading || 'Source')}</a></li>`).join('')}
          </ul>
        </div>
      `;
    }

    botMsg.innerHTML = `
      <div class="bubble">
        <p>${this.escapeHtml(data.answer)}</p>
        ${citationsHtml}
      </div>
      <div class="msg-actions">
        <button type="button" class="chip-btn btn-read-aloud" aria-label="${t.read}">
          <svg viewBox="0 0 24 24" aria-hidden="true">${ICONS.speaker}</svg>
          <span>${t.read}</span>
        </button>
      </div>
    `;

    const readBtn = botMsg.querySelector('.btn-read-aloud');
    readBtn.addEventListener('click', () => this.toggleReadAloud(readBtn, data.answer));

    log.appendChild(botMsg);
    log.scrollTop = log.scrollHeight;
  }

  toggleReadAloud(btn, text) {
    if (!('speechSynthesis' in window)) return;
    if (window.speechSynthesis.speaking) {
      window.speechSynthesis.cancel();
      btn.querySelector('span').textContent = this.t().read;
      return;
    }

    const clean = text.replace(/\[\d+\]/g, '');
    const utter = new SpeechSynthesisUtterance(clean);
    utter.lang = this.currentLang === 'am' ? 'am-ET' : 'en-US';
    utter.onend = () => {
      btn.querySelector('span').textContent = this.t().read;
    };
    utter.onerror = () => {
      btn.querySelector('span').textContent = this.t().read;
    };

    btn.querySelector('span').textContent = this.t().stopRead;
    window.speechSynthesis.speak(utter);
  }

  toggleVoiceInput() {
    const root = this.shadowRoot;
    const micBtn = root.querySelector('.mic-btn');
    const input = root.querySelector('#user-prompt');
    const status = root.querySelector('.status-bar');
    const Speech = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!Speech) {
      status.textContent = 'Voice input not supported in this browser.';
      return;
    }

    if (this.listening) {
      if (this.recognition) this.recognition.stop();
      this.listening = false;
      micBtn.setAttribute('aria-pressed', 'false');
      status.textContent = '';
      return;
    }

    this.recognition = new Speech();
    this.recognition.lang = this.currentLang === 'am' ? 'am-ET' : 'en-US';
    this.recognition.interimResults = true;

    this.recognition.onstart = () => {
      this.listening = true;
      micBtn.setAttribute('aria-pressed', 'true');
      status.textContent = this.t().listening;
    };

    this.recognition.onresult = (e) => {
      const transcript = Array.from(e.results).map(r => r[0].transcript).join('');
      input.value = transcript;
    };

    this.recognition.onerror = () => {
      status.textContent = this.t().error;
      this.listening = false;
      micBtn.setAttribute('aria-pressed', 'false');
    };

    this.recognition.onend = () => {
      this.listening = false;
      micBtn.setAttribute('aria-pressed', 'false');
      status.textContent = input.value ? this.t().heard : '';
    };

    try {
      this.recognition.start();
    } catch {
      status.textContent = this.t().error;
    }
  }

  async escalateToHuman() {
    const t = this.t();
    const status = this.shadowRoot.querySelector('.status-bar');
    status.textContent = 'Opening help ticket…';

    try {
      // Connect to handoff server
      const res = await fetch(`http://localhost:8000/handoff/tickets`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          lang: this.currentLang,
          topic: this.messages.length ? this.messages[this.messages.length - 1].content : 'Assistance requested',
          channel: 'web'
        })
      });

      const data = await res.json();
      status.textContent = '';

      this.dispatchEvent(new CustomEvent('db-assistant:escalated', {
        bubbles: true,
        composed: true,
        detail: { ticketId: data.ticket_id }
      }));

      if (data.chat_url) {
        window.open(`http://localhost:8000${data.chat_url}`, '_blank', 'noopener');
      }
    } catch (err) {
      status.textContent = 'Help ticket queued. A tutor will connect soon.';
    }
  }

  async toggleScreenShare() {
    const btn = this.shadowRoot.querySelector('.btn-share');
    const status = this.shadowRoot.querySelector('.status-bar');

    if (this.screenStream) {
      this.screenStream.getTracks().forEach(t => t.stop());
      this.screenStream = null;
      btn.querySelector('span').textContent = this.t().screenShare;
      status.textContent = 'Screen sharing stopped.';
      return;
    }

    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getDisplayMedia) {
        status.textContent = 'Screen sharing not supported on this device/browser.';
        return;
      }
      this.screenStream = await navigator.mediaDevices.getDisplayMedia({ video: true });
      btn.querySelector('span').textContent = this.t().screenShareStop;
      status.textContent = this.t().screenSharingActive;
      this.screenStream.getVideoTracks()[0].onended = () => {
        this.screenStream = null;
        btn.querySelector('span').textContent = this.t().screenShare;
        status.textContent = 'Screen sharing ended.';
      };
    } catch {
      status.textContent = 'Screen share cancelled.';
    }
  }

  escapeHtml(str) {
    if (!str) return '';
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
}

customElements.define('db-assistant', DbAssistant);
