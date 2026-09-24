<script lang="ts">
  import Icon from './Icon.svelte';
  import PresetCard from './PresetCard.svelte';
  import { FREE_MB } from './format';
  import { disablePush, enablePush, loadPush, setCreators } from './notify';
  import { notify, ui } from './state.svelte';
  import { saved } from './storage';
  import type { Preset } from './types';

  let items = $state<Preset[]>(saved.all());
  let q = $state('');
  let onlyFree = $state(false);

  // --- notifikasi preset baru ---
  let pushOn = $state(false);
  let creators = $state<string[]>([]);
  let newCreator = $state('');
  let pushBusy = $state(false);

  $effect(() => {
    const s = loadPush();
    pushOn = s.on;
    creators = s.creators;
  });

  async function togglePush() {
    pushBusy = true;
    try {
      if (pushOn) {
        await disablePush();
        pushOn = false;
        notify('Notifikasi dimatikan', 'info');
      } else {
        await enablePush(creators);
        pushOn = true;
        notify('Notifikasi preset baru AKTIF 🔔', 'ok');
      }
    } catch (e) {
      notify(e instanceof Error ? e.message : 'Gagal nyalain notifikasi', 'bad');
    } finally {
      pushBusy = false;
    }
  }

  function addCreator() {
    let c = newCreator.trim().toLowerCase().replace(/^@/, '');
    if (!c) return;
    if (!c.includes(':')) c = 'tiktok:' + c;
    const [pf, handle] = c.split(':');
    if (!['youtube', 'yt', 'tiktok', 'tt', 'instagram', 'ig'].includes(pf) || !handle) {
      notify('Format: youtube:@user / tiktok:user / instagram:user', 'bad');
      return;
    }
    if (creators.includes(c)) {
      notify('Udah dipantau', 'info');
      return;
    }
    const next = [...creators, c];
    creators = next;
    newCreator = '';
    setCreators(next).catch(() => {});
  }

  async function removeCreator(c: string) {
    const next = creators.filter((x) => x !== c);
    creators = next;
    try {
      await setCreators(next);
    } catch {
      /* ignore */
    }
  }

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

  <section class="notif card">
    <div class="nrow">
      <Icon name="sparkle" size={18} />
      <div class="ntxt">
        <b>Notifikasi preset baru</b>
        <span class="muted">Dikabari pas creator favorit posting (dicek berkala). Tanpa login.</span>
      </div>
      <button class="btn sm {pushOn ? 'primary' : ''}" disabled={pushBusy} onclick={togglePush}>
        {pushOn ? 'Aktif 🔔' : 'Nyalain'}
      </button>
    </div>
    <div class="pantau">
      <div class="field">
        <Icon name="user" size={15} class="lead" />
        <input
          class="input"
          bind:value={newCreator}
          placeholder="youtube:@user / tiktok:user / instagram:user"
          aria-label="Creator yang dipantau"
          onkeydown={(e) => e.key === 'Enter' && (e.preventDefault(), addCreator())}
        />
      </div>
      <button class="btn sm" onclick={addCreator}><Icon name="bookmark" size={14} />Pantau</button>
    </div>
    {#if creators.length}
      <div class="clist">
        {#each creators as c (c)}
          <span class="chip on">{c}<button class="x" aria-label="Berhenti pantau {c}" onclick={() => removeCreator(c)}><Icon name="x" size={11} /></button></span>
        {/each}
      </div>
    {/if}
  </section>

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
  .notif {
    margin-bottom: 14px;
    padding: 14px;
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  .nrow {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .ntxt {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
  }
  .ntxt b {
    font-size: 14px;
  }
  .ntxt .muted {
    font-size: 12px;
  }
  .pantau {
    display: flex;
    gap: 8px;
  }
  .pantau .field {
    flex: 1;
  }
  .clist {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }
  .clist .chip {
    gap: 6px;
    padding-right: 6px;
  }
  .clist .x {
    border: 0;
    background: none;
    color: inherit;
    display: grid;
    place-items: center;
    padding: 2px;
    border-radius: 50%;
  }
  .clist .x:hover {
    background: rgba(255, 255, 255, 0.15);
  }
</style>
