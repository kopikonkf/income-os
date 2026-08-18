# test_fx02_fx04.py — rejection fixtures: die_accept.py menolak klaim palsu
import json, pathlib, subprocess, sys

FX = pathlib.Path(__file__).parent / "fixtures"
DIE_ACCEPT = pathlib.Path(__file__).resolve().parents[1].parent / "bin" / "die_accept.py"


def _run(fx, tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    inp = FX / fx / "input"
    job = json.loads((inp / "JOB.json").read_text(encoding="utf-8"))
    job["workspace"] = str(ws)
    job["constraints"]["allowed_paths"] = [str(ws)]
    (ws / "JOB.json").write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
    (ws / "RESULT.json").write_text((inp / "RESULT.json").read_text(encoding="utf-8"), encoding="utf-8")
    if (inp / "out.md").exists():
        (ws / "out.md").write_text((inp / "out.md").read_text(encoding="utf-8"), encoding="utf-8")
    changed = inp / "changed-paths.json"
    changed_arg = str(ws / "changed-paths.json")
    if changed.exists():
        (ws / "changed-paths.json").write_text(changed.read_text(encoding="utf-8"), encoding="utf-8")
    r = subprocess.run([sys.executable, str(DIE_ACCEPT), str(ws), changed_arg],
                       capture_output=True, text=True, timeout=30)
    return r


def test_fx02_done_tanpa_evidence(tmp_path):
    exp = json.loads((FX / "fx-02" / "expected.json").read_text(encoding="utf-8"))
    r = _run("fx-02", tmp_path)
    assert r.returncode == exp["exit_code"], r.stdout + r.stderr
    out = json.loads(r.stdout)
    assert out["accepted_status"] == exp["accepted_status"]
    joined = " ".join(out["problems"])
    for sub in exp["problems_substring"]:
        assert sub in joined, f"{sub} tidak ada di problems: {joined}"


def test_fx04_tulis_di_luar_scope(tmp_path):
    exp = json.loads((FX / "fx-04" / "expected.json").read_text(encoding="utf-8"))
    r = _run("fx-04", tmp_path)
    assert r.returncode == exp["exit_code"], r.stdout + r.stderr
    out = json.loads(r.stdout)
    assert out["accepted_status"] == exp["accepted_status"]
    joined = " ".join(out["problems"])
    for sub in exp["problems_substring"]:
        assert sub in joined, f"{sub} tidak ada di problems: {joined}"