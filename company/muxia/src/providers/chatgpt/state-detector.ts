import type { Page } from 'playwright';
import type {
  ProviderPageSnapshot,
  ProviderStateObservation,
  ProviderStateReason,
} from '../contract.js';

const BODY_TEXT_LIMIT = 16_384;

const COMPOSER_SELECTORS = [
  '[data-testid="prompt-textarea"]',
  '#prompt-textarea',
  'textarea[placeholder*="Message" i]',
  'textarea[placeholder*="Ask" i]',
  '[contenteditable="true"][data-lexical-editor="true"]',
] as const;

const LOGIN_SELECTORS = [
  'a[href*="/auth/login"]',
  'button:has-text("Log in")',
  'a:has-text("Log in")',
  'button:has-text("Sign up")',
  'a:has-text("Sign up")',
  'button[data-testid*="login" i]',
  'a[data-testid*="login" i]',
] as const;

const RATE_LIMIT_PATTERNS = [
  /too many requests/i,
  /rate limit/i,
  /you(?:'|’)ve reached (?:the )?(?:current )?(?:usage )?limit/i,
  /you have reached (?:the )?(?:current )?(?:usage )?limit/i,
  /try again later/i,
] as const;

const PROTECTION_PATTERNS = [
  /verify (?:that )?you(?:'|’)re human/i,
  /verify you are human/i,
  /checking your browser/i,
  /security check/i,
  /challenge-platform/i,
  /captcha/i,
] as const;

const PROTECTION_TITLE_PATTERNS = [
  /^just a moment\.{0,3}$/i,
  /attention required.*cloudflare/i,
  /security verification/i,
  /checking your browser/i,
] as const;

const ACCOUNT_BLOCKED_PATTERNS = [
  /account (?:has been )?(?:deactivated|disabled|suspended)/i,
  /account is (?:deactivated|disabled|suspended)/i,
  /your account has been blocked/i,
] as const;

const ACCESS_DENIED_PATTERNS = [
  /access denied/i,
  /you do not have access/i,
  /not available in your (?:country|region)/i,
  /unsupported (?:country|region)/i,
] as const;

const LOGIN_TEXT_PATTERNS = [
  /\blog in\b/i,
  /\bsign in\b/i,
  /\bcreate account\b/i,
  /\bsign up\b/i,
] as const;

function matchesAny(text: string, patterns: readonly RegExp[]): boolean {
  return patterns.some((pattern) => pattern.test(text));
}

function hasAnySelector(snapshot: ProviderPageSnapshot, selectors: readonly string[]): boolean {
  return selectors.some((selector) => snapshot.visibleSelectors.includes(selector));
}

function observation(
  snapshot: ProviderPageSnapshot,
  state: ProviderStateObservation['state'],
  reason: ProviderStateReason,
  signals: string[],
  observedAt: string,
): ProviderStateObservation {
  return {
    state,
    reason,
    url: snapshot.url,
    observedAt,
    signals,
    operatorActionRequired: state !== 'READY',
  };
}

export function classifyChatGptSnapshot(
  snapshot: ProviderPageSnapshot,
  observedAt = new Date().toISOString(),
): ProviderStateObservation {
  const text = snapshot.bodyText.slice(0, BODY_TEXT_LIMIT);
  const url = snapshot.url;
  const title = snapshot.title.slice(0, 256);

  if (matchesAny(title, PROTECTION_TITLE_PATTERNS)) {
    return observation(snapshot, 'BLOCKED', 'PROTECTION_CHALLENGE', ['protection-title'], observedAt);
  }

  if (matchesAny(text, ACCOUNT_BLOCKED_PATTERNS)) {
    return observation(snapshot, 'BLOCKED', 'ACCOUNT_BLOCKED', ['account-blocked-text'], observedAt);
  }

  if (matchesAny(text, ACCESS_DENIED_PATTERNS)) {
    return observation(snapshot, 'BLOCKED', 'ACCESS_DENIED', ['access-denied-text'], observedAt);
  }

  if (matchesAny(text, PROTECTION_PATTERNS)) {
    return observation(snapshot, 'BLOCKED', 'PROTECTION_CHALLENGE', ['protection-text'], observedAt);
  }

  if (matchesAny(text, RATE_LIMIT_PATTERNS)) {
    return observation(snapshot, 'BLOCKED', 'RATE_LIMIT', ['rate-limit-text'], observedAt);
  }

  const authUrl = /(?:auth\.openai\.com|chatgpt\.com\/auth|chat\.openai\.com\/auth)/i.test(url);
  const authSelector = hasAnySelector(snapshot, LOGIN_SELECTORS);
  const authText = matchesAny(text, LOGIN_TEXT_PATTERNS);
  if (authUrl || authSelector || (authText && !hasAnySelector(snapshot, COMPOSER_SELECTORS))) {
    const signals = [
      ...(authUrl ? ['auth-url'] : []),
      ...(authSelector ? ['login-selector'] : []),
      ...(authText ? ['login-text'] : []),
    ];
    return observation(snapshot, 'AUTH_REQUIRED', 'LOGIN_REQUIRED', signals, observedAt);
  }

  if (hasAnySelector(snapshot, COMPOSER_SELECTORS)) {
    return observation(snapshot, 'READY', 'COMPOSER_READY', ['composer-visible'], observedAt);
  }

  return observation(snapshot, 'UNKNOWN', 'UNRECOGNIZED_PAGE', ['no-known-safe-state'], observedAt);
}

async function firstVisible(page: Page, selectors: readonly string[]): Promise<string[]> {
  const visible: string[] = [];
  for (const selector of selectors) {
    try {
      const locator = page.locator(selector).first();
      if (await locator.isVisible({ timeout: 250 })) visible.push(selector);
    } catch {
      // Missing/invalid/transient DOM state is non-fatal; classification fails closed later.
    }
  }
  return visible;
}

export async function detectChatGptPageState(
  page: Page,
  observedAt = new Date().toISOString(),
): Promise<ProviderStateObservation> {
  const url = page.url();
  let title = '';
  let bodyText = '';
  try {
    title = (await page.title()).slice(0, 256);
  } catch {
    title = '';
  }
  try {
    bodyText = (await page.locator('body').innerText({ timeout: 1_000 })).slice(0, BODY_TEXT_LIMIT);
  } catch {
    bodyText = '';
  }

  const visibleSelectors = [
    ...(await firstVisible(page, COMPOSER_SELECTORS)),
    ...(await firstVisible(page, LOGIN_SELECTORS)),
  ];

  return classifyChatGptSnapshot({ url, title, bodyText, visibleSelectors }, observedAt);
}

export const CHATGPT_STATE_DETECTOR_VERSION = 'chatgpt-state-detector-v1.1';
