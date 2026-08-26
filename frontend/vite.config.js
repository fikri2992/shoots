import { fileURLToPath, URL } from 'node:url'

import tailwindcss from '@tailwindcss/vite'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    proxy: {
      '/api': { target: process.env.SHOOTS_API_TARGET || 'http://localhost:8000', changeOrigin: true },
      '/auth': { target: process.env.SHOOTS_API_TARGET || 'http://localhost:8000', changeOrigin: true },
      '/drive': { target: process.env.SHOOTS_API_TARGET || 'http://localhost:8000', changeOrigin: true },
    },
  },
  test: {
    environment: 'jsdom',
    include: ['src/**/*.spec.js'],
  },
})
