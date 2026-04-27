<template>
  <div class="portfolio-form-editor" :class="{ 'modal-mode': isModalMode }">
    <div class="page-header">
      <div class="header-left">
        <button v-if="!isModalMode" class="btn-text" @click="goBack">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="15 18 9 12 15 6"></polyline>
          </svg>
          返回
        </button>
        <div class="title-section">
          <h1 class="page-title">{{ isEditMode ? '编辑投资组合' : '创建投资组合' }}</h1>
          <p v-if="!isModalMode" class="page-subtitle">配置交易策略、选股器、仓位管理和风控规则</p>
        </div>
      </div>
      <div class="header-actions">
        <button class="btn-secondary" data-testid="btn-cancel-form" @click="goBack">取消</button>
        <button class="btn-primary" data-testid="btn-save-portfolio" :disabled="saving" @click="savePortfolio">
          {{ isEditMode ? '保存' : '创建' }}
        </button>
      </div>
    </div>

    <div class="form-layout">
      <!-- 左侧面板 -->
      <div class="left-panel">
        <form @submit.prevent>
          <!-- 基本信息卡片 -->
          <div class="card form-card">
            <div class="card-header-sm">
              <h4>基本信息</h4>
            </div>
            <div class="card-body-sm">
              <div class="form-row">
                <div class="form-group">
                  <label class="form-label">名称 <span class="required">*</span></label>
                  <input v-model="formData.name" type="text" placeholder="组合名称" data-testid="input-portfolio-name" class="form-input" />
                </div>
                <div class="form-group">
                  <label class="form-label">初始资金 <span class="required">*</span></label>
                  <div class="input-group">
                    <span class="input-prefix">¥</span>
                    <input
                      type="text"
                      :value="formatNumber(formData.initial_cash)"
                      @input="onInitialCashInput"
                      class="form-input"
                    />
                  </div>
                </div>
              </div>
              <div class="form-row">
                <div class="form-group">
                  <label class="form-label">运行模式 <span class="required">*</span></label>
                  <select v-model="formData.mode" class="form-select">
                    <option value="BACKTEST">回测</option>
                    <option value="PAPER">模拟盘</option>
                    <option value="LIVE">实盘</option>
                  </select>
                </div>
                <div class="form-group">
                  <label class="form-label">基准</label>
                  <input v-model="formData.benchmark" type="text" placeholder="000001.SZ（可选）" class="form-input" />
                </div>
              </div>
              <div class="form-group">
                <label class="form-label">描述</label>
                <textarea v-model="formData.description" :rows="2" placeholder="组合描述" class="form-textarea"></textarea>
              </div>
            </div>
          </div>

          <!-- 添加组件卡片 -->
          <div class="card form-card">
            <div class="card-header-sm">
              <h4>添加组件</h4>
            </div>
            <div class="card-body-sm">
              <div class="component-type-tabs">
                <button
                  v-for="type in componentTypes"
                  :key="type.key"
                  :class="['type-btn', { active: activeComponentType === type.key }]"
                  type="button"
                  @click="activeComponentType = type.key"
                >
                  {{ type.label }}
                </button>
              </div>

              <div class="component-selector">
                <SearchSelect
                  v-if="activeComponentType === 'selector'"
                  placeholder="搜索选股器..."
                  :search-fn="q => searchComponents('selector', q)"
                  :exclude-values="formData.selectors.map(s => s.uuid)"
                  @select="o => addSelector(o.value)"
                />
                <SearchSelect
                  v-else-if="activeComponentType === 'sizer'"
                  placeholder="搜索仓位管理器..."
                  :search-fn="q => searchComponents('sizer', q)"
                  :exclude-values="formData.sizer ? [formData.sizer.uuid] : []"
                  @select="o => addSizer(o.value)"
                />
                <SearchSelect
                  v-else-if="activeComponentType === 'strategy'"
                  placeholder="搜索策略..."
                  :search-fn="q => searchComponents('strategy', q)"
                  :exclude-values="formData.strategies.map(s => s.uuid)"
                  @select="o => addStrategy(o.value)"
                />
                <SearchSelect
                  v-else-if="activeComponentType === 'risk'"
                  placeholder="搜索风控规则..."
                  :search-fn="q => searchComponents('risk', q)"
                  :exclude-values="formData.risk_managers.map(r => r.uuid)"
                  @select="o => addRisk(o.value)"
                />
                <SearchSelect
                  v-else-if="activeComponentType === 'analyzer'"
                  placeholder="搜索分析器..."
                  :search-fn="q => searchComponents('analyzer', q)"
                  :exclude-values="formData.analyzers.map(a => a.uuid)"
                  @select="o => addAnalyzer(o.value)"
                />
              </div>
            </div>
          </div>
        </form>
      </div>

      <!-- 右侧面板 -->
      <div class="right-panel">
        <div class="card config-card">
          <div class="card-header-sm">
            <h4>组件配置</h4>
          </div>
          <div class="card-body-sm config-content">
            <!-- 选股器配置 -->
            <div v-if="formData.selectors.length > 0" class="config-section">
              <div class="section-header">
                <span class="section-title">选股器 ({{ formData.selectors.length }})</span>
              </div>
              <div class="config-list">
                <div v-for="(selector, index) in formData.selectors" :key="selector.uuid" class="config-item">
                  <div class="item-header">
                    <div class="item-info">
                      <span class="item-name">{{ selector.name }}</span>
                      <select
                        v-model="selector.version"
                        class="version-select"
                        :disabled="getComponentVersions(selector.name, 'selector').length <= 1"
                        @change="onSelectorVersionChange(index)"
                      >
                        <option v-for="v in getComponentVersions(selector.name, 'selector')" :key="v.uuid" :value="v.version">
                          {{ v.version }}{{ v.is_latest ? ' (最新)' : '' }}
                        </option>
                      </select>
                    </div>
                    <button class="btn-icon text-red" @click="removeSelector(index)">
                      <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                      </svg>
                    </button>
                  </div>
                  <div v-if="selector.parameters && selector.parameters.length > 0" class="item-params">
                    <div v-for="param in selector.parameters" :key="param.name" class="param-row">
                      <label class="param-label">{{ param.label || param.name }}</label>
                      <input
                        v-if="param.type === 'number'"
                        :value="formatNumber(selector.config[param.name] ?? 0)"
                        type="text"
                        inputmode="decimal"
                        class="param-input"
                        @focus="e => setInputValue(e, selector.config[param.name] ?? '')"
                        @blur="e => { selector.config[param.name] = parseNumber(getInputValue(e)); setInputValue(e, formatNumber(selector.config[param.name])) }"
                      />
                      <div v-else-if="param.type === 'boolean'" class="switch-container">
                        <input :id="`sel-${selector.uuid}-${param.name}`" v-model="selector.config[param.name]" type="checkbox" class="switch-input" />
                        <label :for="`sel-${selector.uuid}-${param.name}`" class="switch-label"></label>
                      </div>
                      <select v-else-if="param.type === 'select'" v-model="selector.config[param.name]" class="param-select">
                        <option v-for="opt in param.options" :key="opt" :value="opt">{{ opt }}</option>
                      </select>
                      <input v-else v-model="selector.config[param.name]" type="text" class="param-input" />
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 仓位管理器配置 -->
            <div v-if="formData.sizer" class="config-section">
              <div class="section-header">
                <span class="section-title">仓位管理器</span>
                <button class="btn-icon text-red" @click="removeSizer">
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="18" y1="6" x2="6" y2="18"></line>
                    <line x1="6" y1="6" x2="18" y2="18"></line>
                  </svg>
                </button>
              </div>
              <div class="config-list">
                <div class="config-item">
                  <div class="item-header">
                    <div class="item-info">
                      <span class="item-name">{{ formData.sizer.name }}</span>
                      <select
                        v-model="formData.sizer.version"
                        class="version-select"
                        :disabled="getComponentVersions(formData.sizer.name, 'sizer').length <= 1"
                        @change="onSizerVersionChange"
                      >
                        <option v-for="v in getComponentVersions(formData.sizer.name, 'sizer')" :key="v.uuid" :value="v.version">
                          {{ v.version }}{{ v.is_latest ? ' (最新)' : '' }}
                        </option>
                      </select>
                    </div>
                  </div>
                  <div v-if="formData.sizer.parameters && formData.sizer.parameters.length > 0" class="item-params">
                    <div v-for="param in formData.sizer.parameters" :key="param.name" class="param-row">
                      <label class="param-label">{{ param.label || param.name }}</label>
                      <input
                        v-if="param.type === 'number'"
                        :value="formatNumber(formData.sizer.config[param.name] ?? 0)"
                        type="text"
                        inputmode="decimal"
                        class="param-input"
                        @focus="e => { if (formData.sizer) setInputValue(e, formData.sizer.config[param.name] ?? '') }"
                        @blur="e => { if (formData.sizer) { formData.sizer.config[param.name] = parseNumber(getInputValue(e)); setInputValue(e, formatNumber(formData.sizer.config[param.name])) } }"
                      />
                      <div v-else-if="param.type === 'boolean'" class="switch-container">
                        <input :id="`sizer-${param.name}`" v-model="formData.sizer.config[param.name]" type="checkbox" class="switch-input" />
                        <label :for="`sizer-${param.name}`" class="switch-label"></label>
                      </div>
                      <select v-else-if="param.type === 'select'" v-model="formData.sizer.config[param.name]" class="param-select">
                        <option v-for="opt in param.options" :key="opt" :value="opt">{{ opt }}</option>
                      </select>
                      <input v-else v-model="formData.sizer.config[param.name]" type="text" class="param-input" />
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 策略配置 -->
            <div v-if="formData.strategies.length > 0" class="config-section">
              <div class="section-header">
                <span class="section-title">策略 ({{ formData.strategies.length }})</span>
              </div>
              <div class="config-list">
                <div v-for="(strategy, index) in formData.strategies" :key="strategy.uuid" class="config-item">
                  <div class="item-header">
                    <div class="item-info">
                      <span class="item-name">{{ strategy.name }}</span>
                      <select
                        v-model="strategy.version"
                        class="version-select"
                        :disabled="getComponentVersions(strategy.name, 'strategy').length <= 1"
                        @change="onStrategyVersionChange(index)"
                      >
                        <option v-for="v in getComponentVersions(strategy.name, 'strategy')" :key="v.uuid" :value="v.version">
                          {{ v.version }}{{ v.is_latest ? ' (最新)' : '' }}
                        </option>
                      </select>
                    </div>
                    <div class="item-actions">
                      <input v-model.number="strategy.weight" type="number" :min="0" :max="100" class="weight-input" />
                      <span class="unit">%</span>
                      <button class="btn-icon text-red" @click="removeStrategy(index)">
                        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                          <line x1="18" y1="6" x2="6" y2="18"></line>
                          <line x1="6" y1="6" x2="18" y2="18"></line>
                        </svg>
                      </button>
                    </div>
                  </div>
                  <div v-if="strategy.parameters && strategy.parameters.length > 0" class="item-params">
                    <div v-for="param in strategy.parameters" :key="param.name" class="param-row">
                      <label class="param-label">{{ param.label || param.name }}</label>
                      <input
                        v-if="param.type === 'number'"
                        :value="formatNumber(strategy.config[param.name] ?? 0)"
                        type="text"
                        inputmode="decimal"
                        class="param-input"
                        @focus="e => setInputValue(e, strategy.config[param.name] ?? '')"
                        @blur="e => { strategy.config[param.name] = parseNumber(getInputValue(e)); setInputValue(e, formatNumber(strategy.config[param.name])) }"
                      />
                      <div v-else-if="param.type === 'boolean'" class="switch-container">
                        <input :id="`strat-${strategy.uuid}-${param.name}`" v-model="strategy.config[param.name]" type="checkbox" class="switch-input" />
                        <label :for="`strat-${strategy.uuid}-${param.name}`" class="switch-label"></label>
                      </div>
                      <select v-else-if="param.type === 'select'" v-model="strategy.config[param.name]" class="param-select">
                        <option v-for="opt in param.options" :key="opt" :value="opt">{{ opt }}</option>
                      </select>
                      <input v-else v-model="strategy.config[param.name]" type="text" class="param-input" />
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 风控配置 -->
            <div v-if="formData.risk_managers.length > 0" class="config-section">
              <div class="section-header">
                <span class="section-title">风控 ({{ formData.risk_managers.length }})</span>
              </div>
              <div class="config-list">
                <div v-for="(risk, index) in formData.risk_managers" :key="risk.uuid" class="config-item">
                  <div class="item-header">
                    <div class="item-info">
                      <span class="item-name">{{ risk.name }}</span>
                      <select
                        v-model="risk.version"
                        class="version-select"
                        :disabled="getComponentVersions(risk.name, 'risk').length <= 1"
                        @change="onRiskVersionChange(index)"
                      >
                        <option v-for="v in getComponentVersions(risk.name, 'risk')" :key="v.uuid" :value="v.version">
                          {{ v.version }}{{ v.is_latest ? ' (最新)' : '' }}
                        </option>
                      </select>
                    </div>
                    <button class="btn-icon text-red" @click="removeRisk(index)">
                      <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                      </svg>
                    </button>
                  </div>
                  <div v-if="risk.parameters && risk.parameters.length > 0" class="item-params">
                    <div v-for="param in risk.parameters" :key="param.name" class="param-row">
                      <label class="param-label">{{ param.label || param.name }}</label>
                      <input
                        v-if="param.type === 'number'"
                        :value="formatNumber(risk.config[param.name] ?? 0)"
                        type="text"
                        inputmode="decimal"
                        class="param-input"
                        @focus="e => setInputValue(e, risk.config[param.name] ?? '')"
                        @blur="e => { risk.config[param.name] = parseNumber(getInputValue(e)); setInputValue(e, formatNumber(risk.config[param.name])) }"
                      />
                      <div v-else-if="param.type === 'boolean'" class="switch-container">
                        <input :id="`risk-${risk.uuid}-${param.name}`" v-model="risk.config[param.name]" type="checkbox" class="switch-input" />
                        <label :for="`risk-${risk.uuid}-${param.name}`" class="switch-label"></label>
                      </div>
                      <select v-else-if="param.type === 'select'" v-model="risk.config[param.name]" class="param-select">
                        <option v-for="opt in param.options" :key="opt" :value="opt">{{ opt }}</option>
                      </select>
                      <input v-else v-model="risk.config[param.name]" type="text" class="param-input" />
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 分析器配置 -->
            <div v-if="formData.analyzers.length > 0" class="config-section">
              <div class="section-header">
                <span class="section-title">分析器 ({{ formData.analyzers.length }})</span>
              </div>
              <div class="config-list">
                <div v-for="(analyzer, index) in formData.analyzers" :key="analyzer.uuid" class="config-item">
                  <div class="item-header">
                    <div class="item-info">
                      <span class="item-name">{{ analyzer.name }}</span>
                      <select
                        v-model="analyzer.version"
                        class="version-select"
                        :disabled="getComponentVersions(analyzer.name, 'analyzer').length <= 1"
                        @change="onAnalyzerVersionChange(index)"
                      >
                        <option v-for="v in getComponentVersions(analyzer.name, 'analyzer')" :key="v.uuid" :value="v.version">
                          {{ v.version }}{{ v.is_latest ? ' (最新)' : '' }}
                        </option>
                      </select>
                    </div>
                    <button class="btn-icon text-red" @click="removeAnalyzer(index)">
                      <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="18" y1="6" x2="6" y2="18"></line>
                        <line x1="6" y1="6" x2="18" y2="18"></line>
                      </svg>
                    </button>
                  </div>
                  <div v-if="analyzer.parameters && analyzer.parameters.length > 0" class="item-params">
                    <div v-for="param in analyzer.parameters" :key="param.name" class="param-row">
                      <label class="param-label">{{ param.label || param.name }}</label>
                      <input
                        v-if="param.type === 'number'"
                        :value="formatNumber(analyzer.config[param.name] ?? 0)"
                        type="text"
                        inputmode="decimal"
                        class="param-input"
                        @focus="e => setInputValue(e, analyzer.config[param.name] ?? '')"
                        @blur="e => { analyzer.config[param.name] = parseNumber(getInputValue(e)); setInputValue(e, formatNumber(analyzer.config[param.name])) }"
                      />
                      <div v-else-if="param.type === 'boolean'" class="switch-container">
                        <input :id="`ana-${analyzer.uuid}-${param.name}`" v-model="analyzer.config[param.name]" type="checkbox" class="switch-input" />
                        <label :for="`ana-${analyzer.uuid}-${param.name}`" class="switch-label"></label>
                      </div>
                      <select v-else-if="param.type === 'select'" v-model="analyzer.config[param.name]" class="param-select">
                        <option v-for="opt in param.options" :key="opt" :value="opt">{{ opt }}</option>
                      </select>
                      <input v-else v-model="analyzer.config[param.name]" type="text" class="param-input" />
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- 空状态 -->
            <div v-if="isConfigEmpty" class="empty-state">
              <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                <line x1="9" y1="3" x2="9" y2="21"></line>
              </svg>
              <p>暂未配置组件</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { portfolioApi } from '@/api/modules/portfolio'
