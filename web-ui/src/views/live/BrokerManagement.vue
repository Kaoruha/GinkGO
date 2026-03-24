<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { RefreshCw, Play, Pause, Square, AlertTriangle, Activity, Clock, Settings } from 'lucide-vue-next'

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
    color: '#6b7280',
    bgColor: 'rgba(107, 114, 128, 0.1)'
  },
  initializing: {
    label: '初始化中',
    variant: 'outline',
    icon: Activity,
    color: '#f59e0b',
    bgColor: 'rgba(245, 158, 11, 0.1)'
  },
  running: {
    label: '运行中',
    variant: 'success',
    icon: Activity,
    color: '#10b981',
    bgColor: 'rgba(16, 185, 129, 0.1)'
  },
  paused: {
    label: '已暂停',
    variant: 'secondary',
    icon: Pause,
    color: '#f59e0b',
    bgColor: 'rgba(245, 158, 11, 0.1)'
  },
  stopped: {
    label: '已停止',
    variant: 'secondary',
    icon: Square,
    color: '#6b7280',
    bgColor: 'rgba(107, 114, 128, 0.1)'
  },
  error: {
    label: '错误',
    variant: 'destructive',
    icon: AlertTriangle,
    color: '#ef4444',
    bgColor: 'rgba(239, 68, 68, 0.1)'
  }
}

// 加载 Broker 列表
const loadBrokers = async () => {
  loading.value = true
  try {
    const response = await fetch('/api/v1/accounts/brokers')
    if (response.ok) {
      const result = await response.json()
      brokers.value = result.data || []
    }
  } catch (error) {
    console.error('Failed to load brokers:', error)
  } finally {
    loading.value = false
  }
}

// Broker 操作
const startBroker = async (brokerUuid: string) => {
  actionLoading.value = brokerUuid
  try {
    const response = await fetch(`/api/v1/accounts/brokers/${brokerUuid}/start`, {
      method: 'POST'
    })
    if (response.ok) {
      await loadBrokers()
    } else {
      const error = await response.json()
      alert(error.message || '启动失败')
    }
  } catch (error) {
    console.error('Failed to start broker:', error)
    alert('启动失败')
  } finally {
    actionLoading.value = null
  }
}

const pauseBroker = async (brokerUuid: string) => {
  actionLoading.value = brokerUuid
  try {
    const response = await fetch(`/api/v1/accounts/brokers/${brokerUuid}/pause`, {
      method: 'POST'
    })
    if (response.ok) {
      await loadBrokers()
    } else {
      const error = await response.json()
      alert(error.message || '暂停失败')
    }
  } catch (error) {
    console.error('Failed to pause broker:', error)
    alert('暂停失败')
  } finally {
    actionLoading.value = null
  }
}

const resumeBroker = async (brokerUuid: string) => {
  actionLoading.value = brokerUuid
  try {
    const response = await fetch(`/api/v1/accounts/brokers/${brokerUuid}/resume`, {
      method: 'POST'
    })
    if (response.ok) {
      await loadBrokers()
    } else {
      const error = await response.json()
      alert(error.message || '恢复失败')
    }
  } catch (error) {
    console.error('Failed to resume broker:', error)
    alert('恢复失败')
  } finally {
    actionLoading.value = null
  }
}

const stopBroker = async (brokerUuid: string) => {
  if (!confirm('确定要停止此 Broker 吗？')) return

  actionLoading.value = brokerUuid
  try {
    const response = await fetch(`/api/v1/accounts/brokers/${brokerUuid}/stop`, {
      method: 'POST'
    })
    if (response.ok) {
      await loadBrokers()
    } else {
      const error = await response.json()
      alert(error.message || '停止失败')
    }
  } catch (error) {
    console.error('Failed to stop broker:', error)
    alert('停止失败')
  } finally {
    actionLoading.value = null
  }
}

