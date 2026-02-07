<template>
  <div class="portfolio-graph-editor">
    <!-- 页面头部 -->
    <div class="page-header">
      <div class="header-left">
        <a-button
          class="back-btn"
          @click="goBack"
        >
          <ArrowLeftOutlined /> 返回
        </a-button>
        <div class="title-section">
          <h1 class="page-title">
            {{ isEditMode ? '编辑投资组合' : '创建投资组合' }}
          </h1>
          <p class="page-subtitle">
            拖拽组件节点到画布，连接它们来配置投资组合
          </p>
        </div>
      </div>
      <div class="header-actions">
        <a-button
          @click="validateGraph"
          :loading="validating"
        >
          <template #icon>
            <CheckOutlined />
          </template>
          验证配置
        </a-button>
        <a-button
          type="primary"
          :disabled="!isValid"
          :loading="saving"
          @click="savePortfolio"
        >
          <template #icon>
            <SaveOutlined />
          </template>
          {{ isEditMode ? '保存' : '创建' }}
        </a-button>
      </div>
    </div>

    <!-- 基本信息卡片 -->
    <a-card class="info-card" title="基本信息">
      <a-form
        ref="formRef"
        :model="formData"
        layout="horizontal"
        :label-col="{ style: { width: '100px' } }"
        :rules="formRules"
      >
        <a-row :gutter="24">
          <a-col :span="8">
            <a-form-item
              label="组合名称"
              name="name"
            >
              <a-input
                v-model:value="formData.name"
                placeholder="请输入投资组合名称"
              />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item
              label="运行模式"
              name="mode"
            >
              <a-select
                v-model:value="formData.mode"
                :disabled="isEditMode"
              >
                <a-select-option value="BACKTEST">
                  回测
                </a-select-option>
                <a-select-option value="PAPER">
                  模拟
                </a-select-option>
                <a-select-option value="LIVE">
                  实盘
                </a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item
              label="初始资金"
              name="initial_cash"
            >
              <a-input-number
                v-model:value="formData.initial_cash"
                :min="1000"
                :max="100000000"
                :step="10000"
                :precision="2"
                style="width: 100%"
                :disabled="isEditMode"
              >
                <template #prefix>
                  ¥
                </template>
              </a-input-number>
            </a-form-item>
          </a-col>
        </a-row>
      </a-form>
    </a-card>

    <!-- 编辑器内容 -->
    <div class="editor-content">
      <!-- 左侧组件面板 -->
      <div class="component-palette">
        <div class="palette-header">
          <h3>组件库</h3>
        </div>
        <div class="palette-search">
          <a-input
            v-model:value="searchKeyword"
            placeholder="搜索组件..."
            allow-clear
            size="small"
          >
            <template #prefix>
              🔍
            </template>
          </a-input>
        </div>
        <div class="palette-content">
          <!-- 策略组件 -->
          <div class="palette-section" v-if="filteredStrategies.length > 0 || !searchKeyword">
            <div
              class="section-header"
              @click="toggleSection('strategy')"
            >
              <Tag color="blue">策略</Tag>
              <span class="section-count">({{ filteredStrategies.length }}/{{ availableStrategies.length }})</span>
              <span class="collapse-icon" :class="{ expanded: expandedSections.strategy }">
                ‹
              </span>
            </div>
            <div v-show="expandedSections.strategy" class="section-content">
              <div
                v-for="strategy in filteredStrategies"
                :key="strategy.uuid"
                class="palette-item draggable-item"
                :draggable="true"
                @dragstart="handleDragStart($event, 'strategy', strategy)"
              >
                <div class="item-name">{{ strategy.name }}</div>
                <div class="item-type">{{ strategy.component_type }}</div>
              </div>
              <div
                v-if="filteredStrategies.length === 0 && availableStrategies.length > 0"
                class="empty-hint"
              >
                无匹配组件
              </div>
              <div
                v-if="availableStrategies.length === 0"
                class="empty-hint"
              >
                暂无策略组件
              </div>
            </div>
          </div>

          <!-- 选股器组件 -->
          <div class="palette-section" v-if="filteredSelectors.length > 0 || !searchKeyword">
            <div
              class="section-header"
              @click="toggleSection('selector')"
            >
              <Tag color="green">选股器</Tag>
              <span class="section-count">({{ filteredSelectors.length }}/{{ availableSelectors.length }})</span>
              <span class="collapse-icon" :class="{ expanded: expandedSections.selector }">
                ‹
              </span>
            </div>
            <div v-show="expandedSections.selector" class="section-content">
              <div
                v-for="selector in filteredSelectors"
                :key="selector.uuid"
                class="palette-item draggable-item"
                :draggable="true"
                @dragstart="handleDragStart($event, 'selector', selector)"
              >
                <div class="item-name">{{ selector.name }}</div>
                <div class="item-type">{{ selector.component_type }}</div>
              </div>
              <div
                v-if="filteredSelectors.length === 0 && availableSelectors.length > 0"
                class="empty-hint"
              >
                无匹配组件
              </div>
              <div
                v-if="availableSelectors.length === 0"
                class="empty-hint"
              >
                暂无选股器组件
              </div>
            </div>
          </div>

          <!-- Sizer 组件 -->
          <div class="palette-section" v-if="filteredSizers.length > 0 || !searchKeyword">
            <div
              class="section-header"
              @click="toggleSection('sizer')"
            >
              <Tag color="orange">仓位管理</Tag>
              <span class="section-count">({{ filteredSizers.length }}/{{ availableSizers.length }})</span>
              <span class="collapse-icon" :class="{ expanded: expandedSections.sizer }">
                ‹
              </span>
            </div>
            <div v-show="expandedSections.sizer" class="section-content">
              <div
                v-for="sizer in filteredSizers"
                :key="sizer.uuid"
                class="palette-item draggable-item"
                :draggable="true"
                @dragstart="handleDragStart($event, 'sizer', sizer)"
              >
                <div class="item-name">{{ sizer.name }}</div>
                <div class="item-type">{{ sizer.component_type }}</div>
              </div>
              <div
                v-if="filteredSizers.length === 0 && availableSizers.length > 0"
                class="empty-hint"
              >
                无匹配组件
              </div>
              <div
                v-if="availableSizers.length === 0"
                class="empty-hint"
              >
                暂无 Sizer 组件
              </div>
            </div>
          </div>

          <!-- 风控组件 -->
          <div class="palette-section" v-if="filteredRisks.length > 0 || !searchKeyword">
            <div
              class="section-header"
              @click="toggleSection('risk')"
            >
              <Tag color="red">风控</Tag>
              <span class="section-count">({{ filteredRisks.length }}/{{ availableRisks.length }})</span>
              <span class="collapse-icon" :class="{ expanded: expandedSections.risk }">
                ‹
              </span>
            </div>
            <div v-show="expandedSections.risk" class="section-content">
              <div
                v-for="risk in filteredRisks"
                :key="risk.uuid"
                class="palette-item draggable-item"
                :draggable="true"
                @dragstart="handleDragStart($event, 'risk', risk)"
              >
                <div class="item-name">{{ risk.name }}</div>
                <div class="item-type">{{ risk.component_type }}</div>
              </div>
              <div
                v-if="filteredRisks.length === 0 && availableRisks.length > 0"
                class="empty-hint"
              >
                无匹配组件
              </div>
              <div
                v-if="availableRisks.length === 0"
                class="empty-hint"
              >
                暂无风控组件
              </div>
            </div>
          </div>

          <!-- 搜索无结果提示 -->
          <div
            v-if="searchKeyword && filteredStrategies.length === 0 && filteredSelectors.length === 0 && filteredSizers.length === 0 && filteredRisks.length === 0"
            class="search-empty"
          >
            <p>未找到匹配的组件</p>
          </div>
        </div>
      </div>

      <!-- 中间画布区域 -->
      <div class="canvas-wrapper">
        <div
          v-if="nodes.length === 0"
          class="canvas-empty"
          @drop="handleDrop"
          @dragover.prevent
        >
          <div class="empty-icon">
            <NodeIndexOutlined />
          </div>
          <p class="empty-title">
            拖拽组件到此处开始配置
          </p>
          <p class="empty-desc">
            从左侧选择组件，拖拽到画布上，然后配置它们之间的连接关系
          </p>
        </div>
        <NodeGraphCanvas
          v-else
          :nodes="nodes"
          :edges="edges"
          :available-components="{
            strategies: availableStrategies,
            selectors: availableSelectors,
            sizers: availableSizers,
            risks: availableRisks
          }"
          @node-click="handleNodeClick"
          @edge-click="handleEdgeClick"
          @nodes-change="handleNodesChange"
          @edges-change="handleEdgesChange"
          @delete="handleDelete"
          @connection-start="handleConnectionStart"
        />
      </div>

      <!-- 右侧属性面板 -->
      <div class="property-panel">
        <div class="panel-header">
          <h3>属性</h3>
        </div>
        <div
          v-if="selectedNode"
          class="panel-content"
        >
          <NodePropertyPanel
            :node="selectedNode"
            @node-update="handleNodeUpdate"
          />
        </div>
        <div
          v-else
          class="panel-empty"
        >
          <p>选择一个节点查看属性</p>
        </div>
      </div>
    </div>

    <!-- 验证结果弹窗 -->
    <a-modal
      v-model:open="showValidationModal"
      title="配置验证"
      :footer="null"
    >
      <a-result
        :status="validationStatus"
        :title="validationTitle"
      >
        <template #subTitle>
          <div v-if="validationErrors.length > 0">
            <p>发现以下问题：</p>
            <ul class="error-list">
              <li
                v-for="(error, index) in validationErrors"
                :key="index"
                class="error-item"
              >
                {{ error }}
              </li>
            </ul>
          </div>
          <div v-else>
            <p>配置验证通过，可以保存投资组合</p>
          </div>
        </template>
      </a-result>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { message, Tag } from 'ant-design-vue'
