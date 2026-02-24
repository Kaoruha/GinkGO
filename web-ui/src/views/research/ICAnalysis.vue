<template>
  <div class="page-container">
    <PageHeader
      title="IC 分析"
      description="评估因子对未来收益的预测能力。IC均值>0.05为强因子，ICIR>0.5为优秀因子。"
    />

    <a-card title="因子配置" class="config-card">
      <a-form layout="inline">
        <a-form-item label="回测任务">
          <a-select v-model:value="config.backtestId" style="width: 200px">
            <a-select-option v-for="bt in backtestList" :key="bt.run_id" :value="bt.run_id">
              {{ bt.run_id }}
            </a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="收益周期">
          <a-select v-model:value="config.returnPeriod" style="width: 100px">
            <a-select-option :value="1">1日</a-select-option>
            <a-select-option :value="5">5日</a-select-option>
            <a-select-option :value="10">10日</a-select-option>
            <a-select-option :value="20">20日</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item>
          <a-button type="primary" @click="runAnalysis" :loading="loading">开始分析</a-button>
        </a-form-item>
      </a-form>
    </a-card>

    <a-card title="IC 统计结果" class="result-card">
      <template v-if="result">
        <a-row :gutter="16" style="margin-bottom: 16px">
          <a-col :span="6"><StatCard title="IC 均值" :value="result.ic_mean" type="decimal" :decimals="4" /></a-col>
          <a-col :span="6"><StatCard title="IC 标准差" :value="result.ic_std" type="decimal" :decimals="4" /></a-col>
          <a-col :span="6"><StatCard title="ICIR" :value="result.icir" type="decimal" :decimals="4" /></a-col>
          <a-col :span="6"><StatCard title="IC > 0 比例" :value="result.ic_positive_ratio" type="percent" /></a-col>
        </a-row>
        <a-table :columns="icColumns" :dataSource="result.ic_series" :rowKey="(_, i) => `ic-${i}`" :pagination="false" size="small" />
      </template>
      <a-empty v-else description="请配置参数并开始分析" />
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { backtestApi, researchApi } from '@/api'
import type { ICAnalysisResult } from '@/api'
import { PageHeader } from '@/components/layout'
import { StatCard } from '@/components/common'

const loading = ref(false)
const backtestList = ref<any[]>([])
const result = ref<ICAnalysisResult | null>(null)

const config = reactive({
  backtestId: '',
  returnPeriod: 5,
})

const icColumns = [
  { title: '日期', dataIndex: 'date', width: 120 },
  { title: 'IC', dataIndex: 'ic', width: 100 },
  { title: 'Rank IC', dataIndex: 'rank_ic', width: 100 },
]

const fetchBacktestList = async () => {
  try {
    const response = await backtestApi.list({ size: 20 })
    backtestList.value = response.data || []
  } catch (e) { console.error(e) }
}

const runAnalysis = async () => {
  if (!config.backtestId) { message.warning('请选择回测任务'); return }
  loading.value = true
  try {
    result.value = await researchApi.icAnalysis({
      backtest_id: config.backtestId,
      return_period: config.returnPeriod,
    })
    message.success('分析完成')
  } catch (e: any) { message.error('分析失败') }
  finally { loading.value = false }
}

onMounted(() => { fetchBacktestList() })
</script>
