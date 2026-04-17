<template>
  <div class="analyzer-panel">
    <!-- 分析器选择器 -->
    <div class="analyzer-selector">
      <span class="label">选择分析器：</span>
      <select
        v-model="selectedAnalyzer"
        class="form-select"
        @change="onAnalyzerChange"
      >
        <option value="">请选择分析器</option>
        <option v-for="a in analyzers" :key="a.name" :value="a.name">
          {{ a.name }} ({{ a.record_count }}条)
        </option>
      </select>
    </div>

    <!-- 图表区域 -->
    <div v-if="selectedAnalyzer" class="card">
      <div class="card-header">
        <h3>时序图表</h3>
      </div>
      <div class="card-body">
        <div v-if="chartLoading" class="loading-container">
          <div class="spinner"></div>
        </div>
        <div v-else-if="chartData.length > 0" class="chart-container">
          <!-- Chart placeholder - would use actual chart component -->
          <div class="chart-placeholder">
            <p>图表数据点: {{ chartData.length }}</p>
          </div>
        </div>
        <div v-else class="empty-state">
          <p>暂无数据</p>
        </div>
      </div>
    </div>

    <!-- 统计信息 -->
    <div v-if="stats" class="card stats-card">
      <div class="card-header">
        <h3>统计信息</h3>
      </div>
      <div class="card-body">
        <div class="stats-grid">
          <div class="stat-item">
            <div class="stat-label">记录数</div>
            <div class="stat-value">{{ stats.count }}</div>
          </div>
          <div class="stat-item">
            <div class="stat-label">最小值</div>
            <div class="stat-value">{{ stats.min?.toFixed(4) || '-' }}</div>
          </div>
          <div class="stat-item">
            <div class="stat-label">最大值</div>
            <div class="stat-value">{{ stats.max?.toFixed(4) || '-' }}</div>
          </div>
          <div class="stat-item">
            <div class="stat-label">平均值</div>
            <div class="stat-value">{{ stats.avg?.toFixed(4) || '-' }}</div>
          </div>
          <div class="stat-item">
            <div class="stat-label">首值</div>
            <div class="stat-value">{{ stats.first?.toFixed(4) || '-' }}</div>
          </div>
          <div class="stat-item">
            <div class="stat-label">末值</div>
            <div class="stat-value" :class="stats.change >= 0 ? 'text-success' : 'text-danger'">
              {{ stats.latest?.toFixed(4) || '-' }}
            </div>
          </div>
        </div>
        <div class="stats-row">
          <div class="stat-item stat-item-wide">
            <div class="stat-label">变化量</div>
            <div class="stat-value" :class="stats.change >= 0 ? 'text-success' : 'text-danger'">
              {{ stats.change?.toFixed(4) || '-' }}
              <span v-if="stats.change >= 0" class="trend-icon">↑</span>
              <span v-else class="trend-icon">↓</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 数据表格 -->
    <div v-if="tableData.length > 0" class="card table-card">
      <div class="card-header">
        <h3>数据记录</h3>
      </div>
      <div class="card-body">
        <div class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th width="150">时间</th>
                <th width="150">值</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in tableData" :key="row.time">
                <td>{{ row.time }}</td>
                <td>{{ row.value?.toFixed(4) || '-' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onMounted } from 'vue'

// 简化的通知函数
const showToast = (message: string, type: 'success' | 'error' | 'info' | 'warning' = 'success') => {
  console.log(`[${type.toUpperCase()}] ${message}`)
}

interface LineData {
  time: string
  value: number
}

interface AnalyzerInfo {
  name: string
  record_count: number
}

interface Props {
  taskId: string
  portfolioId: string
  analyzers: AnalyzerInfo[]
}

const props = defineProps<Props>()

const selectedAnalyzer = ref<string>('')
const chartLoading = ref(false)
const chartData = ref<LineData[]>([])
const tableData = ref<Array<{ time: string; value: number }>>([])
const stats = ref<{
  count: number
  min: number
  max: number
  avg: number
  latest: number | null
  first: number | null
  change: number
} | null>(null)

const onAnalyzerChange = async (name: string) => {
  if (!name || !props.taskId) return

  chartLoading.value = true
  try {
    // Mock data - replace with actual API call
    chartData.value = []
    tableData.value = []
    stats.value = {
      count: 0,
      min: 0,
      max: 0,
      avg: 0,
      latest: null,
      first: null,
      change: 0
    }
  } catch (e) {
    console.error('Failed to load analyzer data:', e)
    showToast('加载分析器数据失败', 'error')
  } finally {
    chartLoading.value = false
  }
}

// 监听 analyzers 变化，自动选择第一个
watch(() => props.analyzers, (newAnalyzers) => {
  if (newAnalyzers.length > 0 && !selectedAnalyzer.value) {
    // 优先选择 net_value
    const netValue = newAnalyzers.find(a => a.name === 'net_value')
    selectedAnalyzer.value = netValue?.name || newAnalyzers[0].name
    onAnalyzerChange(selectedAnalyzer.value)
  }
}, { immediate: true })
</script>

<style scoped>
.analyzer-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.analyzer-selector {
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.analyzer-selector .label {
  font-weight: 500;
  margin-right: 8px;
  color: #ffffff;
}

/* Card */

.stats-card {
  margin-bottom: 16px;
}

.table-card {
  flex: 1;
  overflow: hidden;
  margin-bottom: 0;
  display: flex;
  flex-direction: column;
}

.table-card .card-body {
  flex: 1;
  overflow: hidden;
  padding: 12px;
  display: flex;
  flex-direction: column;
}

.table-card .table-wrapper {
  flex: 1;
  overflow: auto;
}

/* Loading */

/* Chart Placeholder */
.chart-container {
  height: 300px;
}

.chart-placeholder {
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #2a2a3e;
  border-radius: 4px;
  color: #8a8a9a;
}

/* Empty State */
.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 40px;
  color: #8a8a9a;
}

/* Stats Grid */

.stat-item {
  text-align: center;
}

.stat-item-wide {
  flex: 1;
  text-align: center;
}

.trend-icon {
  margin-left: 4px;
  font-size: 14px;
}

.text-success {
  color: #52c41a;
}

.text-danger {
  color: #f5222d;
}

/* Table */
.table-wrapper {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.data-table th,
.data-table td {
  padding: 8px 12px;
  text-align: left;
  border-bottom: 1px solid #2a2a3e;
}

.data-table th {
  background: #2a2a3e;
  color: #ffffff;
  font-weight: 500;
  position: sticky;
  top: 0;
}

.data-table td {
  color: #ffffff;
}

.data-table tbody tr:hover {
  background: #2a2a3e;
}
</style>
