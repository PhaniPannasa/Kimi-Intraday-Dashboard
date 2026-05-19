import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'
import path from 'path'

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      manifest: false,
      injectRegister: 'auto'
    })
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    },
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test-setup.ts'],
  },
  server: {
    port: 8190,
    host: true,
    allowedHosts: ['kimi.intraday-edge-4zz.uk', 'localhost'],
    proxy: {
      '/api': {
        target: 'http://localhost:8172',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
      '/ws': {
        target: 'ws://localhost:8170',
        ws: true,
        changeOrigin: true,
      },
    }
  }
})
