from pathlib import Path
R=Path(__file__).resolve().parents[2];H=R/'company/company-os/die-h01/engineering'
def test_only_problem_providers_route_to_playwright_strategy():
 s=(H/'h01_108_run_one.py').read_text()
 assert "PLAYWRIGHT={'gemini','chatgpt','copilot'}" in s
 assert "TEXT={'claude','qwen','manus'}" in s
 assert 'provider_svg_playwright_strategy.mjs' in s
def test_strategy_attaches_to_existing_loopback_cdp_without_browser_close():
 s=(H/'provider_svg_playwright_strategy.mjs').read_text()
 assert 'connectOverCDP(`http://127.0.0.1:${port}`' in s
 assert 'Browser.close' not in s
 assert 'browser.close' not in s
 assert '/opt/die/staging/income-os/company/muxia/node_modules/playwright/index.mjs' in s
def test_chatgpt_reuses_factory_send_selector_family():
 s=(H/'provider_svg_playwright_strategy.mjs').read_text()
 for needle in ['[data-testid="send-button"]','button[aria-label*="Send" i]','form button[type="submit"]','button[aria-label*="Submit" i]']:
  assert needle in s
 assert '[data-message-author-role="assistant"]' in s
def test_gemini_uses_baseline_new_download_control_and_expect_download():
 s=(H/'provider_svg_playwright_strategy.mjs').read_text()
 assert 'baseDownloads' in s
 assert 'download\\s*svg' in s
 assert "page.waitForEvent('download'" in s
 assert "acquisition_method:'UI_DOWNLOAD_SVG'" in s
 assert "acquisition_method:'DOM_SVG_GEOMETRY_FRAGMENT'" in s
def test_copilot_enter_primary_and_commit_evidence():
 s=(H/'provider_svg_playwright_strategy.mjs').read_text()
 assert "else{await comp.press('Enter');submitMethod='composer-enter'" in s
 assert 'commitEvidence' in s
 assert 'E_SUBMIT_NOT_COMMITTED' in s
def test_complete_svg_required_for_text_fallback():
 s=(H/'provider_svg_playwright_strategy.mjs').read_text()
 assert "t.indexOf('<svg')" in s and "t.lastIndexOf('</svg>')" in s
 assert "source_kind:'PROVIDER_RESPONSE_TEXT'" in s

def test_h01_108_prefers_existing_canonical_h01_102_blueprint():
 s=(H/'h01_108_blueprint.py').read_text()
 assert "glob('h01-102-*-blueprint.v2.json')" in s
 assert "existing.get('queue_id')==item['queue_item_id']" in s

def test_rich_composer_fill_reuses_factory_verify_then_keyboard_fallback():
 s=(H/'provider_svg_playwright_strategy.mjs').read_text()
 assert "method='locator-fill'" in s
 assert "page.keyboard.press('Control+A')" in s
 assert "page.keyboard.type(p,{delay:2})" in s
 assert "method='keyboard-type'" in s

def test_gemini_fragment_is_acquired_without_reprompt_and_normalized_downstream():
 s=(H/'provider_svg_playwright_strategy.mjs').read_text()
 assert "acquisition_method:'DOM_SVG_GEOMETRY_FRAGMENT'" in s
 assert 'provider_reprompted:false' in s
 assert 'repairPrompt' not in s
 assert 'GEMINI_SVG_ROOT_REPAIR_DISPATCHED' not in s
 assert 'E_GEMINI_REPAIR_DRIFT' not in s
