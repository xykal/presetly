<script lang="ts">
  import Icon from './Icon.svelte';
  import { toast } from './state.svelte';
</script>

<div class="wrap" aria-live="polite">
  {#if toast.msg}
    {#key toast.seq}
      <div class="toast {toast.tone}" role="status">
        <Icon name={toast.tone === 'bad' ? 'alert' : toast.tone === 'ok' ? 'check' : 'info'} size={16} />
        <span>{toast.msg}</span>
      </div>
    {/key}
  {/if}
</div>

<style>
  .wrap {
    position: fixed;
    left: 0;
    right: 0;
    bottom: calc(84px + var(--safe-b));
    display: flex;
    justify-content: center;
    pointer-events: none;
    z-index: 90;
    padding: 0 16px;
  }
  @media (min-width: 900px) {
    .wrap {
      bottom: 28px;
    }
  }
  .toast {
    display: flex;
    align-items: center;
    gap: 9px;
    max-width: 520px;
    padding: 11px 15px;
    border-radius: 13px;
    background: rgba(26, 23, 40, 0.94);
    border: 0;
    box-shadow: var(--shadow);
    font-size: 13.5px;
    font-weight: 500;
    animation: in 0.28s var(--ease) both;
  }
  .toast.ok :global(svg) {
    color: var(--ok);
  }
  .toast.bad :global(svg) {
    color: var(--bad);
  }
  .toast.info :global(svg) {
    color: var(--brand);
  }
  @keyframes in {
    from {
      opacity: 0;
      transform: translateY(12px) scale(0.98);
    }
  }
</style>
