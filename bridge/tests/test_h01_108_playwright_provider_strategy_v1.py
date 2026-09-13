from pathlib import Path
R=Path(__file__).resolve().parents[2];H=R/'company/company-os/die-h01/engineering'
def test_only_problem_providers_route_to_playwright_strategy():
 s=(H/'h01_108_run_one.py').read_text()
 assert "PLAYWRIGHT={'gemini','chatgpt','copilot','qwen'}" in s
 assert "TEXT={'claude','manus'}" in s
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
 assert "submitMethod='composer-enter';await comp.press('Enter')" in s
 assert 'commitEvidence' in s
 assert 'E_SUBMIT_NOT_COMMITTED' in s
def test_complete_svg_required_for_text_fallback():
 s=(H/'provider_svg_playwright_strategy.mjs').read_text()
 assert "matchAll(/<svg\\b[\\s\\S]*?<\\/svg>/gi)" in s
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


def test_qwen_reuses_playwright_and_requires_strong_dispatch_commit():
 s=(H/'provider_svg_playwright_strategy.mjs').read_text()
 assert "qwen:{origin:'https://chat.qwen.ai'" in s
 assert "provider==='qwen'" in s
 assert "url!==beforeUrl||responses>beforeResponses" in s
 assert "textarea[placeholder*=\"Ask Qwen\" i]" in s
 assert "provider==='gemini'||provider==='qwen'" in s

def test_dispatch_receipt_is_written_immediately_after_strong_commit():
 s=(H/'provider_svg_playwright_strategy.mjs').read_text()
 assert "dispatchReceiptFile=arg('--dispatch-receipt','')" in s
 assert 'function writeDispatch' in s
 assert "status:'COMMITTED'" in s
 assert 'writeDispatch(commit,submitMethod)' in s
 assert "provider_reprompted:false" in s

def test_playwright_supports_read_only_same_conversation_recheck():
 s=(H/'provider_svg_playwright_strategy.mjs').read_text()
 assert "recheckUrl=arg('--recheck-url','')" in s
 assert 'const recheckOnly=!!recheckUrl' in s
 assert "submitMethod='READ_ONLY_RECHECK'" in s
 assert 'if(!recheckOnly)' in s

def test_all_provider_paths_emit_durable_dispatch_commit_receipt():
 run=(H/'h01_108_run_one.py').read_text()
 text=(H/'provider_text_svg_cdp_canary.mjs').read_text()
 assert run.count("'--dispatch-receipt'") >= 2
 assert "dispatchReceiptFile=arg('--dispatch-receipt','')" in text
 assert "status:'COMMITTED'" in text
 assert 'commitEnd=Date.now()+15000' in text
 assert "if(!commit?.committed)throw new Error(`E_SUBMIT_NOT_COMMITTED" in text

def test_daily_thread_extractor_selects_latest_complete_svg_not_first_to_last_blob():
 s=(H/'provider_svg_playwright_strategy.mjs').read_text()
 assert "matchAll(/<svg\\b[\\s\\S]*?<\\/svg>/gi)" in s
 assert 'for(let i=xs.length-1;i>=0;i--)' in s
 assert "t.lastIndexOf('</svg>')" not in s

def test_playwright_daily_thread_stabilizes_baseline_before_submit():
 s=(H/'provider_svg_playwright_strategy.mjs').read_text()
 assert "threadUrl=arg('--thread-url','')" in s
 assert 'async function settleThreadBaseline()' in s
 assert 'if(threadUrl&&!recheckOnly)await settleThreadBaseline()' in s
 assert 'const baseCandidates=' in s
 assert '.filter(x=>!baseCandidates.has(sha(x)))' in s
 assert 'E_DAILY_THREAD_DRIFT' in s

def test_raw_cdp_daily_thread_uses_only_post_baseline_svg_delta():
 s=(H/'provider_text_svg_cdp_canary.mjs').read_text()
 assert "threadUrl=arg('--thread-url','')" in s
 assert 'async function responseSnapshot' in s
 assert 'async function settleThreadBaseline' in s
 assert 'const baselineSvgHashes=await settleThreadBaseline(cdp,cfg,threadUrl)' in s
 assert "fresh=(snap.svgs||[]).filter(x=>!baselineSvgHashes.has(sha(x)))" in s
 assert "candidate=fresh.length?fresh[fresh.length-1]:''" in s
 assert 'E_DAILY_THREAD_DRIFT_PRE_SUBMIT' in s
 assert 'E_DAILY_THREAD_DRIFT' in s

def test_raw_cdp_svg_surface_is_complete_document_scoped_not_history_blob():
 s=(H/'provider_text_svg_cdp_canary.mjs').read_text()
 assert "const SVG_DOC_PATTERN='<svg\\\\b[\\\\s\\\\S]*?</svg>'" in s
 assert "new RegExp(${JSON.stringify(SVG_DOC_PATTERN)},'gi')" in s
 assert 't.matchAll(re)' in s
 assert "t.lastIndexOf('</svg>')" not in s
