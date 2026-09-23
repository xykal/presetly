<script lang="ts">
  import Icon from './Icon.svelte';
  import { CROWD_SOURCES, isFree, isMobile, safeUrl, SRC_LABEL } from './format';
  import { copyText, ui } from './state.svelte';
  import type { FoundLink } from './types';

  let { link, compact = false }: { link: FoundLink; compact?: boolean } = $props();

  const info = $derived(link.info ?? {});
  const url = $derived(info.fixed_url || link.url);
  const status = $derived(info.status);
  const free = $derived(isFree(info.size_mb));
  const crowd = $derived(CROWD_SOURCES.has(link.source));

  function open(e: MouseEvent) {
    // Di PC link alight.link cuma buka Play Store -> kasih QR biar discan pakai HP.
    if (!isMobile()) {
      e.preventDefault();
      ui.qr = { url, name: info.name };
    }
  }
</script>

<div class="am" class:dead={status === 'dead'} class:compact>
  <div class="thumb">
    {#if info.thumb}
      <img src={info.thumb} alt="" loading="lazy" referrerpolicy="no-referrer" />
    {:else}
      <Icon name="sparkle" size={20} />
    {/if}
  </div>
  <div class="body">
    <div class="name">{info.name || 'Preset Alight Motion'}{#if info.projects && info.projects > 1}<span class="muted"> · {info.projects} project</span>{/if}</div>
    <div class="meta">
      {#if status === 'ok'}
        {#if info.size_text}<span class="size">{info.size_text}</span>{/if}
        {#if free === true}<span class="badge ok">AM gratis bisa</span>{:else if free === false}<span class="badge warn">Butuh premium</span>{/if}
      {:else if status === 'dead'}
        <span class="badge bad">Link mati</span>
      {:else if status === 'error'}
        <span class="badge">Gagal dicek</span>
      {/if}
      <span class="src" class:crowd title={crowd ? 'Dari komentar penonton, cek dulu sebelum dipake' : ''}>
        {crowd ? 'dari ' : 'via '}{SRC_LABEL[link.source] ?? link.source}
      </span>
    </div>
    {#if !compact}<div class="url mono">{url.replace(/^https?:\/\//, '')}</div>{/if}
  </div>
  {#if status !== 'dead'}
    <div class="actions">
      <a class="btn sm primary" href={safeUrl(url)} target="_blank" rel="noopener" onclick={open}>Buka di AM</a>
      <button class="btn sm icon" title="Copy link" aria-label="Copy link" onclick={() => copyText(url)}><Icon name="copy" size={15} /></button>
      <button class="btn sm icon" title="QR code" aria-label="QR code" onclick={() => (ui.qr = { url, name: info.name })}><Icon name="qr" size={15} /></button>
    </div>
  {/if}
</div>

<style>
  .am {
    display: grid;
    grid-template-columns: 52px 1fr auto;
    gap: 12px;
    align-items: center;
    padding: 10px;
    border-radius: 14px;
    background: var(--bg-1);
    border: 1px solid var(--line);
    position: relative;
  }
  .am::before {
    content: '';
    position: absolute;
    left: 0;
    top: 12px;
    bottom: 12px;
    width: 3px;
    border-radius: 0 3px 3px 0;
    background: linear-gradient(var(--brand), var(--cyan));
  }
  .am.dead {
    opacity: 0.55;
  }
  .am.dead::before {
    background: var(--bad);
  }
  .thumb {
    width: 52px;
    height: 52px;
    border-radius: 11px;
    overflow: hidden;
    background: var(--surface-2);
    display: grid;
    place-items: center;
    color: var(--brand);
  }
  .thumb img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
  .body {
    min-width: 0;
  }
  .name {
    font-weight: 650;
    font-size: 14px;
    line-height: 1.3;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .meta {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 5px 7px;
    margin-top: 4px;
    font-size: 12px;
  }
  .size {
    font-weight: 700;
    color: var(--text);
  }
  .src {
    color: var(--faint);
  }
  .src.crowd {
    color: var(--warn);
  }
  .url {
    margin-top: 3px;
    font-size: 11px;
    color: var(--faint);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .actions {
    display: flex;
    gap: 6px;
  }
  @media (max-width: 560px) {
    .am {
      grid-template-columns: 46px 1fr;
      gap: 10px;
    }
    .thumb {
      width: 46px;
      height: 46px;
    }
    .actions {
      grid-column: 1 / -1;
    }
    .actions .primary {
      flex: 1;
    }
  }
  .compact {
    grid-template-columns: 44px 1fr auto;
  }
  .compact .thumb {
    width: 44px;
    height: 44px;
  }
</style>
