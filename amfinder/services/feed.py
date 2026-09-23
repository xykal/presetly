"""Feed preset hasil crawler GitHub Actions (feed.json di branch `data`)."""

import threading
import time

import requests

from ..config import FEED_URL, HTTP_TIMEOUT
from ..sources import tiktok

_LOCK = threading.Lock()
_CACHE: dict = {"at": 0.0, "data": None}
_EMPTY = {"updated": None, "items": []}


def get_feed(max_age: int = 600) -> dict:
    now = time.time()
    with _LOCK:
        fresh = _CACHE["data"] is not None and now - _CACHE["at"] < max_age
        if fresh:
            return _CACHE["data"]
    try:
        r = requests.get(FEED_URL, timeout=HTTP_TIMEOUT)
        data = r.json() if r.ok else None
    except (requests.RequestException, ValueError):
        data = None
    with _LOCK:
        if isinstance(data, dict) and isinstance(data.get("items"), list):
            _CACHE.update(at=now, data=data)
        elif _CACHE["data"] is None:
            _CACHE["at"] = now - max_age + 60  # gagal: coba lagi semenit lagi, jangan spam
        return _CACHE["data"] or _EMPTY


def videos_for_tag(tag: str, limit: int) -> list[dict]:
    """Video TikTok yang ditemuin crawler lewat #tag (cuma yang ada preset aktifnya)."""
    want = "#" + tag.lower()
    out, seen = [], set()
    for preset in get_feed().get("items") or []:
        for s in preset.get("sources") or []:
            vid = str(s.get("id") or "")
            if s.get("platform") != "tiktok" or (s.get("via") or "").lower() != want or not vid or vid in seen:
                continue
            seen.add(vid)
            out.append(
                tiktok.base_rec(
                    vid,
                    author_handle=s.get("author_handle"),
                    author=s.get("author"),
                    caption=s.get("title") or "",
                    views=s.get("views"),
                )
            )
    return out[:limit]
