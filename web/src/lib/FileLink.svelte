<script lang="ts">
  import Icon from './Icon.svelte';
  import { CROWD_SOURCES, hostOf, KIND_LABEL, safeUrl, SRC_LABEL } from './format';
  import { copyText } from './state.svelte';
  import type { FoundLink } from './types';

  let { link }: { link: FoundLink } = $props();
  const info = $derived(link.info ?? {});
  const kind = $derived(link.kind ?? 'file');
  const icon = $derived(({ folder: 'folder', sound: 'music', zip: 'zip' } as Record<string, string>)[kind] ?? 'file');
</script>

<div class="file">
  <span class="ic k-{kind}"><Icon name={icon} size={17} /></span>
  <div class="body">
    <div class="name">{info.name || `${KIND_LABEL[kind]} di ${hostOf(link.url)}`}</div>
    <div class="meta">
      <span class="badge brand">{KIND_LABEL[kind]}</span>
      <span>{hostOf(link.url)}</span>
      {#if info.status === 'private'}<span class="badge bad">Privat</span>{/if}
      {#if info.status === 'dead'}<span class="badge bad">Mati</span>{/if}
      <span class:crowd={CROWD_SOURCES.has(link.source)}>via {SRC_LABEL[link.source] ?? link.source}</span>
    </div>
  </div>
  <a class="btn sm" href={safeUrl(link.url)} target="_blank" rel="noopener">Buka</a>
  <button class="btn sm icon" aria-label="Copy link" title="Copy link" onclick={() => copyText(link.url)}><Icon name="copy" size={15} /></button>
</div>

<style>
  .file {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 8px 10px;
    border-radius: 12px;
    border: 1px dashed var(--line-2);
  }
  .ic {
    width: 34px;
    height: 34px;
    border-radius: 9px;
    display: grid;
    place-items: center;
    background: var(--surface-2);
    color: var(--text-2);
    flex: none;
  }
  .ic.k-xml {
    color: var(--cyan);
  }
  .ic.k-sound {
    color: var(--pink);
  }
  .body {
    min-width: 0;
    flex: 1;
  }
  .name {
    font-size: 13px;
    font-weight: 600;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
  .meta {
    display: flex;
    flex-wrap: wrap;
    gap: 4px 7px;
    align-items: center;
    font-size: 11.5px;
    color: var(--faint);
    margin-top: 2px;
  }
  .crowd {
    color: var(--warn);
  }
</style>
