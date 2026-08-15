<template>
  <PageLayout>
    <template #title>因子正交化</template>
    <template #description>消除多因子之间的相关性，避免信息重复。正交化后因子相互独立，组合效果更好。</template>

    <!-- 骨架页横幅(#4652 纪律:后端 orthogonalize 接口未实现,禁止伪造 API 假装可用) -->
    <div role="alert" style="display:flex;align-items:center;gap:8px;padding:10px 14px;margin-bottom:16px;background:hsl(var(--primary) / 0.08);border:1px solid hsl(var(--primary) / 0.3);border-left-width:3px;border-radius: var(--radius);color:hsl(var(--foreground));font-size:13px;">
      <span aria-hidden="true">🚧</span>
      <span>该功能后端接口开发中，当前为预览骨架，暂不可用。</span>
    </div>

    <div class="card config-card">
      <div class="card-header">
        <h4>正交化配置</h4>
      </div>
      <div class="card-body">
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">回测任务</label>
            <select v-model="config.backtestId" class="form-select">
              <option value="">选择回测任务</option>
              <option v-for="bt in backtestList" :key="bt.task_id" :value="bt.task_id">{{ bt.task_id }}</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">正交化方法</label>
            <select v-model="config.method" class="form-select">
              <option value="gram_schmidt">Gram-Schmidt</option>
              <option value="pca">PCA</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">&nbsp;</label>
            <button class="btn-primary" :disabled="loading" @click="runAnalysis">
              {{ loading ? '分析中...' : '开始分析' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <div class="card result-card">
      <div class="card-header">
        <h4>相关性矩阵对比</h4>
      </div>
      <div class="card-body">
        <div v-if="result" class="stats-grid">
          <div class="stat-card">
            <span class="stat-value">{{ result.original_avg_corr?.toFixed(4) || '-' }}</span>
            <span class="stat-label">原始平均相关系数</span>
          </div>
          <div class="stat-card">
            <span class="stat-value">{{ result.orthogonal_avg_corr?.toFixed(4) || '-' }}</span>
            <span class="stat-label">正交后平均相关系数</span>
          </div>
        </div>
        <EmptyState v-else description="请先选择回测任务并开始分析" />
      </div>
    </div>
  </PageLayout>
</template>

<script setup lang="ts">
import EmptyState from '@/components/common/EmptyState.vue'
import { ref, reactive, onMounted } from 'vue'
import PageLayout from '@/components/common/PageLayout.vue'
import { backtestApi } from '@/api/modules/backtest'
import { message } from '@/utils/toast'

interface FactorOrthogonalizeResult {
  original_avg_corr: number
  orthogonal_avg_corr: number
}

const loading = ref(false)
const backtestList = ref<any[]>([])
const result = ref<FactorOrthogonalizeResult | null>(null)
const config = reactive({ backtestId: '', method: 'gram_schmidt' as 'gram_schmidt' | 'pca' | 'residual' })

const fetchBacktestList = async () => {
  try {
    // request.ts 拦截器已拆包:分页端点 resolve 即 {items,total,...}
    backtestList.value = (await backtestApi.list({ page: 1, size: 20 }))?.items || []
  } catch (e) {
    // 骨架页(横幅已声明不可用):回测列表拉取失败仅记日志,不弹错误
    console.error('Failed to load backtest list:', e)
  }
}

const runAnalysis = () => {
  if (!config.backtestId) {
    message.warning('请选择回测任务')
    return
  }
  // 后端 orthogonalize 接口未实现(见顶部横幅):明确告知不可用,不再伪造 API 假装成功
  message.warning('该功能后端接口开发中，暂不可用')
}

onMounted(() => {
  fetchBacktestList()
})
</script>

<style scoped>
.config-card {
  margin-bottom: 16px;
}

.result-card {
  margin-bottom: 0;
}

.card-header h4 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: hsl(var(--foreground));
}
@media (max-width: 768px) {
  .form-row {
    flex-direction: column;
    align-items: stretch;
  }

  .form-select,

  .stats-grid {
    grid-template-columns: 1fr;
  }
}
</style>
