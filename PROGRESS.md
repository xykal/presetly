# PROGRESS LOG - AM Preset Finder

> Format sesuai XYVERSE_GLOBAL_RULES.md #4. Append terus, jangan hapus history.

---

### 2026-09-23 - v2.0.0: rewrite total, hosting Vercel + crawler GitHub Actions
**Status:** Done
**Dikerjain oleh:** AI Agent + xykalnotkel

**Latar:**
v1 (prototype lokal: Flask + satu file HTML vanilla + Playwright) jalan tapi gak bisa di-host: nyimpen job state di memori,
butuh headless Chromium buat hashtag, dan UI-nya masih kasar. Kall minta UI/UX dirapihin, repo di GitHub sesuai aturan XyVerse,
preview video bisa diputer, hosting gratis (Vercel / Cloudflare).

**Riset & probe (hasil nyata, bukan asumsi):**
- Deploy probe ke Vercel sin1 (`xyv-diag-probe*`, udah dihapus). Hasil dari IP AWS:
  - YouTube search/listing (yt-dlp flat) jalan. YouTube *player* diblok ("Sign in to confirm you're not a bot") di semua
    player_client (tv, web_safari, mweb, web_embedded, android_vr) -> detail video dipindah ke innertube `/next`
    (deskripsi + komentar, jalan tanpa bot-check). Download YouTube = lokal only.
  - TikTok: API komentar + balasan, `/embed/@user`, `/embed/tag/x`, `/embed/v2/:id`, oEmbed, yt-dlp listing profil jalan.
    `/api/challenge/item_list` (hashtag) balik body kosong, bahkan pake @sparticuz/chromium + puppeteer + stealth
    (webdriver disembunyiin). SSR profil/hashtag 403 buat UA crawler.
  - Stream respons > 4.5 MB dari Python function Vercel jalan (tes 12 MB, 1 detik) -> proxy video aman.
- Probe runner GitHub Actions (branch `probe`, udah dihapus): hashtag lewat Playwright jalan (58 & 88 video).
- Cloudflare Worker (probe `xyv-probe-tmp`, udah dihapus): akses TikTok jalan, tapi yt-dlp (Python) gak bisa di Workers ->
  gak dipake biar stack gak kepecah.
- URL mp4 dari embed TikTok bisa diputer tanpa cookie/referer dari IP mana pun (HTTP 206) -> dipake buat preview `<video>` native.
- Offset `commandRuns` di deskripsi YouTube = UTF-16 code unit (terbukti di video dengan 25 karakter astral). Link diambil
  langsung dari `urlEndpoint` (unwrap `youtube.com/redirect?q=`), jadi aman dari masalah offset.

**Arsitektur akhir:**
- Frontend Svelte 5 + TS + Vite (SPA, 36 KB gzip) -> `dist/` disajikan CDN Vercel.
- Backend Flask satu function `api/index.py` (region sin1, maxDuration 90). Stateless: `/api/list` sekali,
  lalu `/api/scan` per 3 video x 4 paralel dari browser -> progress real-time, gak ada state job di server.
- Crawler `python -m amfinder crawl` di GitHub Actions tiap 6 jam -> `feed.json` di branch `data`
  (orphan, force-push, ada vercel.json `deploymentEnabled:false`) -> dibaca lewat raw.githubusercontent.

**File yang diubah/dibikin:**
- `amfinder/links.py` -> ekstraksi link: NFKC (huruf fancy), buang zero-width, URL char ASCII only (teks Myanmar/Thai
  gak nempel), canonical Drive, `host_matches` (tolak `drive.google.com.evil.com`), `strip_truncated` (buang URL YouTube kepotong "...").
- `amfinder/sources/youtube.py` -> search/channel/playlist + parser `/next` & komentar (pinned via `pinnedText`, creator via `isCreator`),
  fallback yt-dlp penuh buat mode lokal. `channel_base` validasi host.
- `amfinder/sources/tiktok.py` -> embed Frontity parser, profil (yt-dlp + embed buat URL play), video (yt-dlp -> embed -> oEmbed),
  komentar + balasan (buka thread yang nanya preset / dari creator), hashtag live (Playwright, lokal/crawler).
- `amfinder/services/resolver.py` -> cek alight.link (redirect manual cuma di host Alight, anti SSRF), parse ukuran KB/MB/GB,
  potong kode yang nempel teks (17/16 char), nama file Drive/MediaFire, TTL cache, resolve paralel.
