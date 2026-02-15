<template>
  <div class="backtest-create-container">
    <!-- Custom -->
    <div class="page-header">
      <a-button
        class="back-btn"
        @click="goBack"
      >
        <ArrowLeftOutlined /> 返回
      </a-button>
      <div class="title-section">
        <h1 class="page-title">
          创建回测任务
        </h1>
        <p class="page-subtitle">
          配置回测参数并创建任务
        </p>
      </div>
    </div>

    <!-- Custom -->
    <a-card class="form-card">
      <a-form
        ref="formRef"
        :model="form"
        :rules="rules"
        layout="vertical"
        @finish="handleSubmit"
      >
        <!-- Custom -->
        <a-steps
          :current="currentStep"
          class="form-steps"
          size="small"
        >
          <a-step title="选择投资组合" />
          <a-step title="配置参数" />
          <a-step title="分析器（可选）" />
        </a-steps>

        <!-- 1 -->
        <div
          v-show="currentStep === 0"
          class="step-content"
        >
          <div class="form-section">
            <h3 class="section-title">
              基本信息
            </h3>
            <a-form-item
              label="任务名称"
              name="name"
            >
              <a-input
                v-model:value="form.name"
                placeholder="请输入任务名称"
                size="large"
              />
            </a-form-item>
          </div>

          <div class="form-section">
            <h3 class="section-title">
              选择投资组合 <span class="required-mark">*</span>
            </h3>
            <a-form-item name="portfolio_uuids">
              <a-select
                ref="portfolioSelectRef"
                v-model:value="form.portfolio_uuids"
                mode="multiple"
                placeholder="选择一个或多个投资组合"
                size="large"
                :loading="loadingPortfolios"
                show-search
                :filter-option="filterPortfolioOption"
                @select="handlePortfolioSelect"
                @deselect="handlePortfolioDeselect"
              >
                <a-select-option
                  v-for="portfolio in portfolios"
                  :key="portfolio.uuid"
                  :value="portfolio.uuid"
                >
                  <div class="portfolio-option">
                    <span class="portfolio-name">{{ portfolio.name }}</span>
                    <a-tag
                      size="small"
                      :color="getModeColor(portfolio.mode)"
                    >
                      {{ getModeLabel(portfolio.mode) }}
                    </a-tag>
                  </div>
                </a-select-option>
              </a-select>
            </a-form-item>

            <!-- Portfolio -->
            <div
              v-if="selectedPortfolios.length > 0"
              class="selected-portfolios-list"
            >
              <div class="selected-header">
                <span>已选择 {{ selectedPortfolios.length }} 个投资组合</span>
              </div>
              <a-collapse
                v-model:active-key="portfolioCollapseActiveKeys"
                :bordered="false"
                ghost
              >
                <a-collapse-panel
                  v-for="portfolio in selectedPortfolios"
                  :key="portfolio.uuid"
                  :header="portfolio.name"
                >
                  <template #extra>
                    <a-tag size="small">
                      {{ getModeLabel(portfolio.mode) }}
                    </a-tag>
                  </template>
                  <a-tree
                    :tree-data="buildPortfolioTree(portfolio)"
                    :show-icon="false"
                    :show-line="true"
                    default-expand-all
                    class="component-tree"
                  >
                    <template #title="{ title, value }">
                      <span
                        v-if="value !== undefined"
                        class="tree-node-value"
                      >
                        <span class="tree-node-key">{{ title }}:</span>
                        <span class="tree-node-value-text">{{ formatValue(value) }}</span>
                      </span>
                      <span
                        v-else
                        class="tree-node-title"
                      >{{ title }}</span>
                    </template>
                  </a-tree>
                </a-collapse-panel>
              </a-collapse>
            </div>
          </div>

          <div class="step-actions">
            <a-button
              size="large"
              @click="goBack"
            >
              取消
            </a-button>
            <a-button
              type="primary"
              size="large"
              :disabled="!canGoToStep1"
              @click="nextStep"
            >
              下一步
            </a-button>
          </div>
        </div>

        <!-- 2 -->
        <div
          v-show="currentStep === 1"
          class="step-content"
        >
          <div class="form-section">
            <h3 class="section-title">
              回测时间范围
            </h3>

            <!-- Custom -->
            <a-space
              :size="8"
              class="date-quick-select"
              wrap
            >
              <a-button
                size="small"
                @click="setDateRange(0, 0, 0, 0, 0, 0, -1, false)"
              >
                最近1年
              </a-button>
              <a-button
                size="small"
                @click="setDateRange(0, 0, 0, 0, 0, 0, -5, false)"
              >
                最近5年
              </a-button>
              <a-button
                size="small"
                @click="setDateRange(2023, 1, 1, 2023, 12, 31, 0, false)"
              >
                2023年
              </a-button>
              <a-button
                size="small"
                @click="setDateRange(2024, 1, 1, 2024, 12, 31, 0, false)"
              >
                2024年
              </a-button>
              <a-button
                size="small"
                @click="setDateRange(0, 0, 0, 0, 0, 0, 0, true)"
              >
                全周期(1992-)
              </a-button>
            </a-space>

            <a-row
              :gutter="16"
              class="date-row"
            >
              <a-col :span="12">
                <a-form-item
                  label="开始日期"
                  name="start_date"
                  :rules="[
                    {
                      required: true,
                      message: '请选择开始日期',
                      trigger: ['change', 'blur']
                    }
                  ]"
                >
                  <a-date-picker
                    v-model:value="form.start_date"
                    placeholder="选择开始日期"
                    style="width: 100%"
                    size="large"
                    format="YYYY-MM-DD"
                    :disabled-date="disabledStartDate"
                  />
                </a-form-item>
              </a-col>
              <a-col :span="12">
                <a-form-item
                  label="结束日期"
                  name="end_date"
                  :rules="[
                    {
                      required: true,
                      message: '请选择结束日期',
                      trigger: ['change', 'blur']
                    }
                  ]"
                >
                  <a-date-picker
                    v-model:value="form.end_date"
                    placeholder="选择结束日期"
                    style="width: 100%"
                    size="large"
                    format="YYYY-MM-DD"
                    :disabled-date="disabledEndDate"
                  />
                </a-form-item>
              </a-col>
            </a-row>
          </div>

          <a-collapse
            v-model:active-key="configActiveKey"
            :bordered="false"
            class="config-collapse"
          >
            <!-- Custom -->
            <a-collapse-panel
              key="broker"
              header="撮合器配置"
            >
              <a-row :gutter="16">
                <a-col :span="12">
                  <a-form-item
                    label="撮合态度"
                    name="engine_config.broker_attitude"
                  >
                    <a-select
                      v-model:value="form.engine_config.broker_attitude"
                      size="large"
                    >
                      <a-select-option :value="1">
                        悲观（成交难）
                      </a-select-option>
                      <a-select-option :value="2">
                        乐观（成交易）
                      </a-select-option>
                      <a-select-option :value="3">
                        随机
                      </a-select-option>
                    </a-select>
                  </a-form-item>
                </a-col>
                <a-col :span="12">
                  <a-form-item
                    label="手续费率 (%)"
                    name="engine_config.commission_rate"
                  >
                    <a-input-number
                      v-model:value="form.engine_config.commission_rate"
                      :min="0"
                      :max="1"
                      :step="0.0001"
                      :precision="4"
                      style="width: 100%"
                      size="large"
                    />
                  </a-form-item>
                </a-col>
              </a-row>
              <a-row :gutter="16">
                <a-col :span="12">
                  <a-form-item
                    label="滑点率 (%)"
                    name="engine_config.slippage_rate"
                  >
                    <a-input-number
                      v-model:value="form.engine_config.slippage_rate"
                      :min="0"
                      :max="1"
                      :step="0.0001"
                      :precision="4"
                      style="width: 100%"
                      size="large"
                    />
                  </a-form-item>
                </a-col>
                <a-col :span="12">
                  <a-form-item
                    label="最小手续费"
                    name="engine_config.commission_min"
                  >
                    <a-input-number
                      v-model:value="form.engine_config.commission_min"
                      :min="0"
                      :step="1"
                      style="width: 100%"
                      size="large"
                    />
                  </a-form-item>
                </a-col>
              </a-row>
            </a-collapse-panel>
          </a-collapse>

          <div class="step-actions">
            <a-button
              size="large"
              @click="prevStep"
            >
              上一步
            </a-button>
            <a-button
              size="large"
              @click="nextStep"
            >
              下一步
            </a-button>
            <a-button
              type="primary"
              size="large"
              html-type="submit"
              :loading="submitting"
            >
              创建回测任务
            </a-button>
          </div>
        </div>

        <!-- 3 -->
        <div
          v-show="currentStep === 2"
          class="step-content"
        >
          <div class="form-section">
            <h3 class="section-title">
              添加分析器 <span class="optional-mark">(可选)</span>
            </h3>
            <p class="section-desc">
              分析器在 Engine 级别统一管理，可接收所有 Portfolio 的数据进行分析
            </p>

            <a-button
              type="dashed"
              size="large"
              block
              @click="showAnalyzerModal"
            >
              <PlusOutlined /> 添加分析器
            </a-button>

            <div
              v-if="form.engine_config.analyzers.length > 0"
              class="analyzers-list"
            >
              <div
                v-for="(analyzer, index) in form.engine_config.analyzers"
                :key="index"
                class="analyzer-item"
              >
                <div class="analyzer-main">
                  <span class="analyzer-name">{{ analyzer.name || analyzer.type }}</span>
                  <a-tag>{{ analyzer.type }}</a-tag>
                  <a-button
                    danger
                    size="small"
                    @click="removeAnalyzer(index)"
                  >
                    <DeleteOutlined /> 移除
                  </a-button>
                </div>
                <div class="analyzer-config">
                  {{ getAnalyzerConfig(analyzer.type) }}
                </div>
              </div>
            </div>
          </div>

          <div class="step-actions">
            <a-button
              size="large"
              @click="prevStep"
            >
              上一步
            </a-button>
            <a-button
              type="primary"
              size="large"
              html-type="submit"
              :loading="submitting"
            >
              创建回测任务
            </a-button>
          </div>
        </div>
      </a-form>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { message, Modal } from 'ant-design-vue'