import { componentsApi } from '@/api/modules/components'
import SearchSelect from '@/components/common/SearchSelect.vue'
import type { SearchOption } from '@/components/common/SearchSelect.vue'
import { message } from '@/utils/toast'

// Props
const props = defineProps<{
  isModalMode?: boolean
}>()

// Emits
const emit = defineEmits<{
  (e: 'created', uuid: string): void
  (e: 'cancel'): void
}>()

const router = useRouter()
const route = useRoute()

// 加载状态
const saving = ref(false)

// 是否编辑模式
const isEditMode = computed(() => !!route.params.uuid)

// 表单数据
const formData = ref({
  name: '',
  initial_cash: 1000000,
  mode: 'BACKTEST',
  benchmark: '',
  description: '',
  selectors: [] as Array<{ uuid: string; name: string; version: string; parameters?: any[]; config: Record<string, any> }>,
  sizer: null as { uuid: string; name: string; version: string; parameters?: any[]; config: Record<string, any> } | null,
  strategies: [] as Array<{ uuid: string; name: string; version: string; weight: number; parameters?: any[]; config: Record<string, any> }>,
  risk_managers: [] as Array<{ uuid: string; name: string; version: string; parameters?: any[]; config: Record<string, any> }>,
  analyzers: [] as Array<{ uuid: string; name: string; version: string; parameters?: any[]; config: Record<string, any> }>
})

