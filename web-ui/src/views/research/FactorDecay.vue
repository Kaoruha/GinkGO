<template>
  <div class="page-container">
    <PageHeader
      title="因子衰减"
      description="测量因子信号随时间的有效性衰减。半衰期短需高频调仓，半衰期长可降低换手率。"
    />
    <a-card title="衰减分析配置" class="config-card">
      <a-form layout="inline">
        <a-form-item label="回测任务">
          <a-select v-model:value="config.backtestId" style="width: 200px">
            <a-select-option v-for="bt in backtestList" :key="bt.run_id" :value="bt.run_id">{{ bt.run_id }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="最大周期">
          <a-input-number v-model:value="config.maxPeriod" :min="5" :max="60" style="width: 80px" />
        </a-form-item>
        <a-form-item>
          <a-button type="primary" @click="runAnalysis" :loading="loading">开始分析</a-button>
        </a-form-item>
      </a-form>
    </a-card>
    <a-card title="IC 衰减结果" class="result-card">
      <template v-if="result">
        <a-row :gutter="16" style="margin-bottom: 16px">
          <a-col :span="8"><StatCard title="半衰期" :value="result.half_life" suffix="天" /></a-col>
          <a-col :span="8"><StatCard title="最优调仓周期" :value="result.optimal_rebalance_freq" suffix="天" /></a-col>
        </a-row>
        <a-table :columns="decayColumns" :dataSource="result.decay_series" :rowKey="(_, i) => `decay-${i}`" :pagination="false" size="small" />
      </template>
      <a-empty v-else />
    </a-card>
  </div>
</template>
<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { backtestApi, researchApi } from '@/api'
import type { FactorDecayResult } from '@/api'
import { PageHeader } from '@/components/layout'
import { StatCard } from '@/components/common'

const loading = ref(false)
const backtestList = ref<any[]>([])
const result = ref<FactorDecayResult | null>(null)
const config = reactive({ backtestId: '', maxPeriod: 20 })

const decayColumns = [
  { title: '周期', dataIndex: 'lag', width: 80 },
  { title: 'IC', dataIndex: 'ic', width: 100 },
  { title: '自相关', dataIndex: 'autocorrelation', width: 100 },
]

const fetchBacktestList = async () => {
  try { backtestList.value = (await backtestApi.list({ size: 20 })).data || [] } catch {}
}

const runAnalysis = async () => {
  if (!config.backtestId) { message.warning('请选择回测任务'); return }
  loading.value = true
  try { result.value = await researchApi.decay({ backtest_id: config.backtestId, max_lag: config.maxPeriod }); message.success('完成') }
  catch { message.error('失败') }
  finally { loading.value = false }
}

onMounted(() => { fetchBacktestList() })
</script>
