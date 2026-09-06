from __future__ import annotations
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import subprocess
import tempfile
import pytest

R = Path(__file__).resolve().parents[3]
RUNNER = R / 'company/factory-asset/bin/run_fa121_stability_canary.mjs'

def _broker() -> dict:
    cp = subprocess.run(['curl','-fsS','--max-time','3','http://127.0.0.1:39121/v1/status'], text=True, capture_output=True, timeout=5)
    if cp.returncode != 0:
        pytest.skip('live FA-121 broker not available')
    return json.loads(cp.stdout)

def _run(args, timeout=12):
    return subprocess.run(['node', str(RUNNER), *args], cwd=R, text=True, capture_output=True, timeout=timeout, check=True)

def test_live_safe_init_status_reconcile_tick_oneshots_exit_and_preserve_broker():
    before = _broker()
    assert before['state'] == 'READY'
    assert before['tab_leases']['active_leases'] == 0
    assert before['tab_leases']['open_pages'] <= 8
    owner_pid = before['browser_owner_pid']
    with tempfile.TemporaryDirectory(prefix='fa121-oneshot-') as td:
        state_root = Path(td)
        assert json.loads(_run(['init','--repo-root',str(R),'--state-root',str(state_root),'--repo-revision','TEST-ONESHOT']).stdout)['result'] == 'INITIALIZED'
        assert json.loads(_run(['status','--repo-root',str(R),'--state-root',str(state_root)]).stdout)['provider_calls_performed'] == 0
        assert json.loads(_run(['reconcile','--repo-root',str(R),'--state-root',str(state_root)]).stdout)['action'] == 'RECONCILED'
        state = json.loads((state_root/'state.json').read_text())
        start = datetime.fromisoformat(state['start_at'].replace('Z','+00:00'))
        before_start = (start - timedelta(minutes=1)).astimezone(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
        tick = json.loads(_run(['tick','--repo-root',str(R),'--state-root',str(state_root),'--now',before_start]).stdout)
        assert tick['action'] == 'HEARTBEAT_ONLY_BEFORE_START'
        assert json.loads(_run(['status','--repo-root',str(R),'--state-root',str(state_root)]).stdout)['provider_calls_performed'] == 0
    after = _broker()
    assert after['state'] == 'READY'
    assert after['browser_owner_pid'] == owner_pid
    assert after['tab_leases']['active_leases'] == 0
    assert after['tab_leases']['open_pages'] <= 8
