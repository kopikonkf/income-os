#!/usr/bin/env python3
"""Gemini keyword enrichment for NexaBurst WC lane (Founder GO required for full-run).

Reads 7 Gemini API keys from makan.zip (never prints them, never writes them
to disk). Round-robin across keys with a minimum per-key gap. One image per
request -> EXACTLY 50 Adobe-style keywords per asset.

Output (sidecar only, does NOT touch vaulted metadata):
  <OUT>/receipts.jsonl   per-asset receipt {asset_id, keywords, model, key_index, usage}
  <OUT>/state.json       progress + per-key last-call timestamps (resume-safe)
  <OUT>/run.log          human-readable log

Usage:
  nexaburst-kw-enrich.py --limit 5            # test 5 assets
  nexaburst-kw-enrich.py --all                # full run (~14k)
  nexaburst-kw-enrich.py --all --min-gap 10   # slower, safer vs 429
"""
from __future__ import annotations
import argparse, base64, json, os, sys, time, urllib.request, urllib.error, zipfile
from pathlib import Path

ZIP_PATH = Path('/home/kopiko/Dee_Workspace/makan.zip')
ZIP_MEMBER = 'makan/makan.txt'
KEY_LINES = list(range(20, 27))          # 0-based lines 21..27 = 7 keys
NBU = Path('/var/lib/die/h01/nexaburst')
OUT = Path('/var/lib/die/h01/nexaburst-kw-gemini')
MODEL_CHAIN = ['gemini-3.5-flash-lite', 'gemini-3.1-flash-lite',
               'gemini-3.5-flash', 'gemini-3.6-flash', 'gemini-3.7-flash']
THINK_MODELS = {'gemini-3.5-flash', 'gemini-3.6-flash', 'gemini-3.7-flash',
                 'gemini-3.8-flash'}
TRANSIENT = ('HTTP_503', 'HTTP_429', 'HTTP_404', 'HTTP_500')

PROMPT_TMPL_V2 = (
 "You are an Adobe Stock contributor specialist. Your goal is metadata that makes this image "
 "DISCOVERABLE by real buyers searching a stock marketplace. "
 "Context: the depicted object is '%NOUN%' (style: %STYLE%), shown isolated on white background. "
 "Verify visually; if the image clearly shows something else, trust your eyes. "
 "Return ONLY valid JSON with EXACTLY these keys: "
 "{\"title\": ..., \"description\": ..., \"keywords\": [...]}. Rules:\n"
 "- title: one buyer-facing stock-photo title, max 190 characters, Title Case, no keyword stuffing.\n"
 "- description: 1-2 sentences describing the image for buyers (subject, style, background, use).\n"
 "- keywords: EXACTLY 50. Order by importance: 7 strongest buyer-relevant terms FIRST "
 "(marketplaces weight early keywords highest). Mix (lowercase, no duplicates, max 3 words each): "
 "(a) literal object + synonyms/plurals of '%NOUN%', "
 "(b) visible attributes: colors, materials, texture, count, style, "
 "(c) longtail buyer phrases (2-3 words), "
 "(d) conceptual/context terms, (e) use-case terms buyers search.\n"
 "- Every keyword must genuinely describe THIS image — never spam unrelated trending terms. "
 "No explanations, JSON only."
)

def load_keys() -> list[str]:
    z = zipfile.ZipFile(ZIP_PATH)
    lines = z.read(ZIP_MEMBER).decode('utf-8', errors='replace').splitlines()
    keys = [lines[i].strip() for i in KEY_LINES]
    extra_f = OUT / 'keys.extra.json'  # 600, user-provided extra keys
    if extra_f.is_file():
        try:
            for k in json.loads(extra_f.read_text(encoding='utf-8')).get('keys', []):
                if k and k not in keys:
                    keys.append(k)
        except Exception:
            pass
    assert all(len(k) > 20 for k in keys), 'key load failed'
    return keys

