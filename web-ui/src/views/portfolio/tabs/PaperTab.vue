<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { getPaperAccount, getPaperPositions, getPaperOrders } from '@/api/modules/trading'
import type { Position, Order } from '@/api/modules/trading'
import { RefreshCw } from 'lucide-vue-next'

const route = useRoute()
const portfolioId = route.params.id as string

// 状态
const loading = ref(false)
const account = ref<any>(null)
const positions = ref<Position[]>([])
const orders = ref<Order[]>([])

// 格式化
const fmt = (v: number | string | null, d = 2) => {
  if (v === null || v === undefined) return '-'
  const n = typeof v === 'string' ? parseFloat(v) : v
  if (isNaN(n)) return '-'
  return n.toFixed(d)
}

const pct = (v: number | null) => {
  if (v === null || v === undefined) return '-'
  const n = typeof v === 'string' ? parseFloat(v) : v
  if (isNaN(n)) return '-'
  return (n >= 0 ? '+' : '') + n.toFixed(2) + '%'
}

const pnlClass = (v: number | null) => {
  if (v === null || v === undefined) return ''
  const n = typeof v === 'string' ? parseFloat(v) : v
  if (n > 0) return 'pnl-pos'
  if (n < 0) return 'pnl-neg'
  return ''
}

// 加载数据
const loadData = async () => {
  loading.value = true
  try {
    const [accRes, posRes, ordRes] = await Promise.all([
      getPaperAccount(portfolioId).catch(() => null),
      getPaperPositions(portfolioId).catch(() => null),
      getPaperOrders(portfolioId).catch(() => null),
    ])
    const accData = (accRes as any)?.data
    account.value = accData || null
    positions.value = accData?.positions || (posRes as any)?.data || []
    orders.value = accData?.active_orders || (ordRes as any)?.data || []
  } catch (e) {
    console.error('加载模拟盘数据失败:', e)
  } finally {
    loading.value = false
  }
}

onMounted(() => { loadData() })
</script>

<template>
  <div class="paper-tab">
    <!-- 加载状态 -->
    <div v-if="loading" class="loading-state">
      <RefreshCw class="w-5 h-5 animate-spin text-muted-foreground" />
      <span>加载中...</span>
    </div>

    <template v-else>
      <!-- 账户概览 -->
      <div class="stats-row">
        <div class="stat-card">
          <div class="stat-label">总资产</div>
          <div class="stat-value">{{ fmt(account?.total_asset) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">可用现金</div>
          <div class="stat-value">{{ fmt(account?.available_cash) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">持仓市值</div>
          <div class="stat-value">{{ fmt(account?.position_value) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">当日盈亏</div>
          <div class="stat-value" :class="pnlClass(account?.today_pnl)">{{ fmt(account?.today_pnl) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">总盈亏</div>
          <div class="stat-value" :class="pnlClass(account?.total_pnl)">{{ fmt(account?.total_pnl) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">初始资金</div>
          <div class="stat-value">{{ fmt(account?.initial_capital) }}</div>
        </div>
      </div>

      <!-- 持仓 -->
      <div class="section">
        <div class="section-header">
          <h3>持仓</h3>
          <button class="btn-ghost" @click="loadData"><RefreshCw class="w-3.5 h-3.5" /></button>
        </div>
        <div v-if="positions.length === 0" class="empty-hint">暂无持仓</div>
        <table v-else class="data-table">
          <thead>
            <tr>
              <th>代码</th><th>名称</th><th>数量</th><th>成本价</th>
              <th>现价</th><th>市值</th><th>盈亏</th><th>盈亏%</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in positions" :key="p.code">
              <td class="font-mono">{{ p.code }}</td>
              <td>{{ p.name }}</td>
              <td>{{ p.shares }}</td>
              <td>{{ fmt(p.cost) }}</td>
              <td>{{ fmt(p.current) }}</td>
              <td>{{ fmt(p.market_value) }}</td>
              <td :class="pnlClass(p.pnl)">{{ fmt(p.pnl) }}</td>
              <td :class="pnlClass(p.pnl_ratio)">{{ pct(p.pnl_ratio) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 订单 -->
      <div class="section">
        <div class="section-header">
          <h3>订单</h3>
        </div>
        <div v-if="orders.length === 0" class="empty-hint">暂无订单</div>
        <table v-else class="data-table">
          <thead>
            <tr>
              <th>时间</th><th>代码</th><th>方向</th><th>价格</th>
              <th>数量</th><th>已成交</th><th>均价</th><th>状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="o in orders" :key="o.order_id">
              <td class="text-xs text-muted-foreground">{{ o.time?.slice(5, 19) || '-' }}</td>
              <td class="font-mono">{{ o.code }}</td>
              <td>
                <span class="badge" :class="o.side === 'buy' ? 'badge-buy' : 'badge-sell'">
                  {{ o.side === 'buy' ? '买入' : '卖出' }}
                </span>
              </td>
              <td>{{ fmt(o.price) }}</td>
              <td>{{ o.volume }}</td>
              <td>{{ o.filled }}</td>
              <td>{{ fmt(o.avg_price) }}</td>
              <td>
                <span class="badge badge-status" :class="'status-' + o.status">{{ o.status }}</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </div>
</template>

<style scoped>
.paper-tab { display: flex; flex-direction: column; gap: 20px; }

.loading-state { display: flex; align-items: center; gap: 8px; padding: 32px 0; color: rgba(255,255,255,0.5); }

.stats-row { display: flex; gap: 12px; }
.stat-card {
  flex: 1; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08);
  border-radius: 8px; padding: 14px 16px;
}
.stat-label { font-size: 12px; color: rgba(255,255,255,0.45); margin-bottom: 4px; }
.stat-value { font-size: 18px; font-weight: 700; color: #fff; }

.pnl-pos { color: #10b981; }
.pnl-neg { color: #ef4444; }

.section { background: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.06); border-radius: 8px; padding: 16px; }
.section-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.section-header h3 { margin: 0; font-size: 15px; font-weight: 600; color: rgba(255,255,255,0.85); }

.empty-hint { color: rgba(255,255,255,0.35); font-size: 13px; padding: 24px 0; text-align: center; }

.data-table { width: 100%; border-collapse: collapse; }
.data-table th, .data-table td { padding: 8px 12px; text-align: left; border-bottom: 1px solid rgba(255,255,255,0.06); font-size: 13px; }
.data-table th { color: rgba(255,255,255,0.5); font-weight: 500; font-size: 12px; }
.data-table td { color: rgba(255,255,255,0.85); }
.data-table tbody tr:hover { background: rgba(255,255,255,0.03); }

.font-mono { font-family: monospace; font-size: 12px; }
.text-xs { font-size: 12px; }
.text-muted-foreground { color: rgba(255,255,255,0.4); }

.badge {
  display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;
}
.badge-buy { background: rgba(16,185,129,0.15); color: #10b981; }
.badge-sell { background: rgba(239,68,68,0.15); color: #ef4444; }
.badge-status { background: rgba(255,255,255,0.08); color: rgba(255,255,255,0.6); }
.status-filled { background: rgba(16,185,129,0.12); color: #10b981; }
.status-cancelled { background: rgba(255,255,255,0.06); color: rgba(255,255,255,0.4); }
.status-pending { background: rgba(59,130,246,0.12); color: #3b82f6; }
.status-rejected { background: rgba(239,68,68,0.12); color: #ef4444; }

.btn-ghost {
  background: none; border: none; color: rgba(255,255,255,0.4); cursor: pointer; padding: 4px;
  display: flex; align-items: center;
}
.btn-ghost:hover { color: rgba(255,255,255,0.7); }
</style>
