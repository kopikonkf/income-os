function safeUrl(raw) {
  try { const u = new URL(raw); return `${u.origin}${u.pathname}`; } catch { return ''; }
}

async function anyVisible(page, selectors = []) {
  for (const selector of selectors) {
    const loc = page.locator(selector);
    const n = Math.min(await loc.count().catch(() => 0), 20);
    for (let i = 0; i < n; i += 1) if (await loc.nth(i).isVisible().catch(() => false)) return true;
  }
  return false;
}

async function bodyContains(page, patterns = []) {
  if (!patterns.length) return false;
  const text = (await page.locator('body').innerText().catch(() => '')).toLowerCase();
  return patterns.some((p) => text.includes(String(p).toLowerCase()));
}

export function sanitizeProviderStatusUrl(raw) { return safeUrl(raw); }

export async function classifyProviderPage({ page, providerId, profile, observedAt = new Date().toISOString() }) {
  if (!page || !providerId || !profile) throw new Error('E_PROVIDER_READINESS_CONFIG');
  const url = safeUrl(page.url());
  let origin = '';
  try { origin = new URL(page.url()).origin; } catch {}
  const allowed = Array.isArray(profile.allowed_origins) && profile.allowed_origins.includes(origin);
  const authVisible = await anyVisible(page, profile.auth_selectors || []);
  const checkpointVisible = await bodyContains(page, profile.checkpoint_patterns || []);
  const composerVisible = await anyVisible(page, profile.composer_selectors || []);
  let state = 'DEGRADED'; let reasonCode = 'COMPOSER_NOT_READY';
  if (!allowed) { state = 'UNAVAILABLE'; reasonCode = 'ORIGIN_MISMATCH'; }
  else if (checkpointVisible) { state = 'CHECKPOINT'; reasonCode = 'PROTECTION_CHALLENGE'; }
  else if (authVisible || /\/(login|signin|signup|auth)(?:\/|$)/i.test(new URL(page.url()).pathname)) { state = 'AUTH_REQUIRED'; reasonCode = 'AUTH_UI_VISIBLE'; }
  else if (composerVisible) { state = 'HEALTHY'; reasonCode = 'COMPOSER_READY'; }
  return {
    schema: 'die.muxia.provider-readiness.v1', provider_id: providerId, state, reason_code: reasonCode,
    safe_url: url, observed_at: observedAt, composer_visible: composerVisible,
    auth_ui_visible: authVisible, checkpoint_visible: checkpointVisible,
    operator_action_required: state === 'AUTH_REQUIRED' || state === 'CHECKPOINT',
    credential_values_read: false, cookies_or_tokens_read: false,
  };
}

export async function probeProviderReadiness({ context, providerId, profile, claimUrl = null, observedAt = new Date().toISOString() }) {
  const pages = context.pages().filter((p) => !p.isClosed());
  let page = null;
  if (claimUrl) page = pages.find((p) => p.url() === claimUrl) || null;
  if (!page) {
    for (const candidate of pages) {
      try { if ((profile.allowed_origins || []).includes(new URL(candidate.url()).origin)) { page = candidate; break; } } catch {}
    }
  }
  if (!page) return {
    schema:'die.muxia.provider-readiness.v1',provider_id:providerId,state:'UNAVAILABLE',reason_code:'PAGE_NOT_FOUND',safe_url:'',observed_at:observedAt,
    composer_visible:false,auth_ui_visible:false,checkpoint_visible:false,operator_action_required:false,credential_values_read:false,cookies_or_tokens_read:false,
  };
  return await classifyProviderPage({ page, providerId, profile, observedAt });
}

export function aggregateClusterReadiness(results) {
  const active = results.filter((x) => x.membership === 'ACTIVE');
  if (!active.length) return 'OFFLINE';
  const healthy = active.filter((x) => x.state === 'HEALTHY').length;
  if (healthy === active.length) return 'HEALTHY';
  if (healthy > 0) return 'DEGRADED';
  return active.some((x) => ['AUTH_REQUIRED','CHECKPOINT','DEGRADED'].includes(x.state)) ? 'DEGRADED' : 'OFFLINE';
}
