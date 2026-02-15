<template>
  <div class="portfolio-form-editor">
    <div class="page-header">
      <div class="header-left">
        <a-button @click="goBack" type="text">
          <LeftOutlined />
          返回
        </a-button>
        <div class="title-section">
          <h1 class="page-title">{{ isEditMode ? '编辑投资组合' : '创建投资组合' }}</h1>
          <p class="page-subtitle">配置交易策略、选股器、仓位管理和风控规则</p>
        </div>
      </div>
      <div class="header-actions">
        <a-button @click="goBack">取消</a-button>
        <a-button type="primary" :loading="saving" @click="savePortfolio">
          {{ isEditMode ? '保存' : '创建' }}
        </a-button>
      </div>
    </div>

    <div class="form-layout">
      <!--  +  -->
      <div class="left-panel">
        <a-form ref="formRef" :model="formData" :rules="formRules" layout="vertical">
          <!-- Custom -->
          <a-card title="基本信息" size="small" class="form-card">
            <a-row :gutter="16">
              <a-col :span="12">
                <a-form-item label="名称" name="name">
                  <a-input v-model:value="formData.name" placeholder="组合名称" allow-clear />
                </a-form-item>
              </a-col>
              <a-col :span="12">
                <a-form-item label="初始资金" name="initial_cash">
                  <a-input-number
                    v-model:value="formData.initial_cash"
                    :min="0"
                    :precision="2"
                    :step="10000"
                    :formatter="value => `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ',')"
                    :parser="value => value ? value.replace(/,/g, '') : ''"
                    style="width: 100%"
                  >
                    <template #prefix>¥</template>
                  </a-input-number>
                </a-form-item>
              </a-col>
            </a-row>
            <a-row :gutter="16">
              <a-col :span="12">
                <a-form-item label="运行模式" name="mode">
                  <a-select v-model:value="formData.mode">
                    <a-select-option value="BACKTEST">回测</a-select-option>
                    <a-select-option value="PAPER">模拟盘</a-select-option>
                    <a-select-option value="LIVE">实盘</a-select-option>
                  </a-select>
                </a-form-item>
              </a-col>
              <a-col :span="12">
                <a-form-item label="基准" name="benchmark">
                  <a-input v-model:value="formData.benchmark" placeholder="000001.SZ（可选）" allow-clear />
                </a-form-item>
              </a-col>
            </a-row>
            <a-form-item label="描述" name="description">
              <a-textarea v-model:value="formData.description" :rows="2" placeholder="组合描述" allow-clear />
            </a-form-item>
          </a-card>

          <!-- Custom -->
          <a-card size="small" class="form-card">
            <template #title>
              <span>添加组件</span>
            </template>

            <!-- Custom -->
            <div class="component-type-tabs">
              <button
                v-for="type in componentTypes"
                :key="type.key"
                :class="['type-btn', { active: activeComponentType === type.key }]"
                @click="activeComponentType = type.key"
              >
                {{ type.label }}
              </button>
            </div>

            <!-- Custom -->
            <div class="component-selector">
              <a-select
                v-if="activeComponentType === 'selector'"
                v-model:value="selectedSelector"
                placeholder="选择选股器"
                show-search
                :filter-option="filterComponent"
                @change="addSelector"
                style="width: 100%"
              >
                <a-select-option
                  v-for="selector in availableSelectors.filter(s => !isSelectorAdded(s.uuid))"
                  :key="selector.uuid"
                  :value="selector.uuid"
                >
                  <div class="component-option">
                    <span class="component-name">{{ selector.name }}</span>
                    <a-tag size="small" color="lime">SEL</a-tag>
                  </div>
                </a-select-option>
              </a-select>

              <a-select
                v-else-if="activeComponentType === 'sizer'"
                v-model:value="selectedSizer"
                placeholder="选择仓位管理器"
                show-search
                :filter-option="filterComponent"
                @change="addSizer"
                style="width: 100%"
              >
                <a-select-option
                  v-for="sizer in availableSizers.filter(s => !formData.sizer || s.uuid !== formData.sizer.uuid)"
                  :key="sizer.uuid"
                  :value="sizer.uuid"
                >
                  <div class="component-option">
                    <span class="component-name">{{ sizer.name }}</span>
                    <a-tag size="small" color="gold">SIZ</a-tag>
                  </div>
                </a-select-option>
              </a-select>

              <a-select
                v-else-if="activeComponentType === 'strategy'"
                v-model:value="selectedStrategy"
                placeholder="选择策略"
                show-search
                :filter-option="filterComponent"
                @change="addStrategy"
                style="width: 100%"
              >
                <a-select-option
                  v-for="strategy in availableStrategies.filter(s => !isStrategyAdded(s.uuid))"
                  :key="strategy.uuid"
                  :value="strategy.uuid"
                >
                  <div class="component-option">
                    <span class="component-name">{{ strategy.name }}</span>
                    <a-tag size="small" color="cyan">STRAT</a-tag>
                  </div>
                </a-select-option>
              </a-select>

              <a-select
                v-else-if="activeComponentType === 'risk'"
                v-model:value="selectedRisk"
                placeholder="选择风控规则"
                show-search
                :filter-option="filterComponent"
                @change="addRisk"
                style="width: 100%"
              >
                <a-select-option
                  v-for="risk in availableRisks.filter(r => !isRiskAdded(r.uuid))"
                    :key="risk.uuid"
                    :value="risk.uuid"
                >
                  <div class="component-option">
                    <span class="component-name">{{ risk.name }}</span>
                    <a-tag size="small" color="red">RISK</a-tag>
                  </div>
                </a-select-option>
              </a-select>

              <a-select
                v-else-if="activeComponentType === 'analyzer'"
                v-model:value="selectedAnalyzer"
                placeholder="选择分析器（可选）"
                show-search
                :filter-option="filterComponent"
                @change="addAnalyzer"
                style="width: 100%"
              >
                <a-select-option
                  v-for="analyzer in availableAnalyzers.filter(a => !isAnalyzerAdded(a.uuid))"
                    :key="analyzer.uuid"
                    :value="analyzer.uuid"
                >
                  <div class="component-option">
                    <span class="component-name">{{ analyzer.name }}</span>
                    <a-tag size="small" color="purple">ANA</a-tag>
                  </div>
                </a-select-option>
              </a-select>
            </div>
          </a-card>
        </a-form>
      </div>

      <!-- Custom -->
      <div class="right-panel">
        <a-card title="组件配置" size="small" class="config-card">
          <!-- Custom -->
          <div v-if="formData.selectors.length > 0" class="config-section">
            <div class="section-header">
              <span class="section-title">选股器 ({{ formData.selectors.length }})</span>
            </div>
            <div class="config-list">
              <div
                v-for="(selector, index) in formData.selectors"
                :key="selector.uuid"
                class="config-item"
              >
                <div class="item-header">
                  <span class="item-name">{{ selector.name }}</span>
                  <a-button type="text" danger size="small" @click="removeSelector(index)">
                    <CloseOutlined />
                  </a-button>
                </div>
                <div v-if="selector.parameters && selector.parameters.length > 0" class="item-params">
                  <div
                    v-for="param in selector.parameters"
                    :key="param.name"
                    class="param-row"
                  >
                    <label class="param-label">{{ param.label || param.name }}</label>
                    <a-input-number
                      v-if="param.type === 'number'"
                      v-model:value="selector.config[param.name]"
                      :min="param.min"
                      :max="param.max"
                      :step="param.step || 1"
                      :precision="param.precision || 2"
                      size="small"
                    />
                    <a-input
                      v-else
                      v-model:value="selector.config[param.name]"
                      size="small"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Custom -->
          <div v-if="formData.sizer" class="config-section">
            <div class="section-header">
              <span class="section-title">仓位管理器</span>
              <a-button type="text" danger size="small" @click="removeSizer">
                <CloseOutlined />
              </a-button>
            </div>
            <div class="config-list">
              <div class="config-item">
                <div class="item-header">
                  <span class="item-name">{{ formData.sizer.name }}</span>
                </div>
                <div v-if="formData.sizer.parameters && formData.sizer.parameters.length > 0" class="item-params">
                  <div
                    v-for="param in formData.sizer.parameters"
                    :key="param.name"
                    class="param-row"
                  >
                    <label class="param-label">{{ param.label || param.name }}</label>
                    <a-input-number
                      v-if="param.type === 'number'"
                      v-model:value="formData.sizer.config[param.name]"
                      :min="param.min"
                      :max="param.max"
                      :step="param.step || 1"
                      :precision="param.precision || 2"
                      size="small"
                    />
                    <a-input
                      v-else
                      v-model:value="formData.sizer.config[param.name]"
                      size="small"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Custom -->
          <div v-if="formData.strategies.length > 0" class="config-section">
            <div class="section-header">
              <span class="section-title">策略 ({{ formData.strategies.length }})</span>
            </div>
            <div class="config-list">
              <div
                v-for="(strategy, index) in formData.strategies"
                :key="strategy.uuid"
                class="config-item"
              >
                <div class="item-header">
                  <span class="item-name">{{ strategy.name }}</span>
                  <div class="item-actions">
                    <a-input-number
                      v-model:value="strategy.weight"
                      :min="0"
                      :max="100"
                      :precision="2"
                      size="small"
                      style="width: 70px"
                    />
                    <span class="unit">%</span>
                    <a-button type="text" danger size="small" @click="removeStrategy(index)">
                      <CloseOutlined />
                    </a-button>
                  </div>
                </div>
                <div v-if="strategy.parameters && strategy.parameters.length > 0" class="item-params">
                  <div
                    v-for="param in strategy.parameters"
                    :key="param.name"
                    class="param-row"
                  >
                    <label class="param-label">{{ param.label || param.name }}</label>
                    <a-input-number
                      v-if="param.type === 'number'"
                      v-model:value="strategy.config[param.name]"
                      :min="param.min"
                      :max="param.max"
                      :step="param.step || 1"
                      :precision="param.precision || 2"
                      size="small"
                    />
                    <a-input
                      v-else
                      v-model:value="strategy.config[param.name]"
                      size="small"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Custom -->
          <div v-if="formData.risk_managers.length > 0" class="config-section">
            <div class="section-header">
              <span class="section-title">风控 ({{ formData.risk_managers.length }})</span>
            </div>
            <div class="config-list">
              <div
                v-for="(risk, index) in formData.risk_managers"
                :key="risk.uuid"
                class="config-item"
              >
                <div class="item-header">
                  <span class="item-name">{{ risk.name }}</span>
                  <a-button type="text" danger size="small" @click="removeRisk(index)">
                    <CloseOutlined />
                  </a-button>
                </div>
                <div v-if="risk.parameters && risk.parameters.length > 0" class="item-params">
                  <div
                    v-for="param in risk.parameters"
                    :key="param.name"
                    class="param-row"
                  >
                    <label class="param-label">{{ param.label || param.name }}</label>
                    <a-input-number
                      v-if="param.type === 'number'"
                      v-model:value="risk.config[param.name]"
                      :min="param.min"
                      :max="param.max"
                      :step="param.step || 1"
                      :precision="param.precision || 2"
                      size="small"
                    />
                    <a-input
                      v-else
                      v-model:value="risk.config[param.name]"
                      size="small"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Custom -->
          <div v-if="formData.analyzers.length > 0" class="config-section">
            <div class="section-header">
              <span class="section-title">分析器 ({{ formData.analyzers.length }})</span>
            </div>
            <div class="config-list">
              <div
                v-for="(analyzer, index) in formData.analyzers"
                :key="analyzer.uuid"
                class="config-item"
              >
                <div class="item-header">
                  <span class="item-name">{{ analyzer.name }}</span>
                  <a-button type="text" danger size="small" @click="removeAnalyzer(index)">
                    <CloseOutlined />
                  </a-button>
                </div>
                <div v-if="analyzer.parameters && analyzer.parameters.length > 0" class="item-params">
                  <div
                    v-for="param in analyzer.parameters"
                    :key="param.name"
                    class="param-row"
                  >
                    <label class="param-label">{{ param.label || param.name }}</label>
                    <a-input-number
                      v-if="param.type === 'number'"
                      v-model:value="analyzer.config[param.name]"
                      :min="param.min"
                      :max="param.max"
                      :step="param.step || 1"
                      :precision="param.precision || 2"
                      size="small"
                    />
                    <a-input
                      v-else
                      v-model:value="analyzer.config[param.name]"
                      size="small"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Custom -->
          <a-empty v-if="isConfigEmpty" description="暂未配置组件" :image="false" />
        </a-card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { LeftOutlined, CloseOutlined } from '@ant-design/icons-vue'
