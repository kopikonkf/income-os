from pathlib import Path
import json
import subprocess
import tempfile

R=Path(__file__).resolve().parents[3]
DRIVER=R/'company/browser/linux/external_cdp_attach_driver.mjs'
OWNER=R/'company/browser/linux/external_chrome_owner.sh'
LAUNCHER=R/'company/muxia/scripts/linux/muxia-cluster-broker.mjs'
CORE=R/'company/browser/linux/cluster_broker_core.mjs'
SYSTEMD=R/'company/factory-asset/systemd'
REG=R/'company/factory-asset/registries/web-ai-clusters.v1.json'
INSTALL=R/'company/factory-asset/bin/install_fa338_job_scoped_lifecycle.sh'


def test_attach_driver_remains_as_rollback_reference_and_is_loopback_only():
 s=DRIVER.read_text()
 assert "debugHost !== '127.0.0.1'" in s
 assert 'connectOverCDP' in s
 assert 'Browser.close' in s
 assert 'this.browser = null' in s
 assert 'await this.browser.close(' not in s and 'this.browser.close(' not in s


def test_owner_script_remains_non_playwright_rollback_material():
 s=OWNER.read_text().lower()
 assert '/usr/bin/google-chrome-stable' in s
 assert '--remote-debugging-address=127.0.0.1' in s
 assert '--remote-debugging-port=' in s
 assert '--user-data-dir=' in s
 for bad in ('playwright','enable-automation','launchpersistentcontext','connectovercdp'):
  assert bad not in s


def test_launcher_supports_both_historical_attach_and_fa338_owned_browser_modes():
 s=LAUNCHER.read_text()
 assert "arg('--attach-cdp-port', '0')" in s
 assert 'ExternalCdpAttachDriver' in s
 assert 'PlaywrightChromiumDriver' in s
 assert "arg('--headless', 'true')" in s


def test_core_can_report_driver_owner_model():
 s=CORE.read_text()
 assert "this.handle.ownerModel || 'SINGLE_LONG_LIVED_CHROMIUM_PROCESS'" in s


def test_historical_split_owner_units_are_retained_but_fa338_disables_them():
 a=(SYSTEMD/'die-fa121-cluster-broker.service').read_text();b=(SYSTEMD/'die-muxia-cluster-b.service').read_text()
 ao=(SYSTEMD/'die-muxia-cluster-a-browser.service').read_text();bo=(SYSTEMD/'die-muxia-cluster-b-browser.service').read_text()
 assert 'requires=die-muxia-cluster-a-browser.service' in a.lower() and '--attach-cdp-port 39221' in a
 assert 'requires=die-muxia-cluster-b-browser.service' in b.lower() and '--attach-cdp-port 39222' in b
 assert '--debug-port 39221' in ao and '--debug-port 39222' in bo
 cut=INSTALL.read_text()
 for unit in ['die-fa121-cluster-broker.service','die-muxia-cluster-a-browser.service','die-muxia-cluster-b.service','die-muxia-cluster-b-browser.service']:
  assert unit in cut
 assert 'disable --now' in cut


def test_registry_is_now_job_scoped_not_external_persistent():
 d=json.loads(REG.read_text());assert d['revision'].startswith('1.5.0-fa338')
 assert 'JOB_SCOPED' in d['rules']['browser_owner_model']
 for c in d['clusters']:
  assert c['browser_owner_model']=='JOB_SCOPED_HEADFUL_BROWSER_CDP'
  assert c['runtime_owner']=='FA338_JOB_SCOPED_MUXIA_BROKER_BROWSER_RUNTIME'
  assert c['browser_executable']=='/usr/bin/google-chrome-stable'
  assert c['browser_debug_host']=='127.0.0.1'


def test_external_driver_rejects_non_loopback_config_without_network():
 with tempfile.TemporaryDirectory() as td:
  h=Path(td)/'h.mjs';h.write_text(f'''import {{ ExternalCdpAttachDriver }} from {json.dumps(DRIVER.as_uri())};let e='';try{{new ExternalCdpAttachDriver({{debugHost:'0.0.0.0',debugPort:39221,playwrightEntry:'/x',ownerPidFile:'/y'}})}}catch(x){{e=String(x.message||x)}}console.log(e);''')
  r=subprocess.run(['node',str(h)],capture_output=True,text=True,check=True,timeout=30)
  assert 'E_EXTERNAL_CDP_NON_LOOPBACK' in r.stdout