import {
  ArrowLeftOutlined,
  CheckOutlined,
  SaveOutlined,
  NodeIndexOutlined
} from '@ant-design/icons-vue'
import NodeGraphCanvas from '@/components/node-graph/NodeGraphCanvas.vue'
import NodePropertyPanel from '@/components/node-graph/NodePropertyPanel.vue'
import { componentsApi, type ComponentSummary } from '@/api/modules/components'
import { portfolioApi } from '@/api/modules/portfolio'
import type {
  GraphNode,
  GraphEdge,
  NodeType
} from '@/components/node-graph/types'

const router = useRouter()
const route = useRoute()

// 表单数据
const formRef = ref()
const formData = reactive({
  name: '',
  mode: 'BACKTEST',
  initial_cash: 100000
})

const formRules = {
  name: [{ required: true, message: '请输入组合名称', trigger: 'blur' }],
  mode: [{ required: true, message: '请选择运行模式', trigger: 'change' }],
  initial_cash: [{ required: true, message: '请输入初始资金', trigger: 'blur' }]
}

// 状态管理
const nodes = ref<GraphNode[]>([])
const edges = ref<GraphEdge[]>([])
const selectedNode = ref<GraphNode | null>(null)
const validating = ref(false)
const saving = ref(false)
const isValid = ref(false)
const showValidationModal = ref(false)
const validationErrors = ref<string[]>([])
const validationStatus = ref<'success' | 'error' | 'warning'>('success')
const validationTitle = ref('')