// 可用组件列表
const availableStrategies = ref<any[]>([])
const availableSelectors = ref<any[]>([])
const availableSizers = ref<any[]>([])
const availableRisks = ref<any[]>([])
const availableAnalyzers = ref<any[]>([])

// 组件版本缓存
const componentVersionsCache = ref<Record<string, any[]>>({})

// 临时选择（不再需要，SearchSelect 自行管理）
const selectedSelector = ref<string>('')
const selectedSizer = ref<string>('')
const selectedStrategy = ref<string>('')
const selectedRisk = ref<string>('')
const selectedAnalyzer = ref<string>('')

// 当前激活的组件类型
const activeComponentType = ref('selector')

// 组件类型定义
const componentTypes = [
  { key: 'selector', label: '选股器' },
  { key: 'sizer', label: '仓位管理' },
  { key: 'strategy', label: '策略' },
  { key: 'risk', label: '风控' },
  { key: 'analyzer', label: '分析器' }
]

// 判断配置是否为空
const isConfigEmpty = computed(() => {
  return formData.value.selectors.length === 0 &&
         !formData.value.sizer &&
         formData.value.strategies.length === 0 &&
         formData.value.risk_managers.length === 0 &&
         formData.value.analyzers.length === 0
})

// 格式化数字
const formatNumber = (value: number) => {
  return value.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',')
}

