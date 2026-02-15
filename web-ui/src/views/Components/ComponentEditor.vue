<template>
  <div class="component-editor flex flex-col bg-white text-gray-900 h-full">
    <!-- Custom -->
    <div class="flex items-center justify-between px-4 py-2 bg-gray-50 border-b border-gray-200 flex-shrink-0">
      <div class="flex items-center space-x-2">
        <span class="text-lg font-semibold">{{ componentInfo?.name || '加载中...' }}</span>
        <a-tag :color="getComponentTypeColor(componentInfo?.component_type)">
          {{ getComponentTypeLabel(componentInfo?.component_type) }}
        </a-tag>
      </div>
      <div class="flex items-center">
        <!-- Custom -->
      </div>
    </div>

    <!-- Custom -->
    <div class="flex-1 flex flex-col min-h-0 overflow-hidden">
      <!-- Custom -->
      <div class="flex-1 flex overflow-hidden min-h-0">
        <!-- Custom -->
        <div class="w-60 bg-gray-50 border-r border-gray-200 overflow-y-auto flex-shrink-0">
          <div class="p-3">
            <h3 class="text-xs font-semibold text-gray-600 mb-2">
              组件信息
            </h3>
            <div class="space-y-2">
              <div>
                <label class="text-xs text-gray-500">组件名称</label>
                <a-input
                  v-model:value="componentForm.name"
                  size="small"
                  class="mt-1"
                />
              </div>
              <div>
                <label class="text-xs text-gray-500">描述</label>
                <a-textarea
                  v-model:value="componentForm.description"
                  :rows="2"
                  size="small"
                  class="mt-1"
                />
              </div>
            </div>
          </div>

          <!-- Custom -->
          <div class="p-3 border-t border-gray-200">
            <h3 class="text-xs font-semibold text-gray-600 mb-2">
              参数配置
            </h3>
            <div class="space-y-2">
              <div
                v-for="(param, key) in parameters"
                :key="key"
                class="text-xs"
              >
                <label class="text-gray-500">{{ key }}</label>
                <a-input
                  v-model:value="param.value"
                  size="small"
                />
              </div>
            </div>
          </div>

          <!-- Custom -->
          <div class="p-3 border-t border-gray-200">
            <h3 class="text-xs font-semibold text-gray-600 mb-2">
              测试配置
            </h3>
            <div class="space-y-2">
              <div>
                <label class="text-xs text-gray-500">测试股票代码</label>
                <a-select
                  v-model:value="testConfig.code"
                  size="small"
                  class="w-full mt-1"
                  show-search
                >
                  <a-select-option
                    v-for="stock in testStocks"
                    :key="stock.code"
                    :value="stock.code"
                  >
                    {{ stock.code }} - {{ stock.name || '未知' }}
                  </a-select-option>
                </a-select>
              </div>
              <div>
                <label class="text-xs text-gray-500">测试日期范围</label>
                <a-range-picker
                  v-model:value="testConfig.dateRange"
                  size="small"
                  class="w-full mt-1"
                />
              </div>
              <div>
                <label class="text-xs text-gray-500">初始资金</label>
                <a-input-number
                  v-model:value="testConfig.initialCash"
                  :min="10000"
                  :step="10000"
                  size="small"
                  class="w-full mt-1"
                />
              </div>
              <a-button
                :loading="testing"
                type="primary"
                class="w-full mt-2"
                block
                @click="runTest"
              >
                <template #icon>
                  <PlayCircleOutlined />
                </template>
                运行测试
              </a-button>
            </div>
          </div>
        </div>

        <!-- Custom -->
        <div class="flex-1 flex flex-col min-w-0">
          <div class="flex-1 relative bg-white min-h-0">
            <!-- Custom -->
            <div class="absolute top-3 right-3 z-10">
              <a-button
                :loading="saving"
                type="primary"
                @click="saveComponent"
              >
                <template #icon>
                  <SaveOutlined />
                </template>
                保存
              </a-button>
            </div>
            <!-- CodeMirror  -->
            <codemirror
              v-model="code"
              :style="{ height: '100%' }"
              :extensions="extensions"
              :autofocus="true"
            />
          </div>
        </div>
      </div>

      <!-- Custom -->
      <div
        class="border-t border-gray-200 bg-gray-50 flex-shrink-0 transition-all duration-300"
        :style="{ height: panelHeight }"
      >
        <!-- / -->
        <div
          class="flex items-center justify-between px-3 py-1 border-b border-gray-200 bg-white cursor-pointer"
          @click="togglePanel"
        >
          <span class="text-xs font-medium text-gray-600">测试结果</span>
          <div class="flex items-center space-x-2">
            <!-- Custom -->
            <span
              v-if="testResult"
              class="text-xs text-gray-500"
            >
              收益率: <span :class="testResult.returnRate >= 0 ? 'text-green-600' : 'text-red-600'">{{ testResult.returnRate?.toFixed(2) }}%</span>
            </span>
            <a-button
              size="small"
              type="text"
              class="p-0 h-6 w-6 flex items-center justify-center"
            >
              <template #icon>
                <DownOutlined v-if="!isPanelCollapsed" />
                <UpOutlined v-else />
              </template>
            </a-button>
          </div>
        </div>

        <!-- Custom -->
        <div
          v-show="!isPanelCollapsed"
          class="overflow-hidden"
          style="height: calc(100% - 32px)"
        >
          <a-tabs
            v-model:active-key="activeTab"
            class="h-full"
          >
            <template #rightExtra>
              <a-button
                size="small"
                type="text"
                @click.stop="clearLogs"
              >
                <template #icon>
                  <ClearOutlined />
                </template>
              </a-button>
            </template>

            <!-- Custom -->
            <a-tab-pane
              key="logs"
              tab="日志"
            >
              <div class="h-48 overflow-y-auto p-2 font-mono text-xs bg-white">
                <div
                  v-if="logs.length === 0"
                  class="text-gray-400 text-center py-4"
                >
                  运行测试后查看日志
                </div>
                <div
                  v-for="(log, index) in logs"
                  :key="index"
                  class="mb-1"
                >
                  <span :class="getLogClass(log.level)">[{{ log.level }}]</span>
                  <span class="text-gray-400">{{ log.time }}</span>
                  <span :class="getLogClass(log.level)">{{ log.message }}</span>
                </div>
              </div>
            </a-tab-pane>

            <!-- Custom -->
            <a-tabPane
              key="charts"
              tab="图表"
            >
              <div class="h-48 overflow-y-auto p-2 bg-white">
                <div
                  v-if="!testResult"
                  class="text-gray-400 text-center py-4"
                >
                  运行测试后查看图表
                </div>
                <div
                  v-else
                  ref="chartContainer"
                  class="w-full h-40"
                />
              </div>
            </a-tabPane>

            <!-- Custom -->
            <a-tabPane
              key="output"
              tab="输出"
            >
              <div class="h-48 overflow-y-auto p-2 bg-white">
                <pre
                  v-if="testOutput"
                  class="text-xs text-gray-700 whitespace-pre-wrap"
                >{{ testOutput }}</pre>
                <div
                  v-else
                  class="text-gray-400 text-center py-4"
                >
                  运行测试后查看输出
                </div>
              </div>
            </a-tabPane>

            <!-- Custom -->
            <a-tabPane
              key="stats"
              tab="统计"
            >
              <div class="h-48 overflow-y-auto p-3 bg-white">
                <div
                  v-if="testResult"
                  class="space-y-2 text-xs"
                >
                  <div class="flex justify-between py-1 border-b border-gray-100">
                    <span class="text-gray-500">初始资金:</span>
                    <span class="text-gray-900">¥{{ testResult.initialCash?.toFixed(2) }}</span>
                  </div>
                  <div class="flex justify-between py-1 border-b border-gray-100">
                    <span class="text-gray-500">最终净值:</span>
                    <span :class="testResult.finalValue >= testResult.initialCash ? 'text-green-600' : 'text-red-600'">
                      ¥{{ testResult.finalValue?.toFixed(2) || '0.00' }}
                    </span>
                  </div>
                  <div class="flex justify-between py-1 border-b border-gray-100">
                    <span class="text-gray-500">收益率:</span>
                    <span :class="testResult.returnRate >= 0 ? 'text-green-600' : 'text-red-600'">
                      {{ testResult.returnRate?.toFixed(2) || '0.00' }}%
                    </span>
                  </div>
                  <div class="flex justify-between py-1 border-b border-gray-100">
                    <span class="text-gray-500">交易次数:</span>
                    <span class="text-gray-900">{{ testResult.tradeCount || 0 }}</span>
                  </div>
                  <div class="flex justify-between py-1">
                    <span class="text-gray-500">胜率:</span>
                    <span class="text-gray-900">{{ testResult.winRate?.toFixed(2) || '0.00' }}%</span>
                  </div>
                </div>
                <div
                  v-else
                  class="text-gray-400 text-center py-4"
                >
                  点击"运行测试"查看统计
                </div>
              </div>
            </a-tabPane>
          </a-tabs>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onBeforeUnmount, nextTick, computed, shallowRef } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import {
  SaveOutlined,
  PlayCircleOutlined,
  ClearOutlined,
  DownOutlined,
  UpOutlined
} from '@ant-design/icons-vue'
import dayjs from 'dayjs'
import { componentsApi, dataApi, type ComponentDetail } from '@/api/modules/components'
import * as echarts from 'echarts'
import { Codemirror } from 'vue-codemirror'
import { python } from '@codemirror/lang-python'
import { autocompletion } from '@codemirror/autocomplete'
import { EditorView } from '@codemirror/view'
import { EditorState } from '@codemirror/state'

