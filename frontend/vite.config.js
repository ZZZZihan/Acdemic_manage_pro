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
        target: 'http://localhost:8003',
        changeOrigin: true,
      },
      '/mcp': {
        target: 'http://localhost:8003',
        changeOrigin: true,
      },
      '/api': {
        target: 'http://localhost:5003',
        changeOrigin: true,
      }
    }
  }
}) 