// 解析数字
const parseNumber = (value: string) => {
  return parseFloat(value.replace(/,/g, '')) || 0
}

// 判断组件是否已添加
const isSelectorAdded = (uuid: string) => formData.value.selectors.some(s => s.uuid === uuid)
const isStrategyAdded = (uuid: string) => formData.value.strategies.some(s => s.uuid === uuid)
const isRiskAdded = (uuid: string) => formData.value.risk_managers.some(r => r.uuid === uuid)
const isAnalyzerAdded = (uuid: string) => formData.value.analyzers.some(a => a.uuid === uuid)

// 获取组件的所有版本
const getComponentVersions = (name: string, type: string): any[] => {
  const cacheKey = `${name}_${type}`
  return componentVersionsCache.value[cacheKey] || []
}

// 加载组件参数定义（从详情 API 获取，含 AST 解析的参数）
const loadComponentParameters = async (uuid: string) => {
  try {
    const res = await componentsApi.get(uuid) as any
    const data = res.data || res
    return data.parameters || []
  } catch {
    return []
  }
}

// 根据参数定义构建默认配置
const buildDefaultConfig = (parameters: any[]) => {
  const config: Record<string, any> = {}
  for (const param of parameters) {
    if (param.default !== undefined) {
      config[param.name] = param.default
    }
  }
  return config
}

