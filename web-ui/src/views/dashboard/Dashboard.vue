<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">概览</div>
    </div>

    <div class="page-content">
      <!-- 系统状态卡片 -->
      <div class="stats-grid" data-testid="stats-grid">
        <div class="stat-card" data-testid="stat-portfolio">
          <div class="stat-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"/>
              <polygon points="10,8 16,12 10,16"/>
            </svg>
          </div>
          <div class="stat-content">
            <div class="stat-label">运行中 Portfolio</div>
            <div class="stat-value" v-if="!loading">{{ stats.running }} <span class="stat-suffix">个</span></div>
            <div class="stat-value" v-else>--</div>
          </div>
        </div>

        <div class="stat-card" data-testid="stat-backtest">
          <div class="stat-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M4.5 16.5c-1.5 1.26-2 5-2 5s3.74-.5 5-2c.71-.84.7-2.13-.09-2.91a2.18 2.18 0 0 0-2.91-.09z"/>
              <path d="m12 15-3-3a22 22 0 0 1 2-3.95A12.88 12.88 0 0 1 22 2c0 2.72-.78 7.5-6 11a22.35 22.35 0 0 1-4 2z"/>
              <path d="M9 12H4s.55-3.03 2-4c1.62-1.08 5 0 5 0"/>
              <path d="M12 15v5s3.03-.55 4-2c1.08-1.62 0-5 0-5"/>
            </svg>
          </div>
          <div class="stat-content">
            <div class="stat-label">Portfolio 总数</div>
            <div class="stat-value" v-if="!loading">{{ stats.total }} <span class="stat-suffix">个</span></div>
            <div class="stat-value" v-else>--</div>
          </div>
        </div>

        <div class="stat-card" data-testid="stat-worker">
          <div class="stat-icon">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="2" y="2" width="20" height="8" rx="2" ry="2"/>
              <rect x="2" y="14" width="20" height="8" rx="2" ry="2"/>
              <line x1="6" y1="6" x2="6.01" y2="6"/>
              <line x1="6" y1="18" x2="6.01" y2="18"/>
            </svg>
          </div>
          <div class="stat-content">
            <div class="stat-label">总资产</div>
            <div class="stat-value" v-if="!loading">{{ stats.totalAssets.toLocaleString() }} <span class="stat-suffix">元</span></div>
            <div class="stat-value" v-else>--</div>
          </div>
        </div>

        <div class="stat-card" data-testid="stat-system">
          <div class="stat-icon success">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
              <polyline points="22,4 12,14.01 9,11.01"/>
            </svg>
          </div>
          <div class="stat-content">
            <div class="stat-label">平均净值</div>
            <div class="stat-value" v-if="!loading">{{ stats.avgNetValue.toFixed(4) }}</div>
            <div class="stat-value" v-else>--</div>
          </div>
        </div>
      </div>

      <!-- 4阶段概览 -->
      <div class="stages-grid" data-testid="stages-grid">
        <div class="stage-card stage-1" data-testid="stage-backtest">
          <div class="stage-header">
            <h3>回测</h3>
          </div>
          <div class="stage-stats">
            <div class="stage-stat">
              <span class="stat-label">回测组合</span>
              <span class="stat-number">{{ portfolios.filter(p => String(p.mode) === 'BACKTEST').length }}</span>
            </div>
            <div class="stage-stat">
              <span class="stat-label">运行中</span>
              <span class="stat-number">{{ portfolios.filter(p => String(p.mode) === 'BACKTEST' && String(p.state) === 'RUNNING').length }}</span>
            </div>
          </div>
          <button @click="$router.push('/backtest')" class="stage-link" data-testid="stage-link-backtest">
            进入回测 →
          </button>
        </div>

        <div class="stage-card stage-2" data-testid="stage-validation">
          <div class="stage-header">
            <h3>验证</h3>
          </div>
          <div class="stage-stats">
            <div class="stage-stat">
              <span class="stat-label">验证组合</span>
              <span class="stat-number">--</span>
            </div>
            <div class="stage-stat">
              <span class="stat-label">通过验证</span>
              <span class="stat-number">--</span>
            </div>
          </div>
          <button @click="$router.push('/validation/walkforward')" class="stage-link" data-testid="stage-link-validation">
            进入验证 →
          </button>
        </div>

        <div class="stage-card stage-3" data-testid="stage-paper">
          <div class="stage-header">
            <h3>模拟</h3>
          </div>
          <div class="stage-stats">
            <div class="stage-stat">
              <span class="stat-label">模拟组合</span>
              <span class="stat-number">{{ portfolios.filter(p => String(p.mode) === 'PAPER').length }}</span>
            </div>
            <div class="stage-stat">
              <span class="stat-label">运行中</span>
              <span class="stat-number">{{ portfolios.filter(p => String(p.mode) === 'PAPER' && String(p.state) === 'RUNNING').length }}</span>
            </div>
          </div>
          <button @click="$router.push('/paper')" class="stage-link" data-testid="stage-link-paper">
            进入模拟 →
          </button>
        </div>

        <div class="stage-card stage-4" data-testid="stage-live">
          <div class="stage-header">
            <h3>实盘</h3>
          </div>
          <div class="stage-stats">
            <div class="stage-stat">
              <span class="stat-label">实盘组合</span>
              <span class="stat-number">{{ portfolios.filter(p => String(p.mode) === 'LIVE').length }}</span>
            </div>
            <div class="stage-stat">
              <span class="stat-label">运行中</span>
              <span class="stat-number">{{ portfolios.filter(p => String(p.mode) === 'LIVE' && String(p.state) === 'RUNNING').length }}</span>
            </div>
          </div>
          <button @click="$router.push('/live')" class="stage-link" data-testid="stage-link-live">
            进入实盘 →
          </button>
        </div>
      </div>

      <!-- Portfolio 列表 -->
      <div class="portfolio-list-card" v-if="portfolios.length > 0">
        <div class="list-header">
          <h3>Portfolio 列表</h3>
          <button @click="$router.push('/portfolio')" class="list-link">查看全部 →</button>
        </div>
        <div class="portfolio-table">
          <div class="table-row table-header-row">
            <span class="col-name">名称</span>
            <span class="col-mode">模式</span>
            <span class="col-state">状态</span>
            <span class="col-netvalue">净值</span>
          </div>
          <div
            v-for="p in portfolios.slice(0, 8)"
            :key="p.uuid"
            class="table-row"
            @click="$router.push(`/portfolio/${p.uuid}`)"
          >
            <span class="col-name">{{ p.name }}</span>
            <span class="col-mode">{{ modeLabel(p.mode) }}</span>
            <span class="col-state">
              <span class="badge" :class="stateClass(p.state)">{{ stateLabel(p.state) }}</span>
            </span>
            <span class="col-netvalue">{{ p.net_value?.toFixed(4) ?? '--' }}</span>
          </div>
        </div>
      </div>
      <div class="activity-card" v-else>
        <h3>Portfolio 列表</h3>
        <p v-if="loading">加载中...</p>
        <p v-else>暂无 Portfolio，<button @click="$router.push('/portfolio')" class="inline-link">创建一个 →</button></p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { portfolioApi } from '@/api'
