<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { RefreshCw, Pause, Square, AlertTriangle, Activity, Clock, Settings } from 'lucide-vue-next'
import PageLayout from '@/components/common/PageLayout.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import { brokerApi } from '@/api'
import { message } from '@/utils/toast'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'
import { useContextMenu, type MenuItem } from '@/composables/useContextMenu'

/** 卡片右键菜单(替代卡片内操作按钮;停止走菜单内置确认) */
const { open: openCtxMenu } = useContextMenu()
const openBrokerMenu = (e: MouseEvent, broker: BrokerInfo) => {
  const items: MenuItem[] = []
  if (['uninitialized', 'stopped', 'error'].includes(broker.state)) {
    items.push({ label: '启动', action: () => startBroker(broker.uuid) })
  }
  if (broker.state === 'running') {
    items.push({ label: '暂停', action: () => pauseBroker(broker.uuid) })
  }
  if (broker.state === 'paused') {
    items.push({ label: '恢复', action: () => resumeBroker(broker.uuid) })
  }
  if (['running', 'paused', 'initializing'].includes(broker.state)) {
    items.push({ divider: true })
    items.push({
      label: '停止', danger: true,
      confirm: '停止将终止该 Broker 实例的运行。此操作不可逆,确定要继续吗?',
      action: () => doStopDirect(broker.uuid),
    })
  }
  if (items.length === 0) items.push({ label: '刷新', action: loadBrokers })
  openCtxMenu(e, items)
}

// Types
interface BrokerInfo {
  uuid: string
  portfolio_id: string
  live_account_id: string
  state: 'uninitialized' | 'initializing' | 'running' | 'paused' | 'stopped' | 'error'
  process_id?: number
  error_message?: string
  create_at: string
  update_at: string
  live_account?: {
    uuid: string
    name: string
    exchange: string
    environment: string
  }
}

// 状态
const brokers = ref<BrokerInfo[]>([])
const loading = ref(true)
const actionLoading = ref<string | null>(null)
const loadError = ref(false)  // 后端 /accounts/brokers 接口不可用(404=功能未实现)
// 紧急停止 二次确认态
const emergencyConfirmOpen = ref(false)
const emergencyLoading = ref(false)

// 状态配置
const stateConfig: Record<string, {
  label: string;
  variant: 'success' | 'secondary' | 'destructive' | 'outline';
  icon: any;
  color: string;
  bgColor: string;
}> = {
  uninitialized: {
    label: '未初始化',
    variant: 'secondary',
    icon: Settings,
    color: 'hsl(var(--muted-foreground))',
    bgColor: 'hsl(var(--muted-foreground) / 0.1)'
  },
  initializing: {
    label: '初始化中',
    variant: 'outline',
    icon: Activity,
    color: 'hsl(var(--warning))',
    bgColor: 'hsl(var(--warning) / 0.1)'
  },
  running: {
    label: '运行中',
    variant: 'success',
    icon: Activity,
    color: 'hsl(var(--success))',
    bgColor: 'hsl(var(--success) / 0.1)'
  },
  paused: {
    label: '已暂停',
    variant: 'secondary',
    icon: Pause,
    color: 'hsl(var(--warning))',
    bgColor: 'hsl(var(--warning) / 0.1)'
  },
  stopped: {
    label: '已停止',
    variant: 'secondary',
    icon: Square,
    color: 'hsl(var(--muted-foreground))',
    bgColor: 'hsl(var(--muted-foreground) / 0.1)'
  },
  error: {
    label: '错误',
    variant: 'destructive',
    icon: AlertTriangle,
    color: 'hsl(var(--error))',
    bgColor: 'hsl(var(--error) / 0.1)'
  }
}

// 加载 Broker 列表
const loadBrokers = async () => {
  loading.value = true
  try {
    loadError.value = false
    const result = await brokerApi.list()
    brokers.value = (result as any) || []
  } catch (error) {
    // 后端 /accounts/brokers 待实现(实盘 broker stub 阶段),诚实标注而非笼统"加载失败"
    loadError.value = true
    console.warn('Broker 实例加载失败(后端接口待实现):', error)
  } finally {
    loading.value = false
  }
}

// Broker 操作
const startBroker = async (brokerUuid: string) => {
  actionLoading.value = brokerUuid
  try {
    await brokerApi.start(brokerUuid)
    await loadBrokers()
  } catch (error: any) {
    message.error(error?.message || '启动失败')
  } finally {
    actionLoading.value = null
  }
}

const pauseBroker = async (brokerUuid: string) => {
  actionLoading.value = brokerUuid
  try {
    await brokerApi.pause(brokerUuid)
    await loadBrokers()
  } catch (error: any) {
    message.error(error?.message || '暂停失败')
  } finally {
    actionLoading.value = null
  }
}

const resumeBroker = async (brokerUuid: string) => {
  actionLoading.value = brokerUuid
  try {
    await brokerApi.resume(brokerUuid)
    await loadBrokers()
  } catch (error: any) {
    message.error(error?.message || '恢复失败')
  } finally {
    actionLoading.value = null
  }
}

