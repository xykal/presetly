<script lang="ts">
  /*
   * Thumbnail yang bisa langsung jadi preview:
   *  - TikTok: hover (desktop) / tap ikon play -> <video> muted autoplay loop inline.
   *    URL mp4 diambil dari item.play (embed) atau /api/media/tiktok/:id kalau belum ada / expired.
   *  - YouTube: klik -> buka player modal (iframe embed resmi).
   */
  import Icon from './Icon.svelte';
  import { api } from './api';
  import { fmtDur } from './format';
  import { openPlayer } from './state.svelte';
  import type { VideoItem } from './types';

  let { item, size = 'md' }: { item: VideoItem; size?: 'md' | 'lg' } = $props();

  let hovering = $state(false);
  let playing = $state(false);
  let src = $state<string | null>(null);
  let thumb = $state<string | null>(null);
  let failedThumb = $state(false);
  let videoEl = $state<HTMLVideoElement | null>(null);
  let loadingSrc = $state(false);
  // Rantai fallback: 0 = item.play (sering expired), 1 = play segar dari server, 2 = proxy server.
  let stage = 0;

  $effect(() => {
    thumb = item.thumb ?? null;
    src = item.play ?? null;
    failedThumb = false;
    stage = 0;
  });

  const isTT = $derived(item.platform === 'tiktok' || item.platform === 'instagram');
  const vertical = $derived(item.vertical ?? item.platform !== 'youtube');

  async function ensureSrc(): Promise<string | null> {
    if (src) return src;
    if (!isTT || loadingSrc) return null;
    loadingSrc = true;
    try {
      const m = await api.mediaOf(item.platform, item.id);
      src = m.play || m.proxy;
      stage = m.play ? 1 : 2;
      if (m.thumb && failedThumb) {
        thumb = m.thumb;
        failedThumb = false;
      }
    } catch {
      src = `/api/stream/${item.platform}/${item.id}`;
      stage = 2;
    } finally {
      loadingSrc = false;
    }
    return src;
  }

  async function startInline() {
    if (!isTT) return;
    await ensureSrc();
    playing = true;
  }

  function stopInline() {
    playing = false;
    videoEl?.pause();
  }

  function onVideoError() {
    // URL CDN sering expired / diblok -> naikin satu tingkat ke sumber berikutnya.
    if (!isTT) return;
    if (stage === 0) {
      stage = 1;
      api
        .mediaOf(item.platform, item.id)
        .then((m) => (src = m.play || m.proxy))
        .catch(() => {
          stage = 2;
          src = `/api/stream/${item.platform}/${item.id}`;
        });
    } else if (stage === 1) {
      stage = 2;
      src = `/api/stream/${item.platform}/${item.id}`;
    } else {
      playing = false;
    }
  }

  async function onThumbError() {
    if (failedThumb) return;
    failedThumb = true;
    if (isTT) thumb = `/api/thumb/${item.platform}/${item.id}`;
  }

  function openFull() {
    stopInline();
    openPlayer({
      platform: item.platform, id: item.id, title: item.title, author: item.author, url: item.url,
      vertical, play: src ?? item.play ?? null, thumb: thumb ?? item.thumb ?? null,
    });
  }
</script>

<div
  class="vt {size}"
  class:vertical
  role="group"
  onmouseenter={() => {
    hovering = true;
    if (matchMedia('(hover: hover)').matches) startInline();
  }}
  onmouseleave={() => {
    hovering = false;
    stopInline();
  }}
>
  {#if thumb && !(failedThumb && !isTT)}
    <img class="poster" src={thumb} alt="" loading="lazy" referrerpolicy="no-referrer" onerror={onThumbError} />
  {:else}
    <div class="poster ph"><Icon name={isTT ? 'tiktok' : 'youtube'} size={26} /></div>
  {/if}

  {#if playing && src}
    <!-- svelte-ignore a11y_media_has_caption -->
    <video
      bind:this={videoEl}
      {src}
      autoplay
      muted
      loop
      playsinline
      preload="auto"
      onerror={onVideoError}
    ></video>
  {/if}

  <button class="hit" aria-label="Putar preview {item.title ?? ''}" onclick={openFull}></button>

  <div class="overlay">
    {#if isTT}
      <button
        class="pill play"
        aria-label={playing ? 'Stop preview' : 'Preview cepat'}
        onclick={(e) => {
          e.stopPropagation();
          if (playing) stopInline();
          else startInline();
        }}
      >
        {#if loadingSrc}<span class="spin"></span>{:else}<Icon name={playing ? 'pause' : 'play'} size={12} />{/if}
        {playing ? 'Preview' : 'Putar'}
      </button>
    {:else}
      <span class="pill play"><Icon name="play" size={12} /> Tonton</span>
    {/if}
    {#if item.duration}<span class="pill dur">{fmtDur(item.duration)}</span>{/if}
  </div>
  {#if !playing && !hovering}
    <div class="center"><Icon name="play" size={20} /></div>
  {/if}
</div>

<style>
  .vt {
    position: relative;
    overflow: hidden;
    border-radius: 14px;
    background: var(--surface-2);
    flex: none;
    width: 168px;
    aspect-ratio: 16 / 9;
    isolation: isolate;
  }
  .vt.vertical {
    width: 112px;
    aspect-ratio: 9 / 16;
  }
  .vt.lg {
    width: 100%;
  }
  .vt.lg.vertical {
    width: 100%;
  }
  .poster,
  video {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
  video {
    z-index: 1;
    background: #000;
  }
  .ph {
    display: grid;
    place-items: center;
    color: var(--faint);
  }
  .hit {
    position: absolute;
    inset: 0;
    z-index: 2;
    background: transparent;
    border: 0;
  }
  .overlay {
    position: absolute;
    left: 6px;
    right: 6px;
    bottom: 6px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    z-index: 3;
    pointer-events: none;
  }
  .pill {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    height: 22px;
    padding: 0 7px;
    border-radius: 7px;
    background: rgba(7, 6, 11, 0.72);
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    font-size: 10.5px;
    font-weight: 700;
    color: #fff;
    border: 0;
  }
  button.pill {
    pointer-events: auto;
  }
  .center {
    position: absolute;
    inset: 0;
    display: grid;
    place-items: center;
    z-index: 1;
    pointer-events: none;
    color: #fff;
    opacity: 0;
    transition: opacity 0.2s var(--ease);
  }
  .center :global(svg) {
    width: 42px;
    height: 42px;
    padding: 11px;
    border-radius: 50%;
    background: rgba(7, 6, 11, 0.55);
    backdrop-filter: blur(6px);
  }
  .vt:hover .center {
    opacity: 1;
  }
  .spin {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-top-color: #fff;
    animation: spin 0.7s linear infinite;
  }
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
  @media (max-width: 560px) {
    .vt {
      width: 128px;
    }
    .vt.vertical {
      width: 92px;
    }
  }
</style>
