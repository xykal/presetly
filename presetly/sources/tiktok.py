"""TikTok: profil, video, komentar, embed (hosted-safe) + hashtag via Playwright (lokal / crawler).

Peta akses dari IP datacenter (hasil probe Vercel sin1, 2026-09):
  OK   : /api/comment/list, /api/comment/list/reply, /embed/@user, /embed/tag/x, /embed/v2/id,
         oEmbed, yt-dlp user listing & single video, CDN video dari embed (tanpa cookie/referer)
  BLOK : /api/challenge/item_list (body kosong walau pakai headless Chromium), SSR halaman profil
Makanya hashtag lengkap cuma jalan lokal / di runner GitHub Actions (crawler -> feed.json).
"""

import json
import re
import time
import urllib.parse

import requests

from ..config import HTTP_TIMEOUT, UA
from ..http import TTLCache, session
from ..links import LinkBag, extract_links
from ..util import SourceError, dig, title_from, to_int
from .ytdlp_util import flatten, ydl

API = "https://www.tiktok.com/api/"
RE_VIDEO = re.compile(r"tiktok\.com/@([\w.\-]*)/(video|photo)/(\d+)")
RE_SHORT = re.compile(r"(?:vt|vm)\.tiktok\.com/|tiktok\.com/t/")
ASK_RE = re.compile(r"preset|link|xml|\bam\b|\bcc\b|mana|minta|share|bagi|pls|please|info|turun|drop|5mb|kasih|min\b", re.I)
_MEDIA_CACHE = TTLCache(2000)
PLAY_TTL = 600  # play URL signed CDN cepat expired
MEDIA_TTL = 24 * 3600  # cache entry (cover awet, play diperbarui tiap PLAY_TTL)


# ---------------------------------------------------------------------------
# util
# ---------------------------------------------------------------------------
def parse_user(s: str) -> str:
    s = (s or "").strip()
    m = re.search(r"tiktok\.com/@([\w.\-]+)", s)
    return (m.group(1) if m else s).lstrip("@").strip("/ ")


def parse_tag(s: str) -> str:
    s = (s or "").strip()
    m = re.search(r"tiktok\.com/tag/([^/?#]+)", s)
    if m:
        s = urllib.parse.unquote(m.group(1))
    return re.sub(r"[^\w]", "", s.lstrip("#"), flags=re.UNICODE)[:80]


def video_url(user: str | None, vid: str, kind: str = "video") -> str:
    return "https://www.tiktok.com/@{}/{}/{}".format(user or "_", kind, vid)


def ts_from_id(vid: str) -> int | None:
    try:
        return int(vid) >> 32
    except (TypeError, ValueError):
        return None


def base_rec(vid: str, **kw) -> dict:
    user = kw.get("author_handle")
    rec = {
        "platform": "tiktok",
        "id": str(vid),
        "url": video_url(user, vid, kw.pop("kind", "video")),
        "title": None,
        "caption": "",
        "author": None,
        "author_handle": user,
        "author_url": "https://www.tiktok.com/@" + user if user else None,
        "views": None,
        "likes": None,
        "duration": None,
        "ts": ts_from_id(vid),
        "thumb": None,
        "play": None,
        "vertical": True,
    }
    rec.update({k: v for k, v in kw.items() if v is not None})
    rec["title"] = title_from(rec.get("caption"), "(video TikTok tanpa caption)")
    return rec


# ---------------------------------------------------------------------------
# embed (Frontity SSR) - jalan dari IP datacenter
# ---------------------------------------------------------------------------
def frontity_state(url: str) -> dict | None:
    r = session().get(url, timeout=HTTP_TIMEOUT, headers={"User-Agent": UA})
    if r.status_code != 200:
        return None
    m = re.search(r'<script[^>]*id="__FRONTITY_CONNECT_STATE__"[^>]*>(.*?)</script>', r.text, re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(1))
    except ValueError:
        return None


def _page(state: dict | None, prefix: str) -> dict:
    for k, v in (dig(state, "source", "data") or {}).items():
        if k.startswith(prefix) and isinstance(v, dict):
            return v
    return {}


