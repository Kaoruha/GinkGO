import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
<<<<<<< HEAD
import { fileURLToPath, URL } from 'node:url'
=======
import { resolve } from 'path'
>>>>>>> 011-quant-research

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
<<<<<<< HEAD
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      },
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true
      }
    }
  },
  build: {
    target: 'es2020',
=======
      '@': resolve(__dirname, 'src'),
    },
  },
  server: {
    host: process.env.HOST || '0.0.0.0',
    port: parseInt(process.env.PORT || '5173'),
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
>>>>>>> 011-quant-research
    outDir: 'dist',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
<<<<<<< HEAD
          'vendor': ['vue', 'vue-router', 'pinia'],
          'antd': ['ant-design-vue'],
          'charts': ['lightweight-charts', 'echarts', 'vue-echarts']
        }
      }
    }
  }
=======
          'vue-vendor': ['vue', 'vue-router', 'pinia'],
          'antd': ['ant-design-vue', '@ant-design/icons-vue'],
          'charts': ['lightweight-charts'],
        },
      },
    },
  },
>>>>>>> 011-quant-research
})
