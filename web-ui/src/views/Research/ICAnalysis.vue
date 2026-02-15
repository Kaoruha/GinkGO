<template>
  <div class="ic-analysis">
    <a-card title="因子IC分析">
      <template #extra>
        <a-space>
          <a-select v-model:value="selectedFactor" placeholder="选择因子" style="width: 150px">
            <a-select-option v-for="f in factors" :key="f" :value="f">{{ f }}</a-select-option>
          </a-select>
          <a-range-picker v-model:value="dateRange" />
          <a-button type="primary" @click="runAnalysis">分析</a-button>
        </a-space>
      </template>

      <a-row :gutter="16" class="stats-row">
        <a-col :span="4">
          <a-statistic title="IC均值" :value="icStats.mean" :precision="3" />
        </a-col>
        <a-col :span="4">
          <a-statistic title="IC标准差" :value="icStats.std" :precision="3" />
        </a-col>
        <a-col :span="4">
          <a-statistic title="ICIR" :value="icStats.icir" :precision="3" />
        </a-col>
        <a-col :span="4">
          <a-statistic title="t统计量" :value="icStats.tStat" :precision="3" />
        </a-col>
        <a-col :span="4">
          <a-statistic title="正IC占比" :value="icStats.posRatio" suffix="%" />
        </a-col>
        <a-col :span="4">
          <a-statistic title="绝对IC均值" :value="icStats.absMean" :precision="3" />
        </a-col>
      </a-row>

      <div class="chart-section">
        <h4>IC时序图</h4>
        <ICIRChart :ic-data="icData" height="300px" />
      </div>

      <div class="chart-section">
        <h4>IC分布</h4>
        <div ref="histRef" class="histogram-chart" style="height: 250px"></div>
      </div>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ICIRChart } from '@/components/charts/factor'
import { message } from 'ant-design-vue'
import { analyzeIC } from '@/api/modules/research'
import type { ICDataPoint } from '@/api/modules/research'
import dayjs from 'dayjs'

const factors = ref(['momentum', 'reversal', 'volatility', 'liquidity'])
const selectedFactor = ref('')
const dateRange = ref<any[]>([])
const histRef = ref<HTMLDivElement>()
const loading = ref(false)

const icStats = ref({
  mean: 0,
  std: 0,
  icir: 0,
  tStat: 0,
  posRatio: 0,
  absMean: 0
})

const icData = ref<ICDataPoint[]>([])

const runAnalysis = async () => {
  if (!selectedFactor.value) {
    message.warning('请选择因子')
    return
  }

  loading.value = true
  try {
    const res = await analyzeIC({
      factor_name: selectedFactor.value,
      start_date: dateRange.value[0] ? dayjs(dateRange.value[0]).format('YYYY-MM-DD') : undefined,
      end_date: dateRange.value[1] ? dayjs(dateRange.value[1]).format('YYYY-MM-DD') : undefined,
      periods: [1, 5, 10, 20]
    })

    icData.value = res.data?.timeseries || []
    icStats.value = res.data?.statistics || icStats.value
    message.success('IC分析完成')
  } catch (e) {
    message.error('IC分析失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.ic-analysis {
  padding: 16px;
}

.stats-row {
  margin-bottom: 24px;
}

.chart-section {
  margin-top: 24px;
}

.chart-section h4 {
  margin-bottom: 12px;
}
</style>
