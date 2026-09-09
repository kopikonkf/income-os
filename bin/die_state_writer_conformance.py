#!/usr/bin/env python3
"""Static conformance checker for DIE State Manager physical-writer sovereignty."""
from __future__ import annotations
import argparse, ast, json
from pathlib import Path

GLOBAL_STORES = {"EVENTS.jsonl", "DECISIONS.jsonl", "ECONOMICS.jsonl"}
GLOBAL_WRITER = "bin/die_event.py"
FACTORY_WRITER = "company/factory-asset/lib/factory_state_manager.py"
FACTORY_REGISTRY = "company/factory-asset/registries/governed-canary-assets.v1.json"
REGISTRY = "company/identity-registry.json"


def _is_state_root(node: ast.AST) -> bool:
    if isinstance(node, ast.Name): return node.id == "STATE"
    if isinstance(node, ast.Attribute): return node.attr == "STATE"
    return False


def _canonical_expr(node: ast.AST, env: dict[str, str]) -> str | None:
    if isinstance(node, ast.Name): return env.get(node.id)
    if isinstance(node, ast.Attribute):
        if isinstance(node.value, ast.Name) and node.value.id == "config" and node.attr in {"EVENTS", "DECISIONS", "ECONOMICS"}:
            return f"state/{node.attr}.jsonl"
        return None
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        if _is_state_root(node.left) and isinstance(node.right, ast.Constant) and node.right.value in GLOBAL_STORES:
            return f"state/{node.right.value}"
    return None


def _mode_is_write(node: ast.AST | None) -> bool:
    if node is None: return False
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        mode=node.value
        return any(ch in mode for ch in "wa+")
    return False


def scan_python_writer(path: Path, rel: str) -> list[dict]:
    try: tree=ast.parse(path.read_text(encoding="utf-8-sig"), filename=rel)
    except (OSError, SyntaxError, UnicodeDecodeError): return []
    findings=[]
    class V(ast.NodeVisitor):
        def __init__(self): self.env: dict[str,str]={}
        def visit_Assign(self,node):
            target=_canonical_expr(node.value,self.env)
            if target:
                for t in node.targets:
                    if isinstance(t,ast.Name): self.env[t.id]=target
            self.generic_visit(node)
        def visit_AnnAssign(self,node):
            if node.value is not None and isinstance(node.target,ast.Name):
                target=_canonical_expr(node.value,self.env)
                if target:self.env[node.target.id]=target
            self.generic_visit(node)
        def visit_Call(self,node):
            target=None; kind=None
            if isinstance(node.func,ast.Name) and node.func.id=="_append" and node.args:
                target=_canonical_expr(node.args[0],self.env)
                if target: kind="append_helper"
            elif isinstance(node.func,ast.Name) and node.func.id=="open" and node.args:
                target=_canonical_expr(node.args[0],self.env)
                mode=node.args[1] if len(node.args)>1 else next((k.value for k in node.keywords if k.arg=="mode"),None)
                if target and _mode_is_write(mode): kind="open_write"
            elif isinstance(node.func,ast.Attribute):
                if node.func.attr in {"write_text","write_bytes","unlink","replace","rename"}:
                    target=_canonical_expr(node.func.value,self.env)
                    if target: kind=node.func.attr
                elif node.func.attr=="open":
                    target=_canonical_expr(node.func.value,self.env)
                    mode=node.args[0] if node.args else next((k.value for k in node.keywords if k.arg=="mode"),None)
                    if target and _mode_is_write(mode):kind="path_open_write"
            if target and kind:
                findings.append({"file":rel,"line":getattr(node,"lineno",None),"store":target,"kind":kind})
            self.generic_visit(node)
    V().visit(tree)
    return findings


