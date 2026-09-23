import { api, ApiError, pool, type ListParams, type ScanOpts } from './api';
import { recent } from './storage';
import type { FoundLink, Health, PlayerTarget, Profile, ScanResult, VideoItem } from './types';

/* ---------------- toast ---------------- */
export const toast = $state({ msg: '', tone: 'info' as 'info' | 'ok' | 'bad', seq: 0 });
let toastTimer: ReturnType<typeof setTimeout> | undefined;
export function notify(msg: string, tone: 'info' | 'ok' | 'bad' = 'info', ms = 2600) {
  toast.msg = msg;
  toast.tone = tone;
  toast.seq++;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (toast.msg = ''), ms);
}

export async function copyText(text: string, msg = 'Link disalin') {
  try {
    await navigator.clipboard.writeText(text);
  } catch {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.cssText = 'position:fixed;opacity:0';
    document.body.appendChild(ta);
    ta.select();
    try {
      document.execCommand('copy');
    } catch {
      /* ignore */
    }
    ta.remove();
  }
  notify(msg, 'ok');
}

/* ---------------- app shell ---------------- */
export type Tab = 'cari' | 'jelajah' | 'koleksi';
export const ui = $state({
  tab: 'cari' as Tab,
  player: null as PlayerTarget | null,
  qr: null as { url: string; name?: string | null } | null,
  health: null as Health | null,
});

export async function loadHealth() {
  try {
    ui.health = await api.health();
  } catch {
    ui.health = null;
  }
}

/* ---------------- search ---------------- */
export const search = $state({
  status: 'idle' as 'idle' | 'listing' | 'scanning' | 'done' | 'error' | 'stopped',
  params: null as ListParams | null,
  items: [] as VideoItem[],
  results: {} as Record<string, ScanResult>,
  failed: 0,
  profile: null as Profile | null,
  presetCheck: null as FoundLink[] | null,
  notes: [] as string[],
  error: '',
  startedAt: 0,
  finishedAt: 0,
});

let controller: AbortController | null = null;
const BATCH = 3;
const CONCURRENCY = 4;

export const keyOf = (v: { platform: string; id: string }) => `${v.platform}:${v.id}`;

export async function runSearch(p: ListParams, opts: ScanOpts) {
  controller?.abort();
  controller = new AbortController();
  const signal = controller.signal;
  Object.assign(search, {
    status: 'listing', params: p, items: [], results: {}, failed: 0, profile: null, presetCheck: null,
    notes: [], error: '', startedAt: Date.now(), finishedAt: 0,
  });
  recent.push({ platform: p.platform, mode: p.mode, query: p.query });
  try {
    const res = await api.list(p, signal);
    search.items = res.items;
    search.profile = res.profile;
    search.presetCheck = res.preset_check;
    search.notes = res.notes;
    if (!res.items.length) {
      search.status = 'done';
      search.finishedAt = Date.now();
      return;
    }
    search.status = 'scanning';
    const batches: VideoItem[][] = [];
    for (let i = 0; i < res.items.length; i += BATCH) batches.push(res.items.slice(i, i + BATCH));
    await pool(
      batches.map((batch) => async () => {
        try {
          const { results } = await api.scan(batch, opts, signal);
          for (const r of results) search.results[keyOf(r)] = r;
        } catch (e) {
          if ((e as Error).name === 'AbortError') throw e;
          // retry sekali per batch (rate limit / cold start)
          await new Promise((r) => setTimeout(r, 1200));
          try {
            const { results } = await api.scan(batch, opts, signal);
            for (const r of results) search.results[keyOf(r)] = r;
          } catch (e2) {
            if ((e2 as Error).name === 'AbortError') throw e2;
            search.failed += batch.length;
            for (const v of batch) {
              search.results[keyOf(v)] = {
                ...v, links: [], n_am: 0, n_ok: 0, n_xml: 0, min_size: null,
                error: e2 instanceof ApiError ? e2.message : 'Gagal discan',
              };
            }
          }
        }
      }),
      CONCURRENCY,
      signal,
    );
    if (!signal.aborted) search.status = 'done';
  } catch (e) {
    if ((e as Error).name === 'AbortError') {
      search.status = 'stopped';
    } else {
      search.status = 'error';
      search.error = e instanceof Error ? e.message : String(e);
    }
  } finally {
    search.finishedAt = Date.now();
  }
}

export function stopSearch() {
  controller?.abort();
  search.status = 'stopped';
}

export function resetSearch() {
  controller?.abort();
  Object.assign(search, {
    status: 'idle', params: null, items: [], results: {}, failed: 0, profile: null, presetCheck: null,
    notes: [], error: '',
  });
}

export function openPlayer(t: PlayerTarget) {
  ui.player = t;
}
