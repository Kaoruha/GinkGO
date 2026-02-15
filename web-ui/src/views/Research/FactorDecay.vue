<template>
  <div class="factor-decay">
    <a-card title="因子衰减分析">
      <template #extra>
        <a-button @click="$router.push('/portfolio')">选择因子</a-button>
      </template>

      <!-- Custom -->
      <a-row :gutter="16" class="mb-4">
        <a-col :span="12">
          <a-form-item label="选择因子">
            <a-select v-model:value="selectedFactor" placeholder="选择要分析的因子">
              <a-select-option v-for="f in factors" :key="f.name" :value="f.name">
                {{ f.label }}
              </a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
        <a-col :span="12">
          <a-form-item label="最大滞后期">
            <a-input-number v-model:value="maxLag" :min="1" :max="60" style="width: 100%" />
          </a-form-item>
        </a-col>
      </a-row>

      <!-- Custom -->
      <div class="action-buttons">
        <a-space>
          <a-button type="primary" :loading="analyzing" @click="startAnalysis">
            开始分析
          </a-button>
        </a-space>
      </div>
    </a-card>

    <!-- Custom -->
    <a-card v-if="decayData.length > 0" title="衰减曲线" class="mt-4">
      <div ref="decayChartRef" class="chart-container" style="height: 350px"></div>
    </a-card>

    <!-- Custom -->
    <a-card v-if="halfLife" title="半衰期" class="mt-4">
      <a-row :gutter="16">
        <a-col :span="12">
          <a-card title="半衰期（天）" size="small">
            <a-statistic :value="halfLife" />
          </a-card>
        </a-col>
        <a-col :span="12">
          <a-card title="最佳滞后期" size="small">
            <a-statistic :value="bestLag" :precision="1" suffix="天" />
          </a-card>
        </a-col>
      </a-row>
    </a-card>

    <!-- Custom -->
    <a-card title="各期IC值" class="mt-4">
      <a-table
        :columns="lagColumns"
        :data-source="lagData"
        :pagination="false"
        size="small"
      >
        <template #bodyCell="{ column, record }">
          <span v-if="column.dataIndex === 'ic'" :style="{ color: record.ic > 0 ? '#52c41a' : '#f5222d' }">
            {{ record.ic.toFixed(3) }}
          </span>
        </template>
      </a-table>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import { message } from 'ant-design-vue'
import { analyzeDecay } from '@/api/modules/research'

const router = useRouter()

// 监听衰减数据变化，自动渲染图表
watch(() => decayData.value.length, async (newLen) => {
  if (newLen > 0) {
    await nextTick()
    renderChart()
  }
})

const factors = ref([
  { name: 'momentum', label: '动量因子' },
  { name: 'reversal', label: '反转因子' },
  { name: 'volatility', label: '波动率因子' },
])

const selectedFactor = ref('')
const maxLag = ref(20)
const analyzing = ref(false)
const decayData = ref<any[]>([])
const halfLife = ref(0)
const bestLag = ref(0)
const decayChartRef = ref<HTMLDivElement>()

// 滞后数据
const lagData = ref<any[]>([])

const lagColumns = [
  { title: '滞后期(天)', dataIndex: 'lag', width: 120 },
  { title: 'IC', dataIndex: 'ic', width: 100 },
  { title: '|IC|', dataIndex: 'abs_ic', width: 100 },
  { title: 't统计量', dataIndex: 't_stat', width: 100 }
]

// 开始分析
const startAnalysis = async () => {
  if (!selectedFactor.value) {
    message.warning('请先选择因子')
    return
  }

  analyzing.value = true
  decayData.value = []
  lagData.value = []

  try {
    // TODO: 调用衰减分析API
    // const res = await analyzeDecay({
    //   factor_name: selectedFactor.value,
    //   max_lag: maxLag.value
    // })

    // 模拟数据
    for (let lag = 1; lag <= maxLag.value; lag++) {
      const ic = Math.random() * 0.15 - 0.08
      const tStat = ic / (0.15 / Math.sqrt(100))

      decayData.value.push({
        lag: lag,
        ic: ic,
        t_stat: tStat
      })

      if (lag <= maxLag.value / 2) {
        halfLife.value = lag
        bestLag.value = lag
      }

      await new Promise(resolve => setTimeout(resolve, 50))
    }

    // 计算半衰期（IC值降到最大值的一半时的滞后期）
    const maxIC = Math.max(...decayData.value.map(d => d.ic))
    const halfLifeData = decayData.value.find(d => Math.abs(d.ic) < maxIC * 0.5)
    halfLife.value = halfLifeData?.lag || maxLag.value

    // 找到最佳滞后期（IC绝对值最大的滞后期）
    const bestICData = decayData.value.reduce((best, curr) =>
      Math.abs(curr.ic) > Math.abs(best.ic) ? curr : best
    )
    bestLag.value = bestICData.lag

    message.success('衰减分析完成')
  } catch (e) {
    message.error('衰减分析失败')
  } finally {
    analyzing.value = false
  }
}

// 渲染衰减曲线
const renderChart = () => {
  if (!decayChartRef.value || decayData.value.length === 0) return

  const chart = echarts.init(decayChartRef.value, {
    height: 350,
    width: decayChartRef.value.clientWidth
  })

  chart.setOption({
    tooltip: {
      trigger: 'axis',
      formatter: (params: any) => `滞后期: ${params.mark[0].lag}天<br/>IC: ${params.mark[0].ic.toFixed(3)}<br/>t统计: ${params.mark[1].toFixed(2)}`
    },
    xAxis: {
      type: 'category',
      data: decayData.value.map(d => d.lag),
      name: '滞后期(天)',
      axisLabel: {
        formatter: (v) => v + '天'
      }
    },
    yAxis: {
      type: 'value',
      name: 'IC值',
      axisLabel: {
        formatter: (v) => v.toFixed(2)
      }
    },
    series: [{
      type: 'line',
      data: decayData.value.map(d => d.ic),
      smooth: true,
      markLine: {
        data: [{ value: 0 }],
        lineStyle: { color: '#999', type: 'dashed' }
      },
      markArea: {
        silent: true
      }
    }],
    visualMap: {
      min: -0.15,
      max: 0.15,
      calculable: true,
      inRange: { color: '#52c41a' },
      outOfRange: { color: '#eee' }
    }
  })
}
</script>

<style scoped>
.factor-decay {
  padding: 16px;
}

.action-buttons {
  text-align: center;
}

.chart-container {
  width: 100%;
}
</style>
