<template>
  <div
    ref="rootEl"
    class="range-nav"
  >
    <!-- 全量收盘缩略图(SVG 自绘):像素↔索引↔时间全部自算,无图表库坐标轴黑盒 -->
    <svg
      class="rn-spark"
      :viewBox="`0 0 ${rnWidth} 52`"
      preserveAspectRatio="none"
    >
      <polyline :points="sparkPoints" />
    </svg>
    <!-- 手柄层:左右遮罩 + 可拖窗口(平移) + 双端手柄(收放) -->
    <div class="rn-overlay">
      <div
        class="rn-mask"
        :style="{ width: windowLeft + 'px' }"
      />
      <div
        class="rn-window"
        :style="{ left: windowLeft + 'px', width: windowWidth + 'px' }"
        @pointerdown.prevent="startDrag('window', $event)"
      >
        <div
          class="rn-handle"
          @pointerdown.prevent.stop="startDrag('left', $event)"
        />
        <div
          class="rn-handle rn-handle-r"
          @pointerdown.prevent.stop="startDrag('right', $event)"
        />
      </div>
      <div
        class="rn-mask"
        :style="{ left: (windowLeft + windowWidth) + 'px' }"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
/**
 * 区间导航条(2026-08-18,v2 SVG 自绘):TradingView Lightweight Charts 无内置
 * range slider。v1 用第二个 lw 实例的坐标轴做 px↔time 映射,timeToCoordinate
 * 语义/时机不可控(实测窗口坐标 NaN/溢出/事件失灵);v2 改纯像素比例映射:
 * 数据按索引均分铺满宽度,px↔index↔time 线性换算,SVG polyline 画缩略图,
 * 零图表库依赖、零坐标轴黑盒。
 *
 * 交互:拖窗口=平移;拖左右手柄=单端收放;外部主图缩放 → setRange() 同步。
 * 数据流:拖拽 → emit('rangeChange',{from,to}) → 宿主 setVisibleRange;
 * 拖拽进行中忽略 setRange 回写(防迭代反馈环,松手后自然校正)。
 */
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'

const props = defineProps<{
  /** 全量数据(升序): {time:'YYYY-MM-DD', close:number}[] */
  data: { time: string; close: number }[]
}>()

const emit = defineEmits<{
  (e: 'rangeChange', range: { from: string; to: string }): void
  /** 拖拽起止通知:宿主在拖拽中挂起懒加载(每帧 emit 会形成加载风暴),松手后补一次 */
  (e: 'dragState', dragging: boolean): void
}>()

const rootEl = ref<HTMLElement | null>(null)
const rnWidth = ref(1000)
const windowLeft = ref(0)
const windowWidth = ref(0)

let dragMode: 'window' | 'left' | 'right' | null = null
let dragStartX = 0
let dragStartLeft = 0
let dragStartWidth = 0

const width = () => rootEl.value?.clientWidth ?? 0
const n = () => props.data.length

// ---- px ↔ index ↔ time(线性均分) ----
function xToTime(x: number): string | null {
  if (n() < 2 || width() <= 0) return null
  const ratio = Math.max(0, Math.min(1, x / width()))
  const idx = Math.round(ratio * (n() - 1))
  return props.data[idx]?.time ?? null
}
function timeToX(t: string): number | null {
  if (n() < 2 || width() <= 0) return null
  // 二分:数据升序,时间串字典序=时间序
  let lo = 0, hi = n() - 1
  if (t < props.data[0].time) return 0
  if (t > props.data[hi].time) return width()
  while (lo < hi) {
    const mid = (lo + hi) >> 1
    if (props.data[mid].time < t) lo = mid + 1
    else hi = mid
  }
  return (lo / (n() - 1)) * width()
}

// ---- 缩略折线(close 归一化铺满) ----
const sparkPoints = computed(() => {
  const d = props.data
  if (d.length < 2) return ''
  const vals = d.map(x => x.close)
  const min = Math.min(...vals), max = Math.max(...vals)
  const span = max - min || 1
  const H = 48, pad = 2
  const step = rnWidth.value / (d.length - 1)
  return d.map((x, i) => {
    const y = pad + (H - pad * 2) * (1 - (x.close - min) / span)
    return `${(i * step).toFixed(1)},${y.toFixed(1)}`
  }).join(' ')
})

