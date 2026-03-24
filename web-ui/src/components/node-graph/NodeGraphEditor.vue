<template>
  <div class="node-graph-editor">
    <!-- Custom -->
    <div class="toolbar">
      <div class="btn-group">
        <button
          class="btn-primary"
          :disabled="validating"
          @click="validateGraph"
        >
          <svg v-if="!validating" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
          <svg v-else xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 12a9 9 0 1 1-6.219-8.56"></path>
          </svg>
          验证
        </button>
        <button
          class="btn-secondary"
          :disabled="!isValid"
          @click="saveGraph"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M19 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11l5 5v11a2 2 0 0 1-2 2z"></path>
            <polyline points="17 21 17 13 7 13 7 21"></polyline>
            <polyline points="7 3 7 8 15 8"></polyline>
          </svg>
          保存
        </button>
        <button
          class="btn-secondary"
          :disabled="!isValid"
          @click="compileGraph"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="16 18 22 12 16 6"></polyline>
            <polyline points="8 6 2 12 8 18"></polyline>
          </svg>
          编译
        </button>
        <button
          class="btn-primary"
          :disabled="!compiledConfig"
          @click="createBacktest"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="10"></circle>
            <polygon points="10 8 16 12 10 16 10 8"></polygon>
          </svg>
          创建回测任务
        </button>
      </div>

      <div class="toolbar-spacer"></div>

      <div class="btn-group">
        <button
          class="btn-secondary"
          :disabled="!canUndo"
          @click="undo"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M3 7v6h6"></path>
            <path d="M21 17a9 9 0 0 0-9-9 9 9 0 0 0-6 2.3L3 13"></path>
          </svg>
          撤销
        </button>
        <button
          class="btn-secondary"
          :disabled="!canRedo"
          @click="redo"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 7v6h-6"></path>
            <path d="M3 17a9 9 0 0 1 9-9 9 9 0 0 1 6 2.3l3 2.7"></path>
          </svg>
          重做
        </button>
      </div>
    </div>

    <!-- Custom -->
    <div class="editor-content">
      <!-- Custom -->
      <div class="node-palette">
        <NodePalette @node-drag-start="handleNodeDragStart" />
      </div>

      <!-- Custom -->
      <div class="canvas-container">
        <NodeGraphCanvas
          :nodes="nodes"
          :edges="edges"
          @node-click="handleNodeClick"
          @edge-click="handleEdgeClick"
          @nodes-change="handleNodesChange"
          @edges-change="handleEdgesChange"
        />
      </div>

      <!-- Custom -->
      <div class="property-panel">
        <NodePropertyPanel
          v-if="selectedNode"
          :node="selectedNode"
          @node-update="handleNodeUpdate"
        />
        <div
          v-else
          class="empty-hint"
        >
          <p>选择一个节点以编辑其属性</p>
        </div>
      </div>
    </div>

    <!-- Custom -->
    <div
      v-if="validationResult"
      class="validation-panel"
      :class="{ show: true }"
    >
      <GraphValidator
        :validation-result="validationResult"
        @close="validationResult = null"
      />
    </div>

    <!-- Custom -->
    <div
      v-if="compileModalVisible"
      class="modal-overlay"
      @click.self="compileModalVisible = false"
    >
      <div class="modal">
        <div class="modal-header">
          <h3>编译结果</h3>
          <button class="modal-close" @click="compileModalVisible = false">×</button>
        </div>
        <div class="modal-body">
          <pre class="compile-preview">{{ JSON.stringify(compiledConfig, null, 2) }}</pre>
        </div>
        <div class="modal-actions">
          <button class="btn-secondary" @click="compileModalVisible = false">关闭</button>
          <button
            v-if="compiledConfig"
            class="btn-primary"
            @click="createBacktest"
          >
            创建回测任务
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import NodeGraphCanvas from './NodeGraphCanvas.vue'
import NodePalette from './NodePalette.vue'
import NodePropertyPanel from './NodePropertyPanel.vue'
import GraphValidator from './GraphValidator.vue'
import {
  NodeType,
  GraphNode,
  GraphEdge,
  GraphData,
  ValidationResult,
  BacktestTaskCreate
} from './types'
import { useNodeGraph } from '@/composables/useNodeGraph'
import { nodeGraphApi } from '@/api/modules/nodeGraph'

// 简化的通知函数
const showToast = (message: string, type: 'success' | 'error' | 'info' | 'warning' = 'success') => {
  console.log(`[${type.toUpperCase()}] ${message}`)
}

const emit = defineEmits(['update:modelValue'])

// Props
interface Props {
  graphUuid?: string
  initialData?: GraphData
}

const props = withDefaults(defineProps<Props>(), {
  initialData: undefined
})

// 使用节点图操作 composable
const {
  nodes,
  edges,
  selectedNode,
  selectedEdge,
  isValid,
  validationResult,
  canUndo,
  canRedo,
  addNode,
  removeNode,
  addEdge,
  removeEdge,
  updateNode,
  undo,
  redo,
  validateGraph: validateGraphInternal,
} = useNodeGraph()

// 编译状态
const compiledConfig = ref<BacktestTaskCreate | null>(null)
const compileModalVisible = ref(false)
const validating = ref(false)

// 初始化数据
if (props.initialData) {
  nodes.value = props.initialData.nodes
  edges.value = props.initialData.edges
}

// 处理节点拖拽开始
const handleNodeDragStart = (nodeType: NodeType) => {
  // NodePalette 组件会处理拖拽
  console.log('Drag start:', nodeType)
}