def asset_image_map(queue_path: Path | None = None) -> dict[str, dict]:
    """asset_id -> {path, noun, style} (from v2-queue)."""
    m: dict[str, dict] = {}
    q = queue_path or (NBU / 'state' / 'v2-queue.jsonl')
    if q.is_file():
        for line in q.read_text(encoding='utf-8').splitlines():
            if not line.strip():
                continue
            try:
                o = json.loads(line)
                p = o.get('source_path')
                if o.get('asset_id') and p and os.path.isfile(p):
                    m.setdefault(o['asset_id'], {
                        'path': p,
                        'noun': str(o.get('noun', '') or ''),
                        'style': str(o.get('style', '') or '')})
            except Exception:
                pass
    return m

def build_prompt(noun: str, style: str) -> str:
    return PROMPT_TMPL_V2.replace('%NOUN%', noun or 'unknown object').replace('%STYLE%', style or 'isolated-object')

def gcall(key: str, model: str, b64: str, prompt: str, timeout: int = 90) -> tuple[str, dict]:
    gen: dict = {'response_mime_type': 'application/json',
                 'maxOutputTokens': 2048}
    if model in THINK_MODELS:
        # full-flash thinks (~2k tokens) until output truncates -> disable
        gen['thinkingConfig'] = {'thinkingBudget': 0}
    # lite models REJECT thinkingConfig (HTTP 400) -> omitted above
    body = json.dumps({
        'contents': [{'parts': [
            {'text': prompt},
            {'inline_data': {'mime_type': 'image/jpeg', 'data': b64}}]}],
        'generationConfig': gen}).encode()
    req = urllib.request.Request(
        f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key=' + key,
        data=body, headers={'Content-Type': 'application/json'})
    try:
        r = urllib.request.urlopen(req, timeout=timeout)
        d = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f'HTTP_{e.code}:{e.read().decode()[:150]}')
    txt = d['candidates'][0]['content']['parts'][0]['text']
    return txt, d.get('usageMetadata', {})

