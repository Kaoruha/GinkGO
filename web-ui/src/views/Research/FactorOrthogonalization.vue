<template>
  <div class="factor-orthogonalization">
    <a-card title="因子正交化">
      <template #extra>
        <a-button @click="$router.push('/portfolio')">选择因子</a-button>
      </template>

      <!-- Custom -->
      <a-row :gutter="16" class="mb-4">
        <a-col :span="24">
          <a-form-item label="选择要正交化的因子">
            <a-select
              v-model:value="selectedFactors"
              mode="multiple"
              placeholder="选择2个以上因子"
              style="width: 100%"
            >
              <a-select-option v-for="f in availableFactors" :key="f.name" :value="f.name">
                {{ f.label }} ({{ f.category }})
              </a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
      </a-row>

      <!-- Custom -->
      <a-row :gutter="16" class="mb-4">
        <a-col :span="12">
          <a-form-item label="正交化方法">
            <a-select v-model:value="method">
              <a-select-option value="gram-schmidt">Gram-Schmidt</a-select-option>
              <a-select-option value="symmetric-orthogonalize">对称正交化</a-select-option>
              <a-select-option value="residual">残差正交化</a-select-option>
            </a-select>
          </a-form-item>
        </a-col>
        <a-col :span="12">
          <a-form-item label="保留因子数">
            <a-input-number v-model:value="keepFactors" :min="1" style="width: 100%" />
          </a-form-item>
        </a-col>
      </a-row>

      <!-- Custom -->
      <a-row :gutter="16" class="mb-4">
        <a-col :span="24">
          <a-range-picker v-model:value="dateRange" style="width: 100%" />
        </a-col>
      </a-row>

      <!-- Custom -->
      <div class="action-buttons">
        <a-space>
          <a-button type="primary" :loading="processing" @click="startOrthogonalize">
            开始正交化
          </a-button>
          <a-button @click="resetConfig">重置</a-button>
        </a-space>
      </div>
    </a-card>

    <!-- Custom -->
    <a-card v-if="results" title="正交化结果" class="mt-4">
      <template #extra>
        <a-button @click="exportResults">导出结果</a-button>
      </template>

      <!-- Custom -->
      <a-descriptions title="原始因子相关性" bordered :column="2" size="small" class="mb-4">
        <a-descriptions-item v-for="(corr, idx) in originalCorr" :key="idx">
          <span>{{ corr.factor1 }} × {{ corr.factor2 }}</span>
          <span :style="{ color: getCorrColor(corr.value) }">{{ corr.value.toFixed(3) }}</span>
        </a-descriptions-item>
      </a-descriptions>

      <!-- Custom -->
      <a-descriptions title="正交化后相关性" bordered :column="2" size="small" class="mb-4">
        <a-descriptions-item v-for="(corr, idx) in orthogonalizedCorr" :key="idx">
          <span>{{ corr.factor1 }} × {{ corr.factor2 }}</span>
          <span :style="{ color: getCorrColor(corr.value) }">{{ corr.value.toFixed(3) }}</span>
        </a-descriptions-item>
      </a-descriptions>

      <!-- Custom -->
      <a-row :gutter="16" class="mb-4">
        <a-col :span="6">
          <a-card title="去相关效果" size="small">
            <a-statistic title="平均相关系数" :value="avgCorrReduction" :precision="3" />
            <a-statistic title="最大相关系数" :value="maxCorrReduction" :precision="3" />
          </a-card>
        </a-col>
        <a-col :span="6">
          <a-card title="因子保留统计" size="small">
            <a-statistic title="保留因子数" :value="results?.kept_factors || 0" />
            <a-statistic title="剔除因子数" :value="results?.removed_factors || 0" />
          </a-card>
        </a-col>
      </a-row>

      <!-- Custom -->
      <a-table
        :columns="columns"
        :data-source="factorList"
        :pagination="false"
        size="small"
        class="mt-4"
      >
        <template #bodyCell="{ column, record }">
          <span v-if="column.dataIndex === 'ic_preserve'" :style="{ color: record.ic_preserve > 0 ? '#52c41a' : '#f5222d' }">
            {{ record.ic_preserve > 0 ? '+' : '' }}{{ (record.ic_preserve * 100).toFixed(2) }}%
          </span>
          <span v-if="column.dataIndex === 'ic_post' && getIcChangeStatus(record.ic_post)">
            <a-tag :color="getIcChangeColor(record.ic_post)">
              {{ Math.abs(record.ic_post) > 0.05 ? '显著提升' : '下降' }}
            </a-tag>
          </span>
        </template>
      </a-table>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'

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
const method = ref('gram-schmidt')
const keepFactors = ref(2)
const dateRange = ref<any[]>([])

