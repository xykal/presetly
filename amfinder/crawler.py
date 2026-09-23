"""Generator feed preset.

- `crawl()`      : dijalanin GitHub Actions tiap 6 jam (IP runner gak diblok TikTok buat hashtag).
                   Output feed.json di-push ke branch `data`, dibaca web lewat /api/feed.
- `quick_feed()` : versi cepat (< 20 detik) yang aman dari IP cloud, dipake /api/feed sebagai
                   fallback kalau feed crawler gak kebaca.

Format: {"updated": ts, "mode": "crawler"|"live", "tags": [...], "items": [preset...]}
Tiap item = 1 preset aktif unik (dedupe by share_url) + daftar video sumbernya.
"""

import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

from .services import scanner
from .sources import tiktok, youtube

YT_QUERIES = ["preset alight motion", "preset am dibawah 5mb", "preset alight motion jedag jedug", "preset xml alight motion"]
QUICK_YT = ["preset alight motion", "preset am dibawah 5mb", "preset alight motion jedag jedug"]
QUICK_TT_TAGS = ["presetalightmotion", "presetdibawah5mb"]
MAX_ITEMS = 400
KEEP_DAYS = 21
SCAN_OPTS = {"comments": True, "deep": True, "resolve": True}


def _log(msg: str):
    print(msg, file=sys.stderr, flush=True)


def _dedupe(videos: list[dict]) -> list[dict]:
    seen, out = set(), []
    for v in videos:
        key = (v["platform"], v["id"])
        if key not in seen:
            seen.add(key)
            out.append(v)
    return out


def _scan_all(videos: list[dict], workers: int = 6) -> list[dict]:
    with ThreadPoolExecutor(workers) as ex:
        return list(ex.map(lambda v: scanner.scan_one(v, SCAN_OPTS), videos))


def crawl(out_path: str, tags: list[str], per_tag: int = 30):
    t0 = time.time()
    videos: list[dict] = []
    try:
        found = tiktok.hashtag_live(tags, per_tag, on_progress=lambda t, n: _log(f"  #{t}: {n}"))
        for tag, recs in found.items():
            _log(f"#{tag} -> {len(recs)} video")
            for r in recs:
                r["found_via"] = "#" + tag
            videos += recs
    except Exception as e:  # jangan gagalin seluruh crawl gara-gara TikTok
        _log(f"hashtag gagal: {e}")
    for q in YT_QUERIES:
        try:
            recs = youtube.search(q, 15, "new")
            for r in recs:
                r["found_via"] = "yt:" + q
            videos += recs
            _log(f"yt '{q}' -> {len(recs)}")
        except Exception as e:
            _log(f"yt gagal '{q}': {e}")

    uniq = _dedupe(videos)
    _log(f"scan {len(uniq)} video...")
    results = _scan_all(uniq)

    prev: dict = {}
    if os.path.exists(out_path):
        try:
            with open(out_path, encoding="utf-8") as f:
                prev = {it["key"]: it for it in json.load(f).get("items", [])}
        except (OSError, ValueError, KeyError):
            prev = {}

    feed = build_feed(results, prev, tags, mode="crawler")
    feed["took_sec"] = round(time.time() - t0)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(feed, f, ensure_ascii=False, separators=(",", ":"))
    _log(f"feed: {len(feed['items'])} preset aktif ({len(results)} video discan) dalam {feed['took_sec']}s")


def quick_feed(per_query: int = 8) -> dict:
    videos: list[dict] = []
    for q in QUICK_YT:
        try:
            for r in youtube.search(q, per_query, "new"):
                r["found_via"] = "yt:" + q
                videos.append(r)
        except Exception as e:
            _log(f"quick yt gagal '{q}': {e}")
    for tag in QUICK_TT_TAGS:
        try:
            for r in tiktok.embed_tag(tag):
                r["found_via"] = "#" + tag
                videos.append(r)
        except Exception as e:
            _log(f"quick tag gagal '{tag}': {e}")
    results = _scan_all(_dedupe(videos)[:30], workers=8)
    return build_feed(results, {}, QUICK_TT_TAGS, mode="live")


def build_feed(results: list[dict], prev: dict, tags: list[str], mode: str) -> dict:
    now = int(time.time())
    items: dict[str, dict] = {}
    for r in results:
        xmls = [lk["url"] for lk in r.get("links", []) if lk["type"] == "xml"][:3]
        for lk in r.get("links", []):
            info = lk.get("info") or {}
            if lk["type"] != "am" or info.get("status") != "ok":
                continue
            key = info.get("share_url") or lk["url"]
            old = prev.get(key) or {}
            it = items.get(key) or dict(old, key=key, first_seen=old.get("first_seen", now))
            short = lk["url"] if lk["url"].startswith("https://alight.link") else None
            it.update(
                {
                    "am_url": info.get("fixed_url") or short or it.get("am_url") or lk["url"],
                    "name": info.get("name"),
                    "size_mb": info.get("size_mb"),
                    "size_text": info.get("size_text"),
                    "projects": info.get("projects"),
                    "thumb": info.get("thumb"),
                    "last_seen": now,
                }
            )
            srcs = [s for s in it.get("sources", []) if s.get("video_url") != r.get("url")]
            srcs.insert(
                0,
                {
                    "platform": r["platform"],
                    "id": r["id"],
                    "video_url": r.get("url"),
                    "title": (r.get("title") or "")[:140],
                    "author": r.get("author"),
                    "author_handle": r.get("author_handle"),
                    "views": r.get("views"),
                    "source": lk["source"],
                    "xml": xmls,
                    "via": r.get("found_via"),
                    "vertical": r.get("vertical", True),
                    "thumb": r.get("thumb") if r["platform"] == "youtube" else None,
                },
            )
            it["sources"] = srcs[:8]
            items[key] = it
    # Preset lama yang masih < 21 hari tetap disimpen walau gak nongol di crawl ini.
    for key, it in prev.items():
        if key not in items and now - it.get("last_seen", 0) < KEEP_DAYS * 86400:
            items[key] = it

    def rank(it):
        views = (it.get("sources") or [{}])[0].get("views") or 0
        return (-it.get("last_seen", 0), -views)

    ordered = sorted(items.values(), key=rank)
    return {"updated": now, "mode": mode, "tags": tags, "items": ordered[:MAX_ITEMS]}
