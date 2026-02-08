<template>
  <div
    class="node-graph-canvas"
    @mousemove="handleMouseMove"
    @mouseup="handleMouseUp"
  >
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

    <!-- 临时连接线 -->
    <svg
      v-if="tempConnection"
      class="temp-connection"
      :style="{ pointerEvents: 'none' }"
    >
      <path
        :d="tempConnectionPath"
        stroke="#1890ff"
        stroke-width="2"
        fill="none"
        stroke-dasharray="5,5"
      />
    </svg>

    <!-- 快速创建菜单 -->
    <NodeCreateMenu
      v-model:visible="showCreateMenu"
      :position="menuPosition"
      :source-port="sourcePort"
      :available-components="availableComponents"
      @close="closeCreateMenu"
      @select="handleSelectComponent"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, markRaw, watch, computed, onMounted, onUnmounted } from 'vue'
import { VueFlow, useVueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { MiniMap } from '@vue-flow/minimap'
import type { Node, Edge, Connection, NodeTypes } from '@vue-flow/core'
import type { GraphNode, GraphEdge, NodeType, NodePort } from './types'
import NodeComponent from './NodeComponent.vue'
import NodeCreateMenu from './NodeCreateMenu.vue'
import { NODE_TYPE_LABELS, NodeType as NodeTypeEnum } from './types'

interface Props {
  nodes: GraphNode[]
  edges: GraphEdge[]
  availableComponents?: {
    strategies: any[]
    selectors: any[]
    sizers: any[]
    risks: any[]
  }
}

const props = withDefaults(defineProps<Props>(), {
  nodes: () => [],
  edges: () => [],
  availableComponents: () => ({ strategies: [], selectors: [], sizers: [], risks: [] })
})
const emit = defineEmits(['node-click', 'edge-click', 'nodes-change', 'edges-change', 'connection-start'])

// 本地响应式节点和边数据
const localNodes = ref<GraphNode[]>([])
const localEdges = ref<GraphEdge[]>([])

// 初始化
if (props.nodes && props.nodes.length > 0) {
  localNodes.value = [...props.nodes]
}
if (props.edges && props.edges.length > 0) {
  localEdges.value = [...props.edges]
}

// 监听props变化同步到local
watch(() => props.nodes, (newNodes) => {
  if (newNodes) {
    localNodes.value = [...newNodes]
  }
}, { deep: true })

watch(() => props.edges, (newEdges) => {
  if (newEdges) {
    localEdges.value = [...newEdges]
  }
}, { deep: true })

// 监听节点上的连接开始事件
watch(() => localNodes.value, () => {
  // 通过VueFlow事件总线处理
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
const { onNodesChange, onEdgesChange, onConnect: onConnectVueFlow, getNodes, getEdges, project, vueFlowRef } = useVueFlow()

// 监听节点变化并emit给父组件
onNodesChange((params) => {
  if (params.nodes) {
    localNodes.value = params.nodes as GraphNode[]
    emit('nodes-change', localNodes.value)
  }
})

// 监听边变化并emit给父组件
onEdgesChange((params) => {
  if (params.edges) {
    localEdges.value = params.edges as GraphEdge[]
    emit('edges-change', localEdges.value)
  }
})

// 快速创建菜单状态
const showCreateMenu = ref(false)
const menuPosition = ref({ x: 0, y: 0 })
const sourcePort = ref<{
  nodeId: string
  port: NodePort
  handleType: 'source' | 'target'
  nodeType: NodeType
} | undefined>(undefined)

// 临时连接状态
const tempConnection = ref<{
  startX: number
  startY: number
  endX: number
  endY: number
} | undefined>(undefined)

// 临时连接线路径
const tempConnectionPath = computed(() => {
  if (!tempConnection.value) return ''

  const { startX, startY, endX, endY } = tempConnection.value
  const dx = Math.abs(endX - startX) * 0.5

  return `M ${startX} ${startY} C ${startX + dx} ${startY}, ${endX - dx} ${endY}, ${endX} ${endY}`
})

// 事件监听器处理函数
const handleConnectionStartEvent = (event: Event) => {
  const customEvent = event as CustomEvent
  const data = customEvent.detail
  handleNodeConnectionStart(data)
}

// 挂载和卸载事件监听
onMounted(() => {
  document.addEventListener('node-connection-start', handleConnectionStartEvent)
})

onUnmounted(() => {
  document.removeEventListener('node-connection-start', handleConnectionStartEvent)
})

// 监听NodeComponent的connection-start事件
const handleNodeConnectionStart = (data: {
  nodeId: string
  port: NodePort
  handleType: 'source' | 'target'
  nodeType: NodeType
}) => {
  sourcePort.value = data

  // 获取源端口位置
  const nodes = getNodes()
  const sourceNode = nodes.find(n => n.id === data.nodeId)
  if (!sourceNode) return

  // 计算端口位置
  const position = sourceNode.position
  const isSource = data.handleType === 'source'
  const portOffset = isSource ? 180 : -20 // 节点宽度约320px，端口在左右两侧
  const startX = position.x + (isSource ? 320 : 0)
  const startY = position.y + 50

  tempConnection.value = {
    startX,
    startY,
    endX: startX,
    endY: startY
  }

  emit('connection-start', data)
}

// 处理鼠标移动
const handleMouseMove = (event: MouseEvent) => {
  if (!tempConnection.value || !vueFlowRef.value) return

  // 转换鼠标坐标到画布坐标
  const { x, y } = project({ x: event.clientX, y: event.clientY })

  tempConnection.value.endX = x
  tempConnection.value.endY = y
}

// 处理鼠标释放
const handleMouseUp = (event: MouseEvent) => {
  if (!tempConnection.value) return

  // 清除临时连接
  tempConnection.value = undefined

  // 检查是否在节点上释放（正常连接）
  const target = event.target as HTMLElement
  const nodeElement = target.closest('.vue-flow__node')

  if (nodeElement) {
    // 这是正常的节点连接，让VueFlow处理
    return
  }

  // 在空白处释放，显示快速创建菜单
  if (sourcePort.value && sourcePort.value.handleType === 'source') {
    showCreateMenu.value = true
    menuPosition.value = {
      x: event.clientX,
      y: event.clientY
    }
  }
}

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
  // 验证连接规则
  // TODO: 添加验证逻辑
  onConnectVueFlow(connection)
}

// 处理拖拽放置
const handleDrop = (event: DragEvent) => {
  event.preventDefault()

  // 首先尝试获取组件数据（从组件面板拖拽）
  const componentData = event.dataTransfer?.getData('application/json')
  if (componentData) {
    try {
      const { type, component } = JSON.parse(componentData)

      // 直接使用 event.target 获取 VueFlow 容器
      const target = event.currentTarget as HTMLElement
      if (!target) return

      // 获取容器边界框
      const rect = target.getBoundingClientRect()

      // 计算相对于容器的坐标
      const relativeX = event.clientX - rect.left
      const relativeY = event.clientY - rect.top

      // 创建新节点，节点左上角对准鼠标在容器中的位置
      const newNode: GraphNode = {
        id: `node-${Date.now()}`,
        type: type as NodeType,
        position: { x: relativeX, y: relativeY },
        data: {
          label: component.name,
          config: {
            component_uuid: component.uuid
          },
          componentUuid: component.uuid,
          description: component.description
        },
      }

      // 确保 localNodes.value 是数组
      if (!Array.isArray(localNodes.value)) {
        localNodes.value = []
      }

      // 添加节点
      localNodes.value = [...localNodes.value, newNode]
      emit('nodes-change', localNodes.value)
      return
    } catch (e) {
      console.error('Failed to parse component data:', e)
    }
  }
}

// 处理拖拽悬停
const handleDragOver = (event: DragEvent) => {
  event.preventDefault()
  event.dataTransfer!.dropEffect = 'move'
}

// 关闭创建菜单
const closeCreateMenu = () => {
  showCreateMenu.value = false
  sourcePort.value = undefined
}

// 处理组件选择
const handleSelectComponent = (data: {
  component: any
  nodeType: string
  sourcePort?: any
}) => {
  if (!data.sourcePort) return

  // 计算新节点位置（在鼠标位置）
  const { x, y } = project({ x: menuPosition.value.x, y: menuPosition.value.y })

  // 创建新节点
  const newNode: GraphNode = {
    id: `node-${Date.now()}`,
    type: data.nodeType as NodeType,
    position: { x: x - 160, y: y - 50 }, // 居中显示
    data: {
      label: data.component.name,
      config: {
        component_uuid: data.component.uuid
      },
      componentUuid: data.component.uuid,
      description: data.component.description
    }
  }

  // 创建连接
  const newEdge: GraphEdge = {
    id: `edge-${Date.now()}`,
    source: data.sourcePort.nodeId,
    target: newNode.id,
    sourceHandle: data.sourcePort.port.name,
    animated: true
  }

  // 更新节点和边
  localNodes.value = [...localNodes.value, newNode]
  localEdges.value = [...localEdges.value, newEdge]

  emit('nodes-change', localNodes.value)
  emit('edges-change', localEdges.value)

  closeCreateMenu()
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
    // 移除默认样式，使用自定义组件样式
    background: transparent;
    border: none;
    box-shadow: none;
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

  .temp-connection {
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
    z-index: 100;
  }
}
</style>