import dayjs, { Dayjs } from 'dayjs'
import { ArrowLeftOutlined, PlusOutlined, DeleteOutlined } from '@ant-design/icons-vue'
import { portfolioApi, type Portfolio, type PortfolioDetail } from '@/api/modules/portfolio'
import { backtestApi, type BacktestCreate, type AnalyzerConfig, type Engine } from '@/api/modules/backtest'
import {
  MODE_LABELS,
  STATE_COLORS,
  BROKER_ATTITUDES,
  getModeLabel,
  getModeColor,
  formatDateOnly
} from '@/constants'

const router = useRouter()

// 状态
const formRef = ref()
const portfolioSelectRef = ref()
const submitting = ref(false)
const loadingPortfolios = ref(false)
const loadingEngines = ref(false)
const loadingAnalyzers = ref(false)
const portfolios = ref<Portfolio[]>([])
const selectedPortfolioDetails = ref<Map<string, PortfolioDetail>>(new Map())
const engines = ref<Engine[]>([])
const analyzers = ref<any[]>([])

// 步骤状态
const currentStep = ref(0)
const configActiveKey = ref([] as string[])

// Portfolio折叠面板展开状态（默认展开所有选中的）
const portfolioCollapseActiveKeys = ref<string[]>([])

// 表单数据
const form = reactive({
  name: '',
  portfolio_uuids: [] as string[],
  // 日期字段扁平化到顶层，避免嵌套路径验证问题
  start_date: null as Dayjs | null,
  end_date: null as Dayjs | null,
  engine_config: {
    broker_type: 'backtest' as 'backtest' | 'okx',
    initial_cash: null as number | null,
    commission_rate: 0.0003,
    slippage_rate: 0.0001,
    broker_attitude: 2,
    commission_min: 5,
    analyzers: [] as AnalyzerConfig[],
  },
})

