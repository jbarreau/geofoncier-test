import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      // Les services FastAPI exposent leurs routes sous /api/ (préfixe natif
      // des routeurs) — pas de réécriture nécessaire.
      '/api/auth': { target: 'http://localhost:8000', changeOrigin: true },
      '/api/tasks': { target: 'http://localhost:8001', changeOrigin: true },
      '/api/analytics': { target: 'http://localhost:8002', changeOrigin: true },
      '/api/permissions': { target: 'http://localhost:8000', changeOrigin: true },
      '/api/roles': { target: 'http://localhost:8000', changeOrigin: true },
      '/api/users': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
})
