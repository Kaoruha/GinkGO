<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">
        <a-tag color="green">验证</a-tag>
        蒙特卡洛模拟
      </div>
    </div>

    <a-row :gutter="16">
      <!-- 配置面板 -->
      <a-col :span="8">
        <a-card title="模拟配置">
          <a-form layout="vertical">
            <a-form-item label="回测任务">
              <a-select v-model:value="config.backtestId" placeholder="选择回测任务" style="width: 100%">
                <a-select-option v-for="bt in backtestList" :key="bt.task_id" :value="bt.task_id">
                  {{ bt.task_id }}
                </a-select-option>
              </a-select>
            </a-form-item>

            <a-form-item label="模拟次数">
              <a-input-number v-model:value="config.nSimulations" :min="1000" :max="100000" :step="1000" style="width: 100%" />
            </a-form-item>

            <a-form-item label="置信水平">
              <a-select v-model:value="config.confidenceLevel" style="width: 100%">
                <a-select-option :value="0.9">90%</a-select-option>
                <a-select-option :value="0.95">95%</a-select-option>
                <a-select-option :value="0.99">99%</a-select-option>
              </a-select>
            </a-form-item>

            <a-form-item>
              <a-button type="primary" block @click="runSimulation" :loading="loading">
                开始模拟
              </a-button>
            </a-form-item>
          </a-form>
        </a-card>
      </a-col>

      <!-- 结果面板 -->
      <a-col :span="16">
        <template v-if="result">
          <!-- 统计卡片 -->
          <a-row :gutter="16" style="margin-bottom: 16px">
            <a-col :span="6">
              <a-card>
                <a-statistic title="VaR" :value="(result.var * 100).toFixed(2)" suffix="%" :value-style="{ color: '#cf1322' }" />
              </a-card>
            </a-col>
            <a-col :span="6">
              <a-card>
                <a-statistic title="CVaR" :value="(result.cvar * 100).toFixed(2)" suffix="%" :value-style="{ color: '#cf1322' }" />
              </a-card>
            </a-col>
            <a-col :span="6">
              <a-card>
                <a-statistic title="期望收益" :value="(result.expected_return * 100).toFixed(2)" suffix="%" />
              </a-card>
            </a-col>
            <a-col :span="6">
              <a-card>
                <a-statistic title="损失概率" :value="(result.loss_probability * 100).toFixed(2)" suffix="%" />
              </a-card>
            </a-col>
          </a-row>

          <!-- 分布统计 -->
          <a-card title="收益分布统计">
            <a-descriptions :column="4" size="small">
              <a-descriptions-item label="最大收益">{{ (result.max_return * 100).toFixed(2) }}%</a-descriptions-item>
              <a-descriptions-item label="最小收益">{{ (result.min_return * 100).toFixed(2) }}%</a-descriptions-item>
              <a-descriptions-item label="标准差">{{ (result.std_dev * 100).toFixed(2) }}%</a-descriptions-item>
              <a-descriptions-item label="偏度">{{ result.skewness?.toFixed(2) || '-' }}</a-descriptions-item>
            </a-descriptions>
          </a-card>
        </template>
        <a-empty v-else description="请配置参数并开始模拟" />
      </a-col>
    </a-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import request from '@/api/request'

interface MonteCarloResult {
  var: number
  cvar: number
  expected_return: number
  loss_probability: number
  max_return: number
  min_return: number
  std_dev: number
  skewness: number
}

const loading = ref(false)
const backtestList = ref<any[]>([])
const result = ref<MonteCarloResult | null>(null)

const config = reactive({
  backtestId: '',
  nSimulations: 10000,
  confidenceLevel: 0.95,
})

const fetchBacktestList = async () => {
  try {
    const response = await request.get('/api/v1/backtest', { params: { size: 20 } })
    backtestList.value = response.data?.data || []
  } catch (e) {
    console.error('获取回测列表失败:', e)
  }
}

const runSimulation = async () => {
  if (!config.backtestId) {
    message.warning('请选择回测任务')
    return
  }

  loading.value = true
  try {
    const response = await request.post('/api/v1/validation/montecarlo', {
      backtest_id: config.backtestId,
      n_simulations: config.nSimulations,
      confidence_level: config.confidenceLevel,
    })
    result.value = response.data || null
    message.success('模拟完成')
  } catch (e: any) {
    message.error('模拟失败: ' + (e.message || '未知错误'))
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
