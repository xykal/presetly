"""Sumber "luas": nulusur topik lintas platform pakai beberapa LAPIS query.

Ide: 1 kata kunci dari user dipecah jadi beberapa query turunan (lapis) yang
menarget pola penulisan creator preset ("preset am", "alight motion preset",
"template am"). Tiap lapis dijalanin paralel, hasilnya digabung & didedup.
Ini bikin jangkauan penemuan jauh lebih luas daripada 1 query polosan —
kreator sering pakai istilah berbeda-beda untuk hal yang sama.
"""

from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..util import short_err
from . import youtube

_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="multi")

# Pola turunan dibangun langsung di lanes(): cuma ditambahin kalau query belum
# mengandung kata itu (biar gak dobel semantik).


def lanes(query: str) -> list[str]:
    """Turunin query user jadi beberapa lapis pencarian. Maks 4, ter-dedup.

    Kalau query udah ngandung kata preset/template/xml, lapis yang nambahin
    kata itu lagi dilewati (biar gak dobel: "preset x preset x").
    """
    q = re.sub(r"\s+", " ", (query or "").strip())[:80]
    if not q:
        return []
    low = f" {q.lower()} "
    out: list[str] = [q]
    if " preset " not in low and " template " not in low:
        out.append(f"{q} preset alight motion")
        out.append(f"preset am {q}")
        out.append(f"{q} template am")
    if " xml " not in low and (" preset " not in low or " template " not in low):
        out.append(f"{q} xml preset")
    seen: set[str] = set()
    uniq: list[str] = []
    for lane in out:
        k = lane.lower()
        if k not in seen:
            seen.add(k)
            uniq.append(lane)
    return uniq[:4]


def topik(query: str, limit: int = 24) -> tuple[list[dict], list[str]]:
    """Cari topik di beberapa lapis sekaligus. Return (items, notes).

    Urutan: hasil lapis PERSIS (query asli) paling atas, temuan lapis turunan
    nyusul di belakang. Frontend punya sort sendiri, jadi di sini yang penting
    dedup + luas temuan.
    """
    ls = lanes(query)
    if not ls:
        return [], []
    per_lane = max(6, min(24, limit))
    notes: list[str] = []
    futs = {_POOL.submit(youtube.search, lane, per_lane): i for i, lane in enumerate(ls)}
    per_lane_rows: list[list[dict]] = [[] for _ in ls]
    for fut in as_completed(futs):
        i = futs[fut]
        lane = ls[i]
        try:
            rows = fut.result() or []
        except Exception as e:  # noqa: BLE001 - satu lapis gagal gak boleh matiin lapis lain
            rows = []
            notes.append(f"lapis-gagal:{lane}:{short_err(e)}")
        per_lane_rows[i] = rows
        notes.append(f"lapis:{lane}:{len(rows)}")
    seen: set[str] = set()
    items: list[dict] = []
    for rows in per_lane_rows:
        for r in rows:
            key = r.get("id") or r.get("url")
            if not key or key in seen:
                continue
            seen.add(key)
            items.append(r)
    return items[:limit], notes
