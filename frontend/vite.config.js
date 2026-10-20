import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    proxy: {
      '/api/v2': {
        target: process.env.V2_PROXY_TARGET || 'http://localhost:8003',
        changeOrigin: true,
      },
      '/mcp': {
        target: process.env.V2_PROXY_TARGET || 'http://localhost:8003',
        changeOrigin: true,
      },
      '/api': {
        target: process.env.V1_PROXY_TARGET || 'http://localhost:5003',
        changeOrigin: true,
      }
    }
  }
}) 
