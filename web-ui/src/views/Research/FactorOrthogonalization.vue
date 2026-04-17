<template>
  <div class="factor-orthogonalization">
    <div class="page-header">
      <h1 class="page-title">因子正交化</h1>
      <button class="btn-secondary" @click="$router.push('/portfolio')">选择因子</button>
    </div>

    <!-- 配置卡片 -->
    <div class="card">
      <div class="card-header">
        <h3>正交化配置</h3>
      </div>
      <div class="card-body">
        <div class="form-row">
          <div class="form-group full-width">
            <label class="form-label">选择要正交化的因子</label>
            <select v-model="selectedFactorsList" multiple class="form-select" style="width: 100%">
              <option v-for="f in availableFactors" :key="f.name" :value="f.name">
                {{ f.label }} ({{ f.category }})
              </option>
            </select>
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">正交化方法</label>
            <select v-model="method" class="form-select">
              <option value="gram-schmidt">Gram-Schmidt</option>
              <option value="symmetric-orthogonalize">对称正交化</option>
              <option value="residual">残差正交化</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">保留因子数</label>
            <input v-model.number="keepFactors" type="number" min="1" class="form-input" />
          </div>
        </div>
        <div class="form-actions">
          <button class="btn-primary" :disabled="processing" @click="startOrthogonalize">
            {{ processing ? '处理中...' : '开始正交化' }}
          </button>
          <button class="btn-secondary" @click="resetConfig">重置</button>
        </div>
      </div>
    </div>

    <!-- 结果卡片 -->
    <div v-if="results" class="card">
      <div class="card-header">
        <h3>正交化结果</h3>
        <button class="btn-secondary" @click="exportResults">导出结果</button>
      </div>
      <div class="card-body">
        <!-- 统计卡片 -->
        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-label">去相关效果</div>
            <div class="stat-value">平均相关系数 -{{ avgCorrReduction.toFixed(3) }}</div>
            <div class="stat-sub">最大相关系数 -{{ maxCorrReduction.toFixed(3) }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">因子保留统计</div>
            <div class="stat-value">保留 {{ results?.kept_factors || 0 }} 个</div>
            <div class="stat-sub">剔除 {{ results?.removed_factors || 0 }} 个</div>
          </div>
        </div>

        <!-- 因子表格 -->
        <div v-if="factorList.length > 0" class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>因子名称</th>
                <th>IC保留</th>
                <th>IC下降</th>
                <th>相关后</th>
                <th>状态</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="record in factorList" :key="record.name">
                <td>{{ record.label }}</td>
                <td>
                  <span :class="record.ic_preserve > 0 ? 'text-success' : 'text-danger'">
                    {{ record.ic_preserve > 0 ? '+' : '' }}{{ (record.ic_preserve * 100).toFixed(2) }}%
                  </span>
                </td>
                <td>
                  <span v-if="getIcChangeStatus(record.ic_post)" class="tag" :class="getIcChangeClass(record.ic_post)">
                    {{ getIcChangeStatus(record.ic_post) }}
                  </span>
                </td>
                <td>{{ record.correlation_after?.toFixed(3) || '-' }}</td>
                <td>{{ record.status }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

// 可用因子（模拟）
const availableFactors = ref([
  { name: 'momentum', label: '动量因子', category: '技术' },
  { name: 'reversal', label: '反转因子', category: '技术' },
  { name: 'volatility', label: '波动率因子', category: '技术' },
  { name: 'liquidity', label: '流动性因子', category: '技术' },
  { name: 'size', label: '市值因子', category: '基本面' },
  { name: 'value', label: '价值因子', category: '基本面' },
])

const selectedFactors = ref<string[]>([])
const selectedFactorsList = ref<any[]>([])
const method = ref('gram-schmidt')
const keepFactors = ref(2)

const processing = ref(false)
const results = ref(null)

const originalCorr = ref<any[]>([])
const orthogonalizedCorr = ref<any[]>([])

// 计算属性：多选列表
watch(() => selectedFactors.value, (newVal) => {
  selectedFactorsList.value = newVal
})

const factorList = computed(() => {
  if (!results.value) return []
  return results.value.factors.map((f: any) => ({
    name: f.name,
    label: f.label,
    ic_preserve: f.ic_preserve,
    ic_post: f.ic_post,
    correlation_after: f.correlation_after,
    status: f.kept ? '保留' : '剔除'
  }))
})

const avgCorrReduction = computed(() => {
  if (!results.value) return 0
  const avgOriginal = results.value.avg_correlation_original || 0
  const avgAfter = results.value.avg_correlation_orthogonalized || 0
  return avgOriginal - avgAfter
})

const maxCorrReduction = computed(() => {
  if (!results.value) return 0
  const maxOriginal = Math.max(...originalCorr.value.map((c: any) => Math.abs(c.value)))
  const maxAfter = Math.max(...orthogonalizedCorr.value.map((c: any) => Math.abs(c.value)))
  return maxOriginal - maxAfter
})

const startOrthogonalize = async () => {
  if (selectedFactorsList.value.length < 2) {
    console.warn('请至少选择2个因子进行正交化')
    return
  }

  processing.value = true
  try {
    await simulateOrthogonalization()
    console.log('正交化完成')
  } catch (e) {
    console.error('正交化失败')
  } finally {
    processing.value = false
  }
}

const simulateOrthogonalization = async () => {
  // 模拟正交化结果
  const icPreserveResults = selectedFactorsList.value.map((fName, idx) => ({
    name: fName,
    label: availableFactors.value.find((f: any) => f.name === fName)?.label || fName,
    ic_preserve: Math.random() * 0.1 - 0.05,
    ic_post: Math.random() * 0.15 - 0.1,
    correlation_after: Math.random() * 0.1,
    kept: Math.random() > 0.3
  }))

  results.value = {
    avg_correlation_original: Math.random() * 0.6,
    avg_correlation_orthogonalized: Math.random() * 0.2,
    kept_factors: icPreserveResults.filter((f: any) => f.kept).length,
    removed_factors: icPreserveResults.filter((f: any) => !f.kept).length,
    factors: icPreserveResults
  }
}

const getCorrColor = (value: number) => {
  if (Math.abs(value) < 0.1) return '#52c41a'
  if (Math.abs(value) < 0.3) return '#722ed1f'
  if (Math.abs(value) < 0.5) return '#faad14'
  return '#999'
}

const getIcChangeStatus = (value: number) => {
  const absValue = Math.abs(value)
  if (absValue > 0.1) return '显著提升'
  if (absValue > 0.05) return '稳定'
  return '下降'
}

const getIcChangeClass = (value: number) => {
  const absValue = Math.abs(value)
  if (absValue > 0.1) return 'tag-green'
  if (absValue > 0.05) return 'tag-orange'
  return 'tag-red'
}

const resetConfig = () => {
  selectedFactors.value = []
  results.value = null
}

const exportResults = () => {
  if (!results.value) {
    console.warn('没有可导出的结果')
    return
  }
  console.log('导出正交化结果...')
}
</script>

<style scoped>
.factor-orthogonalization {
  padding: 16px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.page-title {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: #ffffff;
}

.form-group.full-width {
  flex: 1;
}

.form-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
}

.btn-primary:hover:not(:disabled) {
  background: #40a9ff;
}

.stat-sub {
  font-size: 12px;
  color: #8a8a9a;
}

.table-wrapper {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th,
.data-table td {
  padding: 12px;
  text-align: left;
  border-bottom: 1px solid #2a2a3e;
}

.data-table th {
  background: #2a2a3e;
  color: #ffffff;
  font-weight: 500;
  font-size: 13px;
}

.data-table td {
  color: #ffffff;
  font-size: 14px;
}

.text-success {
  color: #52c41a;
}

.text-danger {
  color: #f5222d;
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