const processing = ref(false)
const results = ref(null)

const originalCorr = ref<any[]>([])
const orthogonalizedCorr = ref<any[]>([])

const factorList = computed(() => {
  if (!results.value) return []

  return results.value.factors.map(f => ({
    name: f.name,
    label: f.label,
    ic_preserve: f.ic_preserve,
    ic_post: f.ic_post,
    correlation_after: f.correlation_after,
    status: f.kept ? '保留' : '剔除'
  }))
})

const columns = [
  { title: '因子名称', dataIndex: 'name', width: 150 },
  { title: '类别', dataIndex: 'category', width: 100 },
  { title: 'IC保留', dataIndex: 'ic_preserve', width: 100 },
  { title: 'IC下降', dataIndex: 'ic_post', width: 100 },
  { title: '相关后', dataIndex: 'correlation_after', width: 100 },
  { title: '状态', dataIndex: 'status', width: 100 }
]

const avgCorrReduction = computed(() => {
  if (!results.value) return 0

  const avgOriginal = results.value.avg_correlation_original || 0
  const avgAfter = results.value.avg_correlation_orthogonalized || 0
  return avgOriginal - avgAfter
})

const maxCorrReduction = computed(() => {
  if (!results.value) return 0

  const maxOriginal = Math.max(...originalCorr.value.map(c => Math.abs(c.value)))
  const maxAfter = Math.max(...orthogonalizedCorr.value.map(c => Math.abs(c.value)))
  return maxOriginal - maxAfter
})

const startOrthogonalize = async () => {
  if (selectedFactors.value.length < 2) {
    message.warning('请至少选择2个因子进行正交化')
    return
  }

  processing.value = true

  try {
    // TODO: 调用API进行因子正交化
    // const res = await orthogonalizeFactors({
    //   factor_names: selectedFactors.value,
    //   method: method.value,
    //   keep_factors: keepFactors.value,
    //   date_range: dateRange.value
    // })

    await simulateOrthogonalization()

    message.success('正交化完成')
  } catch (e) {
    message.error('正交化失败')
  } finally {
    processing.value = false
  }
}

// 模拟正交化过程
const simulateOrthogonalization = async () => {
  const n = selectedFactors.value.length

  // 原始相关性矩阵（模拟）
  originalCorr.value = []
  for (let i = 0; i < n; i++) {
    const row: any = {}
    for (let j = 0; j < n; j++) {
      row[`f${j + 1}`] = Math.random() * 2 - 1
    }
    originalCorr.value.push(row)
  }

  // 正交化后相关性矩阵（模拟）
  orthogonalizedCorr.value = originalCorr.value.map(row => {
    const newRow: any = {}
    for (let j = 0; j < n; j++) {
      newRow[`f${j + 1}`] = row[`f${j + 1}`]
    }
    return newRow
  })

  // 计算IC保留率（模拟因子列表）
  const icPreserveResults = selectedFactors.value.map((fName, idx) => ({
    name: fName,
    label: availableFactors.value.find(f => f.name === fName)?.label || fName,
    ic_preserve: Math.random() * 0.1 - 0.05,
    ic_post: Math.random() * 0.15 - 0.1,
    correlation_after: Math.random() * 0.1,
    kept: Math.random() > 0.3
  }))

  results.value = {
    avg_correlation_original: Math.random() * 0.6,
    avg_correlation_orthogonalized: Math.random() * 0.2,
    std_correlation_original: Math.random() * 0.3,
    std_correlation_orthogonalized: Math.random() * 0.15,
    kept_factors: icPreserveResults.filter(f => f.kept).length,
    removed_factors: icPreserveResults.filter(f => !f.kept).length,
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
  if (absValue > 0.1) return { status: '提升', color: 'green' }
  if (absValue > 0.05) return { status: '稳定', color: 'orange' }
  return { status: '下降', color: 'red' }
}

const getIcChangeColor = (status: any) => {
  return status?.color || '#999'
}

const resetConfig = () => {
  selectedFactors.value = []
  results.value = null
}

const exportResults = () => {
  if (!results.value) {
    message.warning('没有可导出的结果')
    return
  }
  message.info('导出正交化结果...')
}
</script>

<style scoped>
.factor-orthogonalization {
  padding: 16px;
}

.action-buttons {
  text-align: center;
  margin-top: 24px;
}
</style>