// 模拟加载组件版本
const loadComponentVersions = async (name: string, type: string) => {
  const cacheKey = `${name}_${type}`
  if (!componentVersionsCache.value[cacheKey]) {
    componentVersionsCache.value[cacheKey] = []
  }
  return componentVersionsCache.value[cacheKey]
}

// 切换组件版本
const changeComponentVersion = async (componentType: string, index: number, versionValue: string) => {
  try {
    let componentName = ''
    let oldConfig: Record<string, any> = {}
    let componentTypeKey = ''

    if (componentType === 'selector') {
      componentName = formData.value.selectors[index].name
      oldConfig = formData.value.selectors[index].config || {}
      componentTypeKey = 'selector'
    } else if (componentType === 'sizer') {
      componentName = formData.value.sizer!.name
      oldConfig = formData.value.sizer!.config || {}
      componentTypeKey = 'sizer'
    } else if (componentType === 'strategy') {
      componentName = formData.value.strategies[index].name
      oldConfig = formData.value.strategies[index].config || {}
      componentTypeKey = 'strategy'
    } else if (componentType === 'risk') {
      componentName = formData.value.risk_managers[index].name
      oldConfig = formData.value.risk_managers[index].config || {}
      componentTypeKey = 'risk'
    } else if (componentType === 'analyzer') {
      componentName = formData.value.analyzers[index].name
      oldConfig = formData.value.analyzers[index].config || {}
      componentTypeKey = 'analyzer'
    }

    const versions = getComponentVersions(componentName, componentTypeKey)
    const targetVersion = versions.find((v: any) => v.version === versionValue)
    if (!targetVersion) return

    const newUuid = targetVersion.uuid
    const parameters = await loadComponentParameters(newUuid)
    const newConfig = buildDefaultConfig(parameters)

    // 合并配置
    const mergedConfig: Record<string, any> = {}
    for (const param of parameters) {
      const paramName = param.name
      if (paramName in oldConfig) {
        mergedConfig[paramName] = oldConfig[paramName]
      } else {
        mergedConfig[paramName] = newConfig[paramName]
      }
    }

    // 更新组件信息
    if (componentType === 'selector') {
      formData.value.selectors[index].uuid = newUuid
      formData.value.selectors[index].version = versionValue
      formData.value.selectors[index].parameters = parameters
      formData.value.selectors[index].config = mergedConfig
    } else if (componentType === 'sizer') {
      if (formData.value.sizer) {
        formData.value.sizer.uuid = newUuid
        formData.value.sizer.version = versionValue
        formData.value.sizer.parameters = parameters
        formData.value.sizer.config = mergedConfig
      }
    } else if (componentType === 'strategy') {
      formData.value.strategies[index].uuid = newUuid
      formData.value.strategies[index].version = versionValue
      formData.value.strategies[index].parameters = parameters
      formData.value.strategies[index].config = mergedConfig
    } else if (componentType === 'risk') {
      formData.value.risk_managers[index].uuid = newUuid
      formData.value.risk_managers[index].version = versionValue
      formData.value.risk_managers[index].parameters = parameters
      formData.value.risk_managers[index].config = mergedConfig
    } else if (componentType === 'analyzer') {
      formData.value.analyzers[index].uuid = newUuid
      formData.value.analyzers[index].version = versionValue
      formData.value.analyzers[index].parameters = parameters
      formData.value.analyzers[index].config = mergedConfig
    }
  } catch (error) {
    message.error('切换版本失败')
  }
}

