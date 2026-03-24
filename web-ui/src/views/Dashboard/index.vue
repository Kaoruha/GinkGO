<template>
  <div class="dashboard-container">
    <!-- Custom -->
    <div class="welcome-banner">
      <div class="banner-content">
        <h1 class="banner-title">欢迎使用 Ginkgo 量化交易平台</h1>
        <p class="banner-subtitle">管理您的投资组合、回测策略和实时交易</p>
      </div>
      <div class="banner-actions">
        <button class="btn btn-large btn-primary" @click="goToPortfolio">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="5" x2="12" y2="19"></line>
            <line x1="5" y1="12" x2="19" y2="12"></line>
          </svg>
          创建投资组合
        </button>
        <button class="btn btn-large btn-secondary" @click="goToBacktest">
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="3" y1="3" x2="21" y2="3"></line>
            <path d="m19 9-5 5-4-4-3 3"></path>
          </svg>
          创建回测
        </button>
      </div>
    </div>

    <!-- Custom -->
    <div class="stats-section">
      <h2 class="section-title">概览统计</h2>
      <div class="stats-grid">
        <div class="stat-card stat-primary">
          <div class="stat-icon" style="background: rgba(24, 144, 255, 0.2); color: #1890ff;">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
            </svg>
          </div>
          <div class="stat-content">
            <div class="stat-label">总投资组合</div>
            <div class="stat-value">{{ dashboardStats.totalPortfolios }}</div>
          </div>
        </div>
        <div class="stat-card stat-success">
          <div class="stat-icon" style="background: rgba(82, 196, 26, 0.2); color: #52c41a;">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
              <polyline points="14 2 14 8 20 8"></polyline>
              <line x1="16" y1="13" x2="8" y2="13"></line>
              <line x1="16" y1="17" x2="8" y2="17"></line>
              <polyline points="10 9 9 9 8 9"></polyline>
            </svg>
          </div>
          <div class="stat-content">
            <div class="stat-label">总回测任务</div>
            <div class="stat-value">{{ dashboardStats.totalBacktests }}</div>
          </div>
        </div>
        <div class="stat-card stat-warning">
          <div class="stat-icon" style="background: rgba(250, 173, 20, 0.2); color: #faad14;">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <circle cx="12" cy="12" r="10"></circle>
              <polygon points="10 8 16 12 10 16 10 8"></polygon>
            </svg>
          </div>
          <div class="stat-content">
            <div class="stat-label">运行中策略</div>
            <div class="stat-value">{{ dashboardStats.runningStrategies }}</div>
          </div>
        </div>
        <div class="stat-card stat-purple">
          <div class="stat-icon" style="background: rgba(114, 46, 209, 0.2); color: #722ed1;">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="12" y1="1" x2="12" y2="23"></line>
              <path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path>
            </svg>
          </div>
          <div class="stat-content">
            <div class="stat-label">总资产</div>
            <div class="stat-value">¥{{ formatNumber(dashboardStats.totalAssets) }}</div>
          </div>
        </div>
      </div>
    </div>

    <!-- Custom -->
    <div class="quick-access-section">
      <h2 class="section-title">快捷入口</h2>
      <div class="quick-access-grid">
        <div class="quick-access-item" @click="router.push('/portfolio')">
          <div class="quick-icon quick-blue">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
            </svg>
          </div>
          <div class="quick-content">
            <h3>投资组合</h3>
            <p>管理和监控投资组合</p>
          </div>
          <svg class="quick-arrow" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="9 18 15 12 9 6"></polyline>
          </svg>
        </div>

        <div class="quick-access-item" @click="router.push('/backtest')">
          <div class="quick-icon quick-green">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="3" y1="3" x2="21" y2="3"></line>
              <path d="m19 9-5 5-4-4-3 3"></path>
            </svg>
          </div>
          <div class="quick-content">
            <h3>回测任务</h3>
            <p>创建和管理回测任务</p>
          </div>
          <svg class="quick-arrow" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="9 18 15 12 9 6"></polyline>
          </svg>
        </div>

        <div class="quick-access-item" @click="router.push('/research')">
          <div class="quick-icon quick-orange">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <path d="M10 2v7.31"></path>
              <path d="M14 2v7.31"></path>
              <path d="M8.5 2h7"></path>
              <path d="M14 9.3a6.5 6.5 0 1 1-4 0"></path>
            </svg>
          </div>
          <div class="quick-content">
            <h3>因子研究</h3>
            <p>分析因子表现</p>
          </div>
          <svg class="quick-arrow" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="9 18 15 12 9 6"></polyline>
          </svg>
        </div>

        <div class="quick-access-item" @click="router.push('/trading')">
          <div class="quick-icon quick-red">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon>
            </svg>
          </div>
          <div class="quick-content">
            <h3>实时交易</h3>
            <p>监控实时交易</p>
          </div>
          <svg class="quick-arrow" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="9 18 15 12 9 6"></polyline>
          </svg>
        </div>

        <div class="quick-access-item" @click="router.push('/components')">
          <div class="quick-icon quick-purple">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="3" y="3" width="7" height="7"></rect>
              <rect x="14" y="3" width="7" height="7"></rect>
              <rect x="14" y="14" width="7" height="7"></rect>
              <rect x="3" y="14" width="7" height="7"></rect>
            </svg>
          </div>
          <div class="quick-content">
            <h3>组件管理</h3>
            <p>管理策略组件</p>
          </div>
          <svg class="quick-arrow" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="9 18 15 12 9 6"></polyline>
          </svg>
        </div>

        <div class="quick-access-item" @click="router.push('/data')">
          <div class="quick-icon quick-cyan">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <ellipse cx="12" cy="5" rx="9" ry="3"></ellipse>
              <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"></path>
              <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"></path>
            </svg>
          </div>
          <div class="quick-content">
            <h3>数据管理</h3>
            <p>管理市场数据</p>
          </div>
          <svg class="quick-arrow" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="9 18 15 12 9 6"></polyline>
          </svg>
        </div>
      </div>
    </div>

    <!-- Custom -->
    <div class="recent-section">
      <h2 class="section-title">最近活动</h2>
      <div class="card">
        <div v-if="recentActivities.length === 0" class="empty-state">
          <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
          </svg>
          <p>暂无最近活动</p>
        </div>
        <div v-else class="timeline">
          <div
            v-for="activity in recentActivities"
            :key="activity.id"
            class="timeline-item"
            :class="`timeline-${activity.color}`"
          >
            <div class="timeline-dot">
              <svg v-if="activity.type === 'success'" class="timeline-icon" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                <polyline points="22 4 12 14.01 9 11.01"></polyline>
              </svg>
              <svg v-else-if="activity.type === 'folder'" class="timeline-icon" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
              </svg>
              <svg v-else class="timeline-icon" xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="12" cy="12" r="10"></circle>
                <polyline points="12 6 12 12 16 14"></polyline>
              </svg>
            </div>
            <div class="timeline-content">
              <div class="activity-header">
                <span class="activity-title">{{ activity.title }}</span>
                <span class="activity-time">{{ activity.time }}</span>
              </div>
              <p class="activity-description">{{ activity.description }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

// 仪表盘统计数据
const dashboardStats = ref({
  totalPortfolios: 0,
  totalBacktests: 0,
  runningStrategies: 0,
  totalAssets: 0
})

// 最近活动
const recentActivities = ref<any[]>([])

// 格式化数字
const formatNumber = (num: number): string => {
  return num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// 跳转投资组合
const goToPortfolio = () => {
  router.push('/portfolio')
}

// 跳转回测
const goToBacktest = () => {
  router.push('/backtest')
}

// 加载仪表盘数据
const loadDashboardData = async () => {
  try {
    // TODO: 从 API 加载数据
    dashboardStats.value = {
      totalPortfolios: 12,
      totalBacktests: 48,
      runningStrategies: 3,
      totalAssets: 1580000.50
    }

    // 模拟最近活动
    recentActivities.value = [
      {
        id: '1',
        title: '回测完成',
        description: '双均线策略 v2 回测完成，年化收益 15.6%',
        time: '10分钟前',
        type: 'success',
        color: 'green'
      },
      {
        id: '2',
        title: '投资组合创建',
        description: '创建新投资组合 "多因子选股策略"',
        time: '1小时前',
        type: 'folder',
        color: 'blue'
      },
      {
        id: '3',
        title: '回测任务运行中',
        description: '均线交叉策略回测正在进行中 (45%)',
        time: '2小时前',
        type: 'clock',
        color: 'orange'
      }
    ]
  } catch (error) {
    console.error('加载仪表盘数据失败:', error)
  }
}

onMounted(() => {
  loadDashboardData()
})
</script>

<style scoped>
.dashboard-container {
  padding: 24px;
  background: #0f0f1a;
  min-height: calc(100vh - 64px);
}

/* 欢迎横幅 */
.welcome-banner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 32px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 16px;
  margin-bottom: 32px;
  color: white;
}

.banner-content {
  flex: 1;
}

.banner-title {
  font-size: 32px;
  font-weight: 700;
  margin: 0 0 8px 0;
  color: white;
}

.banner-subtitle {
  font-size: 16px;
  margin: 0;
  opacity: 0.9;
}

.banner-actions {
  display: flex;
  gap: 16px;
}

.btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  border-radius: 4px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}

