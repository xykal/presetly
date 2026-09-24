"""Instagram: profil & reel lewat endpoint publik yang masih bisa diakses tanpa login (dicek 2026-09-24).

Jalan  : GET /api/v1/users/web_profile_info/?username=.. (profil + timeline + reels + video_url)
         GET /api/v1/oembed/?url=<link reel/post>       (caption, author, thumbnail, media_id)
Tembok : /api/v1/media/{id}/info (302 login), hashtag, komentar (butuh sesi login) -> gak dipakai.

Strategi link tunggal: oembed buat metadata + username author -> cari di 24 item terakhir profilnya
buat dapetin video_url segar. Kalau ketuaan / gak ketemu, preview jatuh ke iframe embed di frontend.
"""

import html
import re
import threading
import time
import urllib.parse

from ..config import HTTP_TIMEOUT
from ..http import TTLCache, session
from ..links import LinkBag, host_matches
from ..util import SourceError, to_int

API = "https://www.instagram.com/api/v1"
API2 = "https://www.instagram.com/api/v1"  # lapis 2: sama, tapi beda kuki (anti-429 loop)
API3 = "https://api.instagram.com/api/v1"  # lapis 3: public-API host resmi, WAF beda
APP_ID = "936619743392459"  # app id web publik Instagram (dipake klien web resmi)
RE_IG_URL = re.compile(r"(?:https?://)?(?:www\.)?instagram\.com/(?:[\w.\-]+/)?(reel|reels|p|tv)/([A-Za-z0-9_-]{5,24})", re.I)
RE_IG_USER = re.compile(r"(?:https?://)?(?:www\.)?instagram\.com/([\w.\-]+)/?$", re.I)
SHORTCODE_ALPHA = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"

_MEDIA_CACHE = TTLCache(2000)
PLAY_TTL = 900  # video_url signed CDN cepat expired
MEDIA_TTL = 24 * 3600


def short_to_media_id(code: str) -> int:
    n = 0
    for ch in code:
        n = n * 64 + SHORTCODE_ALPHA.index(ch)
    return n


_REQ_LOCK = threading.Lock()
_REQ_AT = [0.0]


def _throttle() -> None:
    """Jarak minimal antar-request IG. Cuma 0.25s — request berantai panjang
    (delay besar per-request = sinyal bot jelas); yang penting gak burst."""
    with _REQ_LOCK:
        wait = 0.25 - (time.time() - _REQ_AT[0])
        if wait > 0:
            time.sleep(wait)
        _REQ_AT[0] = time.time()


def _get(path: str, params: dict | None = None) -> dict:
    # Lapis penembus + anti rate-limit:
    #   ronde 1: www -> gagal/429 -> i.instagram.com (host mobile resmi, WAF beda)
    #   ronde 2: napas 1.4s dulu, coba dua host lagi (rate-limit biasanya lepas cepat)
    last: SourceError | None = None
    for ronde in range(2):
        for base in (API, API2, API3):
            _throttle()
            r = session().get(
                base + path,
                params=params,
                headers={"x-ig-app-id": APP_ID, "Accept": "*/*"},
                timeout=HTTP_TIMEOUT,
            )
            if r.status_code == 200:
                try:
                    return r.json()
                except ValueError:
                    last = SourceError("Respons Instagram gak valid")
                    continue
            last = SourceError(f"Instagram nolak request (HTTP {r.status_code})")
        if ronde == 0:
            import random

            time.sleep(2.2 + random.random() * 1.8)  # jitter, rendahin beban IP sesi
    assert last is not None
    raise last


def parse_url(url: str) -> tuple[str | None, str | None, str | None]:
    """-> (kind 'video'|'user', code/username, username dari path bila ada)."""
    u = urllib.parse.urlparse(url if "://" in url else "https://" + url)
    host = (u.hostname or "").lower()
    if not host_matches(host, ("instagram.com", "instagr.am")):
        return None, None, None
    path = urllib.parse.unquote(u.path or "/")
    m = re.match(r"^/(?:([\w.\-]+)/)?(reel|reels|p|tv)/([A-Za-z0-9_-]{5,24})/?", path)
    if m:
        return "video", m.group(3), m.group(1)
    m = re.match(r"^/([A-Za-z0-9._]{1,30})/?(reels|tagged)?/?$", path)
    if m and m.group(1).lower() not in ("p", "reel", "reels", "tv", "explore", "about", "developer", "accounts"):
        return "user", m.group(1), None
    return None, None, None


