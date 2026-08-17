<template>
  <div
    ref="fieldRef"
    class="date-field"
    :class="{ open, bordered }"
    tabindex="0"
    @click="toggle"
    @keydown.escape="open = false"
  >
    <span :class="{ placeholder: !modelValue }">{{ modelValue || placeholder }}</span>
    <span
      v-if="clearable && modelValue"
      class="clear-btn"
      @click.stop="$emit('update:modelValue', '')"
    >×</span>
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
      <!-- 月视图:« » 快捷翻年,‹ › 翻月;标题可点进年视图 -->
      <template v-if="view === 'month'">
        <div class="picker-header">
          <button
            type="button"
            class="picker-nav"
            title="上一年"
            @click="year--"
          >
            «
          </button>
          <button
            type="button"
            class="picker-nav"
            @click="month--"
          >
            ‹
          </button>
          <button
            type="button"
            class="picker-title"
            title="选择年份"
            @click="view = 'year'"
          >
            {{ year }}年{{ month + 1 }}月
          </button>
          <button
            type="button"
            class="picker-nav"
            @click="month++"
          >
            ›
          </button>
          <button
            type="button"
            class="picker-nav"
            title="下一年"
            @click="year++"
          >
            »
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
      </template>
      <!-- 年视图:12 年一页,快切远距年份;点年回月视图 -->
      <template v-else>
        <div class="picker-header">
          <button
            type="button"
            class="picker-nav"
            @click="yearPage -= 12"
          >
            ‹
          </button>
          <button class="picker-title">
            {{ yearPage }} ~ {{ yearPage + 11 }}
          </button>
          <button
            type="button"
            class="picker-nav"
            @click="yearPage += 12"
          >
            ›
          </button>
        </div>
        <div class="picker-years">
          <button
            v-for="y in 12"
            :key="y"
            type="button"
            class="picker-year"
            :class="{ selected: yearPage + y - 1 === year }"
            @click="year = yearPage + y - 1; view = 'month'"
          >
            {{ yearPage + y - 1 }}
          </button>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 单日期字段 + 内联日历面板(YYYY-MM-DD),全站统一日期选择组件
 *
 * 从 BacktestTab 创建弹窗手写双日历抽出(两个 350 行的重复 picker 合一),
 * 后收敛全部原生 <input type="date">。
 * - 年快切:« » 直接翻年;点标题进年视图(12 年/页),跨远距年份两次点击可达
 * - 弹层外点击/Escape 关闭;选日 emit update:modelValue 后自动收起
 * - clearable:字段尾部出 × 清空(emit '')
 * - bordered:输入框外观变体(边框/内边距),筛选栏与表单场景用
 */
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'

const props = withDefaults(defineProps<{
  modelValue: string
  placeholder?: string
  /** 初始定位月份(YYYY-MM-DD);缺省=当前月 */
  initial?: string
  /** 输入框外观(边框/内边距);缺省=裸字段(modal 表单风) */
  bordered?: boolean
  /** 可清空:字段尾部 × 一键清空 */
  clearable?: boolean
}>(), {
  placeholder: '选择日期',
  initial: '',
  bordered: false,
  clearable: false,
})

defineEmits<{ 'update:modelValue': [value: string] }>()

const open = ref(false)
const view = ref<'month' | 'year'>('month')
const toggle = () => {
  open.value = !open.value
  if (open.value) view.value = 'month'
}

const now = props.initial ? new Date(props.initial) : new Date()
const year = ref(isNaN(now.getTime()) ? new Date().getFullYear() : now.getFullYear())
const month = ref(isNaN(now.getTime()) ? new Date().getMonth() : now.getMonth())
// 年视图基准年(所在 12 年页的首年)
const yearPage = ref(year.value - (year.value % 12))

// 月份溢出进位(12月→次年1月)
watch(month, (v) => {
  if (v < 0) { month.value = 11; year.value-- }
  if (v > 11) { month.value = 0; year.value++ }
})
// 翻年时年视图跟随翻页
watch(year, (v) => { yearPage.value = v - (v % 12) })

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

// 弹层外点击关闭(面板/字段自身除外);字段可聚焦以接 Escape
const fieldRef = ref<HTMLElement>()
const onDocMouseDown = (e: MouseEvent) => {
  if (open.value && fieldRef.value && !fieldRef.value.contains(e.target as Node)) open.value = false
}
onMounted(() => document.addEventListener('mousedown', onDocMouseDown))
onUnmounted(() => document.removeEventListener('mousedown', onDocMouseDown))
</script>

<style scoped>
/* 样式自 BacktestTab 原样迁入(视觉零变化),bordered 变体后补 */
.date-field {
  position: relative;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  color: hsl(var(--foreground));
  outline: none;
}

.date-field .placeholder { color: hsl(var(--muted-foreground)); }
.date-field svg { color: hsl(var(--muted-foreground)); flex-shrink: 0; }

/* 输入框外观变体:对齐 form-input(边框/内边距),替换原生 date input 时用 */
.date-field.bordered {
  padding: 7px 10px;
  background: hsl(var(--card));
  border: 1px solid hsl(var(--border));
  border-radius: var(--radius-sm);
  font-size: 13px;
}
.date-field.bordered:focus-within { border-color: hsl(var(--primary)); }

.clear-btn {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  font-size: 12px;
  line-height: 1;
  color: hsl(var(--muted-foreground));
}
.clear-btn:hover { background: hsl(var(--border)); color: hsl(var(--foreground)); }

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
  gap: 2px;
  margin-bottom: 8px;
}

.picker-title {
  flex: 1;
  text-align: center;
  font-size: 13px;
  font-weight: 600;
  color: hsl(var(--foreground));
  background: none;
  border: none;
  border-radius: var(--radius-sm);
  padding: 2px 0;
  cursor: pointer;
}
.picker-title:hover { background: hsl(var(--border)); }

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

/* 年视图:12 年网格(3×4),与月视图同宽 */
.picker-years {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 2px;
}

.picker-year {
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  font-size: 13px;
  color: hsl(var(--foreground));
  background: transparent;
  border: none;
  cursor: pointer;
}

.picker-year:hover { background: hsl(var(--border)); }
.picker-year.selected { background: hsl(var(--primary)); color: hsl(var(--primary-foreground)); }
</style>
