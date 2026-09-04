import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
CONSOLE=ROOT/'company/factory-asset/console-prototype'
SYNC=ROOT/'company/factory-asset/bin/sync_console_mirror.py'

def load_server(path,name):
 spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);assert spec and spec.loader;sys.modules[spec.name]=m;spec.loader.exec_module(m);return m

def test_repo_layout_root_resolution():
 m=load_server(CONSOLE/'server.py','console_root_repo');assert m.ROOT==ROOT

def test_standalone_mirror_layout_imports_without_parent_overflow(tmp_path):
 subprocess.run([sys.executable,str(SYNC),'--dest',str(tmp_path)],check=True)
 mirrored=tmp_path/'console-prototype/server.py'
 m=load_server(mirrored,'console_root_mirror')
 assert m.ROOT==tmp_path.resolve()
 assert len(m.queue_state()['events'])>=1

def test_sync_mirror_copies_runtime_support_tree(tmp_path):
 subprocess.run([sys.executable,str(SYNC),'--dest',str(tmp_path)],check=True)
 assert (tmp_path/'console-prototype/server.py').is_file()
 assert (tmp_path/'company/factory-asset/lib/blueprint_compiler.py').is_file()
 assert (tmp_path/'company/factory-asset/schemas/asset-blueprint-v2.schema.json').is_file()
 assert (tmp_path/'company/factory-asset/registries/asset-types.v1.json').is_file()