from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
HOOK=ROOT/'company/muxia/config/linux/xrdp/reconnectwm.sh'
INSTALL=ROOT/'company/muxia/scripts/linux/mx050-gui-provision.sh'

def test_reconnect_hook_repairs_only_chansrv_not_desktop():
    s=HOOK.read_text(encoding='utf-8')
    assert 'xrdp_chansrv_socket_$N' in s
    assert 'pgrep -u "$(id -u)" -x xrdp-chansrv' in s
    assert '/usr/sbin/xrdp-chansrv' in s
    assert 'killall Xorg' not in s and 'systemctl restart xrdp' not in s and 'pkill -f xfce' not in s
    assert 'XRDP_SOCKET_PATH' in s and 'XRDP_SESSION' in s

def test_gui_provision_installs_hook_and_preserves_clipboard_channels():
    s=INSTALL.read_text(encoding='utf-8')
    assert 'config/linux/xrdp/reconnectwm.sh' in s
    for token in ["cliprdr=true", "rdpdr=true", "drdynvc=true", "RestrictInboundClipboard=none", "RestrictOutboundClipboard=none"]:
        assert token in s