.btn-large {
  padding: 12px 24px;
  font-size: 16px;
}

.btn-primary {
  background: #ffffff;
  color: #667eea;
}

.btn-primary:hover {
  background: #f0f0f0;
}

.btn-secondary {
  background: rgba(255, 255, 255, 0.2);
  color: #ffffff;
  border: 1px solid rgba(255, 255, 255, 0.3);
}

.btn-secondary:hover {
  background: rgba(255, 255, 255, 0.3);
}

/* 统计概览 */
.stats-section {
  margin-bottom: 32px;
}

.section-title {
  font-size: 20px;
  font-weight: 600;
  color: #ffffff;
  margin: 0 0 20px 0;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: #1a1a2e;
  border-radius: 12px;
  border: 1px solid #2a2a3e;
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-content {
  flex: 1;
}

.stat-label {
  font-size: 13px;
  color: #8a8a9a;
  margin-bottom: 4px;
}

.stat-value {
  font-size: 24px;
  font-weight: 600;
  color: #ffffff;
}

/* 快捷入口 */
.quick-access-section {
  margin-bottom: 32px;
}

.quick-access-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}

.quick-access-item {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: #1a1a2e;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s;
  border: 1px solid #2a2a3e;
}

.quick-access-item:hover {
  transform: translateY(-4px);
  border-color: #1890ff;
  box-shadow: 0 8px 24px rgba(24, 144, 255, 0.15);
}

