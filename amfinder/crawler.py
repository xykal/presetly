"""Crawler feed preset. Dijalanin GitHub Actions tiap 6 jam (IP runner gak diblok TikTok).

Output feed.json (di-push ke branch `data`) dibaca web lewat /api/feed:
  {"updated": ts, "tags": [...], "items": [ {preset...}, ... ]}
Tiap item = 1 preset aktif unik (dedupe by share_url), plus video sumbernya.
"""

import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

from .services import scanner
from .sources import tiktok, youtube

YT_QUERIES = ["preset alight motion", "preset am dibawah 5mb", "preset alight motion jedag jedug", "preset xml alight motion"]
MAX_ITEMS = 400


def _log(msg: str):
    print(msg, file=sys.stderr, flush=True)


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

    seen, uniq = set(), []
    for v in videos:
        if (v["platform"], v["id"]) not in seen:
            seen.add((v["platform"], v["id"]))
            uniq.append(v)
    _log(f"scan {len(uniq)} video...")
    opts = {"comments": True, "deep": True, "resolve": True}
    with ThreadPoolExecutor(6) as ex:
        results = list(ex.map(lambda v: scanner.scan_one(v, opts), uniq))

    prev = {}
    if os.path.exists(out_path):
        try:
            with open(out_path, encoding="utf-8") as f:
                prev = {it["key"]: it for it in json.load(f).get("items", [])}
        except (OSError, ValueError):
            prev = {}

    now = int(time.time())
    items: dict[str, dict] = {}
    for r in results:
        xmls = [lk["url"] for lk in r.get("links", []) if lk["type"] == "xml"][:3]
        for lk in r.get("links", []):
            info = lk.get("info") or {}
            if lk["type"] != "am" or info.get("status") != "ok":
                continue
            key = info.get("share_url") or lk["url"]
            it = items.get(key) or dict(prev.get(key) or {}, key=key, first_seen=(prev.get(key) or {}).get("first_seen", now))
            it.update(
                {
                    "am_url": info.get("fixed_url")
                    or (lk["url"] if lk["url"].startswith("https://alight.link") else it.get("am_url") or lk["url"]),
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
    # simpan preset lama yang masih < 21 hari walau gak nongol di crawl ini
    for key, it in prev.items():
        if key not in items and now - it.get("last_seen", 0) < 21 * 86400:
            items[key] = it
    ordered = sorted(
        items.values(),
        key=lambda it: (-it.get("last_seen", 0), -(it["sources"][0].get("views") or 0) if it.get("sources") else 0),
    )
    feed = {"updated": now, "tags": tags, "took_sec": round(time.time() - t0), "items": ordered[:MAX_ITEMS]}
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(feed, f, ensure_ascii=False, separators=(",", ":"))
    _log(f"feed: {len(feed['items'])} preset aktif ({len(results)} video discan) dalam {feed['took_sec']}s")
