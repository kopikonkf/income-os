# test_fx01_fx03_fx05.py — Worker Contract fixtures (B3.5, D6 §7)
import json, pathlib, subprocess, sys

FX = pathlib.Path(__file__).parent / "fixtures"
DIE_ACCEPT = pathlib.Path(__file__).resolve().parents[1].parent / "bin" / "die_accept.py"


def _read_text(path):
    """Read text file with auto-detection of UTF-8/UTF-16 BOM."""
    data = path.read_bytes()
    if data.startswith(b'\xff\xfe') or data.startswith(b'\xfe\xff'):
        return data.decode('utf-16')
    return data.decode('utf-8')


def _run(fx, tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    inp = FX / fx / "input"
    job = json.loads(_read_text(inp / "JOB.json"))
    job["workspace"] = str(ws)
    job["constraints"]["allowed_paths"] = [str(ws)]
    (ws / "JOB.json").write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
    (ws / "RESULT.json").write_text(_read_text(inp / "RESULT.json"), encoding="utf-8")
    
    # Copy all files from input to workspace
    for f in inp.iterdir():
        if f.is_file() and f.name not in ("JOB.json", "RESULT.json", "changed-paths.json"):
            (ws / f.name).write_text(_read_text(f), encoding="utf-8")
    
    changed = inp / "changed-paths.json"
    changed_arg = str(ws / "changed-paths.json")
    if changed.exists():
        (ws / "changed-paths.json").write_text(_read_text(changed), encoding="utf-8")
    if (inp / "evidence").exists():
        import shutil
        shutil.copytree(inp / "evidence", ws / "evidence", dirs_exist_ok=True)
    r = subprocess.run([sys.executable, str(DIE_ACCEPT), str(ws), changed_arg],
                       capture_output=True, text=True, timeout=30)
    return r


def test_fx01_happy_path(tmp_path):
    exp = json.loads((FX / "fx-01" / "expected.json").read_text(encoding="utf-8"))
    r = _run("fx-01", tmp_path)
    assert r.returncode == exp["exit_code"], r.stdout + r.stderr
    out = json.loads(r.stdout)
    assert out["accepted_status"] == exp["accepted_status"]
    joined = " ".join(out["problems"])
    for sub in exp["problems_substring"]:
        assert sub in joined, f"{sub} tidak ada di problems: {joined}"


def test_fx03_test_fail(tmp_path):
    exp = json.loads((FX / "fx-03" / "expected.json").read_text(encoding="utf-8"))
    r = _run("fx-03", tmp_path)
    assert r.returncode == exp["exit_code"], r.stdout + r.stderr
    out = json.loads(r.stdout)
    assert out["accepted_status"] == exp["accepted_status"]
    joined = " ".join(out["problems"])
    for sub in exp["problems_substring"]:
        assert sub in joined, f"{sub} tidak ada di problems: {joined}"


def test_fx05_resume_golden_data(tmp_path):
    """
    Fixture fx-05 adalah data golden untuk resume.
    Test ini memverifikasi:
    1. PROGRESS.md terbaca dengan benar (ada di workspace)
    2. RESULT.json mengandung field 'resumed: true'
    3. die_accept.py tetap lolos (accepted_status: done) karena semua kriteria terpenuhi
    """
    exp = json.loads((FX / "fx-05" / "expected.json").read_text(encoding="utf-8"))
    r = _run("fx-05", tmp_path)
    assert r.returncode == exp["exit_code"], r.stdout + r.stderr
    out = json.loads(r.stdout)
    assert out["accepted_status"] == exp["accepted_status"]
    # Verifikasi RESUME: RESULT.json harus punya resumed: true
    res = json.loads((tmp_path / "ws" / "RESULT.json").read_text(encoding="utf-8"))
    assert res.get("resumed") is True, "RESULT.json harus punya resumed: true"
    # Verifikasi PROGRESS.md ada dan terbaca
    progress = (tmp_path / "ws" / "PROGRESS.md").read_text(encoding="utf-8")
    assert "Langkah terakhir yang selesai" in progress
    assert "Menulis convert.py" in progress