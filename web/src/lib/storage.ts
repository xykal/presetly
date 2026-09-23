import type { Preset } from './types';

const KEY_SAVED = 'amf:saved:v2';
const KEY_RECENT = 'amf:recent:v2';

function read<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function write(key: string, value: unknown) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* quota penuh / private mode - aman diabaikan */
  }
}

export const saved = {
  all: (): Preset[] => read<Preset[]>(KEY_SAVED, []),
  has: (key: string) => saved.all().some((p) => p.key === key),
  toggle(p: Preset): boolean {
    const list = saved.all();
    const i = list.findIndex((x) => x.key === p.key);
    if (i >= 0) {
      list.splice(i, 1);
      write(KEY_SAVED, list);
      return false;
    }
    list.unshift({ ...p, saved_at: Math.floor(Date.now() / 1000) });
    write(KEY_SAVED, list.slice(0, 500));
    return true;
  },
  remove(key: string) {
    write(KEY_SAVED, saved.all().filter((p) => p.key !== key));
  },
};

export interface RecentSearch {
  platform: string;
  mode: string;
  query: string;
  at: number;
}

export const recent = {
  all: (): RecentSearch[] => read<RecentSearch[]>(KEY_RECENT, []),
  push(r: Omit<RecentSearch, 'at'>) {
    const list = recent.all().filter((x) => !(x.query === r.query && x.platform === r.platform && x.mode === r.mode));
    list.unshift({ ...r, at: Math.floor(Date.now() / 1000) });
    write(KEY_RECENT, list.slice(0, 8));
  },
  clear: () => write(KEY_RECENT, []),
};
