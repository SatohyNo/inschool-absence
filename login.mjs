#!/usr/bin/env node
// Logs in to Visma InSchool and saves the session for absence.py.
// Opens a separate Chrome window. You log in yourself (e.g. with Feide) and open InSchool;
// as soon as InSchool answers, its cookies are saved to ~/.visma-inschool-session.json (mode 600)
// and the window closes. Your password is never read or stored.
//
// Usage: node login.mjs <your-school>.inschool.visma.no [start-url]
//   start-url — page to open first, e.g. your school's portal with the "Log in" button
//               (default: https://<your-school>.inschool.visma.no/)
import { spawn } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const HOST = process.argv[2] || process.env.INSCHOOL_HOST;
if (!HOST) {
  console.error("Usage: node login.mjs <your-school>.inschool.visma.no [start-url]");
  process.exit(2);
}
const START = process.argv[3] || `https://${HOST}/`;
const HOME = os.homedir();
const SESSION = process.env.INSCHOOL_SESSION || path.join(HOME, ".visma-inschool-session.json");
const PROFILE = path.join(HOME, ".visma-inschool-chrome");
const CHROME = process.env.CHROME_PATH || "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const PORT = 9333;

for (const f of ["SingletonLock", "SingletonSocket", "SingletonCookie"]) fs.rmSync(path.join(PROFILE, f), { force: true });
const chrome = spawn(CHROME, [`--remote-debugging-port=${PORT}`, `--user-data-dir=${PROFILE}`,
  "--no-first-run", "--no-default-browser-check", START], { stdio: "ignore" });
let closed = false;
chrome.on("exit", () => { closed = true; });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
let wsUrl;
for (let i = 0; i < 60 && !wsUrl && !closed; i++) {
  await sleep(500);
  try { wsUrl = (await (await fetch(`http://127.0.0.1:${PORT}/json/version`)).json()).webSocketDebuggerUrl; } catch {}
}
if (!wsUrl) { console.error("Chrome did not start (close other windows of this profile and try again, or set CHROME_PATH)"); process.exit(1); }
const ws = new WebSocket(wsUrl);
await new Promise((r) => ws.addEventListener("open", r));
let seq = 0;
const waiting = new Map();
ws.addEventListener("message", (ev) => {
  const m = JSON.parse(ev.data);
  if (m.id && waiting.has(m.id)) { waiting.get(m.id)(m.result || {}); waiting.delete(m.id); }
});
const send = (method, params = {}) => new Promise((resolve) => {
  const id = ++seq; waiting.set(id, resolve); ws.send(JSON.stringify({ id, method, params }));
});

// Logged in once /control/permissions/user answers with JSON containing learnerId
async function check(cookies) {
  const header = cookies.map((c) => `${c.name}=${c.value}`).join("; ");
  try {
    const r = await fetch(`https://${HOST}/control/permissions/user`, { headers: { cookie: header }, redirect: "manual" });
    return r.status === 200 && "learnerId" in (await r.json());
  } catch { return false; }
}

console.log("A Chrome window is open: log in and open InSchool. It closes by itself when done.");
const deadline = Date.now() + 15 * 60_000;
let ok = false;
while (!closed && Date.now() < deadline && ws.readyState === WebSocket.OPEN) {
  await sleep(2000);
  const { cookies = [] } = await send("Storage.getCookies");
  const mine = cookies.filter((c) => HOST.endsWith(c.domain.replace(/^\./, "")));
  if (mine.length && await check(mine)) {
    fs.writeFileSync(SESSION, JSON.stringify({ host: HOST, saved_at: new Date().toISOString(),
      cookies: mine.map(({ name, value, domain, path, expires }) => ({ name, value, domain, path, expires })) }, null, 1), { mode: 0o600 });
    fs.chmodSync(SESSION, 0o600);
    ok = true;
    break;
  }
}
send("Browser.close"); await sleep(1000);
chrome.kill();
console.log(ok ? `Done: session saved to ${SESSION}. Next: python3 absence.py`
               : "Login not finished, no session saved.");
process.exit(ok ? 0 : 1);