// 添加选股器
const addSelector = async (uuid: string) => {
  const selector = availableSelectors.value.find(s => s.uuid === uuid)
  if (selector && !isSelectorAdded(uuid)) {
    await loadComponentVersions(selector.name, 'selector')
    const parameters = await loadComponentParameters(uuid)
    const config = buildDefaultConfig(parameters)
    formData.value.selectors.push({
      uuid: selector.uuid,
      name: selector.name,
      version: selector.version || 'UNKNOWN_VERSION',
      parameters,
      config
    })
    selectedSelector.value = ''
  }
}

// 移除选股器
const removeSelector = (index: number) => {
  formData.value.selectors.splice(index, 1)
}

// 添加仓位管理器
const addSizer = async (uuid: string) => {
  const sizer = availableSizers.value.find(s => s.uuid === uuid)
  if (sizer) {
    await loadComponentVersions(sizer.name, 'sizer')
    const parameters = await loadComponentParameters(uuid)
    const config = buildDefaultConfig(parameters)
    formData.value.sizer = {
      uuid: sizer.uuid,
      name: sizer.name,
      version: sizer.version || 'UNKNOWN_VERSION',
      parameters,
      config
    }
    selectedSizer.value = ''
  }
}

// 移除仓位管理器
const removeSizer = () => {
  formData.value.sizer = null
}

// 添加策略
const addStrategy = async (uuid: string) => {
  const strategy = availableStrategies.value.find(s => s.uuid === uuid)
  if (strategy && !isStrategyAdded(uuid)) {
    await loadComponentVersions(strategy.name, 'strategy')
    const parameters = await loadComponentParameters(uuid)
    const config = buildDefaultConfig(parameters)
    formData.value.strategies.push({
      uuid: strategy.uuid,
      name: strategy.name,
      version: strategy.version || 'UNKNOWN_VERSION',
      weight: 100,
      parameters,
      config
    })
    selectedStrategy.value = ''
  }
}

// 移除策略
const removeStrategy = (index: number) => {
  formData.value.strategies.splice(index, 1)
}

// 添加风控
const addRisk = async (uuid: string) => {
  const risk = availableRisks.value.find(r => r.uuid === uuid)
  if (risk && !isRiskAdded(uuid)) {
    await loadComponentVersions(risk.name, 'risk')
    const parameters = await loadComponentParameters(uuid)
    const config = buildDefaultConfig(parameters)
    formData.value.risk_managers.push({
      uuid: risk.uuid,
      name: risk.name,
      version: risk.version || 'UNKNOWN_VERSION',
      parameters,
      config
    })
    selectedRisk.value = ''
  }
}

// 移除风控
const removeRisk = (index: number) => {
  formData.value.risk_managers.splice(index, 1)
}

// 添加分析器
const addAnalyzer = async (uuid: string) => {
  const analyzer = availableAnalyzers.value.find(a => a.uuid === uuid)
  if (analyzer && !isAnalyzerAdded(uuid)) {
    await loadComponentVersions(analyzer.name, 'analyzer')
    const parameters = await loadComponentParameters(uuid)
    const config = buildDefaultConfig(parameters)
    formData.value.analyzers.push({
      uuid: analyzer.uuid,
      name: analyzer.name,
      version: analyzer.version || 'UNKNOWN_VERSION',
      parameters,
      config
    })
    selectedAnalyzer.value = ''
  }
}