// 处理节点点击
const handleNodeClick = (node: GraphNode) => {
  selectedNode.value = node
  selectedEdge.value = null
}

// 处理连接线点击
const handleEdgeClick = (edge: GraphEdge) => {
  selectedEdge.value = edge
  selectedNode.value = null
}

// 处理节点变化
const handleNodesChange = (newNodes: GraphNode[]) => {
  nodes.value = newNodes
  emit('update:modelValue', { nodes: newNodes, edges: edges.value })
}

// 处理连接线变化
const handleEdgesChange = (newEdges: GraphEdge[]) => {
  edges.value = newEdges
  emit('update:modelValue', { nodes: nodes.value, edges: newEdges })
}

// 处理节点更新
const handleNodeUpdate = (updatedNode: GraphNode) => {
  updateNode(updatedNode)
  emit('update:modelValue', { nodes: nodes.value, edges: edges.value })
}

// 验证节点图
const validateGraph = async () => {
  validating.value = true
  try {
    // 前端验证逻辑在 useNodeGraph 中实现
    const result = validateGraphInternal()
    if (result.is_valid) {
      showToast('节点图配置有效')
    } else {
      showToast(`发现 ${result.errors.length} 个错误`, 'warning')
    }
  } finally {
    validating.value = false
  }
}

// 保存节点图
const saveGraph = async () => {
  try {
    const name = '我的回测配置' // TODO: 显示输入对话框
    const response = await nodeGraphApi.create({
      name,
      graph_data: { nodes: nodes.value, edges: edges.value },
    })
    // 更新 graphUuid
    if (response.data) {
      emit('update:graphUuid', response.data.uuid)
    }
    showToast('节点图已保存')
  } catch (error: any) {
    showToast(`保存失败: ${error.message}`, 'error')
  }
}

// 编译节点图
const compileGraph = async () => {
  try {
    // 先验证
    await validateGraph()
    if (!isValid.value) {
      return
    }

    // 如果没有graphUuid，先创建节点图
    let uuid = props.graphUuid
    if (!uuid) {
      const response = await nodeGraphApi.create({
        name: '回测配置',
        graph_data: { nodes: nodes.value, edges: edges.value },
      })
      uuid = response.data.uuid
    }

    // 调用后端编译 API
    const response = await nodeGraphApi.compile(uuid, {
      nodes: nodes.value,
      edges: edges.value,
    })
    compiledConfig.value = response.data.backtest_config
    compileModalVisible.value = true
    showToast('编译成功')
  } catch (error: any) {
    showToast(`编译失败: ${error.message}`, 'error')
  }
}

// 创建回测任务
const createBacktest = async () => {
  if (!compiledConfig.value) {
    return
  }

  try {
    // 导入backtestApi
    const { backtestApi } = await import('@/api/modules/backtest')

    // 调用 /api/backtest 创建任务
    const response = await backtestApi.create(compiledConfig.value)
    const backtestUuid = response.data.uuid

    showToast(`回测任务创建成功: ${backtestUuid}`)
    compileModalVisible.value = false

    // 跳转到回测详情页
    // TODO: 使用router跳转到详情页
    window.location.href = `/backtest/${backtestUuid}`
  } catch (error: any) {
    showToast(`创建回测任务失败: ${error.message}`, 'error')
  }
}
</script>

<style scoped>
.node-graph-editor {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #0f0f1a;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: #1a1a2e;
  border-bottom: 1px solid #2a2a3e;
}

.toolbar-spacer {
  flex: 1;
}

.btn-group {
  display: flex;
  gap: 4px;
}

.btn-group button {
  border-radius: 0;
}

.btn-group button:first-child {
  border-top-left-radius: 4px;
  border-bottom-left-radius: 4px;
}

.btn-group button:last-child {
  border-top-right-radius: 4px;
  border-bottom-right-radius: 4px;
}

.editor-content {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.node-palette {
  width: 220px;
  background: #1a1a2e;
  border-right: 1px solid #2a2a3e;
  overflow-y: auto;
}

.canvas-container {
  flex: 1;
  position: relative;
  background: #0f0f1a;
}

.property-panel {
  width: 320px;
  background: #1a1a2e;
  border-left: 1px solid #2a2a3e;
  overflow-y: auto;
}

.property-panel .empty-hint {
  padding: 40px 20px;
  text-align: center;
  color: #8a8a9a;
}

.validation-panel {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  max-height: 200px;
  background: #1a1a2e;
  border-top: 1px solid #2a2a3e;
  transform: translateY(100%);
  transition: transform 0.3s ease;
  z-index: 100;
}

.validation-panel.show {
  transform: translateY(0);
}

.compile-preview {
  background: #0f0f1a;
  padding: 16px;
  border-radius: 6px;
  max-height: 400px;
  overflow: auto;
  color: #a0d911;
  font-size: 12px;
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: #1890ff;
  border: 1px solid #1890ff;
  color: #ffffff;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-primary:hover:not(:disabled) {
  background: #40a9ff;
  border-color: #40a9ff;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: #1a1a2e;
  border: 1px solid #3a3a4e;
  color: #ffffff;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-secondary:hover:not(:disabled) {
  border-color: #1890ff;
  color: #1890ff;
}

.btn-secondary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 模态框样式 */
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
  max-width: 800px;
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
  padding: 20px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 16px 20px;
  border-top: 1px solid #2a2a3e;
}
</style>
