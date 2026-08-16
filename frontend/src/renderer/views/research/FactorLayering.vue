<template>
  <PageLayout>
    <template #title>
      因子分层
    </template>
    <template #description>
      将股票按因子值分组，验证因子的选股效果。理想因子各组收益应单调递减，多空收益越高越好。
    </template>

    <!-- 功能开发中:研究/优化/验证后端 API 未实现(记忆 arch_parameter_optimization_unwired / arch_factor_subsystem_dormant_75pct);
         此为占位骨架,配置后不会产出真实结果,加横幅以免用户误判可用(#4652 静默失败纪律) -->
    <div
      role="alert"
      style="display:flex;align-items:center;gap:8px;padding:10px 14px;margin-bottom:16px;background:hsl(var(--primary) / 0.08);border:1px solid hsl(var(--primary) / 0.3);border-left-width:3px;border-radius: var(--radius);color:hsl(var(--foreground));font-size:13px;"
    >
      <span aria-hidden="true">🚧</span>
      <span>该功能后端接口开发中，当前为预览骨架，暂不可用。</span>
    </div>

    <!-- 配置卡片 -->
    <div class="card">
      <div class="card-header">
        <h3>分层配置</h3>
      </div>
      <div class="card-body">
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">回测任务</label>
            <select
              v-model="config.backtestId"
              class="form-select"
            >
              <option value="">
                选择回测任务
              </option>
              <option
                v-for="bt in backtestList"
                :key="bt.task_id"
                :value="bt.task_id"
              >
                {{ bt.task_id }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">分层数</label>
            <input
              v-model.number="config.nGroups"
              type="number"
              min="3"
              max="10"
              class="form-input"
            >
          </div>
          <div class="form-group">
            <button
              class="btn-primary"
              :disabled="loading"
              @click="runAnalysis"
            >
              {{ loading ? '分析中...' : '开始分析' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 结果卡片 -->
    <div class="card">
      <div class="card-header">
        <h3>分层结果</h3>
      </div>
      <div class="card-body">
        <div v-if="result">
          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-label">
                多空收益
              </div>
              <div
                class="stat-value"
                :class="result.long_short_return >= 0 ? 'stat-danger' : 'stat-success'"
              >
                {{ ((result.long_short_return || 0) * 100).toFixed(2) }}%
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-label">
                最佳组
              </div>
              <div class="stat-value">
                {{ result.best_group || '-' }}
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-label">
                最佳组收益
              </div>
              <div
                class="stat-value"
                :class="result.best_group_return >= 0 ? 'stat-danger' : 'stat-success'"
              >
                {{ ((result.best_group_return || 0) * 100).toFixed(2) }}%
              </div>
            </div>
          </div>

          <div
            v-if="result.groups && result.groups.length > 0"
            class="table-wrapper"
          >
            <table class="data-table">
              <thead>
                <tr>
                  <th>组别</th>
                  <th class="num">
                    收益
                  </th>
                  <th class="num">
                    股票数
                  </th>
                </tr>
              </thead>
              <tr
                v-for="(record, i) in result.groups"
                :key="`group-${i}`"
              >
                <td>{{ record.layer }}</td>
                <td class="num">
                  <span :class="record.return_mean >= 0 ? 'text-danger' : 'text-success'">
                    {{ ((record.return_mean || 0) * 100).toFixed(2) }}%
                  </span>
                </td>
                <td class="num">
                  {{ record.count }}
                </td>
              </tr>
            </table>
          </div>
        </div>
        <EmptyState
          v-else
          description="请配置参数并开始分析"
        />
      </div>
    </div>
  </PageLayout>
</template>

<script setup lang="ts">
import EmptyState from '@/components/common/EmptyState.vue'
import { ref, reactive, onMounted } from 'vue'
import PageLayout from '@/components/common/PageLayout.vue'

const loading = ref(false)
const backtestList = ref<any[]>([])
const result = ref<any>(null)
const config = reactive({ backtestId: '', nGroups: 5 })

const fetchBacktestList = async () => {
  // TODO: 调用 API 获取回测列表
  backtestList.value = []
}

const runAnalysis = async () => {
  if (!config.backtestId) {
    console.warn('请选择回测任务')
    return
  }
  loading.value = true
  try {
    // TODO: 调用 API 进行因子分层分析
    await new Promise(resolve => setTimeout(resolve, 1000))
    console.log('完成')
  } catch {
    console.error('失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchBacktestList()
})
</script>

<style scoped>
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
