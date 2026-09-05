from pathlib import Path

R = Path(__file__).resolve().parents[3]
P = R / 'company/factory-asset/providers/qwen/linux/qwen_muxia_auth.sh'
CANARY = R / 'company/factory-asset/providers/qwen/linux/qwen_muxia_canary.mjs'
CORE = R / 'company/browser/linux/operator_browser_core.mjs'


def test_handoff_reuses_muxia_cluster_a_profile():
    s = P.read_text()
    assert 'chatgpt-linux-a' in s
    assert 'web-ai-shared' not in s
    assert 'muxia-webai-browser-runtime.mjs' in s


def test_handoff_never_contains_generation_or_secret_copy_logic():
    s = P.read_text().lower()
    for bad in ('--prompt', 'generate(', 'cookie=', 'token=', 'credentials/qwen', 'd:/assets', 'connect_over_cdp'):
        assert bad not in s


def test_login_requires_visible_display_and_runs_without_cdp_flags():
    s = P.read_text()
    assert 'FA112_QWEN_LOGIN_REQUIRES_VISIBLE_RDP_DISPLAY' in s
    login = s.split('login)', 1)[1].split(';;', 1)[0]
    assert '"$BROWSER_EXECUTABLE"' in login
    assert '--user-data-dir="$PROFILE_DIR"' in login
    assert '--remote-debugging-address' not in login
    assert '--remote-debugging-port' not in login


def test_probe_uses_muxia_runtime_and_xvfb():
    s = P.read_text()
    assert '"$XVFB" -a' in s
    assert '--command probe' in s


def test_probe_reports_no_prompt_or_credential_read_and_sanitizes_url():
    s = P.read_text()
    assert "'prompt_submitted':False" in s
    assert "'credential_values_read':False" in s
    assert 'urlsplit(raw)' in s
    assert "f'{s.scheme}://{s.netloc}{s.path}'" in s


def test_generic_muxia_status_writer_strips_query_and_fragment():
    s = CORE.read_text()
    assert 'export function sanitizeStatusUrl' in s
    assert 'new URL(String(value' in s
    assert 'return `${parsed.origin}${parsed.pathname}`' in s
    assert 'url: sanitizeStatusUrl(status?.url)' in s
    assert "url: sanitizeStatusUrl(page.url())" in s


def test_canary_uses_muxia_owned_cluster_a_and_one_bounded_dispatch():
    s = CANARY.read_text()
    assert "PlaywrightChromiumDriver" in s
    assert "/var/lib/muxia/profiles/chatgpt-linux-a/browser" in s
    assert "browser_runtime_owner: 'MUXIA'" in s
    assert s.count("composer.press('Enter')") == 1
    assert 'timeoutMs = 240000' in s


def test_canary_never_reads_session_secret_material_or_windows_paths():
    s = CANARY.read_text().lower()
    for bad in ('context.cookies', 'storage_state', 'storagestate', 'cookie=', 'token=', 'credentials/qwen', 'd:/assets', 'c:\\'):
        assert bad not in s
    assert 'credential_values_read: false' in s
    assert 'cookies_or_tokens_read: false' in s
    assert 'operator_actions_after_dispatch: 0' in s
