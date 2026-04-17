<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">
        <span class="tag tag-red">实盘</span>
        持仓管理
      </h1>
      <div class="page-actions">
        <div class="filter-group">
          <input v-model="filterCode" type="text" placeholder="股票代码" class="form-input" />
          <button class="btn-primary" @click="loadPositions">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="11" cy="11" r="8"></circle>
              <path d="m21 21-4.35-4.35"></path>
            </svg>
            搜索
          </button>
          <button class="btn-secondary" @click="loadPositions">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"></path>
              <path d="M3 3v5h5"></path>
              <path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"></path>
              <path d="M16 21h5v-5"></path>
            </svg>
            刷新
          </button>
        </div>
      </div>
    </div>

    <!-- 汇总信息 -->
    <div v-if="summary" class="stats-grid">
      <div class="stat-card">
        <div class="stat-label">持仓数量</div>
        <div class="stat-value">{{ summary.position_count }} 只</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">总市值</div>
        <div class="stat-value">¥{{ summary.total_market_value?.toFixed(2) || '0.00' }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">总盈亏</div>
        <div class="stat-value" :class="{ 'stat-danger': summary.total_profit >= 0, 'stat-success': summary.total_profit < 0 }">
          ¥{{ summary.total_profit?.toFixed(2) || '0.00' }}
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-label">总手续费</div>
        <div class="stat-value">¥{{ summary.total_fee?.toFixed(2) || '0.00' }}</div>
      </div>
    </div>

    <!-- 持仓表格 -->
    <div class="card">
      <div class="card-body" :style="{ padding: loading ? '20px' : '0' }">
        <div v-if="loading" class="loading-state">加载中...</div>
        <div v-else class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>代码</th>
                <th>持仓量</th>
                <th>可用量</th>
                <th>成本价</th>
                <th>现价</th>
                <th>市值</th>
                <th>盈亏</th>
                <th>手续费</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="record in positions" :key="record.uuid">
                <td><span class="code-cell">{{ record.code }}</span></td>
                <td>{{ record.volume }}</td>
                <td>{{ record.volume - (record.frozen_volume || 0) }}</td>
                <td>{{ record.cost?.toFixed(2) || '-' }}</td>
                <td>{{ record.price?.toFixed(2) || '-' }}</td>
                <td>{{ record.market_value?.toFixed(2) || '-' }}</td>
                <td>
                  <span :class="record.profit >= 0 ? 'text-danger' : 'text-success'">
                    {{ record.profit?.toFixed(2) }} ({{ record.profit_pct >= 0 ? '+' : '' }}{{ record.profit_pct }}%)
                  </span>
                </td>
                <td>{{ record.fee?.toFixed(2) || '-' }}</td>
                <td>
                  <button class="btn-link btn-link-danger" @click="sellPosition(record.uuid)">
                    卖出
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-if="positions.length === 0" class="empty-state">
            <p>暂无持仓数据</p>
          </div>
        </div>

        <!-- 分页 -->
        <div v-if="!loading && positions.length > 0" class="pagination">
          <div class="pagination-info">共 {{ pagination.total }} 条</div>
          <div class="pagination-controls">
            <button class="pagination-btn" :disabled="pagination.current === 1" @click="goToPage(1)">
              首页
            </button>
            <button class="pagination-btn" :disabled="pagination.current === 1" @click="goToPage(pagination.current - 1)">
              上一页
            </button>
            <span class="pagination-current">第 {{ pagination.current }} 页</span>
            <button class="pagination-btn" :disabled="pagination.current >= totalPages" @click="goToPage(pagination.current + 1)">
              下一页
            </button>
            <button class="pagination-btn" :disabled="pagination.current >= totalPages" @click="goToPage(totalPages)">
              末页
            </button>
            <select v-model="pagination.pageSize" @change="loadPositions" class="pagination-size">
              <option :value="50">50条/页</option>
              <option :value="100">100条/页</option>
              <option :value="200">200条/页</option>
            </select>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'

const loading = ref(false)
const positions = ref<any[]>([])
const summary = ref<any>(null)

const filterCode = ref<string>('')

const pagination = reactive({
  current: 1,
  pageSize: 100,
  total: 0,
})

const totalPages = computed(() => Math.ceil(pagination.total / pagination.pageSize))

const loadPositions = async () => {
  loading.value = true
  try {
    const params: any = {
      page: pagination.current - 1,
      size: pagination.pageSize,
    }
    if (filterCode.value) {
      params.code = filterCode.value
    }

    // TODO: Replace with actual API call
    await new Promise(resolve => setTimeout(resolve, 500))
    positions.value = []
    pagination.total = 0
    summary.value = null
  } catch (e: any) {
    console.error('加载持仓失败:', e)
  } finally {
    loading.value = false
  }
}

const goToPage = (page: number) => {
  pagination.current = page
  loadPositions()
}

const sellPosition = (uuid: string) => {
  console.log('卖出持仓:', uuid)
}

onMounted(() => {
  loadPositions()
})
</script>

<style scoped>
.page-container {
  padding: 0;
  background: transparent;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  flex-wrap: wrap;
  gap: 16px;
}

.page-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #ffffff;
  display: flex;
  align-items: center;
  gap: 12px;
}

.filter-group {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.btn-link-danger {
  color: #f5222d;
}

.btn-link-danger:hover {
  color: #ff4d4f;
}

.stat-danger {
  color: #f5222d;
}

.text-success {
  color: #52c41a;
}

.text-danger {
  color: #f5222d;
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
  white-space: nowrap;
}

.data-table td {
  color: #ffffff;
  font-size: 14px;
}

.data-table tbody tr:hover {
  background: #2a2a3e;
}

.code-cell {
  font-weight: 600;
}

.empty-state {
  text-align: center;
  padding: 40px;
  color: #8a8a9a;
}

.empty-state p {
  margin: 0;
}

.pagination {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-top: 1px solid #2a2a3e;
  flex-wrap: wrap;
  gap: 16px;
}

.pagination-info {
  color: #8a8a9a;
  font-size: 14px;
}

.pagination-controls {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.pagination-btn {
  padding: 4px 12px;
  background: transparent;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.pagination-btn:hover:not(:disabled) {
  border-color: #1890ff;
  color: #1890ff;
}

.pagination-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.pagination-current {
  color: #8a8a9a;
  font-size: 14px;
  padding: 0 8px;
}

.pagination-size {
  padding: 4px 8px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  cursor: pointer;
}

@media (max-width: 768px) {
  .page-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .filter-group {
    width: 100%;
  }

  .form-input {
    flex: 1;
  }

  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .pagination {
    flex-direction: column;
    align-items: center;
  }
}
</style>
