export const FREE_MB = 5;

export function fmtNum(n: number | null | undefined): string {
  if (n == null || Number.isNaN(n)) return '-';
  const f = (v: number, s: string) => `${(v >= 100 ? Math.round(v) : Math.round(v * 10) / 10).toString().replace('.', ',')}${s}`;
  if (n >= 1e9) return f(n / 1e9, 'M');
  if (n >= 1e6) return f(n / 1e6, 'jt');
  if (n >= 1e3) return f(n / 1e3, 'rb');
  return String(n);
}

export function timeAgo(ts: number | null | undefined): string {
  if (!ts) return '';
  const d = Date.now() / 1000 - ts;
  if (d < 0) return '';
  const units: [number, string][] = [
    [31536000, 'thn'], [2592000, 'bln'], [604800, 'mgg'], [86400, 'hari'], [3600, 'jam'], [60, 'mnt'],
  ];
  for (const [s, n] of units) if (d >= s) return `${Math.floor(d / s)} ${n} lalu`;
  return 'baru aja';
}

export function fmtDur(s: number | null | undefined): string {
  if (!s) return '';
  s = Math.round(s);
  const m = Math.floor(s / 60);
  const x = String(s % 60).padStart(2, '0');
  return m >= 60 ? `${Math.floor(m / 60)}:${String(m % 60).padStart(2, '0')}:${x}` : `${m}:${x}`;
}

export function hostOf(u: string): string {
  try {
    return new URL(u).hostname.replace(/^www\./, '');
  } catch {
    return '';
  }
}

export function safeUrl(u: string | null | undefined): string {
  return u && /^https?:\/\//i.test(u) ? u : '#';
}

export const SRC_LABEL: Record<string, string> = {
  deskripsi: 'deskripsi',
  caption: 'caption',
  'komen pinned': 'komen pinned',
  'komen creator': 'komen creator',
  'balasan creator': 'balasan creator',
  bio: 'bio creator',
  komen: 'komen penonton',
  balasan: 'balasan penonton',
  input: 'link lu',
};

export const CROWD_SOURCES = new Set(['komen', 'balasan']);

export const KIND_LABEL: Record<string, string> = {
  xml: 'XML', zip: 'ZIP', sound: 'Sound', folder: 'Folder', video: 'Video', image: 'Gambar', apk: 'APK', file: 'File',
};

export function isFree(mb: number | null | undefined): boolean | null {
  return mb == null ? null : mb <= FREE_MB;
}

export function isMobile(): boolean {
  return /Android|iPhone|iPad|iPod/i.test(navigator.userAgent);
}