// 浅色主题配置
const lightTheme = EditorView.theme({
  '&': {
    backgroundColor: '#ffffff',
    color: '#1f2937'
  },
  '.cm-gutters': {
    backgroundColor: '#f3f4f6',
    color: '#6b7280',
    border: 'none'
  },
  '.cm-activeLineGutter': {
    backgroundColor: '#e5e7eb',
    color: '#374151'
  },
  '.cm-activeLine': {
    backgroundColor: '#f9fafb'
  },
  '.cm-line': {
    padding: '0 4px'
  },
  '&.cm-focused': {
    outline: 'none'
  },
  '.cm-selectionBackground': {
    backgroundColor: '#d1d5db'
  },
  '&.cm-focused .cm-selectionBackground': {
    backgroundColor: '#bfdbfe'
  }
}, { dark: false })

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
  lightTheme,
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
  dateRange: [dayjs().subtract(1, 'year'), dayjs()],
  initialCash: 100000
})

// 测试股票列表
const testStocks = ref<any[]>([])

// 测试结果
const testResult = ref<any>(null)
const testOutput = ref('')
const logs = ref<Array<{ level: string; time: string; message: string }>>([])
const activeTab = ref('logs')

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
  return colors[type || ''] || 'default'
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

// 获取日志样式
const getLogClass = (level: string) => {
  const classes: Record<string, string> = {
    INFO: 'text-blue-600',
    WARNING: 'text-yellow-600',
    ERROR: 'text-red-600',
    DEBUG: 'text-gray-400'
  }
  return classes[level] || 'text-gray-600'
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
    message.error('加载组件失败')
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
    message.success('保存成功')
    await loadComponent()
  } catch (error: any) {
    message.error(`保存失败: ${error?.response?.data?.detail || error?.message}`)
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
  addLog('INFO', `日期范围: ${dayjs(testConfig.dateRange[0]).format('YYYY-MM-DD')} ~ ${dayjs(testConfig.dateRange[1]).format('YYYY-MM-DD')}`)
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
      textStyle: { color: '#374151' }
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(255,255,255,0.95)',
      borderColor: '#e5e7eb',
      textStyle: { color: '#1f2937' }
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: '#e5e7eb' } },
      axisLabel: { color: '#6b7280' }
    },
    yAxis: {
      type: 'value',
      axisLine: { lineStyle: { color: '#e5e7eb' } },
      axisLabel: { color: '#6b7280' },
      splitLine: { lineStyle: { color: '#f3f4f6' } }
    },
    series: [{
      data: values,
      type: 'line',
      smooth: true,
      lineStyle: { color: '#3b82f6', width: 2 },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(59, 130, 246, 0.3)' },
          { offset: 1, color: 'rgba(59, 130, 246, 0.05)' }
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
    const container = document.querySelector('.overflow-y-auto')
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
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
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
</style>
