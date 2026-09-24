"""CLI: python -m presetly <perintah>

serve                              jalanin web lokal (http://localhost:8000)
yt "preset am 5mb" [-n 20]         cari di YouTube
yt-channel @channel                scan 1 channel
tt-user @username                  scan profil TikTok
tt-tag presetalightmotion          hashtag TikTok (live, butuh Playwright)
link <url...>                      tempel link apa aja
crawl [--out feed.json]            crawler feed (dipake GitHub Actions)
"""

import argparse
import json
import os
import sys


def _print(results: list[dict]):
    rows = sorted([r for r in results if r.get("n_am") or r.get("n_xml")], key=lambda r: -(r.get("views") or 0))
    print(f"\n{len(rows)} video ada link preset/XML (dari {len(results)} discan)\n")
    for r in rows:
        print("[{}] {}".format(r["platform"], (r.get("title") or "")[:90]))
        print("  {} | {} | {} views".format(r.get("url"), r.get("author") or "-", r.get("views") or "-"))
        for lk in r["links"]:
            if lk["type"] == "other":
                continue
            i = lk.get("info") or {}
            if lk["type"] == "am":
                print(
                    "   PRESET {:<6} {} | {} | {} [{}]".format(
                        i.get("status", "?"),
                        i.get("fixed_url") or lk["url"],
                        i.get("name") or "-",
                        i.get("size_text") or "",
                        lk["source"],
                    )
                )
            else:
                print("   FILE   {} {} [{}]".format(lk["url"], ("- " + i["name"]) if i.get("name") else "", lk["source"]))
        print()


def main(argv=None):
    ap = argparse.ArgumentParser(prog="presetly", description="Presetly - Built-in XyVerse")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("serve")
    s.add_argument("--port", type=int, default=int(os.environ.get("PORT", 8000)))
    s.add_argument("--host", default="0.0.0.0")  # noqa: S104 - server lokal emang buat diakses dari HP di jaringan yang sama
    for name in ("yt", "yt-channel", "tt-user", "tt-tag", "link"):
        sp = sub.add_parser(name)
        sp.add_argument("query", nargs="+")
        sp.add_argument("-n", "--limit", type=int, default=20)
        sp.add_argument("--new", action="store_true")
        sp.add_argument("--no-comments", action="store_true")
        sp.add_argument("--json", action="store_true", help="output JSON mentah")
    c = sub.add_parser("crawl")
    c.add_argument("--out", default="feed.json")
    c.add_argument("--tags", default="presetalightmotion,presetam,presetdibawah5mb,presetxml,alightmotionpreset,presetjedagjedug")
    c.add_argument("--per-tag", type=int, default=30)
    a = ap.parse_args(argv)

    if a.cmd == "serve":
        from .web import app

        print(f"Presetly jalan di http://localhost:{a.port}")
        app.run(host=a.host, port=a.port, threaded=True)
        return
    if a.cmd == "crawl":
        from .crawler import crawl

        crawl(a.out, [t.strip() for t in a.tags.split(",") if t.strip()], a.per_tag)
        return

    from .services import scanner
    from .sources import tiktok

    platform, mode = {
        "yt": ("youtube", "search"),
        "yt-channel": ("youtube", "channel"),
        "tt-user": ("tiktok", "profile"),
        "tt-tag": ("tiktok", "hashtag"),
        "link": ("link", "auto"),
    }[a.cmd]
    query = "\n".join(a.query) if a.cmd == "link" else " ".join(a.query)
    if a.cmd == "tt-tag":
        items = tiktok.hashtag_live([query], a.limit, on_progress=lambda t, n: print(f"  #{t}: {n} video", file=sys.stderr))
        items = next(iter(items.values()), [])
        listing = {"items": items, "profile": None, "preset_check": None}
    else:
        listing = scanner.build_list(
            {"platform": platform, "mode": mode, "query": query, "limit": a.limit, "sort": "new" if a.new else "relevance"}
        )
    print(f"{len(listing['items'])} video, scanning...", file=sys.stderr)
    opts = {"comments": not a.no_comments, "deep": True, "resolve": True}
    results = []
    for i in range(0, len(listing["items"]), 6):
        results += scanner.scan_many(listing["items"][i : i + 6], opts)
        print(f"  {len(results)}/{len(listing['items'])}", file=sys.stderr)
    if listing.get("preset_check"):
        results.insert(
            0,
            {
                "platform": "link",
                "id": "input",
                "url": None,
                "title": "Link yang ditempel",
                "links": listing["preset_check"],
                "n_am": 1,
                "n_xml": 0,
            },
        )
    if a.json:
        json.dump(results, sys.stdout, ensure_ascii=False, indent=1)
    else:
        _print(results)


if __name__ == "__main__":
    main()