- `amfinder/services/scanner.py` -> `classify` pakai hostname hasil parse (bukan substring) -> nutup SSRF lewat
  yt-dlp generic extractor. Playlist dibangun ulang dari `list=` id doang.
- `amfinder/services/media.py` + `web.py` -> stream TikTok (allowlist host CDN), CSV anti formula-injection, rate limit per IP,
  header keamanan, cache CDN (`s-maxage`) buat feed/QR/thumb.
- `amfinder/crawler.py` -> merge feed lama (preset < 21 hari tetap disimpen), dedupe by share_url.
- `web/src/**` -> UI baru: tab Cari/Jelajah/Koleksi, dock bawah di HP, preview inline TikTok (hover/tap), player modal
  (video native + fallback iframe player TikTok), QR modal (otomatis di PC), skeleton, empty state, filter & sort,
  section **JUGA DARI XYVERSE** + **Built-in XyVerse** di footer & header.
- `tests/` -> 43 test (parser, klasifikasi URL + SSRF, API validasi, CSV injection, rate limit).
- `.github/workflows/ci.yml` (ruff + pytest + svelte-check + build), `crawl.yml` (cron 6 jam).
- `vercel.json`, `.vercelignore`, `pyproject.toml`, `README.md`, `LICENSE` (MIT).

**Kendala & Solusi:**
- TikTok hashtag diblok dari IP cloud -> crawler di Actions + mode "hashtag lite" (feed + embed teratas) di web.
- YouTube player diblok dari IP cloud -> detail via `/next`; download YouTube dijelasin jujur sebagai fitur lokal.
- Logo resmi XyVerse di filebin (`xyverse-logo-pack-9f3k2`) **udah expired** (bin kosong, dicek 2026-09-23) ->
  pakai logo pixel dari `xykalnotkel/xykalnotkel/assets/xyverse-icon.svg` (di-inline jadi komponen `XyverseMark.svelte`).
  Kalau logo pack baru udah diupload ulang, ganti di komponen itu.
- Token di `uploads/kuncikerjasama.txt` dipake cuma buat bikin repo, push, dan deploy. Gak ada secret yang masuk repo;
  app ini emang gak butuh secret sama sekali.

**Build & Release:**
- CI: GitHub Actions `CI` di tiap push ke main.
- Web: https://am-preset-finder.vercel.app (Vercel Git integration, auto-deploy dari `main`).
- Feed: https://raw.githubusercontent.com/xykalnotkel/am-preset-finder/data/feed.json

**Update (sesi sama, setelah push):**
- Semua REST API GitHub buat user `xykalnotkel` balik "API rate limit exceeded" (bucket 60/jam, kayak anonim) dan
  profil + semua repo xykalnotkel 404 buat pengunjung anonim (termasuk repo lama kayak XyDesk & fotolivemaker).
  githubstatus lagi ada incident "API Requests" (investigating). Git push/ls-remote pakai token tetap jalan
  (commit 5a23a82 udah di main). Konsekuensi: raw.githubusercontent feed bisa gak kebaca -> ditambahin fallback.
- `quick_feed()` + `/api/feed` fallback: kalau feed crawler gak kebaca, server scan cepat YouTube terbaru + hashtag
  teratas (embed) -> tes lokal 84 preset aktif dalam 15.8 detik. Cache 30 menit per instance + CDN s-maxage 1800.
- Vercel GitHub App belum ke-install di akun GitHub ini (API: "install the GitHub integration first"),
  jadi deploy lewat Vercel CLI (`vercel deploy --prod`). Auto-deploy dari push butuh Kall install app sekali.

**Next Step:**
- Kall: install https://github.com/apps/vercel ke repo `am-preset-finder` biar auto-deploy tiap push.
- Kall: cek kenapa akun GitHub 404 buat publik (kemungkinan flag/limit dari incident atau aktivitas API berat) -
  kalau udah normal, workflow CI + Crawl jalan sendiri.
- Tambah sumber Instagram Reels (butuh riset akses publik 2026).
- Notifikasi preset baru dari creator favorit (Web Push / OneSignal XyCloudStore? perlu app terpisah biar key gak ketuker).
- Kalau traffic naik: pindah cache link ke Vercel KV / Upstash biar hasil cek dishare antar instance.
