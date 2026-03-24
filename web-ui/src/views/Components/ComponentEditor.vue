<template>
  <div class="component-editor">
    <!-- Header -->
    <div class="editor-header">
      <div class="header-left">
        <span class="component-name">{{ componentInfo?.name || '加载中...' }}</span>
        <span class="tag" :class="`tag-${getComponentTypeColor(componentInfo?.component_type)}`">
          {{ getComponentTypeLabel(componentInfo?.component_type) }}
        </span>
      </div>
      <div class="header-right">
      </div>
    </div>

    <!-- Main Content -->
    <div class="editor-content">
      <div class="editor-main">
        <!-- Sidebar -->
        <div class="sidebar">
          <div class="sidebar-section">
            <h3 class="section-title">组件信息</h3>
            <div class="form-group">
              <label class="form-label">组件名称</label>
              <input
                v-model="componentForm.name"
                type="text"
                class="form-input"
              />
            </div>
            <div class="form-group">
              <label class="form-label">描述</label>
              <textarea
                v-model="componentForm.description"
                :rows="2"
                class="form-textarea"
              ></textarea>
            </div>
          </div>

          <div class="sidebar-section">
            <h3 class="section-title">参数配置</h3>
            <div
              v-for="(param, key) in parameters"
              :key="key"
              class="form-group"
            >
              <label class="form-label">{{ key }}</label>
              <input
                v-model="param.value"
                type="text"
                class="form-input"
              />
            </div>
          </div>

          <div class="sidebar-section">
            <h3 class="section-title">测试配置</h3>
            <div class="form-group">
              <label class="form-label">测试股票代码</label>
              <select v-model="testConfig.code" class="form-select">
                <option v-for="stock in testStocks" :key="stock.code" :value="stock.code">
                  {{ stock.code }} - {{ stock.name || '未知' }}
                </option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">测试日期范围</label>
              <div class="date-range">
                <input
                  v-model="testConfig.startDate"
                  type="date"
                  class="form-input"
                />
                <span>至</span>
                <input
                  v-model="testConfig.endDate"
                  type="date"
                  class="form-input"
                />
              </div>
            </div>
            <div class="form-group">
              <label class="form-label">初始资金</label>
              <input
                v-model.number="testConfig.initialCash"
                type="number"
                :min="10000"
                :step="10000"
                class="form-input"
              />
            </div>
            <button
              class="btn btn-primary btn-block"
              :disabled="testing"
              @click="runTest"
            >
              <svg v-if="!testing" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polygon points="5 3 19 12 5 12 12 12 5 21 5 21 12"></polygon>
              </svg>
              {{ testing ? '测试中...' : '运行测试' }}
            </button>
          </div>
        </div>

        <!-- Editor Area -->
        <div class="editor-area">
          <div class="editor-toolbar">
            <button
              class="btn btn-primary"
              :disabled="saving"
              @click="saveComponent"
            >
              <svg v-if="!saving" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
                <polyline points="17 21 17 13 7 13 7 21"></polyline>
                <polyline points="7 3 7 8 15 8"></polyline>
              </svg>
              {{ saving ? '保存中...' : '保存' }}
            </button>
          </div>
          <codemirror
            v-model="code"
            :style="{ height: '100%' }"
            :extensions="extensions"
            :autofocus="true"
          />
        </div>
      </div>

      <!-- Bottom Panel -->
      <div
        class="bottom-panel"
        :style="{ height: panelHeight }"
      >
        <div class="panel-header" @click="togglePanel">
          <span class="panel-title">测试结果</span>
          <div class="panel-actions">
            <span
              v-if="testResult"
              class="panel-stat"
              :class="testResult.returnRate >= 0 ? 'text-green' : 'text-red'"
            >
              收益率: {{ testResult.returnRate?.toFixed(2) }}%
            </span>
            <button class="btn-icon">
              <svg v-if="!isPanelCollapsed" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="6 9 12 15 15 15"></polyline>
              </svg>
              <svg v-else xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="18 15 12 9 9 9"></polyline>
              </svg>
            </button>
          </div>
        </div>

        <div
          v-show="!isPanelCollapsed"
          class="panel-content"
        >
          <div class="tabs-header">
            <button
              v-for="tab in tabs"
              :key="tab.key"
              class="tab-button"
              :class="{ active: activeTab === tab.key }"
              @click="activeTab = tab.key"
            >
              {{ tab.label }}
            </button>
            <button class="tab-clear" @click="clearLogs">
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="3 6 5 6 21 6"></polyline>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
              </svg>
            </button>
          </div>

          <!-- Logs Tab -->
          <div v-show="activeTab === 'logs'" class="tab-panel">
            <div class="logs-container">
              <div
                v-if="logs.length === 0"
                class="empty-hint"
              >
                运行测试后查看日志
              </div>
              <div
                v-for="(log, index) in logs"
                :key="index"
                class="log-line"
                :class="`log-${log.level.toLowerCase()}`"
              >
                <span class="log-level">[{{ log.level }}]</span>
                <span class="log-time">{{ log.time }}</span>
                <span class="log-message">{{ log.message }}</span>
              </div>
            </div>
          </div>

          <!-- Charts Tab -->
          <div v-show="activeTab === 'charts'" class="tab-panel">
            <div
              v-if="!testResult"
              class="empty-hint"
            >
              运行测试后查看图表
            </div>
            <div
              v-else
              ref="chartContainer"
              class="chart-container"
            ></div>
          </div>

          <!-- Output Tab -->
          <div v-show="activeTab === 'output'" class="tab-panel">
            <div class="output-container">
              <pre
                v-if="testOutput"
                class="output-text"
              >{{ testOutput }}</pre>
              <div
                v-else
                class="empty-hint"
              >
                运行测试后查看输出
              </div>
            </div>
          </div>

          <!-- Stats Tab -->
          <div v-show="activeTab === 'stats'" class="tab-panel">
            <div
              v-if="testResult"
              class="stats-container"
            >
              <div class="stat-row">
                <span class="stat-label">初始资金:</span>
                <span class="stat-value">¥{{ testResult.initialCash?.toFixed(2) }}</span>
              </div>
              <div class="stat-row">
                <span class="stat-label">最终净值:</span>
                <span class="stat-value" :class="testResult.finalValue >= testResult.initialCash ? 'text-green' : 'text-red'">
                  ¥{{ testResult.finalValue?.toFixed(2) || '0.00' }}
                </span>
              </div>
              <div class="stat-row">
                <span class="stat-label">收益率:</span>
                <span class="stat-value" :class="testResult.returnRate >= 0 ? 'text-green' : 'text-red'">
                  {{ testResult.returnRate?.toFixed(2) || '0.00' }}%
                </span>
              </div>
              <div class="stat-row">
                <span class="stat-label">交易次数:</span>
                <span class="stat-value">{{ testResult.tradeCount || 0 }}</span>
              </div>
              <div class="stat-row">
                <span class="stat-label">胜率:</span>
                <span class="stat-value">{{ testResult.winRate?.toFixed(2) || '0.00' }}%</span>
              </div>
            </div>
            <div
              v-else
              class="empty-hint"
            >
              点击"运行测试"查看统计
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onBeforeUnmount, nextTick, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import dayjs from 'dayjs'
import { componentsApi, dataApi, type ComponentDetail } from '@/api/modules/components'
import * as echarts from 'echarts'
import { Codemirror } from 'vue-codemirror'
import { python } from '@codemirror/lang-python'
import { autocompletion } from '@codemirror/autocomplete'
import { EditorView } from '@codemirror/view'
import { EditorState } from '@codemirror/state'

