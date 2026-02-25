<template>
  <div class="page-container">
    <PageHeader title="蒙特卡洛模拟" description="基于历史收益统计特征随机模拟，评估策略风险分布和极端损失概率。">
      <template #tag><a-tag color="green">验证</a-tag></template>
    </PageHeader>

    <a-card title="模拟配置" class="config-card">
      <a-form layout="inline">
        <a-form-item label="回测任务">
          <a-select v-model:value="config.backtestId" placeholder="选择回测任务" style="width: 200px">
            <a-select-option v-for="bt in backtestList" :key="bt.run_id" :value="bt.run_id">{{ bt.run_id }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="模拟次数">
          <a-input-number v-model:value="config.nSimulations" :min="1000" :max="100000" :step="1000" style="width: 120px" />
        </a-form-item>
        <a-form-item label="置信水平">
          <a-select v-model:value="config.confidenceLevel" style="width: 80px">
            <a-select-option :value="0.9">90%</a-select-option>
            <a-select-option :value="0.95">95%</a-select-option>
            <a-select-option :value="0.99">99%</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item>
          <a-button type="primary" @click="runSimulation" :loading="loading">开始模拟</a-button>
        </a-form-item>
      </a-form>
    </a-card>

    <template v-if="result">
      <a-row :gutter="16" style="margin-bottom: 16px">
        <a-col :span="6"><StatCard title="VaR" :value="result.var" type="percent" color="negative" /></a-col>
        <a-col :span="6"><StatCard title="CVaR" :value="result.cvar" type="percent" color="negative" /></a-col>
        <a-col :span="6"><StatCard title="期望收益" :value="result.expected_return" type="percent" /></a-col>
        <a-col :span="6"><StatCard title="损失概率" :value="result.loss_probability" type="percent" /></a-col>
      </a-row>
      <a-card title="收益分布统计">
        <a-row :gutter="16">
          <a-col :span="6"><StatCard title="最大收益" :value="result.max_return" type="percent" /></a-col>
          <a-col :span="6"><StatCard title="最小收益" :value="result.min_return" type="percent" /></a-col>
          <a-col :span="6"><StatCard title="标准差" :value="result.std_dev" type="percent" /></a-col>
          <a-col :span="6"><StatCard title="偏度" :value="result.skewness" type="decimal" /></a-col>
        </a-row>
      </a-card>
    </template>
    <a-empty v-else description="请配置参数并开始模拟" />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { backtestApi, validationApi } from '@/api'
import type { MonteCarloResult } from '@/api'
import { PageHeader } from '@/components/layout'
import { StatCard } from '@/components/common'

const loading = ref(false)
const backtestList = ref<any[]>([])
const result = ref<MonteCarloResult | null>(null)

const config = reactive({
  backtestId: '',
  nSimulations: 10000,
  confidenceLevel: 0.95,
})

const fetchBacktestList = async () => {
  try { backtestList.value = (await backtestApi.list({ size: 20 })).data || [] } catch {}
}

const runSimulation = async () => {
  if (!config.backtestId) { message.warning('请选择回测任务'); return }
  loading.value = true
  try {
    result.value = await validationApi.monteCarlo({
      backtest_id: config.backtestId,
      n_simulations: config.nSimulations,
      confidence_level: config.confidenceLevel,
    })
    message.success('模拟完成')
  } catch { message.error('模拟失败') }
  finally { loading.value = false }
}

onMounted(() => { fetchBacktestList() })
</script>
