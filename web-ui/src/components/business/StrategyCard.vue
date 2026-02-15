<template>
  <div class="strategy-card">
    <div class="card-header">
      <span class="card-title">{{ strategy.name }}</span>
      <a-tag :color="getCategoryColor(strategy.category)">{{ strategy.category }}</a-tag>
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
        <a-button type="primary" size="small" @click="handleSelect(strategy)">使用策略</a-button>
        <a-button size="small">查看详情</a-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { defineProps, defineEmits } from 'vue'

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
  select: []
}>()

const getCategoryColor = (category: string) => {
  const colors = {
    trend: 'blue',
    reversal: 'orange',
    mean_revert: 'green',
    arbitrage: 'purple'
  }
  return colors[category] || 'default'
}

const handleSelect = () => {
  emit('select', props.strategy)
}
</script>

<style scoped>
.strategy-card {
  border: 1px solid #e8e8e8;
  border-radius: 8px;
  padding: 16px;
  cursor: pointer;
  transition: all 0.3s;
}

.strategy-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-4px);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.card-title {
  font-size: 16px;
  font-weight: 600;
  color: #1a1a1a;
}

.card-meta {
  display: flex;
  gap: 12px;
  flex-direction: column;
  align-items: flex-start;
}

.card-description {
  font-size: 13px;
  color: #8c8c8c;
}

.card-stats {
  display: flex;
  gap: 16px;
}

.card-stats span {
  font-size: 12px;
  color: #8c8c8c;
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
  background: #f5f5f5;
  border-radius: 4px;
}

.param-name {
  font-size: 12px;
  color: #8c8c8c;
}

.param-value {
  font-size: 12px;
  color: #1a1a1a;
  font-weight: 500;
}

.card-actions {
  display: flex;
  gap: 8px;
  margin-top: 16px;
}
</style>
