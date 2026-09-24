"""Helper kecil yang dipake lintas modul."""

import re


class SourceError(RuntimeError):
    """Error yang pesannya aman ditampilin ke user."""


def dig(obj, *path):
    """Traversal aman buat JSON bersarang: dig(d, 'a', 0, 'b')."""
    for key in path:
        if isinstance(obj, dict):
            obj = obj.get(key)
        elif isinstance(obj, list) and isinstance(key, int) and -len(obj) <= key < len(obj):
            obj = obj[key]
        else:
            return None
    return obj


def short_err(exc) -> str:
    s = re.sub(r"\x1b\[[0-9;]*m", "", str(exc)).replace("ERROR: ", "").strip()
    return s[:240] or exc.__class__.__name__


def title_from(text: str | None, fallback: str = "(tanpa caption)") -> str:
    t = re.sub(r"\s+", " ", text or "").strip()
    return t[:160] if t else fallback


def to_int(v) -> int | None:
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return int(v)
    digits = re.sub(r"[^\d]", "", str(v))
    return int(digits) if digits else None
