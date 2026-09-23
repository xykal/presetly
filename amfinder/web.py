"""Flask API. Di Vercel dijalanin lewat api/index.py, lokal lewat `python -m amfinder serve`."""

import io
import os
import re
import time

from flask import Flask, Response, abort, jsonify, request, send_from_directory, stream_with_context

from . import __version__
from .config import IS_SERVERLESS, MAX_SCAN_ITEMS
from .links import extract_links
from .services import feed, media, resolver, scanner
from .sources import tiktok
from .util import SourceError, short_err

DIST = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dist")

app = Flask(__name__, static_folder=None)
app.json.ensure_ascii = False
app.json.sort_keys = False

_RATE: dict[str, list[float]] = {}


def _client_ip() -> str:
    return (request.headers.get("x-forwarded-for") or request.remote_addr or "?").split(",")[0].strip()


def _rate_limited(bucket: str, limit: int, window: int = 60) -> bool:
    """Rate limit ringan per-IP per-instance (bukan pengganti WAF, cuma rem spam)."""
    now = time.time()
    key = bucket + ":" + _client_ip()
    hits = [t for t in _RATE.get(key, []) if now - t < window]
    if len(hits) >= limit:
        _RATE[key] = hits
        return True
    hits.append(now)
    _RATE[key] = hits
    if len(_RATE) > 5000:
        _RATE.clear()
    return False


def _err(msg: str, code: int = 400):
    return jsonify(error=msg), code


@app.after_request
def _headers(resp):
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    if request.path.startswith("/api/") and "Cache-Control" not in resp.headers:
        resp.headers["Cache-Control"] = "no-store"
    return resp


@app.errorhandler(SourceError)
def _source_error(e):
    return _err(str(e), 422)


@app.get("/api/health")
def health():
    live = False
    try:
        import playwright  # noqa: F401

        live = not IS_SERVERLESS
    except ImportError:
        pass
    return jsonify(
        ok=True,
        version=__version__,
        serverless=IS_SERVERLESS,
        hashtag_live=live,
        youtube_download=not IS_SERVERLESS,
        max_scan=MAX_SCAN_ITEMS,
    )


@app.post("/api/list")
def api_list():
    if _rate_limited("list", 20):
        return _err("Kebanyakan request, tunggu semenit ya", 429)
    p = request.get_json(force=True, silent=True) or {}
    if p.get("live") and IS_SERVERLESS:
        p["live"] = False
    try:
        return jsonify(scanner.build_list(p))
    except SourceError:
        raise
    except Exception as e:
        return _err("Gagal ngambil daftar video: " + short_err(e), 502)


@app.post("/api/scan")
def api_scan():
    if _rate_limited("scan", 90):
        return _err("Kebanyakan request, tunggu semenit ya", 429)
    body = request.get_json(force=True, silent=True) or {}
    items = []
    for it in body.get("items") or []:
        if not isinstance(it, dict):
            continue
        pid, pf = str(it.get("id") or ""), it.get("platform")
        if (pf == "youtube" and re.fullmatch(r"[\w-]{11}", pid)) or (pf == "tiktok" and re.fullmatch(r"\d{15,21}", pid)):
            it["caption"] = str(it.get("caption") or "")[:5000]
            items.append(it)
    if not items:
        return _err("items kosong / gak valid")
    opts = {k: bool(body.get(k, True)) for k in ("comments", "deep", "resolve")}
    return jsonify(results=scanner.scan_many(items, opts))


@app.post("/api/check")
def api_check():
    if _rate_limited("check", 40):
        return _err("Kebanyakan request, tunggu semenit ya", 429)
    text = str((request.get_json(force=True, silent=True) or {}).get("url") or "")[:2000]
    found = [lk for lk in extract_links(text) if lk["type"] == "am"][:10]
    if not found:
        return _err("Bukan link preset Alight Motion")
    links = [{**lk, "source": "input", "by": None, "count": 1} for lk in found]
    for lk in links:
        lk["info"] = resolver.resolve_am(lk["url"], use_cache=False)
    return jsonify(links=resolver.enrich(links, resolve=False))


@app.get("/api/media/tiktok/<vid>")
def api_tt_media(vid):
    if not re.fullmatch(r"\d{15,21}", vid):
        abort(400)
    m = tiktok.media(vid)
    resp = jsonify(play=m.get("play"), proxy=f"/api/stream/tiktok/{vid}", thumb=m.get("thumb"))
    resp.headers["Cache-Control"] = "public, max-age=1800, s-maxage=3600"
    return resp


@app.get("/api/thumb/tiktok/<vid>")
def api_tt_thumb(vid):
    """Cover TikTok yang URL-nya udah expired -> redirect ke cover baru dari embed."""
    if not re.fullmatch(r"\d{15,21}", vid):
        abort(400)
    thumb = tiktok.media(vid).get("thumb")
    if not thumb:
        abort(404)
    resp = Response(status=302, headers={"Location": thumb})
    resp.headers["Cache-Control"] = "public, max-age=21600, s-maxage=21600"
    return resp


