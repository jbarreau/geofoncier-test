import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import federation from '@originjs/vite-plugin-federation'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [
    vue(),
    federation({
      name: 'task-front',
      filename: 'remoteEntry.js',
      exposes: {
        './TaskList': './src/views/TasksView.vue',
        './TaskForm': './src/components/TaskForm.vue',
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
    port: 5002,
    proxy: {
      '/api/tasks': { target: 'http://localhost:8001', changeOrigin: true },
      '/api/auth': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
  preview: {
    port: 5002,
  },
  build: {
    target: 'esnext',
    modulePreload: false,
    minify: false,
    cssCodeSplit: false,
  },
})
