<template>
  <PageLayout>
    <template #title>
      遗传算法优化
    </template>
    <template #description>
      模拟生物进化进行参数搜索，适合高维参数空间。可能陷入局部最优。
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
            <label class="form-label">种群大小</label>
            <input
              v-model.number="config.populationSize"
              type="number"
              min="10"
              max="200"
              class="form-input"
            >
          </div>
          <div class="form-group">
            <label class="form-label">迭代次数</label>
            <input
              v-model.number="config.generations"
              type="number"
              min="10"
              max="500"
              class="form-input"
            >
          </div>
          <div class="form-group">
            <label class="form-label">变异率</label>
            <input
              v-model.number="config.mutationRate"
              type="number"
              min="0.01"
              max="0.5"
              step="0.01"
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
                {{ result.generations }}
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-label">
                最佳收益
              </div>
              <div
                class="stat-value"
                :class="result.best_fitness >= 0 ? 'stat-danger' : 'stat-success'"
              >
                {{ formatPercent(result.best_fitness) }}
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-label">
                收敛代数
              </div>
              <div class="stat-value">
                {{ result.convergence_gen }}
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
                    代数
                  </th>
                  <th class="num">
                    最佳适应度
                  </th>
                  <th class="num">
                    平均适应度
                  </th>
                  <th class="num">
                    多样性
                  </th>
                </tr>
              </thead>
              <tr
                v-for="(record, i) in result.history"
                :key="`gen-${i}`"
              >
                <td class="num">
                  {{ record.generation }}
                </td>
                <td class="num">
                  {{ formatDecimal(record.best_fitness, 4) }}
                </td>
                <td class="num">
                  {{ formatDecimal(record.avg_fitness, 4) }}
                </td>
                <td class="num">
                  {{ formatDecimal(record.diversity, 4) }}
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
const config = reactive({ strategyId: '', populationSize: 50, generations: 100, mutationRate: 0.1 })

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
    // TODO: 调用 API 进行遗传算法优化
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
