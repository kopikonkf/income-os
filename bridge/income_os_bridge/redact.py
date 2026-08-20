# redact.py — penyaring rahasia di jalur keluar (wajib dipakai tiap output)
import re

_PATTERNS = [
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}"),
    re.compile(r"\bgh[pous]_[A-Za-z0-9_-]{10,}"),
    re.compile(r"(?i)\b(api[_-]?key|token|secret|password)\b\s*[=:]\s*\S+"),
    re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{8,}"),
    re.compile(r"(?i)(\.env\b|\.hermes[\\/]\.env\b)"),
]

_REDACTED = "[REDACTED]"


def redact(text):
    if not isinstance(text, str):
        return text
    for p in _PATTERNS:
        text = p.sub(_REDACTED, text)
    return text


def redact_event(ev):
    out = dict(ev)
    for k in ("summary", "detail_ref"):
        if isinstance(out.get(k), str):
            out[k] = redact(out[k])
    return out