// 分析器选项
const analyzerOptions = computed(() =>
  analyzers.value.map(a => ({
    value: a.type,
    label: a.name,
    desc: a.description,
    defaultName: a.name,
    defaultConfig: a.default_config
  }))
)

// 已选Portfolio
const selectedPortfolios = computed(() => {
  return form.portfolio_uuids
    .map(uuid => {
      const detail = selectedPortfolioDetails.value.get(uuid)
      const basic = portfolios.value.find(p => p.uuid === uuid)
      return detail || basic
    })
    .filter((p): p is any => p !== undefined)
})

// 能否进入步骤1
const canGoToStep1 = computed(() => {
  return form.name.trim() !== '' && form.portfolio_uuids.length > 0
})

// 表单验证规则
const rules = {
  name: [
    { required: true, message: '请输入任务名称', trigger: 'blur' }
  ],
  portfolio_uuids: [
    { required: true, type: 'array', min: 1, message: '请选择至少一个投资组合', trigger: 'change' }
  ]
  // 日期字段的验证规则已直接在 form-item 上定义，以避免嵌套路径问题
}

// 日期禁用规则
const disabledStartDate = (current: Dayjs) => {
  if (!current) return false
  if (current.isAfter(dayjs())) return true
  if (form.end_date && current.isAfter(form.end_date)) return true
  return false
}

