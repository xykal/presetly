"""Entrypoint Vercel Function (Python runtime). Semua /api/* di-rewrite ke sini (lihat vercel.json)."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from presetly.web import app  # noqa: E402,F401
