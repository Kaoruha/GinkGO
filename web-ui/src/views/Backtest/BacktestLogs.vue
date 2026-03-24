<template>
  <div class="backtest-logs">
    <div class="card">
      <div class="card-header">
        <h3>回测日志</h3>
        <div class="header-actions">
          <select v-model="logLevel" class="form-select">
            <option value="all">全部</option>
            <option value="DEBUG">DEBUG</option>
            <option value="INFO">INFO</option>
            <option value="WARNING">WARNING</option>
            <option value="ERROR">ERROR</option>
          </select>
          <input v-model="dateRangeText" type="text" placeholder="选择日期范围" class="form-input" />
          <button class="btn-secondary" @click="clearLogs">清空</button>
          <button class="btn-secondary" @click="exportLogs">导出</button>
          <button class="btn-primary" :disabled="connecting" @click="connectStream">
            {{ connecting ? '连接中...' : (connected ? '已连接' : '连接日志流') }}
          </button>
        </div>
      </div>

      <div class="card-body">
        <div class="search-section">
          <input
            v-model="searchKeyword"
            type="text"
            placeholder="搜索日志内容"
            class="form-input"
            @keyup.enter="onSearch"
          />
        </div>

        <div ref="logsContainer" class="logs-container">
          <div
            v-for="(log, index) in filteredLogs"
            :key="index"
            class="log-entry"
            :class="`log-level-${log.level}`"
          >
            <span class="log-time">{{ formatTime(log.timestamp) }}</span>
            <span class="log-level">[{{ log.level }}]</span>
            <span class="log-message">{{ log.message }}</span>
            <span v-if="log.context" class="log-context">{{ log.context }}</span>
          </div>
        </div>

        <div class="log-stats">
          <span>共 {{ filteredLogs.length }} 条日志</span>
          <span v-if="hasNewLogs" class="new-logs-indicator">● 新日志</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const backtestId = route.params.uuid || ''

// 配置
const logLevel = ref('all')
const dateRangeText = ref('')
const searchKeyword = ref('')
const connecting = ref(false)
const connected = ref(false)

// 日志数据
const logs = ref<any[]>([])
const logsContainer = ref<HTMLDivElement>()
const hasNewLogs = ref(false)

// 模拟日志数据
const mockLogs = [
  { timestamp: '2024-01-10T09:30:00.000Z', level: 'INFO', message: '回测任务开始执行', context: 'BacktestEngine' },
  { timestamp: '2024-01-10T09:30:01.000Z', level: 'DEBUG', message: '加载数据: 000001.SZ', context: 'DataManager' },
  { timestamp: '2024-01-10T09:30:02.000Z', level: 'INFO', message: '计算技术指标', context: 'IndicatorCalculator' },
  { timestamp: '2024-01-10T09:30:03.000Z', level: 'WARNING', message: '数据缺失，跳过', context: 'DataValidator' },
  { timestamp: '2024-01-10T09:30:04.000Z', level: 'INFO', message: '生成交易信号', context: 'SignalGenerator' },
  { timestamp: '2024-01-10T09:30:05.000Z', level: 'DEBUG', message: '信号: BUY 000001.SZ @ 13.50', context: 'SignalExecutor' },
  { timestamp: '2024-01-10T09:30:06.000Z', level: 'INFO', message: '执行订单: 买入 100股', context: 'OrderExecutor' },
  { timestamp: '2024-01-10T09:30:07.000Z', level: 'INFO', message: '订单成交', context: 'FillHandler' },
  { timestamp: '2024-01-10T09:30:08.000Z', level: 'ERROR', message: '订单失败: 余额不足', context: 'OrderExecutor' }
]

// 过滤后的日志
const filteredLogs = computed(() => {
  let filtered = logs.value

  // 按级别过滤
  if (logLevel.value !== 'all') {
    filtered = filtered.filter(log => log.level === logLevel.value)
  }

  // 按关键词搜索
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    filtered = filtered.filter(log =>
      log.message.toLowerCase().includes(keyword) ||
      (log.context && log.context.toLowerCase().includes(keyword))
    )
  }

  return filtered
})

