<template>
  <!-- 主布局:侧边栏 + 头部 + 内容区(需要登录的页面) -->
  <div class="app-layout">
    <AppSider
      :collapsed="collapsed"
      :selected-keys="selectedKeys"
      @select="selectedKeys = [$event]"
    />
    <div class="main">
      <AppHeader :collapsed="collapsed" @toggle="collapsed = !collapsed" />
      <main class="content" :class="{ 'content-fullscreen': isEditorPage }">
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { AppSider, AppHeader } from '@/components/layout'
import { keyForPath } from '@/config/menu'

const route = useRoute()

const collapsed = ref(false)
const selectedKeys = ref<string[]>(['dashboard'])

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

/* 路由动画 wrapper 保持布局中立（页面依赖 height:100% 链） */
.content > :deep(.m-page) {
  height: 100%;
}

.content-fullscreen {
  padding: 0;
  overflow: hidden;
}
</style>
