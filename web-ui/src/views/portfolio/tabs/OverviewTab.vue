<template>
  <div class="overview-tab">
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-label">最新净值</div>
        <div class="stat-value">{{ formatNumber(portfolio?.net_value) }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">总收益率</div>
        <div class="stat-value" :class="pnlClass">{{ formatPct(portfolio?.pnl_rate) }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">最大回撤</div>
        <div class="stat-value text-danger">{{ formatPct(portfolio?.max_drawdown) }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">夏普比率</div>
        <div class="stat-value">{{ formatNumber(portfolio?.sharpe_ratio) }}</div>
      </div>
    </div>
    <div class="section">
      <h3>最近活动</h3>
      <div class="activity-list">
        <div v-if="!activities.length" class="empty-hint">暂无活动记录</div>
        <div v-for="item in activities" :key="item.id" class="activity-item">
          <span class="activity-time">{{ item.time }}</span>
          <span class="activity-text">{{ item.text }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  portfolio: Record<string, any> | null
}>()

const activities = computed(() => [])

const pnlClass = computed(() => {
  const rate = props.portfolio?.pnl_rate
  if (rate == null) return ''
  return rate >= 0 ? 'text-profit' : 'text-danger'
})

const formatNumber = (v: any) => v != null ? Number(v).toFixed(4) : '--'
const formatPct = (v: any) => v != null ? `${v >= 0 ? '+' : ''}${(Number(v) * 100).toFixed(2)}%` : '--'
</script>

<style scoped>
.stats-row {
  display: flex;
  gap: 16px;
  margin-bottom: 24px;
}
.stat-card {
  flex: 1;
  background: #1a1a2e;
  border-radius: 8px;
  padding: 16px;
}
.stat-label {
  font-size: 12px;
  color: rgba(255,255,255,0.5);
  text-transform: uppercase;
  margin-bottom: 4px;
}
.stat-value {
  font-size: 20px;
  font-weight: 700;
}
.text-profit { color: #22c55e; }
.text-danger { color: #ef4444; }
.section {
  margin-top: 16px;
}
.section h3 {
  font-size: 14px;
  margin-bottom: 12px;
}
.activity-item {
  padding: 6px 0;
  font-size: 13px;
  color: rgba(255,255,255,0.7);
}
.activity-time {
  margin-right: 12px;
  color: rgba(255,255,255,0.4);
  font-size: 12px;
}
.empty-hint {
  color: rgba(255,255,255,0.4);
  font-size: 13px;
  padding: 16px 0;
}
</style>
