<template>
  <a-card :class="['statistic-card', `card-${type}`]" :hoverable="hoverable" :bordered="bordered">
    <div class="stat-header">
      <div v-if="icon || $slots.icon" class="stat-icon-wrapper" :style="{ backgroundColor: iconColor }">
        <slot name="icon">
          <component :is="icon" class="stat-icon" />
        </slot>
      </div>
      <div class="stat-meta">
        <slot name="title">
          <span class="stat-title">{{ title }}</span>
        </slot>
        <slot name="extra">
          <span v-if="extra" class="stat-extra">{{ extra }}</span>
        </slot>
      </div>
    </div>

    <div class="stat-content">
      <div class="stat-value" :class="`value-${size}`">
        <slot name="prefix">
          <span v-if="prefix" class="value-prefix">{{ prefix }}</span>
        </slot>
        <span class="value-number">{{ formatValue(value) }}</span>
        <slot name="suffix">
          <span v-if="suffix" class="value-suffix">{{ suffix }}</span>
        </slot>
      </div>
      <div v-if="showTrend" class="stat-trend" :class="`trend-${trend}`">
        <slot name="trendIcon">
          <component v-if="trendIcon" :is="trendIcon" class="trend-icon" :spin="spin" />
        </slot>
        <span class="trend-value">{{ trendValue }}</span>
      </div>
    </div>
  </a-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'

type CardType = 'primary' | 'success' | 'warning' | 'danger' | 'info'
type TrendType = 'up' | 'down' | 'flat'
type SizeType = 'small' | 'medium' | 'large'

interface Props {
  title: string
  value: number | string
  type?: CardType
  prefix?: string
  suffix?: string
  trend?: TrendType
  trendValue?: string
  trendIcon?: any
  showTrend?: boolean
  size?: SizeType
  precision?: number
  hoverable?: boolean
  bordered?: boolean
  loading?: boolean
  icon?: any
  iconColor?: string
  extra?: string
  spin?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  type: 'info',
  size: 'medium',
  precision: 2,
  showTrend: false,
  hoverable: true,
  bordered: false,
  loading: false,
  iconColor: '#1890ff',
  spin: false
})

const formatValue = (val: number | string) => {
  if (typeof val === 'number') {
    return val.toLocaleString('zh-CN', {
      minimumFractionDigits: props.precision,
      maximumFractionDigits: props.precision
    })
  }
  return val
}
</script>

<style scoped>
.statistic-card {
  border-radius: 12px;
  transition: all 0.3s ease;
  height: 100%;
  border: none;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.statistic-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
}

.card-primary {
  border-left: 4px solid #1890ff;
}

.card-success {
  border-left: 4px solid #52c41a;
}

.card-warning {
  border-left: 4px solid #faad14;
}

.card-danger {
  border-left: 4px solid #f5222d;
}

.card-info {
  border-left: 4px solid #13c2c2;
}

.stat-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}

.stat-icon-wrapper {
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

.stat-icon {
  font-size: 20px;
}

.stat-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
}

.stat-title {
  font-size: 14px;
  color: #8c8c8c;
  font-weight: 500;
}

.stat-extra {
  font-size: 12px;
  color: #8c8c8c;
}

.stat-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.value-small .value-number {
  font-size: 24px;
}

.value-medium .value-number {
  font-size: 28px;
}

.value-large .value-number {
  font-size: 32px;
}

.value-number {
  font-weight: 600;
  color: #1a1a1a;
}

.value-prefix {
  margin-right: 4px;
  font-size: 14px;
  color: #8c8c8c;
}

.value-suffix {
  margin-left: 4px;
  font-size: 14px;
  color: #8c8c8c;
}

.stat-trend {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
}

.trend-up .trend-value {
  color: #52c41a;
}

.trend-down .trend-value {
  color: #f5222d;
}

.trend-flat .trend-value {
  color: #8c8c8c;
}

.trend-icon {
  font-size: 14px;
}
</style>