// 初始化默认节点
const initializeDefaultNodes = () => {
  // 如果是编辑模式或已有节点，不重复初始化
  if (isEditMode.value || nodes.value.length > 0) return

  // 创建默认的Portfolio节点（居中）
  const defaultPortfolioNode: GraphNode = {
    id: 'portfolio-root',
    type: 'PORTFOLIO',
    position: { x: 400, y: 200 },
    data: {
      label: formData.name || '投资组合',
      config: {
        initial_cash: formData.initial_cash,
        mode: formData.mode
      },
      description: '投资组合主节点'
    }
  }

  nodes.value = [defaultPortfolioNode]
}

// 可用组件列表
const availableStrategies = ref<ComponentSummary[]>([])
const availableSelectors = ref<ComponentSummary[]>([])
const availableSizers = ref<ComponentSummary[]>([])
const availableRisks = ref<ComponentSummary[]>([])

// 组件类型折叠状态（默认全部展开）
const expandedSections = ref({
  strategy: true,
  selector: true,
  sizer: true,
  risk: true
})

// 搜索关键词
const searchKeyword = ref('')

// 过滤后的组件列表
const filteredStrategies = computed(() => {
  if (!searchKeyword.value) return availableStrategies.value
  const keyword = searchKeyword.value.toLowerCase()
  return availableStrategies.value.filter(c =>
    c.name.toLowerCase().includes(keyword) ||
    c.component_type?.toLowerCase().includes(keyword) ||
    c.description?.toLowerCase().includes(keyword)
  )
})