def base_rec(code: str, **kw) -> dict:
    rec = {
        "platform": "instagram",
        "id": code,
        "url": "https://www.instagram.com/reel/" + code + "/",
        "title": None,
        "caption": "",
        "author": None,
        "author_handle": None,
        "author_url": None,
        "views": None,
        "likes": None,
        "duration": None,
        "ts": None,
        "thumb": None,
        "play": None,
        "vertical": True,
        "kind": "video",
    }
    rec.update({k: v for k, v in kw.items() if v is not None})
    cap = rec.get("caption") or ""
    rec["title"] = cap.splitlines()[0][:80] if cap.strip() else "(reel Instagram)"
    return rec


def _caption_of(node: dict) -> str:
    edges = ((node.get("edge_media_to_caption") or {}).get("edges")) or []
    if edges:
        return html.unescape((edges[0].get("node") or {}).get("text") or "")
    return ""


def _rec_from_node(n: dict) -> dict | None:
    code = n.get("shortcode")
    if not code:
        return None
    meta = n.get("dimensions") or {}
    user = n.get("owner") or {}
    return base_rec(
        code,
        caption=_caption_of(n),
        author=user.get("username"),
        author_handle=user.get("username") or n.get("owner", {}).get("username"),
        views=to_int(n.get("video_view_count") or n.get("play_count")),
        likes=to_int(((n.get("edge_liked_by") or {}).get("count")) or (n.get("like_count"))),
        duration=int(float(n.get("video_duration") or 0)) or None,
        ts=to_int(n.get("taken_at_timestamp") or n.get("taken_at")),
        thumb=n.get("thumbnail_src") or n.get("display_url"),
        play=n.get("video_url"),
        vertical=(meta.get("height") or 16) >= (meta.get("width") or 9),
        kind="video",
    )


def web_profile(username: str) -> tuple[dict, list[dict]]:
    username = username.lstrip("@").strip()
    if not re.fullmatch(r"[A-Za-z0-9._]{1,30}", username):
        raise SourceError("Username Instagram gak valid")
    d = _get("/users/web_profile_info/", {"username": username})
    u = (d.get("data") or {}).get("user")
    if not u:
        raise SourceError(f"Profil @{username} gak ketemu atau private")
    if u.get("is_private"):
        raise SourceError(f"Profil @{username} private")
    items = []
    for key in ("edge_owner_to_timeline_media", "edge_felix_video_timeline"):
        for e in (u.get(key) or {}).get("edges") or []:
            n = e.get("node") or {}
            if n.get("is_video") or n.get("video_url"):
                r = _rec_from_node(n)
                if r:
                    items.append(r)
    seen, out = set(), []
    for r in items:  # dedupe, timeline dulu (paling baru)
        if r["id"] not in seen:
            seen.add(r["id"])
            r["author_handle"] = r.get("author_handle") or u.get("username")
            r["author"] = r.get("author") or u.get("full_name") or u.get("username")
            r["author_url"] = r.get("author_url") or ("https://www.instagram.com/" + u.get("username") + "/")
            out.append(r)
    profile = {
        "handle": u.get("username"),
        "name": u.get("full_name"),
        "bio": u.get("biography") or "",
        "avatar": u.get("profile_pic_url_hd") or u.get("profile_pic_url"),
        "followers": to_int((u.get("edge_followed_by") or {}).get("count")),
        "likes": None,
        "verified": bool(u.get("is_verified")),
        "url": "https://www.instagram.com/" + u.get("username") + "/",
    }
    # link bio (lynx_url di-unwrap: https://l.instagram.com/?u=<target>)
    bio_urls = []
    for b in u.get("bio_links") or []:
        raw = b.get("url") or ""
        if not raw:
            lu = urllib.parse.urlparse(b.get("lynx_url") or "")
            raw = (urllib.parse.parse_qs(lu.query).get("u") or [""])[0]
        if raw:
            bio_urls.append(raw)
    if u.get("external_url"):
        bio_urls.append(u["external_url"])
    if bio_urls or profile["bio"]:
        bag = LinkBag()
        bag.add_text("\n".join(bio_urls), "bio")
        bag.add_text(profile["bio"], "bio")
        profile["links"] = bag.list()
    return profile, out


