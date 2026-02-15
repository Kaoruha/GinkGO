<template>
  <div class="factor-comparison">
    <a-card title="因子对比">
      <template #extra>
        <a-space>
          <a-select
            v-model:value="selectedFactors"
            mode="multiple"
            placeholder="选择因子"
            style="width: 300px"
          >
            <a-select-option v-for="f in allFactors" :key="f" :value="f">{{ f }}</a-select-option>
          </a-select>
          <a-range-picker v-model:value="dateRange" />
          <a-button type="primary" @click="compare">对比</a-button>
        </a-space>
      </template>

      <a-table
        :columns="compColumns"
        :data-source="comparisonData"
        :pagination="false"
        size="small"
        bordered
      >
        <template #bodyCell="{ column, record }">
          <span v-if="column.isMetric" :class="{ 'best-value': record.isBest }">
            {{ record[column.dataIndex] }}
          </span>
        </template>
      </a-table>

      <div class="chart-section">
        <h4>IC对比</h4>
        <ICIRChart :ic-data="icChartData" height="280px" />
      </div>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ICIRChart } from '@/components/charts/factor'
import { message } from 'ant-design-vue'

const allFactors = ref(['momentum', 'reversal', 'volatility', 'liquidity', 'size', 'value'])
const selectedFactors = ref<string[]>([])
const dateRange = ref<any[]>([])

const compColumns = [
  { title: '因子', dataIndex: 'factor', width: 120 },
  { title: 'IC均值', dataIndex: 'icMean', isMetric: true, width: 100 },
  { title: 'ICIR', dataIndex: 'icir', isMetric: true, width: 100 },
  { title: 't统计量', dataIndex: 'tStat', isMetric: true, width: 100 },
  { title: '正IC占比', dataIndex: 'posRatio', isMetric: true, width: 100 },
  { title: '综合评分', dataIndex: 'score', isMetric: true, width: 100 },
]

const comparisonData = ref<any[]>([])

const icChartData = ref<any[]>([])

const compare = async () => {
  if (selectedFactors.value.length < 2) {
    message.warning('请至少选择2个因子')
    return
  }
  // TODO: 调用因子对比API
  message.info('进行因子对比...')
}
</script>

<style scoped>
.factor-comparison {
  padding: 16px;
}

.chart-section {
  margin-top: 24px;
}

.best-value {
  color: #52c41a;
  font-weight: 600;
}
</style>
