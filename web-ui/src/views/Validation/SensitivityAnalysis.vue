<template>
  <div class="sensitivity-analysis-container">
    <div class="page-header">
      <h1 class="page-title">参数敏感性分析</h1>
      <p class="page-subtitle">分析参数变化对策略表现的影响</p>
    </div>

    <a-card class="config-card">
      <a-row :gutter="16">
        <a-col :span="12">
          <a-form-item label="选择策略">
            <a-select v-model:value="selectedStrategy" placeholder="选择要分析参数的策略">
              <a-select-option v-for="s in strategies" :key="s.uuid" :value="s.uuid">
                {{ s.name }}
              </a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
        <a-col :span="12">
          <a-form-item label="分析目标">
            <a-select v-model:value="analyzeTarget">
              <a-select-option value="sharpe">夏普比率</a-select-option>
              <a-select-option value="total_return">总收益</a-select-option>
              <a-select-option value="max_drawdown">最大回撤</a-select-option>
              <a-select-option value="win_rate">胜率</a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
      </a-row>

      <a-divider>敏感性参数配置</a-divider>

      <a-row :gutter="16">
        <a-col :span="8">
          <a-form-item label="要分析的参数">
            <a-select v-model:value="sensitivityParam.name">
              <a-select-option v-for="p in parameterList" :key="p.name" :value="p.name">
                {{ p.label }}
              </a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
        <a-col :span="8">
          <a-form-item label="最小值">
            <a-input-number v-model:value="rangeConfig.min" style="width: 100%" />
          </a-form-item>
        </a-col>
        <a-col :span="8">
          <a-form-item label="最大值">
            <a-input-number v-model:value="rangeConfig.max" style="width: 100%" />
          </a-form-item>
        </a-col>
      </a-row>

      <a-row :gutter="16">
        <a-col :span="8">
          <a-form-item label="步长">
            <a-input-number v-model:value="rangeConfig.step" :min="0.001" style="width: 100%" />
          </a-form-item>
        </a-col>
        <a-col :span="8">
          <a-form-item label="测试点数">
            <a-input-number v-model:value="rangeConfig.points" :min="5" :max="100" style="width: 100%" />
          </a-form-item>
        </a-col>
        <a-col :span="8">
          <a-button type="primary" :loading="analyzing" @click="runAnalysis">
            开始分析
          </a-button>
        </a-col>
      </a-row>
    </a-card>

    <a-card v-if="results.length > 0" class="result-card">
      <template #title>分析结果</template>
      <a-table :columns="resultColumns" :data-source="results" :pagination="false" size="small">
        <template #bodyCell="{ column, record }">
          <template v-if="column.dataIndex === 'value'">
            <span :class="getValueClass(record.target)">{{ record.target?.toFixed(4) }}</span>
          </template>
        </template>
      </a-table>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { message } from 'ant-design-vue'

const selectedStrategy = ref('')
const analyzeTarget = ref('sharpe')
const analyzing = ref(false)

const strategies = ref<any[]>([
  { uuid: '1', name: '双均线策略' },
  { uuid: '2', name: '动量策略' }
])

const parameterList = ref<any[]>([
  { name: 'short_period', label: '短周期' },
  { name: 'long_period', label: '长周期' },
  { name: 'stop_loss', label: '止损比例' }
])

const sensitivityParam = reactive({
  name: 'short_period',
  baseValue: 10
})

const rangeConfig = reactive({
  min: 5,
  max: 20,
  step: 1,
  points: 10
})

const results = ref<any[]>([])

const resultColumns = [
  { title: '参数值', dataIndex: 'param_value', width: 150 },
  { title: '目标值', dataIndex: 'value', width: 150 },
  { title: '变化率', dataIndex: 'change', width: 150 }
]

const getValueClass = (value: number) => {
  if (value > 1) return 'value-up'
  if (value < 0.5) return 'value-down'
  return ''
}

const runAnalysis = async () => {
  if (!selectedStrategy.value) {
    message.warning('请选择策略')
    return
  }

  analyzing.value = true
  try {
    // 模拟分析结果
    results.value = []
    for (let i = rangeConfig.min; i <= rangeConfig.max; i += rangeConfig.step) {
      results.value.push({
        key: i,
        param_value: i,
        target: Math.random() * 2,
        change: (Math.random() * 20 - 10).toFixed(2) + '%'
      })
    }
    message.success('分析完成')
  } catch (error: any) {
    message.error(`分析失败: ${error.message}`)
  } finally {
    analyzing.value = false
  }
}
</script>

<style scoped>
.sensitivity-analysis-container {
  padding: 24px;
  background: #f5f7fa;
  min-height: calc(100vh - 64px);
}

.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  margin: 0 0 8px 0;
}

.page-subtitle {
  font-size: 14px;
  color: #8c8c8c;
  margin: 0;
}

.config-card,
.result-card {
  margin-bottom: 24px;
  border-radius: 8px;
}

.value-up {
  color: #f5222d;
}

.value-down {
  color: #52c41a;
}
</style>
