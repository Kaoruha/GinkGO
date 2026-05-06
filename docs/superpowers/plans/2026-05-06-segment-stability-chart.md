# 分段稳定性折线图 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为 SegmentStability.vue 添加 ECharts 折线图（跨 window 概览 + 每 window 详情），让用户直观对比各段表现差异。

**Architecture:** 在现有 SegmentStability.vue 内直接使用 ECharts init/setOption 模式，不封装独立图表组件。概览图用多Y轴折线图，详情图用双线折线图，数据直接从 API 返回的 result.windows 读取。

**Tech Stack:** Vue 3 Composition API + ECharts 5

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `web-ui/package.json` | Modify | 添加 echarts 依赖 |
| `web-ui/src/views/portfolio/validation/SegmentStability.vue` | Modify | 添加图表容器、ECharts 初始化/更新/销毁逻辑、双列网格样式 |

---

### Task 1: 安装 ECharts 依赖

**Files:**
- Modify: `web-ui/package.json`

- [ ] **Step 1: 安装 echarts**

Run:
```bash
cd /home/kaoru/Ginkgo/web-ui && npm install echarts
```

- [ ] **Step 2: 验证安装**

Run:
```bash
cd /home/kaoru/Ginkgo/web-ui && node -e "require('echarts'); console.log('echarts OK')"
```
Expected: `echarts OK`

- [ ] **Step 3: Commit**

```bash
cd /home/kaoru/Ginkgo && git add web-ui/package.json web-ui/package-lock.json && git commit -m "chore: add echarts dependency for segment stability charts"
```

---

### Task 2: 添加跨 window 概览折线图

**Files:**
- Modify: `web-ui/src/views/portfolio/validation/SegmentStability.vue`

概览图在 stats-grid 下方、详情网格上方，全宽 card，X轴=分段数，多Y轴（收益/夏普/回撤/胜率）。

- [ ] **Step 1: 在 `<script setup>` 中添加 ECharts 逻辑**

在现有 import 后添加 echarts 导入和图表逻辑：

```typescript
import * as echarts from 'echarts'

// 概览图
const overviewChartRef = ref<HTMLDivElement | null>(null)
let overviewChart: echarts.ECharts | null = null

const initOverviewChart = () => {
  if (!overviewChartRef.value || !result.value) return
  if (overviewChart) overviewChart.dispose()

  overviewChart = echarts.init(overviewChartRef.value)

  const windows = result.value.windows
  const xData = windows.map((w: any) => `${w.n_segments}段`)

  overviewChart.setOption({
    backgroundColor: '#1a1a2e',
    tooltip: { trigger: 'axis' },
    legend: {
      data: ['收益率', '夏普比率', '最大回撤', '胜率'],
      textStyle: { color: 'rgba(255,255,255,0.6)', fontSize: 12 },
      top: 0,
    },
    grid: { top: 40, right: 120, bottom: 30, left: 60 },
    xAxis: {
      type: 'category',
      data: xData,
      axisLabel: { color: 'rgba(255,255,255,0.6)' },
      axisLine: { lineStyle: { color: '#2a2a3e' } },
    },
    yAxis: [
      {
        type: 'value',
        name: '收益率',
        nameTextStyle: { color: '#3b82f6', fontSize: 11 },
        axisLabel: { color: '#3b82f6', formatter: '{value}%' },
        splitLine: { lineStyle: { color: '#2a2a3e' } },
      },
      {
        type: 'value',
        name: '夏普',
        nameTextStyle: { color: '#eab308', fontSize: 11 },
        axisLabel: { color: '#eab308' },
        splitLine: { show: false },
      },
      {
        type: 'value',
        name: '回撤',
        nameTextStyle: { color: '#ef4444', fontSize: 11 },
        axisLabel: { color: '#ef4444', formatter: '{value}%' },
        splitLine: { show: false },
        offset: 60,
      },
    ],
    series: [
      {
        name: '收益率',
        type: 'line',
        data: windows.map((w: any) => {
          const avg = w.segments.reduce((s: number, seg: any) => s + seg.total_return, 0) / w.segments.length
          return (avg * 100).toFixed(2)
        }),
        yAxisIndex: 0,
        itemStyle: { color: '#3b82f6' },
        lineStyle: { width: 2 },
        symbol: 'circle',
        symbolSize: 8,
      },
      {
        name: '夏普比率',
        type: 'line',
        data: windows.map((w: any) => {
          const avg = w.segments.reduce((s: number, seg: any) => s + seg.sharpe, 0) / w.segments.length
          return avg.toFixed(2)
        }),
        yAxisIndex: 1,
        itemStyle: { color: '#eab308' },
        lineStyle: { width: 2 },
        symbol: 'diamond',
        symbolSize: 8,
      },
      {
        name: '最大回撤',
        type: 'line',
        data: windows.map((w: any) => {
          const avg = w.segments.reduce((s: number, seg: any) => s + seg.max_drawdown, 0) / w.segments.length
          return (avg * 100).toFixed(2)
        }),
        yAxisIndex: 2,
        itemStyle: { color: '#ef4444' },
        lineStyle: { width: 2 },
        symbol: 'triangle',
        symbolSize: 8,
      },
      {
        name: '胜率',
        type: 'line',
        data: windows.map((w: any) => {
          const avg = w.segments.reduce((s: number, seg: any) => s + seg.win_rate, 0) / w.segments.length
          return (avg * 100).toFixed(1)
        }),
        yAxisIndex: 0,
        itemStyle: { color: '#22c55e' },
        lineStyle: { width: 2, type: 'dashed' },
        symbol: 'rect',
        symbolSize: 8,
      },
    ],
  })
}
```