// 简化的通知函数
const showToast = (message: string, type: 'success' | 'error' | 'info' | 'warning' = 'success') => {
  console.log(`[${type.toUpperCase()}] ${message}`)
}

const route = useRoute()
const router = useRouter()
const componentUuid = route.params.uuid as string

// 组件信息
const componentInfo = ref<ComponentDetail | null>(null)
const componentForm = reactive({
  name: '',
  description: ''
})

// 代码编辑器
const code = ref('')
const extensions = [
  EditorView.theme({
    '&': {
      backgroundColor: '#1a1a2e',
      color: '#ffffff'
    },
    '.cm-gutters': {
      backgroundColor: '#0f0f1a',
      color: '#8a8a9a',
      border: 'none'
    },
    '.cm-activeLineGutter': {
      backgroundColor: '#2a2a3e',
      color: '#ffffff'
    },
    '.cm-activeLine': {
      backgroundColor: '#2a2a3e'
    },
    '.cm-line': {
      padding: '0 4px'
    },
    '&.cm-focused': {
      outline: 'none'
    },
    '.cm-selectionBackground': {
      backgroundColor: '#3a4a5e'
    },
    '&.cm-focused .cm-selectionBackground': {
      backgroundColor: '#3a4a5e'
    }
  }, { dark: true }),
  python(),
  autocompletion(),
  EditorView.lineWrapping,
  EditorState.tabSize.of(4)
]