// 停止单个 Broker(确认由菜单内置 ConfirmDialog 承担)
const doStopDirect = async (brokerUuid: string) => {
  actionLoading.value = brokerUuid
  try {
    await brokerApi.stop(brokerUuid)
    message.success('已停止该 Broker')
    await loadBrokers()
  } catch (error: any) {
    message.error(error?.message || '停止失败')
  } finally {
    actionLoading.value = null
  }
}

// 紧急停止全部:打开二次确认(全量终止,不可逆,危险)
const handleEmergencyClick = () => {
  emergencyConfirmOpen.value = true
}

const doEmergencyStop = async () => {
  emergencyLoading.value = true
  try {
    await brokerApi.emergencyStop()
    message.success('已发送紧急停止指令')
    emergencyConfirmOpen.value = false
    await loadBrokers()
  } catch (error: any) {
    message.error(error?.message || '紧急停止失败')
  } finally {
    emergencyLoading.value = false
  }
}

// 格式化时间
const formatTime = (timeStr: string) => {
  const date = new Date(timeStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)

  if (diffMins < 1) return '刚刚'
  if (diffMins < 60) return `${diffMins} 分钟前`
  if (diffMins < 1440) return `${Math.floor(diffMins / 60)} 小时前`
  return date.toLocaleString()
}

const getBrokerId = (uuid: string) => uuid.slice(0, 8)

onMounted(() => {
  loadBrokers()
})
</script>

<template>
  <PageLayout>
    <template #title>Broker 管理</template>
    <template #description>管理实盘 Broker 实例的生命周期</template>
    <template #actions>
      <Button
        variant="destructive"
        size="sm"
        class="emergency-btn"
        @click="handleEmergencyClick"
      >
        <Square class="w-4 h-4 mr-2" />
        紧急停止全部
      </Button>
      <Button
        variant="outline"
        size="sm"
        class="refresh-btn"
        :disabled="loading"
        @click="loadBrokers"
      >
        <RefreshCw :class="['w-4 h-4 mr-2', loading && 'animate-spin']" />
        刷新
      </Button>
    </template>

    <Card class="broker-card">
      <CardContent class="broker-content">
        <!-- 加载状态 -->
        <div v-if="loading" class="loading-state">
          <RefreshCw class="w-8 h-8 animate-spin text-muted-foreground" />
          <p class="text-muted-foreground">加载中...</p>
        </div>

        <!-- 功能未实现(后端接口 404) -->
        <EmptyState
          v-else-if="loadError"
          title="实盘 Broker 管理功能开发中"
          description="实盘引擎就绪后启用(后端接口待实现)"
        >
          <template #icon><AlertTriangle class="w-16 h-16" /></template>
        </EmptyState>

        <!-- 空状态 -->
        <EmptyState
          v-else-if="brokers.length === 0"
          title="暂无 Broker 实例"
          description="Broker 实例会在创建实盘组合后自动创建"
        >
          <template #icon><Settings class="w-16 h-16" /></template>
        </EmptyState>

        <!-- Broker 列表 -->
        <div v-else class="broker-list">
          <div
            v-for="broker in brokers"
            :key="broker.uuid"
            class="broker-item"
            :class="{ 'has-error': broker.state === 'error' }"
            @contextmenu="openBrokerMenu($event, broker)"
          >
            <!-- 状态指示器 -->
            <div class="broker-status-indicator" :style="{ backgroundColor: stateConfig[broker.state]?.bgColor }">
              <component :is="stateConfig[broker.state]?.icon" class="status-icon" :style="{ color: stateConfig[broker.state]?.color }" />
            </div>

            <!-- Broker 主要信息 -->
            <div class="broker-main">
              <div class="broker-header-row">
                <div class="broker-title-row">
                  <h3 class="broker-name">Broker {{ getBrokerId(broker.uuid) }}</h3>
                  <Badge
                    :variant="stateConfig[broker.state]?.variant || 'secondary'"
                    class="state-badge"
                    :style="{
                      backgroundColor: stateConfig[broker.state]?.bgColor,
                      color: stateConfig[broker.state]?.color,
                      border: 'none'
                    }"
                  >
                    <component :is="stateConfig[broker.state]?.icon" class="w-3 h-3 mr-1" />
                    {{ stateConfig[broker.state]?.label || broker.state }}
                  </Badge>
                </div>

                <!-- 账号信息 -->
                <div v-if="broker.live_account" class="account-info">
                  <span class="account-name">{{ broker.live_account.name }}</span>
                  <Badge variant="outline" class="exchange-badge">
                    {{ broker.live_account.exchange.toUpperCase() }}
                  </Badge>
                  <Badge
                    :variant="broker.live_account.environment === 'production' ? 'destructive' : 'secondary'"
                    class="env-badge"
                  >
                    {{ broker.live_account.environment === 'production' ? '实盘' : '模拟' }}
                  </Badge>
                </div>

                <!-- 进程信息 -->
                <div v-if="broker.process_id" class="process-info">
                  <Clock class="w-3 h-3 mr-1" />
                  <span class="text-xs text-muted-foreground">PID: {{ broker.process_id }}</span>
                </div>
              </div>

            </div>

            <!-- 错误信息 -->
            <div v-if="broker.error_message" class="error-message">
              <AlertTriangle class="w-4 h-4 mr-2" />
              {{ broker.error_message }}
            </div>

            <!-- 时间信息 -->
            <div class="broker-time">
              <span class="time-label">创建于 {{ formatTime(broker.create_at) }}</span>
              <span v-if="broker.update_at" class="time-label">更新于 {{ formatTime(broker.update_at) }}</span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
    <ConfirmDialog
      v-model:open="emergencyConfirmOpen"
      title="紧急停止全部 Broker"
      description="将立即停止所有正在运行的 Broker 实例。此操作不可逆且影响范围最大,确定要继续吗?"
      danger
      confirm-text="紧急停止全部"
      :loading="emergencyLoading"
      @confirm="doEmergencyStop"
    />
  </PageLayout>
