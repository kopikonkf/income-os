from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import jsonschema

ROOT = Path(__file__).resolve().parents[4]
H01 = ROOT / 'company/company-os/die-h01'
BLUEPRINT_SCHEMA = H01 / 'contracts/h01-svg-blueprint-v2.schema.json'
MASTER_SCHEMA = H01 / 'contracts/h01-svg-master-instruction-v2.schema.json'
PROMPT_SCHEMA = H01 / 'contracts/h01-svg-provider-prompt-v2.schema.json'
PROFILE_PATH = H01 / 'runtime/h01-svg-prompt-profiles.v2.json'
REVISION = '2.0.0'

class SvgPromptError(ValueError):
    def __init__(self, code: str, detail: str = ''):
        super().__init__(f'{code}: {detail}' if detail else code)
        self.code = code

def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8-sig'))

def _bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()

def sha256_value(value: Any) -> str:
    return hashlib.sha256(_bytes(value)).hexdigest()

def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()

def _validate(value: Any, schema_path: Path, code: str) -> None:
    validator = jsonschema.Draft202012Validator(_load(schema_path))
    errors = sorted(validator.iter_errors(value), key=lambda e: list(e.absolute_path))
    if errors:
        e = errors[0]
        where = '.'.join(str(x) for x in e.absolute_path) or '$'
        raise SvgPromptError(code, f'{where}: {e.message}')

def _clean(text: str) -> str:
    return ' '.join(str(text).strip().split())

def _list_clause(label: str, items: list[str]) -> str | None:
    vals = [_clean(x) for x in items if _clean(x)]
    return f'{label}: ' + '; '.join(vals) if vals else None

def validate_blueprint(blueprint: dict[str, Any]) -> None:
    _validate(blueprint, BLUEPRINT_SCHEMA, 'BLUEPRINT_SCHEMA_INVALID')
    encoded = _bytes(blueprint)
    if len(encoded) > 32_768:
        raise SvgPromptError('BLUEPRINT_TOO_LARGE', str(len(encoded)))
    # Blueprint is WHAT-only: provider/transport/dialect knobs are forbidden recursively.
    forbidden = {'provider','provider_id','provider_profile','model','transport','cdp','mcp','prompt','system_prompt','temperature','max_tokens'}
    def walk(value: Any, path: str = '$') -> None:
        if isinstance(value, dict):
            for k, v in value.items():
                if str(k).lower() in forbidden:
                    raise SvgPromptError('BLUEPRINT_PROVIDER_LEAK', f'{path}.{k}')
                walk(v, f'{path}.{k}')
        elif isinstance(value, list):
            for i, v in enumerate(value): walk(v, f'{path}[{i}]')
    walk(blueprint)
    if blueprint['subject']['canonical_name'].casefold() not in blueprint['commercial']['primary_use_case'].casefold():
        raise SvgPromptError('COMMERCIAL_USE_CASE_SUBJECT_MISSING', blueprint['subject']['canonical_name'])
    if not set(blueprint['output_contract']['forbidden_svg_features']).issuperset({'script','external references','embedded raster image','foreignObject','text'}):
        raise SvgPromptError('SVG_SAFETY_CONTRACT_INCOMPLETE')