import type { ComponentSummary } from '@/api/modules/components'
import { componentsApi } from '@/api/modules/components'
import { portfolioApi } from '@/api/modules/portfolio'
import { useFormErrorHandler } from '@/composables/useErrorHandler'

const router = useRouter()
const route = useRoute()
const formRef = ref()

// 使用统一错误处理
const { loading: saving, submit, reset } = useFormErrorHandler()

// 是否编辑模式
const isEditMode = computed(() => !!route.params.uuid)
const portfolioUuid = computed(() => route.params.uuid as string | undefined)

// 表单数据
const formData = ref({
  name: '',
  initial_cash: 1000000,
  mode: 'BACKTEST',
  benchmark: '',
  description: '',
  selectors: [] as Array<{ uuid: string; name: string; parameters?: any[]; config: Record<string, any> }>,
  sizer_uuid: undefined as string | undefined,
  sizer: null as { uuid: string; name: string; parameters?: any[]; config: Record<string, any> } | null,
  strategies: [] as Array<{ uuid: string; name: string; weight: number; parameters?: any[]; config: Record<string, any> }>,
  risk_managers: [] as Array<{ uuid: string; name: string; parameters?: any[]; config: Record<string, any> }>,
  analyzers: [] as Array<{ uuid: string; name: string; parameters?: any[]; config: Record<string, any> }>
})

