from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
READINESS = ROOT / "company/browser/linux/provider_readiness.mjs"
WORKER = ROOT / "company/factory-asset/lib/console_broker_provider_worker.mjs"
PROFILES = ROOT / "company/factory-asset/registries/provider-readiness-profiles.v1.json"


def _run_node(source: str) -> dict:
    with tempfile.TemporaryDirectory() as td:
        script = Path(td) / "probe.mjs"
        script.write_text(source, encoding="utf-8")
        result = subprocess.run(["node", str(script)], capture_output=True, text=True, timeout=30, check=True)
        return json.loads(result.stdout.strip())


def test_chatgpt_cloudflare_just_a_moment_is_checkpoint_not_composer_error():
    value = _run_node(
        f'''
import {{ classifyProviderPage }} from {json.dumps(READINESS.as_uri())};
import fs from 'node:fs/promises';
const profile=JSON.parse(await fs.readFile({json.dumps(str(PROFILES))},'utf8')).providers.chatgpt;
const empty=()=>({{count:async()=>0,nth:()=>({{isVisible:async()=>false}}),innerText:async()=>''}});
const page={{
  url:()=> 'https://chatgpt.com/',
  title:async()=> 'Just a moment...',
  locator:()=>empty(),
}};
const result=await classifyProviderPage({{page,providerId:'chatgpt',profile,observedAt:'2026-09-08T03:00:00Z'}});
console.log(JSON.stringify(result));
'''
    )
    assert value["state"] == "CHECKPOINT"
    assert value["reason_code"] == "PROTECTION_CHALLENGE"
    assert value["composer_visible"] is False
    assert value["composer_writable"] is False
    assert value["operator_action_required"] is True
    assert value["credential_values_read"] is False
    assert value["cookies_or_tokens_read"] is False


def test_chatgpt_profile_has_specific_composer_selectors_before_generic_fallbacks():
    profile = json.loads(PROFILES.read_text(encoding="utf-8"))["providers"]["chatgpt"]
    selectors = profile["composer_selectors"]
    assert selectors[:6] == [
        '[data-testid="prompt-textarea"]',
        '#prompt-textarea',
        'div#prompt-textarea[contenteditable="true"]',
        '[contenteditable="true"][data-lexical-editor="true"]',
        '[contenteditable="true"][role="textbox"]',
        'form [contenteditable="true"]',
    ]
    assert selectors[-2:] == ["textarea", '[contenteditable="true"]']


def test_chatgpt_submit_uses_keyboard_fallback_and_verified_write():
    value = _run_node(
        f'''
import {{ fillAndSubmitChatGpt }} from {json.dumps(WORKER.as_uri())};
let text=''; let sendClicked=false; let fillCalls=0; let keyboardTypes=0;
const composer={{
  isVisible:async()=>true,
  isEditable:async()=>true,
  click:async()=>{{}},
  fill:async()=>{{fillCalls+=1; throw new Error('synthetic lexical fill failure');}},
  evaluate:async()=>text,
  press:async()=>{{throw new Error('enter fallback should not be needed');}},
}};
const invisible={{isVisible:async()=>false,isEditable:async()=>false,click:async()=>{{}},isEnabled:async()=>false}};
const send={{isVisible:async()=>true,isEnabled:async()=>true,click:async()=>{{sendClicked=true;}}}};
const page={{
  locator:(selector)=>({{first:()=> selector==='[data-testid="prompt-textarea"]'?composer:(selector==='[data-testid="send-button"]'?send:invisible)}}),
  keyboard:{{press:async()=>{{}},type:async(value)=>{{keyboardTypes+=1;text=value;}}}},
  waitForTimeout:async()=>{{}},
}};
const result=await fillAndSubmitChatGpt(page,'bounded synthetic prompt');
console.log(JSON.stringify({{result,text,sendClicked,fillCalls,keyboardTypes}}));
'''
    )
    assert value["text"] == "bounded synthetic prompt"
    assert value["sendClicked"] is True
    assert value["fillCalls"] == 1
    assert value["keyboardTypes"] == 1
    assert value["result"]["write_method"] == "keyboard-type"
    assert value["result"]["send_selector"] == '[data-testid="send-button"]'


def test_hardening_code_does_not_read_browser_secrets():
    text = (READINESS.read_text(encoding="utf-8") + WORKER.read_text(encoding="utf-8")).lower()
    for forbidden in (
        "context.cookies",
        "storagestate",
        "localstorage",
        "sessionstorage",
        "indexeddb",
        "document.cookie",
        "authorization",
    ):
        assert forbidden not in text
