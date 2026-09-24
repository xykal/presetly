"""YouTube: search & listing channel (yt-dlp flat), detail + komentar (innertube /next).

Kenapa detail pakai innertube /next, bukan extractor penuh yt-dlp: dari IP datacenter
(Vercel/AWS) endpoint *player* YouTube minta "Sign in to confirm you're not a bot",
sedangkan /next (deskripsi + komentar) tetap jalan. Mode flat yt-dlp (search/listing)
juga aman. Kalau /next gagal, fallback ke yt-dlp penuh (jalan normal di IP rumahan).
"""

import re
import time
import urllib.parse
from datetime import UTC, datetime

from ..config import HTTP_TIMEOUT
from ..http import session
from ..links import LinkBag, strip_truncated
from ..util import SourceError, dig, short_err, to_int
from .ytdlp_util import flatten, ydl

RE_YT_ID = re.compile(r"(?:v=|youtu\.be/|shorts/|live/|embed/)([A-Za-z0-9_-]{11})")
_NEXT = "https://www.youtube.com/youtubei/v1/next?prettyPrint=false"
_MONTHS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "mei": 5,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "agu": 8,
    "agt": 8,
    "aug": 8,
    "sep": 9,
    "okt": 10,
    "oct": 10,
    "nov": 11,
    "des": 12,
    "dec": 12,
}


def _client_version() -> str:
    try:
        from yt_dlp.extractor.youtube._base import INNERTUBE_CLIENTS

        return INNERTUBE_CLIENTS["web"]["INNERTUBE_CONTEXT"]["client"]["clientVersion"]
    except Exception:
        return "2.20260708.00.00"


def base_rec(vid: str, *, title=None, author=None, views=None, duration=None, short=False) -> dict:
    return {
        "platform": "youtube",
        "id": vid,
        "url": ("https://www.youtube.com/shorts/%s" if short else "https://www.youtube.com/watch?v=%s") % vid,
        "title": title,
        "caption": "",
        "author": author,
        "author_handle": None,
        "author_url": None,
        "views": views,
        "likes": None,
        "duration": duration,
        "ts": None,
        "thumb": f"https://i.ytimg.com/vi/{vid}/mqdefault.jpg",
        "vertical": bool(short),
    }


def _entry(e: dict) -> dict | None:
    url = e.get("url") or ""
    vid = e.get("id")
    if not vid or len(vid) != 11:
        m = RE_YT_ID.search(url)
        vid = m.group(1) if m else None
    if not vid or (e.get("ie_key") or "Youtube").lower() != "youtube":
        return None
    return base_rec(
        vid,
        title=e.get("title"),
        author=e.get("channel") or e.get("uploader"),
        views=e.get("view_count"),
        duration=e.get("duration"),
        short="/shorts/" in url,
    )


def _flat(url: str, limit: int) -> list[dict]:
    with ydl(extract_flat="in_playlist", playlistend=limit) as y:
        info = y.extract_info(url, download=False)
    return [x for x in (_entry(e) for e in flatten(info)) if x]


def search(query: str, limit: int = 20, sort: str = "relevance") -> list[dict]:
    url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(query)
    if sort == "new":
        url += "&sp=CAI%253D"
    return _flat(url, limit)[:limit]


def channel_base(q: str) -> str:
    q = q.strip()
    if "/" in q or "." in q.split("@")[-1] and "youtube" in q:
        pu = urllib.parse.urlparse(q if "://" in q else "https://" + q)
        host = (pu.hostname or "").lower()
        if host not in ("youtube.com", "www.youtube.com", "m.youtube.com"):
            raise SourceError("Link channel harus dari youtube.com")
        m = re.match(r"^/(@[\w.\-]{1,100}|channel/UC[\w-]{22}|c/[\w.\-]{1,100}|user/[\w.\-]{1,100})", pu.path or "")
        if not m:
            raise SourceError("Format link channel gak dikenali")
        return "https://www.youtube.com/" + m.group(1).lstrip("/")
    if re.fullmatch(r"UC[\w-]{22}", q):
        return "https://www.youtube.com/channel/" + q
    handle = q.lstrip("@")
    if not re.fullmatch(r"[\w.\-]{1,100}", handle):
        raise SourceError("Handle channel gak valid")
    return "https://www.youtube.com/@" + handle


def channel(q: str, limit: int = 30) -> list[dict]:
    base = channel_base(q)
    lists, errors = [], []
    for tab in ("/shorts", "/videos"):
        try:
            lists.append(_flat(base + tab, limit))
        except Exception as e:  # channel tanpa tab shorts itu normal
            errors.append(e)
    out, seen = [], set()
    for i in range(max((len(x) for x in lists), default=0)):
        for lst in lists:
            if i < len(lst) and lst[i]["id"] not in seen:
                seen.add(lst[i]["id"])
                out.append(lst[i])
    if not out and errors:
        raise SourceError("Channel gak ketemu / kosong: " + short_err(errors[0]))
    return out[:limit]


