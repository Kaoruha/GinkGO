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
</script>
