"""Cek link preset AM & file XML: nama, ukuran, thumbnail, status aktif/mati.

alight.link/XXX -> 302 alight.page.link/XXX -> 302 alightcreative.com/am/share/u/../p/..
Halaman share punya og:title (nama), og:description ("contains N project, total 12.1 MB"), og:image.
"""

import html
import re
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

import requests

from ..config import CACHE_TTL_DEAD, CACHE_TTL_OK, FREE_LIMIT_MB, HTTP_TIMEOUT, MAX_RESOLVE_PER_ITEM
from ..http import TTLCache, session
from ..links import file_kind, host_matches

_CACHE = TTLCache()
_SIZE_UNITS = {"B": 1 / 1048576, "BYTES": 1 / 1048576, "KB": 1 / 1024, "MB": 1.0, "GB": 1024.0}
_POOL = ThreadPoolExecutor(max_workers=12, thread_name_prefix="resolve")


def _meta(txt: str, prop: str) -> str | None:
    m = re.search(rf'<meta\s+property="{re.escape(prop)}"\s+content="([^"]*)"', txt)
    return html.unescape(m.group(1)).strip() if m else None


def parse_share_page(txt: str) -> dict:
    info = {
        "name": _meta(txt, "og:title"),
        "thumb": _meta(txt, "og:image"),
        "projects": None,
        "project_names": [],
        "size_mb": None,
        "size_text": None,
        "am_version": None,
    }
    desc = _meta(txt, "og:description") or ""
    m = re.search(r"contains\s+(\d+)\s+project", desc, re.I)
    if m:
        info["projects"] = int(m.group(1))
    m = re.search(r"total\s+([\d.,]+)\s*(bytes|B|KB|MB|GB)\b", desc, re.I)
    if m:
        num = float(m.group(1).replace(",", ""))
        info["size_mb"] = round(num * _SIZE_UNITS[m.group(2).upper()], 3)
        info["size_text"] = f"{m.group(1)} {m.group(2).upper()}"
    m = re.search(r'<ul id="project-list">(.*?)</ul>', txt, re.S)
    if m:
        info["project_names"] = [
            html.unescape(re.sub(r"<[^>]+>", "", x)).strip() for x in re.findall(r"<li>(.*?)</li>", m.group(1), re.S)
        ][:20]
    m = re.search(r"amVersionString=([\d.]+)", txt)
    if m:
        info["am_version"] = m.group(1)
    if info["size_mb"] is not None:
        info["free_ok"] = info["size_mb"] <= FREE_LIMIT_MB
    return info


_ALIGHT_HOSTS = ("alight.link", "alight.page.link", "alightcreative.com")


def _allowed(url: str) -> bool:
    pu = urllib.parse.urlparse(url)
    return pu.scheme == "https" and host_matches(pu.hostname or "", _ALIGHT_HOSTS)


def _follow_to_share(url: str) -> tuple[str | None, bool]:
    """Return (share_url, dead). Ikutin redirect manual (cuma di host Alight) biar bisa nangkep intent:// Android."""
    s = session()
    cur = url
    for _ in range(6):
        if not _allowed(cur):
            return None, False
        if urllib.parse.urlparse(cur).path.startswith("/am/share/") and host_matches(
            urllib.parse.urlparse(cur).hostname or "", ("alightcreative.com",)
        ):
            return cur.split("?")[0].split("#")[0], False
        r = s.get(cur, allow_redirects=False, timeout=HTTP_TIMEOUT)
        if r.status_code in (301, 302, 303, 307, 308):
            loc = r.headers.get("location", "")
            if loc.startswith("intent:"):
                m = re.search(r"url%3D(https?[^;&]+)", loc) or re.search(r"url=(https?[^;&]+)", loc)
                loc = urllib.parse.unquote(m.group(1)) if m else ""
            if not loc:
                return None, False
            cur = urllib.parse.urljoin(cur, loc)
            continue
        return None, r.status_code in (404, 410)
    return None, False


