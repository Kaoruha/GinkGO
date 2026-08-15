<template>
  <PageLayout>
    <template #title>
      <span class="tag tag-green">验证</span>
      走步验证
    </template>
    <template #description>时间序列交叉验证，评估策略样本外表现。退化程度大说明过拟合风险高。</template>

    <!-- 功能开发中:研究/优化/验证后端 API 未实现(记忆 arch_parameter_optimization_unwired / arch_factor_subsystem_dormant_75pct);
         此为占位骨架,配置后不会产出真实结果,加横幅以免用户误判可用(#4652 静默失败纪律) -->
    <div role="alert" style="display:flex;align-items:center;gap:8px;padding:10px 14px;margin-bottom:16px;background:hsl(var(--primary) / 0.08);border:1px solid hsl(var(--primary) / 0.3);border-left-width:3px;border-radius: var(--radius);color:hsl(var(--foreground));font-size:13px;">
      <span aria-hidden="true">🚧</span>
      <span>该功能后端接口开发中，当前为预览骨架，暂不可用。</span>
    </div>

    <!-- 配置卡片 -->
    <div class="card">
      <div class="card-header">
        <h3>验证配置</h3>
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
            <label class="form-label">折数</label>
            <input v-model.number="config.nFolds" type="number" min="2" max="10" class="form-input" style="width: 80px" />
          </div>
          <div class="form-group">
            <label class="form-label">训练期比例: {{ config.trainRatio }}</label>
            <input v-model.number="config.trainRatio" type="range" min="0.5" max="0.9" step="0.1" class="form-slider" />
          </div>
          <div class="form-group">
            <label class="form-label">窗口类型</label>
            <div class="radio-group">
              <label class="radio-label">
                <input type="radio" v-model="config.windowType" value="expanding" />
                <span>扩展窗口</span>
              </label>
              <label class="radio-label">
                <input type="radio" v-model="config.windowType" value="rolling" />
                <span>滚动窗口</span>
              </label>
            </div>
          </div>
          <div class="form-group">
            <button class="btn-primary" :disabled="loading" @click="runValidation">
              {{ loading ? '验证中...' : '开始验证' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 结果卡片 -->
    <div class="card">
      <div class="card-header">
        <h3>验证结果</h3>
      </div>
      <div class="card-body">
        <div v-if="result">
          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-label">平均训练收益</div>
              <div class="stat-value" :class="{ 'stat-danger': result.avg_train_return >= 0, 'stat-success': result.avg_train_return < 0 }">
                {{ (result.avg_train_return * 100).toFixed(2) }}%
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-label">平均测试收益</div>
              <div class="stat-value" :class="{ 'stat-danger': result.avg_test_return >= 0, 'stat-success': result.avg_test_return < 0 }">
                {{ (result.avg_test_return * 100).toFixed(2) }}%
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-label">退化程度</div>
              <div class="stat-value" :class="{ 'stat-danger': result.degradation >= 0, 'stat-success': result.degradation < 0 }">
                {{ (result.degradation * 100).toFixed(2) }}%
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-label">稳定性评分</div>
              <div class="stat-value">{{ result.stability_score?.toFixed(2) || '-' }}</div>
            </div>
          </div>

          <div v-if="result.folds && result.folds.length > 0" class="table-wrapper">
            <table class="data-table">
              <thead>
                <tr>
                  <th class="num">Fold</th>
                  <th>训练开始</th>
                  <th>训练结束</th>
                  <th>测试开始</th>
                  <th>测试结束</th>
                  <th class="num">训练收益</th>
                  <th class="num">测试收益</th>
                </tr>
              </thead>
                <tr v-for="(record, i) in result.folds" :key="`fold-${i}`">
                  <td class="num">{{ record.fold }}</td>
                  <td>{{ record.train_start }}</td>
                  <td>{{ record.train_end }}</td>
                  <td>{{ record.test_start }}</td>
                  <td>{{ record.test_end }}</td>
                  <td class="num">
                    <span :class="record.train_return >= 0 ? 'text-success' : 'text-danger'">
                      {{ (record.train_return * 100).toFixed(2) }}%
                    </span>
                  </td>
                  <td class="num">
                    <span :class="record.test_return >= 0 ? 'text-success' : 'text-danger'">
                      {{ (record.test_return * 100).toFixed(2) }}%
                    </span>
                  </td>
                </tr>
              
            </table>
          </div>
        </div>
        <EmptyState v-else description="请配置参数并开始验证" />
      </div>
    </div>
  </PageLayout>
</template>

<script setup lang="ts">
import EmptyState from '@/components/common/EmptyState.vue'
import { ref, reactive, onMounted } from 'vue'
import PageLayout from '@/components/common/PageLayout.vue'
import { message } from '@/utils/toast'

const loading = ref(false)
const backtestList = ref<any[]>([])
const result = ref<any>(null)

const config = reactive({
  backtestId: '',
  nFolds: 5,
  trainRatio: 0.7,
  windowType: 'expanding' as 'expanding' | 'rolling',
})

const fetchBacktestList = async () => {
  // TODO: 调用 API 获取回测列表
  backtestList.value = []
}

const runValidation = async () => {
  if (!config.backtestId) {
    message.warning('请选择回测任务')
    return
  }

  loading.value = true
  try {
    // TODO: 调用 API 进行走步验证
    await new Promise(resolve => setTimeout(resolve, 1000))
    console.log('验证完成')
  } catch {
    console.error('验证失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchBacktestList()
})
</script>

<style scoped>
.form-slider {
  width: 150px;
  accent-color: hsl(var(--primary));
}

.radio-group {
  display: flex;
  gap: 16px;
}

.radio-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: hsl(var(--foreground));
  cursor: pointer;
}

.radio-label input[type="radio"] {
  accent-color: hsl(var(--primary));
  cursor: pointer;
}

.stat-danger {
  color: hsl(var(--error));
}

.text-success {
  color: hsl(var(--success));
}

.text-danger {
  color: hsl(var(--error));
}

.table-wrapper {
  overflow-x: clip;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th,
.data-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid hsl(var(--border));
}

.data-table th {
  position: sticky;
  top: 0;
  z-index: 1;
  background: hsl(var(--border));
  color: hsl(var(--foreground));
  font-weight: 500;
  font-size: 13px;
}

.data-table td {
  color: hsl(var(--foreground));
  font-size: 14px;
}
@media (max-width: 768px) {
  .form-row {
    flex-direction: column;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }
}
</style>
