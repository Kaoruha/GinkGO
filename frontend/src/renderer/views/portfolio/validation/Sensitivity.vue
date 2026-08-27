<template>
  <PageLayout>
    <template #title>
      <span class="tag tag-green">验证</span>
      敏感性分析
    </template>
    <template #description>
      评估策略对参数变化的敏感程度。敏感性低说明参数选择更稳健，不易过拟合。
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
        <h3>分析配置</h3>
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
            <label class="form-label">分析参数</label>
            <input
              v-model="config.paramName"
              type="text"
              placeholder="如: max_position"
              class="form-input"
            >
          </div>
          <div class="form-group">
            <label class="form-label">参数值</label>
            <input
              v-model="config.paramValues"
              type="text"
              placeholder="0.1,0.2,0.3,0.4"
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
        <h3>分析结果</h3>
      </div>
      <div class="card-body">
        <div
          v-if="result"
          class="stats-grid-three"
        >
          <div class="stat-card">
            <div class="stat-label">
              敏感性分数
            </div>
            <div class="stat-value">
              {{ result.sensitivity_score }}
            </div>
          </div>
          <div class="stat-card">
            <div class="stat-label">
              最优参数值
            </div>
            <div class="stat-value">
              {{ result.optimal_value }}
            </div>
          </div>
          <div class="stat-card">
            <div class="stat-label">
              最优收益
            </div>
            <div class="stat-value">
              {{ formatPercent(result.optimal_return) }}
            </div>
          </div>
        </div>

        <div
          v-if="result?.data_points && result.data_points.length > 0"
          class="table-wrapper"
        >
          <table class="data-table">
            <thead>
              <tr>
                <th class="num">
                  参数值
                </th>
                <th class="num">
                  收益率
                </th>
                <th class="num">
                  夏普比率
                </th>
                <th class="num">
                  最大回撤
                </th>
                <th>标记</th>
              </tr>
            </thead>
            <tr
              v-for="(record, i) in result.data_points"
              :key="`point-${i}`"
            >
              <td class="num">
                {{ record.param_value }}
              </td>
              <td class="num">
                <span :style="{ color: record.return >= 0 ? 'hsl(var(--success))' : 'hsl(var(--error))' }">
                  {{ formatPercent(record.return) }}
                </span>
              </td>
              <td class="num">
                {{ formatDecimal(record.sharpe_ratio) }}
              </td>
              <td class="num">
                {{ formatDecimal(record.max_drawdown) }}
              </td>
              <td>
                <span
                  v-if="record.is_optimal"
                  class="tag tag-green"
                >最优</span>
              </td>
            </tr>
          </table>
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
import { formatDecimal, formatPercent } from '@/utils/format'
import { message } from '@/utils/toast'

const loading = ref(false)
const backtestList = ref<any[]>([])
const result = ref<any>(null)

const config = reactive({ backtestId: '', paramName: '', paramValues: '' })

const fetchBacktestList = async () => {
  // TODO: 调用 API 获取回测列表
  backtestList.value = []
}

const runAnalysis = async () => {
  if (!config.backtestId) {
    message.warning('请选择回测任务')
    return
  }
  if (!config.paramName) {
    message.warning('请输入参数名称')
    return
  }
  if (!config.paramValues.trim()) {
    message.warning('请输入参数值列表')
    return
  }

  loading.value = true
  try {
    // TODO: 调用 API 进行敏感性分析
    await new Promise(resolve => setTimeout(resolve, 1000))
    console.log('分析完成')
  } catch {
    console.error('分析失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchBacktestList()
})
</script>

<style scoped>
.stats-grid-three {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 20px;
}

.table-wrapper {
  overflow-x: clip;
}

@media (max-width: 768px) {
  .form-row {
    flex-direction: column;
  }

  .stats-grid-three {
    grid-template-columns: 1fr;
  }
}
</style>
