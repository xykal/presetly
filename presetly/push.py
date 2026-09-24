"""Notifikasi preset baru via Web Push standar (VAPID) + Cloudflare D1 sebagai penyimpanan.

- `subs`  : langganan push (endpoint, keys, daftar creator yang dipantau).
- `seen`  : id video yang udah dikabari (biar gak dobel) + penanda internal (`_k:*`).

Dipanggil dari:
- POST /api/push/run (header X-Presetly-Secret) -- bisa dipanggil cron/Vercel cron kapan pun.
- Otomatis pas /api/feed bangun live feed (throttle 30 menit global lewat seen `_k:lastrun`).

Enggak ada secret di repo: token D1 + kunci VAPID dibaca dari env (lihat .env.example).
"""

import json
import os
import time

import requests

from .config import HTTP_TIMEOUT
from .util import short_err

D1_TOKEN = os.environ.get("PRESETLY_D1_TOKEN", "")
D1_ACCOUNT = os.environ.get("PRESETLY_D1_ACCOUNT", "a678fee6e0a026ccd2fd978cdf07806a")
D1_DB = os.environ.get("PRESETLY_D1_DB", "8a43bb2d-1254-471f-b99f-55a8eee33be9")
VAPID_PRIV = os.environ.get("PRESETLY_VAPID_PRIV", "")
VAPID_PUB = os.environ.get("PRESETLY_VAPID_PUB", "")
VAPID_SUB = os.environ.get("PRESETLY_VAPID_SUB", "mailto:xycdigital@gmail.com")
PUSH_SECRET = os.environ.get("PRESETLY_PUSH_SECRET", "")
THROTTLE = 30 * 60
MAX_CREATORS_PER_RUN = 10
MAX_VIDEOS_PER_CREATOR = 3


def enabled() -> bool:
    return bool(D1_TOKEN and VAPID_PRIV and VAPID_PUB)


def d1(sql: str, params: list | None = None) -> list[dict]:
    """Jalanin SQL di D1 lewat REST. Return list hasil per statement."""
    if not D1_TOKEN:
        raise RuntimeError("PRESETLY_D1_TOKEN belum diset")
    r = requests.post(
        f"https://api.cloudflare.com/client/v4/accounts/{D1_ACCOUNT}/d1/database/{D1_DB}/query",
        headers={"Authorization": "Bearer " + D1_TOKEN, "Content-Type": "application/json"},
        json={"sql": sql, "params": params or []},
        timeout=HTTP_TIMEOUT,
    )
    j = r.json()
    if not j.get("success"):
        raise RuntimeError("D1 error: " + short_err(RuntimeError(str(j.get("errors")[:1]))))
    return j.get("result") or []


def d1_rows(sql: str, params: list | None = None) -> list[dict]:
    out = []
    for stmt in d1(sql, params):
        out += stmt.get("results") or []
    return out


# ---------------------------------------------------------------- langganan
def subscribe(endpoint: str, p256dh: str, auth: str, creators: list[str]) -> None:
    d1(
        "INSERT INTO subs (endpoint, p256dh, auth, creators, created_at) VALUES (?,?,?,?,?) "
        "ON CONFLICT(endpoint) DO UPDATE SET p256dh=excluded.p256dh, auth=excluded.auth, creators=excluded.creators",
        [endpoint, p256dh, auth, json.dumps(_norm_creators(creators)), int(time.time())],
    )


def unsubscribe(endpoint: str) -> None:
    d1("DELETE FROM subs WHERE endpoint = ?", [endpoint])


def _norm_creators(creators: list[str]) -> list[str]:
    """Beresin format creator: 'youtube:@user' | 'tiktok:user' | 'instagram:user'."""
    out = []
    for c in creators or []:
        c = str(c).strip().lower().lstrip("@")
        if ":" in c:
            pf, handle = c.split(":", 1)
        else:
            pf, handle = "tiktok", c
        pf = {"yt": "youtube", "ig": "instagram", "tt": "tiktok"}.get(pf, pf)
        handle = handle.strip()
        if (
            pf in ("youtube", "tiktok", "instagram")
            and handle
            and (pf, handle) not in [(p, h) for p, h in (x.split(":", 1) for x in out)]
        ):
            out.append(f"{pf}:{handle}")
    return out[:20]


