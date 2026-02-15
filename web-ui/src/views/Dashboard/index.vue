<template>
  <div class="dashboard-container">
    <!-- Custom -->
    <div class="welcome-banner">
      <div class="banner-content">
        <h1 class="banner-title">欢迎使用 Ginkgo 量化交易平台</h1>
        <p class="banner-subtitle">管理您的投资组合、回测策略和实时交易</p>
      </div>
      <div class="banner-actions">
        <a-button type="primary" size="large" @click="goToPortfolio">
          <PlusOutlined /> 创建投资组合
        </a-button>
        <a-button size="large" @click="goToBacktest">
          <LineChartOutlined /> 创建回测
        </a-button>
      </div>
    </div>

    <!-- Custom -->
    <div class="stats-section">
      <h2 class="section-title">概览统计</h2>
      <div class="stats-grid">
        <StatisticCard
          title="总投资组合"
          :value="dashboardStats.totalPortfolios"
          :icon="FolderOutlined"
          icon-color="#1890ff"
          type="primary"
        />
        <StatisticCard
          title="总回测任务"
          :value="dashboardStats.totalBacktests"
          :icon="FileTextOutlined"
          icon-color="#52c41a"
          type="success"
        />
        <StatisticCard
          title="运行中策略"
          :value="dashboardStats.runningStrategies"
          :icon="PlayCircleOutlined"
          icon-color="#fa8c16"
          type="warning"
        />
        <StatisticCard
          title="总资产"
          :value="dashboardStats.totalAssets"
          :precision="2"
          prefix="¥"
          :icon="DollarOutlined"
          icon-color="#722ed1"
        />
      </div>
    </div>

    <!-- Custom -->
    <div class="quick-access-section">
      <h2 class="section-title">快捷入口</h2>
      <div class="quick-access-grid">
        <div class="quick-access-item" @click="router.push('/portfolio')">
          <div class="quick-icon" style="background: #e6f7ff;">
            <FolderOutlined />
          </div>
          <div class="quick-content">
            <h3>投资组合</h3>
            <p>管理和监控投资组合</p>
          </div>
          <ArrowRightOutlined class="quick-arrow" />
        </div>

        <div class="quick-access-item" @click="router.push('/backtest')">
          <div class="quick-icon" style="background: #f6ffed;">
            <LineChartOutlined />
          </div>
          <div class="quick-content">
            <h3>回测任务</h3>
            <p>创建和管理回测任务</p>
          </div>
          <ArrowRightOutlined class="quick-arrow" />
        </div>

        <div class="quick-access-item" @click="router.push('/research')">
          <div class="quick-icon" style="background: #fff7e6;">
            <ExperimentOutlined />
          </div>
          <div class="quick-content">
            <h3>因子研究</h3>
            <p>分析因子表现</p>
          </div>
          <ArrowRightOutlined class="quick-arrow" />
        </div>

        <div class="quick-access-item" @click="router.push('/trading')">
          <div class="quick-icon" style="background: #fff1f0;">
            <ThunderboltOutlined />
          </div>
          <div class="quick-content">
            <h3>实时交易</h3>
            <p>监控实时交易</p>
          </div>
          <ArrowRightOutlined class="quick-arrow" />
        </div>

        <div class="quick-access-item" @click="router.push('/components')">
          <div class="quick-icon" style="background: #f9f0ff;">
            <AppstoreOutlined />
          </div>
          <div class="quick-content">
            <h3>组件管理</h3>
            <p>管理策略组件</p>
          </div>
          <ArrowRightOutlined class="quick-arrow" />
        </div>

        <div class="quick-access-item" @click="router.push('/data')">
          <div class="quick-icon" style="background: #e6fffb;">
            <DatabaseOutlined />
          </div>
          <div class="quick-content">
            <h3>数据管理</h3>
            <p>管理市场数据</p>
          </div>
          <ArrowRightOutlined class="quick-arrow" />
        </div>
      </div>
    </div>

    <!-- Custom -->
    <div class="recent-section">
      <h2 class="section-title">最近活动</h2>
      <a-card class="recent-card">
        <a-empty v-if="recentActivities.length === 0" description="暂无最近活动" />
        <a-timeline v-else>
          <a-timeline-item
            v-for="activity in recentActivities"
            :key="activity.id"
            :color="activity.color"
          >
            <template #dot>
              <component :is="activity.icon" class="timeline-icon" />
            </template>
            <div class="activity-content">
              <span class="activity-title">{{ activity.title }}</span>
              <span class="activity-time">{{ activity.time }}</span>
            </div>
            <p class="activity-description">{{ activity.description }}</p>
          </a-timeline-item>
        </a-timeline>
      </a-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  PlusOutlined,
  LineChartOutlined,
  FolderOutlined,
  FileTextOutlined,
  PlayCircleOutlined,
  DollarOutlined,
  ArrowRightOutlined,
  ExperimentOutlined,
  ThunderboltOutlined,
  AppstoreOutlined,
  DatabaseOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined
} from '@ant-design/icons-vue'
import StatisticCard from '@/components/data/StatisticCard.vue'

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
        icon: CheckCircleOutlined,
        color: 'green'
      },
      {
        id: '2',
        title: '投资组合创建',
        description: '创建新投资组合 "多因子选股策略"',
        time: '1小时前',
        icon: FolderOutlined,
        color: 'blue'
      },
      {
        id: '3',
        title: '回测任务运行中',
        description: '均线交叉策略回测正在进行中 (45%)',
        time: '2小时前',
        icon: ClockCircleOutlined,
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
  background: #f5f7fa;
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

/* 统计概览 */
.stats-section {
  margin-bottom: 32px;
}

.section-title {
  font-size: 20px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0 0 20px 0;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
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
  background: white;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.quick-access-item:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

.quick-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  color: white;
  flex-shrink: 0;
}

.quick-content {
  flex: 1;
}

.quick-content h3 {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a1a;
  margin: 0 0 4px 0;
}

.quick-content p {
  font-size: 13px;
  color: #8c8c8c;
  margin: 0;
}

.quick-arrow {
  font-size: 14px;
  color: #8c8c8c;
}

/* 最近活动 */
.recent-section {
  margin-bottom: 32px;
}

.recent-card {
  border-radius: 12px;
  border: none;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.timeline-icon {
  font-size: 14px;
  color: white;
}

.activity-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}

.activity-title {
  font-size: 14px;
  font-weight: 500;
  color: #1a1a1a;
}

.activity-time {
  font-size: 12px;
  color: #8c8c8c;
}

.activity-description {
  font-size: 13px;
  color: #595c8c;
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
  }

  .banner-actions .ant-btn {
    flex: 1;
  }

  .stats-grid {
    grid-template-columns: 1fr;
  }

  .quick-access-grid {
    grid-template-columns: 1fr;
  }
}
</style>