// 状态
const saving = ref(false)
const testing = ref(false)
const originalCode = ref('')

// 参数
const parameters = ref<Record<string, { value: any }>>({})

// 测试配置
const testConfig = reactive({
  code: '000001.SZ',
  startDate: dayjs().subtract(1, 'year').format('YYYY-MM-DD'),
  endDate: dayjs().format('YYYY-MM-DD'),
  initialCash: 100000
})

// 测试股票列表
const testStocks = ref<any[]>([])

// 测试结果
const testResult = ref<any>(null)
const testOutput = ref('')
const logs = ref<Array<{ level: string; time: string; message: string }>>([])
const activeTab = ref('logs')

const tabs = [
  { key: 'logs', label: '日志' },
  { key: 'charts', label: '图表' },
  { key: 'output', label: '输出' },
  { key: 'stats', label: '统计' }
]

// 图表
const chartContainer = ref<HTMLElement | null>(null)
let chartInstance: echarts.ECharts | null = null

// 面板折叠状态
const isPanelCollapsed = ref(false)
const panelExpandedHeight = '280px'
const panelCollapsedHeight = '32px'

const panelHeight = computed(() => {
  return isPanelCollapsed.value ? panelCollapsedHeight : panelExpandedHeight
})

// 切换面板折叠状态
const togglePanel = () => {
  isPanelCollapsed.value = !isPanelCollapsed.value
  if (!isPanelCollapsed.value && activeTab.value === 'charts' && chartInstance) {
    setTimeout(() => {
      chartInstance?.resize()
    }, 300)
  }
}

// 获取组件类型颜色
const getComponentTypeColor = (type?: string) => {
  const colors: Record<string, string> = {
    strategy: 'blue',
    analyzer: 'green',
    risk: 'orange',
    sizer: 'purple',
    selector: 'cyan'
  }
  return colors[type || ''] || 'gray'
}

// 获取组件类型标签
const getComponentTypeLabel = (type?: string) => {
  const labels: Record<string, string> = {
    strategy: '策略',
    analyzer: '分析器',
    risk: '风控',
    sizer: '仓位管理',
    selector: '选择器'
  }
  return labels[type || ''] || type || ''
}

// 加载组件详情
const loadComponent = async () => {
  try {
    const detail = await componentsApi.get(componentUuid)
    componentInfo.value = detail
    componentForm.name = detail.name
    componentForm.description = detail.description || ''
    code.value = detail.code || ''
    originalCode.value = detail.code || ''
  } catch (error: any) {
    showToast('加载组件失败', 'error')
  }
}

// 加载测试股票列表
const loadTestStocks = async () => {
  try {
    const response = await dataApi.getStockInfo({ page: 1, page_size: 100 })
    testStocks.value = response.items.filter((s: any) => s.is_active).slice(0, 20)
  } catch (error: any) {
    console.error('加载测试股票失败:', error)
  }
}

// 保存组件
const saveComponent = async () => {
  saving.value = true
  try {
    await componentsApi.update(componentUuid, {
      name: componentForm.name,
      description: componentForm.description,
      code: code.value
    })
    originalCode.value = code.value
    showToast('保存成功')
    await loadComponent()
  } catch (error: any) {
    showToast(`保存失败: ${error?.response?.data?.detail || error?.message}`, 'error')
  } finally {
    saving.value = false
  }
}

// 运行测试
const runTest = async () => {
  testing.value = true
  logs.value = []
  testResult.value = null
  testOutput.value = ''

  if (isPanelCollapsed.value) {
    isPanelCollapsed.value = false
  }

  addLog('INFO', '开始测试组件...')

  try {
    await simulateTest()
  } catch (error: any) {
    addLog('ERROR', `测试失败: ${error?.message || '未知错误'}`)
  } finally {
    testing.value = false
  }
}

