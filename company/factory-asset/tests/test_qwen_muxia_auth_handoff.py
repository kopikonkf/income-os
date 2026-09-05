from pathlib import Path
R=Path(__file__).resolve().parents[3]
P=R/'company/factory-asset/providers/qwen/linux/qwen_muxia_auth.sh'
def test_handoff_is_muxia_owned_and_production_profile_isolated():
 s=P.read_text();assert 'web-ai-shared' in s;assert 'muxia-webai-browser-runtime.mjs' in s;assert 'chatgpt-linux-a' not in s
def test_handoff_never_contains_generation_or_secret_copy_logic():
 s=P.read_text().lower()
 for bad in ('--prompt','generate(', 'cookie=', 'token=', 'credentials/qwen', 'd:/assets', 'connect_over_cdp'):
  assert bad not in s
def test_login_requires_visible_display_and_probe_uses_xvfb():
 s=P.read_text();assert 'FA112_QWEN_LOGIN_REQUIRES_VISIBLE_RDP_DISPLAY' in s;assert '"$XVFB" -a' in s;assert '--command launch' in s and '--command probe' in s
def test_probe_reports_no_prompt_or_credential_read():
 s=P.read_text();assert "'prompt_submitted':False" in s;assert "'credential_values_read':False" in s
