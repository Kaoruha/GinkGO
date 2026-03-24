<template>
  <div class="backtest-create-container">
    <div class="page-header">
      <button class="btn-text" @click="goBack">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M19 12H5M12 19l-7-7 7-7"/>
        </svg>
        返回
      </button>
      <div class="title-section">
        <h1 class="page-title">创建回测任务</h1>
        <p class="page-subtitle">配置回测参数并创建任务</p>
      </div>
    </div>

    <div class="form-card">
      <form @submit.prevent="handleSubmit">
        <!-- 步骤指示器 -->
        <div class="steps-indicator">
          <div class="step-item" :class="{ active: currentStep === 0, completed: currentStep > 0 }">
            <div class="step-number">1</div>
            <span class="step-label">选择投资组合</span>
          </div>
          <div class="step-line" :class="{ active: currentStep > 0 }"></div>
          <div class="step-item" :class="{ active: currentStep === 1, completed: currentStep > 1 }">
            <div class="step-number">2</div>
            <span class="step-label">配置参数</span>
          </div>
          <div class="step-line" :class="{ active: currentStep > 1 }"></div>
          <div class="step-item" :class="{ active: currentStep === 2 }">
            <div class="step-number">3</div>
            <span class="step-label">分析器（可选）</span>
          </div>
        </div>

        <!-- 步骤 1: 选择投资组合 -->
        <div v-show="currentStep === 0" class="step-content">
          <div class="form-section">
            <h3 class="section-title">基本信息</h3>
            <div class="form-group">
              <label class="form-label">任务名称</label>
              <input v-model="form.name" type="text" placeholder="请输入任务名称" class="form-input" />
            </div>
          </div>

          <div class="form-section">
            <h3 class="section-title">
              选择投资组合 <span class="required-mark">*</span>
            </h3>
            <div class="form-group">
              <label class="form-label">选择一个或多个投资组合</label>
              <select v-model="selectedPortfolio" class="form-select" @change="handlePortfolioSelect">
                <option value="">请选择投资组合</option>
                <option v-for="portfolio in portfolios" :key="portfolio.uuid" :value="portfolio.uuid">
                  {{ portfolio.name }} ({{ getModeLabel(portfolio.mode) }})
                </option>
              </select>
            </div>

            <!-- 已选择的Portfolio列表 -->
            <div v-if="selectedPortfolios.length > 0" class="selected-portfolios-list">
              <div class="selected-header">
                <span>已选择 {{ selectedPortfolios.length }} 个投资组合</span>
              </div>
              <div class="portfolio-items">
                <details v-for="portfolio in selectedPortfolios" :key="portfolio.uuid" class="portfolio-collapse" open>
                  <summary class="portfolio-header">
                    <span class="portfolio-name">{{ portfolio.name }}</span>
                    <span class="tag" :class="'tag-' + getModeTagColor(portfolio.mode)">
                      {{ getModeLabel(portfolio.mode) }}
                    </span>
                    <button type="button" class="btn-remove" @click.prevent="removePortfolio(portfolio.uuid)">×</button>
                  </summary>
                  <div class="portfolio-body">
                    <div class="component-tree">
                      <div v-for="(section, key) in buildPortfolioTree(portfolio)" :key="key" class="tree-section">
                        <div class="tree-section-title">{{ section.title }}</div>
                        <div class="tree-items">
                          <div v-for="(item, idx) in section.children" :key="idx" class="tree-item">
                            <div v-if="item.value !== undefined" class="tree-node-value">
                              <span class="tree-node-key">{{ item.title }}:</span>
                              <span class="tree-node-value-text">{{ formatValue(item.value) }}</span>
                            </div>
                            <span v-else class="tree-node-title">{{ item.title }}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </details>
              </div>
            </div>
          </div>

          <div class="step-actions">
            <button type="button" class="btn-secondary" @click="goBack">取消</button>
            <button type="button" class="btn-primary" :disabled="!canGoToStep1" @click="nextStep">
              下一步
            </button>
          </div>
        </div>

        <!-- 步骤 2: 配置参数 -->
        <div v-show="currentStep === 1" class="step-content">
          <div class="form-section">
            <h3 class="section-title">回测时间范围</h3>

            <div class="date-quick-select">
              <button type="button" class="btn-small" @click="setDateRange(0, 0, 0, 0, 0, 0, -1, false)">最近1年</button>
              <button type="button" class="btn-small" @click="setDateRange(0, 0, 0, 0, 0, 0, -5, false)">最近5年</button>
              <button type="button" class="btn-small" @click="setDateRange(2023, 1, 1, 2023, 12, 31, 0, false)">2023年</button>
              <button type="button" class="btn-small" @click="setDateRange(2024, 1, 1, 2024, 12, 31, 0, false)">2024年</button>
              <button type="button" class="btn-small" @click="setDateRange(0, 0, 0, 0, 0, 0, 0, true)">全周期(1992-)</button>
            </div>

            <div class="date-row">
              <div class="form-group">
                <label class="form-label">开始日期 <span class="required-mark">*</span></label>
                <input v-model="form.start_date" type="date" class="form-input" />
              </div>
              <div class="form-group">
                <label class="form-label">结束日期 <span class="required-mark">*</span></label>
                <input v-model="form.end_date" type="date" class="form-input" />
              </div>
            </div>
          </div>

          <details class="config-collapse" :open="configActiveKey.includes('broker')">
            <summary class="collapse-header">
              <h4>撮合器配置</h4>
            </summary>
            <div class="collapse-body">
              <div class="form-row">
                <div class="form-group">
                  <label class="form-label">撮合态度</label>
                  <select v-model="form.engine_config.broker_attitude" class="form-select">
                    <option :value="1">悲观（成交难）</option>
                    <option :value="2">乐观（成交易）</option>
                    <option :value="3">随机</option>
                  </select>
                </div>
                <div class="form-group">
                  <label class="form-label">手续费率 (%)</label>
                  <input v-model.number="form.engine_config.commission_rate" type="number" step="0.0001" min="0" max="1" class="form-input" />
                </div>
              </div>
              <div class="form-row">
                <div class="form-group">
                  <label class="form-label">滑点率 (%)</label>
                  <input v-model.number="form.engine_config.slippage_rate" type="number" step="0.0001" min="0" max="1" class="form-input" />
                </div>
                <div class="form-group">
                  <label class="form-label">最小手续费</label>
                  <input v-model.number="form.engine_config.commission_min" type="number" step="1" min="0" class="form-input" />
                </div>
              </div>
            </div>
          </details>

          <div class="step-actions">
            <button type="button" class="btn-secondary" @click="prevStep">上一步</button>
            <button type="button" class="btn-secondary" @click="nextStep">下一步</button>
            <button type="submit" class="btn-primary" :disabled="submitting">
              {{ submitting ? '创建中...' : '创建回测任务' }}
            </button>
          </div>
        </div>

        <!-- 步骤 3: 分析器（可选） -->
        <div v-show="currentStep === 2" class="step-content">
          <div class="form-section">
            <h3 class="section-title">
              添加分析器 <span class="optional-mark">(可选)</span>
            </h3>
            <p class="section-desc">
              分析器在 Engine 级别统一管理，可接收所有 Portfolio 的数据进行分析
            </p>

            <button type="button" class="btn-dashed" @click="showAnalyzerSelector">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <line x1="12" y1="5" x2="12" y2="19"/>
                <line x1="5" y1="12" x2="19" y2="12"/>
              </svg>
              添加分析器
            </button>

            <div v-if="form.engine_config.analyzers.length > 0" class="analyzers-list">
              <div v-for="(analyzer, index) in form.engine_config.analyzers" :key="index" class="analyzer-item">
                <div class="analyzer-main">
                  <span class="analyzer-name">{{ analyzer.name || analyzer.type }}</span>
                  <span class="tag tag-blue">{{ analyzer.type }}</span>
                  <button type="button" class="btn-small btn-danger" @click="removeAnalyzer(index)">
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                      <polyline points="3 6 5 6 21 6"/>
                      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                    </svg>
                    移除
                  </button>
                </div>
                <div class="analyzer-config">{{ getAnalyzerConfig(analyzer.type) }}</div>
              </div>
            </div>
          </div>

          <div class="step-actions">
            <button type="button" class="btn-secondary" @click="prevStep">上一步</button>
            <button type="submit" class="btn-primary" :disabled="submitting">
              {{ submitting ? '创建中...' : '创建回测任务' }}
            </button>
          </div>
        </div>
      </form>
    </div>

    <!-- 分析器选择弹窗 -->
    <div v-if="analyzerModalVisible" class="modal-overlay" @click.self="analyzerModalVisible = false">
      <div class="modal">
        <div class="modal-header">
          <h3>选择分析器</h3>
          <button class="modal-close" @click="analyzerModalVisible = false">×</button>
        </div>
        <div class="modal-body">
          <div class="analyzer-select-list">
            <div
              v-for="opt in analyzerOptions"
              :key="opt.value"
              class="analyzer-select-item"
              @click="selectAnalyzer(opt)"
            >
              <div class="analyzer-select-name">{{ opt.label }}</div>
              <div class="analyzer-select-desc">{{ opt.desc }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { portfolioApi } from '@/api/modules/portfolio'
import { backtestApi } from '@/api/modules/backtest'

const router = useRouter()

// 简化的通知函数
const showToast = (message: string, type: 'success' | 'error' = 'success') => {
  console.log(`[${type.toUpperCase()}] ${message}`)
}

// 状态
const submitting = ref(false)
const loadingPortfolios = ref(false)
const portfolios = ref<any[]>([])
const selectedPortfolioDetails = ref<Map<string, any>>(new Map())
const analyzers = ref<any[]>([])

// 步骤状态
const currentStep = ref(0)
const configActiveKey = ref(['broker'])

// 分析器弹窗
const analyzerModalVisible = ref(false)
const selectedPortfolio = ref('')

// 表单数据
const form = reactive({
  name: '',
  portfolio_uuids: [] as string[],
  start_date: '',
  end_date: '',
  engine_config: {
    broker_type: 'backtest' as 'backtest' | 'okx',
    initial_cash: null as number | null,
    commission_rate: 0.0003,
    slippage_rate: 0.0001,
    broker_attitude: 2,
    commission_min: 5,
    analyzers: [] as any[],
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

// 获取模式标签
const getModeLabel = (mode: string) => {
  const labels: Record<string, string> = {
    BACKTEST: '回测',
    LIVE: '实盘',
    PAPER: '模拟盘'
  }
  return labels[mode] || mode
}

// 获取模式标签颜色
const getModeTagColor = (mode: string) => {
  const colors: Record<string, string> = {
    BACKTEST: 'blue',
    LIVE: 'green',
    PAPER: 'orange'
  }
  return colors[mode] || 'gray'
}

// 格式化值显示
const formatValue = (value: any) => {
  if (typeof value === 'boolean') {
    return value ? '是' : '否'
  }
  if (typeof value === 'number') {
    return Number.isInteger(value) ? value : parseFloat(value.toFixed(4))
  }
  if (Array.isArray(value)) {
    return `[${value.join(', ')}]`
  }
  return String(value)
}

// 构建Portfolio组件树状数据
const buildPortfolioTree = (portfolio: any) => {
  const treeData: any = {}

  // 添加基本信息
  treeData.basic = {
    title: '基本信息',
    children: [
      { title: 'UUID', value: portfolio.uuid },
      { title: '模式', value: getModeLabel(portfolio.mode) },
      { title: '初始资金', value: `¥${portfolio.initial_cash?.toLocaleString()}` },
    ]
  }

  // 策略
  if (portfolio.strategies?.length) {
    treeData.strategies = {
      title: `策略 (${portfolio.strategies.length})`,
      children: portfolio.strategies.map((s: any) => ({ title: s.name }))
    }
  }

  // 选股器
  if (portfolio.selectors?.length) {
    treeData.selectors = {
      title: `选股器 (${portfolio.selectors.length})`,
      children: portfolio.selectors.map((s: any) => ({ title: s.name }))
    }
  }

  return treeData
}

// 选择Portfolio
const handlePortfolioSelect = async () => {
  if (!selectedPortfolio.value) return
  const uuid = selectedPortfolio.value

  if (!form.portfolio_uuids.includes(uuid)) {
    form.portfolio_uuids.push(uuid)

    // 加载详情
    if (!selectedPortfolioDetails.value.has(uuid)) {
      try {
        const response = await portfolioApi.get(uuid)
        selectedPortfolioDetails.value.set(uuid, response.data || null)
      } catch (error: any) {
        showToast(`加载 Portfolio 信息失败: ${error.message}`, 'error')
      }
    }
  }

  selectedPortfolio.value = ''
}

// 移除Portfolio
const removePortfolio = (uuid: string) => {
  const index = form.portfolio_uuids.indexOf(uuid)
  if (index > -1) {
    form.portfolio_uuids.splice(index, 1)
    selectedPortfolioDetails.value.delete(uuid)
  }
}

// 显示分析器选择器
const showAnalyzerSelector = () => {
  analyzerModalVisible.value = true
}

// 选择分析器
const selectAnalyzer = (opt: any) => {
  form.engine_config.analyzers.push({
    name: opt.defaultName,
    type: opt.value,
    config: opt.defaultConfig
  })
  analyzerModalVisible.value = false
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
  const now = new Date()
  let start, end

  if (allTime) {
    start = new Date('1992-01-01')
    end = now
  } else if (offsetYears < 0) {
    start = new Date(now.getFullYear() + offsetYears, now.getMonth(), now.getDate())
    end = now
  } else if (year > 0) {
    start = new Date(year, month - 1, day)
    end = new Date(endYear, endMonth - 1, endDay)
  } else {
    start = new Date(now.getFullYear() - 1, now.getMonth(), now.getDate())
    end = now
  }

  form.start_date = start.toISOString().split('T')[0]
  form.end_date = end.toISOString().split('T')[0]
}

// 步骤控制
const nextStep = () => {
  if (currentStep.value === 0) {
    if (!canGoToStep1.value) {
      showToast('请填写任务名称并选择至少一个投资组合', 'error')
      return
    }
    currentStep.value = 1
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

    const submitData = {
      name: form.name,
      portfolio_uuids: form.portfolio_uuids,
      engine_config: {
        start_date: form.start_date,
        end_date: form.end_date,
        broker_type: form.engine_config.broker_type,
        initial_cash: form.engine_config.initial_cash ?? undefined,
        commission_rate: form.engine_config.commission_rate,
        slippage_rate: form.engine_config.slippage_rate,
        broker_attitude: form.engine_config.broker_attitude,
        commission_min: form.engine_config.commission_min,
        analyzers: form.engine_config.analyzers
          .filter(a => a.name && a.type)
          .map(({ name, type, config }) => ({ name, type, config })),
      },
    }

    const response = await backtestApi.create(submitData)
    const backtest = response.data

    showToast(`回测任务创建成功！任务ID: ${backtest.uuid}`)

    setTimeout(() => {
      router.push(`/backtest/${backtest.uuid}`)
    }, 500)
  } catch (error: any) {
    showToast(`创建回测任务失败: ${error.message}`, 'error')
  } finally {
    submitting.value = false
  }
}

// 生命周期
onMounted(() => {
  loadPortfolios()
  loadAnalyzers()
  setDateRange(0, 0, 0, 0, 0, 0, -1, false)
})

// 加载Portfolio列表
const loadPortfolios = async () => {
  loadingPortfolios.value = true
  try {
    const response = await portfolioApi.list({ mode: 'BACKTEST' })
    portfolios.value = response.data || []
  } catch (error: any) {
    showToast(`加载投资组合列表失败: ${error.message}`, 'error')
  } finally {
    loadingPortfolios.value = false
  }
}

// 加载分析器列表
const loadAnalyzers = async () => {
  try {
    const response = await backtestApi.getAnalyzers()
    analyzers.value = response.data || []
  } catch (error: any) {
    showToast(`加载分析器列表失败: ${error.message}`, 'error')
  }
}
</script>

<style scoped>
.backtest-create-container {
  padding: 24px;
  background: #0f0f1a;
  min-height: calc(100vh - 64px);
}

.page-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 24px;
  flex-wrap: wrap;
}

.btn-text {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background: transparent;
  border: none;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-text:hover {
  background: #2a2a3e;
}

.title-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #ffffff;
  margin: 0;
}

.page-subtitle {
  font-size: 14px;
  color: #8a8a9a;
  margin: 0;
}

.form-card {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  padding: 24px;
  max-width: 900px;
  margin: 0 auto;
}

.steps-indicator {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-bottom: 32px;
  padding-bottom: 24px;
  border-bottom: 1px solid #2a2a3e;
}

.step-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.step-number {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #2a2a3e;
  border: 2px solid #3a3a4e;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #8a8a9a;
  font-weight: 600;
  font-size: 14px;
  transition: all 0.2s;
}

.step-item.active .step-number {
  background: #1890ff;
  border-color: #1890ff;
  color: #ffffff;
}

.step-item.completed .step-number {
  background: #52c41a;
  border-color: #52c41a;
  color: #ffffff;
}

.step-label {
  font-size: 12px;
  color: #8a8a9a;
}

.step-item.active .step-label {
  color: #ffffff;
}

.step-line {
  width: 60px;
  height: 2px;
  background: #3a3a4e;
  transition: all 0.2s;
}

.step-line.active {
  background: #52c41a;
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
  color: #ffffff;
  margin: 0 0 16px 0;
  padding-bottom: 12px;
  border-bottom: 1px solid #2a2a3e;
}

.required-mark {
  color: #f5222d;
  margin-left: 4px;
}

.optional-mark {
  color: #8a8a9a;
  font-weight: 400;
  font-size: 14px;
}

.section-desc {
  font-size: 14px;
  color: #8a8a9a;
  margin: -8px 0 16px 0;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 16px;
}

.form-label {
  font-size: 13px;
  color: #8a8a9a;
  font-weight: 500;
}

.form-input,
.form-select {
  padding: 10px 12px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  transition: border-color 0.2s;
}

.form-input:focus,
.form-select:focus {
  outline: none;
  border-color: #1890ff;
}

.form-input::placeholder {
  color: #5a5a6e;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.date-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-top: 16px;
}

.date-quick-select {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.btn-small {
  padding: 6px 12px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-small:hover {
  border-color: #1890ff;
  color: #1890ff;
}

.btn-danger {
  background: rgba(245, 34, 45, 0.1);
  border-color: #f5222d;
  color: #f5222d;
}

.btn-danger:hover {
  background: rgba(245, 34, 45, 0.2);
}

.btn-dashed {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
  padding: 12px;
  background: transparent;
  border: 2px dashed #3a3a4e;
  border-radius: 4px;
  color: #8a8a9a;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-dashed:hover {
  border-color: #1890ff;
  color: #1890ff;
}

.btn-primary {
  padding: 10px 20px;
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
  padding: 10px 20px;
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

.selected-portfolios-list {
  margin-top: 20px;
  background: #2a2a3e;
  border-radius: 8px;
  padding: 16px;
}

.selected-header {
  font-size: 14px;
  font-weight: 500;
  color: #ffffff;
  margin-bottom: 12px;
}

.portfolio-items {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.portfolio-collapse {
  background: #1a1a2e;
  border-radius: 6px;
  overflow: hidden;
}

.portfolio-collapse summary {
  list-style: none;
}

.portfolio-collapse::-webkit-details-marker {
  display: none;
}

.portfolio-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  cursor: pointer;
  user-select: none;
}

.portfolio-header:hover {
  background: #2a2a3e;
}

.portfolio-name {
  flex: 1;
  font-weight: 500;
  color: #ffffff;
}

.portfolio-body {
  padding: 12px 16px;
  border-top: 1px solid #2a2a3e;
}

.component-tree {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.tree-section {
  background: #2a2a3e;
  border-radius: 6px;
  padding: 12px;
}

.tree-section-title {
  font-size: 13px;
  font-weight: 500;
  color: #ffffff;
  margin-bottom: 8px;
}

.tree-items {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding-left: 12px;
}

.tree-item {
  font-size: 13px;
}

.tree-node-title {
  color: #ffffff;
  font-weight: 500;
}

.tree-node-value {
  display: flex;
  align-items: center;
  gap: 4px;
}

.tree-node-key {
  color: #8a8a9a;
}

.tree-node-value-text {
  color: #1890ff;
  font-family: 'Consolas', 'Monaco', monospace;
}

.config-collapse {
  background: #2a2a3e;
  border-radius: 8px;
  margin-top: 24px;
  overflow: hidden;
}

.config-collapse summary {
  list-style: none;
  cursor: pointer;
}

.config-collapse::-webkit-details-marker {
  display: none;
}

.collapse-header {
  padding: 16px 20px;
  border-bottom: 1px solid #3a3a4e;
}

.collapse-header h4 {
  margin: 0;
  font-size: 14px;
  font-weight: 500;
  color: #ffffff;
}

.collapse-body {
  padding: 20px;
}

.analyzers-list {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.analyzer-item {
  padding: 12px 16px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
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
  color: #ffffff;
}

.analyzer-config {
  font-size: 12px;
  color: #8a8a9a;
  font-family: monospace;
}

.step-actions {
  display: flex;
  justify-content: center;
  gap: 16px;
  padding-top: 24px;
  border-top: 1px solid #2a2a3e;
  margin-top: 32px;
}

.tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.tag-blue {
  background: rgba(24, 144, 255, 0.2);
  color: #1890ff;
}

.tag-green {
  background: rgba(82, 196, 26, 0.2);
  color: #52c41a;
}

.tag-orange {
  background: rgba(250, 140, 22, 0.2);
  color: #fa8c16;
}

.tag-gray {
  background: #2a2a3e;
  color: #8a8a9a;
}

.btn-remove {
  padding: 2px 8px;
  background: transparent;
  border: none;
  color: #8a8a9a;
  font-size: 18px;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.2s;
}

.btn-remove:hover {
  background: rgba(245, 34, 45, 0.1);
  color: #f5222d;
}

/* 模态框 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  width: 90%;
  max-width: 500px;
  max-height: 80vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #2a2a3e;
}

.modal-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
}

.modal-close {
  padding: 4px 8px;
  background: transparent;
  border: none;
  color: #8a8a9a;
  font-size: 20px;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.2s;
}

.modal-close:hover {
  background: #2a2a3e;
  color: #ffffff;
}

.modal-body {
  padding: 16px;
  overflow-y: auto;
}

.analyzer-select-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.analyzer-select-item {
  padding: 12px;
  border: 1px solid #3a3a4e;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.analyzer-select-item:hover {
  border-color: #1890ff;
  background: rgba(24, 144, 255, 0.05);
}

.analyzer-select-name {
  font-weight: 500;
  color: #ffffff;
}

.analyzer-select-desc {
  font-size: 12px;
  color: #8a8a9a;
  margin-top: 4px;
}

@media (max-width: 768px) {
  .steps-indicator {
    flex-wrap: wrap;
  }

  .step-line {
    display: none;
  }

  .form-row {
    grid-template-columns: 1fr;
  }

  .date-row {
    grid-template-columns: 1fr;
  }
}
</style>