const disabledEndDate = (current: Dayjs) => {
  if (!current) return false
  if (current.isAfter(dayjs())) return true
  if (form.start_date && current.isBefore(form.start_date)) return true
  return false
}

// 分析器选择弹窗
const showAnalyzerModal = () => {
  Modal.select({
    title: '选择分析器',
    content: (h: any) => {
      const selected = ref<string>()
      return h('div', { class: 'analyzer-select-modal' },
        analyzerOptions.value.map(opt => h('div', {
          class: 'analyzer-select-item',
          onClick: () => {
            form.engine_config.analyzers.push({
              name: opt.defaultName,
              type: opt.value,
              config: opt.defaultConfig
            })
            Modal.destroyAll()
          }
        }, [
          h('div', { class: 'analyzer-select-name' }, opt.label),
          h('div', { class: 'analyzer-select-desc' }, opt.desc)
        ]))
      )
    },
    width: 500,
    okText: '取消',
    onOk: () => {}
  })
}

// 分析器变更处理
const handleAnalyzerChange = (index: number) => {
  const analyzer = form.engine_config.analyzers[index]
  const option = analyzerOptions.value.find(o => o.value === analyzer.type)
  if (option) {
    analyzer.name = option.defaultName
    analyzer.config = option.defaultConfig
  }
}

// 获取分析器配置描述
const getAnalyzerConfig = (type: string) => {
  const option = analyzerOptions.value.find(o => o.value === type)
  if (!option) return ''
  const config = option.defaultConfig
  if (!config || Object.keys(config).length === 0) return '使用默认配置'
  return JSON.stringify(config)
}

// 删除分析器
const removeAnalyzer = (index: number) => {
  form.engine_config.analyzers.splice(index, 1)
}

// 快速设置日期范围
const setDateRange = (year: number, month: number, day: number, endYear: number, endMonth: number, endDay: number, offsetYears = 0, allTime = false) => {
  const now = dayjs()
  let start, end

  if (allTime) {
    start = dayjs('1992-01-01')
    end = now
  } else if (offsetYears < 0) {
    start = now.subtract(Math.abs(offsetYears), 'year')
    end = now
  } else if (year > 0) {
    start = dayjs(`${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`)
    end = dayjs(`${endYear}-${String(endMonth).padStart(2, '0')}-${String(endDay).padStart(2, '0')}`)
  } else {
    start = now.subtract(1, 'year')
    end = now
  }

  form.start_date = start
  form.end_date = end

  // 清除验证状态
  nextTick(() => {
    formRef.value?.clearValidate(['start_date', 'end_date'])
  })
}

