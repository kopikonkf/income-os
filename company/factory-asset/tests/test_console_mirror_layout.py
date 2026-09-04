import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CONSOLE = ROOT / 'company/factory-asset/console-prototype'
SYNC = ROOT / 'company/factory-asset/bin/sync_console_mirror.py'


def load_server(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_repo_layout_root_resolution():
    mod = load_server(CONSOLE / 'server.py', 'console_root_repo')
    assert mod.ROOT == ROOT


def test_standalone_mirror_layout_imports_without_parent_overflow(tmp_path):
    subprocess.run([sys.executable, str(SYNC), '--dest', str(tmp_path)], check=True)
    mirrored = tmp_path / 'console-prototype/server.py'
    mod = load_server(mirrored, 'console_root_mirror')
    assert mod.ROOT == tmp_path.resolve()
    assert len(mod.queue_state()['events']) >= 1
    assert len(mod.provider_dashboard_state()['providers']) == 6


def test_sync_mirror_copies_runtime_support_tree(tmp_path):
    subprocess.run([sys.executable, str(SYNC), '--dest', str(tmp_path)], check=True)
    assert (tmp_path / 'console-prototype/server.py').is_file()
    assert (tmp_path / 'company/factory-asset/lib/blueprint_compiler.py').is_file()
    assert (tmp_path / 'company/factory-asset/schemas/asset-blueprint-v2.schema.json').is_file()
    assert (tmp_path / 'company/factory-asset/registries/asset-types.v1.json').is_file()
    assert (tmp_path / 'company/factory-asset/fixtures/provider-dashboard/synthetic-observed.v1.json').is_file()