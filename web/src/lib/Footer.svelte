<script lang="ts">
  import Icon from './Icon.svelte';
  import XyverseMark from './XyverseMark.svelte';
  import { copyText, ui } from './state.svelte';

  // Section wajib "JUGA DARI XYVERSE" (XYVERSE_GLOBAL_RULES.md #6), gaya PROFIL:
  // tanpa card - list ke kiri: mark -> nama -> deskripsi -> panah.
  // Mark = blok warna flat (paket logo resmi filebin expired 2026-09; swap kalau re-upload).
  const APPS = [
    { name: 'XyVerse', desc: 'Cloud PC, apps & software', url: 'https://www.xyverse.my.id', bg: '#7c5ce0', mark: 'xv' },
    { name: 'XyDesk', desc: 'Remote desktop low-latency', url: 'https://github.com/xykalnotkel/XyDesk', bg: '#8f71f0', mark: 'D' },
    { name: 'XyCloudStore', desc: 'Sewa Cloud PC & akun digital', url: 'https://github.com/xykalnotkel/XyCloudStore', bg: '#4fb7ff', mark: 'C' },
    { name: 'XyDownloader', desc: 'Downloader semua platform', url: 'https://xydownloader.vercel.app', bg: '#46c98b', mark: 'X' },
    { name: 'Suara Deck', desc: 'Deck musik + lirik sinkron', url: 'https://suara-deck.vercel.app', bg: '#e0a947', mark: 'S' },
    { name: 'FotoLive Maker', desc: 'Video jadi Live Photo TikTok', url: 'https://github.com/xykalnotkel/fotolivemaker', bg: '#e8649c', mark: 'F' },
  ];
  const DANA = '6283116632566';
  const danaQty = 'DANA_RELIEF_PRESETLY';
</script>

<footer>
  <div class="container">
    <div class="head">
      <XyverseMark size={16} />
      <span>JUGA DARI XYVERSE</span>
    </div>

    <div class="list">
      {#each APPS as a (a.name)}
        <a class="row" href={a.url} target="_blank" rel="noopener">
          <span class="mark m-{a.mark}" style="background:{a.bg}">
            {#if a.mark === 'xv'}
              <XyverseMark size={22} />
            {:else}
              {a.mark}
            {/if}
          </span>
          <span class="txt">
            <b>{a.name}</b>
            <small>{a.desc}</small>
          </span>
          <Icon name="chevron" size={16} class="arr" />
        </a>
      {/each}
    </div>

    <div class="head don">
      <Icon name="heart" size={15} />
      <span>DONASI DUKUNGAN</span>
    </div>

    <div class="list">
      <div class="row dana">
        <span class="mark d-mark">DANA</span>
        <span class="txt">
          <b>DANA - {DANA.slice(0, 4)} {DANA.slice(4, 8)} {DANA.slice(8)}</b>
          <small>Bantu jaga server Presetly tetap hidup. Berapapun makasih, bro.</small>
        </span>
        <span class="acts">
          <button class="btn sm" onclick={() => copyText(DANA, 'Nomor DANA disalin')} aria-label="Salin nomor DANA"><Icon name="copy" size={14} />Salin</button>
          <button class="btn sm" onclick={() => (ui.qr = { url: `DANA ${DANA}`, name: 'Dana Presetly' })} aria-label="QR DANA"><Icon name="qr" size={14} />QR</button>
        </span>
      </div>
    </div>

    <div class="bottom">
      <div class="made">
        <XyverseMark size={18} />
        <div class="txt">
          <b>Built-in XyVerse</b>
          <small class="muted">Made in XyVerse By Kall</small>
        </div>
      </div>
      <p class="muted disc">
        Gak berafiliasi sama Alight Motion, TikTok, YouTube, atau Instagram. Preset milik creator masing-masing - jangan lupa kasih credit (cr) kalau dipake.
      </p>
      <a class="gh" href="https://github.com/xykal/presetly" target="_blank" rel="noopener"><Icon name="github" size={16} />Source code</a>
    </div>
  </div>
</footer>

<style>
  footer {
    margin-top: 52px;
    padding: 30px 0 calc(104px + var(--safe-b));
    background: var(--bg-1);
  }
  @media (min-width: 900px) {
    footer {
      padding-bottom: 36px;
    }
  }
  .head {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 11px;
    letter-spacing: 0.14em;
    font-weight: 800;
    color: var(--text-2);
    margin-bottom: 14px;
  }
  .head :global(svg) {
    color: var(--brand-2);
  }
  .head.don {
    margin-top: 30px;
  }
  .head.don :global(svg) {
    color: var(--pink);
  }
  .list {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  @media (min-width: 720px) {
    .list {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 4px 22px;
    }
  }
  .row {
    display: flex;
    align-items: center;
    gap: 13px;
    padding: 11px 12px;
    border-radius: var(--r);
    background: var(--surface);
    transition: background 0.16s var(--ease), transform 0.16s var(--ease);
    text-align: left;
  }
  .row:hover {
    background: var(--surface-2);
    transform: translateX(3px);
  }
  .mark {
    flex: none;
    width: 42px;
    height: 42px;
    border-radius: 12px;
    display: grid;
    place-items: center;
    font-weight: 800;
    font-size: 16px;
    color: #fff;
    letter-spacing: 0.02em;
  }
  .d-mark {
    background: var(--dana);
    font-size: 9.5px;
    letter-spacing: 0.06em;
  }
  .txt {
    display: flex;
    flex-direction: column;
    gap: 1px;
    min-width: 0;
  }
  .txt b {
    font-size: 13.5px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .txt small {
    font-size: 11.5px;
    color: var(--muted);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .row :global(.arr) {
    margin-left: auto;
    color: var(--faint);
    flex: none;
  }
  .row.dana .acts {
    margin-left: auto;
    display: flex;
    gap: 6px;
    flex: none;
  }
  .bottom {
    margin-top: 26px;
    display: flex;
    flex-wrap: wrap;
    gap: 14px 22px;
    align-items: center;
  }
  .made {
    display: flex;
    gap: 10px;
    align-items: center;
  }
  .disc {
    flex: 1 1 300px;
    margin: 0;
    font-size: 12px;
  }
  .gh {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-size: 12.5px;
    color: var(--text-2);
  }
  .gh:hover {
    color: var(--text);
  }
</style>
