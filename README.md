<div align="center">

<img src="web/public/favicon.svg" width="72" alt="Presetly" />

# Presetly

[![CI](https://github.com/xykal/presetly/actions/workflows/ci.yml/badge.svg)](https://github.com/xykal/presetly/actions/workflows/ci.yml) [![Deploy](https://github.com/xykal/presetly/actions/workflows/deploy.yml/badge.svg)](https://github.com/xykal/presetly/actions/workflows/deploy.yml)

**Cari link preset Alight Motion dari YouTube & TikTok tanpa scroll berjam-jam.**
Deskripsi, caption, komen pinned, sampai balasan creator dibaca otomatis. Tiap link preset dicek: nama, ukuran MB, bisa dipake AM gratis atau nggak, masih aktif atau udah mati. Videonya bisa langsung diputer & di-download.

[**Buka web**](https://presetly.xyverse.my.id) · [Laporan bug](https://github.com/xykal/presetly/issues)

<sub>Built-in XyVerse · Made in XyVerse By Kall</sub>

</div>

---

## Fitur

| | |
|---|---|
| **Cari** | YouTube (keyword / channel), TikTok (profil creator / hashtag), Instagram (profil creator), atau tempel link campur (video, shorts, `vt.tiktok.com`, reel IG, profil, playlist, `alight.link`). |
| **Baca sampai dalem** | YouTube: deskripsi + komen pinned + komen creator. TikTok: caption + komen + **balasan creator** (di TikTok link preset paling sering nongol di balasan komen, bukan di caption). Instagram: caption + link bio. |
| **Cek preset** | Nama, thumbnail, ukuran, jumlah project, status aktif/mati. Label **AM gratis bisa** (≤ 5 MB) vs **butuh premium**. Link XML (Drive/MediaFire/catbox) ikut ditampilin + nama filenya. |
| **Preview video** | TikTok & Instagram: hover / tap **Putar** buat preview inline (muted, loop), klik buat player penuh. YouTube: thumbnail kilat + player embed pas diklik. **Semua preview & download TikTok tanpa watermark** (varian wm dibuang otomatis). |
| **Download** | TikTok MP4 H.264 tanpa watermark. YouTube: cuma mode lokal (lihat [Keterbatasan](#keterbatasan)). |
| **Jelajah** | Feed preset aktif: scan berkala YouTube terbaru + hashtag teratas di server (cache 30 menit), atau hasil crawler kalau dijalanin. |
| **Koleksi** | Simpen preset favorit (disimpen di browser, gak perlu login). Export `.txt`. Notifikasi preset baru (Web Push). |
| **Bagikan** | Pencarian bisa dibagikan lewat URL (`?pf=&mode=&q=`) - penerima langsung lihat hasil yang sama. Salin semua link preset sekali klik. |
| **Buka di AM** | Di HP langsung kebuka di Alight Motion. Di PC muncul QR buat discan pakai HP. |

## Arsitektur

```
Browser (Svelte 5 SPA, Vite)
   │  /api/list   -> daftar video (1 request)
   │  /api/scan   -> scan 3 video per request, 4 paralel (progress real-time, stateless)
   │  /api/feed   -> feed.json hasil crawler (cache CDN)
   ▼
Vercel Function (Python 3.12 + Flask, region sin1)          Crawler opsional (manual / mesin sendiri)
   ├─ YouTube: yt-dlp flat (search/listing)                    ├─ Playwright scroll #hashtag TikTok
   │           + innertube /next (deskripsi + komentar)        ├─ scan + cek semua link preset
   ├─ TikTok : embed SSR, API komentar, yt-dlp listing         └─ push feed.json -> branch `data`
   ├─ Instagram: web_profile_info + oembed (tanpa login)                │
   └─ Alight : alight.link -> share page (og:title/size)                 │
                                                                raw.githubusercontent.com (CDN, gratis)
```

**Kenapa dibelah dua?** Hasil probe langsung dari Vercel (sin1), September 2026:

| Endpoint | Dari Vercel (AWS) | Dari runner GitHub |
|---|---|---|
| YouTube search/listing, `/next` (deskripsi + komen) | jalan | jalan |
| YouTube player (buat download) | **diblok** ("Sign in to confirm you're not a bot") | - |
| TikTok komentar, balasan, embed, oEmbed, listing profil | jalan | jalan |
| TikTok `/api/challenge/item_list` (hashtag) | **body kosong**, bahkan pake headless Chromium | **jalan** (58-88 video/hashtag) |

Jadi hashtag lengkap cuma bisa dari IP non-datacenter: mode lokal, atau crawler opsional yang hasilnya disajikan statis. Tanpa crawler pun web tetap jalan: `/api/feed` otomatis fallback ke scan cepat di server. Semua gratis (Vercel Hobby).

> Workflow `Crawl feed preset` sengaja **manual only** (tanpa cron). GitHub Additional Product Terms ngelarang runner hosted dipake buat aktivitas di luar production/testing/deployment project, dan crawling data berkala itu area abu-abu. Paling aman jalanin crawler di mesin sendiri lalu push `feed.json` ke branch `data`.

## Deploy sendiri (gratis)

1. Fork repo ini.
2. [vercel.com/new](https://vercel.com/new) -> import repo. Semua setting kebaca dari `vercel.json`, gak perlu env var.
3. Opsional: generate feed lengkap (`python -m presetly crawl --out feed.json` di mesin sendiri), push ke branch `data`. Tanpa ini tab Jelajah tetap keisi dari scan server.
4. Kalau repo lu beda nama, set env `PRESETLY_FEED_URL` di Vercel ke `https://raw.githubusercontent.com/<user>/<repo>/data/feed.json`.

## Jalanin lokal

Mode lokal ngebuka semua fitur (hashtag TikTok penuh + download YouTube), soalnya pakai IP rumahan.

```bash
git clone https://github.com/xykal/presetly && cd presetly
pip install -r requirements-local.txt
python -m playwright install chromium      # buat hashtag TikTok penuh
npm ci && npm run build                    # build frontend ke dist/
python -m presetly serve                   # http://localhost:8000
```

Dev frontend dengan hot reload: `python -m presetly serve` di satu terminal, `npm run dev` di terminal lain (`/api` otomatis di-proxy).

> Download YouTube butuh JS runtime (Deno / Node) + ffmpeg, sesuai kebutuhan yt-dlp 2026.

### CLI

```bash
python -m presetly yt "preset am dibawah 5mb" -n 20
python -m presetly yt-channel @namachannel
python -m presetly tt-user @dan_newbie
python -m presetly tt-tag presetalightmotion -n 40
python -m presetly link https://vt.tiktok.com/xxxx/ https://alight.link/xxxx
python -m presetly crawl --out feed.json     # generate feed lengkap (butuh Playwright)
```
Tambah `--json` buat output mentah.

### Termux (Android)

```bash
pkg install python nodejs
pip install -r requirements.txt
npm ci && npm run build && python -m presetly serve
```
Playwright gak jalan di Android, jadi hashtag pakai mode lite (sama kayak versi web).

## Struktur

```
presetly/
  links.py            ekstraksi & normalisasi link (unicode fancy, zero-width, URL kepotong, host lookalike)
  sources/youtube.py  search/channel (yt-dlp flat) + detail & komentar (innertube /next)
  sources/tiktok.py   profil, video, embed, komentar & balasan, hashtag live (Playwright)
  services/resolver.py cek alight.link -> nama/ukuran/status, nama file Drive/MediaFire
  services/scanner.py  orkestrasi list + scan batch, klasifikasi URL (anti SSRF)
  services/media.py    stream/download video
  web.py              Flask API (rate limit per IP, header keamanan)
  crawler.py          generator feed.json
api/index.py          entrypoint Vercel
web/src/              frontend Svelte 5 + TypeScript
tests/                pytest (parser, klasifikasi, API)
```

## Keterbatasan

- **Hashtag TikTok di versi web cuma "lite"**: video dari feed crawler (kalau ada) + video teratas dari embed. Hasil lengkap: jalanin lokal.
- **Download YouTube cuma di mode lokal.** YouTube minta verifikasi bot buat IP datacenter, dan bypass-nya butuh cookie akun (gak aman buat server publik).
- **Instagram: komen & hashtag gak kebaca** (butuh login). Yang dibaca: caption + link bio. Reel yang lebih tua dari 24 post terakhir creator-nya: preview jatuh ke iframe embed (link & caption tetap ketemu lewat oembed).
- **Instagram + IP cloud (Vercel dsb)**: IG agresif nge-limit IP datacenter — dari web bisa kena 429 sementara walau kodenya bener (dari laptop/HP jaringan biasa lancar). Kalau kena: tunggu 1-2 menit, atau tempel link reel langsung di tab **Tempel link**.
- Link di Linktree / web bio cuma ditampilin, gak ikut discan.
- Link dari **komen penonton** ditandain kuning, bisa aja spam. Cek dulu sebelum dipake.
- TikTok & YouTube sering ganti sistem. Kalau tiba-tiba kosong, biasanya cukup update `yt-dlp`.

## Etika

Preset itu karya creator. Tool ini cuma ngumpulin link yang **udah dishare publik** sama creatornya, gak nge-bypass apa pun. Kasih **credit (cr)** kalau make preset orang, dan follow creatornya.

Gak berafiliasi sama Alight Motion, TikTok, atau YouTube.

---

<div align="center"><sub><b>Built-in XyVerse</b> · Made in XyVerse By Kall · <a href="https://www.xyverse.my.id">xyverse.my.id</a></sub></div>