// 构建Portfolio组件树状数据
const buildPortfolioTree = (portfolio: any) => {
  const treeData: any[] = []

  // 添加基本信息
  const basicInfo: any[] = [
    { title: 'UUID', value: portfolio.uuid },
    { title: '模式', value: getModeLabel(portfolio.mode) },
    { title: '初始资金', value: `¥${portfolio.initial_cash?.toLocaleString()}` },
    { title: '当前资金', value: `¥${portfolio.current_cash?.toLocaleString()}` },
  ]

  // 策略
  if (portfolio.strategies?.length) {
    const strategyChildren = portfolio.strategies.map((s: any) => ({
      title: s.name,
      key: `strategy-${s.uuid}`,
      children: buildComponentProps(s)
    }))
    treeData.push({
      title: `策略 (${portfolio.strategies.length})`,
      key: 'strategies',
      children: strategyChildren
    })
  }

  // 选股器
  if (portfolio.selectors?.length) {
    const selectorChildren = portfolio.selectors.map((s: any) => ({
      title: s.name,
      key: `selector-${s.uuid}`,
      children: buildComponentProps(s)
    }))
    treeData.push({
      title: `选股器 (${portfolio.selectors.length})`,
      key: 'selectors',
      children: selectorChildren
    })
  }

  // Sizer
  if (portfolio.sizers?.length) {
    const sizerChildren = portfolio.sizers.map((s: any) => ({
      title: s.name,
      key: `sizer-${s.uuid}`,
      children: buildComponentProps(s)
    }))
    treeData.push({
      title: `Sizer (${portfolio.sizers.length})`,
      key: 'sizers',
      children: sizerChildren
    })
  }

  // 风控
  if (portfolio.risk_managers?.length) {
    const riskChildren = portfolio.risk_managers.map((r: any) => ({
      title: r.name,
      key: `risk-${r.uuid}`,
      children: buildComponentProps(r)
    }))
    treeData.push({
      title: `风控 (${portfolio.risk_managers.length})`,
      key: 'risk_managers',
      children: riskChildren
    })
  }

  // 如果没有组件，显示基本信息
  if (treeData.length === 0) {
    return [{
      title: '基本信息',
      key: 'basic',
      children: basicInfo
    }]
  }

  return treeData
}

// 构建组件属性树
const buildComponentProps = (component: any) => {
  const props: any[] = []

  // 跳过不需要展示的字段
  const skipKeys = new Set(['uuid', 'name', 'type', 'mount_id', 'created_at'])

  for (const [key, value] of Object.entries(component)) {
    if (skipKeys.has(key)) continue
    if (value === null || value === undefined) continue

    if (key === 'code' && typeof value === 'string') {
      // 组件代码 - 解析类名和__init__参数
      const parsed = parseComponentCode(value)

      // 添加类名
      if (parsed.className) {
        props.push({
          title: '类名',
          value: parsed.className
        })
      }

      // 直接添加__init__参数，不使用中间层
      if (parsed.params && parsed.params.length > 0) {
        parsed.params.forEach((p: any) => {
          props.push({
            title: p.name,
            value: p.default !== undefined ? formatValue(p.default) : '必填'
          })
        })
      }
    } else {
      // 其他字段直接显示
      props.push({
        title: key,
        value: value
      })
    }
  }

  return props
}

