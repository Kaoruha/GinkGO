import { defineConfig, externalizeDepsPlugin } from 'electron-vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// Electron 形态配置(浏览器形态见 vite.config.ts)
// electron-vite 三段式:main(主进程) + preload(预加载) + renderer(渲染进程=Vue 源码)
export default defineConfig({
  main: {
    plugins: [externalizeDepsPlugin()],
    build: {
      rollupOptions: {
        input: { index: resolve(__dirname, 'src/main/index.ts') },
      },
    },
  },
  preload: {
    plugins: [externalizeDepsPlugin()],
    build: {
      rollupOptions: {
        input: { index: resolve(__dirname, 'src/preload/index.ts') },
      },
    },
  },
  renderer: {
    root: 'src/renderer',
    // 与浏览器形态 vite.config.ts 对齐:publicDir 指向 frontend/public
    // 让 App.vue/index.html 里 /favicon.svg 这类公开资源在 dev 与 prod build 都能解析
    publicDir: resolve(__dirname, 'public'),
    build: {
      rollupOptions: {
        input: { index: resolve(__dirname, 'src/renderer/index.html') },
      },
    },
    plugins: [vue()],
    resolve: {
      alias: {
        '@': resolve(__dirname, 'src/renderer'),
      },
    },
  },
})
