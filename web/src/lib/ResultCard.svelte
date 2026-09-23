<script lang="ts">
  import FileLink from './FileLink.svelte';
  import Icon from './Icon.svelte';
  import PresetLink from './PresetLink.svelte';
  import VideoThumb from './VideoThumb.svelte';
  import { fmtNum, safeUrl, timeAgo } from './format';
  import type { ScanResult, VideoItem } from './types';

  let {
    item,
    result,
    onScanBio,
  }: { item: VideoItem; result?: ScanResult; onScanBio?: (handle: string) => void } = $props();

  const r = $derived(result);
  const am = $derived((r?.links ?? []).filter((l) => l.type === 'am'));
  const files = $derived((r?.links ?? []).filter((l) => l.type === 'xml'));
  const others = $derived((r?.links ?? []).filter((l) => l.type === 'other'));
  const shown = $derived({ ...item, ...(r ?? {}) } as VideoItem);
  let showOthers = $state(false);
</script>

<article class="card rc rise" class:empty={r && !am.length && !files.length}>
  <div class="head">
    <VideoThumb item={shown} />
    <div class="info">
      <a class="title" href={safeUrl(shown.url)} target="_blank" rel="noopener">{shown.title || '(tanpa judul)'}</a>
      <div class="meta">
        <span class="pf {shown.platform}"><Icon name={shown.platform} size={13} />{shown.platform === 'tiktok' ? 'TikTok' : 'YouTube'}</span>
        {#if shown.author}<span class="author">{shown.author}</span>{/if}
        {#if shown.views != null}<span><Icon name="eye" size={12} /> {fmtNum(shown.views)}</span>{/if}
        {#if shown.ts}<span>{timeAgo(shown.ts)}</span>{/if}
      </div>
      {#if !r}
        <div class="scanning"><span class="dot"></span>Lagi baca {shown.platform === 'youtube' ? 'deskripsi & komen' : 'caption, komen & balasan'}...</div>
      {:else if r.error}
        <div class="err"><Icon name="alert" size={14} />{r.error}</div>
      {:else}
        <div class="counts">
          {#if am.length}<span class="badge ok">{r.n_ok} preset aktif</span>{/if}
          {#if files.length}<span class="badge brand">{files.length} file</span>{/if}
          {#if !am.length && !files.length}<span class="badge">Gak ada link preset</span>{/if}
        </div>
      {/if}
    </div>
  </div>

  {#if am.length || files.length}
    <div class="links">
      {#each am as link (link.url)}
        <PresetLink {link} />
      {/each}
      {#each files as link (link.url)}
        <FileLink {link} />
      {/each}
    </div>
  {/if}

  {#if r && !am.length && !files.length && r.bio_hint && r.author_handle && onScanBio}
    <button class="hint" onclick={() => onScanBio(r.author_handle!)}>
      <Icon name="sparkle" size={14} />Caption nyebut "bio". Scan profil @{r.author_handle}
      <Icon name="chevron" size={14} />
    </button>
  {/if}

  {#if others.length}
    <button class="more" onclick={() => (showOthers = !showOthers)}>
      {showOthers ? 'Sembunyiin' : `${others.length} link lain dari creator`}
    </button>
    {#if showOthers}
      <div class="others">
        {#each others as o (o.url)}<a href={safeUrl(o.url)} target="_blank" rel="noopener" class="mono">{o.url}</a>{/each}
      </div>
    {/if}
  {/if}
</article>

<style>
  .rc {
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .rc.empty {
    opacity: 0.66;
  }
  .rc.empty:hover {
    opacity: 1;
  }
  .head {
    display: flex;
    gap: 14px;
    align-items: flex-start;
  }
  .info {
    min-width: 0;
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 7px;
  }
  .title {
    font-weight: 650;
    font-size: 14.5px;
    line-height: 1.35;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    word-break: break-word;
  }
  .title:hover {
    color: var(--text-2);
  }
  .meta {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 4px 10px;
    font-size: 12px;
    color: var(--muted);
  }
  .meta span {
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }
  .author {
    max-width: 180px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    display: inline-block !important;
  }
  .pf {
    font-weight: 700;
    font-size: 11.5px;
  }
  .pf.youtube {
    color: #ff8a84;
  }
  .pf.tiktok {
    color: var(--tt);
  }
  .counts {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
  }
  .scanning {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 12.5px;
    color: var(--muted);
  }
  .dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: var(--brand);
    animation: pulse 1s ease-in-out infinite;
  }
  @keyframes pulse {
    50% {
      opacity: 0.25;
      transform: scale(0.8);
    }
  }
  .err {
    display: flex;
    gap: 6px;
    align-items: flex-start;
    font-size: 12.5px;
    color: var(--bad);
  }
  .links {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .hint {
    display: flex;
    align-items: center;
    gap: 7px;
    width: 100%;
    padding: 9px 12px;
    border-radius: 11px;
    border: 1px solid rgba(251, 191, 90, 0.3);
    background: var(--warn-soft);
    color: var(--warn);
    font-size: 12.5px;
    font-weight: 600;
    text-align: left;
  }
  .hint :global(svg:last-child) {
    margin-left: auto;
  }
  .more {
    align-self: flex-start;
    background: none;
    border: 0;
    padding: 0;
    color: var(--muted);
    font-size: 12px;
    text-decoration: underline dotted;
  }
  .others {
    display: flex;
    flex-direction: column;
    gap: 3px;
  }
  .others a {
    font-size: 11.5px;
    color: var(--text-2);
    word-break: break-all;
  }
</style>
