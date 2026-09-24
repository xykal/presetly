import { defineConfig } from 'vite';
import { svelte, vitePreprocess } from '@sveltejs/vite-plugin-svelte';

// Dev: `npm run dev` + `python -m presetly serve --port 8000` -> /api di-proxy ke Flask.
export default defineConfig({
  root: 'web',
  publicDir: 'public',
  plugins: [svelte({ configFile: false, preprocess: vitePreprocess() })],
  build: { outDir: '../dist', emptyOutDir: true, target: 'es2022', cssMinify: true },
  server: { host: true, proxy: { '/api': 'http://127.0.0.1:8000' } },
});