def resolve_am(url: str, use_cache: bool = True) -> dict:
    if use_cache:
        hit = _CACHE.get(url)
        if hit:
            return hit
    res: dict = {"status": "error", "checked": int(time.time()), "share_url": None}
    try:
        share, dead = _follow_to_share(url)
        if dead:
            res["status"] = "dead"
        if share:
            r = session().get(share, timeout=HTTP_TIMEOUT)
            if r.status_code in (404, 410):
                res["status"] = "dead"
            elif r.ok and "og:title" in r.text:
                res.update(parse_share_page(r.text))
                res["status"] = "ok"
                res["share_url"] = share
    except requests.RequestException as e:
        res["error"] = str(e)[:160]

    # Kode nempel sama teks (alight.link/AbC...xyzPRESET): coba potong ke 17 / 16 karakter.
    m = re.match(r"https://alight\.link/([A-Za-z0-9]+)$", url)
    if res["status"] == "dead" and m and len(m.group(1)) > 17:
        for n in (17, 16):
            alt = resolve_am("https://alight.link/" + m.group(1)[:n], use_cache)
            if alt.get("status") == "ok":
                res = dict(alt, fixed_url="https://alight.link/" + m.group(1)[:n])
                break

    if res["status"] == "ok":
        _CACHE.set(url, res, CACHE_TTL_OK)
    elif res["status"] == "dead":
        _CACHE.set(url, res, CACHE_TTL_DEAD)
    return res


def resolve_file(url: str) -> dict | None:
    if not host_matches(urllib.parse.urlparse(url).netloc, ("drive.google.com", "docs.google.com", "mediafire.com")):
        return None
    hit = _CACHE.get(url)
    if hit:
        return hit
    res: dict = {"status": "error", "checked": int(time.time()), "name": None}
    try:
        r = session().get(url, timeout=HTTP_TIMEOUT, allow_redirects=True, stream=True)
        body = r.raw.read(400_000, decode_content=True).decode("utf-8", "ignore")
        r.close()
        if "accounts.google.com" in r.url or "ServiceLogin" in r.url:
            res["status"] = "private"
        elif r.status_code in (404, 410):
            res["status"] = "dead"
        elif r.ok:
            name = _meta(body, "og:title")
            if not name:
                m = re.search(r"<title>(.*?)</title>", body, re.S)
                name = html.unescape(m.group(1)).strip() if m else None
            if name:
                name = re.sub(r"\s*-\s*(Google Drive|MediaFire|Google Docs)\s*$", "", name)
                if name.lower().startswith("google drive: sign-in"):
                    res["status"], name = "private", None
            res["name"] = name
            if res["status"] == "error":
                res["status"] = "ok"
    except requests.RequestException as e:
        res["error"] = str(e)[:160]
    if res["status"] != "error":
        _CACHE.set(url, res, CACHE_TTL_OK)
    return res


def enrich(links: list[dict], resolve: bool = True) -> list[dict]:
    """Tempel info ke tiap link (paralel), lalu gabung alight.link + share URL yang ternyata preset sama."""
    if resolve:
        am = [lk for lk in links if lk["type"] == "am"][:MAX_RESOLVE_PER_ITEM]
        files = [lk for lk in links if lk["type"] == "xml"][:6]
        futs = [(lk, _POOL.submit(resolve_am, lk["url"])) for lk in am]
        futs += [(lk, _POOL.submit(resolve_file, lk["url"])) for lk in files]
        for lk, f in futs:
            try:
                info = f.result(timeout=HTTP_TIMEOUT * 2.5)
            except Exception:
                info = {"status": "error"}
            if info:
                lk["info"] = info
    for lk in links:
        if lk["type"] == "xml":
            lk["kind"] = file_kind(lk["url"], (lk.get("info") or {}).get("name"))

    by_share: dict[str, dict] = {}
    out = []
    for lk in links:
        share = (lk.get("info") or {}).get("share_url") if lk["type"] == "am" else None
        if share and share in by_share:
            keep = by_share[share]
            keep["count"] += lk["count"]
            if keep["url"].startswith("https://alightcreative.com") and lk["url"].startswith("https://alight.link"):
                keep["url"] = lk["url"]
            continue
        if share:
            by_share[share] = lk
        out.append(lk)
    return out


def summarize(rec: dict) -> dict:
    links = rec.get("links") or []
    am = [lk for lk in links if lk["type"] == "am"]
    ok = [lk for lk in am if (lk.get("info") or {}).get("status") == "ok"]
    sizes = [lk["info"]["size_mb"] for lk in ok if lk["info"].get("size_mb") is not None]
    rec["n_am"], rec["n_ok"] = len(am), len(ok)
    rec["n_xml"] = sum(1 for lk in links if lk["type"] == "xml")
    rec["min_size"] = min(sizes) if sizes else None
    return rec