def compile_master_instruction(blueprint: dict[str, Any]) -> dict[str, Any]:
    validate_blueprint(blueprint)
    s, c, v, x, r, out = (blueprint[k] for k in ('subject','commercial','visual','complexity','rights','output_contract'))
    sections: list[dict[str, Any]] = []
    def add(name: str, clauses: list[str | None]) -> None:
        vals = [_clean(q) for q in clauses if q and _clean(q)]
        if vals: sections.append({'name': name, 'clauses': vals})
    add('SUBJECT', [
        f"One standalone {s['canonical_name']}",
        _list_clause('Recognition anchors', s['recognition_anchors']),
        _list_clause('Essential components', s['essential_components']),
        _list_clause('Proportions', s['proportion_notes']),
        _list_clause('Materials', s['material_notes']),
        _list_clause('Colors', s['color_notes']),
        _list_clause('Textures', s['texture_notes']),
    ])
    add('COMMERCIAL', [
        f"Primary use: {c['primary_use_case']}", f"Buyer value: {c['buyer_value']}",
        f"Stock suitability: {c['stock_suitability']}", _list_clause('Reusable contexts', c['reuse_contexts'])
    ])
    add('COMPOSITION', [f"Viewpoint: {v['viewpoint']}", _list_clause('Composition', v['composition']), _list_clause('Visual hierarchy', v['visual_hierarchy'])])
    add('VECTOR_STYLE', [_list_clause('Style system', v['style_system']), _list_clause('Shape language', blueprint['vector']['shape_language']), f"Stroke policy: {blueprint['vector']['stroke_policy']}", f"Fill policy: {blueprint['vector']['fill_policy']}", f"Depth policy: {blueprint['vector']['depth_policy']}", 'Native editable vector geometry is mandatory'])
    add('COMPLEXITY', [f"SVG bytes <= {x['max_svg_bytes']}", f"Geometry elements <= {x['max_geometry_elements']}", f"Total sampled points <= {x['max_total_points']}", f"Characters in any path d <= {x['max_path_chars']}", f"Group depth <= {x['max_group_depth']}"])
    add('RIGHTS_AND_STOCK', ['No logos or trademarks', 'No copyrighted character/style imitation', 'No readable text', 'No watermark', _list_clause('Additional forbidden content', r['forbidden_content'])])
    add('SVG_OUTPUT', [
        'Return genuine SVG source, not a traced/wrapped raster', 'Transparent background; no background rectangle',
        _list_clause('Allowed geometry elements', out['allowed_elements']), _list_clause('Allowed path commands', out['allowed_path_commands']),
        _list_clause('Forbidden SVG features', out['forbidden_svg_features']), 'Root svg must have a finite viewBox and contain editable visible geometry'
    ])
    invariants = [
        'Every Blueprint requirement remains semantically binding downstream',
        'Master Instruction contains no provider/model/transport choice',
        'Provider prompt may change phrasing but may not weaken or omit a clause',
        'Mission/provider/submission/publication authority is not granted by compilation',
    ]
    master = {'schema':'die.h01.svg-master-instruction.v2','compiler_revision':REVISION,'blueprint_id':blueprint['blueprint_id'],'blueprint_sha256':sha256_value(blueprint),'sections':sections,'invariants':invariants,'master_instruction_sha256':'0'*64}
    master['master_instruction_sha256'] = sha256_value({k:v for k,v in master.items() if k!='master_instruction_sha256'})
    _validate(master, MASTER_SCHEMA, 'MASTER_INSTRUCTION_SCHEMA_INVALID')
    return master

def _profiles() -> dict[str, dict[str, Any]]:
    data = _load(PROFILE_PATH)
    if data.get('schema') != 'die.h01.svg-prompt-profiles.v2':
        raise SvgPromptError('PROFILE_REGISTRY_SCHEMA')
    out = {}
    for row in data.get('profiles', []):
        pid = row.get('provider_profile')
        if not pid or pid in out:
            raise SvgPromptError('PROFILE_DUPLICATE', str(pid))
        budget = int(row.get('prompt_budget_chars') or 0)
        if budget < 1000 or budget > 8000:
            raise SvgPromptError('PROFILE_BUDGET_INVALID', str(pid))
        out[pid] = row
    return out

def _section_text(master: dict[str, Any]) -> str:
    lines: list[str] = []
    for sec in master['sections']:
        lines.append(f"[{sec['name']}]")
        for clause in sec['clauses']:
            lines.append(f"- {clause}")
    lines.append('[INVARIANTS]')
    for clause in master['invariants']:
        lines.append(f"- {clause}")
    return '\n'.join(lines)