// 表单验证规则
const formRules = {
  name: [{ required: true, message: '请输入组合名称', trigger: 'blur' }],
  initial_cash: [{ required: true, message: '请输入初始资金', trigger: 'blur' }],
  mode: [{ required: true, message: '请选择运行模式', trigger: 'change' }]
}

// 可用组件列表
const availableStrategies = ref<ComponentSummary[]>([])
const availableSelectors = ref<ComponentSummary[]>([])
const availableSizers = ref<ComponentSummary[]>([])
const availableRisks = ref<ComponentSummary[]>([])
const availableAnalyzers = ref<ComponentSummary[]>([])

// 临时选择
const selectedSelector = ref<string>()
const selectedSizer = ref<string>()
const selectedStrategy = ref<string>()
const selectedRisk = ref<string>()
const selectedAnalyzer = ref<string>()

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

// 组件过滤
const filterComponent = (input: string, option: any) => {
  const component = availableStrategies.value.find(c => c.uuid === option.value) ||
                    availableSelectors.value.find(c => c.uuid === option.value) ||
                    availableSizers.value.find(c => c.uuid === option.value) ||
                    availableRisks.value.find(c => c.uuid === option.value) ||
                    availableAnalyzers.value.find(c => c.uuid === option.value)
  if (!component) return false
  return component.name.toLowerCase().includes(input.toLowerCase())
}