def oembed(url: str) -> dict:
    r = session().get(
        API + "/oembed/",
        params={"url": url},
        headers={"x-ig-app-id": APP_ID},
        timeout=HTTP_TIMEOUT,
    )
    if r.status_code != 200:
        raise SourceError(f"Link Instagram gak ketemu (HTTP {r.status_code})")
    try:
        return r.json()
    except ValueError as e:
        raise SourceError("Respons oembed Instagram gak valid") from e


def video(url: str, hint_user: str | None = None) -> dict:
    """Link reel/post -> rec. video_url diambil dari timeline profil author kalau masih ada."""
    kind, code, user_in_url = parse_url(url)
    if not kind or kind != "video":
        raise SourceError("Link Instagram gak valid")
    kpath = "reel" if re.search(r"/reels?/", url, re.I) else ("tv" if "/tv/" in url else "p")
    url = f"https://www.instagram.com/{kpath}/{code}/"
    try:
        j = oembed(url)
    except SourceError:
        j = {}
    caption = html.unescape(j.get("title") or "")
    author_handle = (j.get("author_url") or "").rstrip("/").split("/")[-1] or hint_user or user_in_url
    rec = base_rec(
        code,
        caption=caption,
        author=j.get("author_name"),
        author_handle=author_handle or None,
        author_url=j.get("author_url"),
        thumb=j.get("thumbnail_url"),
        vertical=(j.get("thumbnail_height") or 16) >= (j.get("thumbnail_width") or 9),
    )
    # lengkapi video_url/views/durasi dari timeline author (masih dalam 24 item terakhir)
    if author_handle:
        try:
            _, recs = web_profile(author_handle)
            hit = next((r for r in recs if r["id"] == code), None)
            if hit:
                rec["play"] = hit.get("play")
                rec["views"] = rec["views"] or hit.get("views")
                rec["likes"] = rec["likes"] or hit.get("likes")
                rec["duration"] = rec["duration"] or hit.get("duration")
                rec["ts"] = rec["ts"] or hit.get("ts")
                rec["thumb"] = rec["thumb"] or hit.get("thumb")
                rec["caption"] = rec["caption"] or hit.get("caption")
        except SourceError:
            pass
    if not rec["caption"] and not rec["thumb"]:
        raise SourceError("Reel Instagram gak ketemu / private / udah dihapus")
    return rec


def media(code: str) -> dict:
    """play (video_url segar) + thumb buat satu kode reel. Cache: play 15 menit, thumb 24 jam."""
    now = time.time()
    hit = _MEDIA_CACHE.get(code) or {}
    if hit.get("play") and now - hit.get("at", 0) < PLAY_TTL:
        return {"play": hit["play"], "thumb": hit.get("thumb")}
    play, thumb = hit.get("play"), hit.get("thumb")
    try:
        rec = video(f"https://www.instagram.com/reel/{code}/")
        play = rec.get("play") or play
        thumb = rec.get("thumb") or thumb
    except SourceError:
        pass
    if play or thumb:
        _MEDIA_CACHE.set(code, {"play": play, "thumb": thumb, "at": now}, MEDIA_TTL)
    return {"play": play, "thumb": thumb}


def profile(user: str, limit: int = 24) -> tuple[dict | None, list[dict]]:
    kind, val, _ = parse_url(user)
    username = val if kind == "user" else user
    prof, recs = web_profile(username or user)
    return prof, recs[:limit]


def scan(rec: dict, scan_comments: bool = True, deep: bool = True) -> dict:
    """Link preset Instagram ada di caption (komen butuh login -> gak discan, jujur)."""
    bag = LinkBag()
    bag.add_text(rec.get("caption"), "caption")
    rec["links"] = bag.list()
    rec["bio_hint"] = bool(re.search(r"(di ?bio|dibio|cek ?bio|link.{0,12}bio|in bio)", rec.get("caption") or "", re.I))
    return rec
