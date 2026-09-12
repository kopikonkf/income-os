from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any

from semantic_family_v1 import canonical_family_id, validate_semantic_family

SCHEMA='die.h01.taxonomy-family-map.v1'
MANIFEST_SCHEMA='die.h01.taxonomy-family-map.manifest.v1'
FAMILY_VERSION='1.0.0'
MAX_EVIDENCE=100

class TaxonomyFamilyMapError(ValueError):
    def __init__(self, code:str, detail:str=''):
        super().__init__(f'{code}:{detail}' if detail else code); self.code=code

def _canon(value:Any)->bytes:
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()

def sha256_value(value:Any)->str:
    return hashlib.sha256(_canon(value)).hexdigest()

def _json_list(value:Any, field:str, subject_id:str)->list[Any]:
    try: out=json.loads(value or '[]')
    except Exception as exc: raise TaxonomyFamilyMapError('E_JSON_FIELD',f'{subject_id}:{field}') from exc
    if not isinstance(out,list): raise TaxonomyFamilyMapError('E_JSON_FIELD',f'{subject_id}:{field}:not-list')
    return out

def _norm_term(value:str)->str:
    return ' '.join(str(value).strip().casefold().split())

def _read_rows(db_path:str|Path)->list[dict[str,Any]]:
    p=Path(db_path).resolve()
    con=sqlite3.connect(f'file:{p}?mode=ro',uri=True); con.row_factory=sqlite3.Row; con.execute('PRAGMA query_only=ON')
    try:
        check=con.execute('PRAGMA quick_check').fetchone()[0]
        if check!='ok': raise TaxonomyFamilyMapError('E_SOURCE_DB_QUICK_CHECK',str(check))
        rows=[dict(r) for r in con.execute('''SELECT id,raw_noun_id,canonical_name,aliases,wordnet_synsets,suitability,ip_risk,wave3_status
            FROM candidate_seeds WHERE wave3_status='eligible' ORDER BY raw_noun_id ASC,id ASC''')]
    finally: con.close()
    return rows

def _prepare_rows(rows:list[dict[str,Any]])->tuple[list[dict[str,Any]],list[dict[str,Any]]]:
    ids=set(); raw_ids=set(); names:dict[str,str]={}; aliases_by_term:dict[str,set[str]]=defaultdict(set); prepared=[]
    for row in rows:
        sid=str(row['id']); rid=int(row['raw_noun_id']); name=' '.join(str(row['canonical_name']).strip().split())
        if not sid or not name: raise TaxonomyFamilyMapError('E_IDENTITY_BLANK',sid or str(rid))
        if sid in ids: raise TaxonomyFamilyMapError('E_DUPLICATE_SUBJECT_ID',sid)
        if rid in raw_ids: raise TaxonomyFamilyMapError('E_DUPLICATE_RAW_NOUN_ID',str(rid))
        key=_norm_term(name)
        if key in names and names[key]!=sid: raise TaxonomyFamilyMapError('E_DUPLICATE_CANONICAL_NAME',f'{key}:{names[key]}:{sid}')
        ids.add(sid); raw_ids.add(rid); names[key]=sid
        aliases=[str(x).strip() for x in _json_list(row.get('aliases'),'aliases',sid) if str(x).strip()]
        synsets=[str(x).strip() for x in _json_list(row.get('wordnet_synsets'),'wordnet_synsets',sid) if str(x).strip()]
        if not synsets: raise TaxonomyFamilyMapError('E_PRIMARY_SYNSET_MISSING',sid)
        primary=synsets[0]
        if not primary.endswith(('.n.01','.n.02','.n.03','.n.04','.n.05','.n.06','.n.07','.n.08','.n.09')) and '.n.' not in primary:
            raise TaxonomyFamilyMapError('E_PRIMARY_SYNSET_NOT_NOUN',f'{sid}:{primary}')
        for alias in aliases: aliases_by_term[_norm_term(alias)].add(sid)
        prepared.append({'subject_id':sid,'raw_noun_id':rid,'canonical_name':name,'aliases':sorted(set(aliases),key=_norm_term),'primary_synset':primary,'suitability':str(row.get('suitability') or ''),'ip_risk':str(row.get('ip_risk') or '')})
    observations=[]
    for term,owners in sorted(aliases_by_term.items()):
        canonical_owner=names.get(term); all_ids=sorted(owners | ({canonical_owner} if canonical_owner else set()))
        if len(all_ids)>1:
            observations.append({'normalized_term':term,'subject_ids':all_ids,'canonical_owner_subject_id':canonical_owner,'action':'PRESERVE_IDENTITIES_REVIEW_ALIAS','merge_authorized':False})
    return prepared,observations

