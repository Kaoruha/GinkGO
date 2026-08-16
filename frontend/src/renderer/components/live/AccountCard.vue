<template>
  <div
    class="account-card"
    @contextmenu="emit('contextmenu', $event, account)"
  >
    <!-- 卡片头部 -->
    <div class="card-header">
      <div class="account-info">
        <div class="account-name">
          <span class="exchange-icon">{{ exchangeIcon }}</span>
          <h3>{{ account.name }}</h3>
        </div>
        <div class="account-meta">
          <Badge
            :variant="account.environment === 'production' ? 'destructive' : 'secondary'"
            class="env-badge"
          >
            {{ account.environment }}
          </Badge>
          <Badge
            :variant="account.status === 'enabled' ? 'success' : 'secondary'"
            class="status-badge"
          >
            {{ account.status === 'enabled' ? '运行中' : '已停用' }}
          </Badge>
        </div>
      </div>
    </div>

    <!-- 错误提示 -->
    <div
      v-if="account.error"
      class="error-banner"
    >
      <AlertCircle class="w-4 h-4" />
      <span>{{ account.error }}</span>
    </div>

    <!-- 余额信息 -->
    <div class="balance-section">
      <!-- 骨架屏：余额加载中 -->
      <div
        v-if="loading?.balance && !account.balance"
        class="skeleton-grid"
      >
        <div
          v-for="i in 3"
          :key="i"
          class="skeleton-item"
        >
          <div class="skeleton-line skeleton-label" />
          <div class="skeleton-line skeleton-value" />
        </div>
      </div>

      <!-- 实际余额数据 -->
      <div v-else-if="account.balance">
        <div class="balance-grid">
          <div class="balance-item">
            <div class="balance-label">
              总权益
            </div>
            <div class="balance-value primary">
              ${{ formatFixed(account.balance.total_equity) }}
            </div>
          </div>
          <div class="balance-item">
            <div class="balance-label">
              可用余额
            </div>
            <div class="balance-value success">
              ${{ formatFixed(account.balance.available_balance) }}
            </div>
          </div>
          <div class="balance-item">
            <div class="balance-label">
              冻结余额
            </div>
            <div class="balance-value warning">
              ${{ formatFixed(account.balance.frozen_balance) }}
            </div>
          </div>
        </div>

        <!-- 币种余额 -->
        <div
          v-if="account.balance.currency_balances?.length > 0"
          class="currency-balances"
        >
          <div
            v-for="cb in activeCurrencyBalances"
            :key="cb.currency"
            class="currency-item"
          >
            <span class="currency-name">{{ cb.currency }}</span>
            <span class="currency-amount">
              <span class="available">{{ formatFixed(cb.available) }}</span>
              <span
                v-if="parseFloat(cb.frozen) > 0"
                class="frozen"
              >
                (冻结: {{ formatFixed(cb.frozen) }})
              </span>
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- 持仓信息（包含现货余额） -->
    <div class="positions-section">
      <!-- 骨架屏：持仓加载中 -->
      <div
        v-if="loading?.positions && !account.positions"
        class="skeleton-positions"
      >
        <div
          v-for="i in 2"
          :key="i"
          class="skeleton-position"
        >
          <div class="skeleton-line skeleton-position-title" />
          <div class="skeleton-position-details">
            <div
              v-for="j in 4"
              :key="j"
              class="skeleton-line"
            />
          </div>
        </div>
      </div>

      <!-- 实际持仓数据 -->
      <template v-else-if="account.positions && account.positions.length > 0">
        <div class="section-title">
          <Activity class="w-4 h-4 mr-2" />
          持仓信息 ({{ account.positions.length }})
        </div>
        <div class="positions-list">
          <PositionItem
            v-for="position in account.positions"
            :key="position.symbol"
            :position="position"
          />
        </div>
      </template>

      <!-- 无持仓 -->
      <div
        v-else-if="!loading?.positions"
        class="no-positions"
      >
        <Activity class="w-4 h-4 mr-2" />
        <span class="text-muted-foreground">暂无持仓</span>
      </div>
    </div>

    <!-- 卡片底部 -->
    <div class="card-footer">
      <Clock class="w-3 h-3 mr-1" />
      <span class="update-time">
        最后更新: {{ formatDate(account.last_update) }}
      </span>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 单个实盘账户卡(头部徽标/余额/币种/持仓/骨架屏/错误横幅),
 * 自 AccountInfo(1055 行巨页)拆出。数据加载与轮询留在父页,
 * 本组件只按 props 渲染。
 */
import { computed } from 'vue'
import { Badge } from '@/components/ui/badge'
import { AlertCircle, Activity, Clock } from 'lucide-vue-next'
import PositionItem from '@/components/live/PositionItem.vue'
import { formatFixed, formatDate } from '@/utils/format'
import type { AccountData } from '@/types/live'

