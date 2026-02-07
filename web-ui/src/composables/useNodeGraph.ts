/**
 * 节点图操作 Composable
 * 提供节点图的增删改查、验证、撤销/重做等操作
 */

import { ref, computed } from 'vue'
import type { Ref } from 'vue'
import {
  GraphNode,
  GraphEdge,
  GraphData,
  NodeType,
  ValidationResult,
  ValidationError,
} from '@/components/node-graph/types'
import { canConnect } from '@/components/node-graph/types'

export function useNodeGraph(initialData?: GraphData) {
  // 节点列表
  const nodes: Ref<GraphNode[]> = ref(initialData?.nodes || [])

  // 连接线列表
  const edges: Ref<GraphEdge[]> = ref(initialData?.edges || [])

  // 选中的节点
  const selectedNode: Ref<GraphNode | null> = ref(null)

  // 选中的连接线
  const selectedEdge: Ref<GraphEdge | null> = ref(null)

  // 撤销/重做历史
  interface GraphCommand {
    execute(): void
    undo(): void
  }

  const undoStack: GraphCommand[] = []
  const redoStack: GraphCommand[] = []

  // 验证结果
  const validationResult: Ref<ValidationResult | null> = ref(null)

  // 节点图是否有效
  const isValid = computed(() => {
    return validationResult.value?.is_valid ?? false
  })

  // 是否可以撤销
  const canUndo = computed(() => undoStack.length > 0)

  // 是否可以重做
  const canRedo = computed(() => redoStack.length > 0)

  // ==================== 节点操作 ====================

  /**
   * 添加节点
   */
  const addNode = (node: GraphNode) => {
    const command: GraphCommand = {
      execute: () => {
        nodes.value.push(node)
      },
      undo: () => {
        removeNodeById(node.id)
      },
    }
    executeCommand(command)
  }

  /**
   * 移除节点
   */
  const removeNode = (nodeId: string) => {
    const nodeIndex = nodes.value.findIndex((n) => n.id === nodeId)
    if (nodeIndex === -1) return

    const removedNode = nodes.value[nodeIndex]
    const relatedEdges = edges.value.filter((e) => e.source === nodeId || e.target === nodeId)

    const command: GraphCommand = {
      execute: () => {
        // 删除节点
        nodes.value.splice(nodeIndex, 1)
        // 删除相关连接线
        edges.value = edges.value.filter((e) => e.source !== nodeId && e.target !== nodeId)
      },
      undo: () => {
        // 恢复节点
        nodes.value.splice(nodeIndex, 0, removedNode)
        // 恢复连接线
        edges.value.push(...relatedEdges)
      },
    }
    executeCommand(command)
  }

  /**
   * 移除节点（按ID）
   */
  const removeNodeById = (nodeId: string) => {
    const index = nodes.value.findIndex((n) => n.id === nodeId)
    if (index !== -1) {
      nodes.value.splice(index, 1)
    }
  }

  /**
   * 更新节点
   */
  const updateNode = (node: GraphNode) => {
    const index = nodes.value.findIndex((n) => n.id === node.id)
    if (index !== -1) {
      const oldNode = nodes.value[index]
      const command: GraphCommand = {
        execute: () => {
          nodes.value[index] = node
        },
        undo: () => {
          nodes.value[index] = oldNode
        },
      }
      executeCommand(command)
    }
  }

  // ==================== 连接操作 ====================

  /**
   * 添加连接线
   */
  const addEdge = (edge: GraphEdge) => {
    const command: GraphCommand = {
      execute: () => {
        edges.value.push(edge)
      },
      undo: () => {
        removeEdgeById(edge.id)
      },
    }
    executeCommand(command)
  }

  /**
   * 移除连接线
   */
  const removeEdge = (edgeId: string) => {
    const index = edges.value.findIndex((e) => e.id === edgeId)
    if (index === -1) return

    const removedEdge = edges.value[index]

    const command: GraphCommand = {
      execute: () => {
        edges.value.splice(index, 1)
      },
      undo: () => {
        edges.value.splice(index, 0, removedEdge)
      },
    }
    executeCommand(command)
  }

  /**
   * 移除连接线（按ID）
   */
  const removeEdgeById = (edgeId: string) => {
    const index = edges.value.findIndex((e) => e.id === edgeId)
    if (index !== -1) {
      edges.value.splice(index, 1)
    }
  }

  // ==================== 验证操作 ====================

  /**
   * 验证节点图
   */
  const validate = (): ValidationResult => {
    const errors: ValidationError[] = []
    const warnings: string[] = []

    // 1. 验证必须有且只有一个 ENGINE 节点
    const engineNodes = nodes.value.filter((n) => n.type === NodeType.ENGINE)
    if (engineNodes.length === 0) {
      errors.push({
        message: '必须有一个 ENGINE 节点',
        severity: 'error',
      })
    } else if (engineNodes.length > 1) {
      errors.push({
        message: '只能有一个 ENGINE 节点',
        severity: 'error',
      })
    }

    // 2. 验证至少有一个 PORTFOLIO 节点
    const portfolioNodes = nodes.value.filter((n) => n.type === NodeType.PORTFOLIO)
    if (portfolioNodes.length === 0) {
      errors.push({
        message: '至少需要一个 PORTFOLIO 节点',
        severity: 'error',
      })
    }

    // 3. 验证 ENGINE 必须连接到至少一个 PORTFOLIO
    if (engineNodes.length === 1) {
      const connectedToPortfolio = edges.value.some(
        (e) => e.source === engineNodes[0].id && portfolioNodes.some((p) => p.id === e.target)
      )
      if (!connectedToPortfolio) {
        errors.push({
          node_id: engineNodes[0].id,
          message: 'ENGINE 节点必须连接到至少一个 PORTFOLIO 节点',
          severity: 'error',
        })
      }
    }

    // 4. 验证连接规则
    for (const edge of edges.value) {
      const sourceNode = nodes.value.find((n) => n.id === edge.source)
      const targetNode = nodes.value.find((n) => n.id === edge.target)
      if (!sourceNode || !targetNode) continue

      if (!canConnect(sourceNode.type as NodeType, targetNode.type as NodeType)) {
        errors.push({
          edge_id: edge.id,
          message: `${sourceNode.type} 节点不能连接到 ${targetNode.type} 节点`,
          severity: 'error',
        })
      }
    }

    // 5. 验证循环依赖
    const cycleEdges = detectCycles()
    cycleEdges.forEach((edge) => {
      errors.push({
        edge_id: edge.id,
        message: '检测到循环依赖',
        severity: 'error',
      })
    })

    // 6. 验证节点参数
    nodes.value.forEach((node) => {
      const nodeErrors = validateNode(node)
      nodeErrors.forEach((error) => {
        errors.push({
          node_id: node.id,
          message: error,
          severity: 'error',
        })
      })
    })

    const result: ValidationResult = {
      is_valid: errors.length === 0,
      errors,
      warnings,
    }

    validationResult.value = result
    return result
  }

  /**
   * 验证单个节点参数
   */
  const validateNode = (node: GraphNode): string[] => {
    const errors: string[] = []
    const config = node.data.config as any

    switch (node.type) {
      case NodeType.ENGINE:
        if (!config.start_date) errors.push('必须配置开始日期')
        if (!config.end_date) errors.push('必须配置结束日期')
        break
      case NodeType.PORTFOLIO:
        if (!config.portfolio_uuid) errors.push('必须选择投资组合')
        break
      case NodeType.STRATEGY:
      case NodeType.SELECTOR:
      case NodeType.SIZER:
      case NodeType.RISK_MANAGEMENT:
      case NodeType.ANALYZER:
        if (!config.component_uuid) errors.push('必须选择组件')
        break
    }

    return errors
  }

  /**
   * 检测循环依赖
   */
  const detectCycles = (): GraphEdge[] => {
    const graph = new Map<string, string[]>()
    edges.value.forEach((edge) => {
      if (!graph.has(edge.source)) {
        graph.set(edge.source, [])
      }
      graph.get(edge.source)!.push(edge.target)
    })

    const visited = new Set<string>()
    const recursionStack = new Set<string>()
    const cycleEdges: GraphEdge[] = []

    const dfs = (nodeId: string, path: string[]): boolean => {
      if (recursionStack.has(nodeId)) {
        // 找到环
        const cycleStartIndex = Array.from(recursionStack).indexOf(nodeId)
        for (let i = cycleStartIndex; i < path.length; i++) {
          const edge = edges.value.find(
            (e) => e.source === path[i] && e.target === path[i + 1]
          )
          if (edge) cycleEdges.push(edge)
        }
        return true
      }

      if (visited.has(nodeId)) {
        return false
      }

      visited.add(nodeId)
      recursionStack.add(nodeId)

      const neighbors = graph.get(nodeId) || []
      for (const neighbor of neighbors) {
        path.push(nodeId)
        if (dfs(neighbor, path)) {
          return true
        }
        path.pop()
      }

      recursionStack.delete(nodeId)
      return false
    }

    nodes.value.forEach((node) => {
      if (!visited.has(node.id)) {
        dfs(node.id, [])
      }
    })

    return cycleEdges
  }

  // ==================== 撤销/重做 ====================

  /**
   * 执行命令
   */
  const executeCommand = (command: GraphCommand) => {
    command.execute()
    undoStack.push(command)
    redoStack.length = 0 // 清空 redo 栈

    // 限制历史记录为 20 步
    if (undoStack.length > 20) {
      undoStack.shift()
    }
  }

  /**
   * 撤销
   */
  const undo = () => {
    const command = undoStack.pop()
    if (command) {
      command.undo()
      redoStack.push(command)
    }
  }

  /**
   * 重做
   */
  const redo = () => {
    const command = redoStack.pop()
    if (command) {
      command.execute()
      undoStack.push(command)
    }
  }

  // ==================== 工具函数 ====================

  /**
   * 清空所有数据
   */
  const clear = () => {
    nodes.value = []
    edges.value = []
    selectedNode.value = null
    selectedEdge.value = null
    validationResult.value = null
    undoStack.length = 0
    redoStack.length = 0
  }

  /**
   * 加载节点图数据
   */
  const loadGraphData = (data: GraphData) => {
    clear()
    nodes.value = data.nodes
    edges.value = data.edges
  }

  /**
   * 获取节点图数据
   */
  const getGraphData = (): GraphData => {
    return {
      nodes: nodes.value,
      edges: edges.value,
    }
  }

  return {
    // 状态
    nodes,
    edges,
    selectedNode,
    selectedEdge,
    isValid,
    validationResult,
    canUndo,
    canRedo,

    // 节点操作
    addNode,
    removeNode,
    removeNodeById,
    updateNode,

    // 连接操作
    addEdge,
    removeEdge,
    removeEdgeById,

    // 验证
    validate,
    validateGraph: validate, // 别名，保持一致性

    // 撤销/重做
    undo,
    redo,

    // 工具
    clear,
    loadGraphData,
    getGraphData,
  }
}
