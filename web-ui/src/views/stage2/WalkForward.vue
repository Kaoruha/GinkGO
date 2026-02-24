<template>
  <div class="page-container">
    <PageHeader title="走步验证" description="时间序列交叉验证，评估策略样本外表现。退化程度大说明过拟合风险高。">
      <template #tag><a-tag color="green">验证</a-tag></template>
    </PageHeader>

    <a-card title="验证配置" class="config-card">
      <a-form layout="inline">
        <a-form-item label="回测任务">
          <a-select v-model:value="config.backtestId" placeholder="选择回测任务" style="width: 200px">
            <a-select-option v-for="bt in backtestList" :key="bt.run_id" :value="bt.run_id">{{ bt.run_id }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="折数">
          <a-input-number v-model:value="config.nFolds" :min="2" :max="10" style="width: 80px" />
        </a-form-item>
        <a-form-item label="训练期比例">
          <a-slider v-model:value="config.trainRatio" :min="0.5" :max="0.9" :step="0.1" style="width: 100px" />
        </a-form-item>
        <a-form-item label="窗口类型">
          <a-radio-group v-model:value="config.windowType">
            <a-radio value="expanding">扩展窗口</a-radio>
            <a-radio value="rolling">滚动窗口</a-radio>
          </a-radio-group>
        </a-form-item>
        <a-form-item>
          <a-button type="primary" @click="runValidation" :loading="loading">开始验证</a-button>
        </a-form-item>
      </a-form>
    </a-card>

    <a-card title="验证结果" class="result-card">
      <template v-if="result">
        <a-row :gutter="16" style="margin-bottom: 16px">
          <a-col :span="6"><StatCard title="平均训练收益" :value="result.avg_train_return" type="percent" /></a-col>
          <a-col :span="6"><StatCard title="平均测试收益" :value="result.avg_test_return" type="percent" /></a-col>
          <a-col :span="6"><StatCard title="退化程度" :value="result.degradation" type="percent" /></a-col>
          <a-col :span="6"><StatCard title="稳定性评分" :value="result.stability_score" type="decimal" /></a-col>
        </a-row>
        <a-table :columns="foldColumns" :dataSource="result.folds" :rowKey="(_, i) => `fold-${i}`" :pagination="false" size="small">
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
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { backtestApi, validationApi } from '@/api'
import type { WalkForwardResult } from '@/api'
import { PageHeader } from '@/components/layout'
import { StatCard } from '@/components/common'

const loading = ref(false)
const backtestList = ref<any[]>([])
const result = ref<WalkForwardResult | null>(null)

const config = reactive({
  backtestId: '',
  nFolds: 5,
  trainRatio: 0.7,
  windowType: 'expanding' as 'expanding' | 'rolling',
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
  try { backtestList.value = (await backtestApi.list({ size: 20 })).data || [] } catch {}
}

const runValidation = async () => {
  if (!config.backtestId) { message.warning('请选择回测任务'); return }
  loading.value = true
  try {
    result.value = await validationApi.walkForward({
      backtest_id: config.backtestId,
      n_folds: config.nFolds,
      window_type: config.windowType,
      train_ratio: config.trainRatio,
    })
    message.success('验证完成')
  } catch { message.error('验证失败') }
  finally { loading.value = false }
}

onMounted(() => { fetchBacktestList() })
</script>
