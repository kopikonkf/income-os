# C:\DIE\bin\die_accept.py <workspace> <changed-paths.json>
# Sumber: S2-B1-Bootstrap-Hermes-VPS.md (Opus 5) B1.8 -- gerbang penerimaan mekanis (D6 5)
import json, sys, pathlib

W = pathlib.Path(sys.argv[1])
job = json.loads((W / "JOB.json").read_text(encoding="utf-8"))
res = json.loads((W / "RESULT.json").read_text(encoding="utf-8"))
ORDER = ["done", "partial", "blocked", "failed"]
status, problems = res.get("status", "failed"), []


def demote(new, why):
    global status
    if ORDER.index(new) > ORDER.index(status):
        status = new
    problems.append(why)


if status == "done" and not res.get("evidence"):
    demote("blocked", "D6-5.1 done tanpa evidence")
claims = " ".join(e.get("claim", "") for e in res.get("evidence", [])) + " " + \
         " ".join(t.get("name", "") for t in res.get("tests", []))
for ac in job["acceptance_criteria"]:
    if ac["id"] not in claims:
        demote("partial", f"D6-5.2 {ac['id']} tidak dipetakan evidence/test")
if any(t.get("result") == "fail" for t in res.get("tests", [])):
    demote("partial", "D6-5.3 ada test dengan result=fail")
for a in res.get("artifact", []):
    if not (W / a["path"]).exists():
        demote("failed", f"D6-5.4 artifact tidak ada di workspace: {a['path']}")
allowed = [str(pathlib.Path(p).resolve()).lower() for p in job["constraints"]["allowed_paths"]]
changed = json.loads(pathlib.Path(sys.argv[2]).read_text(encoding="utf-8"))
if isinstance(changed, str):
    changed = [changed]
outside = [c for c in changed
           if not any(str(pathlib.Path(c).resolve()).lower().startswith(a) for a in allowed)
           and "\\logs\\" not in c.lower()]
if outside:
    demote("failed", "D6-5.5 tulisan di luar allowed_paths: " + "; ".join(outside[:5]))

out = {"task_id": job["task_id"], "accepted_status": status, "problems": problems}
print(json.dumps(out, ensure_ascii=False, indent=2))
sys.exit(0 if status == "done" else 2)