"""Konstanta & konfigurasi runtime. Semua bisa di-override lewat env var."""

import os

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"

# Preset > 5MB biasanya cuma bisa di-import akun AM premium.
FREE_LIMIT_MB = 5.0

HTTP_TIMEOUT = float(os.environ.get("PRESETLY_HTTP_TIMEOUT", "15"))

# Batas per request biar function serverless gak kelamaan.
MAX_SCAN_ITEMS = int(os.environ.get("PRESETLY_MAX_SCAN_ITEMS", "12"))
MAX_LIST_ITEMS = int(os.environ.get("PRESETLY_MAX_LIST_ITEMS", "60"))
MAX_RESOLVE_PER_ITEM = 12

# Cache in-memory (hidup selama instance serverless masih warm).
CACHE_TTL_OK = 3 * 86400
CACHE_TTL_DEAD = 12 * 3600
CACHE_MAX_ENTRIES = 5000


# Opsional: URL feed.json hasil crawler GitHub Actions.
FEED_URL = os.environ.get(
    "PRESETLY_FEED_URL",
    "https://raw.githubusercontent.com/xykal/presetly/data/feed.json",
)

IS_SERVERLESS = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
