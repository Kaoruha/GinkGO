<template>
  <div class="paper-trading-container">
    <div class="page-header">
      <h1 class="page-title">模拟盘交易</h1>
      <button class="btn-primary" @click="showSelectPortfolio = true">
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <line x1="12" y1="5" x2="12" y2="19"></line>
          <line x1="5" y1="12" x2="19" y2="12"></line>
        </svg>
        添加Portfolio
      </button>
    </div>

    <div class="content-grid">
      <!-- 左侧：Portfolio列表 -->
      <div class="left-panel">
        <div class="card">
          <div class="card-header">
            <span>运行中的Portfolio</span>
          </div>

          <div class="card-body">
            <div v-if="loading" class="loading-state">加载中...</div>
            <div v-else-if="portfolios.length === 0" class="empty-tip">
              暂无运行中的模拟盘Portfolio
            </div>
            <div v-else class="portfolio-list">
              <div
                v-for="p in portfolios"
                :key="p.uuid"
                :class="['portfolio-item', { active: selectedPortfolio?.uuid === p.uuid }]"
                @click="selectPortfolio(p)"
              >
                <div class="portfolio-header">
                  <span class="portfolio-name">{{ p.name }}</span>
                  <span class="tag" :class="getStateTagClass(p.state)">{{ getStateLabel(p.state) }}</span>
                </div>
                <div class="portfolio-stats">
                  <span>净值: {{ p.net_value?.toFixed(4) || '-' }}</span>
                </div>
                <div class="portfolio-actions">
                  <button
                    v-if="p.state === 'RUNNING'"
                    class="btn-small"
                    @click.stop="pausePortfolio(p)"
                  >暂停</button>
                  <button
                    v-else-if="p.state === 'PAUSED'"
                    class="btn-small btn-primary"
                    @click.stop="resumePortfolio(p)"
                  >恢复</button>
                  <button
                    v-else
                    class="btn-small btn-primary"
                    @click.stop="startPortfolio(p)"
                  >启动</button>
                  <button class="btn-small btn-danger" @click.stop="removePortfolio(p)">移除</button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧：选中Portfolio详情 -->
      <div class="right-panel">
        <template v-if="selectedPortfolio">
          <!-- 账户信息 -->
          <div class="card mb-4">
            <div class="card-header">
              <span>账户信息</span>
            </div>
            <div class="card-body">
              <div class="stats-grid">
                <div class="stat-card">
                  <div class="stat-label">初始资金</div>
                  <div class="stat-value">¥{{ (portfolioDetail?.initial_cash || 0).toFixed(2) }}</div>
                </div>
                <div class="stat-card">
                  <div class="stat-label">可用资金</div>
                  <div class="stat-value">¥{{ (portfolioDetail?.current_cash || 0).toFixed(2) }}</div>
                </div>
                <div class="stat-card">
                  <div class="stat-label">持仓市值</div>
                  <div class="stat-value">¥{{ positionValue.toFixed(2) }}</div>
                </div>
                <div class="stat-card">
                  <div class="stat-label">累计盈亏</div>
                  <div class="stat-value" :class="totalPnl >= 0 ? 'text-danger' : 'text-success'">
                    ¥{{ totalPnl.toFixed(2) }}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- 当前持仓 -->
          <div class="card mb-4">
            <div class="card-header">
              <span>当前持仓</span>
            </div>
            <div class="card-body">
              <div class="table-wrapper">
                <table class="data-table">
                  <thead>
                    <tr>
                      <th>代码</th>
                      <th>持仓量</th>
                      <th>成本价</th>
                      <th>现价</th>
                      <th>盈亏%</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="record in portfolioDetail?.positions || []" :key="record.code">
                      <td>{{ record.code }}</td>
                      <td>{{ record.volume }}</td>
                      <td>{{ record.cost_price }}</td>
                      <td>{{ record.current_price }}</td>
                      <td :class="record.pnl >= 0 ? 'text-danger' : 'text-success'">
                        {{ record.pnl >= 0 ? '+' : '' }}{{ (record.pnl || 0).toFixed(2) }}%
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          <!-- 风控预警 -->
          <div v-if="portfolioDetail?.risk_alerts?.length" class="card">
            <div class="card-header">
              <span>风控预警</span>
            </div>
            <div class="card-body">
              <div
                v-for="(item, i) in portfolioDetail.risk_alerts"
                :key="`alert-${i}`"
                class="alert"
                :class="item.level === 'high' ? 'alert-error' : 'alert-warning'"
              >
                <div class="alert-icon">
                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
                    <line x1="12" y1="9" x2="12" y2="13"></line>
                    <line x1="12" y1="17" x2="12.01" y2="17"></line>
                  </svg>
                </div>
                <div class="alert-message">{{ item.message }}</div>
              </div>
            </div>
          </div>
        </template>

        <div v-else class="card">
          <div class="card-body empty-state">
            <p>请选择一个Portfolio查看详情</p>
          </div>
        </div>
      </div>
    </div>

    <!-- 选择Portfolio弹窗 -->
    <div v-if="showSelectPortfolio" class="modal-overlay" @click.self="showSelectPortfolio = false">
      <div class="modal">
        <div class="modal-header">
          <h3>选择Portfolio</h3>
          <button class="modal-close" @click="showSelectPortfolio = false">×</button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label class="form-label">选择已有Portfolio</label>
            <select v-model="selectedPortfolioUuid" class="form-select">
              <option value="">选择要添加到模拟盘的Portfolio</option>
              <option v-for="p in availablePortfolios" :key="p.uuid" :value="p.uuid">
                {{ p.name }} ({{ p.mode }})
              </option>
            </select>
          </div>

          <div class="form-group">
            <label class="form-label">或创建新的模拟盘Portfolio</label>
            <button class="btn-secondary" @click="$router.push('/portfolio/create')">新建Portfolio</button>
          </div>

          <div class="form-actions">
            <button class="btn-primary" @click="confirmAddPortfolio">确定</button>
            <button class="btn-secondary" @click="showSelectPortfolio = false">取消</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { portfolioApi, type Portfolio, type PortfolioDetail } from '@/api/modules/portfolio'

