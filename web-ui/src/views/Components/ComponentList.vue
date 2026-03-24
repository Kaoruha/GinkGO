<template>
  <div class="component-list-container">
    <div class="page-header">
      <h1 class="page-title">组件管理</h1>
      <p class="page-subtitle">管理策略、分析器、风控等组件</p>
    </div>

    <div class="stats-grid">
      <div class="stat-card stat-blue">
        <div class="stat-value">{{ componentStats.strategies }}</div>
        <div class="stat-label">策略组件</div>
      </div>
      <div class="stat-card stat-green">
        <div class="stat-value">{{ componentStats.analyzers }}</div>
        <div class="stat-label">分析器</div>
      </div>
      <div class="stat-card stat-orange">
        <div class="stat-value">{{ componentStats.risk }}</div>
        <div class="stat-label">风控组件</div>
      </div>
      <div class="stat-card stat-purple">
        <div class="stat-value">{{ componentStats.others }}</div>
        <div class="stat-label">其他组件</div>
      </div>
    </div>

    <div class="card">
      <div class="filter-row">
        <select v-model="filterType" class="form-select" @change="loadComponents">
          <option value="">全部类型</option>
          <option value="strategy">策略</option>
          <option value="analyzer">分析器</option>
          <option value="risk">风控</option>
          <option value="sizer">仓位管理</option>
          <option value="selector">选择器</option>
        </select>
        <div class="search-input-wrapper">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"></circle>
            <path d="m21 21-4.35-4.35"></path>
          </svg>
          <input
            v-model="searchText"
            type="text"
            placeholder="搜索组件名称"
            class="form-input"
            @keyup.enter="loadComponents"
          />
          <button class="search-btn" @click="loadComponents">搜索</button>
        </div>
        <button class="btn btn-primary" @click="goToCreate">
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
          创建组件
        </button>
      </div>
    </div>

    <div class="card">
      <div v-if="loading" class="loading-container">
        <div class="spinner"></div>
      </div>
      <div v-else class="table-wrapper">
        <table class="data-table">
          <thead>
            <tr>
              <th>组件名称</th>
              <th>类型</th>
              <th>描述</th>
              <th>创建时间</th>
              <th>更新时间</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="record in components" :key="record.uuid">
              <td>{{ record.name }}</td>
              <td>
                <span class="tag" :class="`tag-${getComponentTypeColor(record.component_type)}`">
                  {{ getComponentTypeLabel(record.component_type) }}
                </span>
              </td>
              <td>{{ record.description || '-' }}</td>
              <td>{{ formatDate(record.created_at, 'YYYY-MM-DD') }}</td>
              <td>{{ record.updated_at ? formatDate(record.updated_at, 'YYYY-MM-DD HH:mm') : '-' }}</td>
              <td>
                <div class="action-links">
                  <a @click="viewDetail(record)">查看</a>
                  <a @click="editComponent(record)">编辑</a>
                  <a class="danger-link" @click="deleteComponent(record)">删除</a>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
        <div v-if="components.length === 0" class="empty-state">
          <p>暂无组件数据</p>
        </div>
      </div>
      <!-- Pagination -->
      <div v-if="pagination.total > 0" class="table-pagination">
        <div class="pagination-info">
          共 {{ pagination.total }} 条，第 {{ pagination.current }} / {{ totalPages }} 页
        </div>
        <div class="pagination-controls">
          <button
            class="pagination-btn"
            :disabled="pagination.current === 1"
            @click="pagination.current = 1; loadComponents()"
          >
            首页
          </button>
          <button
            class="pagination-btn"
            :disabled="pagination.current === 1"
            @click="pagination.current--; loadComponents()"
          >
            上一页
          </button>
          <button
            class="pagination-btn"
            :disabled="pagination.current === totalPages"
            @click="pagination.current++; loadComponents()"
          >
            下一页
          </button>
          <button
            class="pagination-btn"
            :disabled="pagination.current === totalPages"
            @click="pagination.current = totalPages; loadComponents()"
          >
            末页
          </button>
          <select v-model.number="pagination.pageSize" @change="loadComponents()" class="pagination-select">
            <option :value="20">20 条/页</option>
            <option :value="50">50 条/页</option>
            <option :value="100">100 条/页</option>
          </select>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { componentsApi } from '@/api/modules/components'
import type { ComponentSummary as Component } from '@/types/component'

// 简化的通知函数
const showToast = (message: string, type: 'success' | 'error' | 'info' | 'warning' = 'success') => {
  console.log(`[${type.toUpperCase()}] ${message}`)
}

const router = useRouter()

const loading = ref(false)
const components = ref<Component[]>([])
const filterType = ref('')
const searchText = ref('')

const pagination = reactive({
  current: 1,
  pageSize: 20,
  total: 0,
  showSizeChanger: true,
  showTotal: (total: number) => `共 ${total} 条`
})

const componentStats = reactive({
  strategies: 0,
  analyzers: 0,
  risk: 0,
  others: 0
})

// 计算总页数
const totalPages = computed(() => {
  return Math.ceil(pagination.total / pagination.pageSize)
})

const getComponentTypeColor = (type: string) => {
  const colors: Record<string, string> = {
    strategy: 'blue',
    analyzer: 'green',
    risk: 'orange',
    sizer: 'purple',
    selector: 'cyan'
  }
  return colors[type] || 'gray'
}

const getComponentTypeLabel = (type: string) => {
  const labels: Record<string, string> = {
    strategy: '策略',
    analyzer: '分析器',
    risk: '风控',
    sizer: '仓位管理',
    selector: '选择器'
  }
  return labels[type] || type
}

