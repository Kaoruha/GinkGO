<template>
  <div class="page-container">
    <PageHeader title="敏感性分析" description="评估策略对参数变化的敏感程度。敏感性低说明参数选择更稳健，不易过拟合。">
      <template #tag><a-tag color="green">验证</a-tag></template>
    </PageHeader>

    <a-card title="分析配置" class="config-card">
      <a-form layout="inline">
        <a-form-item label="回测任务">
          <a-select v-model:value="config.backtestId" placeholder="选择回测任务" style="width: 200px">
            <a-select-option v-for="bt in backtestList" :key="bt.run_id" :value="bt.run_id">{{ bt.run_id }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="分析参数">
          <a-input v-model:value="config.paramName" placeholder="如: max_position" style="width: 150px" />
        </a-form-item>
        <a-form-item label="参数值">
          <a-input v-model:value="config.paramValues" placeholder="0.1,0.2,0.3,0.4" style="width: 200px" />
        </a-form-item>
        <a-form-item>
          <a-button type="primary" @click="runAnalysis" :loading="loading">开始分析</a-button>
        </a-form-item>
      </a-form>
    </a-card>

    <a-card title="分析结果" class="result-card">
      <template v-if="result">
        <a-row :gutter="16" style="margin-bottom: 16px">
          <a-col :span="8"><StatCard title="敏感性分数" :value="result.sensitivity_score" type="decimal" /></a-col>
          <a-col :span="8"><StatCard title="最优参数值" :value="result.optimal_value" /></a-col>
          <a-col :span="8"><StatCard title="最优收益" :value="result.optimal_return" type="percent" /></a-col>
        </a-row>
        <a-table :columns="resultColumns" :dataSource="result.data_points" :rowKey="(_, i) => `point-${i}`" :pagination="false" size="small">
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'return'">
              <span :style="{ color: record.return >= 0 ? '#cf1322' : '#3f8600' }">{{ (record.return * 100).toFixed(2) }}%</span>
            </template>
            <template v-if="column.key === 'is_optimal'">
              <a-tag v-if="record.is_optimal" color="green">最优</a-tag>
            </template>
          </template>
        </a-table>
      </template>
      <a-empty v-else description="请配置参数并开始分析" />
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { backtestApi, validationApi } from '@/api'
import type { SensitivityResult } from '@/api'
import { PageHeader } from '@/components/layout'
import { StatCard } from '@/components/common'

const loading = ref(false)
const backtestList = ref<any[]>([])
const result = ref<SensitivityResult | null>(null)

const config = reactive({ backtestId: '', paramName: '', paramValues: '' })

const resultColumns = [
  { title: '参数值', dataIndex: 'param_value', width: 120 },
  { title: '收益率', key: 'return', width: 120 },
  { title: '夏普比率', dataIndex: 'sharpe_ratio', width: 120 },
  { title: '最大回撤', dataIndex: 'max_drawdown', width: 120 },
  { title: '标记', key: 'is_optimal', width: 80 },
]

const fetchBacktestList = async () => {
  try { backtestList.value = (await backtestApi.list({ size: 20 })).data || [] } catch {}
}

const runAnalysis = async () => {
  if (!config.backtestId) { message.warning('请选择回测任务'); return }
  if (!config.paramName) { message.warning('请输入参数名称'); return }
  if (!config.paramValues.trim()) { message.warning('请输入参数值列表'); return }

  const values = config.paramValues.split(/[,，\n]/).map(v => parseFloat(v.trim())).filter(v => !isNaN(v))
  loading.value = true
  try {
    const results = await validationApi.sensitivity({
      backtest_id: config.backtestId,
      params: { [config.paramName]: { min: Math.min(...values), max: Math.max(...values), steps: values.length } },
    })
    result.value = results[0] || null
    message.success('分析完成')
  } catch { message.error('分析失败') }
  finally { loading.value = false }
}

onMounted(() => { fetchBacktestList() })
</script>
