"""Wrapper yt-dlp: logger senyap + deteksi JS runtime (buat challenge YouTube di mode lokal)."""

import shutil

import yt_dlp


class _QuietLogger:
    def debug(self, msg):
        pass

    def info(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        pass


def ydl(**extra) -> yt_dlp.YoutubeDL:
    opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "logger": _QuietLogger(),
        "socket_timeout": 15,
        "retries": 1,
        "extractor_retries": 1,
    }
    runtimes = {rt: {} for rt in ("deno", "node", "bun") if shutil.which(rt)}
    if runtimes:
        opts["js_runtimes"] = runtimes
    opts.update(extra)
    return yt_dlp.YoutubeDL(opts)


def flatten(info) -> list[dict]:
    if not info:
        return []
    if info.get("_type") in ("playlist", "multi_video"):
        out = []
        for e in info.get("entries") or []:
            if not e:
                continue
            out += flatten(e) if e.get("_type") == "playlist" else [e]
        return out
    return [info]
