<template>
  <div class="page-container">
    <div class="page-header"><div class="page-title">因子分层</div></div>
    <a-row :gutter="16">
      <a-col :span="8">
        <a-card title="分层配置">
          <a-form layout="vertical">
            <a-form-item label="回测任务">
              <a-select v-model:value="config.backtestId" style="width: 100%">
                <a-select-option v-for="bt in backtestList" :key="bt.task_id" :value="bt.task_id">{{ bt.task_id }}</a-select-option>
              </a-select>
            </a-form-item>
            <a-form-item label="分层数"><a-input-number v-model:value="config.nGroups" :min="3" :max="10" style="width: 100%" /></a-form-item>
            <a-form-item><a-button type="primary" block @click="runAnalysis" :loading="loading">开始分析</a-button></a-form-item>
          </a-form>
        </a-card>
      </a-col>
      <a-col :span="16">
        <a-card title="分层结果">
          <template v-if="result">
            <a-row :gutter="16" style="margin-bottom: 16px">
              <a-col :span="8"><a-statistic title="多空收益" :value="(result.long_short_return * 100).toFixed(2)" suffix="%" /></a-col>
              <a-col :span="8"><a-statistic title="最佳组" :value="result.best_group" /></a-col>
              <a-col :span="8"><a-statistic title="最佳组收益" :value="(result.best_group_return * 100).toFixed(2)" suffix="%" /></a-col>
            </a-row>
            <a-table :columns="layerColumns" :dataSource="result.groups" :rowKey="(_, i) => `group-${i}`" :pagination="false" size="small" />
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
const config = reactive({ backtestId: '', nGroups: 5 })
const layerColumns = [
  { title: '组别', dataIndex: 'group', width: 80 },
  { title: '收益', dataIndex: 'return', width: 100 },
  { title: '股票数', dataIndex: 'count', width: 80 },
]
const fetchBacktestList = async () => { try { const r = await request.get('/api/v1/backtest', { params: { size: 20 } }); backtestList.value = r.data?.data || [] } catch {} }
const runAnalysis = async () => {
  if (!config.backtestId) { message.warning('请选择回测任务'); return }
  loading.value = true
  try { const r = await request.post('/api/v1/research/layering', config); result.value = r.data; message.success('完成') } catch { message.error('失败') }
  finally { loading.value = false }
}
onMounted(() => { fetchBacktestList() })
</script>
<style scoped>.page-container { padding: 0; }.page-header { margin-bottom: 16px; }.page-title { font-size: 18px; font-weight: 600; }</style>
