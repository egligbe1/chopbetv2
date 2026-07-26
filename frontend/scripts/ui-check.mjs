/**
 * ui-check.mjs — drive the app in a real browser to eyeball a change and catch
 * client-side crashes (like the React #310 hooks bug) before they ship.
 *
 * Runs HEADED by default (a visible window opens on your PC) using your real
 * installed Chrome when available, falling back to Playwright's Chromium.
 * Captures console output, uncaught page errors, and a screenshot per route.
 *
 * Setup (once):
 *   cd frontend
 *   npm install                 # installs playwright-core (devDependency)
 *   npx playwright-core install chromium   # only needed for the Chromium fallback
 *
 * Usage:
 *   npm run ui-check                                  # localhost:3000, default routes
 *   npm run ui-check -- --base=http://localhost:3003  # different port
 *   npm run ui-check -- --routes=/,/results,/stats,/admin
 *   npm run ui-check -- --url=https://chopbets.onrender.com   # a full URL, once
 *
 * Env vars:
 *   HEADLESS=1        run without a window (pure error capture / CI)
 *   SLOWMO=400        ms delay between actions so you can follow along (default 300)
 *   CDP=http://localhost:9222   attach to YOUR already-open Chrome instead of launching
 *                               (start it with: chrome --remote-debugging-port=9222)
 *
 * Exit code is non-zero if any route logs an uncaught error — handy for gating.
 */
import { chromium } from 'playwright-core';
import { mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));
const SHOTS_DIR = join(__dirname, 'screenshots');

// ── parse args ───────────────────────────────────────────────────────────────
const args = Object.fromEntries(
  process.argv.slice(2)
    .filter((a) => a.startsWith('--'))
    .map((a) => { const [k, ...v] = a.slice(2).split('='); return [k, v.join('=') || true]; })
);
const HEADLESS = process.env.HEADLESS === '1' || process.env.HEADLESS === 'true';
const SLOWMO = Number(process.env.SLOWMO ?? 300);
const CDP = process.env.CDP;
const base = args.base || 'http://localhost:3000';
const targets = args.url
  ? [String(args.url)]
  : String(args.routes || '/,/results,/stats,/admin')
      .split(',').map((r) => r.trim()).filter(Boolean)
      .map((r) => base.replace(/\/$/, '') + (r.startsWith('/') ? r : '/' + r));

mkdirSync(SHOTS_DIR, { recursive: true });

// ── launch (or attach) ───────────────────────────────────────────────────────
async function getBrowser() {
  if (CDP) {
    console.log(`Attaching to your Chrome over CDP at ${CDP} ...`);
    return { browser: await chromium.connectOverCDP(CDP), attached: true };
  }
  // Prefer the user's real Chrome; fall back to bundled Chromium.
  try {
    return { browser: await chromium.launch({ headless: HEADLESS, channel: 'chrome', slowMo: SLOWMO }), attached: false };
  } catch {
    console.log('Real Chrome not found — using Playwright Chromium.');
    return { browser: await chromium.launch({ headless: HEADLESS, slowMo: SLOWMO }), attached: false };
  }
}

const { browser, attached } = await getBrowser();
const context = attached ? browser.contexts()[0] ?? await browser.newContext() : await browser.newContext();

let hadError = false;
for (const url of targets) {
  const page = await context.newPage();
  const errors = [];
  const consoleErrors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('console', (m) => { if (m.type() === 'error') consoleErrors.push(m.text()); });

  process.stdout.write(`\n▶ ${url}\n`);
  try {
    await page.goto(url, { waitUntil: 'networkidle', timeout: 60000 });
  } catch (e) {
    consoleErrors.push(`goto failed: ${e.message}`);
  }
  await page.waitForTimeout(2500);

  const name = (url.replace(/^https?:\/\//, '').replace(/[^\w.-]+/g, '_') || 'root').slice(0, 80);
  const shot = join(SHOTS_DIR, `${name}.png`);
  await page.screenshot({ path: shot, fullPage: true }).catch(() => {});

  const bodyText = (await page.locator('body').innerText().catch(() => '')).slice(0, 120).replace(/\s+/g, ' ');
  const crashed = errors.length > 0 || /Application error: a client-side exception/i.test(bodyText);
  hadError ||= crashed;

  console.log(`   screenshot: ${shot}`);
  console.log(`   preview:    ${bodyText}`);
  if (errors.length) console.log(`   ❌ uncaught: ${errors.join(' | ')}`);
  // Filter out third-party noise (analytics/CORS on non-prod origins) from the console summary.
  const notable = consoleErrors.filter((t) => !/google-analytics|gtag|CORS policy|ERR_FAILED/i.test(t));
  if (notable.length) console.log(`   ⚠ console:  ${notable.slice(0, 5).join(' | ')}`);
  if (!crashed && !notable.length) console.log('   ✓ no errors');

  await page.close();
}

if (attached) { /* leave your Chrome open */ } else { await browser.close(); }
console.log(hadError ? '\nDONE — errors found ❌' : '\nDONE — all routes clean ✓');
process.exit(hadError ? 1 : 0);
