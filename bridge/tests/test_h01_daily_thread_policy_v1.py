from pathlib import Path
from datetime import datetime,timezone
import importlib.util,tempfile
R=Path(__file__).resolve().parents[2]; H=R/'company/company-os/die-h01/engineering'
sp=importlib.util.spec_from_file_location('daily',H/'h01_daily_thread_policy.py');M=importlib.util.module_from_spec(sp);sp.loader.exec_module(M)

def test_jakarta_midnight_rollover_exact():
    assert M.local_day(datetime(2026,9,13,16,59,59,tzinfo=timezone.utc))=='2026-09-13'
    assert M.local_day(datetime(2026,9,13,17,0,0,tzinfo=timezone.utc))=='2026-09-14'

def test_one_thread_per_provider_profile_day():
    with tempfile.TemporaryDirectory() as td:
        reg=Path(td)/'r.json'; runs=Path(td)/'runs'; runs.mkdir(); url='https://chat.qwen.ai/c/day-one'
        assert M.record_dispatch('qwen','h01-web-p001',url,'a'*64,'job1','2026-09-13T17:10:00Z',runs,reg)['dispatch_count']==1
        assert M.resolve('qwen','h01-web-p001',runs,reg,datetime(2026,9,13,18,0,tzinfo=timezone.utc))['conversation_url']==url
        assert M.record_dispatch('qwen','h01-web-p001',url,'b'*64,'job2','2026-09-13T18:20:00Z',runs,reg)['dispatch_count']==2
        failed=False
        try:M.record_dispatch('qwen','h01-web-p001','https://chat.qwen.ai/c/other','c'*64,'job3','2026-09-13T18:30:00Z',runs,reg)
        except RuntimeError:failed=True
        assert failed

def test_success_rate_auditable():
    with tempfile.TemporaryDirectory() as td:
        reg=Path(td)/'r.json';runs=Path(td)/'runs';runs.mkdir();url='https://chatgpt.com/c/day-one'
        M.record_dispatch('chatgpt','h01-web-p001',url,'a'*64,'j1','2026-09-13T17:01:00Z',runs,reg)
        M.record_dispatch('chatgpt','h01-web-p001',url,'b'*64,'j2','2026-09-13T17:02:00Z',runs,reg)
        r=M.mark_success('chatgpt','h01-web-p001','j1',reg,datetime(2026,9,13,18,0,tzinfo=timezone.utc))
        assert r['success_count']==1 and r['success_rate']==0.5

def test_run_one_uses_daily_thread_all_provider_paths():
    s=(H/'h01_108_run_one.py').read_text()
    assert 'resolve_daily_thread(provider,profile,ns.runs_root)' in s
    assert "provider_url=thread_url or ORIGIN[provider]" in s
    assert s.count("'--thread-url',thread_url")>=2
    assert 'record_daily_dispatch' in s and 'mark_daily_success' in s