// 数据就绪:首次初始化窗口=最近 3 个月(按总时间跨度换算 px,非固定比例
// ——不同数据量下 25% 的时间含义漂移);后续数据变化(懒加载 prepend 历史)
// 按"窗口两端时间锚点"重新定位——否则窗口被重置回右侧,用户正在左拖时
// 表现为窗口突然变小/跳走(2026-08-18 实测主 bug)
let initialized = false
const DEFAULT_WINDOW_DAYS = 90  // 3 个月
watch(() => props.data, async (d) => {
  if (d.length < 2) return
  await nextTick()
  const w = width()
  if (w <= 0) return
  rnWidth.value = w
  if (!initialized) {
    const first = new Date(d[0].time).getTime()
    const last = new Date(d[d.length - 1].time).getTime()
    const spanDays = Math.max(1, (last - first) / 86400000)
    const ratio = Math.min(1, DEFAULT_WINDOW_DAYS / spanDays)
    windowWidth.value = Math.max(14, w * ratio)
    windowLeft.value = w - windowWidth.value   // 贴右=最新区间
    initialized = true
    return
  }
  // 保持时间锚:记录拖拽/当前窗口的时间语义,数据扩展后按时间找位
  const anchorFrom = xToTime(windowLeft.value)
  const anchorTo = xToTime(windowLeft.value + windowWidth.value)
  if (anchorFrom && anchorTo) setRange(anchorFrom, anchorTo)
}, { immediate: true })

/** 外部主图可视区间 → 窗口同步(拖拽中忽略,指针独占防反馈环) */
function setRange(from: string, to: string) {
  if (dragMode) return
  const xf = timeToX(from), xt = timeToX(to)
  const w = width()
  if (xf == null || xt == null || w <= 0 || !Number.isFinite(xf) || !Number.isFinite(xt)) return
  windowLeft.value = Math.max(0, Math.min(xf, w))
  windowWidth.value = Math.max(12, Math.min(xt, w) - windowLeft.value)
}
defineExpose({ setRange })

function emitRange() {
  const from = xToTime(windowLeft.value)
  const to = xToTime(windowLeft.value + windowWidth.value)
  if (from && to && from !== to) emit('rangeChange', { from, to })
}

// ---- 拖拽 ----
function startDrag(mode: 'window' | 'left' | 'right', e: PointerEvent) {
  dragMode = mode
  dragStartX = e.clientX
  dragStartLeft = windowLeft.value
  dragStartWidth = windowWidth.value
  emit('dragState', true)
  window.addEventListener('pointermove', onDrag)
  window.addEventListener('pointerup', stopDrag)
}
function onDrag(e: PointerEvent) {
  if (!dragMode) return
  const dx = e.clientX - dragStartX
  const w = width()
  if (w <= 0) return
  if (dragMode === 'window') {
    windowLeft.value = Math.max(0, Math.min(dragStartLeft + dx, w - dragStartWidth))
  } else if (dragMode === 'left') {
    const nl = Math.max(0, Math.min(dragStartLeft + dx, dragStartLeft + dragStartWidth - 12))
    windowWidth.value = dragStartWidth - (nl - dragStartLeft)
    windowLeft.value = nl
  } else {
    windowWidth.value = Math.max(12, Math.min(dragStartWidth + dx, w - dragStartLeft))
  }
  emitRange()
}
function stopDrag() {
  const wasDragging = dragMode !== null
  dragMode = null
  window.removeEventListener('pointermove', onDrag)
  window.removeEventListener('pointerup', stopDrag)
  if (wasDragging) {
    emit('dragState', false)
    emitRange()   // 松手补一帧:宿主据此做一次懒加载判定与窗口校正
  }
}

let ro: ResizeObserver | null = null
onMounted(() => {
  if (!rootEl.value) return
  ro = new ResizeObserver(() => {
    const w = width()
    if (w <= 0) return
    const ratio = windowWidth.value > 0 ? windowWidth.value / w : 0.25
    rnWidth.value = w
    windowWidth.value = w * ratio
    windowLeft.value = Math.min(windowLeft.value, w - windowWidth.value)
  })
  ro.observe(rootEl.value)
})
onUnmounted(() => {
  stopDrag()
  ro?.disconnect()
})
</script>

<style scoped>
.range-nav {
  position: relative;
  width: 100%;
  height: 52px;
  user-select: none;
}
.rn-spark {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}
.rn-spark polyline {
  fill: none;
  stroke: hsl(var(--primary) / 0.7);
  stroke-width: 1;
}
.rn-overlay { position: absolute; inset: 0; display: flex; }
.rn-mask {
  flex: none;
  background: hsl(var(--foreground) / 0.55);
}
.rn-window {
  position: absolute;
  top: 0;
  bottom: 0;
  border: 1px solid hsl(var(--primary) / 0.9);
  background: hsl(var(--primary) / 0.08);
  border-radius: 3px;
  cursor: grab;
  /* 懒加载 prepend 数据 → 缩略图变长 → 时间锚定的窗口等比收窄:瞬跳感知
     为 bug,0.25s 过渡变平滑缩放;拖拽中禁用(指针须跟手无延迟) */
  transition: left 0.25s ease, width 0.25s ease;
}
.rn-window:active { cursor: grabbing; transition: none; }
.rn-window:active { cursor: grabbing; }
.rn-handle {
  position: absolute;
  top: 0;
  bottom: 0;
  left: -1px;
  width: 7px;
  cursor: ew-resize;
  background: hsl(var(--primary));
  border-radius: 3px 0 0 3px;
}
.rn-handle-r {
  left: auto;
  right: -1px;
  border-radius: 0 3px 3px 0;
}
</style>