def _semantic_key_for_synset(primary_synset:str)->str:
    slug=re.sub(r'[^a-z0-9._-]+','-',primary_synset.casefold()).strip('-')
    slug=re.sub(r'-+','-',slug)
    base='wordnet.primary.'+slug
    if len(base)>120:
        suffix=hashlib.sha256(primary_synset.encode()).hexdigest()[:16]
        base=base[:103].rstrip('._-')+'-'+suffix
    if not re.fullmatch(r'[a-z0-9][a-z0-9._-]{2,119}',base):
        raise TaxonomyFamilyMapError('E_SEMANTIC_KEY_SLUG',primary_synset)
    return base


def _family_for_synset(primary_synset:str, members:list[dict[str,Any]], *, db_ref:str, source_fingerprint:str)->dict[str,Any]:
    ordered=sorted(members,key=lambda x:x['subject_id'])
    if len(ordered)<2: raise TaxonomyFamilyMapError('E_FAMILY_TOO_SMALL',primary_synset)
    if 1+len(ordered)>MAX_EVIDENCE: raise TaxonomyFamilyMapError('E_FAMILY_EVIDENCE_OVERFLOW',f'{primary_synset}:{len(ordered)}')
    semantic_key=_semantic_key_for_synset(primary_synset)
    family={
        'schema':'die.h01.semantic-family.v1','schema_version':'1.0.0','family_version':FAMILY_VERSION,'artifact_kind':'SEMANTIC_FAMILY','family_id':'',
        'family_class':'TAXONOMIC',
        'semantic_identity':{
            'semantic_key':semantic_key,
            'definition':f'Object Atlas members sharing exact stored primary WordNet noun synset {primary_synset}.',
            'member_identity_policy':'PRESERVE_CANONICAL_SUBJECT','family_membership_creates_new_asset_identity':False,
        },
        'members':[{
            'member_id':m['subject_id'],'member_kind':'CANONICAL_SEMANTIC_MEMBER',
            'canonical_subject_ref':{'source':'OBJECT_ATLAS','subject_id':m['subject_id'],'canonical_name':m['canonical_name']},
            'semantic_label':m['canonical_name'],'identity_effect':'NONE',
        } for m in ordered],
        'source':{
            'environment':'CANONICAL','derivation':'DETERMINISTIC','evidence':[
                {'evidence_id':f'taxonomy:{primary_synset}','kind':'OBJECT_ATLAS_TAXONOMY','ref':f'{db_ref}#candidate_seeds.wordnet_synsets[0]={primary_synset}','sha256':source_fingerprint},
                *[
                    {'evidence_id':f"record:{m['subject_id']}",'kind':'OBJECT_ATLAS_RECORD','ref':f"{db_ref}#candidate_seeds.id={m['subject_id']};raw_noun_id={m['raw_noun_id']}"}
                    for m in ordered
                ],
            ]
        },
        'rights_class':'REVIEW_REQUIRED',
        'authority':{'production_authorized':False,'submission_authorized':False,'publication_authorized':False,'restricted_family_auto_eligible':False},
        'boundary':{'is_design_set':False,'is_derivative_bundle':False,'is_listing_package':False,'derivatives_create_family_members':False},
        'determinism':{'family_id_algorithm':'SHA256','family_id_hex_chars':24,'member_order':'CANONICAL_SUBJECT_ID_ASC','key_material':['family_version','family_class','semantic_identity.semantic_key','members[].canonical_subject_ref.subject_id']},
    }
    family['family_id']=canonical_family_id(family); validate_semantic_family(family); return family

