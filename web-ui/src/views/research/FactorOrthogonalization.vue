<template>
  <div class="page-container">
    <div class="page-header"><div class="page-title">因子正交化</div></div>
    <a-row :gutter="16">
      <a-col :span="8">
        <a-card title="正交化配置">
          <a-form layout="vertical">
            <a-form-item label="回测任务">
              <a-select v-model:value="config.backtestId" style="width: 100%">
                <a-select-option v-for="bt in backtestList" :key="bt.task_id" :value="bt.task_id">{{ bt.task_id }}</a-select-option>
              </a-select>
            </a-form-item>
            <a-form-item label="正交化方法">
              <a-select v-model:value="config.method" style="width: 100%">
                <a-select-option value="gram_schmidt">Gram-Schmidt</a-select-option>
                <a-select-option value="pca">PCA</a-select-option>
              </a-select>
            </a-form-item>
            <a-form-item><a-button type="primary" block @click="runAnalysis" :loading="loading">开始分析</a-button></a-form-item>
          </a-form>
        </a-card>
      </a-col>
      <a-col :span="16">
        <a-card title="相关性矩阵对比">
          <template v-if="result">
            <a-descriptions title="正交化前后对比" :column="2" size="small">
              <a-descriptions-item label="原始平均相关系数">{{ result.original_avg_corr?.toFixed(4) }}</a-descriptions-item>
              <a-descriptions-item label="正交后平均相关系数">{{ result.orthogonal_avg_corr?.toFixed(4) }}</a-descriptions-item>
            </a-descriptions>
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
const loading = ref(false), backtestList = ref<any[]>([]), result = ref<any>(null)
const config = reactive({ backtestId: '', method: 'gram_schmidt' })
const fetchBacktestList = async () => { try { const r = await request.get('/api/v1/backtest', { params: { size: 20 } }); backtestList.value = r.data?.data || [] } catch {} }
const runAnalysis = async () => {
  if (!config.backtestId) { message.warning('请选择回测任务'); return }
  loading.value = true
  try { const r = await request.post('/api/v1/research/orthogonalize', config); result.value = r.data; message.success('完成') } catch { message.error('失败') }
  finally { loading.value = false }
}
onMounted(() => { fetchBacktestList() })
</script>
<style scoped>.page-container { padding: 0; }.page-header { margin-bottom: 16px; }.page-title { font-size: 18px; font-weight: 600; }</style>