const loading = ref(false)
const portfolios = ref<Portfolio[]>([])
const selectedPortfolio = ref<Portfolio | null>(null)
const portfolioDetail = ref<PortfolioDetail | null>(null)
const showSelectPortfolio = ref(false)
const selectedPortfolioUuid = ref('')
const availablePortfolios = ref<Portfolio[]>([])

const positionValue = computed(() => {
  if (!portfolioDetail.value?.positions) return 0
  return portfolioDetail.value.positions.reduce((sum, p) => sum + p.volume * p.current_price, 0)
})

const totalPnl = computed(() => {
  if (!portfolioDetail.value) return 0
  const init = portfolioDetail.value.initial_cash || 0
  const current = portfolioDetail.value.current_cash + positionValue.value
  return current - init
})

const getStateTagClass = (state: string) => {
  const classes: Record<string, string> = {
    RUNNING: 'tag-green',
    PAUSED: 'tag-orange',
    STOPPED: 'tag-gray',
    INITIALIZED: 'tag-blue'
  }
  return classes[state] || 'tag-gray'
}

const getStateLabel = (state: string) => {
  const labels: Record<string, string> = {
    RUNNING: '运行中',
    PAUSED: '已暂停',
    STOPPED: '已停止',
    INITIALIZED: '已初始化'
  }
  return labels[state] || state
}

const loadPortfolios = async () => {
  loading.value = true
  try {
    const res = await portfolioApi.list({ mode: 'PAPER' })
    portfolios.value = res.data || []
    if (portfolios.value.length > 0 && !selectedPortfolio.value) {
      selectPortfolio(portfolios.value[0])
    }
  } catch (e) {
    console.error('加载Portfolio列表失败')
  } finally {
    loading.value = false
  }
}

const loadAvailablePortfolios = async () => {
  try {
    const res = await portfolioApi.list({})
    availablePortfolios.value = (res.data || []).filter(p => p.mode !== 'PAPER')
  } catch (e) {
    // ignore
  }
}

const selectPortfolio = async (p: Portfolio) => {
  selectedPortfolio.value = p
  try {
    const res = await portfolioApi.get(p.uuid)
    portfolioDetail.value = res.data || null
  } catch (e) {
    console.error('加载Portfolio详情失败')
  }
}

const startPortfolio = async (p: Portfolio) => {
  console.log(`启动Portfolio: ${p.name}`)
  p.state = 'RUNNING'
}

const pausePortfolio = async (p: Portfolio) => {
  console.log(`暂停Portfolio: ${p.name}`)
  p.state = 'PAUSED'
}

const resumePortfolio = async (p: Portfolio) => {
  console.log(`恢复Portfolio: ${p.name}`)
  p.state = 'RUNNING'
}

const removePortfolio = async (p: Portfolio) => {
  portfolios.value = portfolios.value.filter(item => item.uuid !== p.uuid)
  if (selectedPortfolio.value?.uuid === p.uuid) {
    selectedPortfolio.value = null
    portfolioDetail.value = null
  }
  console.log('已移除')
}

