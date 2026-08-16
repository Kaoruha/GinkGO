<template>
  <div
    class="portfolio-form-editor"
    :class="{ 'modal-mode': isModalMode }"
  >
    <PageLayout>
      <template #title>
        <PageTitle
          :title="isEditMode ? '编辑投资组合' : '创建投资组合'"
          :back-action="!isModalMode"
          back-label="返回"
          @back="goBack"
        />
      </template>
      <template
        v-if="!isModalMode"
        #description
      >
        配置交易策略、选股器、仓位管理和风控规则
      </template>
      <template #actions>
        <button
          class="btn-secondary"
          data-testid="btn-cancel-form"
          @click="goBack"
        >
          取消
        </button>
        <button
          class="btn-primary"
          data-testid="btn-save-portfolio"
          :disabled="saving"
          @click="savePortfolio"
        >
          {{ isEditMode ? '保存' : '创建' }}
        </button>
      </template>

      <div
        v-if="isEditMode"
        class="edit-mode-hint"
      >
        编辑模式仅可保存名称、描述与初始资金;组件绑定与运行模式创建后不可更改(如需调整请新建组合)。
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
                    <input
                      v-model="formData.name"
                      type="text"
                      placeholder="组合名称"
                      data-testid="input-portfolio-name"
                      class="form-input"
                    >
                  </div>
                  <div class="form-group">
                    <label class="form-label">初始资金 <span class="required">*</span></label>
                    <div class="input-group">
                      <span class="input-prefix">¥</span>
                      <input
                        type="text"
                        :value="formatNumber(formData.initial_cash)"
                        class="form-input"
                        @input="onInitialCashInput"
                      >
                    </div>
                  </div>
                </div>
                <div class="form-row">
                  <div class="form-group">
                    <label class="form-label">运行模式 <span class="required">*</span></label>
                    <select
                      v-model="formData.mode"
                      class="form-select"
                      :disabled="isEditMode"
                    >
                      <option value="BACKTEST">
                        回测
                      </option>
                      <option value="PAPER">
                        模拟盘
                      </option>
                      <option value="LIVE">
                        实盘
                      </option>
                    </select>
                  </div>
                  <div class="form-group">
                    <label class="form-label">基准</label>
                    <input
                      v-model="formData.benchmark"
                      type="text"
                      placeholder="000001.SZ（可选）"
                      class="form-input"
                      :disabled="isEditMode"
                    >
                  </div>
                </div>
                <div class="form-group">
                  <label class="form-label">描述</label>
                  <textarea
                    v-model="formData.description"
                    :rows="2"
                    placeholder="组合描述"
                    class="form-textarea"
                  />
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
              <ComponentConfigSection
                v-if="formData.selectors.length > 0"
                :title="`选股器 (${formData.selectors.length})`"
                :items="formData.selectors"
                :versions-for="item => getComponentVersions(item.name, 'selector')"
                id-prefix="sel"
                @remove="removeSelector"
                @change-version="(i, v) => changeComponentVersion('selector', i, v)"
              />

              <!-- 仓位管理器配置(单数:header 移除,条目无移除按钮) -->
              <ComponentConfigSection
                v-if="formData.sizer"
                title="仓位管理器"
                :items="[formData.sizer]"
                :versions-for="item => getComponentVersions(item.name, 'sizer')"
                :removable="false"
                remove-label
                id-prefix="sizer"
                @remove="removeSizer"
                @change-version="(i, v) => changeComponentVersion('sizer', i, v)"
              />

              <!-- 策略配置(带权重) -->
              <ComponentConfigSection
                v-if="formData.strategies.length > 0"
                :title="`策略 (${formData.strategies.length})`"
                :items="formData.strategies"
                :versions-for="item => getComponentVersions(item.name, 'strategy')"
                show-weight
                id-prefix="strat"
                @remove="removeStrategy"
                @change-version="(i, v) => changeComponentVersion('strategy', i, v)"
              />

              <!-- 风控配置 -->
              <ComponentConfigSection
                v-if="formData.risk_managers.length > 0"
                :title="`风控 (${formData.risk_managers.length})`"
                :items="formData.risk_managers"
                :versions-for="item => getComponentVersions(item.name, 'risk')"
                id-prefix="risk"
                @remove="removeRisk"
                @change-version="(i, v) => changeComponentVersion('risk', i, v)"
              />

              <!-- 分析器配置 -->
              <ComponentConfigSection
                v-if="formData.analyzers.length > 0"
                :title="`分析器 (${formData.analyzers.length})`"
                :items="formData.analyzers"
                :versions-for="item => getComponentVersions(item.name, 'analyzer')"
                id-prefix="ana"
                @remove="removeAnalyzer"
                @change-version="(i, v) => changeComponentVersion('analyzer', i, v)"
              />

              <!-- 空状态 -->
              <div
                v-if="isConfigEmpty"
                class="empty-state"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  width="48"
                  height="48"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1"
                >
                  <rect
                    x="3"
                    y="3"
                    width="18"
                    height="18"
                    rx="2"
                    ry="2"
                  />
                  <line
                    x1="9"
                    y1="3"
                    x2="9"
                    y2="21"
                  />
                </svg>
                <p>暂未配置组件</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </PageLayout>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import PageLayout from '@/components/common/PageLayout.vue'
