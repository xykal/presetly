<script lang="ts">
  import Icon from './Icon.svelte';
  import { api } from './api';
  import { safeUrl } from './format';
  import { notify, ui } from './state.svelte';

  const t = $derived(ui.player);
  let src = $state<string | null>(null);
  let muted = $state(false);
  let failed = $state(false);
  let triedProxy = false;
  let downloading = $state(false);

  $effect(() => {
    const cur = ui.player;
    src = null;
    failed = false;
    triedProxy = false;
    if (!cur || cur.platform !== 'tiktok') return;
    if (cur.play) {
      src = cur.play;
      return;
    }
    let alive = true;
    api
      .ttMedia(cur.id)
      .then((m) => alive && (src = m.play || m.proxy))
      .catch(() => alive && (src = `/api/stream/tiktok/${cur.id}`));
    return () => {
      alive = false;
    };
  });

  $effect(() => {
    if (!ui.player) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && close();
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    window.addEventListener('keydown', onKey);
    return () => {
      window.removeEventListener('keydown', onKey);
      document.body.style.overflow = prev;
    };
  });

  function close() {
    ui.player = null;
  }

  function onErr() {
    if (!triedProxy && t) {
      triedProxy = true;
      src = `/api/stream/tiktok/${t.id}`;
    } else {
      failed = true;
    }
  }

  function download() {
    if (!t) return;
    downloading = true;
    const handle = (t.url.match(/@([\w.-]+)/) || [])[1] || 'tiktok';
    const a = document.createElement('a');
    a.href = t.platform === 'tiktok' ? `/api/stream/tiktok/${t.id}?dl=1&u=${encodeURIComponent(handle)}` : `/api/stream/youtube/${t.id}`;
    a.rel = 'noopener';
    a.click();
    setTimeout(() => (downloading = false), 2500);
    if (t.platform === 'youtube' && ui.health?.serverless) notify('Download YouTube cuma jalan di mode lokal (lihat README)', 'info', 4200);
  }
</script>

{#if t}
  <div class="backdrop" role="presentation" onclick={(e) => e.target === e.currentTarget && close()}>
    <div class="sheet" class:vertical={t.vertical ?? t.platform === 'tiktok'} role="dialog" aria-modal="true" aria-label="Preview video">
      <div class="stage">
        {#if t.platform === 'youtube'}
          <iframe
            src={`https://www.youtube-nocookie.com/embed/${t.id}?autoplay=1&rel=0&modestbranding=1&playsinline=1`}
            title={t.title ?? 'YouTube'}
            allow="autoplay; encrypted-media; picture-in-picture; fullscreen"
            allowfullscreen
          ></iframe>
        {:else if failed}
          <iframe
            src={`https://www.tiktok.com/player/v1/${t.id}?autoplay=1&loop=1&description=0&music_info=0&rel=0`}
            title={t.title ?? 'TikTok'}
            allow="autoplay; encrypted-media; fullscreen"
            allowfullscreen
          ></iframe>
        {:else if src}
          <!-- svelte-ignore a11y_media_has_caption -->
          <video {src} autoplay loop playsinline controls {muted} onerror={onErr}></video>
        {:else}
          <div class="loading"><span class="spin"></span></div>
        {/if}
      </div>
      <div class="bar">
        <div class="info">
          <div class="title">{t.title ?? ''}</div>
          {#if t.author}<div class="muted small">{t.author}</div>{/if}
        </div>
        <div class="acts">
          {#if t.platform === 'tiktok' && !failed}
            <button class="btn sm icon" aria-label={muted ? 'Nyalain suara' : 'Mute'} onclick={() => (muted = !muted)}>
              <Icon name={muted ? 'mute' : 'volume'} size={15} />
            </button>
          {/if}
          <button class="btn sm" onclick={download} disabled={downloading}>
            <Icon name="download" size={15} />{downloading ? 'Nyiapin...' : 'Download'}
          </button>
          <a class="btn sm icon" href={safeUrl(t.url)} target="_blank" rel="noopener" aria-label="Buka di aplikasi" title="Buka di {t.platform === 'tiktok' ? 'TikTok' : 'YouTube'}">
            <Icon name="external" size={15} />
          </a>
        </div>
      </div>
      <button class="close" aria-label="Tutup" onclick={close}><Icon name="x" size={20} /></button>
    </div>
  </div>
{/if}

<style>
  .backdrop {
    position: fixed;
    inset: 0;
    z-index: 80;
    background: rgba(4, 3, 8, 0.86);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    display: grid;
    place-items: center;
    padding: 14px;
    animation: fade 0.2s var(--ease) both;
  }
  @keyframes fade {
    from {
      opacity: 0;
    }
  }
  .sheet {
    position: relative;
    width: min(94vw, 880px);
    background: var(--surface);
    border: 1px solid var(--line-2);
    border-radius: 20px;
    overflow: hidden;
    box-shadow: 0 30px 80px -20px rgba(0, 0, 0, 0.8);
    animation: pop 0.28s var(--ease) both;
  }
  .sheet.vertical {
    width: min(94vw, 400px);
  }
  @keyframes pop {
    from {
      opacity: 0;
      transform: translateY(16px) scale(0.98);
    }
  }
  .stage {
    position: relative;
    background: #000;
    aspect-ratio: 16 / 9;
  }
  .vertical .stage {
    aspect-ratio: 9 / 16;
    max-height: calc(100dvh - 150px);
    margin: 0 auto;
  }
  .stage iframe,
  .stage video {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    border: 0;
    object-fit: contain;
    background: #000;
  }
  .loading {
    position: absolute;
    inset: 0;
    display: grid;
    place-items: center;
  }
  .spin {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    border: 3px solid rgba(255, 255, 255, 0.15);
    border-top-color: var(--brand);
    animation: spin 0.8s linear infinite;
  }
  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
  .bar {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 11px 12px;
  }
  .info {
    min-width: 0;
    flex: 1;
  }
  .title {
    font-size: 13.5px;
    font-weight: 600;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .small {
    font-size: 12px;
  }
  .acts {
    display: flex;
    gap: 6px;
  }
  .close {
    position: absolute;
    top: 10px;
    right: 10px;
    width: 36px;
    height: 36px;
    border-radius: 50%;
    border: 0;
    display: grid;
    place-items: center;
    background: rgba(7, 6, 11, 0.6);
    backdrop-filter: blur(8px);
    color: #fff;
    z-index: 2;
  }
</style>