// 解析组件代码，提取类名和__init__参数
const parseComponentCode = (code: string) => {
  const result: any = {
    className: '',
    baseClass: '',
    params: []
  }

  // 提取类名和基类：class XxxxStrategy(BaseStrategy):
  const classMatch = code.match(/class\s+(\w+)\s*\(([^)]*)\)/)
  if (classMatch) {
    result.className = classMatch[1]
    result.baseClass = classMatch[2]?.trim() || 'BaseStrategy'
  }

  // 提取__init__参数（支持多行）
  // 匹配从 def __init__( 到 ): 或 ): 的所有内容
  const initMatch = code.match(/def\s+__init__\s*\(([\s\S]*?)\)(?:\s*->\s*[^:]+)?:/)
  if (initMatch) {
    const paramsStr = initMatch[1]
    console.log('[parseComponentCode] paramsStr:', paramsStr)

    // 分割参数，处理逗号分隔
    // 需要小心处理嵌套的括号和字符串
    const params = splitPythonParams(paramsStr)
      .map(p => p.trim())
      .filter(p => p && p !== 'self' && !p.startsWith('*') && !p.startsWith('**'))

    console.log('[parseComponentCode] split params:', params)

    result.params = params.map(param => {
      // 解析参数: name: type = default_value
      // 移除默认值中的注释
      const cleanParam = param.replace(/#.*/, '').trim()
      const match = cleanParam.match(/(\w+)(?:\s*:\s*([^=]+))?(?:\s*=\s*(.+))?/)
      console.log('[parseComponentCode] param:', cleanParam, 'match:', match)
      if (match) {
        return {
          name: match[1],
          type: match[2]?.trim() || 'Any',
          default: match[3]?.trim()
        }
      }
      return {
        name: cleanParam,
        type: 'Any',
        default: null
      }
    })
  }

  return result
}

// 辅助函数：分割Python参数（处理括号嵌套和字符串）
const splitPythonParams = (paramsStr: string): string[] => {
  const params: string[] = []
  let current = ''
  let depth = 0
  let inString = false
  let stringChar = ''

  for (let i = 0; i < paramsStr.length; i++) {
    const char = paramsStr[i]

    if ((char === '"' || char === "'") && (i === 0 || paramsStr[i-1] !== '\\')) {
      if (!inString) {
        inString = true
        stringChar = char
      } else if (char === stringChar) {
        inString = false
      }
    }

    if (!inString) {
      if (char === '(' || char === '[' || char === '{') {
        depth++
      } else if (char === ')' || char === ']' || char === '}') {
        depth--
      } else if (char === ',' && depth === 0) {
        params.push(current)
        current = ''
        continue
      }
    }

    current += char
  }

  if (current) {
    params.push(current)
  }

  return params
}

// 格式化值显示
const formatValue = (value: any) => {
  if (typeof value === 'boolean') {
    return value ? '是' : '否'
  }
  if (typeof value === 'number') {
    // 如果是整数，直接显示；如果是小数，保留4位
    return Number.isInteger(value) ? value : parseFloat(value.toFixed(4))
  }
  if (Array.isArray(value)) {
    return `[${value.join(', ')}]`
  }
  return String(value)
}

// 处理Portfolio选择
const handlePortfolioSelect = async (value: string) => {
  // 加载Portfolio详情
  if (!selectedPortfolioDetails.value.has(value)) {
    try {
      const response = await portfolioApi.get(value)
      selectedPortfolioDetails.value.set(value, response.data || null)
    } catch (error: any) {
      message.error(`加载 Portfolio 信息失败: ${error.message}`)
    }
  }
  // 默认展开所有选中的Portfolio
  portfolioCollapseActiveKeys.value = [...form.portfolio_uuids]
  // 选择后关闭下拉框
  setTimeout(() => {
    portfolioSelectRef.value?.blur()
  }, 100)
}

// 处理Portfolio取消选择
const handlePortfolioDeselect = (value: string) => {
  // 清理未选中的详情
  selectedPortfolioDetails.value.delete(value)
  // 更新展开状态
  portfolioCollapseActiveKeys.value = [...form.portfolio_uuids]
}

// 过滤函数
const filterPortfolioOption = (input: string, option: any) => {
  const portfolio = portfolios.value.find(p => p.uuid === option.value)
  if (!portfolio) return false
  return portfolio.name.toLowerCase().includes(input.toLowerCase())
}

