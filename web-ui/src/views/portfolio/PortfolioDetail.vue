<template>
  <div class="portfolio-detail">
    <!-- Header with portfolio name and action buttons -->
    <div class="detail-header">
      <div class="header-left">
        <router-link to="/portfolios" class="back-link">&larr; 组合列表</router-link>
        <h1 class="page-title">{{ portfolioName }}</h1>
        <span class="portfolio-id">{{ portfolioId }}</span>
        <span v-if="portfolioStatus" class="status-tag" :class="portfolioStatus">{{ statusLabel }}</span>
        <span v-if="deploymentSource" class="deploy-source">
          来源：{{ deploymentSource.source_task_id?.slice(0, 8) }}
        </span>
      </div>
      <div class="header-actions">
        <button class="btn-secondary" @click="$router.push(`/portfolios/${portfolioId}/edit`)">编辑</button>
        <button v-if="portfolioStatus === 'idle'" class="btn-deploy" @click="openDeploy">部署</button>
        <button v-if="portfolioStatus === 'paper' || portfolioStatus === 'live'" class="btn-stop" @click="handleStop">停止</button>
        <button v-if="portfolioStatus === 'idle'" class="btn-primary" @click="startBacktest">新建回测</button>
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
    <DeployModal
      v-model:visible="showDeployModal"
      :portfolio-id="portfolioId"
      @success="onDeploySuccess"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { portfolioApi, deploymentApi } from '@/api'
import { message } from '@/utils/toast'
import DeployModal from '@/components/business/DeployModal.vue'

const route = useRoute()
const router = useRouter()

const portfolioId = computed(() => route.params.id as string)
const portfolioName = ref('加载中...')
const portfolioStatus = ref('')
const deploymentSource = ref<any>(null)

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

async function handleStop() {
  try {
    await portfolioApi.stop(portfolioId.value)
    message.success('停止命令已发送')
    loadPortfolio()
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '停止失败')
  }
}

async function loadPortfolio() {
  try {
    const res: any = await portfolioApi.get(portfolioId.value)
    const p = res?.data || res
    portfolioName.value = p?.name || `组合 ${portfolioId.value.substring(0, 8)}`
    const mode = (p?.mode || '').toString().toUpperCase()
    if (mode === 'PAPER') {
      portfolioStatus.value = 'paper'
      loadDeploymentInfo()
    } else if (mode === 'LIVE') {
      portfolioStatus.value = 'live'
      loadDeploymentInfo()
    } else {
      portfolioStatus.value = 'idle'
    }
  } catch {
    portfolioName.value = `组合 ${portfolioId.value.substring(0, 8)}`
    portfolioStatus.value = 'idle'
  }
}

async function loadDeploymentInfo() {
  try {
    const res: any = await deploymentApi.getStatus(portfolioId.value)
    deploymentSource.value = res?.data || null
  } catch {
    deploymentSource.value = null
  }
}

const showDeployModal = ref(false)

const openDeploy = () => { showDeployModal.value = true }

const onDeploySuccess = (newPortfolioId: string) => {
  if (newPortfolioId) {
    router.push(`/portfolios/${newPortfolioId}`)
  }
  loadPortfolio()
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

.deploy-source {
  font-size: 11px;
  color: #8a8a9a;
  background: rgba(255,255,255,0.05);
  padding: 2px 8px;
  border-radius: 4px;
  font-family: monospace;
}

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

.btn-deploy {
  padding: 8px 16px;
  background: transparent;
  border: 1px solid #52c41a;
  border-radius: 6px;
  color: #52c41a;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-deploy:hover { background: #52c41a; color: #fff; }

.btn-stop {
  padding: 8px 16px;
  border-radius: 6px;
  border: 1px solid #faad14;
  background: #fffbe6;
  color: #d48806;
  cursor: pointer;
  font-size: 13px;
}
.btn-stop:hover {
  background: #fff1b8;
}

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
