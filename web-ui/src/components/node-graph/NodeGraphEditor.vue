<template>
  <div class="node-graph-editor">
    <!-- 工具栏 -->
    <div class="toolbar">
      <a-button-group>
        <a-button @click="validateGraph" :loading="validating">
          <template #icon><CheckOutlined /></template>
          验证
        </a-button>
        <a-button @click="saveGraph" :disabled="!isValid">
          <template #icon><SaveOutlined /></template>
          保存
        </a-button>
        <a-button @click="compileGraph" :disabled="!isValid">
          <template #icon><CodeOutlined /></template>
          编译
        </a-button>
        <a-button @click="createBacktest" type="primary" :disabled="!compiledConfig">
          <template #icon><PlayCircleOutlined /></template>
          创建回测任务
        </a-button>
      </a-button-group>

      <div class="toolbar-spacer"></div>

      <a-button-group>
        <a-button @click="undo" :disabled="!canUndo">
          <template #icon><UndoOutlined /></template>
          撤销
        </a-button>
        <a-button @click="redo" :disabled="!canRedo">
          <template #icon><RedoOutlined /></template>
          重做
        </a-button>
      </a-button-group>
    </div>

    <!-- 主内容区 -->
    <div class="editor-content">
      <!-- 左侧节点选择面板 -->
      <div class="node-palette">
        <NodePalette @node-drag-start="handleNodeDragStart" />
      </div>

      <!-- 中间画布 -->
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

      <!-- 右侧属性面板 -->
      <div class="property-panel">
        <NodePropertyPanel
          v-if="selectedNode"
          :node="selectedNode"
          @node-update="handleNodeUpdate"
        />
        <div v-else class="empty-hint">
          <p>选择一个节点以编辑其属性</p>
        </div>
      </div>
    </div>

    <!-- 验证结果展示 -->
    <div v-if="validationResult" class="validation-panel" :class="{ show: true }">
      <GraphValidator
        :validation-result="validationResult"
        @close="validationResult = null"
      />
    </div>

    <!-- 编译预览弹窗 -->
    <a-modal
      v-model:open="compileModalVisible"
      title="编译结果"
      width="800px"
      :footer="null"
    >
      <pre class="compile-preview">{{ JSON.stringify(compiledConfig, null, 2) }}</pre>
      <template #footer>
        <a-button @click="compileModalVisible = false">关闭</a-button>
        <a-button v-if="compiledConfig" type="primary" @click="createBacktest">创建回测任务</a-button>
      </template>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { message } from 'ant-design-vue'
import {
  CheckOutlined,
  SaveOutlined,
  CodeOutlined,
  PlayCircleOutlined,
  UndoOutlined,
  RedoOutlined,
} from '@ant-design/icons-vue'
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
      message.success('节点图配置有效')
    } else {
      message.warning(`发现 ${result.errors.length} 个错误`)
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
    message.success('节点图已保存')
  } catch (error: any) {
    message.error(`保存失败: ${error.message}`)
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
    message.success('编译成功')
  } catch (error: any) {
    message.error(`编译失败: ${error.message}`)
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

    message.success(`回测任务创建成功: ${backtestUuid}`)
    compileModalVisible.value = false

    // 跳转到回测详情页
    // TODO: 使用router跳转到详情页
    window.location.href = `/backtest/${backtestUuid}`
  } catch (error: any) {
    message.error(`创建回测任务失败: ${error.message}`)
  }
}
</script>

<style scoped lang="less">
.node-graph-editor {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #f5f5f5;

  .toolbar {
    display: flex;
    align-items: center;
    padding: 12px 16px;
    background: #fff;
    border-bottom: 1px solid #e8e8e8;
    gap: 12px;

    .toolbar-spacer {
      flex: 1;
    }
  }

  .editor-content {
    display: flex;
    flex: 1;
    overflow: hidden;

    .node-palette {
      width: 220px;
      background: #fff;
      border-right: 1px solid #e8e8e8;
      overflow-y: auto;
    }

    .canvas-container {
      flex: 1;
      position: relative;
      background: #fafafa;
    }

    .property-panel {
      width: 320px;
      background: #fff;
      border-left: 1px solid #e8e8e8;
      overflow-y: auto;

      .empty-hint {
        padding: 40px 20px;
        text-align: center;
        color: #999;
      }
    }
  }

  .validation-panel {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    max-height: 200px;
    background: #fff;
    border-top: 1px solid #e8e8e8;
    transform: translateY(100%);
    transition: transform 0.3s ease;
    z-index: 100;

    &.show {
      transform: translateY(0);
    }
  }

  .compile-preview {
    background: #f5f5f5;
    padding: 16px;
    border-radius: 4px;
    max-height: 400px;
    overflow: auto;
  }
}
</style>
