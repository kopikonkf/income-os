from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
VNC=ROOT/'company/browser/linux/founder_vnc_view.sh'
REPAIR=ROOT/'company/browser/linux/founder_browser_repair.py'
INSTALL=ROOT/'company/factory-asset/bin/install_founder_observability.sh'
DISPATCH=ROOT/'company/factory-asset/bin/production_multi_cluster_dispatch.mjs'

def test_read_only_vnc_is_loopback_and_attaches_real_xvfb_auth_without_copying_it():
 s=VNC.read_text(encoding='utf-8')
 assert '-localhost' in s and '-viewonly' in s
 assert "pgrep -f \"^Xvfb :${display} \"" in s
 assert '/proc/$pid/cmdline' in s and "== '-auth'" in s
 assert 'cp ' not in s and 'cat "$auth"' not in s
 assert 'x11vnc' in s and '-nopw' in s

def test_systemd_units_target_exact_production_displays_and_private_ports():
 a=(ROOT/'company/factory-asset/systemd/die-founder-vnc-cluster-a.service').read_text(encoding='utf-8')
 b=(ROOT/'company/factory-asset/systemd/die-founder-vnc-cluster-b.service').read_text(encoding='utf-8')
 assert '--display 101 --port 59101 --mode read-only' in a
 assert '--display 102 --port 59102 --mode read-only' in b
 assert 'die-muxia-cluster-a-browser.service' in a and 'die-muxia-cluster-b-browser.service' in b
 assert 'JoinsNamespaceOf=die-muxia-cluster-a-browser.service' in a
 assert 'JoinsNamespaceOf=die-muxia-cluster-b-browser.service' in b
 assert 'PrivateTmp=true' in a and 'PrivateTmp=true' in b
 assert '/opt/die/factory-asset-observability/founder_vnc_view.sh' in a+b

def test_installer_does_not_restart_browser_owner_or_expose_public_endpoint():
 s=INSTALL.read_text(encoding='utf-8')
 assert 'enable --now die-founder-vnc-cluster-a.service die-founder-vnc-cluster-b.service' in s
 assert 'restart die-muxia' not in s and 'stop die-muxia' not in s

def test_interactive_repair_is_idle_only_time_bound_and_restores_read_only_view():
 s=REPAIR.read_text(encoding='utf-8')
 assert "if timeout<30 or timeout>1800" in s
 assert "b.get('state')!='READY' or leases!=0" in s
 assert "'state':'ACTIVE'" in s and "'expires_at_epoch'" in s
 assert "'captcha_bypass_authorized':False" in s
 assert "credential_values_read':False" in s and "cookies_or_tokens_read':False" in s
 assert "systemctl','stop',cfg['view_service']" in s and "systemctl','start',cfg['view_service']" in s
 assert "systemctl','start',cfg['interactive_service']" in s
 assert "systemctl','stop',cfg['interactive_service']" in s
 for cid,display,port,browser in [('a',101,59201,'die-muxia-cluster-a-browser.service'),('b',102,59202,'die-muxia-cluster-b-browser.service')]:
  unit=(ROOT/f'company/factory-asset/systemd/die-founder-repair-vnc-cluster-{cid}.service').read_text(encoding='utf-8')
  assert f'--display {display} --port {port} --mode interactive' in unit
  assert f'JoinsNamespaceOf={browser}' in unit
  assert 'PrivateTmp=true' in unit

def test_production_dispatch_skips_cluster_with_active_founder_repair_hold():
 s=DISPATCH.read_text(encoding='utf-8')
 assert "DIE_FOUNDER_REPAIR_ROOT" in s
 assert "function repairHold(cluster)" in s
 assert "if(repairHold(c.cluster_id))continue" in s
 assert "d.state!=='ACTIVE'" in s and "expires_at_epoch" in s