def playlist(url: str, limit: int = 30) -> list[dict]:
    return _flat(url, limit)[:limit]


# ---------------------------------------------------------------------------
# innertube /next
# ---------------------------------------------------------------------------
def _next(body: dict) -> dict:
    ver = _client_version()
    ctx = {"client": {"clientName": "WEB", "clientVersion": ver, "hl": "id", "gl": "ID"}}
    r = session().post(
        _NEXT,
        json={"context": ctx, **body},
        timeout=HTTP_TIMEOUT,
        headers={"X-Youtube-Client-Name": "1", "X-Youtube-Client-Version": ver, "Origin": "https://www.youtube.com"},
    )
    r.raise_for_status()
    return r.json()


def _text(o) -> str:
    if not o:
        return ""
    if isinstance(o, str):
        return o
    if "simpleText" in o:
        return o["simpleText"]
    if "content" in o:
        return o["content"] or ""
    return "".join(r.get("text", "") for r in o.get("runs") or [])


def _unwrap(u: str) -> str:
    if "youtube.com/redirect" in u:
        q = urllib.parse.parse_qs(urllib.parse.urlparse(u).query).get("q")
        if q:
            return q[0]
    return u


def _run_urls(attributed: dict | None) -> list[str]:
    """URL lengkap dari commandRuns (teks deskripsi YouTube motong link panjang jadi '...')."""
    out = []
    for run in (attributed or {}).get("commandRuns") or []:
        u = dig(run, "onTap", "innertubeCommand", "urlEndpoint", "url")
        if u:
            out.append(_unwrap(u))
    return out


_REL = {
    "detik": 1,
    "menit": 60,
    "jam": 3600,
    "hari": 86400,
    "minggu": 604800,
    "bulan": 2592000,
    "tahun": 31536000,
    "second": 1,
    "minute": 60,
    "hour": 3600,
    "day": 86400,
    "week": 604800,
    "month": 2592000,
    "year": 31536000,
}


def parse_date(text: str) -> int | None:
    rel = re.search(r"(\d+)\s+(detik|menit|jam|hari|minggu|bulan|tahun|second|minute|hour|day|week|month|year)", text or "", re.I)
    m = re.search(r"(\d{1,2})\s+([A-Za-z]{3,})\.?\s+(\d{4})", text or "")
    if not m and rel:
        return int(time.time()) - int(rel.group(1)) * _REL[rel.group(2).lower()]
    if not m:
        return None
    mon = _MONTHS.get(m.group(2)[:3].lower())
    if not mon:
        return None
    try:
        return int(datetime(int(m.group(3)), mon, int(m.group(1)), tzinfo=UTC).timestamp())
    except ValueError:
        return None


def parse_watch_next(j: dict) -> dict:
    out = {
        "title": None,
        "desc": "",
        "desc_urls": [],
        "author": None,
        "author_url": None,
        "views": None,
        "ts": None,
        "ctoken": None,
    }
    contents = dig(j, "contents", "twoColumnWatchNextResults", "results", "results", "contents") or []
    for c in contents:
        p = c.get("videoPrimaryInfoRenderer")
        if p:
            out["title"] = _text(p.get("title")) or None
            out["views"] = to_int(_text(dig(p, "viewCount", "videoViewCountRenderer", "viewCount")))
            out["ts"] = parse_date(_text(p.get("dateText")))
        s = c.get("videoSecondaryInfoRenderer")
        if s:
            ad = s.get("attributedDescription") or {}
            out["desc"] = ad.get("content") or _text(s.get("description"))
            out["desc_urls"] = _run_urls(ad)
            owner = dig(s, "owner", "videoOwnerRenderer") or {}
            out["author"] = _text(owner.get("title")) or _text(owner.get("attributedTitle")) or None
            base = dig(owner, "navigationEndpoint", "browseEndpoint", "canonicalBaseUrl")
            if base:
                out["author_url"] = "https://www.youtube.com" + base
        isr = c.get("itemSectionRenderer")
        if isr and isr.get("sectionIdentifier") == "comment-item-section":
            for x in isr.get("contents") or []:
                tok = dig(x, "continuationItemRenderer", "continuationEndpoint", "continuationCommand", "token")
                if tok:
                    out["ctoken"] = tok
    return out