// 判断组件是否已添加
const isSelectorAdded = (uuid: string) => formData.value.selectors.some(s => s.uuid === uuid)
const isStrategyAdded = (uuid: string) => formData.value.strategies.some(s => s.uuid === uuid)
const isRiskAdded = (uuid: string) => formData.value.risk_managers.some(r => r.uuid === uuid)
const isAnalyzerAdded = (uuid: string) => formData.value.analyzers.some(a => a.uuid === uuid)

// 获取Sizer名称
const getSizerName = () => {
  return formData.value.sizer?.name || ''
}

// 添加选股器
const addSelector = async (uuid: string) => {
  const selector = availableSelectors.value.find(s => s.uuid === uuid)
  if (selector && !isSelectorAdded(uuid)) {
    const parameters = await loadComponentParameters(uuid)
    const config = buildDefaultConfig(parameters)
    formData.value.selectors.push({ uuid: selector.uuid, name: selector.name, parameters, config })
    selectedSelector.value = undefined
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
    const parameters = await loadComponentParameters(uuid)
    const config = buildDefaultConfig(parameters)
    formData.value.sizer = {
      uuid: sizer.uuid,
      name: sizer.name,
      parameters,
      config
    }
    selectedSizer.value = undefined
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
    const parameters = await loadComponentParameters(uuid)
    const config = buildDefaultConfig(parameters)
    formData.value.strategies.push({
      uuid: strategy.uuid,
      name: strategy.name,
      weight: 100,
      parameters,
      config
    })
    selectedStrategy.value = undefined
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
    const parameters = await loadComponentParameters(uuid)
    const config = buildDefaultConfig(parameters)
    formData.value.risk_managers.push({ uuid: risk.uuid, name: risk.name, parameters, config })
    selectedRisk.value = undefined
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
    const parameters = await loadComponentParameters(uuid)
    const config = buildDefaultConfig(parameters)
    formData.value.analyzers.push({ uuid: analyzer.uuid, name: analyzer.name, parameters, config })
    selectedAnalyzer.value = undefined
  }
}

