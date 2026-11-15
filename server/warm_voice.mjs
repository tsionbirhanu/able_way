// Records Mimi's fixed phrases (greeting, confirmations, menu, prompts) on the tutor server, so
// they always play in full: with no voice quota left, with no internet, and before the learner has
// touched the page. Each phrase costs one voice request, once; after that it is served from
// data/tts_cache/. Run it whenever module/i18n/*.json or the menu in module/db-assistant.js change:
//
//   node server/warm_voice.mjs                 (tutor on http://localhost:8001)
//   node server/warm_voice.mjs http://localhost:8000
//
// Browsers with a natural voice of their own (Edge: Amharic Mekdes, English Ava) do not need this.

import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const api = (process.argv[2] || 'http://localhost:8001').replace(/\/$/, '');
const moduleDir = join(dirname(fileURLToPath(import.meta.url)), '..', 'module');
const source = readFileSync(join(moduleDir, 'db-assistant.js'), 'utf8');
const STRINGS = Object.fromEntries(['am', 'en'].map((code) => [code, JSON.parse(readFileSync(join(moduleDir, 'i18n', `${code}.json`), 'utf8'))]));

// The menu order lives in the widget; its words in the language files. Build the text exactly as the
// widget does, because the server keys its recordings by the exact text.
const start = source.indexOf('// ---- menu table start');
const end = source.indexOf('// ---- menu table end', start);
if (start < 0 || end < 0) throw new Error('could not find the menu table in module/db-assistant.js');
const { MENU_TEXT } = Function('STRINGS', `${source.slice(start, end)}; return { MENU_TEXT };`)(STRINGS);

const spoken = (text) => text.replace(/\s*\[\d+\]/g, '').replace(/\s+/g, ' ').trim();
const phrases = [];
for (const lang of ['am', 'en']) {
  const s = STRINGS[lang];
  phrases.push([lang, s.introSpoken], [lang, s.otherLanguageHint], [lang, s.confirm], [lang, s.askNow], [lang, MENU_TEXT(lang)]);
}

let ok = 0;
for (const [lang, text] of phrases) {
  const started = Date.now();
  try {
    const response = await fetch(`${api}/api/tts`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: spoken(text), lang, cache: true }),
    });
    const bytes = (await response.arrayBuffer()).byteLength;
    console.log(`${response.ok ? 'saved ' : 'FAILED'} ${lang} ${String(Date.now() - started).padStart(5)}ms ${response.ok ? bytes + ' bytes' : 'HTTP ' + response.status}  ${text.slice(0, 50)}`);
    if (response.ok) ok++;
  } catch (e) {
    console.log(`FAILED ${lang} ${e.message}  ${text.slice(0, 50)}`);
  }
}
console.log(`\n${ok} of ${phrases.length} phrases recorded.${ok < phrases.length ? ' Run again later (voice quota), or add AZURE_SPEECH_KEY.' : ''}`);
process.exitCode = ok === phrases.length ? 0 : 1;