def map_taxonomy_families(rows:list[dict[str,Any]], *, db_ref:str)->dict[str,Any]:
    prepared,alias_observations=_prepare_rows(rows)
    source_projection=[{k:m[k] for k in ('subject_id','raw_noun_id','canonical_name','aliases','primary_synset','suitability','ip_risk')} for m in prepared]
    source_fingerprint=sha256_value(source_projection)
    groups:dict[str,list[dict[str,Any]]]=defaultdict(list)
    for m in prepared: groups[m['primary_synset']].append(m)
    semantic_keys:dict[str,str]={}
    for synset in groups:
        key=_semantic_key_for_synset(synset)
        prior=semantic_keys.get(key)
        if prior is not None and prior!=synset:
            raise TaxonomyFamilyMapError('E_SEMANTIC_KEY_COLLISION',f'{prior}|{synset}|{key}')
        semantic_keys[key]=synset
    families=[]; singleton_count=0
    for synset in sorted(groups):
        members=groups[synset]
        if len(members)<2: singleton_count+=1; continue
        families.append(_family_for_synset(synset,members,db_ref=db_ref,source_fingerprint=source_fingerprint))
    families.sort(key=lambda f:(f['semantic_identity']['semantic_key'],f['family_id']))
    seen_members=[]
    for f in families: seen_members.extend(m['member_id'] for m in f['members'])
    if len(seen_members)!=len(set(seen_members)): raise TaxonomyFamilyMapError('E_MEMBER_IN_MULTIPLE_PRIMARY_FAMILIES')
    return {
        'schema':SCHEMA,'mapper_revision':'1.0.0','taxonomy_source':'OBJECT_ATLAS_STORED_PRIMARY_WORDNET_SYNSET',
        'source_fingerprint_sha256':source_fingerprint,'eligible_subject_count':len(prepared),'family_count':len(families),
        'family_member_count':len(seen_members),'standalone_singleton_count':singleton_count,'max_family_size':max((len(f['members']) for f in families),default=0),
        'families':families,'alias_observations':alias_observations,
        'controls':{
            'standalone_identity_preserved':True,'family_membership_creates_new_asset_identity':False,'shared_primary_synset_is_alias_merge_authority':False,
            'alias_merge_authorized':False,'duplicate_subject_id_allowed':False,'duplicate_raw_noun_id_allowed':False,'duplicate_normalized_canonical_name_allowed':False,
            'rights_class_default':'REVIEW_REQUIRED','production_authorized':False,
        },
    }

def export_taxonomy_families(*, db_path:str|Path, output_dir:str|Path, expected_eligible:int|None=43005)->dict[str,Any]:
    db=Path(db_path).resolve(); out=Path(output_dir).resolve()
    rows=_read_rows(db)
    if expected_eligible is not None and len(rows)!=expected_eligible: raise TaxonomyFamilyMapError('E_ELIGIBLE_COUNT_MISMATCH',f'{len(rows)}!={expected_eligible}')
    result=map_taxonomy_families(rows,db_ref=str(db))
    out.mkdir(parents=True,exist_ok=True)
    families_path=out/'families.jsonl'; aliases_path=out/'alias-observations.jsonl'; manifest_path=out/'manifest.json'
    family_bytes=b''.join(_canon(f)+b'\n' for f in result['families']); alias_bytes=b''.join(_canon(a)+b'\n' for a in result['alias_observations'])
    families_path.write_bytes(family_bytes); aliases_path.write_bytes(alias_bytes)
    manifest={k:v for k,v in result.items() if k not in {'families','alias_observations'}}
    manifest.update({'schema':MANIFEST_SCHEMA,'source_db':str(db),'source_query':"candidate_seeds.wave3_status='eligible' ORDER BY raw_noun_id ASC,id ASC",'families_jsonl_sha256':hashlib.sha256(family_bytes).hexdigest(),'alias_observations_jsonl_sha256':hashlib.sha256(alias_bytes).hexdigest(),'alias_observation_count':len(result['alias_observations'])})
    manifest_path.write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    return manifest

if __name__=='__main__':
    import argparse
    ap=argparse.ArgumentParser(); ap.add_argument('--db',required=True); ap.add_argument('--output-dir',required=True); ap.add_argument('--expected-eligible',type=int,default=43005)
    ns=ap.parse_args(); print(json.dumps(export_taxonomy_families(db_path=ns.db,output_dir=ns.output_dir,expected_eligible=ns.expected_eligible),sort_keys=True))
