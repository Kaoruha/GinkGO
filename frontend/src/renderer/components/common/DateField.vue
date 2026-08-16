<template>
  <div
    class="date-field"
    :class="{ open }"
    @click="toggle"
  >
    <span :class="{ placeholder: !modelValue }">{{ modelValue || placeholder }}</span>
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      stroke-width="2"
    ><rect
      x="3"
      y="4"
      width="18"
      height="18"
      rx="2"
    /><line
      x1="16"
      y1="2"
      x2="16"
      y2="6"
    /><line
      x1="8"
      y1="2"
      x2="8"
      y2="6"
    /><line
      x1="3"
      y1="10"
      x2="21"
      y2="10"
    /></svg>
    <div
      v-if="open"
      class="picker-panel"
      @click.stop
    >
      <div class="picker-header">
        <button
          type="button"
          class="picker-nav"
          @click="month--"
        >
          ‹
        </button>
        <span class="picker-title">{{ year }}年{{ month + 1 }}月</span>
        <button
          type="button"
          class="picker-nav"
          @click="month++"
        >
          ›
        </button>
      </div>
      <div class="picker-weekdays">
        <span
          v-for="d in ['一','二','三','四','五','六','日']"
          :key="d"
          class="picker-wd"
        >{{ d }}</span>
      </div>
      <div class="picker-days">
        <button
          v-for="(day, i) in days"
          :key="i"
          type="button"
          class="picker-day"
          :class="{
            empty: !day,
            selected: day && modelValue === formatDay(day),
            today: day && isToday(day),
          }"
          :disabled="!day"
          @click="if (day) { $emit('update:modelValue', formatDay(day)); open = false }"
        >
          {{ day || '' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 单日期字段 + 内联月历面板(YYYY-MM-DD)
 *
 * 从 BacktestTab 创建弹窗手写双日历抽出(两个 350 行的重复 picker 合一)。
 * 点击字段开/关;选日 emit update:modelValue 后自动收起。
 * 不含弹层外点击关闭(父级 modal 自身有点击语义,避免冲突)。
 */
import { ref, computed, watch } from 'vue'

const props = withDefaults(defineProps<{
  modelValue: string
  placeholder?: string
  /** 初始定位月份(YYYY-MM-DD);缺省=当前月 */
  initial?: string
}>(), {
  placeholder: '选择日期',
  initial: '',
})

defineEmits<{ 'update:modelValue': [value: string] }>()

const open = ref(false)
const toggle = () => { open.value = !open.value }

const now = props.initial ? new Date(props.initial) : new Date()
const year = ref(isNaN(now.getTime()) ? new Date().getFullYear() : now.getFullYear())
const month = ref(isNaN(now.getTime()) ? new Date().getMonth() : now.getMonth())

// 月份溢出进位(12月→次年1月)
watch(month, (v) => {
  if (v < 0) { month.value = 11; year.value-- }
  if (v > 11) { month.value = 0; year.value++ }
})

function getDaysInMonth(y: number, m: number): (number | null)[] {
  const firstDay = new Date(y, m, 1).getDay()
  const offset = firstDay === 0 ? 6 : firstDay - 1 // Monday=0
  const daysInMonth = new Date(y, m + 1, 0).getDate()
  const cells: (number | null)[] = []
  for (let i = 0; i < offset; i++) cells.push(null)
  for (let d = 1; d <= daysInMonth; d++) cells.push(d)
  while (cells.length < 42) cells.push(null)
  return cells
}

const days = computed(() => getDaysInMonth(year.value, month.value))

const formatDay = (day: number) => {
  const m = String(month.value + 1).padStart(2, '0')
  const d = String(day).padStart(2, '0')
  return `${year.value}-${m}-${d}`
}

const isToday = (day: number) => {
  const t = new Date()
  return day === t.getDate() && month.value === t.getMonth() && year.value === t.getFullYear()
}
</script>

<style scoped>
/* 样式自 BacktestTab 原样迁入(视觉零变化) */
.date-field {
  position: relative;
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  color: hsl(var(--foreground));
}

.date-field .placeholder { color: hsl(var(--muted-foreground)); }
.date-field svg { color: hsl(var(--muted-foreground)); flex-shrink: 0; }

.picker-panel {
  position: absolute;
  top: 100%;
  left: 0;
  margin-top: 4px;
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius-lg);
  padding: 10px;
  z-index: 1100;
  box-shadow: var(--shadow-lg);
  width: 252px;
}

.picker-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.picker-title {
  font-size: 13px;
  font-weight: 600;
  color: hsl(var(--foreground));
}

.picker-nav {
  background: none;
  border: none;
  color: hsl(var(--muted-foreground));
  font-size: 16px;
  cursor: pointer;
  padding: 2px 6px;
  border-radius: var(--radius-sm);
}

.picker-nav:hover { color: hsl(var(--foreground)); background: hsl(var(--border)); }

.picker-weekdays {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 2px;
  margin-bottom: 4px;
}

.picker-wd {
  text-align: center;
  font-size: 11px;
  color: hsl(var(--muted-foreground));
  font-weight: 500;
  height: 24px;
  line-height: 24px;
}

.picker-days {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 2px;
}

.picker-day {
  width: 32px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  font-size: 12px;
  color: hsl(var(--muted-foreground));
  background: transparent;
  border: none;
  cursor: pointer;
  margin: 1px auto;
}

.picker-day:hover:not(:disabled) { background: hsl(var(--border)); color: hsl(var(--foreground)); }
.picker-day:disabled { visibility: hidden; }
.picker-day.selected { background: hsl(var(--primary)); color: hsl(var(--primary-foreground)); }
.picker-day.today { font-weight: 700; color: hsl(var(--primary)); }
.picker-day.today.selected { color: hsl(var(--primary-foreground)); }
</style>
