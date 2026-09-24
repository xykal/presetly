"""Preview & download video.

Preview:
  - TikTok -> URL mp4 dari embed (jalan tanpa cookie/referer), diputer <video> native.
  - YouTube -> iframe embed resmi di frontend (gak lewat server).
Download (stream lewat server, gak nyimpen file):
  - TikTok -> mp4 H.264 tanpa watermark dari embed, fallback format yt-dlp non-watermark.
  - YouTube -> cuma jalan mode lokal/self-host (IP datacenter kena bot-check YouTube).
"""

import re

import requests

from ..config import HTTP_TIMEOUT, UA
from ..sources import instagram, tiktok
from ..sources.ytdlp_util import ydl
from ..util import SourceError

ALLOWED_MEDIA_HOST = re.compile(
    r"^https://[\w.-]+\.(tiktokcdn(-us|-eu)?\.com|tiktok\.com|tiktokv\.(com|us|eu)|ibyteimg\.com|byteoversea\.com|muscdn\.com|cdninstagram\.com|fbcdn\.net)/"
)


def tiktok_stream_source(vid: str) -> tuple[str, dict]:
    """Return (url, headers) buat stream mp4 TikTok."""
    play = tiktok.media(vid).get("play")
    if play and ALLOWED_MEDIA_HOST.match(play):
        return play, {"User-Agent": UA}
    with ydl(format="b[format_id!=download][vcodec^=h264]/b[vcodec^=h264]/b") as y:
        info = y.extract_info(tiktok.video_url(None, vid), download=False)
        url = info.get("url")
        headers = dict(info.get("http_headers") or {})
        cookie = y.cookiejar.get_cookie_header(url) if url else None
        if cookie:
            headers["Cookie"] = cookie
    if not url or not ALLOWED_MEDIA_HOST.match(url):
        raise SourceError("Video TikTok gak bisa diambil")
    return url, headers


def youtube_stream_source(vid: str) -> tuple[str, dict]:
    with ydl(format="18/b[ext=mp4][acodec!=none][vcodec!=none]/b") as y:
        info = y.extract_info("https://www.youtube.com/watch?v=" + vid, download=False)
    url = info.get("url")
    if not url:
        raise SourceError("Format mp4 gabungan gak tersedia")
    return url, dict(info.get("http_headers") or {})


def instagram_stream_source(code: str) -> tuple[str, dict]:
    """Return (url, headers) buat stream mp4 Instagram (scontent CDN)."""
    play = instagram.media(code).get("play")
    if play and ALLOWED_MEDIA_HOST.match(play):
        return play, {"User-Agent": UA, "Referer": "https://www.instagram.com/"}
    raise SourceError("Video Instagram gak bisa diambil (mungkin kehapus / private / kelewat baru)")


def open_upstream(url: str, headers: dict, range_header: str | None = None) -> requests.Response:
    h = dict(headers)
    if range_header:
        h["Range"] = range_header
    r = requests.get(url, headers=h, stream=True, timeout=HTTP_TIMEOUT)
    if r.status_code >= 400:
        r.close()
        raise SourceError(f"Server video nolak (HTTP {r.status_code})")
    return r