// 连接SSE日志流
const connectStream = async () => {
  if (connected.value) {
    connected.value = false
    return
  }

  connecting.value = true

  try {
    // 模拟连接过程
    await new Promise(resolve => setTimeout(resolve, 1000))

    // 模拟接收日志
    logs.value = [...mockLogs]
    connected.value = true
    console.log('日志流已连接')
  } catch (e) {
    console.error('连接日志流失败')
  } finally {
    connecting.value = false
  }
}

// 格式化时间
const formatTime = (timestamp: string) => {
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN', { hour12: false }) + '.' +
         String(date.getMilliseconds()).padStart(3, '0')
}

// 搜索
const onSearch = (value: string) => {
  searchKeyword.value = value
}

// 清空日志
const clearLogs = () => {
  logs.value = []
  hasNewLogs.value = false
}

// 导出日志
const exportLogs = () => {
  if (filteredLogs.value.length === 0) {
    console.warn('没有可导出的日志')
    return
  }

  const logText = filteredLogs.value.map(log =>
    `[${formatTime(log.timestamp)}] [${log.level}] ${log.message}`
  ).join('\n')

  const blob = new Blob([logText], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `backtest_${backtestId}_logs_${new Date().toISOString().slice(0, 10)}.log`
  a.click()
  URL.revokeObjectURL(url)

  console.log('日志导出成功')
}

// 监听新日志，重置提示
watch(() => logs.value.length, () => {
  hasNewLogs.value = false
})

onMounted(() => {
  connectStream()
})

onUnmounted(() => {
  connected.value = false
})
</script>

<style scoped>
.backtest-logs {
  padding: 16px;
}

.card {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
}

.card-header {
  padding: 16px 20px;
  border-bottom: 1px solid #2a2a3e;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.card-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
}

.card-body {
  padding: 20px;
}

.header-actions {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.form-input,
.form-select {
  padding: 6px 12px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
}

.form-input:focus,
.form-select:focus {
  outline: none;
  border-color: #1890ff;
}

.btn-primary {
  padding: 6px 16px;
  background: #1890ff;
  border: none;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-primary:hover:not(:disabled) {
  background: #40a9ff;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  padding: 6px 16px;
  background: transparent;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-secondary:hover {
  border-color: #1890ff;
  color: #1890ff;
}

.search-section {
  margin-bottom: 16px;
}

.logs-container {
  height: 500px;
  overflow-y: auto;
  background: #0d0d0d;
  border: 1px solid #2a2a3e;
  border-radius: 4px;
  padding: 12px;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
}

.log-entry {
  display: flex;
  padding: 4px 0;
  line-height: 1.5;
  border-bottom: 1px solid #1a1a1a;
}

.log-entry:last-child {
  border-bottom: none;
}

.log-time {
  color: #666;
  min-width: 80px;
  font-size: 12px;
}

.log-level {
  min-width: 60px;
  font-weight: 600;
  margin-right: 8px;
  font-size: 12px;
}

.log-level-DEBUG { color: #1890ff; }
.log-level-INFO { color: #52c41a; }
.log-level-WARNING { color: #faad14; }
.log-level-ERROR { color: #f5222d; }

.log-message {
  flex: 1;
  color: #e0e0e0;
  font-size: 13px;
}

.log-context {
  color: #888;
  margin-left: 12px;
  font-size: 12px;
}

.log-stats {
  text-align: center;
  padding: 8px;
  color: #8a8a9a;
  font-size: 14px;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 12px;
}

.new-logs-indicator {
  color: #52c41a;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

@media (max-width: 768px) {
  .header-actions {
    flex-direction: column;
    width: 100%;
  }

  .form-input,
  .form-select {
    width: 100%;
  }

  .logs-container {
    height: 400px;
  }
}
</style>
