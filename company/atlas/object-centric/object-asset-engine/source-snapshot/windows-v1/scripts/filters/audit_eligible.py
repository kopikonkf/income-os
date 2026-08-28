import json
import sqlite3
import re
from collections import Counter

conn = sqlite3.connect(r"D:\object-asset-engine\db\object_asset_engine.db")
conn.row_factory = sqlite3.Row

rows = conn.execute(
    """SELECT canonical_name, senses_count, wave1_soft_score, source_tier,
              wordnet_synsets, category_path
       FROM candidate_seeds WHERE wave3_status='eligible'"""
).fetchall()
print(f"total eligible: {len(rows)}")
words = [r["canonical_name"] for r in rows]

# 1. plural suspicion (ends with s but not common mass nouns)
plural_susp = [w for w in words if w.endswith("s") and not w.endswith(("ss", "us", "is"))]
print(f"\n1. ends-with-s (plural suspicion): {len(plural_susp)} ({len(plural_susp)/len(words)*100:.1f}%)")
print("   sample:", plural_susp[:15])

# 2. pharma/chemical suffix patterns
chem = [w for w in words if re.search(r"(ine$|ole$|ide$|ase$|yme$|anol$|oxide$|ium$)", w)]
print(f"\n2. chemical/pharma-looking suffix: {len(chem)}")
print("   sample:", chem[:15])

# 3. latin taxonomy look (genus species two-word latin)
latin = [w for w in words if re.fullmatch(r"[a-z]+ [a-z]+", w) and
         w.split()[0][-1] in "aus" and False]  # skip complex, do simple
multi = [w for w in words if " " in w]
print(f"\n3. multiword phrases: {len(multi)} ({len(multi)/len(words)*100:.1f}%)")
print("   sample:", multi[:15])

# 4. hyphenated
hyph = [w for w in words if "-" in w]
print(f"\n4. hyphenated: {len(hyph)}")
print("   sample:", hyph[:15])

# 5. length distribution
lens = Counter(len(w) for w in words)
print("\n5. length dist:", dict(sorted(lens.items())[:12]), "... max:", max(lens))
long_w = [w for w in words if len(w) > 20]
print("   >20 chars:", len(long_w), long_w[:10])

# 6. single-sense + low soft score = obscure risk
obscure = [r["canonical_name"] for r in rows
           if r["senses_count"] <= 1 and (r["wave1_soft_score"] or 0) <= 1]
print(f"\n6. obscure-risk (single-sense + soft<=1): {len(obscure)} ({len(obscure)/len(words)*100:.1f}%)")
print("   sample:", obscure[:20])

# 7. random 100 for manual eyeball
import random
random.seed(42)
print("\n7. RANDOM 100:")
sample = random.sample(words, 100)
for i in range(0, 100, 5):
    print("   ", " | ".join(sample[i:i+5]))

# 8. alphabetical slice (A, M, Z coverage)
for letter in ("bra", "mon", "zar"):
    seg = [w for w in words if w.startswith(letter)][:15]
    print(f"\n8. slice '{letter}...':", seg)
