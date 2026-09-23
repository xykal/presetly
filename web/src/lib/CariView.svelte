<script lang="ts">
  import FileLink from './FileLink.svelte';
  import Icon from './Icon.svelte';
  import PresetLink from './PresetLink.svelte';
  import ResultCard from './ResultCard.svelte';
  import SearchPanel from './SearchPanel.svelte';
  import { exportCsv } from './api';
  import { FREE_MB, fmtNum, safeUrl } from './format';
  import { copyText, keyOf, notify, resetSearch, search } from './state.svelte';
  import type { ScanResult } from './types';

  let panel = $state<SearchPanel | null>(null);
  let onlyLinks = $state(true);
  let onlyFree = $state(false);
  let q = $state('');
  let sortBy = $state<'rank' | 'links' | 'views' | 'new' | 'size'>('rank');

  const results = $derived(Object.values(search.results));
  const scanned = $derived(results.length);
  const total = $derived(search.items.length);
  const withLinks = $derived(results.filter((r) => r.n_am || r.n_xml).length);
  const okCount = $derived(results.reduce((a, r) => a + (r.n_ok || 0), 0));
  const freeCount = $derived(
    results.reduce((a, r) => a + r.links.filter((l) => l.type === 'am' && l.info?.status === 'ok' && (l.info.size_mb ?? 99) <= FREE_MB).length, 0),
  );
  const busy = $derived(search.status === 'listing' || search.status === 'scanning');
  const pct = $derived(total ? Math.round((scanned / total) * 100) : 0);

  const visible = $derived.by(() => {
    const needle = q.trim().toLowerCase();
    const list = search.items.filter((it) => {
      const r = search.results[keyOf(it)];
      if (onlyLinks && r && !(r.n_am || r.n_xml)) return false;
      if (onlyFree && r && !r.links.some((l) => l.type === 'am' && l.info?.status === 'ok' && (l.info.size_mb ?? 99) <= FREE_MB)) return false;
      if (onlyFree && !r) return false;
      if (needle) {
        const hay = [it.title, it.author, it.author_handle, ...(r?.links ?? []).map((l) => l.info?.name ?? '')].join(' ').toLowerCase();
        if (!hay.includes(needle)) return false;
      }
      return true;
    });
    const R = (id: string) => search.results[id];
    const key: Record<string, (x: (typeof list)[number]) => number> = {
      rank: (x) => x.rank ?? 0,
      views: (x) => -(x.views ?? 0),
      new: (x) => -(R(keyOf(x))?.ts ?? x.ts ?? 0),
      size: (x) => R(keyOf(x))?.min_size ?? 1e9,
      links: (x) => -((R(keyOf(x))?.n_ok ?? 0) * 10 + (R(keyOf(x))?.n_xml ?? 0)),
    };
    // item yang belum discan tetap di bawah biar gak lompat-lompat
    return [...list].sort((a, b) => {
      const ra = R(keyOf(a)), rb = R(keyOf(b));
      if (!!ra !== !!rb && sortBy !== 'rank') return ra ? -1 : 1;
      return key[sortBy](a) - key[sortBy](b);
    });
  });

  function copyAll() {
    const seen = new Set<string>();
    const lines: string[] = [];
    for (const r of results as ScanResult[])
      for (const l of r.links)
        if (l.type === 'am' && l.info?.status === 'ok') {
          const u = l.info.fixed_url || l.url;
          if (seen.has(u)) continue;
          seen.add(u);
          lines.push(`${l.info.name || 'Preset'}${l.info.size_text ? ` (${l.info.size_text})` : ''}\n${u}`);
        }
    if (!lines.length) return notify('Belum ada link preset aktif', 'bad');
    copyText(lines.join('\n\n'), `${lines.length} link preset disalin`);
  }

  async function doExport() {
    try {
      await exportCsv(results as ScanResult[]);
    } catch (e) {
      notify((e as Error).message, 'bad');
    }
  }
</script>

