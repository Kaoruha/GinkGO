<template>
  <div class="page-container">
    <div class="page-header">
      <div class="page-title">
        <span class="tag tag-cyan">数据</span>
        数据概览
      </div>
      <button class="btn-primary" :disabled="refreshing" @click="refreshStats">
        <svg v-if="!refreshing" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 2v6h-6"/>
          <path d="M3 12a9 9 0 0 1 15-6.7L21 8"/>
          <path d="M3 22v-6h6"/>
          <path d="M21 12a9 9 0 0 1-15 6.7L3 16"/>
        </svg>
        <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" class="spin">
          <path d="M21 12a9 9 0 1 1-6.219-8.56"/>
        </svg>
        {{ refreshing ? '刷新中...' : '刷新统计' }}
      </button>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-grid">
      <div class="stat-card stat-blue" @click="navigateTo('/data/stocks')">
        <div class="stat-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="2" y="7" width="20" height="14" rx="2" ry="2"/>
            <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>
          </svg>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ formatNumber(dataStats.totalStocks) }}</div>
          <div class="stat-label">股票总数</div>
        </div>
        <div class="stat-footer">点击查看详情 →</div>
      </div>

      <div class="stat-card stat-green" @click="navigateTo('/data/bars')">
        <div class="stat-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M3 3v18h18"/>
            <path d="M18 17V9"/>
            <path d="M13 17V5"/>
            <path d="M8 17v-3"/>
          </svg>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ formatNumber(dataStats.totalBars) }}</div>
          <div class="stat-label">K线数据量</div>
        </div>
        <div class="stat-footer">点击查看详情 →</div>
      </div>

      <div class="stat-card stat-orange" @click="navigateTo('/data/ticks')">
        <div class="stat-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polygon points="13,2 3,14 12,14 11,22 21,10 12,10"/>
          </svg>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ formatNumber(dataStats.totalTicks) }}</div>
          <div class="stat-label">Tick数据量</div>
        </div>
        <div class="stat-footer">点击查看详情 →</div>
      </div>

      <div class="stat-card stat-purple" @click="navigateTo('/data/adjustfactors')">
        <div class="stat-icon">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="12" y1="20" x2="12" y2="10"/>
            <line x1="18" y1="20" x2="18" y2="4"/>
            <line x1="6" y1="20" x2="6" y2="16"/>
          </svg>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ formatNumber(dataStats.totalAdjustFactors) }}</div>
          <div class="stat-label">复权因子</div>
        </div>
        <div class="stat-footer">点击查看详情 →</div>
      </div>
    </div>

    <!-- 快捷操作 -->
    <div class="card">
      <h3 class="card-title">快捷操作</h3>
      <div class="actions-grid">
        <button class="action-btn" @click="navigateTo('/data/sync')">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 2v6h-6"/>
            <path d="M3 12a9 9 0 0 1 15-6.7L21 8"/>
            <path d="M3 22v-6h6"/>
            <path d="M21 12a9 9 0 0 1-15 6.7L3 16"/>
          </svg>
          数据同步
        </button>
        <button class="action-btn">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="7,10 12,15 17,10"/>
            <line x1="12" y1="15" x2="12" y2="3"/>
          </svg>
          导入数据
        </button>
        <button class="action-btn">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="17,8 12,3 7,8"/>
            <line x1="12" y1="3" x2="12" y2="15"/>
          </svg>
          导出数据
        </button>
        <button class="action-btn">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="12" cy="12" r="3"/>
            <path d="M12 1v6m0 6v6"/>
            <path d="m4.93 4.93 4.24 4.24m5.66 5.66 4.24 4.24M1 12h6m6 0h6M4.93 19.07l4.24-4.24m5.66-5.66 4.24-4.24"/>
          </svg>
          数据源配置
        </button>
      </div>
    </div>

    <!-- 最近更新 -->
    <div class="two-column-grid">
      <div class="card">
        <h3 class="card-title">最近同步记录</h3>
        <div v-if="recentSyncs.length > 0" class="timeline">
          <div v-for="(item, index) in recentSyncs" :key="index" class="timeline-item">
            <div class="timeline-dot" :class="item.status"></div>
            <div class="timeline-content">
              <div class="timeline-title">{{ item.type }} - {{ item.code }}</div>
              <div class="timeline-time">{{ item.time }}</div>
            </div>
          </div>
        </div>
        <div v-else class="empty-state">
          <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
            <circle cx="12" cy="12" r="10"/>
            <line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          <p>暂无同步记录</p>
        </div>
      </div>

      <div class="card">
        <h3 class="card-title">数据源状态</h3>
        <div class="data-sources">
          <div v-for="source in dataSources" :key="source.name" class="data-source-item">
            <div class="source-info">
              <div class="source-name">{{ source.name }}</div>
              <div class="source-desc">{{ source.description }}</div>
            </div>
            <span class="status-tag" :class="source.status">
              {{ source.status === 'online' ? '在线' : '离线' }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()
const refreshing = ref(false)

const dataStats = reactive({
  totalStocks: 0,
  totalBars: 0,
  totalTicks: 0,
  totalAdjustFactors: 0
})

const recentSyncs = ref([
  { type: 'K线数据', code: '000001.SZ', time: '2024-02-17 10:30:00', status: 'success' },
  { type: '股票信息', code: '全市场', time: '2024-02-17 09:00:00', status: 'success' },
])

const dataSources = ref([
  { name: 'Tushare', description: 'A股行情数据', status: 'online' },
  { name: 'AKShare', description: '多市场数据', status: 'online' },
  { name: 'BaoStock', description: '证券宝数据', status: 'offline' },
])

const refreshStats = async () => {
  refreshing.value = true
  try {
    // TODO: 调用API获取统计数据
    dataStats.totalStocks = 5420
    dataStats.totalBars = 12500000
    dataStats.totalTicks = 250000000
    dataStats.totalAdjustFactors = 54200
  } catch (error: any) {
    console.error(`刷新失败: ${error.message}`)
  } finally {
    refreshing.value = false
  }
}

const navigateTo = (path: string) => {
  router.push(path)
}

const formatNumber = (num: number): string => {
  if (num >= 100000000) {
    return (num / 100000000).toFixed(1) + '亿'
  } else if (num >= 10000) {
    return (num / 10000).toFixed(1) + '万'
  }
  return num.toString()
}

onMounted(() => {
  refreshStats()
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
}

.page-title {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 24px;
  font-weight: 600;
  color: #ffffff;
}

.btn-primary:hover:not(:disabled) {
  background: #40a9ff;
}

/* 统计卡片 */

.stat-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
}

.stat-card.stat-blue::before { background: #1890ff; }
.stat-card.stat-green::before { background: #52c41a; }
.stat-card.stat-orange::before { background: #fa8c16; }
.stat-card.stat-purple::before { background: #722ed1; }

.stat-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: 8px;
  margin-bottom: 12px;
}

.stat-blue .stat-icon { background: rgba(24, 144, 255, 0.1); color: #1890ff; }
.stat-green .stat-icon { background: rgba(82, 196, 26, 0.1); color: #52c41a; }
.stat-orange .stat-icon { background: rgba(250, 140, 22, 0.1); color: #fa8c16; }
.stat-purple .stat-icon { background: rgba(114, 46, 209, 0.1); color: #722ed1; }

.stat-footer {
  margin-top: 12px;
  font-size: 12px;
  color: #1890ff;
}

/* 卡片 */

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
  margin: 0 0 16px 0;
}

/* 快捷操作 */
.actions-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.action-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px;
  background: transparent;
  border: 1px dashed #4a4a5e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.action-btn:hover {
  border-color: #1890ff;
  color: #1890ff;
}

/* 两列网格 */
.two-column-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}

/* 时间线 */
.timeline {
  position: relative;
  padding-left: 20px;
}

.timeline::before {
  content: '';
  position: absolute;
  left: 6px;
  top: 8px;
  bottom: 8px;
  width: 2px;
  background: #2a2a3e;
}

.timeline-item {
  position: relative;
  padding-bottom: 16px;
}

.timeline-item:last-child {
  padding-bottom: 0;
}

.timeline-dot {
  position: absolute;
  left: -20px;
  top: 4px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  border: 2px solid #1a1a2e;
}

.timeline-dot.success {
  background: #52c41a;
}

.timeline-dot.error {
  background: #f5222d;
}

.timeline-content {
  padding-left: 8px;
}

.timeline-title {
  font-size: 14px;
  color: #ffffff;
  margin-bottom: 4px;
}

.timeline-time {
  font-size: 12px;
  color: #8a8a9a;
}

/* 空状态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: #8a8a9a;
}

.empty-state svg {
  margin-bottom: 12px;
  opacity: 0.5;
}

.empty-state p {
  margin: 0;
}

/* 数据源列表 */
.data-sources {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.data-source-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: #2a2a3e;
  border-radius: 4px;
}

.source-info {
  flex: 1;
}

.source-name {
  font-size: 14px;
  color: #ffffff;
  margin-bottom: 4px;
}

.source-desc {
  font-size: 12px;
  color: #8a8a9a;
}

.status-tag {
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 500;
}

.status-tag.online {
  background: rgba(82, 196, 26, 0.2);
  color: #52c41a;
}

.status-tag.offline {
  background: rgba(245, 34, 45, 0.2);
  color: #f5222d;
}
</style>