const filteredSelectors = computed(() => {
  if (!searchKeyword.value) return availableSelectors.value
  const keyword = searchKeyword.value.toLowerCase()
  return availableSelectors.value.filter(c =>
    c.name.toLowerCase().includes(keyword) ||
    c.component_type?.toLowerCase().includes(keyword) ||
    c.description?.toLowerCase().includes(keyword)
  )
})

const filteredSizers = computed(() => {
  if (!searchKeyword.value) return availableSizers.value
  const keyword = searchKeyword.value.toLowerCase()
  return availableSizers.value.filter(c =>
    c.name.toLowerCase().includes(keyword) ||
    c.component_type?.toLowerCase().includes(keyword) ||
    c.description?.toLowerCase().includes(keyword)
  )
})

const filteredRisks = computed(() => {
  if (!searchKeyword.value) return availableRisks.value
  const keyword = searchKeyword.value.toLowerCase()
  return availableRisks.value.filter(c =>
    c.name.toLowerCase().includes(keyword) ||
    c.component_type?.toLowerCase().includes(keyword) ||
    c.description?.toLowerCase().includes(keyword)
  )
})

// 当搜索时自动展开所有类型
watch(searchKeyword, (newVal) => {
  if (newVal) {
    expandedSections.value = { strategy: true, selector: true, sizer: true, risk: true }
  }
})

// 切换组件类型折叠状态
const toggleSection = (type: keyof typeof expandedSections.value) => {
  expandedSections.value[type] = !expandedSections.value[type]
}

// 是否编辑模式
const isEditMode = computed(() => !!route.params.uuid)
const portfolioUuid = computed(() => route.params.uuid as string | undefined)

// 加载组件列表
const loadComponents = async () => {
  try {
    console.log('=== 开始加载组件 ===')
    const allComponents = await componentsApi.list()
    console.log('API返回原始数据:', allComponents)
    console.log('数据类型:', typeof allComponents, '是否为数组:', Array.isArray(allComponents))

    // component_type 是字符串类型: 'strategy', 'selector', 'sizer', 'risk', 'analyzer'
    availableStrategies.value = allComponents.filter((c: ComponentSummary) => c.component_type === 'strategy')
    availableSelectors.value = allComponents.filter((c: ComponentSummary) => c.component_type === 'selector')
    availableSizers.value = allComponents.filter((c: ComponentSummary) => c.component_type === 'sizer')
    availableRisks.value = allComponents.filter((c: ComponentSummary) => c.component_type === 'risk')

    console.log('=== 过滤后的组件 ===')
    console.log('策略:', availableStrategies.value.length, availableStrategies.value.map(c => c.name))
    console.log('选股器:', availableSelectors.value.length)
    console.log('仓位管理:', availableSizers.value.length)
    console.log('风控:', availableRisks.value.length)

    console.log('=== expandedSections状态 ===')
    console.log('expandedSections:', expandedSections.value)
  } catch (error: any) {
    console.error('加载组件失败:', error)
    message.error(`加载组件列表失败: ${error.message}`)
  }
}

// 如果是编辑模式，加载现有数据
const loadPortfolioData = async () => {
  if (!isEditMode.value) return

  try {
    const portfolio = await portfolioApi.get(portfolioUuid.value)
    formData.name = portfolio.name
    formData.mode = portfolio.mode
    formData.initial_cash = portfolio.initial_cash

    // TODO: 从 portfolio 数据构建节点图
    // 这需要后端支持保存和加载节点图数据
  } catch (error: any) {
    message.error(`加载投资组合数据失败: ${error.message}`)
  }
}

// 拖拽开始
const handleDragStart = (event: DragEvent, type: string, component: ComponentSummary) => {
  if (event.dataTransfer) {
    event.dataTransfer.setData('application/json', JSON.stringify({ type, component }))
  }
}

// 放置到画布
const handleDrop = (event: DragEvent) => {
  event.preventDefault()

  const data = event.dataTransfer?.getData('application/json')
  if (!data) return

  const { type, component } = JSON.parse(data)

  // 创建新节点
  const newNode: GraphNode = {
    id: `node-${Date.now()}`,
    type: type === 'strategy' ? 'STRATEGY' :
          type === 'selector' ? 'SELECTOR' :
          type === 'sizer' ? 'SIZER' :
          'RISK_MANAGEMENT',
    position: {
      x: event.offsetX - 100,
      y: event.offsetY - 50
    },
    data: {
      label: component.name,
      config: {
        component_uuid: component.uuid
      },
      componentUuid: component.uuid,
      description: component.description
    }
  }

  nodes.value.push(newNode)
  message.success(`已添加 ${component.name}`)
}