def _proxy(url: str, headers: dict, filename: str | None):
    up = media.open_upstream(url, headers, request.headers.get("Range"))
    out_headers = {
        "Content-Type": up.headers.get("Content-Type", "video/mp4"),
        "Accept-Ranges": "bytes",
        "Cache-Control": "private, max-age=3600",
    }
    for h in ("Content-Length", "Content-Range"):
        if up.headers.get(h):
            out_headers[h] = up.headers[h]
    if filename:
        out_headers["Content-Disposition"] = f'attachment; filename="{filename}"'

    def gen():
        try:
            for chunk in up.iter_content(chunk_size=256 * 1024):
                if chunk:
                    yield chunk
        finally:
            up.close()

    return Response(stream_with_context(gen()), status=up.status_code, headers=out_headers, direct_passthrough=True)


@app.get("/api/stream/tiktok/<vid>")
def api_tt_stream(vid):
    if not re.fullmatch(r"\d{15,21}", vid):
        abort(400)
    if _rate_limited("stream", 120):
        return _err("Kebanyakan request", 429)
    url, headers = media.tiktok_stream_source(vid)
    dl = request.args.get("dl")
    user = re.sub(r"[^\w.\-]", "", request.args.get("u", ""))[:40] or "tiktok"
    return _proxy(url, headers, f"{user}_{vid}.mp4" if dl else None)


@app.get("/api/stream/youtube/<vid>")
def api_yt_stream(vid):
    if not re.fullmatch(r"[\w-]{11}", vid):
        abort(400)
    if IS_SERVERLESS:
        return _err(
            "Download YouTube cuma bisa di mode lokal (YouTube nge-block IP server). Jalanin: python -m amfinder serve", 501
        )
    url, headers = media.youtube_stream_source(vid)
    return _proxy(url, headers, f"youtube_{vid}.mp4")


@app.get("/api/feed")
def api_feed():
    """Feed preset hasil crawler GitHub Actions (branch `data`). Cache 10 menit per instance + CDN."""
    resp = jsonify(feed.get_feed())
    resp.headers["Cache-Control"] = "public, max-age=120, s-maxage=300, stale-while-revalidate=600"
    return resp


@app.get("/api/qr")
def api_qr():
    import segno

    data = request.args.get("d", "")[:500]
    if not data:
        abort(400)
    buf = io.BytesIO()
    segno.make(data, error="m").save(buf, kind="svg", scale=8, border=2, dark="#07060b", light="#ffffff", xmldecl=False)
    resp = Response(buf.getvalue(), mimetype="image/svg+xml")
    resp.headers["Cache-Control"] = "public, max-age=86400, s-maxage=604800, immutable"
    return resp


@app.post("/api/export.csv")
def api_export_csv():
    import csv

    rows = (request.get_json(force=True, silent=True) or {}).get("results") or []

    def cell(v):
        # Cegah CSV/formula injection pas dibuka di Excel/Sheets.
        v = "" if v is None else str(v)
        return "'" + v if v[:1] in ("=", "+", "-", "@", "\t", "\r") else v

    buf = io.StringIO()
    buf.write("\ufeff")
    w = csv.writer(buf)
    w.writerow(
        [
            "platform",
            "video_url",
            "judul",
            "author",
            "views",
            "jenis",
            "link",
            "nama_preset",
            "ukuran",
            "ukuran_mb",
            "status",
            "sumber",
        ]
    )
    for r in rows[:500]:
        for lk in r.get("links") or []:
            if lk.get("type") == "other":
                continue
            i = lk.get("info") or {}
            w.writerow(
                [
                    cell(x)
                    for x in (
                        r.get("platform"),
                        r.get("url"),
                        (r.get("title") or "")[:200],
                        r.get("author"),
                        r.get("views"),
                        "preset" if lk.get("type") == "am" else lk.get("kind") or "file",
                        i.get("fixed_url") or lk.get("url"),
                        i.get("name"),
                        i.get("size_text"),
                        i.get("size_mb"),
                        i.get("status"),
                        lk.get("source"),
                    )
                ]
            )
    return Response(
        buf.getvalue(),
        content_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="preset-am-{}.csv"'.format(time.strftime("%Y%m%d-%H%M"))},
    )


# --- Mode lokal: sajikan hasil build frontend (dist/) ---------------------------------
@app.get("/")
@app.get("/<path:path>")
def spa(path: str = ""):
    if path.startswith("api/"):
        abort(404)
    if not os.path.isdir(DIST):
        return Response("Frontend belum di-build. Jalanin: npm install && npm run build", status=503, mimetype="text/plain")
    full = os.path.join(DIST, path)
    if path and os.path.isfile(full):
        return send_from_directory(DIST, path)
    return send_from_directory(DIST, "index.html")
