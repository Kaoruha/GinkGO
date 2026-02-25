<template>
  <div class="page-container">
    <PageHeader
      title="遗传算法优化"
      description="模拟生物进化进行参数搜索，适合高维参数空间。可能陷入局部最优。"
    />
    <a-card title="优化配置" class="config-card">
      <a-form layout="inline">
        <a-form-item label="策略选择">
          <a-select v-model:value="config.strategyId" style="width: 200px">
            <a-select-option v-for="s in strategyList" :key="s.id" :value="s.id">{{ s.name }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="种群大小">
          <a-input-number v-model:value="config.populationSize" :min="10" :max="200" style="width: 80px" />
        </a-form-item>
        <a-form-item label="迭代次数">
          <a-input-number v-model:value="config.generations" :min="10" :max="500" style="width: 80px" />
        </a-form-item>
        <a-form-item label="变异率">
          <a-input-number v-model:value="config.mutationRate" :min="0.01" :max="0.5" :step="0.01" style="width: 80px" />
        </a-form-item>
        <a-form-item>
          <a-button type="primary" @click="runOptimization" :loading="loading">开始优化</a-button>
        </a-form-item>
      </a-form>
    </a-card>
    <a-card title="优化结果" class="result-card">
      <template v-if="result">
        <a-row :gutter="16" style="margin-bottom: 16px">
          <a-col :span="6"><StatCard title="总迭代" :value="result.generations" /></a-col>
          <a-col :span="6"><StatCard title="最佳收益" :value="result.best_fitness" type="percent" /></a-col>
          <a-col :span="6"><StatCard title="收敛代数" :value="result.convergence_gen" /></a-col>
          <a-col :span="6"><StatCard title="最优参数" :value="result.best_params" /></a-col>
        </a-row>
        <a-table :columns="genColumns" :dataSource="result.history" :rowKey="(_, i) => `gen-${i}`" :pagination="false" size="small" />
      </template>
      <a-empty v-else />
    </a-card>
  </div>
</template>
<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { componentsApi, optimizationApi } from '@/api'
import type { GeneticOptimizerResult } from '@/api'
import { PageHeader } from '@/components/layout'
import { StatCard } from '@/components/common'

const loading = ref(false)
const strategyList = ref<any[]>([])
const result = ref<GeneticOptimizerResult | null>(null)
const config = reactive({ strategyId: '', populationSize: 50, generations: 100, mutationRate: 0.1 })

const genColumns = [
  { title: '代数', dataIndex: 'generation', width: 80 },
  { title: '最佳适应度', dataIndex: 'best_fitness', width: 120 },
  { title: '平均适应度', dataIndex: 'avg_fitness', width: 120 },
  { title: '多样性', dataIndex: 'diversity', width: 100 },
]

const fetchStrategyList = async () => {
  try { strategyList.value = ((await componentsApi.getStrategies()) || []).map((f: any) => ({ id: f.name || f.uuid, name: f.name || f.uuid })) } catch {}
}

const runOptimization = async () => {
  if (!config.strategyId) { message.warning('请选择策略'); return }
  loading.value = true
  try { result.value = await optimizationApi.genetic({ strategy_id: config.strategyId, params: {}, population_size: config.populationSize, generations: config.generations, mutation_rate: config.mutationRate }); message.success('完成') }
  catch { message.error('失败') }
  finally { loading.value = false }
}

onMounted(() => { fetchStrategyList() })
</script>
