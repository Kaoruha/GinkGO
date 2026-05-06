# 分段稳定性折线图设计

## 概述

为分段稳定性验证页面添加 ECharts 折线图，使用户能直观对比各段表现差异。

## 背景

当前 `SegmentStability.vue` 仅展示 stat-card 评分和文字表格，无法直观看出各段间的指标变化趋势。项目使用 lightweight-charts（TradingView 时序图库），不适合非时序的分类数据（X轴=段编号或分段数），因此引入 ECharts。

## 变更范围

| 文件 | 变更 |
|------|------|
| `web-ui/package.json` | 新增 `echarts` 依赖 |
| `web-ui/src/views/portfolio/validation/SegmentStability.vue` | 添加两个 ECharts 图表区域 |

## 新增依赖

- **ECharts** — 通用图表库，支持多Y轴折线图、深色主题、响应式

## 页面布局

从上到下：

1. **分析配置卡片** — 不变（任务选择 + 分段数 Tag 选择器 + 开始分析按钮）
2. **stats-grid 评分卡片** — 不变（每 window 一个 stat-card 展示稳定性评分）
3. **跨 window 对比概览图**（新增）— 全宽 card
   - X轴：分段数（2, 4, 8, 16）
   - Y轴：多Y轴 — 左轴=收益率，右轴1=夏普，右轴2=最大回撤
   - 胜率：用百分比标注或单独右轴
   - 4条折线，不同颜色
4. **每 window 双列网格**（改造）— 2列 grid 排列
   - 每个 card 内上部：折线图（X轴=段编号，收益线+回撤线）
   - 每个 card 内下部：原有数据表

## 图表规格

### 概览图

- 类型：ECharts multi-axis line chart
- 数据源：`result.windows`，取每个 window 的 segments 指标均值
- 系列：
  - 收益率（左Y轴，蓝色 #3b82f6）
  - 夏普比率（右Y轴1，黄色 #eab308）
  - 最大回撤（右Y轴2，红色 #ef4444）
  - 胜率（百分比标注，绿色 #22c55e）
- 主题：深色（背景 #1a1a2e，网格 #2a2a3e，文字 rgba(255,255,255,0.6)）
- 高度：300px

### 详情图（每 window 一个）

- 类型：ECharts line chart
- 数据源：`window.segments` 数组
- X轴：段编号（1, 2, 3, ...）
- 系列：
  - 收益（左Y轴，绿色 #22c55e）
  - 最大回撤（右Y轴，红色 #ef4444）
- 高度：250px
- 与数据表纵向排列在同一 card 内

## 实现要点

- 使用 `echarts` 的 `init` + `setOption` 模式
- 通过 `ref` 持有图表容器 DOM，`onMounted` 初始化，`onUnmounted` 销毁
- `watch(result)` 在数据更新时调用 `setOption` 更新图表
- 窗口 resize 时调用 `chart.resize()`
- 双列网格使用 CSS Grid：`grid-template-columns: repeat(2, 1fr)`

## 不做的事

- 不封装独立图表组件（KISS，仅在 SegmentStability.vue 内使用）
- 不引入 ECharts 的按需加载（直接全量 import，项目规模小）
- 不改动后端 API 或数据结构
