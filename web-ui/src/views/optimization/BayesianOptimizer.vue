<template>
  <div class="page-container">
    <PageHeader
      title="贝叶斯优化"
      description="基于概率模型的智能搜索，利用已有结果推断下一组参数。计算效率最高。"
    />
    <a-card title="优化配置" class="config-card">
      <a-form layout="inline">
        <a-form-item label="策略选择">
          <a-select v-model:value="config.strategyId" style="width: 200px">
            <a-select-option v-for="s in strategyList" :key="s.id" :value="s.id">{{ s.name }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="迭代次数">
          <a-input-number v-model:value="config.nIterations" :min="10" :max="200" style="width: 80px" />
        </a-form-item>
        <a-form-item label="初始点数">
          <a-input-number v-model:value="config.nInitial" :min="3" :max="20" style="width: 80px" />
        </a-form-item>
        <a-form-item>
          <a-button type="primary" @click="runOptimization" :loading="loading">开始优化</a-button>
        </a-form-item>
      </a-form>
    </a-card>
    <a-card title="优化结果" class="result-card">
      <template v-if="result">
        <a-row :gutter="16" style="margin-bottom: 16px">
          <a-col :span="8"><StatCard title="总迭代" :value="result.total_iterations" /></a-col>
          <a-col :span="8"><StatCard title="最佳收益" :value="result.best_value" type="percent" /></a-col>
          <a-col :span="8"><StatCard title="最优参数" :value="result.best_params" /></a-col>
        </a-row>
        <a-table :columns="iterColumns" :dataSource="result.history" :rowKey="(_, i) => `iter-${i}`" :pagination="false" size="small" />
      </template>
      <a-empty v-else />
    </a-card>
  </div>
</template>
<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { componentsApi, optimizationApi } from '@/api'
import type { BayesianOptimizerResult } from '@/api'
import { PageHeader } from '@/components/layout'
import { StatCard } from '@/components/common'

const loading = ref(false)
const strategyList = ref<any[]>([])
const result = ref<BayesianOptimizerResult | null>(null)
const config = reactive({ strategyId: '', nIterations: 50, nInitial: 5 })

const iterColumns = [
  { title: '迭代', dataIndex: 'iteration', width: 60 },
  { title: '参数', dataIndex: 'params', width: 150 },
  { title: '目标值', dataIndex: 'score', width: 100 },
  { title: '不确定性', dataIndex: 'uncertainty', width: 100 },
]

const fetchStrategyList = async () => {
  try { strategyList.value = ((await componentsApi.getStrategies()) || []).map((f: any) => ({ id: f.name || f.uuid, name: f.name || f.uuid })) } catch {}
}

const runOptimization = async () => {
  if (!config.strategyId) { message.warning('请选择策略'); return }
  loading.value = true
  try { result.value = await optimizationApi.bayesian({ strategy_id: config.strategyId, params: {}, n_iterations: config.nIterations, n_initial_points: config.nInitial }); message.success('完成') }
  catch { message.error('失败') }
  finally { loading.value = false }
}

onMounted(() => { fetchStrategyList() })
</script>
