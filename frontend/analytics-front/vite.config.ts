import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import federation from '@originjs/vite-plugin-federation'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [
    vue(),
    federation({
      name: 'analytics-front',
      filename: 'remoteEntry.js',
      exposes: {
        './Dashboard': './src/views/AnalyticsView.vue',
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
    port: 5003,
    proxy: {
      '/api/analytics': { target: 'http://localhost:8002', changeOrigin: true },
      '/api/users': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
  preview: {
    port: 5003,
  },
  build: {
    target: 'esnext',
    modulePreload: false,
    minify: false,
    cssCodeSplit: false,
  },
})