def parse_comments(j: dict) -> tuple[list[dict], str | None]:
    items = []
    for ep in j.get("onResponseReceivedEndpoints") or []:
        for k in ("reloadContinuationItemsCommand", "appendContinuationItemsAction"):
            items += (ep.get(k) or {}).get("continuationItems") or []
    ents = {}
    for m in dig(j, "frameworkUpdates", "entityBatchUpdate", "mutations") or []:
        payload = (m.get("payload") or {}).get("commentEntityPayload")
        if payload:
            ents[m.get("entityKey")] = payload
    out, nxt = [], None
    for it in items:
        tok = dig(it, "continuationItemRenderer", "continuationEndpoint", "continuationCommand", "token")
        if tok:
            nxt = tok
        vm = dig(it, "commentThreadRenderer", "commentViewModel", "commentViewModel")
        if not vm:
            continue
        e = ents.get(vm.get("commentKey"))
        if not e:
            continue
        content = dig(e, "properties", "content") or {}
        out.append(
            {
                "text": content.get("content") or "",
                "urls": _run_urls(content),
                "author": dig(e, "author", "displayName"),
                "creator": bool(dig(e, "author", "isCreator")),
                "pinned": "pinnedText" in vm,
            }
        )
    return out, nxt


def _detail_innertube(vid: str, scan_comments: bool, max_comments: int) -> dict:
    d = parse_watch_next(_next({"videoId": vid}))
    if not d["title"] and not d["desc"]:
        raise SourceError("Video gak bisa dibuka (private / dihapus / dibatasi umur)")
    comments = []
    tok = d["ctoken"] if scan_comments else None
    pages = 0
    while tok and len(comments) < max_comments and pages < 2:
        page, tok = parse_comments(_next({"continuation": tok}))
        comments += page
        pages += 1
    d["comments"] = comments[:max_comments]
    return d


def _detail_ytdlp(vid: str, scan_comments: bool, max_comments: int) -> dict:
    opts = {}
    if scan_comments:
        opts = {
            "getcomments": True,
            "extractor_args": {"youtube": {"max_comments": [str(max_comments), "all", "0", "0"], "comment_sort": ["top"]}},
        }
    with ydl(**opts) as y:
        info = y.extract_info("https://www.youtube.com/watch?v=" + vid, download=False, process=False)
        post = info.pop("__post_extractor", None)
        if post:
            try:
                info.update(post() or {})
            except Exception:  # noqa: S110 - komentar opsional, deskripsi tetap kepake
                pass
    ts = info.get("timestamp")
    if not ts and info.get("upload_date"):
        ts = int(datetime.strptime(info["upload_date"], "%Y%m%d").replace(tzinfo=UTC).timestamp())
    return {
        "title": info.get("title"),
        "desc": info.get("description") or "",
        "desc_urls": [],
        "author": info.get("channel") or info.get("uploader"),
        "author_url": info.get("uploader_url") or info.get("channel_url"),
        "views": info.get("view_count"),
        "ts": ts,
        "duration": info.get("duration"),
        "comments": [
            {
                "text": c.get("text") or "",
                "urls": [],
                "author": c.get("author"),
                "creator": bool(c.get("author_is_uploader")),
                "pinned": bool(c.get("is_pinned")),
            }
            for c in info.get("comments") or []
        ],
    }


def scan(rec: dict, scan_comments: bool = True, max_comments: int = 40) -> dict:
    try:
        d = _detail_innertube(rec["id"], scan_comments, max_comments)
    except Exception as first:
        try:
            d = _detail_ytdlp(rec["id"], scan_comments, max_comments)
        except Exception:
            raise SourceError(short_err(first)) from first
    rec["title"] = rec.get("title") or d.get("title")
    rec["author"] = rec.get("author") or d.get("author")
    rec["author_url"] = d.get("author_url")
    rec["views"] = rec.get("views") if rec.get("views") is not None else d.get("views")
    rec["duration"] = rec.get("duration") or d.get("duration")
    rec["ts"] = d.get("ts")
    rec["caption"] = (d.get("desc") or "")[:3000]

    bag = LinkBag()
    desc = d.get("desc") or ""
    if d.get("desc_urls"):
        desc = strip_truncated(desc)
    bag.add_text(desc + "\n" + "\n".join(d.get("desc_urls") or []), "deskripsi")
    for c in d.get("comments") or []:
        src = "komen pinned" if c["pinned"] else "komen creator" if c["creator"] else "komen"
        text = strip_truncated(c["text"]) if c["urls"] else c["text"]
        bag.add_text(text + "\n" + "\n".join(c["urls"]), src, c["author"], allow_other=src != "komen")
    rec["links"] = bag.list()
    return rec
