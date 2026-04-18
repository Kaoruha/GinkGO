<template>
  <div class="trading-page">
    <div class="tab-bar">
      <router-link
        v-for="tab in tabs"
        :key="tab.key"
        :to="tab.route"
        class="tab-item"
        :class="{ active: isActive(tab.key) }"
      >
        {{ tab.label }}
      </router-link>
    </div>
    <div class="tab-content">
      <router-view />
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'

const route = useRoute()

const tabs = [
  { key: 'paper', label: '模拟盘', route: '/trading/paper' },
  { key: 'live', label: '实盘', route: '/trading/live' },
]

const isActive = (key: string) => route.path.includes(key)
</script>

<style scoped>
.trading-page {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.tab-bar {
  display: flex;
  gap: 0;
  border-bottom: 1px solid #2a2a3e;
  padding: 0 24px;
}
.tab-item {
  padding: 10px 16px;
  color: rgba(255,255,255,0.6);
  text-decoration: none;
  font-size: 14px;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}
.tab-item:hover {
  color: rgba(255,255,255,0.9);
}
.tab-item.active {
  color: #3b82f6;
  border-bottom-color: #3b82f6;
  font-weight: 600;
}
.tab-content {
  flex: 1;
  overflow: auto;
}
</style>
