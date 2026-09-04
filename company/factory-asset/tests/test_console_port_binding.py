import importlib.util
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
SERVER_PATH=ROOT/'company/factory-asset/console-prototype/server.py'

def load_server(name):
    spec=importlib.util.spec_from_file_location(name,SERVER_PATH);m=importlib.util.module_from_spec(spec);assert spec and spec.loader;sys.modules[spec.name]=m;spec.loader.exec_module(m);return m

def test_default_console_port_no_longer_conflicts_with_opencode_bridge():
    m=load_server('console_port_default'); assert m.DEFAULT_PORT==8876; assert 8765 not in (m.DEFAULT_PORT,*m.FALLBACK_PORTS)

def test_bind_falls_back_when_preferred_port_is_busy(monkeypatch):
    m=load_server('console_port_fallback')
    calls=[]
    class FakeServer:
        def __init__(self,address,handler):
            calls.append(address[1])
            if address[1]==8876: raise PermissionError(13,'busy')
            self.server_port=address[1] if address[1] else 49152
    monkeypatch.setattr(m,'ThreadingHTTPServer',FakeServer)
    server,port,attempts=m._bind_loopback_server('127.0.0.1',8876)
    assert calls[:2]==[8876,8877]; assert port==8877; assert attempts and attempts[0][0]==8876

def test_bind_uses_ephemeral_after_both_fixed_ports_fail(monkeypatch):
    m=load_server('console_port_ephemeral')
    class FakeServer:
        def __init__(self,address,handler):
            if address[1] in (8876,8877): raise OSError(10013,'blocked')
            self.server_port=50001
    monkeypatch.setattr(m,'ThreadingHTTPServer',FakeServer)
    _,port,attempts=m._bind_loopback_server('127.0.0.1',8876)
    assert port==50001; assert [x[0] for x in attempts]==[8876,8877]