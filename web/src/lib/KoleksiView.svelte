<script lang="ts">
  import Icon from './Icon.svelte';
  import PresetCard from './PresetCard.svelte';
  import { FREE_MB } from './format';
  import { ui } from './state.svelte';
  import { saved } from './storage';
  import type { Preset } from './types';

  let items = $state<Preset[]>(saved.all());
  let q = $state('');
  let onlyFree = $state(false);

  const list = $derived(
    items.filter((p) => {
      if (onlyFree && !((p.size_mb ?? 99) <= FREE_MB)) return false;
      const needle = q.trim().toLowerCase();
      return !needle || (p.name ?? '').toLowerCase().includes(needle) || (p.sources ?? []).some((s) => `${s.author} ${s.author_handle}`.toLowerCase().includes(needle));
    }),
  );

  function exportTxt() {
    const txt = items.map((p) => `${p.name ?? 'Preset'}${p.size_text ? ` (${p.size_text})` : ''}\n${p.am_url}`).join('\n\n');
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([txt], { type: 'text/plain' }));
    a.download = 'koleksi-preset-am.txt';
    a.click();
  }
</script>

<section class="koleksi">
  <div class="hero">
    <h1>Koleksi</h1>
    <p class="muted">Preset yang lu simpen (ikon bookmark di tab Jelajah). Disimpen di browser ini aja, gak perlu login.</p>
  </div>

  {#if items.length}
    <div class="toolbar">
      <div class="field">
        <Icon name="search" size={15} class="lead" />
        <input class="input" bind:value={q} placeholder="Cari di koleksi" aria-label="Cari di koleksi" />
      </div>
      <button class="chip" class:on={onlyFree} onclick={() => (onlyFree = !onlyFree)}>≤ 5MB</button>
      <div class="spacer"></div>
      <button class="btn sm" onclick={exportTxt}><Icon name="download" size={14} />Export .txt</button>
    </div>
    <div class="grid">
      {#each list as p (p.key)}
        <PresetCard preset={p} onRemove={(k) => (items = items.filter((x) => x.key !== k))} />
      {/each}
    </div>
  {:else}
    <div class="empty card">
      <Icon name="bookmark" size={26} />
      <div><b>Koleksi masih kosong.</b><br />Buka tab Jelajah, terus pencet ikon bookmark di preset yang lu suka.</div>
      <button class="btn sm primary" onclick={() => (ui.tab = 'jelajah')}><Icon name="compass" size={14} />Ke Jelajah</button>
    </div>
  {/if}
</section>

<style>
  .koleksi {
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
  }
  .toolbar {
    display: flex;
    gap: 8px;
    align-items: center;
    flex-wrap: wrap;
  }
  .field {
    position: relative;
    flex: 1 1 200px;
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
  .spacer {
    flex: 1;
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
  }
  .empty {
    padding: 34px 16px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    text-align: center;
    color: var(--muted);
  }
</style>