// 模拟测试（临时）
const simulateTest = async () => {
  addLog('INFO', `加载测试数据: ${testConfig.code}`)
  await delay(500)
  addLog('INFO', `日期范围: ${testConfig.startDate} ~ ${testConfig.endDate}`)
  await delay(300)
  addLog('INFO', '初始化策略...')
  await delay(500)
  addLog('INFO', '开始回测...')
  await delay(1000)

  addLog('DEBUG', 'Generated signal: LONG 000001.SZ at 2024-01-05')
  addLog('DEBUG', 'Generated signal: SHORT 000001.SZ at 2024-01-15')
  addLog('DEBUG', 'Generated signal: LONG 000001.SZ at 2024-02-01')

  testResult.value = {
    initialCash: testConfig.initialCash,
    finalValue: testConfig.initialCash * (1 + Math.random() * 0.4 - 0.1),
    returnRate: (Math.random() * 40 - 10),
    tradeCount: Math.floor(Math.random() * 50) + 10,
    winRate: Math.random() * 40 + 40
  }

  addLog('INFO', `测试完成! 收益率: ${testResult.value.returnRate.toFixed(2)}%`)

  nextTick(() => {
    renderChart()
  })
}

// 渲染图表
const renderChart = () => {
  if (!chartContainer.value) return

  if (chartInstance) {
    chartInstance.dispose()
  }

  chartInstance = echarts.init(chartContainer.value)

  const dates: string[] = []
  const values: number[] = []
  let value = testConfig.initialCash

  for (let i = 0; i < 100; i++) {
    dates.push(dayjs().subtract(100 - i, 'day').format('YYYY-MM-DD'))
    value = value * (1 + (Math.random() - 0.48) * 0.02)
    values.push(value)
  }

  const option = {
    backgroundColor: 'transparent',
    title: {
      text: '净值曲线',
      textStyle: { color: '#ffffff' }
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(26, 26, 46, 0.95)',
      borderColor: '#2a2a3e',
      textStyle: { color: '#ffffff' }
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: '#2a2a3e' } },
      axisLabel: { color: '#8a8a9a' }
    },
    yAxis: {
      type: 'value',
      axisLine: { lineStyle: { color: '#2a2a3e' } },
      axisLabel: { color: '#8a8a9a' },
      splitLine: { lineStyle: { color: '#2a2a3e', type: 'dashed' } }
    },
    series: [{
      data: values,
      type: 'line',
      smooth: true,
      lineStyle: { color: '#1890ff', width: 2 },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(24, 144, 255, 0.3)' },
          { offset: 1, color: 'rgba(24, 144, 255, 0.05)' }
        ])
      }
    }],
    grid: {
      left: 50,
      right: 20,
      top: 40,
      bottom: 30
    }
  }

  chartInstance.setOption(option)
}

// 添加日志
const addLog = (level: string, message: string) => {
  logs.value.push({
    level,
    time: dayjs().format('HH:mm:ss'),
    message
  })
  nextTick(() => {
    const container = document.querySelector('.logs-container')
    if (container) {
      container.scrollTop = container.scrollHeight
    }
  })
}

// 清空日志
const clearLogs = () => {
  logs.value = []
  testOutput.value = ''
  testResult.value = null
  if (chartInstance) {
    chartInstance.dispose()
    chartInstance = null
  }
}

// 延迟函数
const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms))

onMounted(async () => {
  await loadComponent()
  await loadTestStocks()

  window.addEventListener('resize', () => {
    if (chartInstance) {
      chartInstance.resize()
    }
  })
})

onBeforeUnmount(() => {
  if (chartInstance) {
    chartInstance.dispose()
  }
})
</script>

<style scoped>
.component-editor {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #0f0f1a;
  color: #ffffff;
}

/* Header */
.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #1a1a2e;
  border-bottom: 1px solid #2a2a3e;
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.component-name {
  font-size: 16px;
  font-weight: 600;
}

/* Tag */
.tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}

