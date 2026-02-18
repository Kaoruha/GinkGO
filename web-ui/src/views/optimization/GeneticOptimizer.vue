<template>
  <div class="page-container">
    <div class="page-header"><div class="page-title">遗传算法优化</div></div>
    <a-row :gutter="16">
      <a-col :span="8">
        <a-card title="优化配置">
          <a-form layout="vertical">
            <a-form-item label="策略选择">
              <a-select v-model:value="config.strategyId" style="width: 100%">
                <a-select-option v-for="s in strategyList" :key="s.id" :value="s.id">{{ s.name }}</a-select-option>
              </a-select>
            </a-form-item>
            <a-form-item label="种群大小"><a-input-number v-model:value="config.populationSize" :min="10" :max="200" style="width: 100%" /></a-form-item>
            <a-form-item label="迭代次数"><a-input-number v-model:value="config.generations" :min="10" :max="500" style="width: 100%" /></a-form-item>
            <a-form-item label="变异率"><a-input-number v-model:value="config.mutationRate" :min="0.01" :max="0.5" :step="0.01" style="width: 100%" /></a-form-item>
            <a-form-item><a-button type="primary" block @click="runOptimization" :loading="loading">开始优化</a-button></a-form-item>
          </a-form>
        </a-card>
      </a-col>
      <a-col :span="16">
        <a-card title="优化结果">
          <template v-if="result">
            <a-row :gutter="16" style="margin-bottom: 16px">
              <a-col :span="6"><a-statistic title="总迭代" :value="result.generations" /></a-col>
              <a-col :span="6"><a-statistic title="最佳收益" :value="(result.best_fitness * 100).toFixed(2)" suffix="%" /></a-col>
              <a-col :span="6"><a-statistic title="收敛代数" :value="result.convergence_gen" /></a-col>
              <a-col :span="6"><a-statistic title="最优参数" :value="result.best_params" /></a-col>
            </a-row>
            <a-table :columns="genColumns" :dataSource="result.history" :rowKey="(_, i) => `gen-${i}`" :pagination="false" size="small" />
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
const config = reactive({ strategyId: '', populationSize: 50, generations: 100, mutationRate: 0.1 })
const genColumns = [
  { title: '代数', dataIndex: 'generation', width: 80 },
  { title: '最佳适应度', dataIndex: 'best_fitness', width: 120 },
  { title: '平均适应度', dataIndex: 'avg_fitness', width: 120 },
  { title: '多样性', dataIndex: 'diversity', width: 100 },
]
const fetchStrategyList = async () => { try { const r = await request.get('/api/v1/components/strategies'); strategyList.value = (r.data || []).map((f: any) => ({ id: f.name || f.uuid, name: f.name || f.uuid })) } catch {} }
const runOptimization = async () => {
  if (!config.strategyId) { message.warning('请选择策略'); return }
  loading.value = true
  try { const r = await request.post('/api/v1/optimization/genetic', config); result.value = r.data; message.success('完成') } catch { message.error('失败') }
  finally { loading.value = false }
}
onMounted(() => { fetchStrategyList() })
</script>
<style scoped>.page-container { padding: 0; }.page-header { margin-bottom: 16px; }.page-title { font-size: 18px; font-weight: 600; }</style>
