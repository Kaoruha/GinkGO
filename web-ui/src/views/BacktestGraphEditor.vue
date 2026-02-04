<template>
  <div class="backtest-graph-editor-page">
    <NodeGraphEditor
      v-model="graphData"
      :graph-uuid="graphUuid"
      @save="handleSave"
      @compile="handleCompile"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import NodeGraphEditor from '@/components/node-graph/NodeGraphEditor.vue'
import type { GraphData } from '@/components/node-graph/types'
import { useNodeGraphStore } from '@/stores/nodeGraph'
import { message } from 'ant-design-vue'

const route = useRoute()
const nodeGraphStore = useNodeGraphStore()

// 节点图UUID（从路由参数获取）
const graphUuid = ref<string | undefined>(route.params.uuid as string)

// 节点图数据
const graphData = ref<GraphData>({ nodes: [], edges: [] })

// 初始化
onMounted(async () => {
  if (graphUuid.value) {
    try {
      await nodeGraphStore.loadGraph(graphUuid.value)
      graphData.value = nodeGraphStore.currentGraphData
    } catch (error: any) {
      message.error(`加载节点图失败: ${error.message}`)
    }
  }
})

// 处理保存
const handleSave = async (data: GraphData) => {
  try {
    await nodeGraphStore.saveGraph('回测配置', '通过节点图配置的回测任务')
    message.success('保存成功')
  } catch (error: any) {
    message.error(`保存失败: ${error.message}`)
  }
}

// 处理编译
const handleCompile = async (data: GraphData) => {
  try {
    const result = await nodeGraphStore.compileGraph()
    return result
  } catch (error: any) {
    message.error(`编译失败: ${error.message}`)
    throw error
  }
}
</script>

<style scoped lang="less">
.backtest-graph-editor-page {
  width: 100%;
  height: 100vh;
  overflow: hidden;
}
</style>
