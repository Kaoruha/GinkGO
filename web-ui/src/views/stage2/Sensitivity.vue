<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">
        <a-tag color="green">验证</a-tag>
        敏感性分析
      </div>
    </div>

    <a-row :gutter="16">
      <!-- 配置面板 -->
      <a-col :span="8">
        <a-card title="分析配置">
          <a-form layout="vertical">
            <a-form-item label="回测任务">
              <a-select v-model:value="config.backtestId" placeholder="选择回测任务" style="width: 100%">
                <a-select-option v-for="bt in backtestList" :key="bt.task_id" :value="bt.task_id">
                  {{ bt.task_id }}
                </a-select-option>
              </a-select>
            </a-form-item>

            <a-form-item label="分析参数">
              <a-input v-model:value="config.paramName" placeholder="参数名称，如: max_position" />
            </a-form-item>

            <a-form-item label="参数值列表">
              <a-textarea
                v-model:value="config.paramValues"
                :rows="3"
                placeholder="每行一个值&#10;例如：&#10;0.1&#10;0.2&#10;0.3&#10;0.4"
              />
            </a-form-item>

            <a-form-item>
              <a-button type="primary" block @click="runAnalysis" :loading="loading">
                开始分析
              </a-button>
            </a-form-item>
          </a-form>
        </a-card>
      </a-col>

      <!-- 结果面板 -->
      <a-col :span="16">
        <a-card title="分析结果">
          <template v-if="result">
            <!-- 敏感性指标 -->
            <a-row :gutter="16" style="margin-bottom: 16px">
              <a-col :span="8">
                <a-statistic title="敏感性分数" :value="result.sensitivity_score?.toFixed(2) || '-'" />
              </a-col>
              <a-col :span="8">
                <a-statistic title="最优参数值" :value="result.optimal_value || '-'" />
              </a-col>
              <a-col :span="8">
                <a-statistic title="最优收益" :value="((result.optimal_return || 0) * 100).toFixed(2)" suffix="%" />
              </a-col>
            </a-row>

            <!-- 结果表格 -->
            <a-table
              :columns="resultColumns"
              :dataSource="result.data_points"
              :rowKey="(_, i) => `point-${i}`"
              :pagination="false"
              size="small"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'return'">
                  <span :style="{ color: record.return >= 0 ? '#cf1322' : '#3f8600' }">
                    {{ (record.return * 100).toFixed(2) }}%
                  </span>
                </template>
                <template v-if="column.key === 'is_optimal'">
                  <a-tag v-if="record.is_optimal" color="green">最优</a-tag>
                </template>
              </template>
            </a-table>
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

interface DataPoint {
  param_value: number | string
  return: number
  sharpe_ratio: number
  max_drawdown: number
  is_optimal: boolean
}

interface SensitivityResult {
  sensitivity_score: number
  optimal_value: number | string
  optimal_return: number
  data_points: DataPoint[]
}

const loading = ref(false)
const backtestList = ref<any[]>([])
const result = ref<SensitivityResult | null>(null)

const config = reactive({
  backtestId: '',
  paramName: '',
  paramValues: '',
})

const resultColumns = [
  { title: '参数值', dataIndex: 'param_value', width: 120 },
  { title: '收益率', key: 'return', width: 120 },
  { title: '夏普比率', dataIndex: 'sharpe_ratio', width: 120 },
  { title: '最大回撤', dataIndex: 'max_drawdown', width: 120 },
  { title: '标记', key: 'is_optimal', width: 80 },
]

const fetchBacktestList = async () => {
  try {
    const response = await request.get('/api/v1/backtest', { params: { size: 20 } })
    backtestList.value = response.data?.data || []
  } catch (e) {
    console.error('获取回测列表失败:', e)
  }
}

const runAnalysis = async () => {
  if (!config.backtestId) {
    message.warning('请选择回测任务')
    return
  }
  if (!config.paramName) {
    message.warning('请输入参数名称')
    return
  }
  if (!config.paramValues.trim()) {
    message.warning('请输入参数值列表')
    return
  }

  const values = config.paramValues.split('\n').map(v => v.trim()).filter(v => v)

  loading.value = true
  try {
    const response = await request.post('/api/v1/validation/sensitivity', {
      backtest_id: config.backtestId,
      param_name: config.paramName,
      param_values: values,
    })
    result.value = response.data || null
    message.success('分析完成')
  } catch (e: any) {
    message.error('分析失败: ' + (e.message || '未知错误'))
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchBacktestList()
})
</script>

<style scoped>
.page-container { padding: 0; }
.page-header { margin-bottom: 16px; }
.page-title { font-size: 18px; font-weight: 600; display: flex; align-items: center; gap: 8px; }
</style>
