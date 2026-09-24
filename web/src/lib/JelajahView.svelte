<script lang="ts">
  import Icon from './Icon.svelte';
  import PresetCard from './PresetCard.svelte';
  import { api } from './api';
  import { FREE_MB, timeAgo } from './format';
  import type { Feed } from './types';

  let feed = $state<Feed | null>(null);
  let loading = $state(true);
  let error = $state('');
  let q = $state('');
  let onlyFree = $state(false);
  let platform = $state<'all' | 'tiktok' | 'youtube'>('all');
  let sortBy = $state<'new' | 'small' | 'popular'>('new');
  let shown = $state(24);
  let creator = $state<string | null>(null);

  // Creator yang terdeteksi di feed, diurut dari paling produktif.
  const creators = $derived.by(() => {
    const m = new Map<string, number>();
    for (const it of feed?.items ?? [])
      for (const s of it.sources ?? []) {
        const h = (s.author_handle || s.author || '').replace(/^@/, '');
        if (h) m.set(h, (m.get(h) ?? 0) + 1);
      }
    return [...m.entries()].sort((a, b) => b[1] - a[1]);
  });
  const totals = $derived.by(() => {
    const c = { tiktok: 0, youtube: 0 };
    for (const it of feed?.items ?? [])
      for (const s of it.sources ?? []) if (s.platform === 'tiktok' || s.platform === 'youtube') c[s.platform as 'tiktok' | 'youtube'] += 1;
    return c;
  });

  async function load() {
    loading = true;
    error = '';
    try {
      feed = await api.feed();
    } catch (e) {
      error = (e as Error).message;
    } finally {
      loading = false;
    }
  }
  $effect(() => {
    load();
  });

  const items = $derived.by(() => {
    const needle = q.trim().toLowerCase();
    const list = (feed?.items ?? []).filter((p) => {
      if (onlyFree && !((p.size_mb ?? 99) <= FREE_MB)) return false;
      if (platform !== 'all' && !p.sources?.some((s) => s.platform === platform)) return false;
      if (creator && !(p.sources ?? []).some((s) => (s.author_handle || s.author || '').replace(/^@/, '') === creator)) return false;
      if (needle && ![p.name, ...(p.sources ?? []).map((s) => `${s.author} ${s.author_handle} ${s.title}`)].join(' ').toLowerCase().includes(needle)) return false;
      return true;
    });
    const k: Record<string, (p: (typeof list)[number]) => number> = {
      new: (p) => -(p.last_seen ?? 0),
      small: (p) => p.size_mb ?? 1e9,
      popular: (p) => -Math.max(...(p.sources ?? []).map((s) => s.views ?? 0), 0),
    };
    return [...list].sort((a, b) => k[sortBy](a) - k[sortBy](b));
  });

  $effect(() => {
    // reset pagination tiap filter berubah
    void q;
    void onlyFree;
    void platform;
    void sortBy;
    void creator;
    shown = 24;
  });
</script>

