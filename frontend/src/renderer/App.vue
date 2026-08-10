<template>
  <!-- 登录页等全屏页面 -->
  <div v-if="isFullPage" class="full-page">
    <router-view />
  </div>

  <!-- 带布局的主页面（需要登录） -->
  <div v-else-if="authStore.isLoggedIn" class="app-layout">
    <AppSider
      :collapsed="collapsed"
      :selected-keys="selectedKeys"
      @select="selectedKeys = [$event]"
    />
    <div class="main">
      <AppHeader :collapsed="collapsed" @toggle="collapsed = !collapsed" />
      <main class="content" :class="{ 'content-fullscreen': isEditorPage }">
        <router-view />
      </main>
    </div>
  </div>

  <!-- Fallback - 让路由守卫处理重定向 -->
  <router-view v-else />
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { AppSider, AppHeader } from '@/components/layout'
import { keyForPath } from '@/config/menu'

const route = useRoute()
const authStore = useAuthStore()

const collapsed = ref(false)
const selectedKeys = ref<string[]>(['dashboard'])

// 全屏页面（不需要侧边栏布局）
const isFullPage = computed(() => {
  const fullPageRoutes = ['/login', '/404']
  return fullPageRoutes.includes(route.path) || route.meta?.fullPage === true
})

// 组件详情页（需要全屏 content）
const isEditorPage = computed(() => {
  return !!route.path.match(/\/components\/(strategies|risks|sizers|selectors|analyzers|handlers)\/[a-f0-9-]+/)
})

// 路由变化 → 菜单高亮（keyForPath 先精确后前缀，单一配置源）
watch(() => route.path, (path) => {
  const key = keyForPath(path)
  if (key) {
    selectedKeys.value = [key]
  }
}, { immediate: true })
</script>

<style scoped>
.app-layout {
  height: 100vh;
  overflow: hidden;
  background: hsl(var(--background));
  display: flex;
}

.main {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.content {
  padding: 24px;
  background: hsl(var(--background));
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
}

.content-fullscreen {
  padding: 0;
  overflow: hidden;
}
</style>
