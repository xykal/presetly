<script lang="ts">
  import Icon from './Icon.svelte';
  import { fmtNum, isFree, isMobile, safeUrl, timeAgo } from './format';
  import { copyText, notify, openPlayer, ui } from './state.svelte';
  import { saved } from './storage';
  import type { Preset } from './types';

  let { preset, onRemove }: { preset: Preset; onRemove?: (key: string) => void } = $props();

  let isSaved = $state(false);
  $effect(() => {
    isSaved = saved.has(preset.key);
  });
  const src = $derived(preset.sources?.[0]);
  const free = $derived(isFree(preset.size_mb));
  const xml = $derived([...new Set((preset.sources ?? []).flatMap((s) => s.xml ?? []))]);

  function toggleSave() {
    isSaved = saved.toggle(preset);
    notify(isSaved ? 'Disimpen ke Koleksi' : 'Dihapus dari Koleksi', isSaved ? 'ok' : 'info');
    if (!isSaved) onRemove?.(preset.key);
  }

  function open(e: MouseEvent) {
    if (!isMobile()) {
      e.preventDefault();
      ui.qr = { url: preset.am_url, name: preset.name };
    }
  }

  function play() {
    if (!src) return;
    openPlayer({ platform: src.platform, id: src.id, title: src.title, author: src.author, url: src.video_url, vertical: src.vertical ?? src.platform === 'tiktok' });
  }
</script>

<article class="pc card rise">
  <div class="art">
    {#if preset.thumb}
      <img src={preset.thumb} alt="" loading="lazy" referrerpolicy="no-referrer" />
    {:else}
      <div class="ph"><Icon name="sparkle" size={30} /></div>
    {/if}
    <div class="tags">
      {#if free === true}<span class="badge ok">AM gratis</span>{:else if free === false}<span class="badge warn">Premium</span>{/if}
    </div>
    <button class="save" class:on={isSaved} aria-label={isSaved ? 'Hapus dari koleksi' : 'Simpan ke koleksi'} onclick={toggleSave}>
      <Icon name={isSaved ? 'bookmarkFill' : 'bookmark'} size={16} />
    </button>
    {#if src}
      <button class="watch" onclick={play}><Icon name="play" size={12} />Lihat video</button>
    {/if}
  </div>
  <div class="body">
    <div class="name" title={preset.name ?? ''}>{preset.name || 'Preset Alight Motion'}</div>
    <div class="meta">
      {#if preset.size_text}<b>{preset.size_text}</b>{/if}
      {#if preset.projects && preset.projects > 1}<span>{preset.projects} project</span>{/if}
      {#if preset.last_seen}<span>{timeAgo(preset.last_seen)}</span>{/if}
    </div>
    {#if src}
      <a class="src" href={safeUrl(src.video_url)} target="_blank" rel="noopener">
        <Icon name={src.platform} size={12} />
        <span>{src.author || src.author_handle || 'creator'}</span>
        {#if src.views}<span class="muted">· {fmtNum(src.views)}</span>{/if}
      </a>
    {/if}
    <div class="acts">
      <a class="btn sm primary grow" href={safeUrl(preset.am_url)} target="_blank" rel="noopener" onclick={open}>Buka di AM</a>
      <button class="btn sm icon" aria-label="Copy link" title="Copy link" onclick={() => copyText(preset.am_url)}><Icon name="copy" size={15} /></button>
      <button class="btn sm icon" aria-label="QR" title="QR code" onclick={() => (ui.qr = { url: preset.am_url, name: preset.name })}><Icon name="qr" size={15} /></button>
    </div>
    {#if xml.length}
      <div class="xml">
        {#each xml.slice(0, 2) as x, i (x)}
          <a href={safeUrl(x)} target="_blank" rel="noopener"><Icon name="file" size={12} />XML {xml.length > 1 ? i + 1 : ''}</a>
        {/each}
      </div>
    {/if}
  </div>
</article>

<style>
  .pc {
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }
  .art {
    position: relative;
    aspect-ratio: 1;
    background: var(--surface-2);
  }
  .art img,
  .ph {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
  .ph {
    display: grid;
    place-items: center;
    color: var(--brand);
    background: radial-gradient(circle at 30% 20%, rgba(167, 139, 218, 0.25), transparent 60%), var(--surface-2);
  }
  .tags {
    position: absolute;
    top: 8px;
    left: 8px;
    display: flex;
    gap: 5px;
  }
  .tags .badge {
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    background: rgba(7, 6, 11, 0.7);
  }
  .save {
    position: absolute;
    top: 8px;
    right: 8px;
    width: 32px;
    height: 32px;
    border-radius: 10px;
    border: 0;
    display: grid;
    place-items: center;
    background: rgba(7, 6, 11, 0.62);
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    color: #fff;
  }
  .save.on {
    color: var(--brand);
  }
  .watch {
    position: absolute;
    bottom: 8px;
    left: 8px;
    display: inline-flex;
    align-items: center;
    gap: 5px;
    height: 26px;
    padding: 0 9px;
    border-radius: 8px;
    border: 0;
    background: rgba(7, 6, 11, 0.7);
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    color: #fff;
    font-size: 11.5px;
    font-weight: 700;
  }
  .body {
    padding: 11px;
    display: flex;
    flex-direction: column;
    gap: 6px;
    flex: 1;
  }
  .name {
    font-weight: 650;
    font-size: 13.5px;
    line-height: 1.3;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    word-break: break-word;
  }
  .meta {
    display: flex;
    flex-wrap: wrap;
    gap: 3px 8px;
    font-size: 11.5px;
    color: var(--muted);
  }
  .meta b {
    color: var(--text);
  }
  .src {
    display: flex;
    align-items: center;
    gap: 5px;
    font-size: 11.5px;
    color: var(--text-2);
    min-width: 0;
  }
  .src span:first-of-type {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .acts {
    display: flex;
    gap: 6px;
    margin-top: auto;
    padding-top: 4px;
  }
  .grow {
    flex: 1;
  }
  .xml {
    display: flex;
    gap: 10px;
  }
  .xml a {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 11.5px;
    color: var(--cyan);
  }
</style>