const confirmAddPortfolio = async () => {
  if (!selectedPortfolioUuid.value) {
    console.warn('请选择一个Portfolio')
    return
  }
  try {
    await portfolioApi.update(selectedPortfolioUuid.value, { mode: 'PAPER' as any })
    console.log('添加成功')
    showSelectPortfolio.value = false
    selectedPortfolioUuid.value = ''
    loadPortfolios()
  } catch (e) {
    console.error('添加失败')
  }
}

onMounted(() => {
  loadPortfolios()
  loadAvailablePortfolios()
})
</script>

<style scoped>
.paper-trading-container {
  padding: 24px;
  background: #0f0f1a;
  min-height: calc(100vh - 64px);
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
  font-size: 24px;
  font-weight: 600;
  margin: 0;
  color: #ffffff;
}

.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: #1890ff;
  border: none;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-primary:hover {
  background: #40a9ff;
}

.btn-secondary {
  padding: 8px 16px;
  background: transparent;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-secondary:hover {
  border-color: #1890ff;
  color: #1890ff;
}

.btn-danger {
  padding: 8px 16px;
  background: #f5222d;
  border: none;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-danger:hover {
  background: #ff4d4f;
}

.btn-small {
  padding: 4px 8px;
  background: transparent;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-small:hover {
  border-color: #1890ff;
  color: #1890ff;
}

.content-grid {
  display: grid;
  grid-template-columns: 350px 1fr;
  gap: 16px;
}

.mb-4 {
  margin-bottom: 16px;
}

.card {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
}

.card-header {
  padding: 16px 20px;
  border-bottom: 1px solid #2a2a3e;
  color: #ffffff;
  font-size: 16px;
  font-weight: 600;
}

.card-body {
  padding: 20px;
}

.tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.tag-blue { background: rgba(24, 144, 255, 0.2); color: #1890ff; }
.tag-green { background: rgba(82, 196, 26, 0.2); color: #52c41a; }
.tag-red { background: rgba(245, 34, 45, 0.2); color: #f5222d; }
.tag-orange { background: rgba(250, 140, 22, 0.2); color: #fa8c16; }
.tag-gray { background: rgba(140, 140, 140, 0.2); color: #8c8c8c; }

.loading-state {
  text-align: center;
  padding: 40px;
  color: #8a8a9a;
}

.empty-tip {
  text-align: center;
  color: #8a8a9a;
  padding: 24px;
}

.portfolio-list {
  max-height: 400px;
  overflow-y: auto;
}

.portfolio-item {
  padding: 12px;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.3s;
  background: #1a1a2e;
}

.portfolio-item:hover {
  border-color: #1890ff;
}

.portfolio-item.active {
  border-color: #1890ff;
  background: #2a2a3e;
}

.portfolio-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.portfolio-name {
  font-weight: 500;
  color: #ffffff;
}

.portfolio-stats {
  color: #8a8a9a;
  font-size: 12px;
  margin-bottom: 8px;
}

.portfolio-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.stat-card {
  text-align: center;
}

.stat-label {
  font-size: 13px;
  color: #8a8a9a;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 20px;
  font-weight: 600;
  color: #ffffff;
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
}

.data-table td {
  color: #ffffff;
  font-size: 14px;
}

.empty-state {
  text-align: center;
  padding: 40px;
  color: #8a8a9a;
}

.empty-state p {
  margin: 0;
}

.alert {
  display: flex;
  gap: 12px;
  padding: 12px 16px;
  border-radius: 6px;
  margin-bottom: 12px;
}

.alert:last-child {
  margin-bottom: 0;
}

.alert-warning {
  background: rgba(250, 173, 20, 0.1);
  border: 1px solid rgba(250, 173, 20, 0.3);
}

.alert-error {
  background: rgba(245, 34, 45, 0.1);
  border: 1px solid rgba(245, 34, 45, 0.3);
}

.alert-warning .alert-icon {
  color: #faad14;
}

.alert-error .alert-icon {
  color: #f5222d;
}

.alert-message {
  font-size: 14px;
  color: #ffffff;
}

/* 模态框样式 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  max-width: 500px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  padding: 16px 20px;
  border-bottom: 1px solid #2a2a3e;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
}

.modal-close {
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
}

.modal-close:hover {
  color: #ffffff;
}

.modal-body {
  padding: 20px;
}

.form-group {
  margin-bottom: 16px;
}

.form-label {
  display: block;
  font-size: 13px;
  color: #8a8a9a;
  font-weight: 500;
  margin-bottom: 6px;
}

.form-select {
  width: 100%;
  padding: 8px 12px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
}

.form-select:focus {
  outline: none;
  border-color: #1890ff;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 20px;
}

@media (max-width: 1024px) {
  .content-grid {
    grid-template-columns: 1fr;
  }

  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }

  .portfolio-actions {
    flex-direction: column;
  }
}
</style>
