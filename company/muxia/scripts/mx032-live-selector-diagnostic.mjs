import fs from 'node:fs';
import path from 'node:path';
import { PlaywrightChromiumDriver } from '../dist/browser/playwright-driver.js';

const root = process.env.MUXIA_ROOT;
if (!root) throw new Error('MUXIA_ROOT_REQUIRED');
const profileDir = path.join(path.resolve(root), 'profiles', 'chatgpt-a', 'browser');
fs.mkdirSync(profileDir, { recursive: true });

const candidates = [
  '[data-testid="prompt-textarea"]',
  '#prompt-textarea',
  'textarea[placeholder*="Message" i]',
  'textarea[placeholder*="Ask" i]',
  '[contenteditable="true"][data-lexical-editor="true"]',
  'button:has-text("Log in")',
  'a:has-text("Log in")',
  'button:has-text("Sign up")',
  'a:has-text("Sign up")',
  'a[href*="/auth/login"]'
];

const driver = new PlaywrightChromiumDriver({ headless: true, launchTimeoutMs: 30_000, shutdownTimeoutMs: 5_000 });
const out = { schema: 'die.muxia.mx032-selector-diagnostic.v1', prompt_submitted: false, output_extracted: false, credential_values_read: false, selectors: {} };
try {
  const handle = await driver.launch(profileDir);
  const context = handle.browser.contexts()[0];
  const page = context.pages()[0] ?? await context.newPage();
  await page.goto('https://chatgpt.com/', { waitUntil: 'domcontentloaded', timeout: 30_000 });
  await page.waitForTimeout(3000);
  out.url = page.url();
  out.title = (await page.title()).slice(0, 200);
  for (const selector of candidates) {
    try {
      const loc = page.locator(selector);
      out.selectors[selector] = {
        count: await loc.count(),
        visible: await loc.first().isVisible({ timeout: 200 }).catch(() => false)
      };
    } catch {
      out.selectors[selector] = { count: -1, visible: false };
    }
  }
} catch (error) {
  out.error = String(error?.message ?? error).slice(0, 500);
} finally {
  await driver.stop().catch(() => undefined);
}
console.log(JSON.stringify(out, null, 2));
