<template>
  <div class="date-range-picker">
    <div class="card">
      <div class="card-header">
        <h4>选择日期范围</h4>
      </div>
      <div class="card-body">
        <!-- 快捷选择 -->
        <div class="quick-select">
          <div class="btn-group">
            <button class="btn-small" @click="setRange('recent1M')">最近1月</button>
            <button class="btn-small" @click="setRange('recent3M')">最近3月</button>
            <button class="btn-small" @click="setRange('ytd')">今年</button>
            <button class="btn-small" @click="setRange('lastYear')">去年</button>
            <button class="btn-small" @click="setRange('all')">全部</button>
          </div>
        </div>

        <div class="divider"></div>

        <div class="form-row">
          <div class="form-group">
            <label class="form-label">开始日期</label>
            <input v-model="startDate" type="date" class="form-input" />
          </div>
          <div class="form-group">
            <label class="form-label">结束日期</label>
            <input v-model="endDate" type="date" class="form-input" />
          </div>
        </div>

        <div class="form-actions">
          <button class="btn-primary" :disabled="!canConfirm" @click="handleConfirm">确定</button>
          <button class="btn-secondary" @click="handleCancel">取消</button>
        </div>

        <div v-if="startDate && endDate" class="range-stats">
          <div class="stat-item">
            <span class="stat-label">天数</span>
            <span class="stat-value">{{ daysCount }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">周数</span>
            <span class="stat-value">{{ weeksCount }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import dayjs from 'dayjs'

/**
 * 日期范围选择器组件
 * 提供快捷选择和自定义范围功能
 */

interface Props {
  modelValue?: [string, string]
  maxRange?: number // 最大天数范围
}

const props = withDefaults(defineProps<Props>(), {
  maxRange: 365
})

const emit = defineEmits<{
  'update:modelValue': [start: string, end: string]
}>()

const startDate = ref<string>()
const endDate = ref<string>()

// 计算天数
const daysCount = computed(() => {
  if (startDate.value && endDate.value) {
    return dayjs(endDate.value).diff(dayjs(startDate.value), 'day') + 1
  }
  return 0
})

// 计算周数
const weeksCount = computed(() => {
  if (startDate.value && endDate.value) {
    return Math.floor(daysCount.value / 7)
  }
  return 0
})

// 是否可以确认
const canConfirm = computed(() => {
  if (!startDate.value || !endDate.value) return false
  return dayjs(endDate.value).isAfter(dayjs(startDate.value)) || daysCount.value <= props.maxRange
})

// 快捷选择
const setRange = (type: string) => {
  const now = dayjs()

  switch (type) {
    case 'recent1M':
      startDate.value = now.subtract(1, 'month').format('YYYY-MM-DD')
      endDate.value = now.format('YYYY-MM-DD')
      break
    case 'recent3M':
      startDate.value = now.subtract(3, 'month').format('YYYY-MM-DD')
      endDate.value = now.format('YYYY-MM-DD')
      break
    case 'ytd':
      startDate.value = now.startOf('year').format('YYYY-MM-DD')
      endDate.value = now.format('YYYY-MM-DD')
      break
    case 'lastYear':
      startDate.value = now.subtract(1, 'year').format('YYYY-MM-DD')
      endDate.value = now.format('YYYY-MM-DD')
      break
    case 'all':
      startDate.value = undefined
      endDate.value = undefined
      break
  }

  emit('update:modelValue', startDate.value!, endDate.value!)
}

// 确认
const handleConfirm = () => {
  emit('update:modelValue', startDate.value!, endDate.value!)
}

// 取消
const handleCancel = () => {
  startDate.value = undefined
  endDate.value = undefined
}
</script>

<style scoped>
.date-range-picker {
  width: 400px;
}

.card {
  background: #1a1a2e;
  border-radius: 8px;
  border: 1px solid #2a2a3e;
}

.card-header {
  padding: 16px 20px;
  border-bottom: 1px solid #2a2a3e;
}

.card-header h4 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #ffffff;
}

.card-body {
  padding: 20px;
}

.btn-group {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.btn-small {
  padding: 6px 12px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-small:hover {
  background: #3a3a4e;
  border-color: #1890ff;
}

.divider {
  height: 1px;
  background: #2a2a3e;
  margin: 16px 0;
}

.form-row {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
}

.form-group {
  flex: 1;
}

.form-label {
  display: block;
  font-size: 13px;
  color: #8a8a9a;
  margin-bottom: 6px;
}

.form-input {
  width: 100%;
  padding: 8px 12px;
  background: #2a2a3e;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  box-sizing: border-box;
}

.form-input:focus {
  outline: none;
  border-color: #1890ff;
}

.form-actions {
  display: flex;
  gap: 12px;
}

.btn-primary {
  padding: 8px 16px;
  background: #1890ff;
  border: none;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-primary:hover:not(:disabled) {
  background: #40a9ff;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-secondary {
  padding: 8px 16px;
  background: transparent;
  border: 1px solid #3a3a4e;
  border-radius: 4px;
  color: #ffffff;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-secondary:hover {
  border-color: #1890ff;
  color: #1890ff;
}

.range-stats {
  display: flex;
  gap: 24px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid #2a2a3e;
}

.stat-item {
  text-align: center;
}

.stat-label {
  display: block;
  font-size: 12px;
  color: #8a8a9a;
  margin-bottom: 4px;
}

.stat-value {
  display: block;
  font-size: 20px;
  font-weight: 600;
  color: #ffffff;
}
</style>
