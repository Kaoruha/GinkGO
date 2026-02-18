<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">IC 分析</div>
    </div>

    <a-row :gutter="16">
      <a-col :span="8">
        <a-card title="因子配置">
          <a-form layout="vertical">
            <a-form-item label="因子数据源">
              <a-select v-model:value="config.factorSource" style="width: 100%">
                <a-select-option value="backtest">回测结果</a-select-option>
                <a-select-option value="custom">自定义</a-select-option>
              </a-select>
            </a-form-item>
            <a-form-item label="回测任务">
              <a-select v-model:value="config.backtestId" style="width: 100%">
                <a-select-option v-for="bt in backtestList" :key="bt.task_id" :value="bt.task_id">
                  {{ bt.task_id }}
                </a-select-option>
              </a-select>
            </a-form-item>
            <a-form-item label="收益周期">
              <a-select v-model:value="config.returnPeriod" style="width: 100%">
                <a-select-option :value="1">1日</a-select-option>
                <a-select-option :value="5">5日</a-select-option>
                <a-select-option :value="10">10日</a-select-option>
                <a-select-option :value="20">20日</a-select-option>
              </a-select>
            </a-form-item>
            <a-form-item>
              <a-button type="primary" block @click="runAnalysis" :loading="loading">开始分析</a-button>
            </a-form-item>
          </a-form>
        </a-card>
      </a-col>

      <a-col :span="16">
        <a-card title="IC 统计结果">
          <template v-if="result">
            <a-row :gutter="16" style="margin-bottom: 16px">
              <a-col :span="6"><a-statistic title="IC 均值" :value="result.ic_mean?.toFixed(4)" /></a-col>
              <a-col :span="6"><a-statistic title="IC 标准差" :value="result.ic_std?.toFixed(4)" /></a-col>
              <a-col :span="6"><a-statistic title="ICIR" :value="result.icir?.toFixed(4)" /></a-col>
              <a-col :span="6"><a-statistic title="IC > 0 比例" :value="(result.ic_positive_ratio * 100).toFixed(2)" suffix="%" /></a-col>
            </a-row>
            <a-table :columns="icColumns" :dataSource="result.ic_series" :rowKey="(_, i) => `ic-${i}`" :pagination="false" size="small" />
          </template>
          <a-empty v-else description="请配置参数并开始分析" />
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import request from '@/api/request'

const loading = ref(false)
const backtestList = ref<any[]>([])
const result = ref<any>(null)

const config = reactive({
  factorSource: 'backtest',
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
    const response = await request.get('/api/v1/backtest', { params: { size: 20 } })
    backtestList.value = response.data?.data || []
  } catch (e) { console.error(e) }
}

const runAnalysis = async () => {
  if (!config.backtestId) { message.warning('请选择回测任务'); return }
  loading.value = true
  try {
    const response = await request.post('/api/v1/research/ic', {
      backtest_id: config.backtestId,
      return_period: config.returnPeriod,
    })
    result.value = response.data
    message.success('分析完成')
  } catch (e: any) { message.error('分析失败') }
  finally { loading.value = false }
}

onMounted(() => { fetchBacktestList() })
</script>

<style scoped>
.page-container { padding: 0; }
.page-header { margin-bottom: 16px; }
.page-title { font-size: 18px; font-weight: 600; }
</style>