// 移除分析器
const removeAnalyzer = (index: number) => {
  formData.value.analyzers.splice(index, 1)
}

// 搜索组件（供 SearchSelect 使用，同时更新 available 列表）
const searchComponents = async (type: string, query: string): Promise<SearchOption[]> => {
  try {
    const res = await componentsApi.list(type, { keyword: query || undefined, page: 1, page_size: 20 })
    const items = (res as any).data || res || []
    // 同步到 available 列表供 add 函数查找
    const mapped = items.map((c: any) => ({ ...c, uuid: c.uuid, name: c.name }))
    if (type === 'strategy') availableStrategies.value = mapped
    else if (type === 'selector') availableSelectors.value = mapped
    else if (type === 'sizer') availableSizers.value = mapped
    else if (type === 'risk') availableRisks.value = mapped
    else if (type === 'analyzer') availableAnalyzers.value = mapped
    return items.map((c: any) => ({ value: c.uuid, label: c.name, data: c }))
  } catch {
    return []
  }
}

// 加载组件列表
const loadComponents = async () => {
  try {
    const types = ['strategy', 'selector', 'sizer', 'risk', 'analyzer']
    const results = await Promise.all(
      types.map(t => componentsApi.list(t, { page: 1, page_size: 100 }).catch(() => ({ data: [] })))
    )
    availableStrategies.value = results[0].data || []
    availableSelectors.value = results[1].data || []
    availableSizers.value = results[2].data || []
    availableRisks.value = results[3].data || []
    availableAnalyzers.value = results[4].data || []
  } catch (e) {
    console.error('加载组件失败:', e)
  }
}

// 保存投资组合
const savePortfolio = async () => {
  if (!formData.value.name) {
    message.warning('请输入组合名称')
    return
  }
  if (formData.value.strategies.length === 0) {
    message.warning('请至少添加一个策略')
    return
  }

  saving.value = true
  try {
    const payload: any = {
      name: formData.value.name,
      mode: formData.value.mode,
      initial_cash: formData.value.initial_cash,
      benchmark: formData.value.benchmark || undefined,
      description: formData.value.description || undefined,
      strategies: formData.value.strategies.map(s => ({
        component_uuid: s.uuid,
        weight: s.weight || 100,
        config: s.config || {},
      })),
    }
    if (formData.value.selectors.length > 0) {
      payload.selectors = formData.value.selectors.map(s => ({
        component_uuid: s.uuid,
        config: s.config || {},
      }))
    }
    if (formData.value.sizer) {
      payload.sizer_uuid = formData.value.sizer.uuid
      payload.sizer_config = formData.value.sizer.config || {}
    }
    if (formData.value.risk_managers.length > 0) {
      payload.risk_managers = formData.value.risk_managers.map(r => ({
        component_uuid: r.uuid,
        config: r.config || {},
      }))
    }
    if (formData.value.analyzers.length > 0) {
      payload.analyzers = formData.value.analyzers.map(a => ({
        component_uuid: a.uuid,
        config: a.config || {},
      }))
    }

    const result = await portfolioApi.create(payload)
    message.success(isEditMode.value ? '投资组合更新成功' : '投资组合创建成功')
    const createdUuid = result.uuid || (result as any).data?.uuid
    if (!isEditMode.value) {
      if (props.isModalMode) {
        emit('created', createdUuid)
      } else if (createdUuid) {
        router.push(`/portfolios/${createdUuid}`)
      }
    }
  } catch (e: any) {
    message.error(`保存失败: ${e.message || e}`)
  } finally {
    saving.value = false
  }
}

const goBack = () => {
  if (props.isModalMode) {
    emit('cancel')
  } else {
    router.back()
  }
}

// 事件处理包装函数（用于处理模板中的类型断言问题）
const onInitialCashInput = (event: Event) => {
  const target = event.target as HTMLInputElement
  formData.value.initial_cash = parseNumber(target.value)
}

const getInputValue = (e: Event): string => (e.target as HTMLInputElement | null)?.value ?? ''

const setInputValue = (e: Event, value: string): void => {
  const target = e.target as HTMLInputElement | null
  if (target) target.value = value
}

const onSelectorVersionChange = (index: number) => (event: Event) => {
  const target = event.target as HTMLSelectElement
  changeComponentVersion('selector', index, target.value)
}

const onSizerVersionChange = (event: Event) => {
  const target = event.target as HTMLSelectElement
  changeComponentVersion('sizer', 0, target.value)
}

const onStrategyVersionChange = (index: number) => (event: Event) => {
  const target = event.target as HTMLSelectElement
  changeComponentVersion('strategy', index, target.value)
}