const loadComponents = async () => {
  loading.value = true
  try {
    const response = await componentsApi.list({
      type: filterType.value || undefined,
      search: searchText.value || undefined,
      page: pagination.current,
      page_size: pagination.pageSize
    })

    components.value = response.data?.items || []
    pagination.total = response.data?.total || 0

    // 更新统计
    updateStats()
  } catch (error: any) {
    showToast(`加载组件失败: ${error.message}`, 'error')
  } finally {
    loading.value = false
  }
}

const updateStats = () => {
  componentStats.strategies = components.value.filter(c => c.component_type === 'strategy').length
  componentStats.analyzers = components.value.filter(c => c.component_type === 'analyzer').length
  componentStats.risk = components.value.filter(c => c.component_type === 'risk').length
  componentStats.others = components.value.filter(c =>
    !['strategy', 'analyzer', 'risk'].includes(c.component_type)
  ).length
}

const goToCreate = () => {
  router.push('/components/create')
}

const viewDetail = (record: Component) => {
  router.push(`/components/${record.uuid}`)
}

const editComponent = (record: Component) => {
  router.push(`/components/${record.uuid}/edit`)
}

const deleteComponent = async (record: Component) => {
  if (!confirm(`确定要删除组件 "${record.name}" 吗？`)) {
    return
  }
  try {
    await componentsApi.delete(record.uuid)
    showToast('删除成功')
    loadComponents()
  } catch (error: any) {
    showToast(`删除失败: ${error.message}`, 'error')
  }
}

const formatDate = (dateStr: string, format: string) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  if (format === 'YYYY-MM-DD') {
    return date.toISOString().split('T')[0]
  }
  return date.toLocaleString('zh-CN')
}

onMounted(() => {
  loadComponents()
})
</script>

<style scoped>
.component-list-container {
  padding: 24px;
  background: #0f0f1a;
  min-height: calc(100vh - 64px);
}

.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #ffffff;
  margin: 0 0 8px 0;
}

.page-subtitle {
  font-size: 14px;
  color: #8a8a9a;
  margin: 0;
}

/* Stats Grid */
.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  background: #1a1a2e;
  border-radius: 8px;
  border: 1px solid #2a2a3e;
  padding: 20px;
  text-align: center;
}

.stat-value {
  font-size: 28px;
  font-weight: 600;
  margin-bottom: 8px;
}

.stat-label {
  font-size: 13px;
  color: #8a8a9a;
}

.stat-blue .stat-value { color: #1890ff; }
.stat-green .stat-value { color: #52c41a; }
.stat-orange .stat-value { color: #faad14; }
.stat-purple .stat-value { color: #722ed1; }

/* Card */
.card {
  background: #1a1a2e;
  border-radius: 8px;
  border: 1px solid #2a2a3e;
  padding: 20px;
  margin-bottom: 24px;
}

/* Filter Row */
.filter-row {
  display: flex;
  gap: 16px;
  align-items: center;
}

.form-select {
  padding: 8px 12px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  min-width: 150px;
}

.form-select:focus {
  outline: none;
  border-color: #1890ff;
}

.search-input-wrapper {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  padding: 6px 12px;
  flex: 1;
}

.search-input-wrapper svg {
  color: #8a8a9a;
  flex-shrink: 0;
}

.form-input {
  flex: 1;
  background: transparent;
  border: none;
  color: #ffffff;
  font-size: 14px;
  padding: 0;
}

.form-input:focus {
  outline: none;
}

.search-btn {
  padding: 4px 12px;
  background: #1890ff;
  border: none;
  border-radius: 4px;
  color: #ffffff;
  font-size: 13px;
  cursor: pointer;
}

/* Button */
.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.btn-primary {
  background: #1890ff;
  color: #ffffff;
}

.btn-primary:hover {
  background: #40a9ff;
}

/* Loading */
.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 40px;
}

.spinner {
  width: 32px;
  height: 32px;
  border: 3px solid #2a2a3e;
  border-top-color: #1890ff;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* Table */
.table-wrapper {
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
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
}

.data-table td {
  color: #ffffff;
}

.data-table tbody tr:hover {
  background: #2a2a3e;
}

/* Tag */
.tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}

.tag-blue { background: rgba(24, 144, 255, 0.2); color: #1890ff; }
.tag-green { background: rgba(82, 196, 26, 0.2); color: #52c41a; }
.tag-orange { background: rgba(250, 173, 20, 0.2); color: #faad14; }
.tag-purple { background: rgba(114, 46, 209, 0.2); color: #722ed1; }
.tag-cyan { background: rgba(19, 194, 194, 0.2); color: #13c2c2; }
.tag-gray { background: #2a2a3e; color: #8a8a9a; }

/* Action Links */
.action-links {
  display: flex;
  gap: 12px;
}

.action-links a {
  color: #1890ff;
  cursor: pointer;
  font-size: 13px;
}

.action-links a:hover {
  text-decoration: underline;
}

.danger-link {
  color: #f5222d !important;
}

/* Empty State */
.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 40px;
  color: #8a8a9a;
}

/* Pagination */
.table-pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #2a2a3e;
}

.pagination-info {
  font-size: 13px;
  color: #8a8a9a;
}

.pagination-controls {
  display: flex;
  gap: 8px;
  align-items: center;
}

.pagination-btn {
  padding: 4px 10px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.pagination-btn:hover:not(:disabled) {
  background: #3a3a4e;
  border-color: #1890ff;
}

.pagination-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pagination-select {
  padding: 4px 8px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 12px;
  cursor: pointer;
}

.pagination-select:focus {
  outline: none;
  border-color: #1890ff;
}
</style>
