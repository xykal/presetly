<script lang="ts">
  import Icon from './Icon.svelte';
  import type { ListParams, ScanOpts } from './api';
  import { notify, runSearch, search, stopSearch, ui } from './state.svelte';
  import { recent, type RecentSearch } from './storage';

  type Pf = 'youtube' | 'tiktok' | 'instagram' | 'link';
  let pf = $state<Pf>('youtube');
  let ytMode = $state<'search' | 'channel'>('search');
  let ttMode = $state<'hashtag' | 'profile'>('profile');
  let query = $state('');
  let links = $state('');
  let limit = $state(20);
  let sort = $state<'relevance' | 'new'>('relevance');
  let comments = $state(true);
  let deep = $state(true);
  let showOpts = $state(false);
  let recents = $state<RecentSearch[]>(recent.all());

  const busy = $derived(search.status === 'listing' || search.status === 'scanning');
  const mode = $derived(pf === 'youtube' ? ytMode : pf === 'tiktok' ? ttMode : pf === 'instagram' ? 'profile' : 'auto');
  const liveTag = $derived(!!ui.health?.hashtag_live);

  const CONF: Record<string, { ph: string; chips: string[]; note: string; limit: number }> = {
    'youtube:search': {
      ph: 'preset alight motion jedag jedug', limit: 20,
      chips: ['preset alight motion', 'preset am dibawah 5mb', 'preset jedag jedug', 'preset xml alight motion', 'preset am kane', 'preset anime edit'],
      note: 'Baca deskripsi, komen pinned & komen creator tiap video.',
    },
    'youtube:channel': { ph: '@namachannel atau link channel', limit: 30, chips: [], note: 'Scan shorts + video terbaru dari 1 channel.' },
    'tiktok:profile': {
      ph: '@username creator preset', limit: 24, chips: ['@dan_newbie', '@rezzpreset77', '@avn_al', '@dizzypreset8'],
      note: 'Caption, komen, sampai balasan creator ikut dibaca. Bio profil juga dicek.',
    },
    'tiktok:hashtag': {
      ph: 'presetalightmotion (tanpa #)', limit: 40,
      chips: ['presetalightmotion', 'presetam', 'presetdibawah5mb', 'presetxml', 'alightmotionpreset'],
      note: '',
    },
    'link:auto': { ph: '', limit: 30, chips: [], note: 'Bisa campur: video/shorts, vt.tiktok.com, profil, channel, playlist, reel IG, alight.link.' },
    'instagram:profile': {
      ph: '@username atau link profil instagram.com', limit: 24, chips: [],
      note: 'Baca caption + bio profil (komen IG butuh login, gak discan). Reel lama bisa lewat Tempel link.',
    },
  };
  const conf = $derived(CONF[`${pf}:${mode}`]);

  $effect(() => {
    limit = conf.limit;
  });

  function submit(e?: Event) {
    e?.preventDefault();
    const q = (pf === 'link' ? links : query).trim();
    if (!q) {
      notify('Isi dulu keyword / link-nya', 'bad');
      return;
    }
    const p: ListParams = { platform: pf, mode, query: q, limit, sort, live: pf === 'tiktok' && mode === 'hashtag' && liveTag };
    const opts: ScanOpts = { comments, deep, resolve: true };
    runSearch(p, opts);
    recents = recent.all();
    // Simpan pencarian ke URL biar bisa dibagikan / di-bookmark.
    const u = new URL(location.href);
    u.search = pf === 'link' ? '' : '?' + new URLSearchParams({ pf, mode, q: q.slice(0, 120) }).toString();
    u.hash = '';
    history.replaceState(null, '', u.pathname + u.search);
  }

  // Auto-jalan kalau dibuka dari URL hasil share (?pf=&mode=&q=).
  let autoRan = false;
  $effect(() => {
    if (autoRan) return;
    const sp = new URLSearchParams(location.search);
    const qq = sp.get('q');
    if (!qq) return;
    autoRan = true;
    const p2 = sp.get('pf') || 'youtube';
    if (p2 === 'youtube' || p2 === 'tiktok' || p2 === 'instagram' || p2 === 'link') pf = p2;
    const m = sp.get('mode') || '';
    if (pf === 'youtube' && (m === 'search' || m === 'channel')) ytMode = m;
    if (pf === 'tiktok' && (m === 'profile' || m === 'hashtag')) ttMode = m;
    if (pf === 'link') links = qq;
    else query = qq;
    submit();
  });

  function useRecent(r: RecentSearch) {
    pf = r.platform as Pf;
    if (pf === 'youtube') ytMode = r.mode as 'search' | 'channel';
    if (pf === 'tiktok') ttMode = r.mode as 'hashtag' | 'profile';
    if (pf === 'link') links = r.query;
    else query = r.query;
    submit();
  }

  export function scanProfile(handle: string) {
    pf = 'tiktok';
    ttMode = 'profile';
    query = '@' + handle;
    submit();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
</script>

<form class="panel card" onsubmit={submit}>
  <div class="tabs" role="tablist" aria-label="Sumber">
    <button type="button" role="tab" aria-selected={pf === 'youtube'} class:on={pf === 'youtube'} onclick={() => (pf = 'youtube')}>
      <Icon name="youtube" size={17} class="yt" />YouTube
    </button>
    <button type="button" role="tab" aria-selected={pf === 'tiktok'} class:on={pf === 'tiktok'} onclick={() => (pf = 'tiktok')}>
      <Icon name="tiktok" size={16} class="tt" />TikTok
    </button>
    <button type="button" role="tab" aria-selected={pf === 'instagram'} class:on={pf === 'instagram'} onclick={() => (pf = 'instagram')}>
      <Icon name="instagram" size={16} class="ig" />Instagram
    </button>
    <button type="button" role="tab" aria-selected={pf === 'link'} class:on={pf === 'link'} onclick={() => (pf = 'link')}>
      <Icon name="link" size={16} /><span class="full">Tempel link</span><span class="short">Link</span>
    </button>
  </div>

  {#if pf !== 'link'}
    <div class="modes">
      {#if pf === 'youtube'}
        <button type="button" class="chip" class:on={ytMode === 'search'} onclick={() => (ytMode = 'search')}><Icon name="search" size={13} />Keyword</button>
        <button type="button" class="chip" class:on={ytMode === 'channel'} onclick={() => (ytMode = 'channel')}><Icon name="user" size={13} />Channel</button>
      {:else if pf === 'tiktok'}
        <button type="button" class="chip" class:on={ttMode === 'profile'} onclick={() => (ttMode = 'profile')}><Icon name="user" size={13} />Profil creator</button>
        <button type="button" class="chip" class:on={ttMode === 'hashtag'} onclick={() => (ttMode = 'hashtag')}><Icon name="hash" size={13} />Hashtag</button>
      {:else}
        <button type="button" class="chip on"><Icon name="user" size={13} />Profil creator</button>
      {/if}
    </div>
    <div class="field">
      <Icon name={pf === 'tiktok' && ttMode === 'hashtag' ? 'hash' : pf === 'instagram' || pf === 'tiktok' || ytMode === 'channel' ? 'user' : 'search'} size={18} class="lead" />
      <input class="input" bind:value={query} placeholder={conf.ph} autocomplete="off" enterkeyhint="search" aria-label="Kata kunci" />
    </div>
  {:else}
    <textarea class="input" bind:value={links} placeholder={'Satu link per baris:\nhttps://vt.tiktok.com/xxxx/\nhttps://youtube.com/shorts/xxxx\nhttps://www.instagram.com/reel/xxxx\nhttps://www.tiktok.com/@creator\nhttps://alight.link/xxxx'} aria-label="Daftar link"></textarea>
  {/if}

  {#if conf.chips.length}
    <div class="chips">
      {#each conf.chips as c (c)}
        <button type="button" class="chip" onclick={() => { query = c; submit(); }}>{pf === 'tiktok' && ttMode === 'hashtag' ? '#' : ''}{c}</button>
      {/each}
    </div>
  {/if}

  {#if pf === 'tiktok' && ttMode === 'hashtag'}
    <div class="note warnish">
      <Icon name="info" size={15} />
      {#if liveTag}
        <span>Mode lokal: hashtag discan penuh pakai browser headless (20-60 detik).</span>
      {:else}
        <span>TikTok nge-block server cloud buat halaman hashtag, jadi di sini cuma dapet video teratas. Buat hasil lebih banyak cek tab <b>Jelajah</b>, pakai <b>Profil creator</b>, atau jalanin versi lokal.</span>
      {/if}
    </div>
  {:else if conf.note}
    <div class="note"><Icon name="info" size={15} /><span>{conf.note}</span></div>
  {/if}

  <div class="row">
    <button type="button" class="btn ghost sm" onclick={() => (showOpts = !showOpts)} aria-expanded={showOpts}>
      <Icon name="filter" size={14} />Pengaturan
    </button>
    <div class="spacer"></div>
    {#if busy}
      <button type="button" class="btn danger" onclick={stopSearch}><Icon name="stop" size={14} />Stop</button>
    {:else}
      <button type="submit" class="btn primary go"><Icon name="search" size={16} />Cari preset</button>
    {/if}
  </div>

  {#if showOpts}
    <div class="opts">
      <label>Jumlah video
        <select class="input" bind:value={limit}>
          {#each [10, 20, 30, 40, 60] as n (n)}<option value={n}>{n}</option>{/each}
        </select>
      </label>
      {#if pf === 'youtube' && ytMode === 'search'}
        <label>Urutan
          <select class="input" bind:value={sort}><option value="relevance">Paling relevan</option><option value="new">Terbaru</option></select>
        </label>
      {/if}
      <label class="check"><input type="checkbox" bind:checked={comments} /> Scan komentar</label>
      {#if pf !== 'youtube'}<label class="check"><input type="checkbox" bind:checked={deep} /> Buka balasan komen</label>{/if}
    </div>
  {/if}

  {#if recents.length && search.status === 'idle'}
    <div class="recent">
      <span class="muted">Terakhir:</span>
      {#each recents.slice(0, 5) as r (r.platform + r.mode + r.query)}
        <button type="button" class="chip" onclick={() => useRecent(r)}>
          <Icon name={r.platform === 'link' ? 'link' : r.platform} size={12} />{r.query.split('\n')[0].slice(0, 28)}
        </button>
      {/each}
      <button type="button" class="clear" onclick={() => { recent.clear(); recents = []; }}>hapus</button>
    </div>
  {/if}
</form>

<style>
  .panel {
    padding: 14px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .tabs {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 4px;
    padding: 4px;
    border-radius: 14px;
    background: var(--bg-1);
    border: 1px solid var(--line);
  }
  .tabs button {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 7px;
    height: 40px;
    border-radius: 10px;
    border: 0;
    background: transparent;
    color: var(--muted);
    font-weight: 650;
    font-size: 14px;
    transition: all 0.15s var(--ease);
  }
  .tabs button.on {
    background: var(--surface-3);
    color: var(--text);
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.05);
  }
  .tabs button.on :global(.yt) {
    color: var(--yt);
  }
  .tabs button.on :global(.tt) {
    color: var(--tt);
  }
  .modes,
  .chips,
  .recent {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
    align-items: center;
  }
  .field {
    position: relative;
  }
  .field :global(.lead) {
    position: absolute;
    left: 14px;
    top: 50%;
    transform: translateY(-50%);
    color: var(--faint);
    pointer-events: none;
  }
  .field .input {
    padding-left: 42px;
  }
  .note {
    display: flex;
    gap: 8px;
    align-items: flex-start;
    font-size: 12.5px;
    color: var(--muted);
    line-height: 1.45;
  }
  .note :global(svg) {
    flex: none;
    margin-top: 1px;
  }
  .note.warnish {
    padding: 10px 12px;
    border-radius: 12px;
    background: var(--brand-soft);
    color: var(--text-2);
  }
  .row {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .spacer {
    flex: 1;
  }
  .go {
    min-width: 160px;
    height: 44px;
    font-size: 14.5px;
  }
  .opts {
    display: flex;
    flex-wrap: wrap;
    gap: 10px 18px;
    padding: 12px;
    border-radius: 12px;
    background: var(--bg-1);
    border: 1px solid var(--line);
    font-size: 13px;
    color: var(--text-2);
  }
  .opts label {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .opts input[type='checkbox'] {
    accent-color: var(--brand);
    width: 16px;
    height: 16px;
  }
  .recent {
    font-size: 12px;
  }
  .clear {
    background: none;
    border: 0;
    color: var(--faint);
    font-size: 12px;
    text-decoration: underline;
  }
  .short {
    display: none;
  }
  @media (max-width: 420px) {
    .full {
      display: none;
    }
    .short {
      display: inline;
    }
  }
  @media (max-width: 560px) {
    .go {
      min-width: 0;
      flex: 1;
    }
    .tabs button {
      font-size: 13px;
      gap: 5px;
    }
  }
</style>