</template>

<style scoped>
.broker-card {
  background: linear-gradient(135deg, hsl(var(--card)) 0%, hsl(var(--card)) 100%);
  border: 1px solid hsl(var(--border));
  box-shadow: var(--shadow-lg);
}

.emergency-btn {
  background: linear-gradient(135deg, hsl(var(--error)) 0%, hsl(var(--error)) 100%);
  border: none;
}

.emergency-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, hsl(var(--error)) 0%, hsl(var(--error)) 100%);
}

.refresh-btn {
  border-color: hsl(var(--border));
  color: hsl(var(--muted-foreground));
}

.refresh-btn:hover:not(:disabled) {
  background: hsl(var(--foreground) / 0.05);
  border-color: hsl(var(--foreground) / 0.3);
}

.broker-content {
  padding: 20px 0;
}

.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  gap: 16px;
}

.broker-list {
  display: grid;
  gap: 16px;
}

.broker-item {
  position: relative;
  background: hsl(var(--foreground) / 0.03);
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius-lg);
  padding: 20px;
  transition: all 0.2s ease;
}

.broker-item:hover {
  background: hsl(var(--foreground) / 0.05);
  border-color: hsl(var(--foreground) / 0.12);
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}

.broker-item.has-error {
  border-color: hsl(var(--error) / 0.3);
  background: hsl(var(--error) / 0.05);
}

.broker-status-indicator {
  position: absolute;
  left: 20px;
  top: 24px;
  width: 40px;
  height: 40px;
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
}

.status-icon {
  width: 20px;
  height: 20px;
}

.broker-main {
  margin-left: 60px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 24px;
}

.broker-header-row {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.broker-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.broker-name {
  font-size: 16px;
  font-weight: 600;
  color: hsl(var(--foreground));
  margin: 0;
}

.state-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 12px;
  font-size: 12px;
  font-weight: 500;
  border-radius: var(--radius);
}

.account-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.account-name {
  font-size: 14px;
  color: hsl(var(--muted-foreground));
  font-weight: 500;
}

.exchange-badge,
.env-badge {
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 600;
  border-radius: var(--radius-sm);
  text-transform: uppercase;
}

.exchange-badge {
  background: hsl(var(--primary) / 0.1);
  color: hsl(var(--primary));
  border: 1px solid hsl(var(--primary) / 0.2);
}

.env-badge {
  background: hsl(var(--success) / 0.1);
  color: hsl(var(--success));
  border: 1px solid hsl(var(--success) / 0.2);
}

.env-badge:deep(.destructive) {
  background: hsl(var(--error) / 0.1);
  color: hsl(var(--error));
  border-color: hsl(var(--error) / 0.2);
}

.process-info {
  display: flex;
  align-items: center;
  gap: 8px;
  color: hsl(var(--muted-foreground));
  font-size: 12px;
}

.error-message {
  margin-top: 12px;
  padding: 12px;
  background: hsl(var(--error) / 0.1);
  border: 1px solid hsl(var(--error) / 0.3);
  border-radius: var(--radius-lg);
  color: hsl(var(--error));
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.broker-time {
  margin-top: 16px;
  margin-left: 60px;
  padding-top: 16px;
  border-top: 1px solid hsl(var(--border));
  display: flex;
  gap: 16px;
}

.time-label {
  font-size: 12px;
  color: hsl(var(--muted-foreground));
}

/* 响应式 */
@media (max-width: 768px) {
  .broker-main {
    flex-direction: column;
    gap: 16px;
  }

  .broker-time {
    margin-left: 0;
    flex-direction: column;
    gap: 8px;
  }

  .broker-status-indicator {
    position: static;
    margin-bottom: 12px;
  }
}
</style>
