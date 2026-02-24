<template>
  <div class="page-container">
    <PageHeader
      title="因子正交化"
      description="消除多因子之间的相关性，避免信息重复。正交化后因子相互独立，组合效果更好。"
    />
    <a-card title="正交化配置" class="config-card">
      <a-form layout="inline">
        <a-form-item label="回测任务">
          <a-select v-model:value="config.backtestId" style="width: 200px">
            <a-select-option v-for="bt in backtestList" :key="bt.run_id" :value="bt.run_id">{{ bt.run_id }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="正交化方法">
          <a-select v-model:value="config.method" style="width: 150px">
            <a-select-option value="gram_schmidt">Gram-Schmidt</a-select-option>
            <a-select-option value="pca">PCA</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item>
          <a-button type="primary" @click="runAnalysis" :loading="loading">开始分析</a-button>
        </a-form-item>
      </a-form>
    </a-card>
    <a-card title="相关性矩阵对比" class="result-card">
      <template v-if="result">
        <a-row :gutter="16" style="margin-bottom: 16px">
          <a-col :span="8"><StatCard title="原始平均相关系数" :value="result.original_avg_corr" type="decimal" :decimals="4" /></a-col>
          <a-col :span="8"><StatCard title="正交后平均相关系数" :value="result.orthogonal_avg_corr" type="decimal" :decimals="4" /></a-col>
        </a-row>
      </template>
      <a-empty v-else />
    </a-card>
  </div>
</template>
<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { backtestApi, researchApi } from '@/api'
import type { FactorOrthogonalizeResult } from '@/api'
import { PageHeader } from '@/components/layout'
import { StatCard } from '@/components/common'

const loading = ref(false)
const backtestList = ref<any[]>([])
const result = ref<FactorOrthogonalizeResult | null>(null)
const config = reactive({ backtestId: '', method: 'gram_schmidt' as 'gram_schmidt' | 'pca' | 'residual' })

const fetchBacktestList = async () => {
  try { backtestList.value = (await backtestApi.list({ size: 20 })).data || [] } catch {}
}

const runAnalysis = async () => {
  if (!config.backtestId) { message.warning('请选择回测任务'); return }
  loading.value = true
  try { result.value = await researchApi.orthogonalize({ backtest_id: config.backtestId, factors: [], method: config.method }); message.success('完成') }
  catch { message.error('失败') }
  finally { loading.value = false }
}

onMounted(() => { fetchBacktestList() })
</script>