<section class="jelajah">
  <div class="hero">
    <h1>Jelajah preset</h1>
    <p class="muted">
      {#if feed?.mode === 'live'}
        Hasil scan cepat dari YouTube terbaru & hashtag teratas. Cuma preset yang linknya masih aktif.
      {:else}
        Hasil crawler hashtag TikTok & YouTube, cuma preset yang linknya masih aktif.
      {/if}
      {#if feed?.updated}<span class="upd"><Icon name="clock" size={13} />update {timeAgo(feed.updated)}</span>{/if}
    </p>
  </div>

  <div class="toolbar">
    <div class="field">
      <Icon name="search" size={15} class="lead" />
      <input class="input" bind:value={q} placeholder="Cari nama preset / creator" aria-label="Cari preset" />
    </div>
    <select class="input" bind:value={sortBy} aria-label="Urutkan">
      <option value="new">Terbaru</option>
      <option value="popular">Paling rame</option>
      <option value="small">Ukuran terkecil</option>
    </select>
    <div class="chips">
      <button class="chip" class:on={platform === 'all'} onclick={() => (platform = 'all')}>Semua</button>
      <button class="chip" class:on={platform === 'tiktok'} onclick={() => (platform = 'tiktok')}><Icon name="tiktok" size={12} />TikTok</button>
      <button class="chip" class:on={platform === 'youtube'} onclick={() => (platform = 'youtube')}><Icon name="youtube" size={13} />YouTube</button>
      <button class="chip" class:on={onlyFree} onclick={() => (onlyFree = !onlyFree)}>≤ 5MB</button>
    </div>
  </div>

  {#if creators.length > 1}
    <div class="cchips" aria-label="Filter creator">
      <button class="chip sm" class:on={creator === null} onclick={() => (creator = null)}>Semua creator</button>
      {#each creators.slice(0, 8) as [h, n] (h)}
        <button class="chip sm" class:on={creator === h} onclick={() => (creator = creator === h ? null : h)}>@{h} <span class="n">{n}</span></button>
      {/each}
    </div>
  {/if}

  {#if loading}
    <div class="muted small-note">Lagi ngumpulin preset... pertama kali bisa sampe 20 detik.</div>
    <div class="grid">
      {#each Array(8) as _, i (i)}<div class="card skc"><div class="skeleton a"></div><div class="skeleton b"></div><div class="skeleton c"></div></div>{/each}
    </div>
  {:else if error}
    <div class="empty card"><Icon name="alert" size={22} /><div>{error}</div><button class="btn sm" onclick={load}><Icon name="refresh" size={14} />Coba lagi</button></div>
  {:else if !feed?.items.length}
    <div class="empty card"><Icon name="compass" size={24} /><div><b>Feed belum ada isinya.</b><br />Coba refresh bentar lagi ya.</div></div>
  {:else}
    <div class="count muted">{items.length} preset · {creators.length} creator (TikTok {totals.tiktok} · YouTube {totals.youtube})</div>
    <div class="grid">
      {#each items.slice(0, shown) as p (p.key)}<PresetCard preset={p} />{/each}
    </div>
    {#if shown < items.length}
      <button class="btn more" onclick={() => (shown += 24)}>Tampilin lagi ({items.length - shown})</button>
    {/if}
    {#if !items.length}
      <div class="empty card"><Icon name="filter" size={22} /><div>Gak ada yang cocok sama filter.</div></div>
    {/if}
  {/if}
</section>

<style>
  .jelajah {
    display: flex;
    flex-direction: column;
    gap: 14px;
  }
  .hero {
    padding: 10px 2px 0;
  }
  h1 {
    margin: 0;
    font-size: clamp(24px, 4.2vw, 34px);
    letter-spacing: -0.025em;
    font-weight: 800;
  }
  .hero p {
    margin: 8px 0 0;
    font-size: 14px;
    max-width: 680px;
  }
  .upd {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    margin-left: 6px;
    color: var(--text-2);
  }
  .toolbar {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
    position: sticky;
    top: 62px;
    z-index: 5;
    padding: 8px 0;
    background: linear-gradient(var(--bg) 70%, transparent);
  }
  .field {
    position: relative;
    flex: 1 1 220px;
  }
  .field .input {
    height: 38px;
    padding-left: 36px;
    font-size: 13.5px;
  }
  .toolbar :global(.lead) {
    position: absolute;
    left: 12px;
    top: 50%;
    transform: translateY(-50%);
    color: var(--faint);
  }
  .chips {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }
  .count,
  .small-note {
    font-size: 12.5px;
  }
  .grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 12px;
  }
  @media (max-width: 520px) {
    .grid {
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
    }
    .toolbar {
      top: 56px;
    }
  }
  .skc {
    padding: 0 0 12px;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    gap: 9px;
  }
  .skc .a {
    aspect-ratio: 1;
  }
  .skc .b {
    height: 14px;
    margin: 0 11px;
    border-radius: 6px;
  }
  .skc .c {
    height: 30px;
    margin: 0 11px;
    border-radius: 9px;
  }
  .more {
    align-self: center;
  }
  .empty {
    padding: 30px 16px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 10px;
    text-align: center;
    color: var(--muted);
  }

  .cchips {
    display: flex;
    gap: 6px;
    overflow-x: auto;
    padding: 2px 1px 4px;
    scrollbar-width: none;
  }
  .cchips::-webkit-scrollbar {
    display: none;
  }
  .chip.sm {
    height: 26px;
    padding: 0 10px;
    font-size: 11.5px;
    flex: none;
  }
  .chip.sm .n {
    color: var(--muted);
    font-size: 10.5px;
  }
  .chip.sm.on .n {
    color: rgba(246, 243, 255, 0.75);
  }
  .grid > :global(.card) {
    content-visibility: auto;
    contain-intrinsic-size: auto 210px;
  }
</style>
