<script lang="ts">
  import CariView from './lib/CariView.svelte';
  import Footer from './lib/Footer.svelte';
  import Icon from './lib/Icon.svelte';
  import JelajahView from './lib/JelajahView.svelte';
  import KoleksiView from './lib/KoleksiView.svelte';
  import PlayerModal from './lib/PlayerModal.svelte';
  import QrModal from './lib/QrModal.svelte';
  import Toast from './lib/Toast.svelte';
  import XyverseMark from './lib/XyverseMark.svelte';
  import { loadHealth, ui, type Tab } from './lib/state.svelte';

  const TABS: { id: Tab; label: string; icon: string }[] = [
    { id: 'cari', label: 'Cari', icon: 'search' },
    { id: 'jelajah', label: 'Jelajah', icon: 'compass' },
    { id: 'koleksi', label: 'Koleksi', icon: 'bookmark' },
  ];

  function go(t: Tab) {
    ui.tab = t;
    history.replaceState(null, '', t === 'cari' ? '/' : `#${t}`);
    window.scrollTo({ top: 0 });
  }

  $effect(() => {
    const h = location.hash.slice(1) as Tab;
    if (TABS.some((t) => t.id === h)) ui.tab = h;
    loadHealth();
  });
</script>

<header>
  <div class="container bar">
    <a class="brand" href="/" onclick={(e) => { e.preventDefault(); go('cari'); }}>
      <img src="/favicon.svg" alt="" width="32" height="32" />
      <div class="bt">
        <b>AM Preset Finder</b>
        <span><XyverseMark size={10} />Built-in XyVerse</span>
      </div>
    </a>
    <nav class="top" aria-label="Menu">
      {#each TABS as t (t.id)}
        <button class:on={ui.tab === t.id} onclick={() => go(t.id)} aria-current={ui.tab === t.id ? 'page' : undefined}>
          <Icon name={t.icon} size={16} />{t.label}
        </button>
      {/each}
    </nav>
  </div>
</header>

<main class="container">
  {#if ui.tab === 'cari'}
    <CariView />
  {:else if ui.tab === 'jelajah'}
    <JelajahView />
  {:else}
    <KoleksiView />
  {/if}
</main>

<Footer />

<nav class="dock" aria-label="Menu bawah">
  {#each TABS as t (t.id)}
    <button class:on={ui.tab === t.id} onclick={() => go(t.id)} aria-current={ui.tab === t.id ? 'page' : undefined}>
      <Icon name={t.icon} size={20} /><span>{t.label}</span>
    </button>
  {/each}
</nav>

<PlayerModal />
<QrModal />
<Toast />

<style>
  header {
    position: sticky;
    top: 0;
    z-index: 30;
    background: rgba(7, 6, 11, 0.78);
    backdrop-filter: blur(16px) saturate(1.4);
    -webkit-backdrop-filter: blur(16px) saturate(1.4);
    border-bottom: 1px solid var(--line);
  }
  .bar {
    height: 62px;
    display: flex;
    align-items: center;
    gap: 16px;
  }
  .brand {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .brand img {
    border-radius: 10px;
  }
  .bt {
    display: flex;
    flex-direction: column;
    line-height: 1.2;
  }
  .bt b {
    font-size: 15px;
    letter-spacing: -0.01em;
  }
  .bt span {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    font-size: 10.5px;
    color: var(--muted);
    font-weight: 600;
    letter-spacing: 0.02em;
  }
  nav.top {
    margin-left: auto;
    display: flex;
    gap: 4px;
  }
  nav.top button {
    display: flex;
    align-items: center;
    gap: 7px;
    height: 38px;
    padding: 0 14px;
    border-radius: 11px;
    border: 1px solid transparent;
    background: none;
    color: var(--muted);
    font-weight: 600;
    font-size: 14px;
  }
  nav.top button:hover {
    color: var(--text);
  }
  nav.top button.on {
    color: var(--text);
    background: var(--surface-2);
    border-color: var(--line-2);
  }
  main {
    padding-top: 18px;
  }
  .dock {
    display: none;
  }
  @media (max-width: 899px) {
    nav.top {
      display: none;
    }
    .bar {
      height: 56px;
    }
    .dock {
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      position: fixed;
      left: 12px;
      right: 12px;
      bottom: calc(10px + var(--safe-b));
      z-index: 40;
      height: 62px;
      padding: 6px;
      border-radius: 20px;
      background: rgba(18, 16, 28, 0.9);
      backdrop-filter: blur(18px) saturate(1.4);
      -webkit-backdrop-filter: blur(18px) saturate(1.4);
      border: 1px solid var(--line-2);
      box-shadow: 0 16px 40px -12px rgba(0, 0, 0, 0.7);
    }
    .dock button {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 3px;
      border: 0;
      border-radius: 14px;
      background: none;
      color: var(--faint);
      font-size: 11px;
      font-weight: 650;
    }
    .dock button.on {
      color: var(--text);
      background: var(--surface-3);
    }
    .dock button.on :global(svg) {
      color: var(--brand);
    }
  }
</style>
