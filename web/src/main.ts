import { mount } from 'svelte';
import './app.css';
import App from './App.svelte';

const target = document.getElementById('app');
if (!target) throw new Error('#app gak ketemu');

export default mount(App, { target });

// Balikin langganan notifikasi (SW harus terdaftar walau user cuma buka web).
if (localStorage.getItem('presetly.push')?.includes('"on":true') && 'serviceWorker' in navigator) {
  navigator.serviceWorker.register('/sw.js').catch(() => {});
}
