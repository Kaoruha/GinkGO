<template>
  <div class="page-container">
    <PageHeader
      title="网格搜索"
      description="穷举所有参数组合，保证找到全局最优。适合2-3个参数，计算量较大。"
    />
    <a-card title="搜索配置" class="config-card">
      <a-form layout="inline">
        <a-form-item label="策略选择">
          <a-select v-model:value="config.strategyId" style="width: 200px">
            <a-select-option v-for="s in strategyList" :key="s.id" :value="s.id">{{ s.name }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="参数配置 (JSON)">
          <a-input v-model:value="config.params" placeholder='{"param1": [1, 2, 3]}' style="width: 300px" />
        </a-form-item>
        <a-form-item>
          <a-button type="primary" @click="runOptimization" :loading="loading">开始搜索</a-button>
        </a-form-item>
      </a-form>
    </a-card>
    <a-card title="搜索结果" class="result-card">
      <template v-if="result">
        <a-row :gutter="16" style="margin-bottom: 16px">
          <a-col :span="8"><StatCard title="总组合数" :value="result.total_combinations" /></a-col>
          <a-col :span="8"><StatCard title="最佳收益" :value="result.best_return" type="percent" /></a-col>
          <a-col :span="8"><StatCard title="最佳参数" :value="result.best_params" /></a-col>
        </a-row>
        <a-table :columns="resultColumns" :dataSource="result.top_results" :rowKey="(_, i) => `result-${i}`" :pagination="false" size="small" />
      </template>
      <a-empty v-else />
    </a-card>
  </div>
</template>
<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { componentsApi, optimizationApi } from '@/api'
import type { GridSearchResult } from '@/api'
import { PageHeader } from '@/components/layout'
import { StatCard } from '@/components/common'

const loading = ref(false)
const strategyList = ref<any[]>([])
const result = ref<GridSearchResult | null>(null)
const config = reactive({ strategyId: '', params: '' })

const resultColumns = [
  { title: '排名', dataIndex: 'rank', width: 60 },
  { title: '参数', dataIndex: 'params', width: 200 },
  { title: '收益', dataIndex: 'total_return', width: 100 },
  { title: '夏普比率', dataIndex: 'sharpe_ratio', width: 100 },
]

const fetchStrategyList = async () => {
  try { strategyList.value = ((await componentsApi.getStrategies()) || []).map((f: any) => ({ id: f.name || f.uuid, name: f.name || f.uuid })) } catch {}
}

const runOptimization = async () => {
  if (!config.strategyId) { message.warning('请选择策略'); return }
  loading.value = true
  try { result.value = await optimizationApi.gridSearch({ strategy_id: config.strategyId, params: JSON.parse(config.params || '{}') }); message.success('完成') }
  catch { message.error('失败') }
  finally { loading.value = false }
}

onMounted(() => { fetchStrategyList() })
</script>