import PageTitle from '@/components/common/PageTitle.vue'
import { useRouter, useRoute } from 'vue-router'
import { portfolioApi } from '@/api/modules/portfolio'
import { componentsApi } from '@/api/modules/components'
import SearchSelect from '@/components/common/SearchSelect.vue'
import type { SearchOption } from '@/components/common/SearchSelect.vue'
import ComponentConfigSection from '@/components/portfolio/ComponentConfigSection.vue'
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

// 是否编辑模式(modal 模式恒为创建;路由模式读 :id —— 路由定义为 /portfolios/:id/edit)
const isEditMode = computed(() => !props.isModalMode && !!route.params.id)
const editingId = computed(() => (isEditMode.value ? String(route.params.id) : ''))

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
    return res.parameters || []
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

// 合并旧配置到新参数定义(旧值优先,缺失项用默认)
const mergeConfig = (parameters: any[], oldConfig: Record<string, any>): Record<string, any> => {
  const newConfig = buildDefaultConfig(parameters)
  const merged: Record<string, any> = {}
  for (const param of parameters) {
    merged[param.name] = param.name in oldConfig ? oldConfig[param.name] : newConfig[param.name]
  }
  return merged
}

// 组件类型 → formData 列表访问器(sizer 单数,包成单元素数组统一处理)
const componentAccessors: Record<string, () => any[]> = {
  selector: () => formData.value.selectors,
  sizer: () => (formData.value.sizer ? [formData.value.sizer] : []),
  strategy: () => formData.value.strategies,
  risk: () => formData.value.risk_managers,
  analyzer: () => formData.value.analyzers,
}

// 模拟加载组件版本
const loadComponentVersions = async (name: string, type: string) => {
  const cacheKey = `${name}_${type}`
  if (!componentVersionsCache.value[cacheKey]) {
    componentVersionsCache.value[cacheKey] = []
  }
  return componentVersionsCache.value[cacheKey]
}

