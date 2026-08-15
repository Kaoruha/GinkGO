<template>
  <div class="overview-tab">
    <template v-if="stats && stats.completed_backtests > 0">
      <div class="stats-row">
        <div class="stat-card">
          <div class="stat-label">回测数</div>
          <div class="stat-value">{{ stats.completed_backtests }}<span class="stat-sub"> / {{ stats.total_backtests }}</span></div>
          <div class="stat-note">已完成 / 全部</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">平均净值</div>
          <div class="stat-value">{{ fmt(stats.avg_nav, 4) }}</div>
          <div class="stat-note" v-if="stats.best_nav != null">最佳 {{ fmt(stats.best_nav, 4) }} · 最差 {{ fmt(stats.worst_nav, 4) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">平均最大回撤</div>
          <div class="stat-value" :class="{ negative: (stats.avg_max_drawdown ?? 0) < 0 }">{{ pct(stats.avg_max_drawdown) }}</div>
          <div class="stat-note" v-if="stats.worst_max_drawdown != null">最差 {{ pct(stats.worst_max_drawdown) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">平均夏普比率</div>
          <div class="stat-value">{{ fmt(stats.avg_sharpe_ratio, 2) }}</div>
          <div class="stat-note" v-if="stats.best_sharpe_ratio != null">最佳 {{ fmt(stats.best_sharpe_ratio, 2) }}</div>
        </div>
      </div>
      <div class="stats-row">
        <div class="stat-card">
          <div class="stat-label">平均年化收益</div>
          <div class="stat-value">{{ pct(stats.avg_annual_return) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">平均胜率</div>
          <div class="stat-value">{{ pct(stats.avg_win_rate) }}</div>
        </div>
        <div class="stat-card latest-card" v-if="stats.latest_completed">
          <div class="stat-label">最近完成回测</div>
          <div class="latest-name" :title="stats.latest_completed.name">{{ stats.latest_completed.name || stats.latest_completed.uuid }}</div>
          <div class="stat-note">净值 {{ fmt(stats.latest_completed.nav, 4) }} · 回撤 {{ pct(stats.latest_completed.max_drawdown) }} · 夏普 {{ fmt(stats.latest_completed.sharpe_ratio, 2) }}</div>
        </div>
      </div>
    </template>
    <EmptyState
      v-else-if="!loading"
      :title="stats && stats.total_backtests > 0 ? '暂无已完成的回测' : '暂无回测'"
      :description="stats && stats.total_backtests > 0 ? '回测完成后此处将展示聚合统计' : '创建并运行回测后，概况数据将在此显示'"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { backtestApi, PortfolioBacktestStats } from '@/api/modules/backtest'
import { message } from '@/utils/toast'
import EmptyState from '@/components/common/EmptyState.vue'

const route = useRoute()
const stats = ref<PortfolioBacktestStats | null>(null)
const loading = ref(true)

function fmt(v: number | null | undefined, digits: number): string {
  return v == null ? '--' : v.toFixed(digits)
}
function pct(v: number | null | undefined): string {
  return v == null ? '--' : `${(v * 100).toFixed(2)}%`
}

onMounted(async () => {
  const pid = route.params.id as string
  if (!pid) return
  try {
    stats.value = await backtestApi.getPortfolioStats(pid)
  } catch (e) {
    // 静默失败会让统计卡片全显示 '--',须提示让用户知晓是加载失败而非无数据
    console.error('加载组合回测统计失败:', e)
    message.error('组合回测统计加载失败，请刷新重试')
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.overview-tab {
  min-height: 200px;
}

.stats-row {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
}

.stat-card {
  flex: 1;
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius-lg);
  padding: 16px;
  min-width: 0;
}

.stat-label {
  font-size: 12px;
  color: hsl(var(--muted-foreground));
  margin-bottom: 4px;
}

.stat-value {
  font-size: 20px;
  font-weight: 700;
  color: hsl(var(--foreground));
}

.stat-value.negative { color: hsl(var(--destructive)); }

.stat-sub {
  font-size: 13px;
  font-weight: 400;
  color: hsl(var(--muted-foreground));
}

.stat-note {
  margin-top: 4px;
  font-size: 12px;
  color: hsl(var(--muted-foreground));
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.latest-card .latest-name {
  font-size: 14px;
  font-weight: 600;
  color: hsl(var(--foreground));
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
