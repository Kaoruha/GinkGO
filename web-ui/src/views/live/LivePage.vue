<template>
  <!-- LivePage.vue（实盘页） -->
  <div class="live-page">
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
  { key: 'overview', label: '概览', route: '/trading/live' },
  { key: 'accounts', label: '账号配置', route: '/trading/live/accounts' },
  { key: 'monitor', label: '账户监控', route: '/trading/live/monitor' },
  { key: 'brokers', label: 'Broker', route: '/trading/live/brokers' },
  { key: 'market', label: '行情', route: '/trading/live/market' },
  { key: 'history', label: '交易历史', route: '/trading/live/history' },
]

const isActive = (key: string) => {
  if (key === 'overview') {
    // 概览 tab 仅在精确匹配 /trading/live 时高亮
    return route.path === '/trading/live'
  }
  return route.path.includes(key)
}
</script>

<style scoped>
.live-page {
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
