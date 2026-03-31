import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import federation from '@originjs/vite-plugin-federation'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [
    vue(),
    federation({
      name: 'shell',
      filename: 'remoteEntry.js',
      exposes: {
        './stores/auth': './src/stores/auth.ts',
      },
      remotes: {
        'auth-front': 'http://localhost:5001/assets/remoteEntry.js',
        'task-front': 'http://localhost:5002/assets/remoteEntry.js',
        'analytics-front': 'http://localhost:5003/assets/remoteEntry.js',
      },
      shared: {
        vue: { singleton: true, requiredVersion: '^3.4.0' },
        pinia: { singleton: true, requiredVersion: '^2.1.0' },
        'vue-router': { singleton: true, requiredVersion: '^4.3.0' },
      },
    }),
  ],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5000,
    proxy: {
      '/api/auth': { target: 'http://localhost:8000', changeOrigin: true },
      '/api/tasks': { target: 'http://localhost:8001', changeOrigin: true },
      '/api/analytics': { target: 'http://localhost:8002', changeOrigin: true },
      '/api/permissions': { target: 'http://localhost:8000', changeOrigin: true },
      '/api/roles': { target: 'http://localhost:8000', changeOrigin: true },
      '/api/users': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
  preview: {
    port: 5000,
  },
  build: {
    target: 'esnext',
    modulePreload: false,
    minify: false,
    cssCodeSplit: false,
  },
})