const props = defineProps<{
  account: AccountData
  /** 分区加载态(balance/positions 骨架屏开关);缺省视为已加载 */
  loading?: { balance: boolean; positions: boolean }
}>()

const emit = defineEmits<{
  (e: 'contextmenu', event: MouseEvent, account: AccountData): void
}>()

// 交易所图标
const exchangeIcon = computed(() => {
  const icons: Record<string, string> = {
    okx: '🔷',
    binance: '🟡',
    bybit: '⚡'
  }
  return icons[props.account.exchange.toLowerCase()] || '💱'
})

// 只展示有余额(可用或冻结>0)的币种
const activeCurrencyBalances = computed(() =>
  (props.account.balance?.currency_balances || [])
    .filter(c => parseFloat(c.available) > 0 || parseFloat(c.frozen) > 0)
)
</script>

<style scoped>
/* 样式自 AccountInfo 原样迁入(视觉零变化) */
.account-card {
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius-lg);
  overflow: hidden;
  transition: all 0.3s ease;
}

.account-card:hover {
  border-color: hsl(var(--border));
  box-shadow: var(--shadow-md);
}

.account-info {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.account-name {
  display: flex;
  align-items: center;
  gap: 12px;
}

.exchange-icon {
  font-size: 24px;
}

.account-name h3 {
  font-size: 18px;
  font-weight: 600;
  color: hsl(var(--foreground));
  margin: 0;
}

.account-meta {
  display: flex;
  gap: 8px;
}

.env-badge,
.status-badge {
  font-size: 12px;
}

/* 错误提示 */
.error-banner {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 20px;
  padding: 12px;
  background: rgba(255, 77, 79, 0.1);
  border-left: 3px solid hsl(var(--error));
  color: hsl(var(--error));
  font-size: 14px;
}

/* 余额部分 */
.balance-section {
  padding: 20px;
  border-bottom: 1px solid hsl(var(--border));
}

.balance-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}

.balance-item {
  background: hsl(var(--card));
  border-radius: var(--radius-lg);
  padding: 16px;
  border: 1px solid hsl(var(--border));
  transition: all 0.2s ease;
}

.balance-item:hover {
  border-color: hsl(var(--primary));
}

.balance-label {
  font-size: 12px;
  color: hsl(var(--muted-foreground));
  margin-bottom: 8px;
}

.balance-value {
  font-size: 20px;
  font-weight: 600;
  color: hsl(var(--foreground));
}

.balance-value.primary {
  color: hsl(var(--primary));
}

.balance-value.success {
  color: hsl(var(--success));
}

.balance-value.warning {
  color: hsl(var(--warning));
}

/* 币种余额 */
.currency-balances {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.currency-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: hsl(var(--card));
  border-radius: var(--radius-lg);
  font-size: 14px;
}

.currency-name {
  font-weight: 600;
  color: hsl(var(--foreground));
}

.currency-amount {
  color: hsl(var(--muted-foreground));
}

.currency-amount .available {
  color: hsl(var(--success));
}

.currency-amount .frozen {
  color: hsl(var(--warning));
  font-size: 12px;
}

/* 持仓部分 */
.positions-section {
  padding: 20px;
  border-bottom: 1px solid hsl(var(--border));
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: hsl(var(--muted-foreground));
  margin-bottom: 16px;
}

.positions-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.no-positions {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: hsl(var(--muted-foreground));
  font-size: 14px;
}

/* 卡片底部 */
.update-time {
  font-size: 12px;
  color: hsl(var(--muted-foreground));
}

/* 骨架屏加载样式 */
.skeleton-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}

.skeleton-item {
  background: hsl(var(--card));
  border-radius: var(--radius-lg);
  padding: 16px;
  border: 1px solid hsl(var(--border));
}

.skeleton-line {
  background: linear-gradient(90deg, hsl(var(--border)) 25%, hsl(var(--secondary)) 50%, hsl(var(--border)) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
  border-radius: var(--radius-sm);
}

.skeleton-label {
  height: 12px;
  width: 60px;
  margin-bottom: 12px;
}

.skeleton-value {
  height: 24px;
  width: 100px;
}

.skeleton-positions {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.skeleton-position {
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius-lg);
  padding: 16px;
}

.skeleton-position-title {
  height: 16px;
  width: 120px;
  margin-bottom: 12px;
}

.skeleton-position-details {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.skeleton-position-details .skeleton-line {
  height: 32px;
}

@keyframes shimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

@media (max-width: 768px) {
  .balance-grid {
    grid-template-columns: 1fr;
  }
}
</style>
