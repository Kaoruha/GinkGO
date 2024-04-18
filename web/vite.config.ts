import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueJsx from '@vitejs/plugin-vue-jsx'
import VueDevTools from 'vite-plugin-vue-devtools'

// https://vitejs.dev/config/
export default defineConfig({
    // server: { 
    //     proxy: { 
    //         '/api': { 
    //             target: 'http://192.168.50.10:8000', // 目标后端服务地址 
    //             changeOrigin: true, // 是否允许跨域 
    //             rewrite: (path) => path.replace(/^\/api/, '') // 重写请求路径 
    //         } 
    //     } 
    // }, 
    plugins: [ 
        vue(), 
        vueJsx(), 
        VueDevTools(), 
    ], 
    resolve: { 
        alias: { 
            '@': fileURLToPath(new URL('./src', import.meta.url)) 
        } 
    }
})
