<template>
  <PageLayout>
    <template #title>
      <PageTitle :title="portfolioName" back-to="/portfolios" back-label="组合列表" />
    </template>
    <template #meta>
      <span class="portfolio-id" :title="`${portfolioId}（点击复制）`" @click="copyPortfolioId">{{ portfolioId.slice(0, 8) }}</span>
      <span v-if="portfolioStatus" class="status-tag" :class="portfolioStatus">{{ statusLabel }}</span>
      <span v-if="deploymentSource" class="deploy-source">
        来源：{{ deploymentSource.source_task_id?.slice(0, 8) }}
      </span>
    </template>
    <template #actions>
      <button class="btn-secondary" @click="$router.push(`/portfolios/${portfolioId}/edit`)">编辑</button>
      <button v-if="portfolioStatus === 'idle'" class="btn-deploy" @click="openDeploy">部署</button>
      <button v-if="portfolioStatus === 'paper' || portfolioStatus === 'live'" class="btn-stop" @click="handleStop">停止</button>
      <button v-if="portfolioStatus === 'idle'" class="btn-primary" @click="startBacktest">新建回测</button>
    </template>

    <!-- Tab navigation(标准 #tabs 槽,容器由 PageLayout 提供) -->
    <template #tabs>
      <TabsNav :items="tabs" />
    </template>

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
    <ConfirmDialog
      v-model:open="stopConfirmOpen"
      title="停止运行"
      description="将停止该组合当前的运行部署,并撤销未成交委托。此操作不可逆,确定要继续吗?"
      danger
      confirm-text="停止"
      :loading="stopping"
      @confirm="doStop"
    />
  </PageLayout>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import PageLayout from '@/components/common/PageLayout.vue'
import PageTitle from '@/components/common/PageTitle.vue'
import TabsNav from '@/components/common/TabsNav.vue'
import { useRoute, useRouter } from 'vue-router'
import { portfolioApi, deploymentApi } from '@/api'
import { message } from '@/utils/toast'
import { copyText } from '@/utils/clipboard'
import DeployModal from '@/components/business/DeployModal.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'

const route = useRoute()
const router = useRouter()

const portfolioId = computed(() => route.params.id as string)
const portfolioName = ref('加载中...')
const portfolioStatus = ref('')
const deploymentSource = ref<any>(null)
const stopConfirmOpen = ref(false)
const stopping = ref(false)

const statusLabels: Record<string, string> = {
  live: '实盘',
  paper: '模拟',
  idle: '空闲',
}

const statusLabel = computed(() => statusLabels[portfolioStatus.value] || '')

// 短 id 展示 + 点击复制完整值(32 位全显挤占 meta 区)
// http 局域网部署 clipboard API 不可用,copyText 内含 execCommand 降级
async function copyPortfolioId() {
  if (await copyText(portfolioId.value)) message.success('已复制完整 ID')
  else message.info(`ID: ${portfolioId.value}`)
}

const tabs = computed(() => {
  const base = [
    { key: 'overview', label: '概况', to: `/portfolios/${portfolioId.value}` },
  ]
  if (portfolioStatus.value === 'paper') {
    base.push({ key: 'paper', label: '运行', to: `/portfolios/${portfolioId.value}/paper` })
  }
  if (portfolioStatus.value === 'live') {
    base.push({ key: 'live', label: '运行', to: `/portfolios/${portfolioId.value}/live` })
  }
  base.push(
    { key: 'backtests', label: '回测', to: `/portfolios/${portfolioId.value}/backtests` },
    { key: 'validation', label: '验证', to: `/portfolios/${portfolioId.value}/validation` },
    { key: 'components', label: '组件', to: `/portfolios/${portfolioId.value}/components` },
  )
  return base
})

function startBacktest() {
  router.push(`/portfolios/${portfolioId.value}/backtests?action=create`)
}

// 停止为不可逆操作(撤销未成交委托/终止运行),需二次确认
function handleStop() {
  stopConfirmOpen.value = true
}

async function doStop() {
  stopping.value = true
  try {
    await portfolioApi.stop(portfolioId.value)
    message.success('停止命令已发送')
    stopConfirmOpen.value = false
    loadPortfolio()
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '停止失败')
  } finally {
    stopping.value = false
  }
}

async function loadPortfolio() {
  try {
    const res: any = await portfolioApi.get(portfolioId.value)
    const p = res
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
    // 拦截器已拆信封:payload 即部署信息本身(无 .data 包装)
    const res = await deploymentApi.getStatus(portfolioId.value)
    deploymentSource.value = res || null
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
.portfolio-id {
  font-size: 12px;
  color: hsl(var(--muted-foreground));
  font-family: monospace;
  user-select: all;
  cursor: pointer;
}
.portfolio-id:hover { color: hsl(var(--primary)); }


.status-tag {
  padding: 2px 10px;
  border-radius: var(--radius-lg);
  font-size: 12px;
  font-weight: 500;
}
.status-tag.live { background: hsl(var(--success) / 0.15); color: hsl(var(--success)); }
.status-tag.paper { background: hsl(var(--primary) / 0.15); color: hsl(var(--primary)); }
.status-tag.idle { background: hsl(var(--foreground) / 0.1); color: hsl(var(--muted-foreground)); }

.deploy-source {
  font-size: 11px;
  color: hsl(var(--muted-foreground));
  background: hsl(var(--muted) / 0.4);
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  font-family: monospace;
}

.btn-secondary {
  padding: 8px 16px;
  background: transparent;
  border: 1px solid hsl(var(--secondary));
  border-radius: var(--radius);
  color: hsl(var(--foreground));
  font-size: 13px;
  cursor: pointer;
}
.btn-secondary:hover { border-color: hsl(var(--primary)); }

.btn-deploy {
  padding: 8px 16px;
  background: transparent;
  border: 1px solid hsl(var(--success));
  border-radius: var(--radius);
  color: hsl(var(--success));
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}
.btn-deploy:hover { background: hsl(var(--success)); color: hsl(var(--foreground)); }

.btn-stop {
  padding: 8px 16px;
  border-radius: var(--radius);
  border: 1px solid hsl(var(--warning));
  background: hsl(var(--muted));
  color: hsl(var(--warning));
  cursor: pointer;
  font-size: 13px;
}
.btn-stop:hover {
  background: hsl(var(--muted));
}

.tab-content {
  flex: 1;
  overflow: auto;
  padding-top: 16px;
}
</style>
