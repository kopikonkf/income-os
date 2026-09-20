from pathlib import Path
import importlib.util

R=Path(__file__).resolve().parents[2]
P=R/'company/die-agents/hermes/production-runtime/nexaburst/bin/nexaburst-presence-gate.py'

def load_mod():
    spec=importlib.util.spec_from_file_location('nexaburst_presence_gate',P)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def test_irregular_plural_and_punctuation_variants_share_wordnet_head():
    m=load_mod()
    syn=('aardwolf.n.01',)
    for surface in ('aardwolf','aard-wolf','aardwolves','aard-wolves'):
        assert m.morphological_head(surface,syn)=='aardwolf'

def test_latin_plural_abaci_maps_to_abacus_head():
    m=load_mod()
    assert m.morphological_head('abacus',('abacus.n.01',))=='abacus'
    assert m.morphological_head('abaci',('abacus.n.01',))=='abacus'

def test_synonyms_do_not_collapse_when_not_morphological_variants():
    m=load_mod()
    syn=('backpack.n.01',)
    assert m.morphological_head('backpack',syn)=='backpack'
    assert m.morphological_head('back-packs',syn)=='backpack'
    assert m.morphological_head('haversack',syn) is None
