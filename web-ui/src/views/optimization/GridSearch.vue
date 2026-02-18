<template>
  <div class="page-container">
    <div class="page-header"><div class="page-title">网格搜索</div></div>
    <a-row :gutter="16">
      <a-col :span="8">
        <a-card title="搜索配置">
          <a-form layout="vertical">
            <a-form-item label="策略选择">
              <a-select v-model:value="config.strategyId" style="width: 100%">
                <a-select-option v-for="s in strategyList" :key="s.id" :value="s.id">{{ s.name }}</a-select-option>
              </a-select>
            </a-form-item>
            <a-form-item label="参数配置 (JSON)">
              <a-textarea v-model:value="config.params" :rows="5" placeholder='{"param1": [1, 2, 3], "param2": [0.1, 0.2]}' />
            </a-form-item>
            <a-form-item><a-button type="primary" block @click="runOptimization" :loading="loading">开始搜索</a-button></a-form-item>
          </a-form>
        </a-card>
      </a-col>
      <a-col :span="16">
        <a-card title="搜索结果">
          <template v-if="result">
            <a-row :gutter="16" style="margin-bottom: 16px">
              <a-col :span="8"><a-statistic title="总组合数" :value="result.total_combinations" /></a-col>
              <a-col :span="8"><a-statistic title="最佳收益" :value="(result.best_return * 100).toFixed(2)" suffix="%" /></a-col>
              <a-col :span="8"><a-statistic title="最佳参数" :value="result.best_params" /></a-col>
            </a-row>
            <a-table :columns="resultColumns" :dataSource="result.top_results" :rowKey="(_, i) => `result-${i}`" :pagination="false" size="small" />
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
const config = reactive({ strategyId: '', params: '' })
const resultColumns = [
  { title: '排名', dataIndex: 'rank', width: 60 },
  { title: '参数', dataIndex: 'params', width: 200 },
  { title: '收益', dataIndex: 'return', width: 100 },
  { title: '夏普比率', dataIndex: 'sharpe', width: 100 },
]
const fetchStrategyList = async () => { try { const r = await request.get('/api/v1/components/strategies'); strategyList.value = (r.data || []).map((f: any) => ({ id: f.name || f.uuid, name: f.name || f.uuid })) } catch {} }
const runOptimization = async () => {
  if (!config.strategyId) { message.warning('请选择策略'); return }
  loading.value = true
  try { const r = await request.post('/api/v1/optimization/grid', { strategy_id: config.strategyId, params: JSON.parse(config.params || '{}') }); result.value = r.data; message.success('完成') } catch { message.error('失败') }
  finally { loading.value = false }
}
onMounted(() => { fetchStrategyList() })
</script>
<style scoped>.page-container { padding: 0; }.page-header { margin-bottom: 16px; }.page-title { font-size: 18px; font-weight: 600; }</style>