# ---------------------------------------------------------------- kirim push
def _send(sub: dict, payload: dict) -> bool:
    from pywebpush import WebPushException, webpush

    try:
        webpush(
            subscription_info={
                "endpoint": sub["endpoint"],
                "keys": {"p256dh": sub["p256dh"], "auth": sub["auth"]},
            },
            data=json.dumps(payload),
            vapid_private_key=VAPID_PRIV,
            vapid_claims={"sub": VAPID_SUB},
            ttl=3600,
        )
        return True
    except WebPushException as e:
        if e.response is not None and e.response.status_code in (404, 410):
            unsubscribe(sub["endpoint"])  # langganan mati -> buang
        return False


# ---------------------------------------------------------------- cek & kabari
def _latest(ckey: str, limit: int) -> list[dict]:
    pf, handle = ckey.split(":", 1)
    try:
        if pf == "youtube":
            from .sources import youtube

            return youtube.channel("@" + handle if not handle.startswith("@") else handle, limit)
        if pf == "tiktok":
            from .sources import tiktok

            return tiktok.profile(handle, limit)[1]
        if pf == "instagram":
            from .sources import instagram

            return instagram.profile(handle, limit)[1]
    except Exception:  # noqa: S110 - satu creator gagal jangan matiin sisanya
        return []
    return []


def _cursor() -> int:
    rows = d1_rows("SELECT v FROM seen WHERE k = '_k:cursor'")
    return int(rows[0]["v"]) if rows else 0


def check_and_notify(force: bool = False, quiet_first: bool = True) -> dict:
    """Cek postingan baru dari creator yang dipantau -> push ke subscriber-nya.

    quiet_first: video yang pertama kali ketemu TETAP ditandai seen tanpa push kalau
    umurnya > 48 jam (biar pas langganan baru gak banjir notifikasi lama).
    """
    if not enabled():
        return {"ok": False, "reason": "push belum dikonfigurasi di server"}
    now = int(time.time())
    if not force:
        rows = d1_rows("SELECT v FROM seen WHERE k = '_k:lastrun'")
        if rows and now - int(rows[0]["v"]) < THROTTLE:
            return {"ok": True, "skipped": "throttled"}
    d1("INSERT INTO seen (k, v) VALUES ('_k:lastrun', ?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", [now])

    subs = d1_rows("SELECT endpoint, p256dh, auth, creators FROM subs")
    if not subs:
        return {"ok": True, "subs": 0, "sent": 0}
    for s in subs:
        s["creators"] = json.loads(s.get("creators") or "[]")

    all_c: list[str] = []
    for s in subs:
        for c in s["creators"]:
            if c not in all_c:
                all_c.append(c)
    if not all_c:
        return {"ok": True, "subs": len(subs), "sent": 0}

    # giliran cek: round-robin biar creator banyak gak kelindes.
    cur = _cursor()
    n = min(MAX_CREATORS_PER_RUN, len(all_c))
    picks = [all_c[(cur + i) % len(all_c)] for i in range(n)]
    d1("INSERT INTO seen (k, v) VALUES ('_k:cursor', ?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", [(cur + n) % len(all_c)])

    sent, new = 0, 0
    for ckey in picks:
        for rec in _latest(ckey, MAX_VIDEOS_PER_CREATOR):
            vid = "v:" + rec.get("platform", "?") + ":" + rec.get("id", "")
            if not rec.get("id"):
                continue
            if d1_rows("SELECT k FROM seen WHERE k = ?", [vid]):
                continue
            d1("INSERT INTO seen (k, v) VALUES (?, ?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", [vid, now])
            new += 1
            ts = int(rec.get("ts") or 0)
            if quiet_first and ts and now - ts > 48 * 3600:
                continue  # konten lama: tandai seen aja
            title = (rec.get("title") or "postingan baru")[:80]
            handle = ckey.split(":", 1)[1]
            payload = {
                "title": f"Postingan baru dari @{handle}",
                "body": title,
                "url": rec.get("url") or "/",
            }
            for s in subs:
                if ckey in s["creators"] or "*" in s["creators"]:
                    if _send(s, payload):
                        sent += 1
    return {"ok": True, "subs": len(subs), "creators": len(all_c), "checked": picks, "new": new, "sent": sent}
