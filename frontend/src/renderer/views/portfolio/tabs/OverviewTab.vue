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
          <router-link class="latest-name" :to="`/backtests/${stats.latest_completed.uuid}`" :title="`查看 ${stats.latest_completed.name} 详情`">
            {{ stats.latest_completed.name || stats.latest_completed.uuid.slice(0, 8) }} →
          </router-link>
          <div class="stat-note">净值 {{ fmt(stats.latest_completed.nav, 4) }} · 回撤 {{ pct(stats.latest_completed.max_drawdown) }} · 夏普 {{ fmt(stats.latest_completed.sharpe_ratio, 2) }}</div>
        </div>
      </div>

      <!-- 多回测净值叠加对比:组合视角核心(改参数→重跑→对比),均值卡无法呈现走势差异 -->
      <div class="card compare-card">
        <div class="compare-head">
          <h4>回测净值对比</h4>
          <span class="compare-note">最近 {{ compareSeries.length }} 个已完成回测</span>
        </div>
        <div v-if="compareLoading" class="loading-center"><div class="spinner"></div></div>
        <NetValueCompareChart v-else-if="compareSeries.length > 0" :height="280" :series="compareSeries" />
        <p v-else class="compare-empty">净值数据暂缺（回测未产出 net_value 分析器记录）</p>
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
import { NetValueCompareChart } from '@/components/charts'
import type { CompareSeries } from '@/components/charts'

const route = useRoute()
const stats = ref<PortfolioBacktestStats | null>(null)
const loading = ref(true)
const compareSeries = ref<CompareSeries[]>([])
const compareLoading = ref(true)

function fmt(v: number | null | undefined, digits: number): string {
  return v == null ? '--' : v.toFixed(digits)
}
function pct(v: number | null | undefined): string {
  return v == null ? '--' : `${(v * 100).toFixed(2)}%`
}

// 拉最近 N 个已完成回测的净值曲线做叠加对比。净值端点 404/空数据均按"该任务无
// 净值"跳过（老任务可能缺 net_value 记录），不弹错刷屏。
const COMPARE_LIMIT = 5
async function loadCompare(pid: string) {
  try {
    const res = await backtestApi.list({ portfolio_id: pid, status: 'completed', page: 1, page_size: COMPARE_LIMIT })
    const tasks = res.items || []
    const loaded: CompareSeries[] = []
    for (const t of tasks) {
      try {
        const nv = await backtestApi.getNetValue(t.uuid)
        const data = (nv?.strategy || []).map((i: any) => ({ time: String(i.time).substring(0, 10), value: Number(i.value) }))
        if (data.length > 0) {
          loaded.push({ name: t.name || t.uuid.slice(0, 8), data })
        }
      } catch { /* 单任务净值缺失跳过 */ }
    }
    compareSeries.value = loaded
  } catch (e) {
    console.error('加载回测净值对比失败:', e)
  } finally {
    compareLoading.value = false
  }
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
  loadCompare(pid)
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
  color: hsl(var(--primary));
  text-decoration: none;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: block;
}
.latest-card .latest-name:hover { text-decoration: underline; }

.compare-card {
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius-lg);
  padding: 14px 16px;
}
.compare-head {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 6px;
}
.compare-head h4 {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  color: hsl(var(--foreground));
}
.compare-note { font-size: 12px; color: hsl(var(--muted-foreground)); }
.compare-empty { font-size: 13px; color: hsl(var(--muted-foreground)); margin: 8px 0; }

.loading-center { display: flex; justify-content: center; padding: 40px; }
.spinner {
  width: 24px; height: 24px;
  border: 2px solid hsl(var(--border));
  border-top-color: hsl(var(--primary));
  border-radius: 50%;
  animation: spin 0.6s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