// 切换组件版本(sizer 单数走 index=0,通过 componentAccessors 统一访问)
const changeComponentVersion = async (componentType: string, index: number, versionValue: string) => {
  try {
    const accessor = componentAccessors[componentType]
    if (!accessor) return
    const entry = accessor()[index]
    if (!entry) return

    const versions = getComponentVersions(entry.name, componentType)
    const targetVersion = versions.find((v: any) => v.version === versionValue)
    if (!targetVersion) return

    const parameters = await loadComponentParameters(targetVersion.uuid)
    entry.uuid = targetVersion.uuid
    entry.version = versionValue
    entry.parameters = parameters
    entry.config = mergeConfig(parameters, entry.config || {})
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
    const items = (res as any)?.items || []
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
      types.map(t => componentsApi.list(t, { page: 1, page_size: 100 }).catch(() => ({ items: [], total: 0 }) as any))
    )
    availableStrategies.value = results[0]?.items || []
    availableSelectors.value = results[1]?.items || []
    availableSizers.value = results[2]?.items || []
    availableRisks.value = results[3]?.items || []
    availableAnalyzers.value = results[4]?.items || []
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
  // 创建模式要求至少一个策略;编辑模式仅更新基本字段(组件不可改),跳过此校验
  if (!isEditMode.value && formData.value.strategies.length === 0) {
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

    if (isEditMode.value) {
      // 后端仅支持基本字段更新;组件绑定与 mode 创建后不可改(saga update_basic_info)
      await portfolioApi.update(editingId.value, {
        name: formData.value.name,
        desc: formData.value.description ?? '',
        initial_cash: formData.value.initial_cash,
      })
      message.success('投资组合更新成功')
      if (props.isModalMode) {
        emit('created', editingId.value)
      } else {
        router.push(`/portfolios/${editingId.value}`)
      }
    } else {
      const result = await portfolioApi.create(payload)
      message.success('投资组合创建成功')
      if (props.isModalMode) {
        emit('created', result.uuid)
      } else if (result.uuid) {
        router.push(`/portfolios/${result.uuid}`)
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

// 按类型取可用组件列表(编辑回填时匹配 version)
const getAvailableByType = (type: string): any[] => {
  if (type === 'strategy') return availableStrategies.value
  if (type === 'selector') return availableSelectors.value
  if (type === 'sizer') return availableSizers.value
  if (type === 'risk') return availableRisks.value
  if (type === 'analyzer') return availableAnalyzers.value
  return []
}

// 将详情返回的组件映射为 formData 条目(拉参数定义 + 合并旧配置,保留旧值优先)
const mapDetailComponents = async (items: any[], type: string, withWeight = false) => {
  if (!items || items.length === 0) return []
  const available = getAvailableByType(type)
  return Promise.all(items.map(async (c: any) => {
    const parameters = await loadComponentParameters(c.uuid)
    const matched = available.find(a => a.uuid === c.uuid)
    const version = matched?.version || c.version || 'UNKNOWN_VERSION'
    const entry: any = {
      uuid: c.uuid,
      name: c.name,
      version,
      parameters,
      config: parameters.length > 0 ? mergeConfig(parameters, c.config || {}) : (c.config || {}),
    }
    if (withWeight) entry.weight = c.weight ?? 100
    return entry
  }))
}

// 编辑模式:加载现有组合并回填基本字段 + 组件绑定
const loadPortfolioForEdit = async () => {
  if (!editingId.value) return
  try {
    const detail: any = await portfolioApi.get(editingId.value)
    formData.value.name = detail.name || ''
    formData.value.initial_cash = detail.initial_cash ?? 1000000
    const detailMode = typeof detail.mode === 'string' ? detail.mode : 'BACKTEST'
    formData.value.mode = (['BACKTEST', 'PAPER', 'LIVE'].includes(detailMode) ? detailMode : 'BACKTEST') as any
    formData.value.benchmark = detail.benchmark || ''
    formData.value.description = detail.desc || ''
    // 后端详情为顶级键(selectors/sizers/strategies/...),sizers 为数组取首个
    const comps = {
      selectors: detail.selectors || [],
      sizer: (detail.sizers || [])[0] || null,
      strategies: detail.strategies || [],
      risk_managers: detail.risk_managers || [],
      analyzers: detail.analyzers || [],
    }
    formData.value.selectors = await mapDetailComponents(comps.selectors, 'selector')
    formData.value.sizer = comps.sizer ? ((await mapDetailComponents([comps.sizer], 'sizer'))[0] || null) : null
    formData.value.strategies = await mapDetailComponents(comps.strategies, 'strategy', true)
    formData.value.risk_managers = await mapDetailComponents(comps.risk_managers, 'risk')
    formData.value.analyzers = await mapDetailComponents(comps.analyzers, 'analyzer')
  } catch (e: any) {
    message.error(`加载组合失败: ${e.message || e}`)
  }
}

onMounted(async () => {
  await loadComponents()
  if (isEditMode.value) {
    await loadPortfolioForEdit()
  }
})
</script>

<style scoped>
.portfolio-form-editor {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: hsl(var(--background));
}

.portfolio-form-editor.modal-mode .form-layout {
  padding: 0;
}

.portfolio-form-editor.modal-mode :deep(.page-layout-header) {
  padding: 12px 16px;
  border-bottom: 1px solid hsl(var(--border));
  margin-bottom: 0;
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
  border-bottom: 1px solid hsl(var(--border));
}

.card-header-sm h4 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: hsl(var(--foreground));
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
  color: hsl(var(--error));
}

.input-group {
  display: flex;
  align-items: center;
  gap: 8px;
  background: hsl(var(--border));
  border: 1px solid hsl(var(--secondary));
  border-radius: var(--radius-sm);
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
  gap: 8px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid hsl(var(--border));
}

.type-btn {
  flex: 1;
  min-width: 0;
  padding: 6px 8px;
  font-size: 12px;
  border: 1px solid hsl(var(--secondary));
  background: transparent;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.2s;
  text-align: center;
  line-height: 1.2;
  color: hsl(var(--foreground));
}

.type-btn:hover {
  border-color: hsl(var(--primary));
  color: hsl(var(--primary));
}

.type-btn.active {
  background: hsl(var(--primary));
  border-color: hsl(var(--primary));
  color: hsl(var(--primary-foreground));
}

.component-selector {
  margin-top: 8px;
}

/* 组件配置 section/参数行样式已迁至 ComponentConfigSection/ParamFields */

/* 空状态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px;
  color: hsl(var(--muted-foreground));
}

.empty-state svg {
  margin-bottom: 16px;
  opacity: 0.3;
}

.empty-state p {
  margin: 0;
  font-size: 14px;
}

.edit-mode-hint {
  margin: 0 0 12px;
  padding: 8px 12px;
  background: hsl(var(--secondary));
  border-left: 3px solid hsl(var(--primary));
  color: hsl(var(--muted-foreground));
  font-size: 13px;
  border-radius: var(--radius-sm);
}
</style>