// 移除分析器
const removeAnalyzer = (index: number) => {
  formData.value.analyzers.splice(index, 1)
}

// 加载组件参数定义
const loadComponentParameters = async (uuid: string) => {
  try {
    const detail = await componentsApi.get(uuid)
    return detail.parameters || []
  } catch (error) {
    console.error('Failed to load component parameters:', error)
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

// 加载组件列表
const loadComponents = async () => {
  try {
    const allComponents = await componentsApi.list()
    availableStrategies.value = allComponents.filter((c: ComponentSummary) => c.component_type === 'strategy')
    availableSelectors.value = allComponents.filter((c: ComponentSummary) => c.component_type === 'selector')
    availableSizers.value = allComponents.filter((c: ComponentSummary) => c.component_type === 'sizer')
    availableRisks.value = allComponents.filter((c: ComponentSummary) => c.component_type === 'risk')
    availableAnalyzers.value = allComponents.filter((c: ComponentSummary) => c.component_type === 'analyzer')
  } catch (error: any) {
    // 错误已被统一处理，这里只需要记录日志
    console.error('加载组件列表失败:', error)
  }
}

// 加载投资组合数据（编辑模式）
const loadPortfolioData = async () => {
  if (!isEditMode.value) return
  try {
    const data = await portfolioApi.get(portfolioUuid.value!)

    // 加载仓位管理器参数
    let sizer = null
    if (data.sizer_uuid) {
      const parameters = await loadComponentParameters(data.sizer_uuid)
      const config = data.sizer_config || {}
      sizer = {
        uuid: data.sizer_uuid,
        name: data.sizer_name || '',
        parameters,
        config
      }
    }

    const selectors = (data.selectors || []).map((s: any) => ({
      uuid: s.uuid,
      name: s.name,
      parameters: s.parameters || [],
      config: s.config || {}
    }))
    const strategies = (data.strategies || []).map((s: any) => ({
      uuid: s.uuid,
      name: s.name,
      weight: Math.round((s.weight || 0) * 100),
      parameters: s.parameters || [],
      config: s.config || {}
    }))
    const riskManagers = (data.risk_managers || []).map((r: any) => ({
      uuid: r.uuid,
      name: r.name,
      parameters: r.parameters || [],
      config: r.config || {}
    }))
    formData.value = {
      name: data.name,
      initial_cash: data.initial_cash,
      mode: data.mode,
      benchmark: data.benchmark || '',
      description: data.description || '',
      selectors,
      sizer,
      strategies,
      risk_managers,
      analyzers: []
    }
  } catch (error: any) {
    // 错误已被统一处理，这里只需要记录日志
    console.error('加载投资组合失败:', error)
  }
}

// 保存投资组合
const savePortfolio = async () => {
  await formRef.value.validate()

  if (formData.value.selectors.length === 0) {
    message.warning('请至少添加一个选股器')
    return
  }
  if (!formData.value.sizer) {
    message.warning('请选择仓位管理器')
    return
  }
  if (formData.value.strategies.length === 0) {
    message.warning('请至少添加一个策略')
    return
  }

  const totalWeight = formData.value.strategies.reduce((sum, s) => sum + s.weight, 0)
  if (totalWeight === 0) {
    message.warning('策略权重总和不能为0')
    return
  }

  const normalizedStrategies = formData.value.strategies.map(s => ({
    component_uuid: s.uuid,
    weight: s.weight / totalWeight,
    config: s.config || {}
  }))

  const saveData = {
    name: formData.value.name,
    initial_cash: formData.value.initial_cash,
    mode: formData.value.mode,
    benchmark: formData.value.benchmark || null,
    description: formData.value.description || null,
    selectors: formData.value.selectors.map(s => ({
      component_uuid: s.uuid,
      config: s.config || {}
    })),
    sizer_uuid: formData.value.sizer?.uuid || '',
    strategies: normalizedStrategies,
    risk_managers: formData.value.risk_managers.map(r => ({
      component_uuid: r.uuid,
      config: r.config || {}
    })),
    analyzers: formData.value.analyzers.map(a => ({
      component_uuid: a.uuid,
      config: a.config || {}
    }))
  }

  const result = await submit(async () => {
    if (isEditMode.value) {
      return await portfolioApi.update(portfolioUuid.value!, saveData)
    } else {
      return await portfolioApi.create(saveData)
    }
  })

  if (result) {
    message.success(isEditMode.value ? '投资组合更新成功' : '投资组合创建成功')
    if (!isEditMode.value && result.data) {
      router.push(`/portfolio/${result.data.uuid}`)
    }
  }
}

const goBack = () => {
  router.back()
}

onMounted(() => {
  loadComponents()
  loadPortfolioData()
})
</script>

<style scoped lang="less">
.portfolio-form-editor {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 64px);
  background: #f5f7fa;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 24px;
  background: #fff;
  border-bottom: 1px solid #e8e8e8;
  flex-shrink: 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.title-section {
  h1 {
    margin: 0;
    font-size: 16px;
    font-weight: 600;
    color: #1a1a1a;
  }
  p {
    margin: 0;
    font-size: 12px;
    color: #999;
  }
}

.header-actions {
  display: flex;
  gap: 8px;
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

  :deep(.ant-card-body) {
    padding: 16px;
  }
}

.config-card {
  height: 100%;
  display: flex;
  flex-direction: column;

  :deep(.ant-card-body) {
    padding: 12px;
    overflow-y: auto;
    flex: 1;
    min-height: 0;
  }
}

.config-card {
  height: 100%;
  display: flex;
  flex-direction: column;

  :deep(.ant-card-body) {
    padding: 12px;
    overflow-y: auto;
    flex: 1;
    min-height: 0;
  }
}

.component-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;

  .component-name {
    flex: 1;
    font-weight: 500;
  }
}

// 组件类型按钮组
.component-type-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #f0f0f0;
}

