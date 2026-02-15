<template>
  <div class="date-range-picker">
    <a-card title="选择日期范围" size="small">
      <!-- Custom -->
      <div class="quick-select">
        <a-space>
          <a-button size="small" @click="setRange('recent1M')">最近1月</a-button>
          <a-button size="small" @click="setRange('recent3M')">最近3月</a-button>
          <a-button size="small" @click="setRange('ytd')">今年</a-button>
          <a-button size="small" @click="setRange('lastYear')">去年</a-button>
          <a-button size="small" @click="setRange('all')">全部</a-button>
        </a-space>
      </div>

      <!-- Custom -->
      <a-divider />

      <a-form layout="inline">
        <a-form-item label="开始日期">
          <a-date-picker
            v-model:value="startDate"
            placeholder="选择开始日期"
            format="YYYY-MM-DD"
          />
        </a-form-item>
        <a-form-item label="结束日期">
          <a-date-picker
            v-model:value="endDate"
            placeholder="选择结束日期"
            format="YYYY-MM-DD"
          />
        </a-form-item>
        <a-form-item>
          <a-button type="primary" @click="handleConfirm" :disabled="!canConfirm">
            确定
          </a-button>
          <a-button @click="handleCancel">
            取消
          </a-button>
        </a-form-item>
      </a-form>

      <!-- Custom -->
      <div v-if="startDate && endDate" class="range-stats">
        <a-statistic title="天数" :value="daysCount" />
        <a-statistic title="周数" :value="weeksCount" />
      </div>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import dayjs from 'dayjs'

/**
 * 日期范围选择器组件
 * 提供快捷选择和腊定义范围功能
 */

interface Props {
  modelValue?: [string, string]
  maxRange?: number // 最大天数范围
}

const props = withDefaults(defineProps<Props>(), {
  maxRange: 365
})

const emit = defineEmits<{
  'update:modelValue': [string, string]
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

  emit('update:modelValue', [startDate.value, endDate.value])
}

// 确认
const handleConfirm = () => {
  emit('update:modelValue', [startDate.value, endDate.value])
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

.quick-select {
  margin-bottom: 12px;
}

.range-stats {
  margin-top: 16px;
  display: flex;
  gap: 16px;
}
</style>