def parse_embed_list(state: dict | None, prefix: str) -> tuple[dict | None, list[dict]]:
    page = _page(state, prefix)
    recs = []
    for v in page.get("videoList") or []:
        if not v.get("id") or v.get("privateItem"):
            continue
        recs.append(
            base_rec(
                v["id"],
                author_handle=v.get("authorUniqueId"),
                caption=v.get("desc") or "",
                views=to_int(v.get("playCount")),
                thumb=v.get("coverUrl") or v.get("originCoverUrl"),
                play=v.get("playAddr"),
                vertical=(v.get("height") or 16) >= (v.get("width") or 9),
            )
        )
    ui = page.get("userInfo")
    profile = None
    if ui and ui.get("uniqueId"):
        profile = {
            "handle": ui.get("uniqueId"),
            "name": ui.get("nickname"),
            "bio": ui.get("signature") or "",
            "avatar": ui.get("avatarThumbUrl"),
            "followers": to_int(ui.get("followerCount")),
            "likes": to_int(ui.get("heartCount")),
            "verified": bool(ui.get("verified")),
            "url": "https://www.tiktok.com/@" + ui["uniqueId"],
        }
    return profile, recs


def parse_embed_video(state: dict | None) -> dict | None:
    vd = _page(state, "/embed/v2/").get("videoData") or {}
    ii, ai = vd.get("itemInfos") or {}, vd.get("authorInfos") or {}
    if not ii.get("id"):
        return None
    meta = dig(ii, "video", "videoMeta") or {}
    rec = base_rec(
        ii["id"],
        author_handle=ai.get("uniqueId"),
        author=ai.get("nickName"),
        caption=ii.get("text") or "",
        views=to_int(ii.get("playCount")),
        likes=to_int(ii.get("diggCount")),
        duration=meta.get("duration"),
        ts=to_int(ii.get("createTime")),
        thumb=(ii.get("covers") or [None])[0],
        play=(dig(ii, "video", "urls") or [None])[0],
        vertical=(meta.get("height") or 16) >= (meta.get("width") or 9),
        kind="photo" if vd.get("imagePostInfo") else "video",
    )
    return rec


def embed_user(user: str) -> tuple[dict | None, list[dict]]:
    return parse_embed_list(frontity_state("https://www.tiktok.com/embed/@" + urllib.parse.quote(user)), "/embed/@")


def embed_tag(tag: str) -> list[dict]:
    return parse_embed_list(frontity_state("https://www.tiktok.com/embed/tag/" + urllib.parse.quote(tag)), "/embed/tag/")[1]


def embed_video(vid: str) -> dict | None:
    return parse_embed_video(frontity_state("https://www.tiktok.com/embed/v2/" + vid))


def media(vid: str) -> dict:
    """URL mp4 (embed, bisa diputer tanpa cookie) + cover.

    Play URL itu signed URL CDN yang cepat expired, jadi cache-nya PENDENDEK (10 menit).
    Cover awet di-cache 24 jam.
    """
    now = time.time()
    hit = _MEDIA_CACHE.get(vid) or {}
    if hit.get("play") and now - hit.get("at", 0) < PLAY_TTL:
        return {"play": hit["play"], "thumb": hit.get("thumb")}
    try:
        rec = embed_video(vid) or {}
    except requests.RequestException:
        rec = {}
    play = rec.get("play") or hit.get("play")  # play lama lebih baik daripada nihil (frontend ada fallback)
    thumb = rec.get("thumb") or hit.get("thumb")
    if play or thumb:
        _MEDIA_CACHE.set(vid, {"play": play, "thumb": thumb, "at": now}, MEDIA_TTL)
    return {"play": play, "thumb": thumb}


# ---------------------------------------------------------------------------
# listing
# ---------------------------------------------------------------------------
def _rec_from_ytdlp(e: dict) -> dict:
    thumb = None
    for t in e.get("thumbnails") or []:
        if t.get("id") in ("cover", "originCover") and t.get("url"):
            thumb = t["url"]
            break
    return base_rec(
        str(e.get("id")),
        author_handle=e.get("uploader"),
        author=e.get("channel") or e.get("uploader"),
        caption=e.get("description") or e.get("title") or "",
        views=e.get("view_count"),
        likes=e.get("like_count"),
        duration=e.get("duration"),
        ts=e.get("timestamp"),
        thumb=thumb or e.get("thumbnail"),
    )


