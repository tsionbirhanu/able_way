// Accessibility gate check: runs axe-core (WCAG 2.0, 2.1 and 2.2 A and AA rules) in headless Chrome or
// Edge on a page after Mimi has loaded, and fails when there is any critical or serious issue.
//
//   cd tests/a11y && npm install
//   node axe.mjs http://localhost:8000/demo/blank.html            (only the assistant)
//   node axe.mjs http://localhost:8000/demo/blank.html page       (the whole page)
//   npm run check                                                 (blank page and a Savanna page)
import { spawn } from 'node:child_process';
import { existsSync, mkdtempSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const [, , url, scope = 'widget', openPanel = 'closed'] = process.argv;
const axeSource = readFileSync(join(dirname(fileURLToPath(import.meta.url)), 'node_modules/axe-core/axe.min.js'), 'utf8');
const BROWSERS = [process.env.BROWSER, 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', 'C:/Program Files/Google/Chrome/Application/chrome.exe',
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser'].filter(Boolean);
const browserPath = BROWSERS.find((p) => existsSync(p));
if (!browserPath) { console.error('No Chrome or Edge found: set BROWSER=/path/to/chrome'); process.exit(2); }
const port = 9700 + Math.floor(Math.random() * 200);
const proc = spawn(browserPath, [
  '--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${mkdtempSync(join(tmpdir(), 'axe-'))}`,
  '--window-size=1280,900', 'about:blank'], { stdio: 'ignore' });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let target;
for (let i = 0; i < 40 && !target; i++) { await sleep(250); try { target = (await (await fetch(`http://127.0.0.1:${port}/json`)).json()).find((t) => t.type === 'page'); } catch {} }
const ws = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((r) => (ws.onopen = r));
let id = 0; const pending = new Map();
ws.onmessage = (e) => { const m = JSON.parse(e.data); if (m.id && pending.has(m.id)) pending.get(m.id)(m); };
const send = (method, params = {}) => new Promise((r) => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
const ev = async (expression) => { const r = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true }); if (r.result.exceptionDetails) throw new Error(JSON.stringify(r.result.exceptionDetails).slice(0, 400)); return r.result.result.value; };
await send('Runtime.enable'); await send('Page.enable');
await send('Page.navigate', { url });
await sleep(5000);
if (openPanel === 'closed') {
  // Show the card state (chat closed) when the chat opened by default.
  await ev(`(() => { const h = document.querySelector('#ableway-assistant, db-assistant'); const b = h && h.shadowRoot && h.shadowRoot.querySelector('.panel .icon-button[aria-label]'); return !!b; })()`);
}
await ev(axeSource + '; true');
const result = await ev(`axe.run(${scope === 'widget' ? "{ include: [['#ableway-assistant'], ['db-assistant']] }" : 'document'}, { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21a', 'wcag21aa', 'wcag22aa'] }, resultTypes: ['violations'] })
  .then((r) => r.violations.map((v) => ({ id: v.id, impact: v.impact, help: v.help, count: v.nodes.length, where: v.nodes.slice(0, 3).map((n) => n.target.join(' >>> ') + ' :: ' + (n.failureSummary || '').split('\\n').slice(1, 2).join(' ').slice(0, 140)) })))`);
const by = { critical: 0, serious: 0, moderate: 0, minor: 0 };
for (const v of result) by[v.impact] = (by[v.impact] || 0) + v.count;
console.log(JSON.stringify({ url, scope, summary: by, violations: result }, null, 1));
ws.close(); proc.kill(); process.exit(by.critical || by.serious ? 1 : 0);