const emergencyStopAll = async () => {
  if (!confirm('确定要紧急停止所有 Broker 吗？此操作不可逆！')) return

  try {
    const response = await fetch('/api/v1/accounts/brokers/emergency-stop', {
      method: 'POST'
    })
    if (response.ok) {
      const result = await response.json()
      alert(result.message || '已紧急停止所有 Broker')
      await loadBrokers()
    } else {
      alert('紧急停止失败')
    }
  } catch (error) {
    console.error('Failed to emergency stop:', error)
    alert('紧急停止失败')
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
  <div class="broker-management">
    <Card class="broker-card">
      <CardHeader class="broker-header">
        <div class="header-content">
          <div class="header-left">
            <CardTitle class="title">Broker 管理</CardTitle>
            <CardDescription class="description">管理实盘 Broker 实例的生命周期</CardDescription>
          </div>
          <div class="header-actions">
            <Button
              variant="destructive"
              size="sm"
              class="emergency-btn"
              @click="emergencyStopAll"
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
          </div>
        </div>
      </CardHeader>

      <CardContent class="broker-content">
        <!-- 加载状态 -->
        <div v-if="loading" class="loading-state">
          <RefreshCw class="w-8 h-8 animate-spin text-muted-foreground" />
          <p class="text-muted-foreground">加载中...</p>
        </div>

        <!-- 空状态 -->
        <div v-else-if="brokers.length === 0" class="empty-state">
          <Settings class="w-16 h-16 mx-auto mb-4 text-muted-foreground opacity-50" />
          <p class="text-lg font-medium text-muted-foreground">暂无 Broker 实例</p>
          <p class="text-sm text-muted-foreground mt-2">Broker 实例会在创建实盘组合后自动创建</p>
        </div>

        <!-- Broker 列表 -->
        <div v-else class="broker-list">
          <div
            v-for="broker in brokers"
            :key="broker.uuid"
            class="broker-item"
            :class="{ 'has-error': broker.state === 'error' }"
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

              <!-- 操作按钮 -->
              <div class="broker-actions">
                <!-- 启动 -->
                <Button
                  v-if="['uninitialized', 'stopped', 'error'].includes(broker.state)"
                  variant="default"
                  size="sm"
                  class="action-btn start-btn"
                  :disabled="actionLoading === broker.uuid"
                  @click="startBroker(broker.uuid)"
                >
                  <Play :class="['w-4 h-4 mr-2', actionLoading === broker.uuid && 'animate-spin']" />
                  启动
                </Button>

                <!-- 暂停 -->
                <Button
                  v-if="broker.state === 'running'"
                  variant="outline"
                  size="sm"
                  class="action-btn pause-btn"
                  :disabled="actionLoading === broker.uuid"
                  @click="pauseBroker(broker.uuid)"
                >
                  <Pause class="w-4 h-4 mr-2" />
                  暂停
                </Button>

                <!-- 恢复 -->
                <Button
                  v-if="broker.state === 'paused'"
                  variant="default"
                  size="sm"
                  class="action-btn resume-btn"
                  :disabled="actionLoading === broker.uuid"
                  @click="resumeBroker(broker.uuid)"
                >
                  <Play :class="['w-4 h-4 mr-2', actionLoading === broker.uuid && 'animate-spin']" />
                  恢复
                </Button>

                <!-- 停止 -->
                <Button
                  v-if="['running', 'paused', 'initializing'].includes(broker.state)"
                  variant="destructive"
                  size="sm"
                  class="action-btn stop-btn"
                  :disabled="actionLoading === broker.uuid"
                  @click="stopBroker(broker.uuid)"
                >
                  <Square class="w-4 h-4 mr-2" />
                  停止
                </Button>
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
  </div>
</template>

<style scoped>
.broker-management {
  max-width: 1400px;
  margin: 0 auto;
  padding: 24px;
}

.broker-card {
  background: linear-gradient(135deg, #1a1a2e 0%, #16162a 100%);
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
}

.broker-header {
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  padding-bottom: 16px;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 24px;
}

.header-left {
  flex: 1;
}

.title {
  font-size: 24px;
  font-weight: 700;
  color: #ffffff;
  margin-bottom: 4px;
}

.description {
  color: #8a8a9a;
  font-size: 14px;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.emergency-btn {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  border: none;
}

.emergency-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
}

.refresh-btn {
  border-color: rgba(255, 255, 255, 0.2);
  color: #a1a1aa;
}

.refresh-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.3);
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
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 20px;
  transition: all 0.2s ease;
}

.broker-item:hover {
  background: rgba(255, 255, 255, 0.05);
  border-color: rgba(255, 255, 255, 0.12);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
}

.broker-item.has-error {
  border-color: rgba(239, 68, 68, 0.3);
  background: rgba(239, 68, 68, 0.05);
}

.broker-status-indicator {
  position: absolute;
  left: 20px;
  top: 24px;
  width: 40px;
  height: 40px;
  border-radius: 10px;
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
  color: #ffffff;
  margin: 0;
}

.state-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 12px;
  font-size: 12px;
  font-weight: 500;
  border-radius: 6px;
}

.account-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.account-name {
  font-size: 14px;
  color: #d1d5db;
  font-weight: 500;
}

.exchange-badge,
.env-badge {
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 600;
  border-radius: 4px;
  text-transform: uppercase;
}

.exchange-badge {
  background: rgba(59, 130, 246, 0.1);
  color: #3b82f6;
  border: 1px solid rgba(59, 130, 246, 0.2);
}

.env-badge {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
  border: 1px solid rgba(16, 185, 129, 0.2);
}

.env-badge:deep(.destructive) {
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
  border-color: rgba(239, 68, 68, 0.2);
}

.process-info {
  display: flex;
  align-items: center;
  color: #8a8a9a;
  font-size: 12px;
}

.broker-actions {
  display: flex;
  gap: 8px;
}

.action-btn {
  min-width: 80px;
}

.start-btn {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  border: none;
}

.start-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #059669 0%, #047857 100%);
}

.pause-btn {
  border-color: rgba(245, 158, 11, 0.3);
  color: #f59e0b;
}

.pause-btn:hover:not(:disabled) {
  background: rgba(245, 158, 11, 0.1);
}

.resume-btn {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  border: none;
}

.resume-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
}

.stop-btn {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  border: none;
}

.stop-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
}

.error-message {
  margin-top: 12px;
  padding: 12px;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.3);
  border-radius: 8px;
  color: #fca5a5;
  font-size: 13px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.broker-time {
  margin-top: 16px;
  margin-left: 60px;
  padding-top: 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  display: flex;
  gap: 16px;
}

.time-label {
  font-size: 12px;
  color: #6b7280;
}

/* 响应式 */
@media (max-width: 768px) {
  .broker-management {
    padding: 16px;
  }

  .header-content {
    flex-direction: column;
    align-items: stretch;
    gap: 16px;
  }

  .header-actions {
    flex-direction: column;
  }

  .broker-main {
    flex-direction: column;
    gap: 16px;
  }

  .broker-actions {
    width: 100%;
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

@media (prefers-color-scheme: light) {
  .broker-card {
    background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
    border-color: rgba(0, 0, 0, 0.1);
  }

  .title {
    color: #1a1a2e;
  }

  .description {
    color: #64748b;
  }

  .broker-item {
    background: #ffffff;
    border-color: rgba(0, 0, 0, 0.08);
  }

  .broker-item:hover {
    background: #f8fafc;
  }

  .broker-name {
    color: #1a1a2e;
  }

  .account-name {
    color: #4b5563;
  }

  .time-label {
    color: #9ca3af;
  }
}
</style>