// 步骤控制
const nextStep = () => {
  if (currentStep.value === 0) {
    if (!canGoToStep1.value) {
      message.warning('请填写任务名称并选择至少一个投资组合')
      return
    }
    currentStep.value = 1
    // 默认展开撮合器配置
    configActiveKey.value = ['broker']
  } else if (currentStep.value === 1) {
    currentStep.value = 2
  }
}

const prevStep = () => {
  if (currentStep.value > 0) {
    currentStep.value -= 1
  }
}

// 返回
const goBack = () => {
  router.back()
}

// 提交表单
const handleSubmit = async () => {
  try {
    submitting.value = true

    const submitData: BacktestCreate = {
      name: form.name,
      portfolio_uuids: form.portfolio_uuids,
      engine_config: {
        start_date: form.start_date.format('YYYY-MM-DD'),
        end_date: form.end_date.format('YYYY-MM-DD'),
        broker_type: form.engine_config.broker_type,
        initial_cash: form.engine_config.initial_cash ?? undefined,
        commission_rate: form.engine_config.commission_rate,
        slippage_rate: form.engine_config.slippage_rate,
        broker_attitude: form.engine_config.broker_attitude,
        commission_min: form.engine_config.commission_min,
        analyzers: form.engine_config.analyzers
          .filter(a => a.name && a.type)
          .map(({ name, type, config }) => ({ name, type, config } as AnalyzerConfig)),
      },
    }

    const response = await backtestApi.create(submitData)
    const backtest = response.data

    message.success(`回测任务创建成功！任务ID: ${backtest.uuid}`)

    setTimeout(() => {
      router.push(`/backtest/${backtest.uuid}`)
    }, 500)
  } catch (error: any) {
    message.error(`创建回测任务失败: ${error.message}`)
  } finally {
    submitting.value = false
  }
}

// 生命周期
onMounted(() => {
  loadPortfolios()
  loadAnalyzers()

  // 默认设置最近一年的日期
  setDateRange(0, 0, 0, 0, 0, 0, -1, false)
})

// 加载Portfolio列表（只获取回测模式的）
const loadPortfolios = async () => {
  loadingPortfolios.value = true
  try {
    const response = await portfolioApi.list({ mode: 'BACKTEST' })
    portfolios.value = response.data || []
  } catch (error: any) {
    message.error(`加载投资组合列表失败: ${error.message}`)
  } finally {
    loadingPortfolios.value = false
  }
}

// 加载分析器列表
const loadAnalyzers = async () => {
  loadingAnalyzers.value = true
  try {
    const response = await backtestApi.getAnalyzers()
    analyzers.value = response.data || []
  } catch (error: any) {
    message.error(`加载分析器列表失败: ${error.message}`)
  } finally {
    loadingAnalyzers.value = false
  }
}
</script>

<style scoped lang="less">
.backtest-create-container {
  padding: 24px;
  background: #f5f7fa;
  min-height: calc(100vh - 64px);
}

.page-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
}

.back-btn {
  display: flex;
  align-items: center;
  gap: 4px;
}

.title-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0;
}

.page-subtitle {
  font-size: 14px;
  color: #666;
  margin: 0;
}

.form-card {
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  max-width: 900px;
  margin: 0 auto;
}

.form-steps {
  margin-bottom: 32px;
  padding-bottom: 24px;
  border-bottom: 1px solid #f0f0f0;
}

.step-content {
  min-height: 400px;
}

.form-section {
  margin-bottom: 32px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0 0 16px 0;
  padding-bottom: 12px;
  border-bottom: 1px solid #f0f0f0;
}

.required-mark {
  color: #ff4d4f;
  margin-left: 4px;
}

.optional-mark {
  color: #999;
  font-weight: 400;
  font-size: 14px;
}

.section-desc {
  font-size: 14px;
  color: #666;
  margin: -8px 0 16px 0;
}

