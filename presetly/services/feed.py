"""Feed preset: feed.json hasil crawler (branch `data`), fallback ke scan cepat di server."""

import threading
import time

import requests

from ..config import FEED_URL, HTTP_TIMEOUT
from ..sources import tiktok

_LOCK = threading.Lock()
_BUILD_LOCK = threading.Lock()
_REMOTE: dict = {"at": 0.0, "data": None}
_LIVE: dict = {"at": 0.0, "data": None}
_EMPTY = {"updated": None, "mode": "empty", "items": []}
LIVE_TTL = 1800


def remote_feed(max_age: int = 600) -> dict | None:
    now = time.time()
    with _LOCK:
        if _REMOTE["at"] and now - _REMOTE["at"] < max_age:
            return _REMOTE["data"]
    try:
        r = requests.get(FEED_URL, timeout=HTTP_TIMEOUT)
        data = r.json() if r.ok else None
    except (requests.RequestException, ValueError):
        data = None
    ok = isinstance(data, dict) and isinstance(data.get("items"), list) and bool(data["items"])
    with _LOCK:
        _REMOTE.update(at=now, data=data if ok else None)
        return _REMOTE["data"]


def live_feed() -> dict:
    """Scan cepat di server. Satu build per instance tiap 30 menit (lock biar gak dobel)."""
    with _LOCK:
        if _LIVE["data"] and time.time() - _LIVE["at"] < LIVE_TTL:
            return _LIVE["data"]
    with _BUILD_LOCK:
        with _LOCK:
            if _LIVE["data"] and time.time() - _LIVE["at"] < LIVE_TTL:
                return _LIVE["data"]
        from ..crawler import quick_feed

        try:
            data = quick_feed()
        except Exception:
            data = None
        with _LOCK:
            if data and data.get("items"):
                _LIVE.update(at=time.time(), data=data)
            threading.Thread(target=_maybe_push, daemon=True).start()
            return _LIVE["data"] or _EMPTY


def _maybe_push():
    """Sambil live feed dibangun, cek postingan baru creator yang dipantau (throttle di push.py)."""
    try:
        from .. import push

        if push.enabled():
            push.check_and_notify()
    except Exception:  # noqa: S110 - notifikasi boleh gagal tanpa ngerusak feed
        pass


def get_feed() -> dict:
    return remote_feed() or live_feed()


def videos_for_tag(tag: str, limit: int) -> list[dict]:
    """Video TikTok yang ditemuin crawler lewat #tag (cuma dari feed crawler, gak mancing scan live)."""
    want = "#" + tag.lower()
    out, seen = [], set()
    for preset in (remote_feed() or {}).get("items") or []:
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
