import hashlib
EXPECTED = {
    "kanban.db:tasks": "sha256:eaf50a104d8b769d70f67a827cadc6ace52cb5ad108495ef6802aef2a7b6e0d0",
    "state.db:sessions": "sha256:b3863e8cd0b5f71d14185dad9c221f99060286441039ec5240e65c92d593e837",
}
def hash_columns(cols):
    """sha256 dari daftar kolom terurut (delimiter '|')."""
    return "sha256:" + hashlib.sha256(("|".join(cols)).encode("utf-8")).hexdigest()
def check(table_key, cols):
    """True=lolos pinned, False=drift (DEGRADED), None=belum di-pin (ASSUMED)."""
    expected = EXPECTED.get(table_key)
    if expected is None:
        return None
    return hash_columns(cols) == expected
def classify(ok):
    if ok is None:
        return "ASSUMED"
    return "VERIFIED" if ok else "DEGRADED"