// Portfolio 选择
.portfolio-option {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.portfolio-name {
  font-weight: 500;
}

.selected-portfolios-list {
  margin-top: 20px;
  background: #fafafa;
  border-radius: 8px;
  padding: 16px;
}

.selected-header {
  font-size: 14px;
  font-weight: 500;
  color: #666;
  margin-bottom: 12px;
}

// Portfolio 组件树状图显示
.component-tree {
  background: #fafafa;
  border-radius: 6px;
  padding: 12px;

  :deep(.ant-tree-treenode) {
    padding: 2px 0;
  }

  :deep(.ant-tree-node-content-wrapper) {
    &:hover {
      background: rgba(24, 144, 255, 0.05);
    }
  }

  :deep(.ant-tree-switcher) {
    color: #999;
  }

  :deep(.ant-tree-title) {
    font-size: 13px;
  }
}

.tree-node-title {
  font-weight: 500;
  color: #1a1a1a;
}

.tree-node-value {
  display: flex;
  align-items: center;
  gap: 4px;

  .tree-node-key {
    color: #666;
    font-weight: 400;
  }

  .tree-node-value-text {
    color: #1890ff;
    font-weight: 500;
    font-family: 'Consolas', 'Monaco', monospace;
  }
}

// 保留旧的组件详情样式（备用）
.portfolio-components-detail {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.component-section {
  background: #fafafa;
  border-radius: 6px;
  padding: 12px;
}

.component-section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  font-size: 13px;
  font-weight: 500;
}

.component-type-label {
  color: #333;
}

.component-names {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.no-components-inline {
  padding: 16px;
  text-align: center;
}

// 保留原有的简洁标签样式（用于可能的其他用途）
.portfolio-components-mini {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  padding: 8px 0;
}

.comp-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 8px;
  background: #fff;
  border: 1px solid #e8e8e8;
  border-radius: 4px;
  font-size: 12px;
  color: #666;
}

.comp-icon {
  width: 16px;
  height: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 3px;
  font-size: 9px;
  font-weight: 600;
  color: #fff;

  &.strategy-icon {
    background: #1890ff;
  }

  &.selector-icon {
    background: #52c41a;
  }

  &.sizer-icon {
    background: #fa8c16;
  }

  &.risk-icon {
    background: #f5222d;
  }
}

// 日期选择
.date-quick-select {
  margin-bottom: 16px;
}

.date-row {
  margin-top: 16px;
}

// 配置折叠面板
.config-collapse {
  margin-top: 24px;

  :deep(.ant-collapse-header) {
    font-weight: 500;
  }
}

// 分析器列表
.analyzers-list {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.analyzer-item {
  padding: 12px 16px;
  background: #f5f5f5;
  border: 1px solid #e8e8e8;
  border-radius: 6px;
}

.analyzer-main {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}

.analyzer-name {
  font-weight: 500;
  flex: 1;
}

.analyzer-config {
  font-size: 12px;
  color: #666;
  font-family: monospace;
}

// 步骤操作按钮
.step-actions {
  display: flex;
  justify-content: center;
  gap: 16px;
  padding-top: 24px;
  border-top: 1px solid #f0f0f0;
  margin-top: 32px;
}

// 详情弹窗
.portfolio-detail-modal {
  .modal-components {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
}

.modal-component-section {
  background: #fafafa;
  border-radius: 8px;
  padding: 12px;
}

.modal-section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 500;
  margin: 0 0 12px 0;
}

.no-components-hint {
  padding: 24px;
  text-align: center;
}

// 分析器选择弹窗
.analyzer-select-modal {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.analyzer-select-item {
  padding: 12px;
  border: 1px solid #e8e8e8;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: #1890ff;
    background: #f0f9ff;
  }

  .analyzer-select-name {
    font-weight: 500;
    color: #1a1a1a;
  }

  .analyzer-select-desc {
    font-size: 12px;
    color: #8c8c8c;
    margin-top: 4px;
  }
}
</style>