- [ ] **Step 2: 添加 watch 和 resize/销毁逻辑**

在 `onMounted` 之前添加：

```typescript
watch(result, () => {
  nextTick(() => {
    initOverviewChart()
  })
})

const handleResize = () => {
  overviewChart?.resize()
}
```

在 `onMounted` 内添加 resize 监听，并添加 `onUnmounted`：

```typescript
onMounted(() => {
  fetchBacktestList()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  overviewChart?.dispose()
  overviewChart = null
})
```

- [ ] **Step 3: 在 template 中添加概览图容器**

在 `</template>` 之前（`<template v-if="result">` 内的 stats-grid 之后）添加：

```html
<!-- 跨 window 对比概览图 -->
<div class="card overview-chart-card">
  <div class="card-header"><h3>跨分段对比概览</h3></div>
  <div class="card-body">
    <div ref="overviewChartRef" class="overview-chart"></div>
  </div>
</div>
```

- [ ] **Step 4: 添加概览图样式**

在 `<style scoped>` 中添加：

```css
.overview-chart-card {
  flex-shrink: 0;
  margin-bottom: 16px;
}

.overview-chart {
  width: 100%;
  height: 300px;
}
```

- [ ] **Step 5: 通过浏览器验证概览图**

Run Playwright 脚本打开验证页面，运行分析，截图确认概览图正确渲染（4条折线、多Y轴、深色主题）。

- [ ] **Step 6: Commit**

```bash
cd /home/kaoru/Ginkgo && git add web-ui/src/views/portfolio/validation/SegmentStability.vue && git commit -m "feat: add overview line chart for segment stability validation"
```

---

### Task 3: 改造详情区为双列网格 + 每段折线图

**Files:**
- Modify: `web-ui/src/views/portfolio/validation/SegmentStability.vue`

将现有的每个 window card 改为双列网格排列，每个 card 内添加折线图（X轴=段编号，收益+回撤双线）。

- [ ] **Step 1: 添加详情图逻辑到 `<script setup>`**

在概览图逻辑之后添加：

```typescript
// 详情图
const detailChartRefs = ref<Map<number, HTMLDivElement>>(new Map())
const detailCharts = new Map<number, echarts.ECharts>()

const setDetailChartRef = (nSegments: number) => (el: any) => {
  if (el) detailChartRefs.value.set(nSegments, el as HTMLDivElement)
}

const initDetailCharts = () => {
  if (!result.value) return
  // 清理旧图表
  detailCharts.forEach(c => c.dispose())
  detailCharts.clear()

  for (const w of result.value.windows) {
    const el = detailChartRefs.value.get(w.n_segments)
    if (!el) continue

    const chart = echarts.init(el)
    detailCharts.set(w.n_segments, chart)

    const xData = w.segments.map((_: any, i: number) => `段${i + 1}`)

    chart.setOption({
      backgroundColor: 'transparent',
      tooltip: { trigger: 'axis' },
      legend: {
        data: ['收益', '最大回撤'],
        textStyle: { color: 'rgba(255,255,255,0.6)', fontSize: 11 },
        top: 0,
      },
      grid: { top: 36, right: 60, bottom: 24, left: 50 },
      xAxis: {
        type: 'category',
        data: xData,
        axisLabel: { color: 'rgba(255,255,255,0.6)', fontSize: 11 },
        axisLine: { lineStyle: { color: '#2a2a3e' } },
      },
      yAxis: [
        {
          type: 'value',
          name: '收益',
          nameTextStyle: { color: '#22c55e', fontSize: 11 },
          axisLabel: { color: '#22c55e', formatter: '{value}%' },
          splitLine: { lineStyle: { color: '#2a2a3e' } },
        },
        {
          type: 'value',
          name: '回撤',
          nameTextStyle: { color: '#ef4444', fontSize: 11 },
          axisLabel: { color: '#ef4444', formatter: '{value}%' },
          splitLine: { show: false },
        },
      ],
      series: [
        {
          name: '收益',
          type: 'line',
          data: w.segments.map((seg: any) => (seg.total_return * 100).toFixed(2)),
          yAxisIndex: 0,
          itemStyle: { color: '#22c55e' },
          lineStyle: { width: 2 },
          symbol: 'circle',
          symbolSize: 6,
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(34,197,94,0.2)' },
              { offset: 1, color: 'rgba(34,197,94,0)' },
            ]),
          },
        },
        {
          name: '最大回撤',
          type: 'line',
          data: w.segments.map((seg: any) => (seg.max_drawdown * 100).toFixed(2)),
          yAxisIndex: 1,
          itemStyle: { color: '#ef4444' },
          lineStyle: { width: 2 },
          symbol: 'triangle',
          symbolSize: 6,
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: 'rgba(239,68,68,0.15)' },
              { offset: 1, color: 'rgba(239,68,68,0)' },
            ]),
          },
        },
      ],
    })
  }
}
```