.tag-blue { background: rgba(24, 144, 255, 0.2); color: #1890ff; }
.tag-green { background: rgba(82, 196, 26, 0.2); color: #52c41a; }
.tag-orange { background: rgba(250, 173, 20, 0.2); color: #faad14; }
.tag-purple { background: rgba(114, 46, 209, 0.2); color: #722ed1; }
.tag-cyan { background: rgba(19, 194, 194, 0.2); color: #13c2c2; }
.tag-gray { background: #2a2a3e; color: #8a8a9a; }

/* Content */
.editor-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
}

.editor-main {
  flex: 1;
  display: flex;
  min-height: 0;
}

/* Sidebar */
.sidebar {
  width: 240px;
  background: #1a1a2e;
  border-right: 1px solid #2a2a3e;
  overflow-y: auto;
  flex-shrink: 0;
}

.sidebar-section {
  padding: 16px;
  border-bottom: 1px solid #2a2a3e;
}

.sidebar-section:last-child {
  border-bottom: none;
}

.section-title {
  font-size: 11px;
  font-weight: 600;
  color: #8a8a9a;
  text-transform: uppercase;
  margin: 0 0 12px 0;
}

.form-group {
  margin-bottom: 12px;
}

.form-group:last-child {
  margin-bottom: 0;
}

.form-label {
  display: block;
  font-size: 12px;
  color: #8a8a9a;
  margin-bottom: 4px;
}

.form-input,
.form-select,
.form-textarea {
  width: 100%;
  padding: 6px 8px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 13px;
  box-sizing: border-box;
}

.form-input:focus,
.form-select:focus,
.form-textarea:focus {
  outline: none;
  border-color: #1890ff;
}

.form-textarea {
  resize: vertical;
  min-height: 40px;
  font-family: 'Fira Code', monospace;
}

.date-range {
  display: flex;
  align-items: center;
  gap: 8px;
}

.date-range span {
  font-size: 12px;
  color: #8a8a9a;
}

/* Button */
.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 4px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.btn-primary {
  background: #1890ff;
  color: #ffffff;
}

.btn-primary:hover:not(:disabled) {
  background: #40a9ff;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-block {
  width: 100%;
  justify-content: center;
}

.btn-icon {
  padding: 4px;
  background: transparent;
  border: none;
  color: #8a8a9a;
  cursor: pointer;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-icon:hover {
  background: #2a2a3e;
  color: #ffffff;
}

/* Editor Area */
.editor-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.editor-toolbar {
  padding: 8px 16px;
  background: #1a1a2e;
  border-bottom: 1px solid #2a2a3e;
}

/* CodeMirror 自定义样式 */
:deep(.cm-editor) {
  height: 100%;
  font-size: 14px;
}

:deep(.cm-scroller) {
  overflow: auto;
}

:deep(.cm-focused) {
  outline: none !important;
}

/* Bottom Panel */
.bottom-panel {
  background: #1a1a2e;
  border-top: 1px solid #2a2a3e;
  transition: height 0.3s ease;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 16px;
  border-bottom: 1px solid #2a2a3e;
  background: #2a2a3e;
  cursor: pointer;
}

.panel-title {
  font-size: 12px;
  font-weight: 500;
  color: #ffffff;
}

.panel-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.panel-stat {
  font-size: 12px;
  font-weight: 500;
}

.text-green { color: #52c41a; }
.text-red { color: #f5222d; }

.panel-content {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* Tabs */
.tabs-header {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 8px 16px;
  border-bottom: 1px solid #2a2a3e;
  background: #1a1a2e;
}

.tab-button {
  padding: 6px 12px;
  background: transparent;
  border: none;
  color: #8a8a9a;
  font-size: 12px;
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: all 0.2s;
}

.tab-button:hover {
  color: #ffffff;
}

.tab-button.active {
  color: #1890ff;
  border-bottom-color: #1890ff;
}

.tab-clear {
  margin-left: auto;
  padding: 4px;
  background: transparent;
  border: none;
  color: #8a8a9a;
  cursor: pointer;
}

.tab-clear:hover {
  color: #ffffff;
}

.tab-panel {
  flex: 1;
  overflow-y: auto;
  background: #0f0f1a;
}

/* Logs */
.logs-container {
  padding: 12px;
  font-family: 'Fira Code', monospace;
  font-size: 12px;
  line-height: 1.6;
}

.log-line {
  display: flex;
  gap: 8px;
  margin-bottom: 4px;
}

.log-level {
  flex-shrink: 0;
  font-weight: 500;
}

.log-time {
  color: #8a8a9a;
  flex-shrink: 0;
}

.log-message {
  flex: 1;
}

.log-info .log-level { color: #1890ff; }
.log-warning .log-level { color: #faad14; }
.log-error .log-level { color: #f5222d; }
.log-debug .log-level { color: #8a8a9a; }

/* Chart */
.chart-container {
  width: 100%;
  height: 160px;
}

/* Output */
.output-container {
  padding: 12px;
}

.output-text {
  font-family: 'Fira Code', monospace;
  font-size: 12px;
  color: #a0d911;
  white-space: pre-wrap;
  word-break: break-all;
}

/* Stats */
.stats-container {
  padding: 12px;
}

.stat-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid #2a2a3e;
  font-size: 13px;
}

.stat-row:last-child {
  border-bottom: none;
}

.stat-label {
  color: #8a8a9a;
}

.stat-value {
  color: #ffffff;
  font-weight: 500;
}

/* Empty State */
.empty-hint {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 40px 20px;
  color: #8a8a9a;
  font-size: 13px;
}
</style>