const onRiskVersionChange = (index: number) => (event: Event) => {
  const target = event.target as HTMLSelectElement
  changeComponentVersion('risk', index, target.value)
}

const onAnalyzerVersionChange = (index: number) => (event: Event) => {
  const target = event.target as HTMLSelectElement
  changeComponentVersion('analyzer', index, target.value)
}

onMounted(() => {
  loadComponents()
})
</script>

<style scoped>
.portfolio-form-editor {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #0f0f1a;
}

.portfolio-form-editor.modal-mode .form-layout {
  padding: 0;
}

.portfolio-form-editor.modal-mode .page-header {
  padding: 12px 16px;
  border-bottom: 1px solid #2a2a3e;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  background: #1a1a2e;
  border-bottom: 1px solid #2a2a3e;
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.title-section h1 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
}

.title-section p {
  margin: 0;
  font-size: 12px;
  color: #8a8a9a;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.btn-primary:hover:not(:disabled) {
  background: #40a9ff;
}

.form-layout {
  display: flex;
  gap: 16px;
  padding: 16px;
  flex: 1;
  overflow: hidden;
}

.left-panel {
  flex: 0 0 420px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow-y: auto;
  overflow-x: visible;
  min-height: 0;
}

.right-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 0;
}

.form-card {
  flex-shrink: 0;
}

.card-header-sm {
  padding: 12px 16px;
  border-bottom: 1px solid #2a2a3e;
}

.card-header-sm h4 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #ffffff;
}

.card-body-sm {
  padding: 16px;
}

.config-card {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.config-content {
  overflow-y: auto;
  flex: 1;
  min-height: 0;
}

.required {
  color: #f5222d;
}

.input-group {
  display: flex;
  align-items: center;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
}

.input-group .form-input {
  flex: 1;
  border: none;
  background: transparent;
  padding: 8px 12px 8px 0;
}

.input-group .form-input:focus {
  border-color: transparent;
}

/* 组件类型按钮组 */
.component-type-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #2a2a3e;
}

.type-btn {
  flex: 1;
  min-width: 0;
  padding: 6px 8px;
  font-size: 12px;
  border: 1px solid #3a3a4e;
  background: transparent;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
  text-align: center;
  line-height: 1.2;
  color: #ffffff;
}

.type-btn:hover {
  border-color: #1890ff;
  color: #1890ff;
}

.type-btn.active {
  background: #1890ff;
  border-color: #1890ff;
  color: #fff;
}

.component-selector {
  margin-top: 8px;
}

/* 配置区域 */
.config-section {
  margin-bottom: 12px;
}

.config-section:last-child {
  margin-bottom: 0;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 8px;
  background: #2a2a3e;
  border-radius: 4px;
  margin-bottom: 8px;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: #ffffff;
}

.config-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.config-item {
  border: 1px solid #2a2a3e;
  border-radius: 6px;
  overflow: hidden;
}

.item-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: #1a1a2e;
}

.item-info {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.item-name {
  font-size: 13px;
  font-weight: 500;
  color: #ffffff;
}

.version-select {
  padding: 4px 8px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 12px;
  cursor: pointer;
}

.item-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.weight-input {
  width: 60px;
  padding: 4px 8px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 13px;
  text-align: center;
}

.item-actions .unit {
  font-size: 12px;
  color: #8a8a9a;
}

.item-params {
  padding: 8px 12px;
  background: #2a2a3e;
  border-top: 1px solid #3a3a4e;
}

.param-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.param-row:last-child {
  margin-bottom: 0;
}

.param-label {
  font-size: 12px;
  color: #8a8a9a;
  min-width: 80px;
}

.param-input,
.param-select {
  flex: 1;
  padding: 4px 8px;
  background: #1a1a2e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 13px;
}

.param-input:focus,
.param-select:focus {
  outline: none;
  border-color: #1890ff;
}

/* Switch */
.switch-container {
  display: flex;
  align-items: center;
  gap: 8px;
}

.switch-input {
  display: none;
}

.switch-label {
  position: relative;
  width: 36px;
  height: 18px;
  background: #3a3a4e;
  border-radius: 9px;
  cursor: pointer;
  transition: background 0.2s;
}

.switch-label::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 14px;
  height: 14px;
  background: #ffffff;
  border-radius: 50%;
  transition: transform 0.2s;
}

.switch-input:checked + .switch-label {
  background: #1890ff;
}

.switch-input:checked + .switch-label::after {
  transform: translateX(18px);
}

/* 空状态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: #8a8a9a;
}

.empty-state svg {
  margin-bottom: 16px;
  opacity: 0.3;
}

.empty-state p {
  margin: 0;
  font-size: 14px;
}
</style>
