<template>
  <div class="page-container">
    <PageHeader
      title="因子比较"
      description="多因子横向对比，从IC、ICIR、换手率等维度综合评估，选择最优因子。"
    />
    <a-card title="比较配置" class="config-card">
      <a-form layout="inline">
        <a-form-item label="回测任务">
          <a-select v-model:value="config.backtestId" style="width: 200px">
            <a-select-option v-for="bt in backtestList" :key="bt.run_id" :value="bt.run_id">{{ bt.run_id }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item>
          <a-button type="primary" @click="runAnalysis" :loading="loading">开始比较</a-button>
        </a-form-item>
      </a-form>
    </a-card>
    <a-card title="因子对比结果" class="result-card">
      <template v-if="result">
        <a-row :gutter="16" style="margin-bottom: 16px">
          <a-col :span="8"><StatCard title="最佳因子" :value="result.best_factor || '-'" /></a-col>
          <a-col :span="8"><StatCard title="综合评分" :value="result.best_score" type="decimal" /></a-col>
        </a-row>
        <a-table :columns="compareColumns" :dataSource="result.factors" :rowKey="(_, i) => `factor-${i}`" :pagination="false" size="small" />
      </template>
      <a-empty v-else />
    </a-card>
  </div>
</template>
<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { backtestApi, researchApi } from '@/api'
import type { FactorCompareResult } from '@/api'
import { PageHeader } from '@/components/layout'
import { StatCard } from '@/components/common'

const loading = ref(false)
const backtestList = ref<any[]>([])
const result = ref<FactorCompareResult | null>(null)
const config = reactive({ backtestId: '' })

const compareColumns = [
  { title: '因子名', dataIndex: 'name', width: 120 },
  { title: 'IC', dataIndex: 'ic', width: 100 },
  { title: 'ICIR', dataIndex: 'icir', width: 100 },
  { title: '换手率', dataIndex: 'turnover', width: 100 },
]

const fetchBacktestList = async () => {
  try { backtestList.value = (await backtestApi.list({ size: 20 })).data || [] } catch {}
}

const runAnalysis = async () => {
  if (!config.backtestId) { message.warning('请选择回测任务'); return }
  loading.value = true
  try { result.value = await researchApi.compare({ backtest_id_1: config.backtestId }); message.success('完成') }
  catch { message.error('失败') }
  finally { loading.value = false }
}

onMounted(() => { fetchBacktestList() })
</script>