def profile(user: str, limit: int = 30) -> tuple[dict | None, list[dict]]:
    user = parse_user(user)
    if not re.fullmatch(r"[\w.\-]{2,40}", user):
        raise SourceError("Username TikTok gak valid")
    prof, emb = None, []
    try:
        prof, emb = embed_user(user)
    except requests.RequestException:
        pass
    recs: list[dict] = []
    try:
        with ydl(extract_flat="in_playlist", playlistend=limit) as y:
            info = y.extract_info("https://www.tiktok.com/@" + user, download=False)
        recs = [_rec_from_ytdlp(e) for e in flatten(info) if e and e.get("id")]
    except Exception:
        recs = []
    # Lengkapi pakai data embed (punya URL play mp4 yang langsung bisa diputer).
    by_id = {r["id"]: r for r in emb}
    for r in recs:
        e = by_id.pop(r["id"], None)
        if e:
            r["play"] = e.get("play")
            r["thumb"] = r.get("thumb") or e.get("thumb")
    if not recs:
        recs = emb
    if not recs and not prof:
        raise SourceError(f"Profil @{user} gak ketemu, private, atau belum ada video")
    if prof:
        prof["links"] = extract_links(prof.get("bio") or "")
    return prof, recs[:limit]


def resolve_short(url: str) -> str:
    if RE_SHORT.search(url):
        try:
            return session().get(url, allow_redirects=True, timeout=HTTP_TIMEOUT).url
        except requests.RequestException:
            pass
    return url


def video(url: str) -> dict:
    url = resolve_short(url)
    m = RE_VIDEO.search(url)
    if not m:
        raise SourceError("Link TikTok gak valid: " + url[:80])
    user, kind, vid = m.groups()
    if kind == "video":
        try:
            with ydl() as y:
                info = y.extract_info(video_url(user, vid), download=False, process=False)
            rec = _rec_from_ytdlp(info)
            rec["play"] = media(vid).get("play")
            return rec
        except Exception:  # noqa: S110 - fallback ke embed/oEmbed di bawah
            pass
    rec = None
    try:
        rec = embed_video(vid)
    except requests.RequestException:
        pass
    if rec:
        return rec
    rec = base_rec(vid, author_handle=user or None, kind=kind)
    try:
        j = (
            session()
            .get("https://www.tiktok.com/oembed", params={"url": video_url(user, vid, kind)}, timeout=HTTP_TIMEOUT)
            .json()
        )
        rec.update(
            caption=j.get("title") or "",
            author=j.get("author_name"),
            thumb=j.get("thumbnail_url"),
            title=title_from(j.get("title"), "(postingan TikTok)"),
        )
    except (requests.RequestException, ValueError):
        pass
    return rec


