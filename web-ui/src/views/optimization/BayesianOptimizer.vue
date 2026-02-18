<template>
  <div class="page-container">
    <div class="page-header"><div class="page-title">贝叶斯优化</div></div>
    <a-row :gutter="16">
      <a-col :span="8">
        <a-card title="优化配置">
          <a-form layout="vertical">
            <a-form-item label="策略选择">
              <a-select v-model:value="config.strategyId" style="width: 100%">
                <a-select-option v-for="s in strategyList" :key="s.id" :value="s.id">{{ s.name }}</a-select-option>
              </a-select>
            </a-form-item>
            <a-form-item label="迭代次数"><a-input-number v-model:value="config.nIterations" :min="10" :max="200" style="width: 100%" /></a-form-item>
            <a-form-item label="初始点数"><a-input-number v-model:value="config.nInitial" :min="3" :max="20" style="width: 100%" /></a-form-item>
            <a-form-item><a-button type="primary" block @click="runOptimization" :loading="loading">开始优化</a-button></a-form-item>
          </a-form>
        </a-card>
      </a-col>
      <a-col :span="16">
        <a-card title="优化结果">
          <template v-if="result">
            <a-row :gutter="16" style="margin-bottom: 16px">
              <a-col :span="8"><a-statistic title="总迭代" :value="result.total_iterations" /></a-col>
              <a-col :span="8"><a-statistic title="最佳收益" :value="(result.best_value * 100).toFixed(2)" suffix="%" /></a-col>
              <a-col :span="8"><a-statistic title="最优参数" :value="result.best_params" /></a-col>
            </a-row>
            <a-table :columns="iterColumns" :dataSource="result.history" :rowKey="(_, i) => `iter-${i}`" :pagination="false" size="small" />
          </template>
          <a-empty v-else />
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>
<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import request from '@/api/request'
const loading = ref(false), strategyList = ref<any[]>([]), result = ref<any>(null)
const config = reactive({ strategyId: '', nIterations: 50, nInitial: 5 })
const iterColumns = [
  { title: '迭代', dataIndex: 'iteration', width: 60 },
  { title: '参数', dataIndex: 'params', width: 150 },
  { title: '目标值', dataIndex: 'value', width: 100 },
  { title: '采集函数', dataIndex: 'acquisition', width: 100 },
]
const fetchStrategyList = async () => { try { const r = await request.get('/api/v1/components/strategies'); strategyList.value = (r.data || []).map((f: any) => ({ id: f.name || f.uuid, name: f.name || f.uuid })) } catch {} }
const runOptimization = async () => {
  if (!config.strategyId) { message.warning('请选择策略'); return }
  loading.value = true
  try { const r = await request.post('/api/v1/optimization/bayesian', config); result.value = r.data; message.success('完成') } catch { message.error('失败') }
  finally { loading.value = false }
}
onMounted(() => { fetchStrategyList() })
</script>
<style scoped>.page-container { padding: 0; }.page-header { margin-bottom: 16px; }.page-title { font-size: 18px; font-weight: 600; }</style>
