<template>
  <teleport to="body">
    <transition name="loading-fade">
      <div v-if="hasActiveLoading" class="global-loading">
        <div v-if="showOverlay" class="overlay"></div>
        <div class="loading-container">
          <div class="loading-content">
            <div class="loading-spinner">
              <svg class="spinner-icon" xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"></circle>
                <path d="M12 2a10 10 0 0 1 10 10"></path>
              </svg>
            </div>
            <span v-if="loadingMessage" class="loading-message">
              {{ loadingMessage }}
            </span>
            <span v-if="activeLoadings.length > 1" class="loading-count">
              ({{ activeLoadings.length }} 项任务)
            </span>
          </div>
        </div>
      </div>
    </transition>
  </teleport>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useLoadingStore } from '@/stores/loading'

interface Props {
  /** 是否显示遮罩层 */
  showOverlay?: boolean
  /** 自定义加载消息映射 */
  messages?: Record<string, string>
}

const props = withDefaults(defineProps<Props>(), {
  showOverlay: true,
  messages: () => ({})
})

const loadingStore = useLoadingStore()

const activeLoadings = computed(() => loadingStore.activeLoadings)
const highestPriorityLoading = computed(() => loadingStore.highestPriorityLoading)
const hasActiveLoading = computed(() => activeLoadings.value.length > 0)

const defaultMessages: Record<string, string> = {
  'portfolio-list': '加载投资组合列表...',
  'portfolio-detail': '加载投资组合详情...',
  'portfolio-create': '创建投资组合...',
  'portfolio-update': '更新投资组合...',
  'portfolio-delete': '删除投资组合...',
  'backtest-list': '加载回测任务...',
  'backtest-create': '创建回测任务...',
  'backtest-run': '运行回测中...',
  'strategy-list': '加载策略列表...',
  'strategy-create': '创建策略...',
  'data-update': '更新数据中...',
  'default': '加载中...'
}

/**
 * 获取加载消息
 */
const loadingMessage = computed(() => {
  if (!highestPriorityLoading.value) {
    return activeLoadings.value.length === 1 ? '加载中...' : '正在处理...'
  }

  const key = highestPriorityLoading.value.key
  const customMessages = { ...defaultMessages, ...props.messages }
  return customMessages[key] || customMessages['default']
})
</script>

<style scoped>
.global-loading {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
}

.overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  backdrop-filter: blur(2px);
}

.loading-container {
  position: relative;
  z-index: 1;
}

.loading-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  color: #ffffff;
  padding: 24px;
  background: #1a1a2e;
  border-radius: 8px;
  border: 1px solid #2a2a3e;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.loading-spinner {
  display: flex;
  align-items: center;
  justify-content: center;
}

.spinner-icon {
  animation: spin 1s linear infinite;
  color: #1890ff;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.loading-message {
  font-size: 14px;
  font-weight: 500;
}

.loading-count {
  font-size: 12px;
  opacity: 0.8;
  color: #8a8a9a;
}

/* 过渡动画 */
.loading-fade-enter-active,
.loading-fade-leave-active {
  transition: opacity 0.3s ease;
}

.loading-fade-enter-from,
.loading-fade-leave-to {
  opacity: 0;
}
</style>
