<template>
  <PageLayout>
    <template #title>
      贝叶斯优化
    </template>
    <template #description>
      基于概率模型的智能搜索，利用已有结果推断下一组参数。计算效率最高。
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
        <h3>优化配置</h3>
      </div>
      <div class="card-body">
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">策略选择</label>
            <select
              v-model="config.strategyId"
              class="form-select"
            >
              <option value="">
                选择策略
              </option>
              <option
                v-for="s in strategyList"
                :key="s.id"
                :value="s.id"
              >
                {{ s.name }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">迭代次数</label>
            <input
              v-model.number="config.nIterations"
              type="number"
              min="10"
              max="200"
              class="form-input"
            >
          </div>
          <div class="form-group">
            <label class="form-label">初始点数</label>
            <input
              v-model.number="config.nInitial"
              type="number"
              min="3"
              max="20"
              class="form-input"
            >
          </div>
          <div class="form-group">
            <button
              class="btn-primary"
              :disabled="loading"
              @click="runOptimization"
            >
              {{ loading ? '优化中...' : '开始优化' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 结果卡片 -->
    <div class="card">
      <div class="card-header">
        <h3>优化结果</h3>
      </div>
      <div class="card-body">
        <div v-if="result">
          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-label">
                总迭代
              </div>
              <div class="stat-value">
                {{ result.total_iterations }}
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-label">
                最佳收益
              </div>
              <div
                class="stat-value"
                :class="result.best_value >= 0 ? 'stat-danger' : 'stat-success'"
              >
                {{ formatPercent(result.best_value) }}
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-label">
                最优参数
              </div>
              <div class="stat-value stat-small">
                {{ result.best_params }}
              </div>
            </div>
          </div>

          <div
            v-if="result.history && result.history.length > 0"
            class="table-wrapper"
          >
            <table class="data-table">
              <thead>
                <tr>
                  <th class="num">
                    迭代
                  </th>
                  <th>参数</th>
                  <th class="num">
                    目标值
                  </th>
                  <th class="num">
                    不确定性
                  </th>
                </tr>
              </thead>
              <tr
                v-for="(record, i) in result.history"
                :key="`iter-${i}`"
              >
                <td class="num">
                  {{ record.iteration }}
                </td>
                <td>{{ record.params }}</td>
                <td class="num">
                  {{ formatDecimal(record.score, 4) }}
                </td>
                <td class="num">
                  {{ formatDecimal(record.uncertainty, 4) }}
                </td>
              </tr>
            </table>
          </div>
        </div>
        <EmptyState
          v-else
          description="请配置参数并开始优化"
        />
      </div>
    </div>
  </PageLayout>
</template>

<script setup lang="ts">
import EmptyState from '@/components/common/EmptyState.vue'
import { ref, reactive, onMounted } from 'vue'
import PageLayout from '@/components/common/PageLayout.vue'
import { formatDecimal, formatPercent } from '@/utils/format'
import { message } from '@/utils/toast'

const loading = ref(false)
const strategyList = ref<any[]>([])
const result = ref<any>(null)
const config = reactive({ strategyId: '', nIterations: 50, nInitial: 5 })

const fetchStrategyList = async () => {
  // TODO: 调用 API 获取策略列表
  strategyList.value = []
}

const runOptimization = async () => {
  if (!config.strategyId) {
    message.warning('请选择策略')
    return
  }
  loading.value = true
  try {
    // TODO: 调用 API 进行贝叶斯优化
    await new Promise(resolve => setTimeout(resolve, 1000))
    console.log('完成')
  } catch {
    console.error('失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchStrategyList()
})
</script>

<style scoped>
.stat-small {
  font-size: 14px;
}

.stat-danger {
  color: hsl(var(--error));
}

.table-wrapper {
  overflow-x: clip;
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