.quick-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.quick-blue { background: rgba(24, 144, 255, 0.2); }
.quick-blue svg { color: #1890ff; }

.quick-green { background: rgba(82, 196, 26, 0.2); }
.quick-green svg { color: #52c41a; }

.quick-orange { background: rgba(250, 173, 20, 0.2); }
.quick-orange svg { color: #faad14; }

.quick-red { background: rgba(245, 34, 45, 0.2); }
.quick-red svg { color: #f5222d; }

.quick-purple { background: rgba(114, 46, 209, 0.2); }
.quick-purple svg { color: #722ed1; }

.quick-cyan { background: rgba(19, 194, 194, 0.2); }
.quick-cyan svg { color: #13c2c2; }

.quick-content {
  flex: 1;
}

.quick-content h3 {
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
  margin: 0 0 4px 0;
}

.quick-content p {
  font-size: 13px;
  color: #8a8a9a;
  margin: 0;
}

.quick-arrow {
  color: #8a8a9a;
  flex-shrink: 0;
}

/* 最近活动 */
.recent-section {
  margin-bottom: 32px;
}

.card {
  background: #1a1a2e;
  border-radius: 12px;
  border: 1px solid #2a2a3e;
  padding: 20px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  text-align: center;
  color: #8a8a9a;
}

.empty-state svg {
  opacity: 0.3;
  margin-bottom: 16px;
}

.empty-state p {
  margin: 0;
}

.timeline {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.timeline-item {
  display: flex;
  gap: 12px;
}

.timeline-dot {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.timeline-green .timeline-dot {
  background: #52c41a;
}

.timeline-blue .timeline-dot {
  background: #1890ff;
}

.timeline-orange .timeline-dot {
  background: #faad14;
}

.timeline-icon {
  color: #ffffff;
}

.timeline-content {
  flex: 1;
}

.activity-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.activity-title {
  font-size: 14px;
  font-weight: 500;
  color: #ffffff;
}

.activity-time {
  font-size: 12px;
  color: #8a8a9a;
}

.activity-description {
  font-size: 13px;
  color: #8a8a9a;
  margin: 0;
}

/* 响应式 */
@media (max-width: 1400px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .quick-access-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .welcome-banner {
    flex-direction: column;
    gap: 16px;
  }

  .banner-actions {
    width: 100%;
    flex-direction: column;
  }

  .banner-actions .btn {
    width: 100%;
    justify-content: center;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }

  .quick-access-grid {
    grid-template-columns: 1fr;
  }
}
</style>
