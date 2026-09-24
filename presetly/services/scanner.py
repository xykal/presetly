"""Orkestrasi: bikin daftar video (list) lalu scan per batch (scan).

Frontend manggil /api/list sekali, terus /api/scan per 3-4 video secara paralel.
Pola ini bikin tiap request serverless pendek (< 15 detik), progress real-time,
dan gak butuh state job di server (cocok buat Vercel yang stateless).
"""

import re
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..config import MAX_LIST_ITEMS, MAX_SCAN_ITEMS
from ..links import RE_AM_SHARE, RE_AM_SHORT, LinkBag, host_matches
from ..sources import tiktok, youtube
from ..util import SourceError, short_err
from . import feed, resolver

_POOL = ThreadPoolExecutor(max_workers=8, thread_name_prefix="scan")


def classify(url: str) -> str | None:
    """Klasifikasi berdasarkan HOSTNAME hasil parse, bukan substring.

    Substring gampang dikibulin (https://evil.com/?youtube.com/playlist) dan bikin
    server nge-fetch URL sembarang lewat yt-dlp generic extractor (SSRF).
    """
    try:
        pu = urllib.parse.urlparse(url if "://" in url else "https://" + url)
    except ValueError:
        return None
    if pu.scheme not in ("http", "https"):
        return None
    host, path = (pu.hostname or "").lower(), pu.path or "/"
    if host in ("alight.link", "alight.page.link"):
        return "am" if RE_AM_SHORT.search(url) else None
    if host_matches(host, ("alightcreative.com",)):
        return "am" if RE_AM_SHARE.search(url) else None
    if host in ("vt.tiktok.com", "vm.tiktok.com"):
        return "tt_video"
    if host_matches(host, ("tiktok.com",)):
        if path.startswith("/t/") or re.match(r"^/@[\w.\-]*/(video|photo)/\d+", path):
            return "tt_video"
        if path.startswith("/tag/"):
            return "tt_tag"
        if re.match(r"^/@[\w.\-]+", path):
            return "tt_profile"
        return None
    if host == "youtu.be":
        return "yt_video"
    if host_matches(host, ("youtube.com",)):
        if re.match(r"^/(watch|shorts/|live/|embed/)", path):
            return "yt_video"
        if "list=" in (pu.query or ""):
            return "yt_playlist"
        if re.match(r"^/(@|channel/|c/|user/)", path):
            return "yt_channel"
    return None


def yt_playlist_url(url: str) -> str | None:
    q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    lid = (q.get("list") or [""])[0]
    return "https://www.youtube.com/playlist?list=" + lid if re.fullmatch(r"[\w-]{10,64}", lid) else None


def _dedupe(items: list[dict]) -> list[dict]:
    seen, out = set(), []
    for it in items:
        key = (it["platform"], it["id"])
        if key not in seen:
            seen.add(key)
            out.append(it)
    return out


def build_list(p: dict) -> dict:
    """p = {platform, mode, query, limit, sort, live}. Return {items, profile, notes, preset_check}."""
    platform, mode = p.get("platform"), p.get("mode")
    query = (p.get("query") or "").strip()
    limit = max(1, min(int(p.get("limit") or 20), MAX_LIST_ITEMS))
    items: list[dict] = []
    profile, notes = None, []
    preset_check = None

    if not query:
        raise SourceError("Isi dulu keyword / link-nya")

    if platform == "youtube":
        items = youtube.channel(query, limit) if mode == "channel" else youtube.search(query, limit, p.get("sort") or "relevance")
    elif platform == "tiktok":
        if mode == "profile":
            profile, items = tiktok.profile(query, limit)
        else:
            tag = tiktok.parse_tag(query)
            if not tag:
                raise SourceError("Hashtag kosong")
            if p.get("live"):
                items = tiktok.hashtag_live([tag], limit).get(tag, [])
            else:
                # IP cloud diblok buat item_list hashtag: gabungin video hasil crawler (feed) + video teratas dari embed.
                from_feed = feed.videos_for_tag(tag, limit)
                try:
                    from_embed = tiktok.embed_tag(tag)
                except Exception:
                    from_embed = []
                items = from_feed + from_embed
                notes.append(f"hashtag-lite:{len(from_feed)}:{len(from_embed)}")
    elif platform == "link":
        bag = LinkBag()
        for tok in re.findall(r"\S+", query)[:40]:
            url = tok if tok.startswith("http") else ("https://" + tok if re.match(r"^[\w.-]+\.[a-z]{2,}/", tok) else tok)
            kind = classify(url)
            try:
                if kind == "am":
                    bag.add_url(url, "input")
                elif kind == "yt_video":
                    m = youtube.RE_YT_ID.search(url)
                    if m:
                        items.append(youtube.base_rec(m.group(1), short="/shorts/" in url))
                elif kind == "yt_playlist":
                    pl = yt_playlist_url(url)
                    if not pl:
                        raise SourceError("ID playlist gak valid")
                    items += youtube.playlist(pl, limit)
                elif kind == "yt_channel":
                    items += youtube.channel(url, limit)
                elif kind == "tt_video":
                    items.append(tiktok.video(url))
                elif kind == "tt_profile":
                    prof, recs = tiktok.profile(url, limit)
                    profile = profile or prof
                    items += recs
                elif kind == "tt_tag":
                    items += tiktok.embed_tag(tiktok.parse_tag(url))
                else:
                    notes.append("skip:" + tok[:60])
            except Exception as e:
                notes.append(f"gagal:{tok[:60]}:{short_err(e)}")
        if bag:
            preset_check = resolver.enrich(bag.list())
    else:
        raise SourceError("Platform gak valid")

    if profile and profile.get("links"):
        profile["links"] = resolver.enrich(profile["links"])
    items = _dedupe(items)
    for i, it in enumerate(items):
        it["rank"] = i
    return {
        "items": items[: limit if platform != "link" else MAX_LIST_ITEMS],
        "profile": profile,
        "notes": notes,
        "preset_check": preset_check,
    }


def scan_one(item: dict, opts: dict) -> dict:
    rec = dict(item)
    try:
        if rec["platform"] == "youtube":
            rec = youtube.scan(rec, scan_comments=opts.get("comments", True))
        elif rec["platform"] == "tiktok":
            rec = tiktok.scan(rec, scan_comments=opts.get("comments", True), deep=opts.get("deep", True))
        else:
            rec["links"] = []
        rec["links"] = resolver.enrich(rec.get("links") or [], opts.get("resolve", True))
    except Exception as e:
        rec.setdefault("links", [])
        rec["error"] = short_err(e)
    rec["scanned_at"] = int(time.time())
    return resolver.summarize(rec)


def scan_many(items: list[dict], opts: dict) -> list[dict]:
    items = items[:MAX_SCAN_ITEMS]
    futs = {_POOL.submit(scan_one, it, opts): i for i, it in enumerate(items)}
    out: list[dict | None] = [None] * len(items)
    for f in as_completed(futs):
        out[futs[f]] = f.result()
    return [r for r in out if r]
