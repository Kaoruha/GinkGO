<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import {
  DialogRoot,
  DialogPortal,
  DialogOverlay,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { AlertCircle, Square, Play, Pause } from 'lucide-vue-next'

// Types
interface BrokerInstance {
  uuid: string
  portfolio_id: string
  live_account_id: string
  state: string
  process_id: number | null
  heartbeat_at: string | null
  error_message: string | null
  error_count: number
  total_submitted: number
  total_filled: number
  total_cancelled: number
  total_rejected: number
  last_order_at: string | null
  live_account?: {
    uuid: string
    name: string
    exchange: string
    environment: string
  }
}

// 状态
const brokers = ref<BrokerInstance[]>([])
const loading = ref(true)
const showConfirmDialog = ref(false)
const confirmAction = ref<{ type: string; broker: BrokerInstance } | null>(null)
const processingAction = ref(false)

// Broker状态映射
const stateLabels: Record<string, { label: string; color: 'success' | 'info' | 'warning' | 'default' | 'destructive' | 'outline' | 'secondary' }> = {
  uninitialized: { label: '未初始化', color: 'secondary' },
  initializing: { label: '初始化中', color: 'warning' },
  running: { label: '运行中', color: 'success' },
  paused: { label: '已暂停', color: 'warning' },
  stopped: { label: '已停止', color: 'secondary' },
  error: { label: '错误', color: 'destructive' },
  recovering: { label: '恢复中', color: 'warning' }
}

// 加载Broker列表
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

// 启动Broker
const startBroker = async (broker: BrokerInstance) => {
  processingAction.value = true
  try {
    const response = await fetch(`/api/v1/accounts/brokers/${broker.uuid}/start`, {
      method: 'POST'
    })
    if (response.ok) {
      await loadBrokers()
    }
  } finally {
    processingAction.value = false
  }
}

// 暂停Broker
const pauseBroker = async (broker: BrokerInstance) => {
  processingAction.value = true
  try {
    const response = await fetch(`/api/v1/accounts/brokers/${broker.uuid}/pause`, {
      method: 'POST'
    })
    if (response.ok) {
      await loadBrokers()
    }
  } finally {
    processingAction.value = false
  }
}

// 恢复Broker
const resumeBroker = async (broker: BrokerInstance) => {
  processingAction.value = true
  try {
    const response = await fetch(`/api/v1/accounts/brokers/${broker.uuid}/resume`, {
      method: 'POST'
    })
    if (response.ok) {
      await loadBrokers()
    }
  } finally {
    processingAction.value = false
  }
}

// 停止Broker
const stopBroker = async (broker: BrokerInstance) => {
  processingAction.value = true
  try {
    const response = await fetch(`/api/v1/accounts/brokers/${broker.uuid}/stop`, {
      method: 'POST'
    })
    if (response.ok) {
      await loadBrokers()
    }
  } finally {
    processingAction.value = false
  }
}

// 确认对话框操作
const confirmDialogAction = () => {
  if (!confirmAction.value) return

  const { type, broker } = confirmAction.value

  switch (type) {
    case 'start':
      startBroker(broker)
      break
    case 'pause':
      pauseBroker(broker)
      break
    case 'resume':
      resumeBroker(broker)
      break
    case 'stop':
      stopBroker(broker)
      break
    case 'emergency_stop_all':
      emergencyStopAll()
      break
  }

  showConfirmDialog.value = false
  confirmAction.value = null
}

// 请求确认
const requestConfirm = (type: string, broker: BrokerInstance) => {
  confirmAction.value = { type, broker }
  showConfirmDialog.value = true
}

// 紧急停止所有
const emergencyStopAll = async () => {
  processingAction.value = true
  try {
    const response = await fetch('/api/v1/accounts/brokers/emergency-stop', {
      method: 'POST'
    })
    if (response.ok) {
      await loadBrokers()
    }
  } finally {
    processingAction.value = false
  }
}

// 获取Broker状态显示
const getStateDisplay = (broker: BrokerInstance) => {
  const state = stateLabels[broker.state] || { label: broker.state, color: 'secondary' }
  return state
}

// 检查心跳超时
const isHeartbeatTimeout = (broker: BrokerInstance) => {
  if (!broker.heartbeat_at) return false
  const heartbeat = new Date(broker.heartbeat_at)
  const now = new Date()
  const elapsed = (now.getTime() - heartbeat.getTime()) / 1000
  return elapsed > 30  // 30秒超时
}

// 计算成交率
const fillRate = (broker: BrokerInstance) => {
  if (broker.total_submitted === 0) return '0%'
  return ((broker.total_filled / broker.total_submitted) * 100).toFixed(2) + '%'
}

// 组件挂载
onMounted(() => {
  loadBrokers()
  // 定期刷新
  const interval = setInterval(loadBrokers, 5000)
  onUnmounted(() => clearInterval(interval))
})
</script>

<template>
  <div class="trading-control">
    <Card>
      <CardHeader>
        <CardTitle>实盘交易控制</CardTitle>
        <CardDescription>管理和监控Broker实例状态</CardDescription>
      </CardHeader>

      <CardContent>
        <!-- 全局操作 -->
        <div class="flex justify-end mb-4">
          <Button
            variant="destructive"
            :disabled="processingAction"
            @click="requestConfirm('emergency_stop_all', {} as any)"
          >
            <AlertCircle class="w-4 h-4 mr-2" />
            紧急停止全部
          </Button>
        </div>

        <!-- Broker列表 -->
        <div v-if="loading" class="text-center py-8">
          <p>加载中...</p>
        </div>

        <div v-else-if="brokers.length === 0" class="text-center py-8 text-muted-foreground">
          <p>暂无Broker实例</p>
        </div>

        <Table v-else>
          <TableHeader>
            <TableRow>
              <TableHead>Portfolio</TableHead>
              <TableHead>实盘账号</TableHead>
              <TableHead>状态</TableHead>
              <TableHead>心跳</TableHead>
              <TableHead>提交/成交</TableHead>
              <TableHead>成交率</TableHead>
              <TableHead>操作</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            <TableRow
              v-for="broker in brokers"
              :key="broker.uuid"
            >
              <TableCell>{{ broker.portfolio_id.slice(0, 8) }}...</TableCell>

              <TableCell>
                <div v-if="broker.live_account">
                  <div class="font-medium">{{ broker.live_account.name }}</div>
                  <div class="text-sm text-muted-foreground">
                    {{ broker.live_account.exchange }} / {{ broker.live_account.environment }}
                  </div>
                </div>
                <span v-else class="text-muted-foreground">-</span>
              </TableCell>

              <TableCell>
                <Badge :variant="getStateDisplay(broker).color">
                  {{ getStateDisplay(broker).label }}
                </Badge>
                <div v-if="broker.error_message" class="text-xs text-destructive mt-1">
                  {{ broker.error_message }}
                </div>
              </TableCell>

              <TableCell>
                <div class="flex items-center gap-1">
                  <div
                    class="w-2 h-2 rounded-full"
                    :class="isHeartbeatTimeout(broker) ? 'bg-destructive' : 'bg-green-500'"
                  />
                  <span v-if="broker.heartbeat_at" class="text-xs text-muted-foreground">
                    {{ new Date(broker.heartbeat_at).toLocaleTimeString() }}
                  </span>
                  <span v-else class="text-xs text-muted-foreground">未连接</span>
                </div>
              </TableCell>

              <TableCell>
                {{ broker.total_submitted }} / {{ broker.total_filled }}
              </TableCell>

              <TableCell>
                {{ fillRate(broker) }}
              </TableCell>

              <TableCell>
                <div class="flex gap-1">
                  <!-- 启动按钮 -->
                  <Button
                    v-if="broker.state === 'uninitialized' || broker.state === 'stopped'"
                    size="sm"
                    variant="default"
                    :disabled="processingAction"
                    @click="requestConfirm('start', broker)"
                  >
                    <Play class="w-3 h-3" />
                  </Button>

                  <!-- 暂停按钮 -->
                  <Button
                    v-if="broker.state === 'running'"
                    size="sm"
                    variant="outline"
                    :disabled="processingAction"
                    @click="requestConfirm('pause', broker)"
                  >
                    <Pause class="w-3 h-3" />
                  </Button>

                  <!-- 恢复按钮 -->
                  <Button
                    v-if="broker.state === 'paused'"
                    size="sm"
                    variant="default"
                    :disabled="processingAction"
                    @click="requestConfirm('resume', broker)"
                  >
                    <Play class="w-3 h-3" />
                  </Button>

                  <!-- 停止按钮 -->
                  <Button
                    v-if="broker.state === 'running' || broker.state === 'paused'"
                    size="sm"
                    variant="outline"
                    :disabled="processingAction"
                    @click="requestConfirm('stop', broker)"
                  >
                    <Square class="w-3 h-3" />
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>

        <!-- 统计信息 -->
        <div class="mt-4 grid grid-cols-4 gap-4">
          <Card>
            <CardContent class="p-4">
              <div class="text-2xl font-bold">{{ brokers.length }}</div>
              <div class="text-sm text-muted-foreground">总实例数</div>
            </CardContent>
          </Card>

          <Card>
            <CardContent class="p-4">
              <div class="text-2xl font-bold text-green-600">
                {{ brokers.filter(b => b.state === 'running').length }}
              </div>
              <div class="text-sm text-muted-foreground">运行中</div>
            </CardContent>
          </Card>

          <Card>
            <CardContent class="p-4">
              <div class="text-2xl font-bold">
                {{ brokers.reduce((sum, b) => sum + b.total_submitted, 0) }}
              </div>
              <div class="text-sm text-muted-foreground">总提交订单</div>
            </CardContent>
          </Card>

          <Card>
            <CardContent class="p-4">
              <div class="text-2xl font-bold text-blue-600">
                {{ brokers.reduce((sum, b) => sum + b.total_filled, 0) }}
              </div>
              <div class="text-sm text-muted-foreground">总成交订单</div>
            </CardContent>
          </Card>
        </div>
      </CardContent>
    </Card>

    <!-- 确认对话框 -->
    <DialogRoot :open="showConfirmDialog" @update:open="showConfirmDialog = false">
      <DialogPortal>
        <DialogOverlay />
        <DialogContent>
          <DialogHeader>
            <DialogTitle>确认操作</DialogTitle>
            <DialogDescription>
              <span v-if="confirmAction?.type === 'emergency_stop_all'">
                确定要紧急停止所有Broker实例吗？此操作将立即停止所有正在运行的交易。
              </span>
              <span v-else-if="confirmAction?.broker">
                <span v-if="confirmAction.type === 'stop'">
                  确定要停止Broker {{ confirmAction.broker.portfolio_id.slice(0, 8) }}... 吗？
                </span>
                <span v-else-if="confirmAction.type === 'pause'">
                  确定要暂停Broker {{ confirmAction.broker.portfolio_id.slice(0, 8) }}... 吗？
                </span>
                <span v-else>
                  确定要{{ confirmAction.type === 'start' ? '启动' : '恢复' }}Broker吗？
                </span>
              </span>
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" @click="showConfirmDialog = false">取消</Button>
            <Button variant="destructive" @click="confirmDialogAction">
              确认
            </Button>
          </DialogFooter>
        </DialogContent>
      </DialogPortal>
    </DialogRoot>
  </div>
</template>

<style scoped>
.trading-control {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}
</style>