import type { Portfolio } from '@/api'

interface Stats {
  total: number
  running: number
  avgNetValue: number
  totalAssets: number
}

const stats = ref<Stats>({ total: 0, running: 0, avgNetValue: 1, totalAssets: 0 })
const portfolios = ref<Portfolio[]>([])
const loading = ref(true)

async function fetchDashboardData() {
  loading.value = true
  try {
    const [statsResult, listResult] = await Promise.allSettled([
      portfolioApi.getStats(),
      portfolioApi.list({ page: 0, page_size: 10 })
    ])

    if (statsResult.status === 'fulfilled' && statsResult.value) {
      const d = statsResult.value
      stats.value = {
        total: d.total || 0,
        running: d.running || 0,
        avgNetValue: d.avg_net_value ?? 1,
        totalAssets: d.total_assets || 0,
      }
    }

    if (listResult.status === 'fulfilled' && listResult.value?.data) {
      portfolios.value = listResult.value.data
    }
  } finally {
    loading.value = false
  }
}

function stateLabel(state: string | number): string {
  const map: Record<string, string> = {
    RUNNING: '运行中',
    PAUSED: '已暂停',
    STOPPED: '已停止',
    COMPLETED: '已完成',
    ERROR: '异常',
  }
  return map[String(state)] ?? String(state)
}

