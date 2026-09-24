<script lang="ts">
  import Icon from './Icon.svelte';
  import XyverseMark from './XyverseMark.svelte';

  // Section wajib "JUGA DARI XYVERSE" (aturan branding XYVERSE_GLOBAL_RULES.md #6).
  const APPS = [
    { name: 'XyVerse', desc: 'Cloud PC, apps & software', url: 'https://www.xyverse.my.id' },
    { name: 'XyDesk', desc: 'Remote desktop low-latency', url: 'https://github.com/xykalnotkel/XyDesk' },
    { name: 'XyCloudStore', desc: 'Sewa Cloud PC & akun digital', url: 'https://github.com/xykalnotkel/XyCloudStore' },
    { name: 'XyDownloader', desc: 'Downloader semua platform', url: 'https://xydownloader.vercel.app' },
    { name: 'Suara Deck', desc: 'Deck musik + lirik sinkron', url: 'https://suara-deck.vercel.app' },
    { name: 'FotoLive Maker', desc: 'Video jadi Live Photo TikTok', url: 'https://github.com/xykalnotkel/fotolivemaker' },
  ];
</script>

<footer>
  <div class="container">
    <div class="also">
      <div class="label"><XyverseMark size={14} /> JUGA DARI XYVERSE</div>
      <div class="apps">
        {#each APPS as a (a.name)}
          <a href={a.url} target="_blank" rel="noopener" class="app">
            <b>{a.name}</b><span>{a.desc}</span>
          </a>
        {/each}
      </div>
    </div>
    <div class="bottom">
      <div class="made">
        <XyverseMark size={18} />
        <div>
          <b>Built-in XyVerse</b>
          <span class="muted">Made in XyVerse By Kall</span>
        </div>
      </div>
      <p class="muted disc">
        Gak berafiliasi sama Alight Motion, TikTok, atau YouTube. Semua preset milik creator masing-masing, jangan lupa kasih credit (cr) kalau dipake.
      </p>
      <a class="gh" href="https://github.com/xykal/presetly" target="_blank" rel="noopener"><Icon name="github" size={16} />Source code</a>
    </div>
  </div>
</footer>

<style>
  footer {
    margin-top: 48px;
    border-top: 1px solid var(--line);
    padding: 26px 0 calc(96px + var(--safe-b));
    background: linear-gradient(180deg, transparent, rgba(139, 92, 246, 0.04));
  }
  @media (min-width: 900px) {
    footer {
      padding-bottom: 34px;
    }
  }
  .label {
    display: flex;
    align-items: center;
    gap: 7px;
    font-size: 11px;
    letter-spacing: 0.14em;
    font-weight: 800;
    color: var(--text-2);
    margin-bottom: 12px;
  }
  .apps {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
    gap: 8px;
  }
  @media (max-width: 560px) {
    .apps {
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }
  }
  .app {
    display: flex;
    flex-direction: column;
    gap: 2px;
    padding: 10px 12px;
    border-radius: 12px;
    border: 1px solid var(--line);
    background: var(--surface);
    transition: border-color 0.15s var(--ease);
  }
  .app:hover {
    border-color: rgba(167, 139, 218, 0.4);
  }
  .app b {
    font-size: 13px;
  }
  .app span {
    font-size: 11.5px;
    color: var(--muted);
  }
  .bottom {
    margin-top: 22px;
    display: flex;
    flex-wrap: wrap;
    gap: 14px 24px;
    align-items: center;
  }
  .made {
    display: flex;
    gap: 10px;
    align-items: center;
  }
  .made div {
    display: flex;
    flex-direction: column;
    line-height: 1.25;
    font-size: 13px;
  }
  .made span {
    font-size: 11.5px;
  }
  .disc {
    flex: 1 1 320px;
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
</style>
