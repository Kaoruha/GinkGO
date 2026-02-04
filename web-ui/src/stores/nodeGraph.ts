/**
 * 节点图 Pinia Store
 * 管理节点图的全局状态
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { GraphData, ValidationResult } from '@/components/node-graph/types'
import { nodeGraphApi } from '@/api/modules/nodeGraph'

export const useNodeGraphStore = defineStore('nodeGraph', () => {
  // 当前编辑的节点图UUID
  const currentGraphUuid = ref<string | null>(null)

  // 当前节点图数据
  const currentGraphData = ref<GraphData>({ nodes: [], edges: [] })

  // 是否已加载
  const isLoaded = computed(() => currentGraphUuid.value !== null)

  // 加载节点图
  const loadGraph = async (uuid: string) => {
    try {
      const response = await nodeGraphApi.get(uuid)
      const result = response.data
      currentGraphUuid.value = result.uuid
      currentGraphData.value = result.graph_data
      return result
    } catch (error: any) {
      console.error('加载节点图失败:', error)
      throw error
    }
  }

  // 保存节点图
  const saveGraph = async (name: string, description?: string) => {
    try {
      if (currentGraphUuid.value) {
        // 更新现有节点图
        const response = await nodeGraphApi.update(currentGraphUuid.value, {
          name,
          description,
          graph_data: currentGraphData.value,
        })
        return response.data
      } else {
        // 创建新节点图
        const response = await nodeGraphApi.create({
          name,
          description,
          graph_data: currentGraphData.value,
        })
        currentGraphUuid.value = response.data.uuid
        return response.data
      }
    } catch (error: any) {
      console.error('保存节点图失败:', error)
      throw error
    }
  }

  // 另存为
  const saveAs = async (name: string) => {
    try {
      if (currentGraphUuid.value) {
        const response = await nodeGraphApi.duplicate(currentGraphUuid.value, name)
        const result = response.data
        currentGraphUuid.value = result.uuid
        currentGraphData.value = result.graph_data
        return result
      }
      throw new Error('没有可复制的节点图')
    } catch (error: any) {
      console.error('另存为失败:', error)
      throw error
    }
  }

  // 验证节点图
  const validateGraph = async (): Promise<ValidationResult> => {
    try {
      if (!currentGraphUuid.value) {
        throw new Error('没有可验证的节点图')
      }
      const response = await nodeGraphApi.validate(
        currentGraphUuid.value,
        currentGraphData.value
      )
      return response.data
    } catch (error: any) {
      console.error('验证节点图失败:', error)
      throw error
    }
  }

  // 编译节点图
  const compileGraph = async () => {
    try {
      if (!currentGraphUuid.value) {
        throw new Error('没有可编译的节点图')
      }
      const response = await nodeGraphApi.compile(
        currentGraphUuid.value,
        currentGraphData.value
      )
      return response.data
    } catch (error: any) {
      console.error('编译节点图失败:', error)
      throw error
    }
  }

  // 从回测创建节点图
  const createFromBacktest = async (backtestUuid: string) => {
    try {
      const response = await nodeGraphApi.fromBacktest(backtestUuid)
      const result = response.data
      currentGraphUuid.value = result.uuid
      currentGraphData.value = result.graph_data
      return result
    } catch (error: any) {
      console.error('从回测创建节点图失败:', error)
      throw error
    }
  }

  // 清空当前节点图
  const clearGraph = () => {
    currentGraphUuid.value = null
    currentGraphData.value = { nodes: [], edges: [] }
  }

  // 更新节点图数据
  const updateGraphData = (data: GraphData) => {
    currentGraphData.value = data
  }

  return {
    // 状态
    currentGraphUuid,
    currentGraphData,
    isLoaded,

    // 操作
    loadGraph,
    saveGraph,
    saveAs,
    validateGraph,
    compileGraph,
    createFromBacktest,
    clearGraph,
    updateGraphData,
  }
})
