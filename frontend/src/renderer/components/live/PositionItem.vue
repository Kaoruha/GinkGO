<template>
  <div :class="['position-item', position.is_spot ? 'spot-position' : 'contract-position']">
    <div class="position-header">
      <div class="position-title">
        <span class="position-symbol">{{ position.symbol }}</span>
        <!-- 现货持仓特殊标识 -->
        <Badge
          v-if="position.is_spot"
          variant="secondary"
          class="spot-badge"
        >
          💰 现货
        </Badge>
        <Badge :variant="position.side === 'long' ? 'success' : 'destructive'">
          {{ position.side === 'long' ? '做多' : '做空' }}
        </Badge>
      </div>
    </div>
    <div class="position-details">
      <!-- 统一的持仓信息显示 -->
      <div class="position-stat">
        <span class="stat-label">数量</span>
        <span class="stat-value">{{ formatFixed(position.size) }}</span>
      </div>
      <div class="position-stat">
        <span class="stat-label">成本价</span>
        <span class="stat-value">${{ formatFixed(position.avg_price) }}</span>
      </div>
      <div class="position-stat">
        <span class="stat-label">现价</span>
        <span class="stat-value">${{ formatFixed(position.current_price) }}</span>
      </div>
      <div class="position-stat pnl">
        <span class="stat-label">盈亏</span>
        <span :class="['stat-value', pnlColor]">
          <TrendingUp
            v-if="parseFloat(position.unrealized_pnl) > 0"
            class="w-3 h-3 inline mr-1"
          />
          <TrendingDown
            v-else-if="parseFloat(position.unrealized_pnl) < 0"
            class="w-3 h-3 inline mr-1"
          />
          {{ formatFixed(position.unrealized_pnl) }}
          <span class="pnl-percent">({{ formatFixed(position.unrealized_pnl_percentage, 3) }}%)</span>
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 单条持仓展示行(数量/成本/现价/盈亏),自 AccountInfo 账户卡拆出。
 * 纯展示:数据刷新/合并由父级(AccountCard)负责。
 */
import { computed } from 'vue'
import { Badge } from '@/components/ui/badge'
import { TrendingUp, TrendingDown } from 'lucide-vue-next'
import { formatFixed } from '@/utils/format'
import type { PositionInfo } from '@/types/live'

const props = defineProps<{
  position: PositionInfo
}>()

// 未实现盈亏颜色(涨绿跌红)
const pnlColor = computed(() => {
  const n = parseFloat(props.position.unrealized_pnl)
  if (isNaN(n)) return 'text-muted-foreground'
  if (n > 0) return 'text-success'
  if (n < 0) return 'text-error'
  return 'text-muted-foreground'
})
</script>

<style scoped>
.position-item {
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius-lg);
  padding: 16px;
  transition: all 0.2s ease;
}

.position-item:hover {
  border-color: hsl(var(--border));
  background: hsl(var(--card));
}

.position-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.position-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.position-symbol {
  font-size: 16px;
  font-weight: 600;
  color: hsl(var(--foreground));
}

.position-details {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.position-stat {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.position-stat .stat-label {
  font-size: 12px;
  color: hsl(var(--muted-foreground));
}

.position-stat .stat-value {
  font-size: 14px;
  font-weight: 500;
  color: hsl(var(--foreground));
}

.position-stat.pnl .stat-value {
  display: flex;
  align-items: center;
  gap: 4px;
}

.pnl-percent {
  font-size: 12px;
  margin-left: 4px;
  opacity: 0.8;
}

@media (max-width: 768px) {
  .position-details {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
