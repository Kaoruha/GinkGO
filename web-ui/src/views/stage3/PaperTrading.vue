<template>
  <div class="page-container">
    <div class="page-header">
      <h1 class="page-title">
        <span class="tag tag-orange">模拟</span>
        模拟交易
        <span class="tag" :class="runningStatus === 'running' ? 'tag-green' : 'tag-gray'" style="margin-left: 8px">
          {{ runningStatus === 'running' ? '运行中' : '已停止' }}
        </span>
      </h1>
      <div class="page-actions">
        <button class="btn-secondary" @click="settingsVisible = true">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.09a2 2 0 0 1-1-1.74v-.47a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.39a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"></path>
            <circle cx="12" cy="12" r="3"></circle>
          </svg>
          设置
        </button>
        <button v-if="runningStatus !== 'running'" class="btn-primary" @click="startTrading">启动</button>
        <button v-else class="btn-danger" @click="stopTrading">停止</button>
        <button class="btn-secondary" @click="refreshData">
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

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-label">今日盈亏</div>
        <div class="stat-value" :class="{ 'stat-success': stats.todayProfit >= 0, 'stat-danger': stats.todayProfit < 0 }">
          ¥{{ stats.todayProfit.toFixed(2) }}
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-label">持仓数量</div>
        <div class="stat-value">{{ stats.positionCount }} 只</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">可用资金</div>
        <div class="stat-value">¥{{ stats.availableCash.toFixed(2) }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">运行天数</div>
        <div class="stat-value">{{ stats.runningDays }} 天</div>
      </div>
    </div>

    <!-- 当前持仓 -->
    <div class="card">
      <div class="card-header">
        <h3>当前持仓</h3>
      </div>
      <div class="card-body" :style="{ padding: loading ? '20px' : '0' }">
        <div v-if="loading" class="loading-state">加载中...</div>
        <div v-else class="table-wrapper">
          <table class="data-table">
            <thead>
              <tr>
                <th>代码</th>
                <th>数量</th>
                <th>成本</th>
                <th>现价</th>
                <th>市值</th>
                <th>盈亏</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="record in positions" :key="record.uuid">
                <td><span class="code-cell">{{ record.code }}</span></td>
                <td>{{ record.volume }}</td>
                <td>{{ record.cost?.toFixed(2) || '-' }}</td>
                <td>{{ record.price?.toFixed(2) || '-' }}</td>
                <td>{{ record.market_value?.toFixed(2) || '-' }}</td>
                <td>
                  <span :class="record.profit >= 0 ? 'text-danger' : 'text-success'">
                    {{ record.profit?.toFixed(2) }} ({{ record.profit_pct >= 0 ? '+' : '' }}{{ record.profit_pct }}%)
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-if="positions.length === 0" class="empty-state">
            <p>暂无持仓数据</p>
          </div>
        </div>
      </div>
    </div>

    <!-- 设置抽屉 -->
    <div v-if="settingsVisible" class="drawer-overlay" @click.self="settingsVisible = false">
      <div class="drawer">
        <div class="drawer-header">
          <h3>模拟交易设置</h3>
          <button class="drawer-close" @click="settingsVisible = false">×</button>
        </div>
        <div class="drawer-body">
          <div class="form-group">
            <label class="form-label">滑点模型</label>
            <select v-model="settings.slippageModel" class="form-select">
              <option value="fixed">固定滑点</option>
              <option value="percent">百分比滑点</option>
              <option value="dynamic">动态滑点</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">滑点值</label>
            <input v-model.number="settings.slippageValue" type="number" step="0.01" min="0" class="form-input" />
          </div>
          <div class="form-group">
            <label class="form-label">佣金费率 (%)</label>
            <input v-model.number="settings.commissionRate" type="number" step="0.01" min="0" max="100" class="form-input" />
          </div>
          <div class="form-group">
            <label class="form-label">成交延迟 (秒)</label>
            <input v-model.number="settings.executionDelay" type="number" step="1" min="0" class="form-input" />
          </div>
          <div class="form-group">
            <label class="form-label">印花税 (%)</label>
            <input v-model.number="settings.stampDuty" type="number" step="0.01" min="0" max="100" class="form-input" />
          </div>
        </div>
        <div class="drawer-footer">
          <button class="btn-secondary" @click="settingsVisible = false">取消</button>
          <button class="btn-primary" @click="saveSettings">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'

const loading = ref(false)
const settingsVisible = ref(false)
const runningStatus = ref('stopped')

const stats = reactive({
  todayProfit: 0,
  positionCount: 0,
  availableCash: 500000,
  runningDays: 0,
})

const positions = ref<any[]>([])

const settings = reactive({
  slippageModel: 'fixed',
  slippageValue: 0.01,
  commissionRate: 0.03,
  executionDelay: 0,
  stampDuty: 0.1,
})

const loadPositions = async () => {
  loading.value = true
  try {
    // TODO: Replace with actual API call
    // const result = await positionApi.list({ page: 0, size: 100 })
    await new Promise(resolve => setTimeout(resolve, 500))
    positions.value = []
    stats.positionCount = 0
  } catch (e: any) {
    console.error('加载持仓失败:', e)
  } finally {
    loading.value = false
  }
}

const refreshData = async () => {
  await loadPositions()
  console.log('数据已刷新')
}

const startTrading = () => {
  runningStatus.value = 'running'
  console.log('模拟交易已启动')
}

const stopTrading = () => {
  runningStatus.value = 'stopped'
  console.log('模拟交易已停止')
}

const saveSettings = () => {
  console.log('设置已保存')
  settingsVisible.value = false
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
  margin-bottom: 24px;
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

.page-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.stat-danger {
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

.text-danger {
  color: #f5222d;
}

.text-success {
  color: #52c41a;
}

.empty-state {
  text-align: center;
  padding: 40px;
  color: #8a8a9a;
}

.empty-state p {
  margin: 0;
}

/* Drawer styles */
.drawer-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 1000;
  display: flex;
  justify-content: flex-end;
}

.drawer {
  width: 400px;
  max-width: 90vw;
  background: #1a1a2e;
  border-left: 1px solid #2a2a3e;
  display: flex;
  flex-direction: column;
  animation: slideIn 0.3s ease;
}

@keyframes slideIn {
  from {
    transform: translateX(100%);
  }
  to {
    transform: translateX(0);
  }
}

.drawer-header {
  padding: 20px;
  border-bottom: 1px solid #2a2a3e;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.drawer-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #ffffff;
}

.drawer-close {
  background: none;
  border: none;
  color: #8a8a9a;
  font-size: 24px;
  cursor: pointer;
  padding: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: all 0.2s;
}

.drawer-close:hover {
  background: #2a2a3e;
  color: #ffffff;
}

.drawer-body {
  padding: 20px;
  flex: 1;
  overflow-y: auto;
}

.drawer-footer {
  padding: 20px;
  border-top: 1px solid #2a2a3e;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

@media (max-width: 1200px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }

  .page-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .page-actions {
    width: 100%;
  }

  .drawer {
    width: 100%;
    max-width: 100vw;
  }
}
</style>