.type-btn {
  flex: 1;
  min-width: 0;
  padding: 6px 8px;
  font-size: 12px;
  border: 1px solid #d9d9d9;
  background: #fff;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s;
  text-align: center;
  line-height: 1.2;

  &:hover {
    border-color: #1890ff;
    color: #1890ff;
  }

  &.active {
    background: #1890ff;
    border-color: #1890ff;
    color: #fff;
  }
}

.component-selector {
  margin-top: 8px;
}

.config-section {
  margin-bottom: 12px;

  &:last-child {
    margin-bottom: 0;
  }
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 8px;
  background: #fafafa;
  border-radius: 4px;
  margin-bottom: 8px;
}

.section-title {
  font-size: 13px;
  font-weight: 600;
  color: #333;
}

.config-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.config-item {
  border: 1px solid #f0f0f0;
  border-radius: 6px;
  overflow: hidden;
}

.item-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: #fff;
}

.item-name {
  font-size: 13px;
  font-weight: 500;
  color: #1a1a1a;
}

.item-actions {
  display: flex;
  align-items: center;
  gap: 8px;

  .unit {
    font-size: 12px;
    color: #999;
  }
}

.item-params {
  padding: 8px 12px;
  background: #fafafa;
  border-top: 1px solid #f0f0f0;
}

.param-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;

  &:last-child {
    margin-bottom: 0;
  }
}

.param-label {
  font-size: 12px;
  color: #666;
  min-width: 80px;
}
</style>
