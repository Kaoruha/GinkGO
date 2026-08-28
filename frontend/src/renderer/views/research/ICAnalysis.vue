<template>
  <PageLayout>
    <template #title>
      IC 分析
    </template>
    <template #description>
      评估因子对未来收益的预测能力。IC均值>0.05为强因子，ICIR>0.5为优秀因子。
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
        <h3>因子配置</h3>
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
            <label class="form-label">收益周期</label>
            <select
              v-model.number="config.returnPeriod"
              class="form-select"
            >
              <option :value="1">
                1日
              </option>
              <option :value="5">
                5日
              </option>
              <option :value="10">
                10日
              </option>
              <option :value="20">
                20日
              </option>
            </select>
          </div>
          <div class="form-group">
            <!-- stub 页:后端接口未实现,主按钮置禁用而非可点(失败提示前置) -->
            <button
              class="btn-primary"
              :disabled="true"
              title="后端接口开发中，暂不可用"
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
        <h3>IC 统计结果</h3>
      </div>
      <div class="card-body">
        <div v-if="result">
          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-label">
                IC 均值
              </div>
              <div class="stat-value">
                {{ formatDecimal(result.ic_mean, 4) }}
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-label">
                IC 标准差
              </div>
              <div class="stat-value">
                {{ formatDecimal(result.ic_std, 4) }}
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-label">
                ICIR
              </div>
              <div class="stat-value">
                {{ formatDecimal(result.icir, 4) }}
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-label">
                IC > 0 比例
              </div>
              <div class="stat-value">
                {{ formatPercent(result.ic_positive_ratio || 0) }}
              </div>
            </div>
          </div>

          <div
            v-if="result.ic_series && result.ic_series.length > 0"
            class="table-wrapper"
          >
            <table class="data-table">
              <thead>
                <tr>
                  <th>日期</th>
                  <th class="num">
                    IC
                  </th>
                  <th class="num">
                    Rank IC
                  </th>
                </tr>
              </thead>
              <tr
                v-for="(record, i) in result.ic_series"
                :key="`ic-${i}`"
              >
                <td>{{ record.date }}</td>
                <td class="num">
                  {{ formatDecimal(record.ic, 4) }}
                </td>
                <td class="num">
                  {{ formatDecimal(record.rank_ic, 4) }}
                </td>
              </tr>
            </table>
          </div>
        </div>
        <EmptyState
          v-else
          description="请配置参数并开始分析"
          hint="stub · 后端接口未接入"
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

const loading = ref(false)
const backtestList = ref<any[]>([])
const result = ref<any>(null)

const config = reactive({
  backtestId: '',
  returnPeriod: 5,
})

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
    // TODO: 调用 API 进行 IC 分析
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
