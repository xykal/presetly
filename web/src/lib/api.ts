import type { Feed, FoundLink, Health, ListResponse, ScanResult, VideoItem } from './types';

export class ApiError extends Error {
  constructor(message: string, readonly status: number) {
    super(message);
  }
}

async function call<T>(path: string, init?: RequestInit & { json?: unknown }, signal?: AbortSignal): Promise<T> {
  const opts: RequestInit = { ...init, signal };
  if (init?.json !== undefined) {
    opts.method = opts.method ?? 'POST';
    opts.headers = { 'Content-Type': 'application/json', ...(opts.headers ?? {}) };
    opts.body = JSON.stringify(init.json);
  }
  let res: Response;
  try {
    res = await fetch(path, opts);
  } catch (e) {
    if ((e as Error).name === 'AbortError') throw e;
    throw new ApiError('Koneksi putus. Cek internet lu terus coba lagi.', 0);
  }
  let body: unknown = null;
  try {
    body = await res.json();
  } catch {
    /* non-JSON (mis. 504 dari platform) */
  }
  if (!res.ok) {
    const msg = (body as { error?: string } | null)?.error;
    if (res.status === 504) throw new ApiError('Server kelamaan mikir (timeout). Coba kurangin jumlah video.', 504);
    throw new ApiError(msg || `Server error (HTTP ${res.status})`, res.status);
  }
  return body as T;
}

export interface ListParams {
  platform: 'youtube' | 'tiktok' | 'link';
  mode: string;
  query: string;
  limit: number;
  sort?: 'relevance' | 'new';
  live?: boolean;
}

export interface ScanOpts {
  comments: boolean;
  deep: boolean;
  resolve: boolean;
}

export const api = {
  health: () => call<Health>('/api/health'),
  list: (p: ListParams, signal?: AbortSignal) => call<ListResponse>('/api/list', { json: p }, signal),
  scan: (items: VideoItem[], opts: ScanOpts, signal?: AbortSignal) =>
    call<{ results: ScanResult[] }>('/api/scan', { json: { items, ...opts } }, signal),
  check: (url: string) => call<{ links: FoundLink[] }>('/api/check', { json: { url } }),
  feed: () => call<Feed>('/api/feed'),
  ttMedia: (id: string) => call<{ play: string | null; proxy: string; thumb: string | null }>(`/api/media/tiktok/${id}`),
};

export async function exportCsv(results: ScanResult[]) {
  const res = await fetch('/api/export.csv', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ results }),
  });
  if (!res.ok) throw new ApiError('Gagal export CSV', res.status);
  const blob = await res.blob();
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `preset-am-${new Date().toISOString().slice(0, 16).replace(/[:T]/g, '')}.csv`;
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 5000);
}

/** Jalanin task async dengan batas konkurensi. Berhenti rapi kalau signal di-abort. */
export async function pool<T>(tasks: (() => Promise<T>)[], size: number, signal?: AbortSignal): Promise<void> {
  let i = 0;
  const worker = async () => {
    while (i < tasks.length && !signal?.aborted) {
      const task = tasks[i++];
      try {
        await task();
      } catch (e) {
        if ((e as Error).name === 'AbortError') return;
      }
    }
  };
  await Promise.all(Array.from({ length: Math.min(size, tasks.length) }, worker));
}
