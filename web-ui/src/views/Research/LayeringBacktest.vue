<template>
  <div class="layering-backtest">
    <a-card title="因子分层回测">
      <template #extra>
        <a-space>
          <a-select v-model:value="selectedFactor" placeholder="选择因子" style="width: 150px">
            <a-select-option v-for="f in factors" :key="f" :value="f">{{ f }}</a-select-option>
          </a-select>
          <a-select v-model:value="layerCount" placeholder="分层数" style="width: 100px">
            <a-select-option :value="3">3层</a-select-option>
            <a-select-option :value="5">5层</a-select-option>
            <a-select-option :value="10">10层</a-select-option>
          </a-select>
          <a-range-picker v-model:value="dateRange" />
          <a-button type="primary" @click="runBacktest">开始回测</a-button>
        </a-space>
      </template>

      <a-table
        :columns="columns"
        :data-source="layerReturns"
        :pagination="false"
        size="small"
        bordered
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.dataIndex === 'return'">
            <span :style="{ color: record.return >= 0 ? '#f5222d' : '#52c41a' }">
              {{ (record.return * 100).toFixed(2) }}%
            </span>
          </template>
        </template>
      </a-table>

      <div class="chart-section">
        <h4>各组收益对比</h4>
        <LayeringReturnChart :layer-data="chartData" height="350px" />
      </div>

      <a-row :gutter="16" class="stats-section">
        <a-col :span="8">
          <a-statistic title="多空收益" :value="longShortReturn" suffix="%" :precision="2" />
        </a-col>
        <a-col :span="8">
          <a-statistic title="单调性R²" :value="monotonicityR2" :precision="3" />
        </a-col>
        <a-col :span="8">
          <a-statistic title="最大回撤" :value="maxDrawdown" suffix="%" :precision="2" />
        </a-col>
      </a-row>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { LayeringReturnChart } from '@/components/charts/factor'
import { message } from 'ant-design-vue'
import { layeringBacktest } from '@/api/modules/research'
import dayjs from 'dayjs'

const factors = ref(['momentum', 'reversal', 'volatility'])
const selectedFactor = ref('')
const layerCount = ref(5)
const dateRange = ref<any[]>([])
const loading = ref(false)

const columns = computed(() => {
  const layers = Array.from({ length: layerCount.value }, (_, i) => ({
    title: `第${i + 1}组`,
    dataIndex: `group${i + 1}`,
    width: 100
  }))
  return [
    { title: '日期', dataIndex: 'date', width: 120, fixed: 'left' },
    ...layers,
    { title: '多空', dataIndex: 'longShort', width: 100 }
  ]
})

const layerReturns = ref<any[]>([])

const chartData = computed(() => {
  return layerReturns.value.map(d => {
    const returns: Record<string, number> = {}
    for (let i = 1; i <= layerCount.value; i++) {
      returns[`group${i}`] = d[`group${i}`] || 0
    }
    return {
      date: d.date,
      returns: { ...returns, long_short: d.longShort }
    }
  })
})

const longShortReturn = computed(() => {
  if (layerReturns.value.length === 0) return '0.00'
  const last = layerReturns.value[layerReturns.value.length - 1]
  return ((last.longShort || 0) * 100).toFixed(2)
})

const monotonicityR2 = ref(0)
const maxDrawdown = ref(0)

const runBacktest = async () => {
  if (!selectedFactor.value) {
    message.warning('请选择因子')
    return
  }

  loading.value = true
  try {
    const res = await layeringBacktest({
      factor_name: selectedFactor.value,
      n_groups: layerCount.value,
      start_date: dateRange.value[0] ? dayjs(dateRange.value[0]).format('YYYY-MM-DD') : undefined,
      end_date: dateRange.value[1] ? dayjs(dateRange.value[1]).format('YYYY-MM-DD') : undefined
    })

    // 转换结果为表格数据
    layerReturns.value = (res.data?.results || []).map(r => ({
      date: r.date,
      ...r.returns,
      longShort: r.long_short
    }))

    monotonicityR2.value = res.data?.statistics?.monotonicity_r2 || 0
    maxDrawdown.value = (res.data?.statistics?.max_drawdown || 0) * 100

    message.success('分层回测完成')
  } catch (e) {
    message.error('分层回测失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.layering-backtest {
  padding: 16px;
}

.chart-section {
  margin: 24px 0;
}

.stats-section {
  margin-top: 16px;
}
</style>
