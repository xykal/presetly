"""HTTP session per-thread + TTL cache thread-safe."""

import threading
import time
from collections import OrderedDict

import requests

from .config import CACHE_MAX_ENTRIES, UA

_tls = threading.local()


def session() -> requests.Session:
    s = getattr(_tls, "s", None)
    if s is None:
        s = requests.Session()
        s.headers.update({"User-Agent": UA, "Accept-Language": "id-ID,id;q=0.9,en;q=0.8"})
        adapter = requests.adapters.HTTPAdapter(pool_connections=8, pool_maxsize=16, max_retries=1)
        s.mount("https://", adapter)
        s.mount("http://", adapter)
        _tls.s = s
    return s


class TTLCache:
    """LRU + TTL. Dipake buat hasil cek link supaya gak nembak URL yang sama berulang."""

    def __init__(self, max_entries: int = CACHE_MAX_ENTRIES):
        self._d: OrderedDict[str, tuple[float, object]] = OrderedDict()
        self._lock = threading.Lock()
        self._max = max_entries

    def get(self, key: str):
        with self._lock:
            hit = self._d.get(key)
            if not hit:
                return None
            exp, val = hit
            if exp < time.time():
                del self._d[key]
                return None
            self._d.move_to_end(key)
            return val

    def set(self, key: str, val, ttl: float):
        with self._lock:
            self._d[key] = (time.time() + ttl, val)
            self._d.move_to_end(key)
            while len(self._d) > self._max:
                self._d.popitem(last=False)
