<template>
  <div class="portfolio-detail">
    <!-- Header with portfolio name and action buttons -->
    <div class="detail-header">
      <div class="header-left">
        <router-link to="/portfolios" class="back-link">&larr; 组合列表</router-link>
        <h1 class="page-title">{{ portfolioName }}</h1>
        <span class="portfolio-id">{{ portfolioId }}</span>
        <span v-if="portfolioStatus" class="status-tag" :class="portfolioStatus">{{ statusLabel }}</span>
      </div>
      <div class="header-actions">
        <button class="btn-secondary" @click="$router.push(`/portfolios/${portfolioId}/edit`)">编辑</button>
        <button class="btn-primary" @click="startBacktest">新建回测</button>
      </div>
    </div>

    <!-- Tab navigation -->
    <div class="tab-bar">
      <router-link
        v-for="tab in tabs"
        :key="tab.key"
        :to="tab.route"
        class="tab-item"
        :class="{ active: activeTab === tab.key }"
      >
        {{ tab.label }}
      </router-link>
    </div>

    <!-- Tab content -->
    <div class="tab-content">
      <router-view v-slot="{ Component }">
        <component :is="Component" :key="route.fullPath" />
      </router-view>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()

const portfolioId = computed(() => route.params.id as string)
const portfolioName = ref('加载中...')
const portfolioStatus = ref('')

const statusLabels: Record<string, string> = {
  live: '实盘',
  paper: '模拟',
  idle: '空闲',
}

const statusLabel = computed(() => statusLabels[portfolioStatus.value] || '')

const activeTab = computed(() => {
  const path = route.path
  if (path.includes('/backtests')) return 'backtests'
  if (path.includes('/validation')) return 'validation'
  if (path.includes('/components')) return 'components'
  return 'overview'
})

const tabs = computed(() => [
  { key: 'overview', label: '概况', route: `/portfolios/${portfolioId.value}` },
  { key: 'backtests', label: '回测', route: `/portfolios/${portfolioId.value}/backtests` },
  { key: 'validation', label: '验证', route: `/portfolios/${portfolioId.value}/validation` },
  { key: 'components', label: '组件', route: `/portfolios/${portfolioId.value}/components` },
])

function startBacktest() {
  router.push(`/portfolios/${portfolioId.value}/backtests?action=create`)
}

// Load portfolio info
async function loadPortfolio() {
  // Will be wired to API later; for now just set a placeholder name
  portfolioName.value = `组合 ${portfolioId.value.substring(0, 8)}`
}

watch(portfolioId, () => { loadPortfolio() }, { immediate: true })
</script>

<style scoped>
.portfolio-detail {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 0;
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.back-link {
  color: rgba(255,255,255,0.5);
  text-decoration: none;
  font-size: 14px;
}

.back-link:hover {
  color: rgba(255,255,255,0.8);
}

.portfolio-id {
  font-size: 12px;
  color: #6a6a7a;
  font-family: monospace;
  user-select: all;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: #fff;
  margin: 0;
}

.status-tag {
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}
.status-tag.live { background: rgba(34,197,94,0.15); color: #22c55e; }
.status-tag.paper { background: rgba(59,130,246,0.15); color: #3b82f6; }
.status-tag.idle { background: rgba(255,255,255,0.1); color: rgba(255,255,255,0.5); }

.header-actions {
  display: flex;
  gap: 8px;
}

.btn-primary {
  padding: 8px 16px;
  background: #3b82f6;
  border: none;
  border-radius: 6px;
  color: #fff;
  font-size: 13px;
  cursor: pointer;
}
.btn-primary:hover { background: #2563eb; }

.btn-secondary {
  padding: 8px 16px;
  background: transparent;
  border: 1px solid #3a3a4e;
  border-radius: 6px;
  color: #fff;
  font-size: 13px;
  cursor: pointer;
}
.btn-secondary:hover { border-color: #3b82f6; }

.tab-bar {
  display: flex;
  gap: 0;
  border-bottom: 1px solid #2a2a3e;
  flex-shrink: 0;
}

.tab-item {
  padding: 10px 20px;
  color: rgba(255,255,255,0.5);
  text-decoration: none;
  font-size: 14px;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}

.tab-item:hover {
  color: rgba(255,255,255,0.8);
}

.tab-item.active {
  color: #3b82f6;
  border-bottom-color: #3b82f6;
  font-weight: 600;
}

.tab-content {
  flex: 1;
  overflow: auto;
  padding-top: 16px;
}
</style>
