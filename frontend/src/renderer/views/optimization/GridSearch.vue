<template>
  <PageLayout>
    <template #title>
      网格搜索
    </template>
    <template #description>
      穷举所有参数组合，保证找到全局最优。适合2-3个参数，计算量较大。
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
        <h3>搜索配置</h3>
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
            <label class="form-label">参数配置 (JSON)</label>
            <input
              v-model="config.params"
              type="text"
              placeholder="{&quot;param1&quot;: [1, 2, 3]}"
              class="form-input"
              style="width: 300px"
            >
          </div>
          <div class="form-group">
            <!-- stub 页:后端接口未实现,主按钮置禁用而非可点(失败提示前置) -->
            <button
              class="btn-primary"
              :disabled="true"
              title="后端接口开发中，暂不可用"
              @click="runOptimization"
            >
              {{ loading ? '搜索中...' : '开始搜索' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 结果卡片 -->
    <div class="card">
      <div class="card-header">
        <h3>搜索结果</h3>
      </div>
      <div class="card-body">
        <div v-if="result">
          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-label">
                总组合数
              </div>
              <div class="stat-value">
                {{ result.total_combinations }}
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-label">
                最佳收益
              </div>
              <div
                class="stat-value"
                :class="result.best_return >= 0 ? 'stat-danger' : 'stat-success'"
              >
                {{ formatPercent(result.best_return) }}
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-label">
                最佳参数
              </div>
              <div class="stat-value stat-small">
                {{ result.best_params }}
              </div>
            </div>
          </div>

          <div
            v-if="result.top_results && result.top_results.length > 0"
            class="table-wrapper"
          >
            <table class="data-table">
              <thead>
                <tr>
                  <th class="num">
                    排名
                  </th>
                  <th>参数</th>
                  <th class="num">
                    收益
                  </th>
                  <th class="num">
                    夏普比率
                  </th>
                </tr>
              </thead>
              <tr
                v-for="(record, i) in result.top_results"
                :key="`result-${i}`"
              >
                <td class="num">
                  {{ record.rank }}
                </td>
                <td>{{ record.params }}</td>
                <td class="num">
                  {{ formatPercent(record.total_return) }}
                </td>
                <td class="num">
                  {{ formatDecimal(record.sharpe_ratio) }}
                </td>
              </tr>
            </table>
          </div>
        </div>
        <EmptyState
          v-else
          description="请配置参数并开始搜索"
          hint="stub · 后端接口未接入"
        />
      </div>
    </div>
  </PageLayout>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import PageLayout from '@/components/common/PageLayout.vue'
import { formatDecimal, formatPercent } from '@/utils/format'
import { message } from '@/utils/toast'
import EmptyState from '@/components/common/EmptyState.vue'

const loading = ref(false)
const strategyList = ref<any[]>([])
const result = ref<any>(null)
const config = reactive({ strategyId: '', params: '' })

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
    // TODO: 调用 API 进行网格搜索
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