def hashtag_live(tags: list[str], limit: int = 40, max_seconds: int = 60, on_progress=None) -> dict[str, list[dict]]:
    """Scroll halaman hashtag di headless Chromium & tangkep respons /api/challenge/item_list.

    Butuh `pip install playwright && python -m playwright install chromium`.
    Cuma jalan dari IP rumahan / runner GitHub Actions (IP datacenter AWS diblok TikTok).
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        raise SourceError(
            "Mode hashtag live butuh Playwright: pip install playwright && python -m playwright install chromium"
        ) from e
    out: dict[str, list[dict]] = {}
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(
                headless=True, args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-blink-features=AutomationControlled"]
            )
        except Exception as e:
            raise SourceError("Chromium Playwright belum ke-install: python -m playwright install chromium") from e
        try:
            ctx = browser.new_context(user_agent=UA, locale="id-ID", viewport={"width": 1280, "height": 900})
            ctx.route(
                "**/*",
                lambda route: route.abort() if route.request.resource_type in ("image", "media", "font") else route.continue_(),
            )
            for raw in tags:
                tag = parse_tag(raw)
                if not tag:
                    continue
                items: dict[str, dict] = {}
                pending: list = []
                state = {"more": True}
                page = ctx.new_page()
                page.on("response", lambda r, q=pending: q.append(r) if "/api/challenge/item_list" in r.url else None)
                try:
                    page.goto(
                        "https://www.tiktok.com/tag/" + urllib.parse.quote(tag), wait_until="domcontentloaded", timeout=45000
                    )
                    t0, stale = time.time(), 0
                    while len(items) < limit and time.time() - t0 < max_seconds:
                        page.wait_for_timeout(2200)
                        got = 0
                        while pending:
                            try:
                                j = pending.pop(0).json()
                            except Exception:  # noqa: S112 - respons non-JSON (body kosong) dilewat
                                continue
                            state["more"] = bool(j.get("hasMore"))
                            for it in j.get("itemList") or []:
                                if it.get("id") and it["id"] not in items:
                                    items[it["id"]] = it
                                    got += 1
                        if got and on_progress:
                            on_progress(tag, len(items))
                        stale = 0 if got else stale + 1
                        if (not items and time.time() - t0 > 25) or stale >= 4 or not state["more"]:
                            break
                        page.mouse.wheel(0, 6000)
                finally:
                    page.close()
                out[tag] = [_rec_from_item(it) for it in list(items.values())[:limit]]
        finally:
            browser.close()
    return out


def _rec_from_item(it: dict) -> dict:
    a, st, v = it.get("author") or {}, it.get("stats") or {}, it.get("video") or {}
    return base_rec(
        str(it.get("id")),
        author_handle=a.get("uniqueId"),
        author=a.get("nickname"),
        caption=it.get("desc") or "",
        views=to_int(st.get("playCount")),
        likes=to_int(st.get("diggCount")),
        duration=v.get("duration"),
        ts=to_int(it.get("createTime")),
        thumb=v.get("cover") or v.get("originCover"),
        kind="photo" if it.get("imagePost") else "video",
    )


# ---------------------------------------------------------------------------
# komentar
# ---------------------------------------------------------------------------
def _api(path: str, params: dict) -> dict:
    for attempt in range(2):
        try:
            r = session().get(
                API + path, params={"aid": "1988", **params}, headers={"Referer": "https://www.tiktok.com/"}, timeout=HTTP_TIMEOUT
            )
            if r.text.strip():
                return r.json()
        except (requests.RequestException, ValueError):
            pass
        time.sleep(0.6 * (attempt + 1))
    return {}


def comments(vid: str, max_comments: int = 50) -> list[dict]:
    out, cursor = [], 0
    while len(out) < max_comments:
        j = _api("comment/list/", {"aweme_id": vid, "count": 50, "cursor": cursor})
        batch = j.get("comments") or []
        out += batch
        if not batch or not j.get("has_more"):
            break
        cursor = j.get("cursor") or cursor + len(batch)
    return out[:max_comments]


def replies(vid: str, cid: str, count: int = 30) -> list[dict]:
    return _api("comment/list/reply/", {"item_id": vid, "comment_id": cid, "count": count, "cursor": 0}).get("comments") or []


def scan(rec: dict, scan_comments: bool = True, deep: bool = True, max_threads: int = 5) -> dict:
    bag = LinkBag()
    bag.add_text(rec.get("caption"), "caption")
    author = (rec.get("author_handle") or "").lower()
    if scan_comments:
        threads = []
        for c in comments(rec["id"]):
            user = ((c.get("user") or {}).get("unique_id") or "").lower()
            text = c.get("text") or ""
            is_author = bool(author) and user == author
            src = (
                "komen pinned"
                if (c.get("author_pin") or c.get("stick_position"))
                else ("komen creator" if is_author else "komen")
            )
            bag.add_text(text, src, user, allow_other=is_author)
            previews = c.get("reply_comment") or []
            for rc in previews:
                ru = ((rc.get("user") or {}).get("unique_id") or "").lower()
                ra = bool(author) and ru == author
                bag.add_text(rc.get("text"), "balasan creator" if ra else "balasan", ru, allow_other=ra)
            if deep and (c.get("reply_comment_total") or 0) > len(previews) and (ASK_RE.search(text) or is_author):
                threads.append(c)
        threads.sort(key=lambda c: -(c.get("reply_comment_total") or 0))
        for c in threads[:max_threads]:
            for rc in replies(rec["id"], c.get("cid")):
                ru = ((rc.get("user") or {}).get("unique_id") or "").lower()
                ra = bool(author) and ru == author
                bag.add_text(rc.get("text"), "balasan creator" if ra else "balasan", ru, allow_other=ra)
    rec["links"] = bag.list()
    rec["bio_hint"] = bool(re.search(r"(di ?bio|dibio|cek ?bio|link.{0,12}bio|in bio)", rec.get("caption") or "", re.I))
    return rec