def compile_provider_prompt(*, blueprint: dict[str, Any], master: dict[str, Any], provider_profile: str) -> dict[str, Any]:
    validate_blueprint(blueprint)
    _validate(master, MASTER_SCHEMA, 'MASTER_INSTRUCTION_SCHEMA_INVALID')
    if master['blueprint_id'] != blueprint['blueprint_id'] or master['blueprint_sha256'] != sha256_value(blueprint):
        raise SvgPromptError('MASTER_BLUEPRINT_MISMATCH', blueprint['blueprint_id'])
    expected_master_hash = sha256_value({k:v for k,v in master.items() if k!='master_instruction_sha256'})
    if master['master_instruction_sha256'] != expected_master_hash:
        raise SvgPromptError('MASTER_HASH_MISMATCH', blueprint['blueprint_id'])
    profiles = _profiles()
    if provider_profile not in profiles:
        raise SvgPromptError('PROVIDER_PROFILE_UNKNOWN', provider_profile)
    profile = profiles[provider_profile]
    body = _section_text(master)
    prompt = '\n'.join([
        _clean(profile['opening']),
        'Follow every requirement. Do not silently simplify, substitute, or omit constraints.',
        body,
        _clean(profile['closing']),
    ])
    budget = int(profile['prompt_budget_chars'])
    if len(prompt) > budget:
        raise SvgPromptError('PROVIDER_PROMPT_BUDGET_EXCEEDED', f'{provider_profile}:{len(prompt)}>{budget}')
    if '<TODO>' in prompt or 'TBD' in prompt:
        raise SvgPromptError('PROVIDER_PROMPT_PLACEHOLDER')
    # Coverage is exact at the Master Instruction clause level. We fail rather than summarize away semantics.
    lowered = prompt.casefold()
    omissions = []
    for sec in master['sections']:
        for clause in sec['clauses']:
            if clause.casefold() not in lowered:
                omissions.append(f"{sec['name']}:{clause}")
    for clause in master['invariants']:
        if clause.casefold() not in lowered:
            omissions.append(f'INVARIANT:{clause}')
    if omissions:
        raise SvgPromptError('SEMANTIC_CLAUSE_OMITTED', omissions[0])
    compiled = {
        'schema':'die.h01.svg-provider-prompt.v2',
        'composer_revision':REVISION,
        'provider_profile':provider_profile,
        'blueprint_id':blueprint['blueprint_id'],
        'blueprint_sha256':sha256_value(blueprint),
        'master_instruction_sha256':master['master_instruction_sha256'],
        'prompt':prompt,
        'prompt_chars':len(prompt),
        'prompt_budget_chars':budget,
        'prompt_sha256':sha256_text(prompt),
        'semantic_omission_count':0,
        'authority':{'provider_call_authorized':False,'submission_authorized':False,'publication_authorized':False},
    }
    _validate(compiled, PROMPT_SCHEMA, 'PROVIDER_PROMPT_SCHEMA_INVALID')
    return compiled

def compile_pipeline(*, blueprint: dict[str, Any], provider_profile: str) -> tuple[dict[str, Any], dict[str, Any]]:
    master = compile_master_instruction(blueprint)
    prompt = compile_provider_prompt(blueprint=blueprint, master=master, provider_profile=provider_profile)
    return master, prompt

if __name__ == '__main__':
    import argparse
    ap=argparse.ArgumentParser()
    ap.add_argument('--blueprint',required=True)
    ap.add_argument('--provider-profile',default='GENERIC_WEB_AI')
    ap.add_argument('--out-dir',required=True)
    ns=ap.parse_args()
    blueprint=_load(Path(ns.blueprint))
    master,prompt=compile_pipeline(blueprint=blueprint,provider_profile=ns.provider_profile)
    out=Path(ns.out_dir); out.mkdir(parents=True,exist_ok=True)
    (out/'master-instruction.json').write_text(json.dumps(master,indent=2,sort_keys=True)+'\n')
    (out/'provider-prompt.json').write_text(json.dumps(prompt,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'status':'PASS','blueprint_id':blueprint['blueprint_id'],'provider_profile':ns.provider_profile,'prompt_chars':prompt['prompt_chars'],'prompt_budget_chars':prompt['prompt_budget_chars'],'prompt_sha256':prompt['prompt_sha256'],'master_instruction_sha256':master['master_instruction_sha256']},sort_keys=True))
