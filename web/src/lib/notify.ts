import { api } from './api';

/** Notifikasi preset baru (Web Push standar + VAPID). State disimpen di localStorage. */

const KEY = 'presetly.push';

export interface PushState {
  on: boolean;
  creators: string[]; // "youtube:@user" | "tiktok:user" | "instagram:user"
}

export function loadPush(): PushState {
  try {
    const s = JSON.parse(localStorage.getItem(KEY) || '');
    if (s && Array.isArray(s.creators)) return { on: !!s.on, creators: s.creators };
  } catch {
    /* ignore */
  }
  return { on: false, creators: [] };
}

function save(s: PushState) {
  localStorage.setItem(KEY, JSON.stringify(s));
}

function b64ToU8(s: string): Uint8Array {
  const pad = '='.repeat((4 - (s.length % 4)) % 4);
  const b = atob(s.replace(/-/g, '+').replace(/_/g, '/') + pad);
  return Uint8Array.from(b, (c) => c.charCodeAt(0));
}

export async function ensureSw(): Promise<ServiceWorkerRegistration> {
  if (!('serviceWorker' in navigator)) throw new Error('Browser ini belum dukung service worker');
  const reg = await navigator.serviceWorker.register('/sw.js');
  await navigator.serviceWorker.ready;
  return reg;
}

export async function enablePush(creators: string[]): Promise<void> {
  if (!('PushManager' in window)) throw new Error('Browser ini belum dukung notifikasi push');
  const conf = await api.pushConfig();
  if (!conf.enabled || !conf.vapid) throw new Error('Notifikasi belum aktif di server');
  const perm = await Notification.requestPermission();
  if (perm !== 'granted') throw new Error('Izin notifikasi ditolak');
  const reg = await ensureSw();
  let sub = await reg.pushManager.getSubscription();
  if (!sub) {
    sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: b64ToU8(conf.vapid) as BufferSource });
  }
  const j = sub.toJSON();
  if (!j.endpoint || !j.keys?.p256dh || !j.keys?.auth) throw new Error('Langganan push gagal dibuat');
  await api.pushSubscribe({ endpoint: j.endpoint, keys: { p256dh: j.keys.p256dh, auth: j.keys.auth }, creators });
  save({ on: true, creators });
}

export async function disablePush(): Promise<void> {
  try {
    const reg = await navigator.serviceWorker.getRegistration();
    const sub = await reg?.pushManager.getSubscription();
    if (sub) {
      await api.pushUnsubscribe(sub.endpoint).catch(() => {});
      await sub.unsubscribe();
    }
  } catch {
    /* ignore */
  }
  save({ on: false, creators: [] });
}

/** Update daftar creator yang dipantau (auto nyalain kalau belum on). */
export async function setCreators(creators: string[]): Promise<void> {
  const s = loadPush();
  if (!s.on) {
    save({ on: false, creators });
    return;
  }
  await enablePush(creators);
}
