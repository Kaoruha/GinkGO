<template>
  <div class="strategy-card">
    <div class="card-header">
      <span class="card-title">{{ strategy.name }}</span>
      <span class="tag" :class="`tag-${getCategoryColorClass(strategy.category)}`">{{ getCategoryLabel(strategy.category) }}</span>
      <div class="card-meta">
        <span class="card-description">{{ strategy.description }}</span>
        <span class="card-stats">
          <span>年化收益: {{ strategy.annual_return }}%</span>
          <span>夏普: {{ strategy.sharpe }}</span>
        </span>
      </div>
    </div>

    <div class="card-body">
      <div class="param-list">
        <div class="param-item" v-for="param in strategy.params" :key="param.name">
          <span class="param-name">{{ param.label }}</span>
          <span class="param-value">{{ param.value }}</span>
        </div>
      </div>

      <div class="card-actions">
        <button class="btn-primary" @click="handleSelect()">使用策略</button>
        <button class="btn-secondary">查看详情</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">

/**
 * 策略卡片组件
 * 展示策略基本信息、参数、收益等
 */

interface StrategyParam {
  name: string
  label: string
  value: string | number
}

interface Strategy {
  uuid: string
  name: string
  category: 'trend' | 'reversal' | 'mean_revert' | 'arbitrage'
  description: string
  annual_return: number
  sharpe: number
  params: StrategyParam[]
}

interface Props {
  strategy: Strategy
}

const props = defineProps<Props>()

const emit = defineEmits<{
  select: [strategy: Strategy]
}>()

const CATEGORY_LABELS: Record<string, string> = {
  trend: '趋势',
  reversal: '反转',
  mean_revert: '均值回归',
  arbitrage: '套利'
}

const CATEGORY_COLORS: Record<string, string> = {
  trend: 'blue',
  reversal: 'orange',
  mean_revert: 'green',
  arbitrage: 'purple'
}

const getCategoryLabel = (category: string) => {
  return CATEGORY_LABELS[category] || category
}

const getCategoryColorClass = (category: string) => {
  return CATEGORY_COLORS[category] || 'gray'
}

const handleSelect = () => {
  emit('select', props.strategy)
}
</script>

<style scoped>
.strategy-card {
  background: #1a1a2e;
  border: 1px solid #2a2a3e;
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.3s;
}

.strategy-card:hover {
  box-shadow: 0 4px 12px rgba(24, 144, 255, 0.2);
  transform: translateY(-4px);
  border-color: #1890ff;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  flex-wrap: wrap;
  gap: 8px;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
}

.card-meta {
  display: flex;
  gap: 12px;
  flex: 1;
  min-width: 200px;
}

.card-description {
  font-size: 13px;
  color: #8a8a9a;
}

.card-stats {
  display: flex;
  gap: 16px;
}

.card-stats span {
  font-size: 12px;
  color: #8a8a9a;
}

.card-body {
  padding: 12px 0;
}

.param-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}

.param-item {
  display: flex;
  justify-content: space-between;
  padding: 8px;
  background: #2a2a3e;
  border-radius: 4px;
}

.param-name {
  font-size: 12px;
  color: #8a8a9a;
}

.param-value {
  font-size: 12px;
  color: #ffffff;
  font-weight: 500;
}

.card-actions {
  display: flex;
  gap: 8px;
  margin-top: 16px;
}

.btn-primary {
  padding: 6px 12px;
  background: #1890ff;
  border: none;
  border-radius: 4px;
  color: #ffffff;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-primary:hover {
  background: #40a9ff;
}

.btn-secondary {
  padding: 6px 12px;
  background: transparent;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-secondary:hover {
  border-color: #1890ff;
  color: #1890ff;
}

/* Tag */
.tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 500;
}

.tag-blue { background: rgba(24, 144, 255, 0.2); color: #1890ff; }
.tag-green { background: rgba(82, 196, 26, 0.2); color: #52c41a; }
.tag-orange { background: rgba(250, 173, 20, 0.2); color: #faad14; }
.tag-purple { background: rgba(114, 46, 209, 0.2); color: #722ed1; }
.tag-gray { background: #2a2a3e; color: #8a8a9a; }
</style>
