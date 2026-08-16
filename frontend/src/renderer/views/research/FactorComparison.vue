<template>
  <PageLayout>
    <template #title>
      因子比较
    </template>
    <template #description>
      多因子横向对比，从IC、ICIR、换手率等维度综合评估，选择最优因子。
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
        <h3>比较配置</h3>
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
            <button
              class="btn-primary"
              :disabled="loading"
              @click="runAnalysis"
            >
              {{ loading ? '比较中...' : '开始比较' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 结果卡片 -->
    <div class="card">
      <div class="card-header">
        <h3>因子对比结果</h3>
      </div>
      <div class="card-body">
        <div v-if="result">
          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-label">
                最佳因子
              </div>
              <div class="stat-value stat-small">
                {{ result.best_factor || '-' }}
              </div>
            </div>
            <div class="stat-card">
              <div class="stat-label">
                综合评分
              </div>
              <div class="stat-value">
                {{ result.best_score?.toFixed(4) || '-' }}
              </div>
            </div>
          </div>

          <div
            v-if="result.factors && result.factors.length > 0"
            class="table-wrapper"
          >
            <table class="data-table">
              <thead>
                <tr>
                  <th>因子名</th>
                  <th class="num">
                    IC
                  </th>
                  <th class="num">
                    ICIR
                  </th>
                  <th class="num">
                    换手率
                  </th>
                </tr>
              </thead>
              <tr
                v-for="(record, i) in result.factors"
                :key="`factor-${i}`"
              >
                <td>{{ record.name }}</td>
                <td class="num">
                  {{ record.ic?.toFixed(4) || '-' }}
                </td>
                <td class="num">
                  {{ record.icir?.toFixed(4) || '-' }}
                </td>
                <td class="num">
                  {{ record.turnover?.toFixed(4) || '-' }}
                </td>
              </tr>
            </table>
          </div>
        </div>
        <EmptyState
          v-else
          description="请配置参数并开始比较"
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
const config = reactive({ backtestId: '' })

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
    // TODO: 调用 API 进行因子比较
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
.stat-small {
  font-size: 16px;
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
