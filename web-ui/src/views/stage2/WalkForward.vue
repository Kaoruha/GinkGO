<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">
        <a-tag color="green">验证</a-tag>
        走步验证
      </div>
    </div>

    <a-row :gutter="16">
      <!-- 配置面板 -->
      <a-col :span="8">
        <a-card title="验证配置">
          <a-form layout="vertical">
            <a-form-item label="回测任务">
              <a-select v-model:value="config.backtestId" placeholder="选择回测任务" style="width: 100%">
                <a-select-option v-for="bt in backtestList" :key="bt.task_id" :value="bt.task_id">
                  {{ bt.task_id }}
                </a-select-option>
              </a-select>
            </a-form-item>

            <a-form-item label="折数 (Folds)">
              <a-input-number v-model:value="config.nFolds" :min="2" :max="10" style="width: 100%" />
            </a-form-item>

            <a-form-item label="训练期比例">
              <a-slider v-model:value="config.trainRatio" :min="0.5" :max="0.9" :step="0.1" />
            </a-form-item>

            <a-form-item label="窗口类型">
              <a-radio-group v-model:value="config.windowType">
                <a-radio value="expanding">扩展窗口</a-radio>
                <a-radio value="rolling">滚动窗口</a-radio>
              </a-radio-group>
            </a-form-item>

            <a-form-item>
              <a-button type="primary" block @click="runValidation" :loading="loading">
                开始验证
              </a-button>
            </a-form-item>
          </a-form>
        </a-card>
      </a-col>

      <!-- 结果面板 -->
      <a-col :span="16">
        <a-card title="验证结果">
          <template v-if="result">
            <!-- 汇总统计 -->
            <a-row :gutter="16" style="margin-bottom: 16px">
              <a-col :span="6">
                <a-statistic title="平均训练收益" :value="(result.avg_train_return * 100).toFixed(2)" suffix="%" />
              </a-col>
              <a-col :span="6">
                <a-statistic title="平均测试收益" :value="(result.avg_test_return * 100).toFixed(2)" suffix="%" />
              </a-col>
              <a-col :span="6">
                <a-statistic title="退化程度" :value="(result.degradation * 100).toFixed(2)" suffix="%" />
              </a-col>
              <a-col :span="6">
                <a-statistic title="稳定性评分" :value="result.stability_score?.toFixed(2) || '-'" />
              </a-col>
            </a-row>

            <!-- 各 Fold 结果 -->
            <a-table
              :columns="foldColumns"
              :dataSource="result.folds"
              :rowKey="(_, i) => `fold-${i}`"
              :pagination="false"
              size="small"
            >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'train_return' || column.key === 'test_return'">
                  <span :style="{ color: record[column.dataIndex!] >= 0 ? '#cf1322' : '#3f8600' }">
                    {{ (record[column.dataIndex!] * 100).toFixed(2) }}%
                  </span>
                </template>
              </template>
            </a-table>
          </template>
          <a-empty v-else description="请配置参数并开始验证" />
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import request from '@/api/request'

interface FoldResult {
  fold: number
  train_start: string
  train_end: string
  test_start: string
  test_end: string
  train_return: number
  test_return: number
}

interface ValidationResult {
  avg_train_return: number
  avg_test_return: number
  degradation: number
  stability_score: number
  folds: FoldResult[]
}

const loading = ref(false)
const backtestList = ref<any[]>([])
const result = ref<ValidationResult | null>(null)

const config = reactive({
  backtestId: '',
  nFolds: 5,
  trainRatio: 0.7,
  windowType: 'expanding',
})

const foldColumns = [
  { title: 'Fold', dataIndex: 'fold', width: 60 },
  { title: '训练开始', dataIndex: 'train_start', width: 100 },
  { title: '训练结束', dataIndex: 'train_end', width: 100 },
  { title: '测试开始', dataIndex: 'test_start', width: 100 },
  { title: '测试结束', dataIndex: 'test_end', width: 100 },
  { title: '训练收益', key: 'train_return', dataIndex: 'train_return', width: 100 },
  { title: '测试收益', key: 'test_return', dataIndex: 'test_return', width: 100 },
]

const fetchBacktestList = async () => {
  try {
    const response = await request.get('/api/v1/backtest', { params: { size: 20 } })
    backtestList.value = response.data?.data || []
  } catch (e) {
    console.error('获取回测列表失败:', e)
  }
}

const runValidation = async () => {
  if (!config.backtestId) {
    message.warning('请选择回测任务')
    return
  }

  loading.value = true
  try {
    const response = await request.post('/api/v1/validation/walkforward', {
      backtest_config: { backtest_id: config.backtestId },
      n_folds: config.nFolds,
      window_type: config.windowType,
    })
    result.value = response.data || null
    message.success('验证完成')
  } catch (e: any) {
    message.error('验证失败: ' + (e.message || '未知错误'))
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
