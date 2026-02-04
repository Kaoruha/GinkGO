<template>
  <div class="node-graph-canvas">
    <VueFlow
      v-model:nodes="localNodes"
      v-model:edges="localEdges"
      :node-types="nodeTypes"
      :default-viewport="{ zoom: 1, x: 0, y: 0 }"
      :min-zoom="0.1"
      :max-zoom="2"
      fit-view-on-init
      @node-click="handleNodeClick"
      @edge-click="handleEdgeClick"
      @connect="handleConnect"
      @drop="handleDrop"
      @dragover="handleDragOver"
    >
      <Background />
      <Controls />
      <MiniMap />
    </VueFlow>
  </div>
</template>

<script setup lang="ts">
import { ref, markRaw, watch } from 'vue'
import { VueFlow, useVueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import type { Node, Edge, Connection, NodeTypes } from '@vue-flow/core'
import type { GraphNode, GraphEdge, NodeType } from './types'
import NodeComponent from './NodeComponent.vue'
import { NODE_TYPE_LABELS } from './types'

interface Props {
  nodes: GraphNode[]
  edges: GraphEdge[]
}

const props = defineProps<Props>()
const emit = defineEmits(['node-click', 'edge-click', 'nodes-change', 'edges-change'])

// 本地响应式节点和边数据
const localNodes = ref<GraphNode[]>([...props.nodes])
const localEdges = ref<GraphEdge[]>([...props.edges])

// 监听props变化同步到local
watch(() => props.nodes, (newNodes) => {
  localNodes.value = [...newNodes]
}, { deep: true })

watch(() => props.edges, (newEdges) => {
  localEdges.value = [...newEdges]
}, { deep: true })

// 注册所有节点类型
const nodeTypes: NodeTypes = {
  engine: markRaw(NodeComponent),
  feeder: markRaw(NodeComponent),
  broker: markRaw(NodeComponent),
  portfolio: markRaw(NodeComponent),
  strategy: markRaw(NodeComponent),
  selector: markRaw(NodeComponent),
  sizer: markRaw(NodeComponent),
  risk: markRaw(NodeComponent),
  analyzer: markRaw(NodeComponent),
}

// VueFlow 实例
const { onNodesChange, onEdgesChange, onConnect: onConnectVueFlow } = useVueFlow()

// 监听节点变化并emit给父组件
onNodesChange((params) => {
  emit('nodes-change', params.nodes)
})

// 监听边变化并emit给父组件
onEdgesChange((params) => {
  emit('edges-change', params.edges)
})

// 处理节点点击
const handleNodeClick = (node: Node) => {
  emit('node-click', node as GraphNode)
}

// 处理连接线点击
const handleEdgeClick = (edge: Edge) => {
  emit('edge-click', edge as GraphEdge)
}

// 处理连接
const handleConnect = (connection: Connection) => {
  // 验证连接规则（这里可以调用验证逻辑）
  // 暂时允许所有连接
  onConnectVueFlow(connection)
}

// 处理拖拽放置
const handleDrop = (event: DragEvent) => {
  event.preventDefault()

  // 从dataTransfer获取节点类型
  const nodeType = event.dataTransfer?.getData('application/vue-flow') as NodeType
  if (!nodeType) {
    return
  }

  // 获取画布坐标
  const canvas = event.currentTarget as HTMLElement
  const rect = canvas.getBoundingClientRect()
  const x = event.clientX - rect.left
  const y = event.clientY - rect.top

  // 创建新节点
  const newNode: GraphNode = {
    id: `node-${Date.now()}`,
    type: nodeType,
    position: { x, y },
    data: {
      label: NODE_TYPE_LABELS[nodeType],
      config: {},
    },
  }

  // 添加节点
  localNodes.value = [...localNodes.value, newNode]
  emit('nodes-change', localNodes.value)
}

// 处理拖拽悬停
const handleDragOver = (event: DragEvent) => {
  event.preventDefault()
}
</script>

<style scoped lang="less">
.node-graph-canvas {
  width: 100%;
  height: 100%;
  position: relative;

  :deep(.vue-flow) {
    background: #fafafa;
  }

  :deep(.vue-flow__node) {
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    transition: box-shadow 0.2s;

    &:hover {
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
    }

    &.selected {
      box-shadow: 0 0 0 2px #1890ff;
    }
  }

  :deep(.vue-flow__edge) {
    stroke: #b1b1b7;
    stroke-width: 2;

    &.selected {
      stroke: #1890ff;
    }

    &.invalid {
      stroke: #ff4d4f;
      stroke-dasharray: 5 5;
    }
  }
}
</style>
