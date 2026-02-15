<template>
  <div class="backtest-logs">
    <a-card title="回测日志">
      <template #extra>
        <a-space>
          <a-select v-model:value="logLevel" placeholder="日志级别" style="width: 120px">
            <a-select-option value="all">全部</a-select-option>
            <a-select-option value="DEBUG">DEBUG</a-select-option>
            <a-select-option value="INFO">INFO</a-select-option>
            <a-select-option value="WARNING">WARNING</a-select-option>
            <a-select-option value="ERROR">ERROR</a-select-option>
          </a-select>
          <a-range-picker v-model:value="dateRange" show-time style="width: 300px" />
          <a-button @click="clearLogs">清空</a-button>
          <a-button @click="exportLogs">导出</a-button>
          <a-button type="primary" :loading="connecting" @click="connectStream">
            {{ connected ? '已连接' : '连接日志流' }}
          </a-button>
        </a-space>
      </template>

      <!-- Custom -->
      <div class="search-section mb-3">
        <a-input-search
          v-model:value="searchKeyword"
          placeholder="搜索日志内容"
          allow-clear
          style="width: 300px"
          @search="onSearch"
        />
      </div>

      <!-- Custom -->
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

      <!-- Custom -->
      <div class="log-stats mt-3">
        <a-space>
          <span>共 {{ filteredLogs.length }} 条日志</span>
          <span v-if="hasNewLogs" class="new-logs-indicator">● 新日志</span>
        </a-space>
      </div>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'

const route = useRoute()
const backtestId = route.params.uuid || ''

// 配置
const logLevel = ref('all')
const dateRange = ref<any[]>([])
const searchKeyword = ref('')
const connecting = ref(false)
const connected = ref(false)

// 日志数据
const logs = ref<any[]>([])
const logsContainer = ref<HTMLDivElement>()
const hasNewLogs = ref(false)

// EventSource for SSE
let eventSource: EventSource | null = null

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

  // 按时间范围过滤
  if (dateRange.value && dateRange.value.length === 2) {
    const [start, end] = dateRange.value
    filtered = filtered.filter(log => {
      const logTime = new Date(log.timestamp)
      return logTime >= start && logTime <= end
    })
  }

  return filtered
})

// 连接SSE日志流
const connectStream = async () => {
  if (connected.value) {
    eventSource?.close()
    connected.value = false
    return
  }

  connecting.value = true

  try {
    const token = localStorage.getItem('access_token')
    const url = `/api/v1/backtests/${backtestId}/logs/stream`

    eventSource = new EventSource(url, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    })

    eventSource.onmessage = (event) => {
      const log = JSON.parse(event.data)
      logs.value.push(log)
      hasNewLogs.value = true

      // 自动滚动到底部
      nextTick(() => {
        if (logsContainer.value) {
          logsContainer.value.scrollTop = logsContainer.value.scrollHeight
        }
      })
    }

    eventSource.onerror = (error) => {
      message.error('日志流连接失败')
      connected.value = false
    }

    eventSource.onopen = () => {
      connected.value = true
      connecting.value = false
      message.success('日志流已连接')
    }

    eventSource.onclose = () => {
      connected.value = false
    hasNewLogs.value = false
    }
  } catch (e) {
    message.error('连接日志流失败')
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
    message.warning('没有可导出的日志')
    return
  }

  // TODO: 实现日志导出
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

  message.success('日志导出成功')
}

// 监听新日志，重置提示
watch(() => logs.value.length, () => {
  hasNewLogs.value = false
})

onMounted(() => {
  connectStream()
})

onUnmounted(() => {
  eventSource?.close()
})
</script>

<style scoped>
.backtest-logs {
  padding: 16px;
}

.search-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: #fafafa;
  border-radius: 8px;
}

.logs-container {
  height: 500px;
  overflow-y: auto;
  background: #1e1e1e1;
  border: 1px solid #e8e8e8;
  border-radius: 4px;
  padding: 12px;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
}

.log-entry {
  display: flex;
  padding: 4px 0;
  line-height: 1.5;
  border-bottom: 1px solid #f0f0f0;
}

.log-entry:last-child {
  border-bottom: none;
}

.log-time {
  color: #999;
  min-width: 80px;
  font-size: 12px;
}

.log-level {
  min-width: 60px;
  font-weight: 600;
  margin-right: 8px;
}

.log-level-DEBUG { color: #1890ff; }
.log-level-INFO { color: #52c41a; }
.log-level-WARNING { color: #faad14; }
.log-level-ERROR { color: #f5222d; }

.log-message {
  flex: 1;
  color: #333;
}

.log-context {
  color: #666;
  margin-left: 12px;
  font-size: 12px;
}

.log-stats {
  text-align: center;
  padding: 8px;
  color: #999;
}

.new-logs-indicator {
  color: #52c41a;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}
</style>
