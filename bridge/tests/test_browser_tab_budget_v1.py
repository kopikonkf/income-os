from __future__ import annotations
import json, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
TAB=ROOT/'company/browser/linux/tab_budget.mjs'
OP=ROOT/'company/browser/linux/operator_browser_core.mjs'
WAKE=ROOT/'company/browser/linux/wake_transport_core.mjs'
MUXIA=ROOT/'company/muxia/scripts/linux/muxia-chatgpt-image.mjs'

def test_tab_budget_behavior_closes_excess_and_preserves_requested_page():
    source=f'''import {{enforceTabBudget,MAX_TABS_PER_PRINCIPAL}} from {json.dumps(TAB.as_uri())};
const pages=[0,1,2,3,4,5,6,7,8,9].map(i=>({{i,closed:false,isClosed(){{return this.closed}},async close(){{this.closed=true}}}}));
const context={{pages(){{return pages.filter(p=>!p.closed)}}}};
const r=await enforceTabBudget(context,{{preserve:[pages[0]],maxTabs:MAX_TABS_PER_PRINCIPAL}});
console.log(JSON.stringify({{r,open:context.pages().map(p=>p.i),preservedClosed:pages[0].closed}}));'''
    cp=subprocess.run(['node','--input-type=module','-e',source],text=True,capture_output=True,check=False)
    assert cp.returncode==0,cp.stderr
    v=json.loads(cp.stdout)
    assert v['r']=={'before':10,'after':8,'closed':2}
    assert v['preservedClosed'] is False
    assert len(v['open'])==8 and 0 in v['open']

def test_persistent_principals_enforce_eight_tab_ceiling_and_rotation_reclaims_tabs():
    op=OP.read_text(); wake=WAKE.read_text()
    assert 'MAX_TABS_PER_PRINCIPAL' in op and 'enforceTabBudget' in op
    assert 'MAX_TABS_PER_PRINCIPAL' in wake and 'enforceTabBudget' in wake
    assert 'maxTabs: 1' in wake
    assert 'context.newPage()' in wake

def test_muxia_uses_bounded_composer_reacquisition_and_tab_budget():
    s=MUXIA.read_text()
    assert 'COMPOSER_SELECTORS' in s
    for token in ['data-testid="prompt-textarea"','#prompt-textarea','Message','data-lexical-editor']:
        assert token in s
    assert 'acquireAndFillComposer' in s
    assert 'composer_acquisition_attempt' in s
    assert 'CHATGPT_COMPOSER_REACQUIRE_FAILED' in s
    assert 'MAX_TABS_PER_PRINCIPAL' in s and 'enforceTabBudget' in s
    assert "page.locator('#prompt-textarea').first()" not in s