// 节点点击
const handleNodeClick = (node: GraphNode) => {
  selectedNode.value = node
}

// 边点击
const handleEdgeClick = (edge: GraphEdge) => {
  // TODO: 实现边的属性编辑
}

// 连接开始（从端口拖拽）
const handleConnectionStart = (data: any) => {
  // 可以在这里做一些准备工作
  console.log('Connection started from:', data)
}

// 节点变化
const handleNodesChange = (newNodes: GraphNode[]) => {
  nodes.value = newNodes
}

// 边变化
const handleEdgesChange = (newEdges: GraphEdge[]) => {
  edges.value = newEdges
}

// 节点更新
const handleNodeUpdate = (node: GraphNode) => {
  const index = nodes.value.findIndex(n => n.id === node.id)
  if (index !== -1) {
    nodes.value[index] = node
  }
}

// 删除
const handleDelete = () => {
  selectedNode.value = null
}

// 验证图配置
const validateGraph = async () => {
  validating.value = true
  validationErrors.value = []

  try {
    // 验证表单
    await formRef.value.validate()

    // 验证节点
    if (nodes.value.length === 0) {
      validationErrors.value.push('请至少添加一个组件节点')
    }

    // 验证策略节点
    const strategyNodes = nodes.value.filter(n => n.type === 'STRATEGY')
    if (strategyNodes.length === 0) {
      validationErrors.value.push('请至少添加一个策略组件')
    }

    // 验证权重
    const totalWeight = strategyNodes.reduce((sum, node) => {
      return sum + (node.data.config?.weight || 0)
    }, 0)

    if (totalWeight !== 100 && totalWeight !== 0) {
      validationErrors.value.push(`策略权重总和为 ${totalWeight}%，建议设置为 100%`)
    }

    if (validationErrors.value.length === 0) {
      isValid.value = true
      validationStatus.value = 'success'
      validationTitle.value = '验证通过'
    } else {
      isValid.value = false
      validationStatus.value = 'warning'
      validationTitle.value = '发现配置问题'
    }

    showValidationModal.value = true
  } catch (error) {
    // 表单验证失败
    isValid.value = false
  } finally {
    validating.value = false
  }
}

// 保存投资组合
const savePortfolio = async () => {
  try {
    saving.value = true

    // 等待表单验证
    await formRef.value.validate()

    // 构建保存数据
    const saveData: any = {
      name: formData.name,
      initial_cash: formData.initial_cash,
      mode: formData.mode,
      // 将节点图数据转换为组件配置
      strategies: [],
      selectors: [],
      sizers: [],
      risk_managers: []
    }

    // 解析节点数据
    for (const node of nodes.value) {
      const componentUuid = node.data.componentUuid
      const weight = node.data.config?.weight || 0

      switch (node.type) {
        case 'STRATEGY':
          saveData.strategies.push({
            component_uuid: componentUuid,
            weight: weight / 100  // 转换为小数
          })
          break
        case 'SELECTOR':
          saveData.selectors.push({
            component_uuid: componentUuid
          })
          break
        case 'SIZER':
          saveData.sizers.push({
            component_uuid: componentUuid
          })
          break
        case 'RISK_MANAGEMENT':
          saveData.risk_managers.push({
            component_uuid: componentUuid
          })
          break
      }
    }

    if (isEditMode.value) {
      await portfolioApi.update(portfolioUuid.value, saveData)
      message.success('投资组合更新成功')
    } else {
      const result = await portfolioApi.create(saveData)
      message.success('投资组合创建成功')
      router.push(`/portfolio/${result.uuid}`)
    }
  } catch (error: any) {
    message.error(`保存失败: ${error.message || error.response?.data?.detail || '未知错误'}`)
  } finally {
    saving.value = false
  }
}

// 返回
const goBack = () => {
  router.back()
}

// 监听表单数据变化，更新Portfolio节点
watch(() => formData, (newData) => {
  const portfolioNode = nodes.value.find(n => n.id === 'portfolio-root')
  if (portfolioNode) {
    portfolioNode.data.label = newData.name || '投资组合'
    portfolioNode.data.config = {
      initial_cash: newData.initial_cash,
      mode: newData.mode
    }
  }
}, { deep: true })

onMounted(() => {
  loadComponents()
  loadPortfolioData()
  // 组件加载后初始化默认节点
  initializeDefaultNodes()
})
</script>