function stateClass(state: string | number): string {
  const map: Record<string, string> = {
    RUNNING: 'badge-running',
    PAUSED: 'badge-paused',
    STOPPED: 'badge-stopped',
    COMPLETED: 'badge-completed',
    ERROR: 'badge-error',
  }
  return map[String(state)] ?? ''
}

function modeLabel(mode: string | number): string {
  const map: Record<string, string> = {
    BACKTEST: '回测',
    PAPER: '模拟',
    LIVE: '实盘',
  }
  return map[String(mode)] ?? String(mode)
}

onMounted(fetchDashboardData)
</script>

<style scoped>
.page-container {
  padding: 0;
  background: transparent;
}

.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 24px;
  font-weight: 600;
  color: #ffffff;
}

.page-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

/* 统计卡片网格 */

.stat-icon {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #2a2a3e;
  border-radius: 8px;
  color: #00ff88;
}

.stat-icon.success {
  color: #52c41a;
}

.stat-content {
  flex: 1;
}

.stat-suffix {
  font-size: 14px;
  color: #8a8a9a;
  font-weight: 400;
}

.text-success {
  color: #52c41a !important;
}

/* 阶段卡片网格 */
.stages-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.stage-card {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  padding: 20px;
  transition: all 0.2s;
}

.stage-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.stage-card.stage-1 {
  border-top: 3px solid #1890ff;
}

.stage-card.stage-2 {
  border-top: 3px solid #52c41a;
}

.stage-card.stage-3 {
  border-top: 3px solid #fa8c16;
}

.stage-card.stage-4 {
  border-top: 3px solid #f5222d;
}

.stage-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
  margin: 0 0 16px 0;
}

.stage-stats {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 16px;
}

.stage-stat {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stage-stat .stat-label {
  font-size: 12px;
  color: #8a8a9a;
}

.stage-stat .stat-number {
  font-size: 18px;
  font-weight: 600;
  color: #ffffff;
}

.stage-link {
  width: 100%;
  padding: 8px 16px;
  background: transparent;
  border: none;
  color: #1890ff;
  font-size: 14px;
  cursor: pointer;
  text-align: left;
  transition: color 0.2s;
}

.stage-link:hover {
  color: #40a9ff;
  text-decoration: underline;
}

/* 活动卡片 */
.activity-card {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  padding: 20px;
}

.activity-card h3 {
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
  margin: 0 0 16px 0;
}

.activity-card p {
  color: #8a8a9a;
  margin: 0;
}

/* Portfolio 列表 */
.portfolio-list-card {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  padding: 20px;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.list-header h3 {
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
  margin: 0;
}

.list-link {
  background: transparent;
  border: none;
  color: #1890ff;
  font-size: 14px;
  cursor: pointer;
}

.list-link:hover {
  text-decoration: underline;
}

.portfolio-table {
  display: flex;
  flex-direction: column;
}

.table-row {
  display: flex;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid #2a2a3e;
  cursor: pointer;
  transition: background 0.15s;
}

.table-row:hover {
  background: rgba(255, 255, 255, 0.03);
}

.table-row:last-child {
  border-bottom: none;
}

.table-header-row {
  cursor: default;
  color: #8a8a9a;
  font-size: 12px;
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.table-header-row:hover {
  background: transparent;
}

.col-name {
  flex: 2;
  color: #ffffff;
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.col-mode {
  flex: 1;
  color: #8a8a9a;
  font-size: 13px;
}

.col-state {
  flex: 1;
}

.col-netvalue {
  flex: 1;
  text-align: right;
  color: #ffffff;
  font-size: 14px;
  font-variant-numeric: tabular-nums;
}

/* Status badges */
.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.badge-running {
  background: rgba(82, 196, 26, 0.15);
  color: #52c41a;
}

.badge-paused {
  background: rgba(250, 140, 22, 0.15);
  color: #fa8c16;
}

.badge-stopped {
  background: rgba(255, 255, 255, 0.08);
  color: #8a8a9a;
}

.badge-completed {
  background: rgba(24, 144, 255, 0.15);
  color: #1890ff;
}

.badge-error {
  background: rgba(245, 34, 45, 0.15);
  color: #f5222d;
}

.inline-link {
  background: transparent;
  border: none;
  color: #1890ff;
  cursor: pointer;
  font-size: inherit;
  padding: 0;
}

.inline-link:hover {
  text-decoration: underline;
}
</style>
