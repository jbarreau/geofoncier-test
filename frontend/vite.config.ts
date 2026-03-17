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
      // Les services FastAPI enregistrent leurs propres préfixes —
      // on transmet l'URI complète telle quelle (pas de rewrite).
      '/auth': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/tasks': {
        target: 'http://localhost:8001',
        changeOrigin: true,
      },
      '/analytics': {
        target: 'http://localhost:8002',
        changeOrigin: true,
      },
    },
  },
})
