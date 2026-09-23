"""Ekstraksi & normalisasi link dari teks (deskripsi, caption, komentar).

Tipe link:
  am    -> preset Alight Motion (alight.link / alightcreative.com/am/share)
  xml   -> file host (Drive, MediaFire, dll) - bisa xml/zip/sound/folder
  other -> link lain dari creator (linktree, telegram, ...)
"""

import re
import unicodedata
import urllib.parse

ZERO_WIDTH = re.compile(r"[\u200b-\u200f\u202a-\u202e\u2060-\u2064\ufeff]")
URL_CHARS = r"A-Za-z0-9\-._~:/?#@!$&*+,;=%"

RE_AM_SHORT = re.compile(r"(?:https?://)?(?:www\.)?alight(?:\.page)?\s?\.\s?link\s?/([A-Za-z0-9]{4,30})", re.I)
RE_AM_SHARE = re.compile(r"(?:https?://)?(?:www\.)?alightcreative\.com/am/share/u/([\w-]+)/p/([\w-]+)", re.I)
RE_URL = re.compile(r"https?://[" + URL_CHARS + r"]+", re.I)
RE_NOSCHEME_FILE = re.compile(
    r"(?<![\w/.])(?:www\.)?(?:drive\.google\.com|docs\.google\.com|mediafire\.com|sfile\.mobi|mega\.nz)/[" + URL_CHARS + r"]+",
    re.I,
)

FILE_HOSTS = (
    "drive.google.com",
    "docs.google.com",
    "mediafire.com",
    "sfile.mobi",
    "mega.nz",
    "dropbox.com",
    "files.catbox.moe",
    "catbox.moe",
    "terabox",
    "pixeldrain.com",
    "gofile.io",
    "workupload.com",
    "1drv.ms",
    "onedrive.live.com",
)
FILE_HOSTS_EXACT = tuple(h for h in FILE_HOSTS if "." in h)
IGNORE_HOSTS = (
    "youtube.com",
    "youtu.be",
    "tiktok.com",
    "instagram.com",
    "facebook.com",
    "fb.com",
    "fb.me",
    "twitter.com",
    "x.com",
    "apps.apple.com",
    "play.google.com",
    "spotify.com",
    "google.com/search",
    "ytimg.com",
    "tiktokcdn",
)

# Prioritas sumber: makin kecil makin terpercaya.
SRC_RANK = {
    "deskripsi": 0,
    "caption": 0,
    "input": 0,
    "komen pinned": 1,
    "komen creator": 2,
    "balasan creator": 2,
    "bio": 2,
    "komen": 3,
    "balasan": 3,
}
TYPE_RANK = {"am": 0, "xml": 1, "other": 2}
TRUSTED_SOURCES = {"deskripsi", "caption", "input", "komen pinned", "komen creator", "balasan creator", "bio"}


RE_TRUNCATED = re.compile(r"(?:https?://)?[\w.-]+\.[a-z]{2,}/?\S*?(?:\.\.\.|\u2026)(?=\s|$)", re.I)


def host_matches(host: str, domains) -> bool:
    host = host.lower().split(":")[0]
    return any(host == d or host.endswith("." + d) for d in domains)


def strip_truncated(text: str) -> str:
    """Buang URL yang dipotong tampilan YouTube ('https://drive.google.com/file/d/10nhG...').

    Versi lengkapnya diambil terpisah dari commandRuns, jadi potongan ini cuma bikin link palsu.
    """
    return RE_TRUNCATED.sub(" ", text or "")


def clean_text(text: str) -> str:
    """NFKC ngubah huruf 'fancy' (𝗮𝗹𝗶𝗴𝗵𝘁) jadi ASCII + buang karakter zero-width."""
    return unicodedata.normalize("NFKC", ZERO_WIDTH.sub("", text or ""))


def canon_file_url(u: str) -> str:
    """Samain format link Drive biar gak dobel (?usp=drivesdk vs ?usp=sharing, open?id=, uc?id=)."""
    m = re.search(r"drive\.google\.com/(?:file/d/|open\?id=|uc\?(?:[^#]*&)?id=)([\w-]{15,})", u)
    if m:
        return f"https://drive.google.com/file/d/{m.group(1)}/view"
    m = re.search(r"drive\.google\.com/drive/(?:u/\d+/)?folders/([\w-]{15,})", u)
    if m:
        return "https://drive.google.com/drive/folders/" + m.group(1)
    m = re.search(r"docs\.google\.com/(document|spreadsheets|presentation)/d/([\w-]{15,})", u)
    if m:
        return f"https://docs.google.com/{m.group(1)}/d/{m.group(2)}"
    return u


def file_kind(url: str, name: str | None = None) -> str:
    s = ((name or "") + " " + url).lower()
    if "/folders/" in url or "/folder/" in url:
        return "folder"
    for kind, pat in (
        ("xml", r"\.xml\b"),
        ("zip", r"\.(zip|rar|7z)\b"),
        ("sound", r"\.(mp3|wav|m4a|aac|ogg|opus|flac)\b"),
        ("video", r"\.(mp4|mov|mkv|webm)\b"),
        ("image", r"\.(png|jpe?g|webp|gif)\b"),
        ("apk", r"\.(apk|xapk)\b"),
    ):
        if re.search(pat, s):
            return kind
    return "file"


def extract_links(text: str) -> list[dict]:
    if not text:
        return []
    t = clean_text(text)
    out, seen = [], set()

    def add(typ, url):
        if url not in seen:
            seen.add(url)
            out.append({"type": typ, "url": url})

    for m in RE_AM_SHORT.finditer(t):
        add("am", "https://alight.link/" + m.group(1))
    for m in RE_AM_SHARE.finditer(t):
        add("am", f"https://alightcreative.com/am/share/u/{m.group(1)}/p/{m.group(2)}")

    urls = [m.group(0) for m in RE_URL.finditer(t)]
    urls += ["https://" + m.group(0) for m in RE_NOSCHEME_FILE.finditer(t)]
    for u in urls:
        u = u.rstrip(".,;:!?)]}>'\"*~")
        low = u.lower()
        host = urllib.parse.urlparse(u).netloc.lower()
        if "alight.link" in host or "alight.page.link" in host or "alightcreative.com/am/share" in low:
            continue
        if host_matches(host, FILE_HOSTS_EXACT) or "terabox" in host:
            add("xml", canon_file_url(u))
        elif any(h in low for h in IGNORE_HOSTS):
            continue
        elif host and "." in host:
            add("other", u)
    return out


class LinkBag:
    """Kumpulin link dari banyak sumber: dedupe, simpan sumber paling terpercaya + jumlah kemunculan."""

    def __init__(self):
        self._d: dict[str, dict] = {}

    def add_text(self, text: str, source: str, by: str | None = None, allow_other: bool = True):
        for link in extract_links(text):
            if link["type"] == "other" and not allow_other:
                continue
            cur = self._d.get(link["url"])
            if cur:
                cur["count"] += 1
                if SRC_RANK.get(source, 9) < SRC_RANK.get(cur["source"], 9):
                    cur["source"], cur["by"] = source, by
            else:
                self._d[link["url"]] = {**link, "source": source, "by": by, "count": 1}

    def add_url(self, url: str, source: str, by: str | None = None):
        self.add_text(url, source, by)

    def list(self) -> list[dict]:
        return sorted(
            self._d.values(),
            key=lambda e: (TYPE_RANK[e["type"]], SRC_RANK.get(e["source"], 9), -e["count"]),
        )

    def __bool__(self):
        return bool(self._d)
