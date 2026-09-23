<script lang="ts">
  import Icon from './Icon.svelte';
  import { safeUrl } from './format';
  import { copyText, ui } from './state.svelte';

  $effect(() => {
    if (!ui.qr) return;
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && (ui.qr = null);
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  });
</script>

{#if ui.qr}
  <div class="backdrop" role="presentation" onclick={(e) => e.target === e.currentTarget && (ui.qr = null)}>
    <div class="box" role="dialog" aria-modal="true" aria-label="QR code preset">
      <button class="close" aria-label="Tutup" onclick={() => (ui.qr = null)}><Icon name="x" size={18} /></button>
      <div class="name">{ui.qr.name || 'Preset Alight Motion'}</div>
      <div class="qr"><img src={`/api/qr?d=${encodeURIComponent(ui.qr.url)}`} alt="QR code" width="232" height="232" /></div>
      <p class="muted">Scan pakai kamera HP, preset langsung kebuka di Alight Motion.</p>
      <div class="url mono">{ui.qr.url.replace(/^https?:\/\//, '')}</div>
      <div class="acts">
        <button class="btn sm" onclick={() => ui.qr && copyText(ui.qr.url)}><Icon name="copy" size={15} />Copy link</button>
        <a class="btn sm primary" href={safeUrl(ui.qr.url)} target="_blank" rel="noopener">Buka link</a>
      </div>
    </div>
  </div>
{/if}

<style>
  .backdrop {
    position: fixed;
    inset: 0;
    z-index: 85;
    background: rgba(4, 3, 8, 0.82);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    display: grid;
    place-items: center;
    padding: 16px;
  }
  .box {
    position: relative;
    width: min(92vw, 340px);
    padding: 22px 20px 18px;
    text-align: center;
    background: var(--surface);
    border: 1px solid var(--line-2);
    border-radius: 22px;
    animation: pop 0.25s var(--ease) both;
  }
  @keyframes pop {
    from {
      opacity: 0;
      transform: scale(0.96);
    }
  }
  .name {
    font-weight: 700;
    padding: 0 24px;
  }
  .qr {
    margin: 14px auto 10px;
    width: 248px;
    height: 248px;
    padding: 8px;
    border-radius: 16px;
    background: #fff;
  }
  .qr img {
    width: 100%;
    height: 100%;
  }
  p {
    margin: 0;
    font-size: 12.5px;
  }
  .url {
    margin: 8px 0 14px;
    font-size: 11px;
    color: var(--faint);
    word-break: break-all;
  }
  .acts {
    display: flex;
    gap: 8px;
    justify-content: center;
  }
  .close {
    position: absolute;
    top: 10px;
    right: 10px;
    width: 32px;
    height: 32px;
    border: 0;
    border-radius: 50%;
    background: var(--surface-2);
    color: var(--muted);
    display: grid;
    place-items: center;
  }
</style>