<section class="cari">
  <div class="hero">
    <h1>Cari preset <span class="grad">Alight Motion</span> tanpa scroll berjam-jam.</h1>
    <p class="muted">Tempel keyword, profil, atau link. Deskripsi, caption, sampai balasan komen dibaca, terus tiap link preset dicek: nama, ukuran, masih aktif atau nggak.</p>
  </div>

  <SearchPanel bind:this={panel} />

  {#if search.status !== 'idle'}
    <div class="status card">
      <div class="top">
        <div class="stage">
          {#if search.status === 'listing'}<span class="spin"></span>Ngumpulin daftar video...
          {:else if search.status === 'scanning'}<span class="spin"></span>Scan {scanned}/{total} video
          {:else if search.status === 'done'}<Icon name="check" size={16} class="okc" />Kelar, {total} video discan{#if search.failed}, {search.failed} gagal{/if}
          {:else if search.status === 'stopped'}<Icon name="stop" size={14} />Dihentikan di {scanned}/{total}
          {:else}<Icon name="alert" size={16} class="badc" />{search.error}{/if}
        </div>
        {#if !busy}<button class="btn sm ghost" onclick={resetSearch}><Icon name="x" size={14} />Bersihin</button>{/if}
      </div>
      {#if busy || search.status === 'done'}
        <div class="bar" class:indet={search.status === 'listing'}><i style="width:{search.status === 'done' ? 100 : pct}%"></i></div>
      {/if}
      {#if total}
        <div class="stats">
          <div><b>{scanned}</b><span>discan</span></div>
          <div class="g"><b>{withLinks}</b><span>ada link</span></div>
          <div class="g"><b>{okCount}</b><span>preset aktif</span></div>
          <div><b>{freeCount}</b><span>≤ 5MB</span></div>
        </div>
      {/if}
    </div>
  {/if}

  {#if search.profile}
    {@const p = search.profile}
    <div class="profile card rise">
      {#if p.avatar}<img src={p.avatar} alt="" referrerpolicy="no-referrer" />{/if}
      <div class="pbody">
        <a href={safeUrl(p.url)} target="_blank" rel="noopener" class="pname">{p.name || p.handle} <span class="muted">@{p.handle}</span></a>
        <div class="muted small">{fmtNum(p.followers)} followers · {fmtNum(p.likes)} likes</div>
        {#if p.bio}<p class="bio">{p.bio}</p>{/if}
      </div>
      {#if p.links?.length}
        <div class="plinks">
          {#each p.links.filter((l) => l.type === 'am') as l (l.url)}<PresetLink link={l} compact />{/each}
          {#each p.links.filter((l) => l.type === 'xml') as l (l.url)}<FileLink link={l} />{/each}
        </div>
      {/if}
    </div>
  {/if}

  {#if search.presetCheck?.length}
    <div class="card check rise">
      <div class="ctitle"><Icon name="link" size={15} />Cek link preset yang lu tempel</div>
      {#each search.presetCheck as l (l.url)}<PresetLink link={l} />{/each}
    </div>
  {/if}

  {#if total}
    <div class="toolbar">
      <div class="field">
        <Icon name="search" size={15} class="lead" />
        <input class="input" bind:value={q} placeholder="Filter judul, creator, nama preset" aria-label="Filter hasil" />
      </div>
      <select class="input" bind:value={sortBy} aria-label="Urutkan">
        <option value="rank">Urutan asli</option>
        <option value="links">Preset terbanyak</option>
        <option value="views">Views terbanyak</option>
        <option value="new">Paling baru</option>
        <option value="size">Preset paling kecil</option>
      </select>
      <div class="chips">
        <button class="chip" class:on={onlyLinks} onclick={() => (onlyLinks = !onlyLinks)}>Ada link aja</button>
        <button class="chip" class:on={onlyFree} onclick={() => (onlyFree = !onlyFree)}>≤ 5MB (AM gratis)</button>
      </div>
      <div class="spacer"></div>
      <button class="btn sm" onclick={copyAll} disabled={!okCount}><Icon name="copy" size={14} />Copy semua</button>
      <button class="btn sm" onclick={doExport} disabled={!scanned}><Icon name="download" size={14} />CSV</button>
    </div>

    <div class="list">
      {#each visible as it (keyOf(it))}
        <ResultCard item={it} result={search.results[keyOf(it)]} onScanBio={(h) => panel?.scanProfile(h)} />
      {:else}
        <div class="empty card">
          <Icon name="filter" size={22} />
          <div>{busy ? 'Hasil yang ada link bakal muncul di sini...' : 'Gak ada yang cocok sama filter.'}</div>
          {#if !busy}<button class="btn sm" onclick={() => { onlyLinks = false; onlyFree = false; q = ''; }}>Reset filter</button>{/if}
        </div>
      {/each}
    </div>
  {:else if search.status === 'listing'}
    <div class="list">
      {#each [0, 1, 2] as i (i)}
        <div class="card sk"><div class="skeleton t"></div><div class="lines"><div class="skeleton l1"></div><div class="skeleton l2"></div></div></div>
      {/each}
    </div>
  {:else if search.status === 'done' && !total && !search.presetCheck?.length}
    <div class="empty card"><Icon name="search" size={22} /><div>Gak nemu video. Coba keyword / username lain.</div></div>
  {/if}

  {#if search.status === 'idle'}
    <div class="how">
      <div class="step card"><span class="n">1</span><b>Pilih sumber</b><p class="muted">YouTube keyword/channel, profil TikTok, atau tempel link langsung.</p></div>
      <div class="step card"><span class="n">2</span><b>Otomatis discan</b><p class="muted">Deskripsi, komen pinned, sampai balasan creator dibaca. Link palsu & kepotong dibuang.</p></div>
      <div class="step card"><span class="n">3</span><b>Buka di AM</b><p class="muted">Di HP langsung kebuka di Alight Motion. Di PC muncul QR buat discan.</p></div>
    </div>
  {/if}
</section>

<style>
  .cari {
    display: flex;
    flex-direction: column;
    gap: 14px;
  }
  .hero {
    padding: 10px 2px 2px;
  }
  h1 {
    margin: 0;
    font-size: clamp(24px, 4.6vw, 38px);
    line-height: 1.12;
    letter-spacing: -0.025em;
    font-weight: 800;
    max-width: 780px;
  }
  .grad {
    background: linear-gradient(100deg, #d7c9ff, var(--brand) 45%, var(--cyan));
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
  }
  .hero p {
    margin: 10px 0 0;
    max-width: 640px;
    font-size: 14.5px;
  }
  .status {
    padding: 13px 14px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .top {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
  }
  .stage {
    display: flex;
    align-items: center;
    gap: 9px;
    font-weight: 600;
    font-size: 14px;
  }
  .stage :global(.okc) {
    color: var(--ok);
  }
  .stage :global(.badc) {
    color: var(--bad);
  }
  .spin {
    width: 15px;
    height: 15px;
    border-radius: 50%;
    border: 2px solid var(--surface-3);
    border-top-color: var(--brand);
    animation: spin 0.7s linear infinite;
  }
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
  .bar {
    height: 6px;
    border-radius: 99px;
    background: var(--bg-1);
    overflow: hidden;
  }
  .bar i {
    display: block;
    height: 100%;
    border-radius: 99px;
    background: linear-gradient(90deg, var(--brand-2), var(--brand), var(--cyan));
    transition: width 0.4s var(--ease);
  }
  .bar.indet i {
    width: 30% !important;
    animation: ind 1.1s ease-in-out infinite;
  }
  @keyframes ind {
    from {
      margin-left: -30%;
    }
    to {
      margin-left: 100%;
    }
  }
  .stats {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 8px;
  }
  .stats div {
    padding: 8px;
    border-radius: 12px;
    background: var(--bg-1);
    border: 1px solid var(--line);
    text-align: center;
  }
  .stats b {
    display: block;
    font-size: 19px;
    line-height: 1.15;
    font-variant-numeric: tabular-nums;
  }
  .stats .g b {
    color: var(--ok);
  }
  .stats span {
    font-size: 11px;
    color: var(--muted);
  }
  .profile {
    padding: 14px;
    display: grid;
    grid-template-columns: 56px 1fr;
    gap: 12px;
  }
  .profile img {
    width: 56px;
    height: 56px;
    border-radius: 50%;
    object-fit: cover;
    background: var(--surface-2);
  }
  .pname {
    font-weight: 700;
  }
  .small {
    font-size: 12px;
  }
  .bio {
    margin: 6px 0 0;
    white-space: pre-wrap;
    font-size: 13px;
    color: var(--text-2);
  }
  .plinks {
    grid-column: 1 / -1;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .check {
    padding: 14px;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .ctitle {
    display: flex;
    gap: 7px;
    align-items: center;
    font-weight: 650;
    font-size: 14px;
  }
  .toolbar {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 8px;
    position: sticky;
    top: 62px;
    z-index: 5;
    padding: 8px 0;
    background: linear-gradient(var(--bg) 70%, transparent);
  }
  .toolbar .field {
    position: relative;
    flex: 1 1 220px;
  }
  .toolbar .field .input {
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
  }
  .spacer {
    flex: 1;
  }
  .list {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .empty {
    padding: 28px 16px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 10px;
    text-align: center;
    color: var(--muted);
  }
  .sk {
    padding: 12px;
    display: flex;
    gap: 14px;
  }
  .sk .t {
    width: 112px;
    aspect-ratio: 9/16;
    border-radius: 14px;
    max-height: 150px;
  }
  .lines {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding-top: 4px;
  }
  .l1 {
    height: 16px;
    width: 80%;
    border-radius: 6px;
  }
  .l2 {
    height: 12px;
    width: 45%;
    border-radius: 6px;
  }
  .how {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
  }
  .step {
    padding: 14px;
  }
  .step .n {
    display: inline-grid;
    place-items: center;
    width: 24px;
    height: 24px;
    border-radius: 8px;
    background: var(--brand-soft);
    color: var(--text-2);
    font-size: 12px;
    font-weight: 800;
    margin-bottom: 8px;
  }
  .step b {
    display: block;
    font-size: 14px;
  }
  .step p {
    margin: 4px 0 0;
    font-size: 12.5px;
  }
  @media (max-width: 720px) {
    .how {
      grid-template-columns: 1fr;
    }
    .stats {
      grid-template-columns: repeat(2, 1fr);
    }
    .toolbar {
      top: 56px;
    }
  }
</style>
