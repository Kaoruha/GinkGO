import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// 浏览器形态配置(Electron 形态见 electron.vite.config.ts)
// root 指向 src/renderer,与 electron-vite 三段式共享同一份 Vue 源码
export default defineConfig({
  root: 'src/renderer',
  base: './',
  publicDir: resolve(__dirname, 'public'),
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src/renderer'),
    },
  },
  server: {
    host: process.env.HOST || '0.0.0.0',
    port: parseInt(process.env.PORT || '5173'),
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        // Task1 root 迁至 src/renderer 后,前端 api 模块的 dev URL = /api/*.ts,
        // 命中此 proxy 被转后端→401 致整个 @/api 模块树加载失败(ADR-042 §1)。
        // bypass: 带源码扩展名的请求走 vite 自 serve,不转发后端。
        bypass(req) {
          if (/\.(ts|js|jsx|tsx|mjs|vue|css|less|scss|json|map)(\?|$)/.test(req.url)) {
            return req.url
          }
        },
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
        rewrite: (path) => path,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          'vue-vendor': ['vue', 'vue-router', 'pinia'],
          'charts': ['lightweight-charts'],
        },
      },
    },
  },
})