def validate(repo_root: Path, mission_control_root: Path | None=None) -> dict:
    errors=[]; warnings=[]
    reg=json.loads((repo_root/REGISTRY).read_text(encoding="utf-8"))
    expected=reg.get("governance",{}).get("canonical_state_writer")
    sole=[x for x in reg.get("services",[]) if isinstance(x,dict) and x.get("sole_physical_writer") is True]
    if expected!="die-state-manager": errors.append("E_CANONICAL_WRITER_ID")
    if len(sole)!=1 or sole[0].get("id")!=expected: errors.append("E_SOLE_WRITER_REGISTRY")

    findings=[]
    for path in repo_root.rglob("*.py"):
        rel=path.relative_to(repo_root).as_posix()
        if ".git" in path.parts or "__pycache__" in path.parts or "/tests/" in f"/{rel}/" or rel.startswith("tests/"):
            continue
        findings.extend(scan_python_writer(path,rel))
    unauthorized=[x for x in findings if x["file"]!=GLOBAL_WRITER]
    if unauthorized: errors.append("E_COMPETING_GLOBAL_STORE_WRITER")
    allowed=[x for x in findings if x["file"]==GLOBAL_WRITER]
    if not any(x["store"]=="state/EVENTS.jsonl" for x in allowed): errors.append("E_EVENTS_WRITER_NOT_DETECTED")
    if not any(x["store"]=="state/DECISIONS.jsonl" for x in allowed): errors.append("E_DECISIONS_WRITER_NOT_DETECTED")
    if not any(x["store"]=="state/ECONOMICS.jsonl" for x in allowed):
        warnings.append("W_ECONOMICS_WRITER_NOT_IMPLEMENTED_CURRENTLY")

    fw=(repo_root/FACTORY_WRITER).read_text(encoding="utf-8")
    if "WRITER='DIE_STATE_MANAGER'" not in fw and 'WRITER = "DIE_STATE_MANAGER"' not in fw:
        errors.append("E_FACTORY_WRITER_ID")
    if "WRITER_ID_FORBIDDEN" not in fw: errors.append("E_FACTORY_WRITER_FAIL_CLOSED_MISSING")
    fr=json.loads((repo_root/FACTORY_REGISTRY).read_text(encoding="utf-8"))
    if fr.get("canonical_writer")!="DIE_STATE_MANAGER": errors.append("E_FACTORY_REGISTRY_WRITER")

    dg=(repo_root/"bridge/income_os_bridge/decision_gateway.py").read_text(encoding="utf-8")
    if 'WRITER_ID = "die-state-manager"' not in dg: errors.append("E_GATEWAY_WRITER_ID")
    if '"canonical_mutation": False' not in dg: errors.append("E_GATEWAY_REJECTION_MUTATION_GUARD")
    runtime=(repo_root/"bridge/income_os_bridge/runtime_mcp_server.py").read_text(encoding="utf-8")
    if "State Manager" not in runtime or "second" not in runtime.lower(): warnings.append("W_RUNTIME_BOUNDARY_COMMENT_NOT_DETECTED")

    mc={"audited":False,"forbidden_company_store_refs":[]}
    if mission_control_root:
        refs=[]
        needles=("DECISIONS.jsonl","ECONOMICS.jsonl","state/EVENTS.jsonl","die_event.py","governed-canary-assets.v1.json")
        for root_name in ("src","scripts","config"):
            root=mission_control_root/root_name
            if not root.exists(): continue
            for f in root.rglob("*"):
                if not f.is_file():continue
                try:text=f.read_text(encoding="utf-8",errors="ignore")
                except OSError:continue
                for needle in needles:
                    if needle in text: refs.append({"file":f.relative_to(mission_control_root).as_posix(),"needle":needle})
        mc={"audited":True,"forbidden_company_store_refs":refs}
        if refs: errors.append("E_MISSION_CONTROL_COMPANY_STORE_COUPLING")

    return {
      "schema":"die.state-manager.writer-domain-conformance.v1",
      "status":"PASS" if not errors else "FAIL",
      "canonical_state_writer":expected,
      "sole_physical_writer_count":len(sole),
      "global_store_write_findings":findings,
      "unauthorized_global_store_writers":unauthorized,
      "factory_domain":{"logical_writer":"die-state-manager","adapter":FACTORY_WRITER,"registry":FACTORY_REGISTRY,"writer_token":"DIE_STATE_MANAGER"},
      "mission_control":mc,
      "warnings":warnings,
      "errors":errors,
    }


def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--root",default="."); ap.add_argument("--mission-control-root")
    a=ap.parse_args(); result=validate(Path(a.root).resolve(),Path(a.mission_control_root).resolve() if a.mission_control_root else None)
    print(json.dumps(result,indent=2)); raise SystemExit(0 if result["status"]=="PASS" else 1)
if __name__=="__main__": main()