<style scoped lang="less">
.portfolio-graph-editor {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 64px);
  overflow: hidden;
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
  gap: 16px;
}

.back-btn {
  display: flex;
  align-items: center;
  gap: 4px;
}

.title-section {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.page-title {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: #1a1a1a;
}

.page-subtitle {
  margin: 0;
  font-size: 13px;
  color: #666;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.info-card {
  margin: 0 24px 12px 24px;
  border-radius: 8px;
  flex-shrink: 0;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
}

.info-card :deep(.ant-card-body) {
  padding: 16px 24px;
}

.editor-content {
  display: flex;
  flex: 1;
  gap: 16px;
  padding: 0 24px 16px;
  min-height: 0;
  overflow: hidden;
}

// 组件面板
.component-palette {
  width: 280px;
  background: #fff;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.palette-header {
  padding: 16px;
  border-bottom: 1px solid #f0f0f0;

  h3 {
    margin: 0;
    font-size: 14px;
    font-weight: 600;
    color: #1a1a1a;
  }
}

.palette-search {
  padding: 8px 16px;
  border-bottom: 1px solid #f0f0f0;

  :deep(.ant-input) {
    font-size: 12px;
  }
}

.palette-content {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.palette-section {
  margin-bottom: 8px;
  border-bottom: 1px solid #f0f0f0;

  &:last-child {
    border-bottom: none;
  }
}

.section-header {
  display: flex;
  align-items: center;
  padding: 10px 8px;
  cursor: pointer;
  user-select: none;
  transition: background 0.2s;

  &:hover {
    background: #f5f5f5;
  }
}

.section-count {
  margin-left: 4px;
  font-size: 11px;
  color: #999;
}

.collapse-icon {
  margin-left: auto;
  font-size: 16px;
  color: #999;
  transition: transform 0.2s;
  display: inline-block;

  &.expanded {
    transform: rotate(90deg);
  }
}

.section-content {
  padding: 0 8px 8px;
}

.section-title {
  padding: 8px;
  font-size: 12px;
  font-weight: 500;
  color: #666;
}

.palette-item {
  padding: 10px 12px;
  margin-bottom: 8px;
  background: #fafafa;
  border: 1px solid #e8e8e8;
  border-radius: 6px;
  cursor: grab;
  transition: all 0.2s;

  &:hover {
    background: #f0f9ff;
    border-color: #1890ff;
    box-shadow: 0 2px 4px rgba(24, 144, 255, 0.1);
  }

  &:active {
    cursor: grabbing;
  }
}

.item-name {
  font-size: 13px;
  font-weight: 500;
  color: #1a1a1a;
  margin-bottom: 2px;
}

.item-type {
  font-size: 11px;
  color: #8c8c8c;
  font-family: monospace;
}

.empty-hint {
  padding: 12px;
  text-align: center;
  font-size: 12px;
  color: #999;
}

.search-empty {
  padding: 40px 20px;
  text-align: center;

  p {
    margin: 0;
    font-size: 13px;
    color: #999;
  }
}

// 画布区域
.canvas-wrapper {
  flex: 1;
  background: #fff;
  border-radius: 8px;
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.canvas-empty {
  width: calc(100% - 32px);
  height: calc(100% - 32px);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #fafafa;
  border: 2px dashed #d9d9d9;
  border-radius: 8px;
}

.empty-icon {
  font-size: 64px;
  color: #d9d9d9;
  margin-bottom: 16px;
}

.empty-title {
  font-size: 16px;
  font-weight: 500;
  color: #333;
  margin: 0 0 8px 0;
}

.empty-desc {
  font-size: 13px;
  color: #999;
  margin: 0;
  text-align: center;
  max-width: 400px;
}

// 属性面板
.property-panel {
  width: 320px;
  background: #fff;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-header {
  padding: 16px;
  border-bottom: 1px solid #f0f0f0;

  h3 {
    margin: 0;
    font-size: 14px;
    font-weight: 600;
    color: #1a1a1a;
  }
}

.panel-content {
  flex: 1;
  overflow-y: auto;
}

.panel-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  text-align: center;
  color: #999;
  font-size: 13px;
}

// 验证结果
.error-list {
  text-align: left;
  max-width: 400px;
  margin: 0 auto;
}

.error-item {
  color: #ff4d4f;
  padding: 4px 0;
}
</style>
