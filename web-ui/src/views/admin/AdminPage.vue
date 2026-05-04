<template>
  <div class="admin-page">
    <div class="admin-sidebar">
      <div class="admin-nav-group">
        <div class="admin-nav-title">组件库</div>
        <router-link
          v-for="item in componentItems"
          :key="item.route"
          :to="item.route"
          class="admin-nav-item"
          :class="{ active: isActive(item.route) }"
        >
          {{ item.label }}
        </router-link>
      </div>
    </div>
    <div class="admin-content">
      <router-view />
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()

const componentItems = [
  { label: '策略组件', route: '/components/strategies' },
  { label: '风控组件', route: '/components/risks' },
  { label: '仓位组件', route: '/components/sizers' },
  { label: '选股器', route: '/components/selectors' },
  { label: '分析器', route: '/components/analyzers' },
  { label: '事件处理器', route: '/components/handlers' },
]

const isActive = (itemRoute: string) => {
  return route.path.startsWith(itemRoute)
}
</script>

<style scoped>
.admin-page {
  display: flex;
  height: 100%;
}
.admin-sidebar {
  width: 180px;
  background: #1a1a2e;
  border-right: 1px solid #2a2a3e;
  padding: 16px 0;
  overflow-y: auto;
}
.admin-nav-group {
  margin-bottom: 16px;
}
.admin-nav-title {
  padding: 6px 20px;
  font-size: 11px;
  text-transform: uppercase;
  color: rgba(255,255,255,0.4);
  letter-spacing: 0.5px;
}
.admin-nav-item {
  display: block;
  padding: 8px 20px;
  color: rgba(255,255,255,0.6);
  text-decoration: none;
  font-size: 13px;
  transition: all 0.2s;
}
.admin-nav-item:hover {
  color: rgba(255,255,255,0.9);
  background: rgba(255,255,255,0.05);
}
.admin-nav-item.active {
  color: #3b82f6;
  background: rgba(59,130,246,0.1);
  border-right: 2px solid #3b82f6;
}
.admin-content {
  flex: 1;
  overflow: auto;
}
</style>
