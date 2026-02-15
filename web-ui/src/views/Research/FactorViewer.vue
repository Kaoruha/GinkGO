<template>
  <div class="factor-viewer">
    <a-card title="因子查看器">
      <template #extra>
        <a-space>
          <a-select v-model:value="selectedFactor" placeholder="选择因子" style="width: 200px">
            <a-select-option v-for="f in factors" :key="f.name" :value="f.name">
              {{ f.label }}
            </a-select-option>
          </a-select>
          <a-button type="primary" @click="loadFactorData">加载</a-button>
        </a-space>
      </template>

      <a-row :gutter="16">
        <a-col :span="6">
          <a-statistic title="均值" :value="stats.mean" :precision="4" />
        </a-col>
        <a-col :span="6">
          <a-statistic title="标准差" :value="stats.std" :precision="4" />
        </a-col>
        <a-col :span="6">
          <a-statistic title="偏度" :value="stats.skew" :precision="4" />
        </a-col>
        <a-col :span="6">
          <a-statistic title="峰度" :value="stats.kurt" :precision="4" />
        </a-col>
      </a-row>

      <div class="chart-section">
        <h4>因子分布</h4>
        <div ref="distRef" class="distribution-chart" style="height: 300px"></div>
      </div>

      <a-table
        :columns="columns"
        :data-source="factorData"
        :scroll="{ y: 400 }"
        :pagination="{ pageSize: 50 }"
        size="small"
      />
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import * as echarts from 'echarts'
import { getFactorList, queryFactorData } from '@/api/modules/research'
import type { FactorList, FactorValue } from '@/api/modules/research'

const factors = ref<FactorList[]>([])
const selectedFactor = ref('')
const factorData = ref<FactorValue[]>([])
const distRef = ref<HTMLDivElement>()

const stats = computed(() => {
  if (factorData.value.length === 0) return { mean: '-', std: '-', skew: '-', kurt: '-' }
  const values = factorData.value.map(d => d.value)
  const mean = values.reduce((a, b) => a + b, 0) / values.length
  const variance = values.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / values.length
  const std = Math.sqrt(variance)
  return { mean: mean.toFixed(4), std: std.toFixed(4), skew: '-', kurt: '-' }
})

const columns = [
  { title: '日期', dataIndex: 'date', width: 120 },
  { title: '股票代码', dataIndex: 'code', width: 100 },
  { title: '因子值', dataIndex: 'value', width: 100 },
]

// 加载因子列表
const loadFactors = async () => {
  try {
    const res = await getFactorList()
    factors.value = res.data || []
  } catch (e) {
    message.error('加载因子列表失败')
  }
}

// 加载因子数据
const loadFactorData = async () => {
  if (!selectedFactor.value) {
    message.warning('请先选择因子')
    return
  }
  try {
    const res = await queryFactorData({
      factor_name: selectedFactor.value,
      limit: 100
    })
    factorData.value = res.data || []
  } catch (e) {
    message.error('加载因子数据失败')
  }
}

onMounted(() => {
  loadFactors()
})
</script>

<style scoped>
.factor-viewer {
  padding: 16px;
}

.chart-section {
  margin-top: 24px;
}

.distribution-chart {
  width: 100%;
}
</style>