更新 watch result 回调，同时初始化详情图：

```typescript
watch(result, () => {
  nextTick(() => {
    initOverviewChart()
    initDetailCharts()
  })
})
```

更新 onUnmounted，销毁详情图：

```typescript
onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  overviewChart?.dispose()
  overviewChart = null
  detailCharts.forEach(c => c.dispose())
  detailCharts.clear()
})
```

更新 handleResize，同时 resize 详情图：

```typescript
const handleResize = () => {
  overviewChart?.resize()
  detailCharts.forEach(c => c.resize())
}
```

- [ ] **Step 2: 改造 template 中详情卡片为双列网格**

将现有的 `<div class="card" v-for="w in result.windows">` 区块替换为：

```html
<!-- 双列详情网格 -->
<div class="detail-grid">
  <div class="card" v-for="w in result.windows" :key="'detail-' + w.n_segments">
    <div class="card-header">
      <h3>{{ w.n_segments }} 段分析</h3>
      <span :class="scoreClass(w.stability_score)">评分 {{ (w.stability_score * 100).toFixed(1) }}%</span>
    </div>
    <div class="card-body">
      <div :ref="setDetailChartRef(w.n_segments)" class="detail-chart"></div>
      <table class="data-table">
        <thead>
          <tr>
            <th>段</th>
            <th>收益</th>
            <th>夏普</th>
            <th>最大回撤</th>
            <th>胜率</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(seg, i) in w.segments" :key="i">
            <td>{{ i + 1 }}</td>
            <td :class="seg.total_return >= 0 ? 'stat-success' : 'stat-danger'">
              {{ (seg.total_return * 100).toFixed(2) }}%
            </td>
            <td>{{ seg.sharpe.toFixed(2) }}</td>
            <td class="stat-danger">{{ (seg.max_drawdown * 100).toFixed(2) }}%</td>
            <td>{{ (seg.win_rate * 100).toFixed(1) }}%</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</div>
```

- [ ] **Step 3: 添加双列网格和详情图样式**

在 `<style scoped>` 中添加：

```css
.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
  margin-top: 16px;
}

.detail-chart {
  width: 100%;
  height: 250px;
  margin-bottom: 12px;
}
```

- [ ] **Step 4: 通过浏览器验证完整效果**

Run Playwright 脚本：
1. 打开验证页面，运行分析
2. 截图确认概览图 + 双列详情网格（每 card 内含折线图 + 表格）
3. 验证 resize 时图表自适应

- [ ] **Step 5: Commit**

```bash
cd /home/kaoru/Ginkgo && git add web-ui/src/views/portfolio/validation/SegmentStability.vue && git commit -m "feat: add detail charts and grid layout for segment stability"
```

---

### Task 4: 最终验证与清理

- [ ] **Step 1: 完整浏览器 E2E 验证**

Run Playwright 脚本测试完整流程：
1. 登录 → 进入 portfolio 验证 tab
2. 选择任务 + 选择分段（2, 4, 8, 16）→ 点击分析
3. 等待结果加载
4. 截图确认：分析配置 → 评分卡片 → 概览图(多Y轴4条线) → 双列详情(图+表)
5. 滚动页面确认无布局溢出

- [ ] **Step 2: Vite 构建验证**

Run:
```bash
cd /home/kaoru/Ginkgo/web-ui && npx vite build 2>&1 | tail -5
```
Expected: 构建成功，无 TypeScript 错误

- [ ] **Step 3: 最终 Commit**

```bash
cd /home/kaoru/Ginkgo && git add -A && git commit -m "feat: segment stability charts with echarts - overview and detail views"
```

- [ ] **Step 4: Push**

```bash
cd /home/kaoru/Ginkgo && git push -u origin 024-feat/segment-stability-chart
```
