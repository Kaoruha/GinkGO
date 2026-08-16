<template>
  <!-- 登录页等全屏页面 -->
  <EmptyLayout v-if="isFullPage">
    <div :key="route.path" class="m-page">
      <router-view />
    </div>
  </EmptyLayout>

  <!-- 带布局的主页面（需要登录） -->
  <AppLayout v-else-if="authStore.isLoggedIn">
    <div :key="route.path" class="m-page">
      <router-view />
    </div>
  </AppLayout>

  <!-- Fallback - 让路由守卫处理重定向 -->
  <router-view v-else />

  <!-- 全局右键菜单单例(屏蔽浏览器默认菜单,OS 风格自定义交互) -->
  <ContextMenu />
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useServerEvents } from '@/composables/useServerEvents'
import AppLayout from '@/layouts/AppLayout.vue'
import EmptyLayout from '@/layouts/EmptyLayout.vue'
import ContextMenu from '@/components/common/ContextMenu.vue'

const route = useRoute()
const authStore = useAuthStore()

// 全屏页面（不需要侧边栏布局）
const isFullPage = computed(() => {
  const fullPageRoutes = ['/login', '/404']
  return fullPageRoutes.includes(route.path) || route.meta?.fullPage === true
})

// 全局通知通道(ADR-046):登录即连、登出即断;通知事件 → toast。
// useServerEvents 的 bootstrap 订阅随首个 on()/onReconnect() 生效,
// 这里立即调用 useNotificationToasts() 保证 App 挂载时事件层就绪
// (WS 连接生命周期已内化至 useWebSocket 模块,首个 useWebSocket() 调用
//  时按登录态自动连/断,App.vue 不再持有 connect/disconnect)
useServerEvents().useNotificationToasts()
</script>
