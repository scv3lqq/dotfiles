// Screenshot a page in headless Chrome over CDP: real phone widths (the CLI's --window-size renders
// at least ~500px wide and crops) and JS run in the page first (clicks, typing; top-level await works).
//   node shot.mjs <url|file.html> <out.png> [width=1280] [js]
// env CHROME overrides the browser binary. Prints "<out> <width>x<height>": full page, capped at 2400px.
import { spawn } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { pathToFileURL } from "node:url";

const [target, out, width = "1280", script] = process.argv.slice(2);
if (!target || !out) {
  console.error("usage: shot.mjs <url|file.html> <out.png> [width=1280] [js]");
  process.exit(2);
}
const url = /^[a-z]+:\/\//i.test(target) ? target : pathToFileURL(resolve(target)).href;
const w = Number(width);
const profile = mkdtempSync(join(tmpdir(), "shot-"));
const port = 9300 + Math.floor(Math.random() * 600);
const chrome = spawn(
  process.env.CHROME ?? "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  // MacAppCodeSignClone leaves a ~1.5G app copy in /var/folders/*/X per launch when Chrome is killed
  [
    "--headless=new",
    "--disable-gpu",
    "--hide-scrollbars",
    "--disable-features=MacAppCodeSignClone",
    `--remote-debugging-port=${port}`,
    `--user-data-dir=${profile}`,
    "about:blank",
  ],
  { stdio: "ignore" },
);
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
// Chrome keeps writing the profile until it exits
const finish = async (code) => {
  chrome.kill();
  if (chrome.exitCode === null && chrome.signalCode === null) await new Promise((resolve) => chrome.once("exit", resolve));
  rmSync(profile, { recursive: true, force: true, maxRetries: 3 });
  process.exit(code);
};

let page;
for (let i = 0; i < 50 && !page; i++) {
  await sleep(200);
  try {
    page = (await (await fetch(`http://127.0.0.1:${port}/json/list`)).json()).find((t) => t.type === "page");
  } catch {}
}
if (!page) {
  console.error("chrome did not start");
  await finish(1);
}

const ws = new WebSocket(page.webSocketDebuggerUrl);
await new Promise((resolve) => ws.addEventListener("open", resolve));
let seq = 0;
const pending = new Map();
const listeners = new Map();
ws.addEventListener("message", (e) => {
  const msg = JSON.parse(e.data);
  if (msg.id) pending.get(msg.id)?.(msg);
  else listeners.get(msg.method)?.(msg.params);
});
const send = (method, params = {}) =>
  new Promise((resolve) => {
    pending.set(++seq, resolve);
    ws.send(JSON.stringify({ id: seq, method, params }));
  });
const metrics = (height) => send("Emulation.setDeviceMetricsOverride", { width: w, height, deviceScaleFactor: 1, mobile: w < 500 });

await metrics(900);
await send("Page.enable");
const loaded = Promise.race([new Promise((resolve) => listeners.set("Page.loadEventFired", resolve)), sleep(10_000)]);
await send("Page.navigate", { url });
await loaded;
// web fonts and the page's first fetches
await sleep(800);
if (script) {
  const r = await send("Runtime.evaluate", { expression: script, awaitPromise: true, replMode: true, returnByValue: true });
  const err = r.result?.exceptionDetails;
  if (err) {
    console.error(err.exception?.description ?? err.text);
    await finish(1);
  }
  if (r.result?.result?.value !== undefined) console.log(`js: ${JSON.stringify(r.result.result.value)}`);
  await sleep(800);
}
const height = Math.min(Math.ceil((await send("Page.getLayoutMetrics")).result.cssContentSize.height), 2400);
await metrics(height);
await sleep(300);
const shot = await send("Page.captureScreenshot", { format: "png" });
writeFileSync(out, Buffer.from(shot.result.data, "base64"));
console.log(`${out} ${w}x${height}`);
await finish(0);
