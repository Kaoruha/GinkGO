<template>
  <div class="page-container">
    <PageHeader
      title="因子分层"
      description="将股票按因子值分组，验证因子的选股效果。理想因子各组收益应单调递减，多空收益越高越好。"
    />
    <a-card title="分层配置" class="config-card">
      <a-form layout="inline">
        <a-form-item label="回测任务">
          <a-select v-model:value="config.backtestId" style="width: 200px">
            <a-select-option v-for="bt in backtestList" :key="bt.run_id" :value="bt.run_id">{{ bt.run_id }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="分层数">
          <a-input-number v-model:value="config.nGroups" :min="3" :max="10" style="width: 80px" />
        </a-form-item>
        <a-form-item>
          <a-button type="primary" @click="runAnalysis" :loading="loading">开始分析</a-button>
        </a-form-item>
      </a-form>
    </a-card>
    <a-card title="分层结果" class="result-card">
      <template v-if="result">
        <a-row :gutter="16" style="margin-bottom: 16px">
          <a-col :span="8"><StatCard title="多空收益" :value="result.long_short_return" type="percent" color="auto" /></a-col>
          <a-col :span="8"><StatCard title="最佳组" :value="result.best_group" type="decimal" :decimals="0" /></a-col>
          <a-col :span="8"><StatCard title="最佳组收益" :value="result.best_group_return" type="percent" color="auto" /></a-col>
        </a-row>
        <a-table :columns="layerColumns" :dataSource="result.groups" :rowKey="(_, i) => `group-${i}`" :pagination="false" size="small" />
      </template>
      <a-empty v-else />
    </a-card>
  </div>
</template>
<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { backtestApi, researchApi } from '@/api'
import type { FactorLayeringResult } from '@/api'
import { PageHeader } from '@/components/layout'
import { StatCard } from '@/components/common'

const loading = ref(false)
const backtestList = ref<any[]>([])
const result = ref<FactorLayeringResult | null>(null)
const config = reactive({ backtestId: '', nGroups: 5 })

const layerColumns = [
  { title: '组别', dataIndex: 'layer', width: 80 },
  { title: '收益', dataIndex: 'return_mean', width: 100 },
  { title: '股票数', dataIndex: 'count', width: 80 },
]

const fetchBacktestList = async () => {
  try { backtestList.value = (await backtestApi.list({ size: 20 })).data || [] } catch {}
}

const runAnalysis = async () => {
  if (!config.backtestId) { message.warning('请选择回测任务'); return }
  loading.value = true
  try { result.value = await researchApi.layering({ backtest_id: config.backtestId, n_layers: config.nGroups }); message.success('完成') }
  catch { message.error('失败') }
  finally { loading.value = false }
}

onMounted(() => { fetchBacktestList() })
</script>