def parse_kw(txt: str) -> tuple[str, str, list[str]]:
    """Returns (title, description, keywords). Legacy v1 receipts (keywords-only)
    are accepted: title/description fall back to '' (caller: V2 worker skips
    overrides that are empty)."""
    s = txt.strip()
    if s.startswith('```'):
        s = s.split('\n', 1)[1] if '\n' in s else s[3:]
        if s.rstrip().endswith('```'):
            s = s.rstrip()[:-3]
    i = s.find('{')
    if i < 0:
        raise ValueError('no JSON object found')
    try:
        o, _ = json.JSONDecoder().raw_decode(s[i:])
    except json.JSONDecodeError:
        j = s.rfind('}')
        if j <= i:
            raise ValueError('no JSON object found')
        o = json.loads(s[i:j + 1])
    kw = o.get('keywords', [])
    if not isinstance(kw, list):
        raise ValueError('keywords not a list')
    out, seen = [], set()
    for k in kw:
        k = str(k).strip().lower()
        if k and k not in seen:
            seen.add(k)
            out.append(k)
    title = ' '.join(str(o.get('title', '') or '').split()).strip()[:190]
    desc = ' '.join(str(o.get('description', '') or '').split()).strip()[:600]
    return title, desc, out

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--limit', type=int, default=5)
    ap.add_argument('--min-gap', type=float, default=7.0,
                    help='min seconds between calls on the SAME key (5-10)')
    ap.add_argument('--gap', type=float, default=2.0,
                    help='min seconds between CONSECUTIVE requests (any key)')
    ap.add_argument('--daily-cap', type=int, default=950,
                    help='max calls per key per UTC day (free-tier guard)')
    ap.add_argument('--out', default=str(OUT))
    ap.add_argument('--queue', default='',
                    help='v2-queue.jsonl path (default lane1; PSR: lane2 state/v2-queue.jsonl)')
    ap.add_argument('--skip', default='1,6',
                    help='dead key indexes to skip (403 project-denied)')
    ap.add_argument('--prefix', default='',
                    help='only assets starting with this prefix (e.g. NBWC)')
    ap.add_argument('--shard', default='',
                    help='asset shard i/n, e.g. 0/3 (for parallel workers)')
    ap.add_argument('--key-subset', default='',
                    help='comma key indexes this worker may use, e.g. 0,2,7')
    ap.add_argument('--tag', default='',
                    help='per-worker suffix for state/log files (parallel workers)')
    a = ap.parse_args()
    out = Path(a.out)
    (out / 'receipts.jsonl').parent.mkdir(parents=True, exist_ok=True)
    tag = ('-' + a.tag) if a.tag.strip() else ''
    state_f = out / f'state{tag}.json'
    rec_f = out / 'receipts.jsonl'
    log_f = out / f'run{tag}.log'

    keys = load_keys()
    dead = {int(x) for x in a.skip.split(',') if x.strip().isdigit()}
    live = [i for i in range(len(keys)) if i not in dead]
    assert live, 'no live keys'
    nk = len(keys)
    print(f'keys alive: {len(live)}/{nk} (skip dead: {sorted(dead)}) | chain: {" > ".join(MODEL_CHAIN)} | min_gap: {a.min_gap}s')

    imgmap = asset_image_map(Path(a.queue) if a.queue else None)
    print(f'assets with raw image: {len(imgmap)}')
    done: set[str] = set()
    if rec_f.is_file():
        for line in rec_f.read_text(encoding='utf-8').splitlines():
            try:
                done.add(json.loads(line)['asset_id'])
            except Exception:
                pass
    import hashlib as _hl
    todo = [aid for aid in sorted(imgmap) if aid not in done
            and (not a.prefix or aid.startswith(a.prefix))]
    if a.shard:
        si, sn = a.shard.split('/')
        si, sn = int(si), int(sn)
        todo = [x for x in todo
                if int(_hl.sha256(x.encode()).hexdigest(), 16) % sn == si]
        print(f'shard {si}/{sn}: {len(todo)} assets')
    if a.key_subset.strip():
        want = {int(x) for x in a.key_subset.split(',') if x.strip().isdigit()}
        live = [i for i in live if i in want]
        assert live, 'key-subset empty after filter'
        print(f'key-subset: {live}')
    if not a.all:
        todo = todo[:a.limit]
    print(f'todo this run: {len(todo)} (already done: {len(done)})')
    if not todo:
        return 0

    last_call = [0.0] * nk
    today = time.strftime('%Y-%m-%d', time.gmtime())
    day_counts: dict[str, int] = {}
    if state_f.is_file():
        try:
            st = json.loads(state_f.read_text(encoding='utf-8'))
            lc = st.get('last_call', [])
            for i in range(min(nk, len(lc))):
                last_call[i] = float(lc[i])
            if st.get('date') == today:
                day_counts = {str(k): int(v)
                              for k, v in st.get('day_counts', {}).items()}
        except Exception:
            pass
    print(f'day {today} usage: ' + ', '.join(
        f'key{k}={day_counts.get(str(k), 0)}/{a.daily_cap}' for k in live))

    ki = 0  # position within live[]
    ok = fail = 0
    recent_errors: list[str] = []
    last_req = 0.0
    quota_stop = False
    with open(rec_f, 'a', encoding='utf-8') as rf, open(log_f, 'a', encoding='utf-8') as lf:
        for n, aid in enumerate(todo, 1):
            meta = imgmap[aid]
            img = meta['path']
            prompt = build_prompt(meta.get('noun', ''), meta.get('style', ''))
            try:
                b64 = base64.b64encode(open(img, 'rb').read()).decode()
            except Exception as e:
                print(f'[{n}/{len(todo)}] {aid} READ_FAIL {e}')
                continue
            # lifecycle: sequential round-robin, skip quota-capped keys
            avail = [k for k in live
                     if day_counts.get(str(k), 0) < a.daily_cap]
            if not avail:
                print(f'QUOTA_EXHAUSTED_TODAY day={today} '
                      f'usage={sum(day_counts.get(str(k), 0) for k in live)} — resume tomorrow')
                quota_stop = True
                break
            for _ in range(len(live)):
                li = live[ki % len(live)]
                ki = (ki + 1) % len(live)
                if li not in avail:
                    continue
                if time.time() - last_call[li] >= a.min_gap:
                    break
            else:
                li = next(k for k in live if k in avail)
                tw = a.min_gap - (time.time() - last_call[li])
                if tw > 0:
                    time.sleep(tw)
            # inter-request gap (any key): generate(~19s) -> gap(2s) -> next
            gw = a.gap - (time.time() - last_req)
            if gw > 0:
                time.sleep(gw)
            kid = li
            last_call[kid] = time.time()
            last_req = last_call[kid]
            day_counts[str(kid)] = day_counts.get(str(kid), 0) + 1
            model = ''
            errs_this_item: list[str] = []
            try:
                txt = um = None
                errs: list[str] = []
                for attempt in range(2):  # attempt 2 = after 403 key-rotate
                    try:
                        for cand in MODEL_CHAIN:
                            try:
                                txt, um = gcall(keys[kid], cand, b64, prompt)
                                model = cand
                                break
                            except RuntimeError as e:
                                if 'HTTP_403' in str(e):
                                    raise
                                if any(t in str(e) for t in TRANSIENT):
                                    errs.append(str(e))
                                    time.sleep(3)
                                    continue
                                raise
                    except RuntimeError as e:
                        if 'HTTP_403' in str(e) and attempt == 0:
                            print(f'[{n}/{len(todo)}] {aid} key{kid} 403-DEAD, rotating')
                            if kid in live:
                                live.remove(kid)
                            if not live:
                                raise RuntimeError('ALL_KEYS_DEAD')
                            kid = live[ki % len(live)]
                            ki = (ki + 1) % len(live)
                            last_call[kid] = time.time()
                            txt = um = None
                            continue
                        raise
                    if txt is not None:
                        break
                if txt is None:
                    if errs and all('HTTP_429' in x for x in errs):
                        raise RuntimeError('HTTP_429:ALL_MODELS_QUOTA')
                    raise RuntimeError('ALL_MODELS_TRANSIENT')
                title, desc, kw = parse_kw(txt)
                if len(kw) < 25:
                    raise ValueError(f'too few keywords: {len(kw)}')
                rec = {'schema': 'die.h01.nexaburst.kw-receipt.v2', 'asset_id': aid,
                       'title': title, 'description': desc,
                       'keywords': kw, 'n': len(kw), 'model': model,
                       'key_index': kid,
                       'usage': {'in': um.get('promptTokenCount'),
                                 'out': um.get('candidatesTokenCount')},
                       'at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
                rf.write(json.dumps(rec, ensure_ascii=False) + '\n')
                rf.flush()
                ok += 1
                recent_errors.clear()
                print(f'[{n}/{len(todo)}] {aid} OK n={len(kw)} key{kid} {model}')
                lf.write(f"{rec['at']} {aid} OK n={len(kw)} key{kid} {model}\n")
            except Exception as e:
                fail += 1
                err = str(e)[:160]
                errs_this_item.append(err)
                recent_errors.append(err)
                if len(recent_errors) > len(live):
                    recent_errors.pop(0)
                print(f'[{n}/{len(todo)}] {aid} FAIL key{kid} {err}')
                lf.write(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {aid} FAIL key{kid} {err}\n")
                if 'HTTP_429' in err:
                    time.sleep(5)
                    all429 = all('429' in e or 'quota' in e.lower()
                                 for e in recent_errors)
                    if all429:
                        print(f'QUOTA_EXHAUSTED_ALL_KEYS day={today} — stop clean, '
                              f'resume after UTC reset')
                        quota_stop = True
                        break
            lf.flush()
            state_f.write_text(json.dumps(
                {'date': today, 'day_counts': day_counts,
                 'last_call': last_call, 'updated_at': time.strftime(
                     '%Y-%m-%dT%H:%M:%SZ', time.gmtime())}))
            if 'HTTP_429:ALL_MODELS_QUOTA' in errs_this_item:
                if kid in live:
                    live.remove(kid)
                    print(f'key{kid} QUOTA_EXHAUSTED (retired for today)')
                if not live:
                    print(f'QUOTA_EXHAUSTED_ALL_KEYS day={today} — stop clean, '
                          f'resume after UTC reset')
                    quota_stop = True
                    break
    if quota_stop:
        # signal the supervisor: no point relaunching before UTC midnight
        import calendar
        t = time.gmtime()
        reset = calendar.timegm((t.tm_year, t.tm_mon, t.tm_mday + 1,
                                 0, 5, 0, 0, 0, 0))
        (out / 'quota-exhausted-until').write_text(str(reset))
        print(f'stopped: QUOTA_EXHAUSTED_TODAY ok={ok} fail={fail} '
              f'reset_at={time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(reset))}')
    print(f'done: ok={ok} fail={fail}')
    return 0 if fail == 0 else 2

if __name__ == '__main__':
    sys.exit(main())
