# Web UI and API Server - 功能与页面架构

**Feature**: 001-web-ui-api
**Created**: 2026-01-28
**Status**: Draft

## 1. 功能模块架构

### 1.1 功能层级划分

```
Ginkgo Web UI
├── 核心功能层
│   ├── 实时监控
│   ├── 策略回测
│   ├── 数据管理
│   └── 风控管理
│
├── 支撑功能层
│   ├── 用户认证
│   ├── 系统设置
│   └── 日志查看
│
└── 信息功能层
    ├── API文档
    └── 帮助指南
```

### 1.2 功能模块详细划分

#### 模块A: 实时监控 (核心)
- **A1** 持仓监控
  - 当前持仓列表
  - 持仓盈亏统计
  - 持仓分布分析
- **A2** 净值监控
  - 净值曲线展示
  - 收益率统计
  - 回撤分析
- **A3** 系统监控
  - Worker状态
  - 数据延迟
  - 系统健康度
- **A4** 信号管理
  - 统一信号中心（策略信号 + 风控信号）
  - 实时信号展示
  - 信号历史查询
  - 信号标记处理

#### 模块B: 策略回测 (核心)
- **B1** 回测任务
  - 任务列表
  - 任务控制（启动/停止）
  - 任务状态监控
- **B2** 新建回测
  - 选择Portfolio（可多选）
  - 配置回测参数（时间范围、数据范围、税率等）
  - 启动回测
- **B3** 结果分析
  - 性能指标
  - 交易记录
  - 净值曲线
  - 回测对比

#### 模块C: 组件与Portfolio管理 (核心) ⭐
- **C1** 组件库
  - 按类型分组显示 (STRATEGY/SELECTOR/SIZER/RISKMANAGER/ANALYZER)
  - 组件搜索和筛选
  - 组件状态标识 (预置/自定义/使用中)
- **C2** 组件编辑
  - 在线代码编辑器 (Python语法高亮、行号)
  - 代码语法验证
  - 组件版本历史
- **C3** 组件管理
  - 创建自定义组件
  - 复制预置组件
  - 删除组件 (带引用检查)
- **C4** Portfolio管理 ⭐ NEW
  - Portfolio列表
  - 新建Portfolio (节点图编辑器)
  - Portfolio详情
  - Portfolio配置

#### 模块D: 数据管理 (核心)
- **C1** 股票信息
  - 股票列表查询
  - 股票信息更新
  - 数据统计
- **C2** K线数据
  - K线查询展示
  - 数据范围查看
  - 数据质量检查
  - 数据更新
- **C3** Tick数据
  - Tick查询
  - 数据更新
  - 质量检查
- **C4** 复权因子
  - 因子查询
  - 因子更新

#### 模块D: 系统管理 (支撑)
- **E1** 用户设置
  - 个人配置
  - 界面偏好
- **E2** 系统配置
  - 参数配置
  - 数据源配置
- **E3** 用户管理 ⭐ NEW
  - 用户CRUD（创建、查询、编辑、删除）
  - 联系方式管理（Email、Webhook、Discord）
- **E4** 用户组管理 ⭐ NEW
  - 用户组CRUD
  - 组成员管理
  - 批量通知配置
- **E5** 通知管理 ⭐ NEW
  - 通知模板管理
  - 通知历史查询
  - 发送状态追踪
- **E6** 日志查看
  - 系统日志
  - 错误日志

---

## 1.5 技术栈与项目架构

### 1.5.1 技术栈选型

#### 后端 - API Server (独立项目)
```
框架: FastAPI
- 现代异步框架，自动生成OpenAPI文档
- 原生WebSocket支持
- Pydantic数据验证
- 优秀的性能表现

数据库访问:
- 通过service_hub访问Ginkgo核心服务
- 不直接访问数据库，保持架构清晰

通信:
- RESTful API (同步)
- WebSocket (实时推送)
- Kafka (异步通知)
```

#### 前端 - Web UI (独立项目)
```
框架: Vue 3 (Composition API + Vite)
- 响应式设计，支持桌面和移动端
- 组件化开发，状态管理(Pinia)

UI: TailwindCSS + Ant Design Vue
- 原子化CSS优先，无运行时CSS
- Ant Design Vue组件库

代码编辑: Monaco Editor
- VS Code同款，Python语法高亮
- 智能提示和错误检查

图表库: Lightweight Charts + ECharts ⭐
- Lightweight Charts: 专业K线图(TradingView开源)
- ECharts: 通用统计图表(净值、盈亏分析)

状态: Pinia
- 轻量级状态管理
- TypeScript支持

构建: Vite
- 快速热更新
- 生产优化
```

### 1.5.2 项目目录结构

```
ginkgo/
├── apiserver/                  # API Server (独立项目)
│   ├── main.py                 # FastAPI应用入口
│   ├── api/                     # API路由模块
│   │   ├── __init__.py
│   │   ├── portfolio.py         # Portfolio相关API
│   │   ├── backtest.py           # 回测相关API
│   │   ├── components.py         # 组件管理API
│   │   ├── data.py               # 数据管理API
│   │   ├── notifications.py       # 通知系统API
│   │   ├── users.py              # 用户管理API
│   │   └── websocket.py          # WebSocket处理
│   ├── models/                   # Pydantic DTOs
│   ├── services/                 # 业务逻辑层
│   ├── middleware/               # 中间件
│   ├── core/                     # 核心配置
│   ├── websocket/                # WebSocket处理
│   └── requirements.txt          # Python依赖
│
├── web-ui/                     # Web前端 (独立项目)
│   ├── src/
│   │   ├── main.ts               # 应用入口
│   │   ├── App.vue              # 根组件
│   │   ├── layouts/              # 布局组件 ⭐
│   │   │   ├── DashboardLayout.vue
│   │   │   ├── BacktestLayout.vue
│   │   │   ├── ComponentLayout.vue
│   │   │   ├── SettingsLayout.vue
│   │   │   └── EmptyLayout.vue
│   │   ├── views/                # 页面组件
│   │   ├── components/            # 通用组件 ⭐
│   │   │   ├── base/              # 基础组件
│   │   │   │   ├── DataTable.vue   # 数据表格(可配置)
│   │   │   │   ├── FilterBar.vue    # 筛选栏(可配置)
│   │   │   │   ├── ActionBar.vue    # 操作栏(可配置)
│   │   │   │   └── StatCard.vue     # 统计卡片(可配置)
│   │   │   ├── charts/           # 图表组件 ⭐
│   │   │   │   ├── KLineChart.vue   # K线图(Lightweight Charts)
│   │   │   │   ├── NetValueChart.vue # 净值曲线(ECharts)
│   │   │   │   ├── PnLChart.vue      # 盈亏分析(ECharts)
│   │   │   │   └── IndicatorChart.vue # 技术指标(ECharts)
│   │   │   ├── arena/            # 竞技场组件 ⭐
│   │   │   │   ├── ArenaRanking.vue   # 策略排行榜
│   │   │   │   ├── SignalStream.vue   # 实时信号流
│   │   │   │   ├── NewsFeed.vue       # 资讯通知
│   │   │   │   └── MyStats.vue        # 我的指标
│   │   │   ├── forms/             # 表单组件
│   │   │   └── editors/           # 编辑器组件
│   │   │       ├── MonacoEditor.vue    # 代码编辑器
│   │   │   │       ├── NodeGraphEditor.vue # 节点图编辑器
│   │   │   │       └── JsonEditor.vue      # JSON编辑器
│   │   ├── composables/          # 组合式函数 ⭐
│   │   │   ├── useTable.py         # 表格逻辑
│   │   │   ├── useFilter.py        # 筛选逻辑
│   │   │   ├── usePagination.py    # 分页逻辑
│   │   │   └── useWebSocket.py     # WebSocket逻辑
│   │   ├── stores/               # Pinia状态管理
│   │   ├── api/                  # API调用封装
│   │   ├── config/               # 配置文件
│   │   │   ├── tailwind.config.js  # Tailwind配置 ⭐
│   │   │   └── settings.ts
│   │   ├── styles/               # 样式文件
│   │   │   └── main.css           # 全局样式(仅Tailwind)
│   │   ├── types/                # TypeScript类型
│   │   └── utils/                # 工具函数
│   ├── public/                   # 静态资源
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
│
├── src/                         # Ginkgo核心库(已存在)
│   └── ginkgo/
│       ├── data/
│       ├── trading/
│       ├── notifier/
│       └── ...
│
├── .conf/                       # 配置和Docker文件统一存放
│   ├── Dockerfile.api-server    # API Server容器
│   ├── Dockerfile.dataworker   # Data Worker容器(已存在)
│   ├── docker-compose.yml        # 服务编排
│   └── .env                     # 环境变量
│
└── docker-compose.yml           # 顶层编排(可选)
```

### 1.5.3 前端架构设计原则 ⭐

#### 组件抽象策略

**核心理念**: 所有页面由配置驱动的基础组件组合而成

```javascript
// 配置驱动的组件使用示例
const tableConfig = {
  columns: [
    { key: 'code', title: '代码', width: 120 },
    { key: 'name', title: '名称', width: 200 },
    { key: 'price', title: '价格', format: 'currency' },
  ],
  actions: [
    { label: '查看详情', onClick: (row) => router.push(`/data/stockinfo/${row.code}`) },
    { label: '编辑', onClick: (row) => openEditor(row) },
  ]
}

// 在模板中使用
<DataTable :config="tableConfig" :data="stocks" />
```

#### Layout适配策略

```vue
<!-- DashboardLayout.vue - 仪表盘布局 -->
<template>
  <div class="flex h-screen bg-gray-50">
    <!-- 侧边栏 -->
    <Sidebar />

    <!-- 主内容区 -->
    <main class="flex-1 overflow-auto">
      <slot />
    </main>
  </div>
</template>

<!-- EmptyLayout.vue - 空白布局(全屏页面) -->
<template>
  <div class="h-screen">
    <slot />
  </div>
</template>
```

#### TailwindCSS配置规范

**目录结构**:
```
styles/
├── main.css              # 仅包含@tailwind指令
├── components.css       # (禁用) 不使用组件CSS
└── pages.css           # (禁用) 不使用页面CSS
```

**配置规范** (`tailwind.config.js`):
```javascript
export default {
  content: [
    './index.html',
    './src/**/*.{vue,ts}',
  ],
  theme: {
    extend: {
      // 语义化颜色命名
      colors: {
        primary: { DEFAULT: '#1890ff', light: '#40a9ff', dark: '#096dd9' },
        success: { DEFAULT: '#52c41a', light: '#73d13d', dark: '#389e0d' },
        warning: { DEFAULT: '#faad14', light: '#ffc53d', dark: '#d48806' },
        danger:  { DEFAULT: '#ff4d4f', light: '#ff7875', dark: '#cf1322' },
      },
      // 间距规范
      spacing: {
        'section': '2rem',
        'card': '1.5rem',
        'control': '0.75rem',
      }
    }
  },
  plugins: [
    require('@tailwindcss/forms'),  // 表单样式优化
  ]
}
```

**使用规范**:
```vue
<!-- ✅ 正确: 使用Tailwind类 -->
<div class="bg-white rounded-lg shadow-sm p-4">
  <h2 class="text-lg font-semibold text-gray-900">标题</h2>
</div>

<!-- ❌ 错误: 使用style属性 -->
<div style="background: white; padding: 1rem;">
  <h2 style="font-size: 1.125rem;">标题</h2>
</div>

<!-- ❌ 错误: 使用scoped CSS -->
<style scoped>
.custom-card {
  background: white;
  padding: 1rem;
}
</style>
```

### 1.5.4 基础组件设计规范

#### DataTable.vue - 数据表格组件

```vue
<template>
  <div class="bg-white rounded-lg shadow-sm overflow-hidden">
    <!-- 表格 -->
    <a-table
      :columns="config.columns"
      :data-source="data"
      :pagination="false"
      :row-key="config.rowKey || 'id'"
      :scroll="{ x: config.scrollX || 1200 }"
      class="data-table"
    >
      <!-- 动态插槽: 列自定义渲染 -->
      <template v-for="col in config.columns" #[col.slot]="slotProps" :key="col.key">
        <slot :name="col.slot" v-bind="slotProps">
          {{ slotProps.text }}
        </slot>
      </template>

      <!-- 操作列 -->
      <template #action="{ record }">
        <a-space>
          <a v-for="action in config.actions" :key="action.label" @click="action.onClick(record)">
            {{ action.label }}
          </a>
        </a-space>
      </template>
    </a-table>

    <!-- 分页 -->
    <div v-if="config.pagination" class="px-4 py-3 border-t border-gray-200">
      <a-pagination
        v-model:current="pagination.current"
        v-model:page-size="pagination.pageSize"
        :total="pagination.total"
        :show-size-changer="true"
        :show-quick-jumper="true"
        @change="handlePageChange"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
interface ColumnConfig {
  key: string
  title: string
  width?: number
  format?: 'text' | 'currency' | 'percent' | 'date'
  slot?: string
}

interface TableConfig {
  columns: ColumnConfig[]
  actions?: Array<{ label: string; onClick: (row: any) => void }>
  rowKey?: string
  scrollX?: number
  pagination?: boolean
}

const props = defineProps<{
  config: TableConfig
  data: any[]
}>()

const emit = defineEmits(['page-change'])

const pagination = reactive({ current: 1, pageSize: 20, total: 0 })

const handlePageChange = (page: number, pageSize: number) => {
  emit('page-change', { page, pageSize })
}
</script>
```

#### FilterBar.vue - 筛选栏组件

```vue
<template>
  <div class="bg-white rounded-lg shadow-sm p-4 mb-4">
    <a-form layout="inline" :model="filterState">
      <a-form-item v-for="field in config.fields" :key="field.key" :label="field.label">
        <!-- 文本输入 -->
        <a-input
          v-if="field.type === 'text'"
          v-model:value="filterState[field.key]"
          :placeholder="`请输入${field.label}`"
          allow-clear
        />

        <!-- 选择器 -->
        <a-select
          v-if="field.type === 'select'"
          v-model:value="filterState[field.key]"
          :placeholder="`请选择${field.label}`"
          allow-clear
          :options="field.options"
        />

        <!-- 日期范围 -->
        <a-range-picker
          v-if="field.type === 'dateRange'"
          v-model:value="filterState[field.key]"
        />
      </a-form-item>

      <!-- 操作按钮 -->
      <a-form-item>
        <a-space>
          <a-button type="primary" @click="handleSearch">查询</a-button>
          <a-button @click="handleReset">重置</a-button>
        </a-space>
      </a-form-item>
    </a-form>
  </div>
</template>

<script setup lang="ts">
interface FilterField {
  key: string
  label: string
  type: 'text' | 'select' | 'dateRange'
  options?: Array<{ label: string; value: any }>
}

const props = defineProps<{
  config: { fields: FilterField[] }
}>()

const emit = defineEmits(['search', 'reset'])

const filterState = reactive<Record<string, any>>({})

const handleSearch = () => emit('search', { ...filterState })
const handleReset = () => {
  Object.keys(filterState).forEach(key => filterState[key] = undefined)
  emit('reset')
}
</script>
```

#### ActionBar.vue - 操作栏组件

```vue
<template>
  <div class="flex justify-between items-center mb-4">
    <!-- 左侧: 主要操作 -->
    <div class="flex space-x-2">
      <a-button
        v-for="action in config.leftActions"
        :key="action.label"
        :type="action.type || 'default'"
        :danger="action.danger"
        @click="action.onClick"
      >
        <component :is="action.icon" v-if="action.icon" class="mr-1" />
        {{ action.label }}
      </a-button>
    </div>

    <!-- 右侧: 次要操作 -->
    <div class="flex space-x-2">
      <a-button
        v-for="action in config.rightActions"
        :key="action.label"
        @click="action.onClick"
      >
        {{ action.label }}
      </a-button>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Action {
  label: string
  type?: 'primary' | 'default' | 'dashed'
  danger?: boolean
  icon?: any
  onClick: () => void
}

const props = defineProps<{
  config: {
    leftActions?: Action[]
    rightActions?: Action[]
  }
}>()
</script>
```

#### StatCard.vue - 统计卡片组件

```vue
<template>
  <div class="bg-white rounded-lg shadow-sm p-4">
    <div class="flex items-center justify-between">
      <div>
        <p class="text-sm text-gray-500 mb-1">{{ config.title }}</p>
        <p class="text-2xl font-semibold text-gray-900">
          {{ formattedValue }}
        </p>
      </div>

      <!-- 趋势指示器 -->
      <div v-if="config.trend" class="flex items-center">
        <span
          :class="{
            'text-green-500': config.trend.direction === 'up',
            'text-red-500': config.trend.direction === 'down',
          }"
        >
          {{ config.trend.direction === 'up' ? '↑' : '↓' }}
          {{ config.trend.value }}
        </span>
      </div>

      <!-- 图标 -->
      <component :is="config.icon" class="text-gray-400 text-2xl" />
    </div>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  config: {
    title: string
    value: number | string
    format?: 'number' | 'currency' | 'percent'
    trend?: {
      direction: 'up' | 'down'
      value: string
    }
    icon?: any
  }
}>()

const formattedValue = computed(() => {
  const { value, format } = props.config
  if (format === 'currency') return `¥${Number(value).toLocaleString()}`
  if (format === 'percent') return `${value}%`
  return Number(value).toLocaleString()
})
</script>
```

#### KLineChart.vue - K线图表组件

```vue
<template>
  <div class="bg-white rounded-lg shadow-sm p-4">
    <!-- 工具栏 -->
    <div class="flex items-center justify-between mb-4">
      <div class="flex items-center space-x-2">
        <a-select v-model:value="timeframe" style="width: 100px" @change="handleTimeframeChange">
          <a-select-option value="1m">1分钟</a-select-option>
          <a-select-option value="5m">5分钟</a-select-option>
          <a-select-option value="15m">15分钟</a-select-option>
          <a-select-option value="1d">日线</a-select-option>
          <a-select-option value="1w">周线</a-select-option>
        </a-select>
        <a-select v-model:value="indicatorType" style="width: 120px" @change="handleIndicatorChange">
          <a-select-option value="MA">均线</a-select-option>
          <a-select-option value="BOLL">布林带</a-select-option>
          <a-select-option value="MACD">MACD</a-select-option>
          <a-select-option value="VOL">成交量</a-select-option>
        </a-select>
      </div>
      <div class="flex items-center space-x-2">
        <a-button size="small" @click="handleReset">重置</a-button>
        <a-button size="small" type="primary" @click="handleRefresh">刷新</a-button>
      </div>
    </div>

    <!-- 图表容器 -->
    <div ref="chartContainer" class="w-full" :style="{ height: config.height || '500px' }"></div>
  </div>
</template>

<script setup lang="ts">
import { createChart, IChartApi, CandlestickSeries, LineSeries } from 'lightweight-charts'
import { onMounted, onUnmounted, watch } from 'vue'

interface BarData {
  time: string | number
  open: number
  high: number
  low: number
  close: number
}

interface IndicatorData {
  time: string | number
  value: number
}

const props = defineProps<{
  config: {
    code: string
    height?: string
    realtime?: boolean
  }
  data: BarData[]
}>()

const emit = defineEmits(['timeframe-change', 'indicator-change'])

const chartContainer = ref<HTMLElement>()
let chart: IChartApi | null = null
let candlestickSeries: CandlestickSeries | null = null
let indicatorSeries: LineSeries[] = []

const timeframe = ref('1d')
const indicatorType = ref('MA')

onMounted(() => {
  // 创建图表实例
  chart = createChart(chartContainer.value!, {
    width: chartContainer.value!.clientWidth,
    height: props.config.height ? parseInt(props.config.height) : 500,
    layout: {
      background: { color: '#ffffff' },
      textColor: '#333',
    },
    grid: {
      vertLines: { color: '#f0f0f0' },
      horzLines: { color: '#f0f0f0' },
    },
    crosshair: {
      mode: 1, // 十字准星模式
    },
    rightPriceScale: {
      borderColor: '#cccccc',
    },
    timeScale: {
      borderColor: '#cccccc',
      timeVisible: true,
      secondsVisible: false,
    },
  })

  // 创建K线系列
  candlestickSeries = chart.addCandlestickSeries({
    upColor: '#26a69a',
    downColor: '#ef5350',
    borderVisible: false,
    wickUpColor: '#26a69a',
    wickDownColor: '#ef5350',
  })

  // 加载初始数据
  if (props.data.length > 0) {
    candlestickSeries.setData(props.data)
  }

  // 响应式调整大小
  const resizeObserver = new ResizeObserver(() => {
    if (chart && chartContainer.value) {
      chart.applyOptions({
        width: chartContainer.value.clientWidth,
      })
    }
  })
  resizeObserver.observe(chartContainer.value!)

  // 实时更新
  if (props.config.realtime) {
    startRealtimeUpdate()
  }
})

// 监听数据变化
watch(() => props.data, (newData) => {
  if (candlestickSeries && newData.length > 0) {
    candlestickSeries.setData(newData)
  }
}, { deep: true })

// 添加技术指标
const addIndicator = (type: string) => {
  // 清除现有指标
  indicatorSeries.forEach(s => chart?.removeSeries(s))
  indicatorSeries = []

  // 根据类型添加指标
  if (type === 'MA') {
    // 添加MA均线
    const ma5 = chart?.addLineSeries({ color: '#2196f3', lineWidth: 1 })
    const ma20 = chart?.addLineSeries({ color: '#ff9800', lineWidth: 1 })
    indicatorSeries.push(ma5!, ma20!)
  } else if (type === 'BOLL') {
    // 添加布林带
    const upper = chart?.addLineSeries({ color: '#4caf50', lineWidth: 1, lineStyle: 2 })
    const lower = chart?.addLineSeries({ color: '#4caf50', lineWidth: 1, lineStyle: 2 })
    indicatorSeries.push(upper!, lower!)
  }
}

const handleTimeframeChange = (value: string) => {
  emit('timeframe-change', value)
}

const handleIndicatorChange = (value: string) => {
  addIndicator(value)
  emit('indicator-change', value)
}

const handleReset = () => {
  chart?.timeScale().fitContent()
}

const handleRefresh = () => {
  // 触发数据刷新
  emit('timeframe-change', timeframe.value)
}

const startRealtimeUpdate = () => {
  // WebSocket实时更新逻辑
}

onUnmounted(() => {
  if (chart) {
    chart.remove()
  }
})
</script>
```

#### NetValueChart.vue - 净值曲线图组件

```vue
<template>
  <div class="bg-white rounded-lg shadow-sm p-4">
    <!-- 工具栏 -->
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-base font-medium text-gray-900">{{ config.title || '净值曲线' }}</h3>
      <div class="flex items-center space-x-2">
        <a-checkbox v-model:checked="showBenchmark">显示基准</a-checkbox>
        <a-button size="small" @click="handleReset">重置</a-button>
      </div>
    </div>

    <!-- 图表容器 -->
    <div ref="chartContainer" class="w-full" :style="{ height: config.height || '400px' }"></div>
  </div>
</template>

<script setup lang="ts">
import * as echarts from 'echarts'
import { onMounted, onUnmounted, watch } from 'vue'

interface NetValueData {
  date: string
  value: number
  benchmark?: number
}

const props = defineProps<{
  config: {
    title?: string
    height?: string
  }
  data: NetValueData[]
}>()

const chartContainer = ref<HTMLElement>()
let chart: echarts.ECharts | null = null
const showBenchmark = ref(true)

onMounted(() => {
  chart = echarts.init(chartContainer.value!)
  updateChart()

  window.addEventListener('resize', handleResize)
})

watch(() => props.data, updateChart, { deep: true })
watch(showBenchmark, updateChart)

const updateChart = () => {
  if (!chart || !props.data.length) return

  const dates = props.data.map(d => d.date)
  const values = props.data.map(d => d.value)
  const benchmarks = props.data.map(d => d.benchmark || 0)

  const option: echarts.EChartsOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
    },
    legend: {
      data: ['策略净值', '基准指数'],
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: dates,
    },
    yAxis: {
      type: 'value',
      scale: true,
    },
    series: [
      {
        name: '策略净值',
        type: 'line',
        smooth: true,
        data: values,
        itemStyle: { color: '#1890ff' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(24, 144, 255, 0.3)' },
            { offset: 1, color: 'rgba(24, 144, 255, 0.05)' },
          ]),
        },
      },
      ...(showBenchmark.value ? [{
        name: '基准指数',
        type: 'line',
        smooth: true,
        data: benchmarks,
        itemStyle: { color: '#52c41a' },
        lineStyle: { type: 'dashed' },
      }] : []),
    ],
  }

  chart.setOption(option)
}

const handleReset = () => {
  chart?.dispatchAction({
    type: 'dataZoom',
    start: 0,
    end: 100,
  })
}

const handleResize = () => {
  chart?.resize()
}

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
})
</script>
```

#### PnLChart.vue - 盈亏分析图组件

```vue
<template>
  <div class="bg-white rounded-lg shadow-sm p-4">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-base font-medium text-gray-900">盈亏分析</h3>
      <a-radio-group v-model:value="chartType" button-style="solid" size="small">
        <a-radio-button value="bar">柱状图</a-radio-button>
        <a-radio-button value="pie">饼图</a-radio-button>
      </a-radio-group>
    </div>

    <div ref="chartContainer" class="w-full" style="height: 350px"></div>
  </div>
</template>

<script setup lang="ts">
import * as echarts from 'echarts'
import { onMounted, onUnmounted, watch } from 'vue'

interface PnLData {
  symbol: string
  pnl: number
  count: number
}

const props = defineProps<{
  data: PnLData[]
}>()

const chartContainer = ref<HTMLElement>()
let chart: echarts.ECharts | null = null
const chartType = ref<'bar' | 'pie'>('bar')

onMounted(() => {
  chart = echarts.init(chartContainer.value!)
  updateChart()
  window.addEventListener('resize', handleResize)
})

watch(() => props.data, updateChart, { deep: true })
watch(chartType, updateChart)

const updateChart = () => {
  if (!chart || !props.data.length) return

  const symbols = props.data.map(d => d.symbol)
  const pnls = props.data.map(d => d.pnl)
  const colors = props.data.map(d => d.pnl >= 0 ? '#52c41a' : '#ff4d4f')

  let option: echarts.EChartsOption

  if (chartType.value === 'bar') {
    option = {
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
      },
      grid: {
        left: '3%',
        right: '4%',
        bottom: '3%',
        containLabel: true,
      },
      xAxis: {
        type: 'category',
        data: symbols,
        axisLabel: { interval: 0, rotate: 45 },
      },
      yAxis: {
        type: 'value',
        axisLabel: { formatter: '{value}' },
      },
      series: [{
        type: 'bar',
        data: pnls.map((pnl, i) => ({
          value: pnl,
          itemStyle: { color: colors[i] },
        })),
        label: {
          show: true,
          position: 'top',
          formatter: (params: any) => params.value.toFixed(2),
        },
      }],
    }
  } else {
    option = {
      tooltip: {
        trigger: 'item',
        formatter: '{b}: {c} ({d}%)',
      },
      legend: {
        orient: 'vertical',
        right: '10%',
      },
      series: [{
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 10,
          borderColor: '#fff',
          borderWidth: 2,
        },
        label: { show: false },
        data: props.data.map((d, i) => ({
          name: d.symbol,
          value: Math.abs(d.pnl),
          itemStyle: { color: colors[i] },
        })),
      }],
    }
  }

  chart.setOption(option, true)
}

const handleResize = () => chart?.resize()

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
})
</script>
```

#### ArenaRanking.vue - Portfolio竞技场对比组件

```vue
<template>
  <div class="bg-white rounded-lg shadow-sm p-6">
    <!-- 标题 -->
    <div class="flex items-center justify-between mb-6">
      <div class="flex items-center space-x-3">
        <span class="text-3xl">🏆</span>
        <h2 class="text-xl font-bold text-gray-900">Portfolio 竞技场</h2>
      </div>
      <div class="flex items-center space-x-3">
        <!-- 时间范围选择 -->
        <a-radio-group v-model:value="timeRange" size="small" @change="handleTimeRangeChange">
          <a-radio-button value="7d">近7天</a-radio-button>
          <a-radio-button value="30d">近30天</a-radio-button>
          <a-radio-button value="90d">近90天</a-radio-button>
          <a-radio-button value="1y">近1年</a-radio-button>
        </a-radio-group>
        <!-- 选择Portfolio按钮 -->
        <a-button size="small" @click="handleSelectPortfolios">
          <PlusOutlined /> 添加Portfolio
        </a-button>
      </div>
    </div>

    <!-- 已选择的Portfolio标签 -->
    <div class="flex items-center space-x-2 mb-4">
      <span class="text-sm text-gray-500">已选择:</span>
      <a-tag
        v-for="p in selectedPortfolios"
        :key="p.uuid"
        :color="p.color"
        closable
        @close="handleRemove(p.uuid)"
      >
        {{ p.name }}
      </a-tag>
      <span v-if="selectedPortfolios.length === 0" class="text-sm text-gray-400">
        请添加Portfolio进行对比
      </span>
    </div>

    <!-- 对比图表区域 -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <!-- 左侧: 净值对比曲线图 -->
      <div class="lg:col-span-2">
        <div ref="chartContainer" class="w-full" style="height: 400px"></div>
      </div>

      <!-- 右侧: 统计指标对比 -->
      <div class="space-y-4">
        <div class="bg-gray-50 rounded-lg p-4">
          <h4 class="text-sm font-medium text-gray-700 mb-3">收益率排名</h4>
          <div class="space-y-2">
            <div
              v-for="(item, index) in returnRanking"
              :key="item.uuid"
              class="flex items-center justify-between"
            >
              <div class="flex items-center space-x-2">
                <span class="text-lg">{{ ['🥇', '🥈', '🥉'][index] || '' }}</span>
                <a-tag :color="item.color" size="small">{{ item.name }}</a-tag>
              </div>
              <span
                class="font-semibold"
                :class="item.return >= 0 ? 'text-red-500' : 'text-green-500'"
              >
                {{ item.return >= 0 ? '+' : '' }}{{ item.return.toFixed(2) }}%
              </span>
            </div>
          </div>
        </div>

        <div class="bg-gray-50 rounded-lg p-4">
          <h4 class="text-sm font-medium text-gray-700 mb-3">夏普比率</h4>
          <div class="space-y-2">
            <div
              v-for="item in sharpeRanking"
              :key="item.uuid"
              class="flex items-center justify-between"
            >
              <a-tag :color="item.color" size="small">{{ item.name }}</a-tag>
              <span class="font-semibold text-gray-900">{{ item.sharpe.toFixed(2) }}</span>
            </div>
          </div>
        </div>

        <div class="bg-gray-50 rounded-lg p-4">
          <h4 class="text-sm font-medium text-gray-700 mb-3">最大回撤</h4>
          <div class="space-y-2">
            <div
              v-for="item in drawdownRanking"
              :key="item.uuid"
              class="flex items-center justify-between"
            >
              <a-tag :color="item.color" size="small">{{ item.name }}</a-tag>
              <span class="font-semibold text-green-500">{{ item.maxDrawdown.toFixed(2) }}%</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Portfolio选择对话框 -->
    <a-modal
      v-model:open="selectModalVisible"
      title="选择Portfolio进行对比"
      width="600px"
      @ok="handleConfirmSelection"
    >
      <div class="space-y-2 max-h-96 overflow-y-auto">
        <div
          v-for="p in availablePortfolios"
          :key="p.uuid"
          class="flex items-center justify-between p-3 border rounded hover:bg-gray-50"
        >
          <div class="flex items-center space-x-3">
            <a-checkbox
              :checked="isSelected(p.uuid)"
              @change="toggleSelection(p.uuid)"
            />
            <span class="font-medium">{{ p.name }}</span>
          </div>
          <span class="text-sm text-gray-500">{{ p.return }}%</span>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'
import { PlusOutlined } from '@ant-design/icons-vue'
import { arenaApi } from '@/api'

interface Portfolio {
  uuid: string
  name: string
  return: number
  sharpe: number
  maxDrawdown: number
  color: string
}

interface NetValueData {
  date: string
  values: Record<string, number>
}

const props = defineProps<{
  defaultPortfolios?: string[]
}>()

const timeRange = ref('30d')
const selectedPortfolios = ref<Portfolio[]>([])
const availablePortfolios = ref<Portfolio[]>([])
const netValueData = ref<NetValueData | null>(null)
const selectModalVisible = ref(false)

const chartContainer = ref<HTMLElement>()
let chart: echarts.ECharts | null = null

// 预定义颜色
const colors = [
  '#1890ff', '#52c41a', '#faad14', '#f5222d', '#722ed1',
  '#13c2c2', '#eb2f96', '#fa8c16', '#a0d911', '#2f54eb'
]

// 收益率排名
const returnRanking = computed(() => {
  return [...selectedPortfolios.value].sort((a, b) => b.return - a.return)
})

// 夏普比率排名
const sharpeRanking = computed(() => {
  return [...selectedPortfolios.value].sort((a, b) => b.sharpe - a.sharpe)
})

// 最大回撤排名（越小越好）
const drawdownRanking = computed(() => {
  return [...selectedPortfolios.value].sort((a, b) => a.maxDrawdown - b.maxDrawdown)
})

// 初始化图表
const initChart = () => {
  chart = echarts.init(chartContainer.value!)
  updateChart()
  window.addEventListener('resize', handleResize)
}

// 更新图表
const updateChart = () => {
  if (!chart || !netValueData.value || selectedPortfolios.value.length === 0) return

  const dates = netValueData.value.date
  const series = selectedPortfolios.value.map(p => ({
    name: p.name,
    type: 'line',
    smooth: true,
    data: dates.map(d => netValueData.value!.values[d]?.[p.uuid] || null),
    itemStyle: { color: p.color },
    lineStyle: { width: 2 },
  }))

  const option: echarts.EChartsOption = {
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'cross' },
    },
    legend: {
      data: selectedPortfolios.value.map(p => p.name),
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true,
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: dates,
    },
    yAxis: {
      type: 'value',
      scale: true,
      axisLabel: { formatter: '{value}' },
    },
    series,
  }

  chart.setOption(option)
}

const handleResize = () => chart?.resize()

const handleTimeRangeChange = () => {
  fetchData()
}

const handleSelectPortfolios = () => {
  selectModalVisible.value = true
}

const isSelected = (uuid: string) => {
  return selectedPortfolios.value.some(p => p.uuid === uuid)
}

const toggleSelection = (uuid: string) => {
  const index = selectedPortfolios.value.findIndex(p => p.uuid === uuid)
  if (index > -1) {
    selectedPortfolios.value.splice(index, 1)
  } else if (selectedPortfolios.value.length < 8) {
    const p = availablePortfolios.value.find(p => p.uuid === uuid)
    if (p) selectedPortfolios.value.push(p)
  }
}

const handleRemove = (uuid: string) => {
  const index = selectedPortfolios.value.findIndex(p => p.uuid === uuid)
  if (index > -1) selectedPortfolios.value.splice(index, 1)
}

const handleConfirmSelection = () => {
  selectModalVisible.value = false
  updateChart()
}

const fetchData = async () => {
  const uuids = selectedPortfolios.value.map(p => p.uuid)
  if (uuids.length === 0) return

  // 获取对比数据
  const data = await arenaApi.getComparison({
    uuids,
    timeRange: timeRange.value,
  })
  netValueData.value = data.netValues
}

onMounted(async () => {
  // 加载可用的Portfolio列表
  const list = await arenaApi.getPortfolioList()
  availablePortfolios.value = list.items.map((p, i) => ({
    ...p,
    color: colors[i % colors.length],
  }))

  // 默认选择前5个
  if (props.defaultPortfolios) {
    selectedPortfolios.value = props.defaultPortfolios
      .map(uuid => availablePortfolios.value.find(p => p.uuid === uuid))
      .filter(Boolean) as Portfolio[]
  } else {
    selectedPortfolios.value = availablePortfolios.value.slice(0, 5)
  }

  initChart()
  await fetchData()
})

watch(selectedPortfolios, () => {
  updateChart()
}, { deep: true })

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
})
</script>
```

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer)
})
</script>
```

#### SignalStream.vue - 实时信号流组件

```vue
<template>
  <div class="bg-white rounded-lg shadow-sm p-4 h-full flex flex-col">
    <!-- 标题 -->
    <div class="flex items-center justify-between mb-4">
      <div class="flex items-center space-x-2">
        <span class="text-xl">📈</span>
        <h3 class="text-base font-semibold text-gray-900">实时信号流</h3>
        <a-badge :count="unreadCount" :overflow-count="99" />
      </div>
      <a-button size="small" type="link" @click="handleViewAll">查看全部 →</a-button>
    </div>

    <!-- 信号列表 -->
    <div class="flex-1 overflow-y-auto space-y-3">
      <div
        v-for="signal in signals"
        :key="signal.id"
        class="border rounded-lg p-3 hover:shadow-md transition-shadow cursor-pointer"
        :class="{
          'border-green-200 bg-green-50': signal.direction === 'LONG',
          'border-red-200 bg-red-50': signal.direction === 'SHORT',
        }"
        @click="handleViewSignal(signal)"
      >
        <div class="flex items-start justify-between">
          <div class="flex-1">
            <!-- 信号头部 -->
            <div class="flex items-center space-x-2 mb-1">
              <span class="text-lg">🔔</span>
              <span class="text-sm font-medium text-gray-900">{{ signal.strategyName }}</span>
              <a-tag :color="signal.direction === 'LONG' ? 'green' : 'red'" size="small">
                {{ signal.direction }}
              </a-tag>
            </div>

            <!-- 信号内容 -->
            <div class="text-xs text-gray-600 space-y-1">
              <p>代码: <span class="font-mono font-medium">{{ signal.code }}</span></p>
              <p>价格: <span :class="signal.change >= 0 ? 'text-red-500' : 'text-green-500'">
                {{ signal.price }} {{ signal.change >= 0 ? '💚' : '🔴' }} {{ signal.change >= 0 ? '+' : '' }}{{ signal.change }}%
              </span></p>
              <p class="text-gray-400">{{ formatTime(signal.timestamp) }}</p>
            </div>
          </div>

          <!-- 操作 -->
          <div class="flex space-x-1">
            <a-button size="small" @click.stop="handleViewSignal(signal)">查看</a-button>
            <a-button size="small" danger @click.stop="handleIgnore(signal)">忽略</a-button>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-if="signals.length === 0" class="text-center text-gray-400 py-8">
        <p>暂无新信号</p>
      </div>
    </div>

    <!-- 连接状态 -->
    <div class="flex items-center justify-between mt-3 pt-3 border-t">
      <span class="text-xs text-gray-500">
        {{ connected ? '🟢 实时连接中' : '🔴 连接断开' }}
      </span>
      <a-button size="small" @click="handleRefresh">刷新</a-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useWebSocket } from '@/composables/useWebSocket'

interface Signal {
  id: string
  strategyName: string
  code: string
  direction: 'LONG' | 'SHORT'
  price: number
  change: number
  timestamp: string
}

const signals = ref<Signal[]>([])
const unreadCount = ref(0)

// WebSocket连接
const { connected, data, connect } = useWebSocket('ws://localhost:8000/ws/signals')

onMounted(() => {
  connect()

  // 监听新信号
  // 这里需要处理WebSocket接收到的数据
})

const formatTime = (timestamp: string) => {
  const date = new Date(timestamp)
  return date.toLocaleTimeString('zh-CN')
}

const handleViewSignal = (signal: Signal) => {
  // 查看信号详情
}

const handleIgnore = (signal: Signal) => {
  // 忽略信号
  const index = signals.value.findIndex(s => s.id === signal.id)
  if (index > -1) {
    signals.value.splice(index, 1)
    unreadCount.value--
  }
}

const handleViewAll = () => {
  // 跳转到信号中心
}

const handleRefresh = () => {
  // 刷新信号列表
}
</script>
```

#### NewsFeed.vue - 最新资讯/通知组件

```vue
<template>
  <div class="bg-white rounded-lg shadow-sm p-4 h-full flex flex-col">
    <!-- 标题 -->
    <div class="flex items-center justify-between mb-4">
      <div class="flex items-center space-x-2">
        <span class="text-xl">📰</span>
        <h3 class="text-base font-semibold text-gray-900">最新资讯</h3>
      </div>
      <a-button size="small" type="link" @click="handleViewAll">查看全部 →</a-button>
    </div>

    <!-- 分类筛选 -->
    <div class="flex space-x-2 mb-3">
      <a-tag
        v-for="cat in categories"
        :key="cat.value"
        :color="selectedCategory === cat.value ? 'blue' : 'default'"
        class="cursor-pointer"
        @click="selectedCategory = cat.value"
      >
        {{ cat.label }}
      </a-tag>
    </div>

    <!-- 资讯列表 -->
    <div class="flex-1 overflow-y-auto space-y-3">
      <div
        v-for="item in filteredNews"
        :key="item.id"
        class="border rounded-lg p-3 hover:shadow-md transition-shadow cursor-pointer"
        @click="handleViewDetail(item)"
      >
        <div class="flex items-start space-x-3">
          <!-- 图标 -->
          <span class="text-2xl">{{ getIcon(item.type) }}</span>

          <div class="flex-1">
            <!-- 标题 -->
            <p class="text-sm font-medium text-gray-900 mb-1">{{ item.title }}</p>

            <!-- 内容 -->
            <p class="text-xs text-gray-600 line-clamp-2">{{ item.content }}</p>

            <!-- 时间 -->
            <p class="text-xs text-gray-400 mt-1">{{ formatTime(item.timestamp) }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

interface News {
  id: string
  type: 'system' | 'warning' | 'sync' | 'info'
  title: string
  content: string
  timestamp: string
}

const categories = [
  { label: '全部', value: 'all' },
  { label: '系统通知', value: 'system' },
  { label: '风险提醒', value: 'warning' },
  { label: '数据同步', value: 'sync' },
]

const selectedCategory = ref('all')
const news = ref<News[]>([])

const filteredNews = computed(() => {
  if (selectedCategory.value === 'all') return news.value
  return news.value.filter(n => n.type === selectedCategory.value)
})

const getIcon = (type: string) => {
  const icons = {
    system: '📢',
    warning: '⚠️',
    sync: '📊',
    info: 'ℹ️',
  }
  return icons[type] || '📌'
}

const formatTime = (timestamp: string) => {
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now.getTime() - date.getTime()
  const minutes = Math.floor(diff / 60000)

  if (minutes < 1) return '刚刚'
  if (minutes < 60) return `${minutes}分钟前`
  if (minutes < 1440) return `${Math.floor(minutes / 60)}小时前`
  return `${Math.floor(minutes / 1440)}天前`
}

const handleViewDetail = (item: News) => {
  // 查看详情
}

const handleViewAll = () => {
  // 查看全部资讯
}
</script>
```

#### MyStats.vue - 我的关键指标组件

```vue
<template>
  <div class="bg-white rounded-lg shadow-sm p-4">
    <div class="flex items-center space-x-2 mb-4">
      <span class="text-xl">📊</span>
      <h3 class="text-base font-semibold text-gray-900">我的关键指标</h3>
    </div>

    <div class="grid grid-cols-4 gap-4">
      <!-- 总资产 -->
      <div class="text-center p-3 bg-blue-50 rounded-lg">
        <p class="text-xs text-gray-500 mb-1">总资产</p>
        <p class="text-xl font-bold text-gray-900">¥{{ stats.totalAsset.toLocaleString() }}</p>
        <p
          class="text-xs mt-1"
          :class="stats.totalAssetChange >= 0 ? 'text-red-500' : 'text-green-500'"
        >
          {{ stats.totalAssetChange >= 0 ? '💚' : '🔴' }} {{ stats.totalAssetChange >= 0 ? '+' : '' }}{{ stats.totalAssetChange }}%
        </p>
      </div>

      <!-- 今日盈亏 -->
      <div class="text-center p-3 bg-green-50 rounded-lg">
        <p class="text-xs text-gray-500 mb-1">今日盈亏</p>
        <p class="text-xl font-bold" :class="stats.todayPnL >= 0 ? 'text-red-500' : 'text-green-500'">
          ¥{{ stats.todayPnL.toLocaleString() }}
        </p>
        <p class="text-xs mt-1 text-gray-500">
          {{ stats.todayPnL >= 0 ? '💚' : '🔴' }} {{ stats.todayPnLPercent >= 0 ? '+' : '' }}{{ stats.todayPnLPercent }}%
        </p>
      </div>

      <!-- 持仓数量 -->
      <div class="text-center p-3 bg-purple-50 rounded-lg">
        <p class="text-xs text-gray-500 mb-1">持仓数量</p>
        <p class="text-xl font-bold text-gray-900">{{ stats.positionCount }}个</p>
        <p class="text-xs mt-1 text-gray-500">{{ stats.marketCount }}个市场</p>
      </div>

      <!-- 运行策略 -->
      <div class="text-center p-3 bg-orange-50 rounded-lg">
        <p class="text-xs text-gray-500 mb-1">运行策略</p>
        <p class="text-xl font-bold text-gray-900">{{ stats.runningStrategies }}个</p>
        <p class="text-xs mt-1">
          {{ stats.online ? '🟢 在线' : '🔴 离线' }}
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { portfolioApi } from '@/api'

interface MyStats {
  totalAsset: number
  totalAssetChange: number
  todayPnL: number
  todayPnLPercent: number
  positionCount: number
  marketCount: number
  runningStrategies: number
  online: boolean
}

const stats = ref<MyStats>({
  totalAsset: 128500,
  totalAssetChange: 2.1,
  todayPnL: 1250,
  todayPnLPercent: 0.98,
  positionCount: 8,
  marketCount: 2,
  runningStrategies: 5,
  online: true,
})

onMounted(async () => {
  // 获取统计数据
  // stats.value = await portfolioApi.getMyStats()
})
</script>
```

#### MonacoEditor.vue - 代码编辑器组件

```vue
<template>
  <div class="h-full flex flex-col bg-white rounded-lg shadow-sm">
    <!-- 工具栏 -->
    <div class="flex items-center justify-between px-4 py-2 border-b border-gray-200">
      <div class="flex items-center space-x-2">
        <span class="text-sm font-medium text-gray-700">{{ config.language }}</span>
        <a-tag v-if="config.modified" color="orange">已修改</a-tag>
      </div>

      <div class="flex space-x-2">
        <a-button size="small" @click="handleFormat">格式化</a-button>
        <a-button size="small" @click="handleReset">重置</a-button>
        <a-button size="small" type="primary" @click="handleSave">保存</a-button>
      </div>
    </div>

    <!-- 编辑器容器 -->
    <div ref="editorContainer" class="flex-1 overflow-hidden"></div>
  </div>
</template>

<script setup lang="ts">
import * as monaco from 'monaco-editor'

const props = defineProps<{
  config: {
    language: string
    value: string
    readOnly?: boolean
    modified?: boolean
  }
}>()

const emit = defineEmits(['save', 'reset', 'change'])

const editorContainer = ref<HTMLElement>()
let editor: monaco.editor.IStandaloneCodeEditor | null = null

onMounted(() => {
  editor = monaco.editor.create(editorContainer.value!, {
    value: props.config.value,
    language: props.config.language,
    theme: 'vs-light',
    automaticLayout: true,
    minimap: { enabled: false },
    fontSize: 14,
    lineNumbers: 'on',
    readOnly: props.config.readOnly || false,
  })

  editor.onDidChangeModelContent(() => {
    emit('change', editor!.getValue())
  })
})

const handleFormat = () => editor?.getAction('editor.action.formatDocument')?.run()
const handleReset = () => emit('reset')
const handleSave = () => emit('save', editor?.getValue())

onBeforeUnmount(() => editor?.dispose())
</script>
```

#### NodeGraphEditor.vue - 节点图编辑器组件

```vue
<template>
  <div class="h-full bg-gray-50 rounded-lg overflow-hidden">
    <!-- 画布 -->
    <div ref="canvasRef" class="w-full h-full relative">
      <!-- SVG连接线 -->
      <svg class="absolute inset-0 w-full h-full pointer-events-none">
        <path
          v-for="connection in connections"
          :key="`${connection.source}-${connection.target}`"
          :d="getConnectionPath(connection)"
          stroke="#1890ff"
          stroke-width="2"
          fill="none"
        />
      </svg>

      <!-- 节点 -->
      <div
        v-for="node in nodes"
        :key="node.id"
        class="absolute bg-white rounded-lg shadow-md p-4 min-w-48 cursor-move border-2"
        :class="{
          'border-blue-500': node.type === 'STRATEGY',
          'border-green-500': node.type === 'SELECTOR',
          'border-purple-500': node.type === 'SIZER',
          'border-orange-500': node.type === 'RISKMANAGER',
          'border-gray-300': selectedNode === node.id ? 'border-blue-500' : 'border-transparent',
        }"
        :style="{ left: `${node.x}px`, top: `${node.y}px` }"
        @mousedown="startDrag(node, $event)"
        @click="selectNode(node.id)"
      >
        <div class="flex items-center justify-between mb-2">
          <span class="font-medium text-gray-900">{{ node.label }}</span>
          <a-tag :color="getTypeColor(node.type)">{{ node.type }}</a-tag>
        </div>

        <!-- 输入端口 -->
        <div
          v-if="node.type !== 'SELECTOR'"
          class="absolute -left-3 top-1/2 w-3 h-3 bg-green-500 rounded-full"
        />

        <!-- 输出端口 -->
        <div
          class="absolute -right-3 top-1/2 w-3 h-3 bg-blue-500 rounded-full"
          @mousedown="startConnection(node.id, $event)"
        />
      </div>
    </div>

    <!-- 工具栏 -->
    <div class="absolute bottom-4 left-1/2 -translate-x-1/2 bg-white rounded-lg shadow-md px-4 py-2">
      <a-space>
        <a-button size="small" @click="addNode">添加节点</a-button>
        <a-button size="small" @click="deleteNode">删除节点</a-button>
        <a-button size="small" type="primary" @click="saveGraph">保存</a-button>
      </a-space>
    </div>
  </div>
</template>

<script setup lang="ts">
interface Node {
  id: string
  type: 'STRATEGY' | 'SELECTOR' | 'SIZER' | 'RISKMANAGER'
  label: string
  x: number
  y: number
}

const nodes = ref<Node[]>([])
const connections = ref<Array<{ source: string; target: string }>>([])
const selectedNode = ref<string | null>(null)

const getTypeColor = (type: string) => {
  const colors = {
    STRATEGY: 'blue',
    SELECTOR: 'green',
    SIZER: 'purple',
    RISKMANAGER: 'orange',
  }
  return colors[type] || 'default'
}

const getConnectionPath = (conn: any) => {
  // 计算贝塞尔曲线路径
  const source = nodes.value.find(n => n.id === conn.source)
  const target = nodes.value.find(n => n.id === conn.target)
  if (!source || !target) return ''

  const x1 = source.x + 192  // 节点宽度
  const y1 = source.y + 40   // 节点高度的一半
  const x2 = target.x
  const y2 = target.y + 40

  return `M ${x1} ${y1} C ${x1 + 50} ${y1}, ${x2 - 50} ${y2}, ${x2} ${y2}`
}

const emit = defineEmits(['save', 'node-select'])
</script>
```

### 1.5.5 Composables设计规范

#### useTable.ts - 表格逻辑复用

```typescript
import { ref, reactive } from 'vue'

interface UseTableOptions<T> {
  fetchFn: (params: any) => Promise<{ data: T[]; total: number }>
  defaultPageSize?: number
  immediate?: boolean
}

export function useTable<T = any>(options: UseTableOptions<T>) {
  const loading = ref(false)
  const data = ref<T[]>([])
  const pagination = reactive({
    current: 1,
    pageSize: options.defaultPageSize || 20,
    total: 0,
  })

  const fetch = async (params?: any) => {
    loading.value = true
    try {
      const result = await options.fetchFn({
        page: pagination.current,
        pageSize: pagination.pageSize,
        ...params,
      })
      data.value = result.data
      pagination.total = result.total
    } finally {
      loading.value = false
    }
  }

  const refresh = () => fetch()
  const reset = () => {
    pagination.current = 1
    fetch()
  }

  if (options.immediate !== false) {
    fetch()
  }

  return {
    loading,
    data,
    pagination,
    fetch,
    refresh,
    reset,
  }
}
```

#### useWebSocket.ts - WebSocket连接管理

```typescript
import { ref, onUnmounted } from 'vue'

export function useWebSocket(url: string) {
  const connected = ref(false)
  const data = ref<any>(null)
  const error = ref<Error | null>(null)

  let ws: WebSocket | null = null
  let reconnectTimer: number | null = null

  const connect = () => {
    ws = new WebSocket(url)

    ws.onopen = () => {
      connected.value = true
      error.value = null
    }

    ws.onmessage = (event) => {
      data.value = JSON.parse(event.data)
    }

    ws.onerror = (event) => {
      error.value = new Error('WebSocket error')
    }

    ws.onclose = () => {
      connected.value = false
      // 自动重连
      reconnectTimer = window.setTimeout(() => connect(), 3000)
    }
  }

  const send = (message: any) => {
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(message))
    }
  }

  const close = () => {
    if (reconnectTimer) clearTimeout(reconnectTimer)
    ws?.close()
  }

  onUnmounted(close)

  return {
    connected,
    data,
    error,
    connect,
    send,
    close,
  }
}
```

#### usePagination.ts - 分页逻辑复用

```typescript
import { reactive, computed } from 'vue'

export function usePagination(initialPageSize = 20) {
  const state = reactive({
    current: 1,
    pageSize: initialPageSize,
    total: 0,
  })

  const offset = computed(() => (state.current - 1) * state.pageSize)
  const totalPages = computed(() => Math.ceil(state.total / state.pageSize))

  const setPage = (page: number) => {
    state.current = Math.max(1, Math.min(page, totalPages.value))
  }

  const setPageSize = (size: number) => {
    state.pageSize = size
    state.current = 1
  }

  const setTotal = (total: number) => {
    state.total = total
  }

  const reset = () => {
    state.current = 1
    state.pageSize = initialPageSize
  }

  return {
    state,
    offset,
    totalPages,
    setPage,
    setPageSize,
    setTotal,
    reset,
  }
}
```

### 1.5.6 API调用封装规范 ⭐

#### 核心原则

**禁止在页面组件中直接使用 fetch/axios**

所有API调用必须通过封装的 API 函数进行，实现统一的错误处理、请求拦截、响应转换。

#### 目录结构

```
api/
├── index.ts                 # API入口，导出所有API模块
├── request.ts               # 基础请求封装(axios/fetch wrapper)
├── types.ts                 # API通用类型定义
├── modules/                 # API模块(按业务划分)
│   ├── stockinfo.ts         # 股票信息API
│   ├── bars.ts              # K线数据API
│   ├── portfolio.ts         # Portfolio API
│   ├── backtest.ts          # 回测API
│   ├── components.ts        # 组件管理API
│   ├── notifications.ts     # 通知API
│   └── users.ts             # 用户管理API
└── websocket.ts             # WebSocket API封装
```

#### request.ts - 基础请求封装

```typescript
import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'
import { message } from 'ant-design-vue'

// API响应标准格式
interface ApiResponse<T = any> {
  code: number
  message: string
  data: T
}

// 分页响应格式
interface PageResponse<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
}

// 创建axios实例
const service: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
service.interceptors.request.use(
  (config) => {
    // 添加认证token
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
service.interceptors.response.use(
  (response: AxiosResponse<ApiResponse>) => {
    const { code, message: msg, data } = response.data

    // 成功响应
    if (code === 0 || code === 200) {
      return data
    }

    // 业务错误
    message.error(msg || '请求失败')
    return Promise.reject(new Error(msg))
  },
  (error) => {
    // HTTP错误
    if (error.response) {
      const { status } = error.response

      switch (status) {
        case 401:
          message.error('未授权，请重新登录')
          // 跳转登录页
          window.location.href = '/login'
          break
        case 403:
          message.error('拒绝访问')
          break
        case 404:
          message.error('请求资源不存在')
          break
        case 500:
          message.error('服务器错误')
          break
        default:
          message.error(error.response.data?.message || '请求失败')
      }
    } else if (error.request) {
      message.error('网络错误，请检查网络连接')
    } else {
      message.error('请求配置错误')
    }

    return Promise.reject(error)
  }
)

// 通用请求方法
export const request = {
  get<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return service.get(url, config)
  },

  post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    return service.post(url, data, config)
  },

  put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    return service.put(url, data, config)
  },

  delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return service.delete(url, config)
  },

  // 分页查询
  getPage<T = any>(url: string, params?: any): Promise<PageResponse<T>> {
    return service.get(url, { params })
  },
}

export default service
```

#### modules/stockinfo.ts - 股票信息API模块

```typescript
import { request } from '../request'
import type { PageResponse } from '../types'

// 股票信息类型
export interface StockInfo {
  code: string
  name: string
  market: string
  industry: string
  listDate: string
  updateTime: string
}

// 查询参数类型
export interface StockInfoQuery {
  code?: string
  name?: string
  market?: string
  page?: number
  pageSize?: number
}

/**
 * 股票信息API模块
 */
export const stockInfoApi = {
  /**
   * 查询股票列表(分页)
   */
  getList: (params: StockInfoQuery): Promise<PageResponse<StockInfo>> => {
    return request.getPage('/data/stockinfo', params)
  },

  /**
   * 根据代码查询单个股票
   */
  getByCode: (code: string): Promise<StockInfo> => {
    return request.get(`/data/stockinfo/${code}`)
  },

  /**
   * 同步股票信息
   */
  sync: (full: boolean = false): Promise<void> => {
    return request.post('/data/stockinfo/sync', { full })
  },

  /**
   * 批量更新
   */
  batchUpdate: (codes: string[]): Promise<void> => {
    return request.post('/data/stockinfo/batch-update', { codes })
  },

  /**
   * 导出股票信息
   */
  export: (params: StockInfoQuery): Promise<Blob> => {
    return request.get('/data/stockinfo/export', {
      responseType: 'blob',
      params,
    })
  },
}
```

#### modules/components.ts - 组件管理API模块

```typescript
import { request } from '../request'
import type { PageResponse } from '../types'

// 组件类型
export type ComponentType = 'STRATEGY' | 'SELECTOR' | 'SIZER' | 'RISKMANAGER' | 'ANALYZER'

// 组件信息
export interface ComponentInfo {
  uuid: string
  name: string
  type: ComponentType
  code: string
  isBuiltIn: boolean
  createdAt: string
  updatedAt: string
}

// 组件详情
export interface ComponentDetail extends ComponentInfo {
  code: string
  version: number
  description?: string
}

/**
 * 组件管理API模块
 */
export const componentApi = {
  /**
   * 获取组件列表(分页)
   */
  getList: (params: {
    type?: ComponentType
    keyword?: string
    page?: number
    pageSize?: number
  }): Promise<PageResponse<ComponentInfo>> => {
    return request.getPage('/components', params)
  },

  /**
   * 获取组件详情
   */
  getDetail: (uuid: string): Promise<ComponentDetail> => {
    return request.get(`/components/${uuid}`)
  },

  /**
   * 创建自定义组件
   */
  create: (data: {
    name: string
    type: ComponentType
    code: string
    description?: string
  }): Promise<ComponentDetail> => {
    return request.post('/components', data)
  },

  /**
   * 更新组件代码
   */
  update: (uuid: string, data: {
    name?: string
    code?: string
    description?: string
  }): Promise<void> => {
    return request.put(`/components/${uuid}`, data)
  },

  /**
   * 删除组件
   */
  delete: (uuid: string): Promise<void> => {
    return request.delete(`/components/${uuid}`)
  },

  /**
   * 复制预置组件
   */
  copy: (uuid: string, newName: string): Promise<ComponentDetail> => {
    return request.post(`/components/${uuid}/copy`, { name: newName })
  },

  /**
   * 测试组件
   */
  test: (uuid: string, testData: any): Promise<{
    success: boolean
    output?: any
    error?: string
  }> => {
    return request.post(`/components/${uuid}/test`, { testData })
  },

  /**
   * 获取组件版本历史
   */
  getHistory: (uuid: string): Promise<Array<{
    version: number
    code: string
    createdAt: string
  }>> => {
    return request.get(`/components/${uuid}/history`)
  },
}
```

#### modules/portfolio.ts - Portfolio API模块

```typescript
import { request } from '../request'
import type { PageResponse } from '../types'

// Portfolio节点
export interface PortfolioNode {
  id: string
  type: 'STRATEGY' | 'SELECTOR' | 'SIZER' | 'RISKMANAGER'
  componentId: string
  x: number
  y: number
}

// Portfolio连接
export interface PortfolioConnection {
  id: string
  sourceId: string
  targetId: string
}

// Portfolio配置
export interface PortfolioConfig {
  uuid: string
  name: string
  description?: string
  mode: 'LIVE' | 'HISTORIC'
  nodes: PortfolioNode[]
  connections: PortfolioConnection[]
  initialCash: number
  createdAt: string
  updatedAt: string
}

/**
 * Portfolio API模块
 */
export const portfolioApi = {
  /**
   * 获取Portfolio列表
   */
  getList: (params?: {
    keyword?: string
    mode?: string
    page?: number
    pageSize?: number
  }): Promise<PageResponse<PortfolioConfig>> => {
    return request.getPage('/portfolio', params)
  },

  /**
   * 获取Portfolio详情
   */
  getDetail: (uuid: string): Promise<PortfolioConfig> => {
    return request.get(`/portfolio/${uuid}`)
  },

  /**
   * 创建Portfolio
   */
  create: (data: {
    name: string
    description?: string
    mode: 'LIVE' | 'HISTORIC'
    nodes: PortfolioNode[]
    connections: PortfolioConnection[]
    initialCash: number
  }): Promise<PortfolioConfig> => {
    return request.post('/portfolio', data)
  },

  /**
   * 更新Portfolio
   */
  update: (uuid: string, data: Partial<PortfolioConfig>): Promise<void> => {
    return request.put(`/portfolio/${uuid}`, data)
  },

  /**
   * 删除Portfolio
   */
  delete: (uuid: string): Promise<void> => {
    return request.delete(`/portfolio/${uuid}`)
  },

  /**
   * 验证Portfolio配置
   */
  validate: (config: PortfolioConfig): Promise<{
    valid: boolean
    errors?: string[]
  }> => {
    return request.post('/portfolio/validate', config)
  },
}
```

#### modules/arena.ts - 竞技场API模块

```typescript
import { request } from '../request'
import type { PageResponse } from '../types'

// Portfolio条目
export interface PortfolioItem {
  uuid: string
  name: string
  return: number
  sharpe: number
  maxDrawdown: number
  color: string
}

// 信号条目
export interface Signal {
  id: string
  strategyName: string
  portfolioId: string
  code: string
  direction: 'LONG' | 'SHORT'
  price: number
  change: number
  timestamp: string
}

// 资讯条目
export interface News {
  id: string
  type: 'system' | 'warning' | 'sync' | 'info'
  title: string
  content: string
  timestamp: string
  read: boolean
}

/**
 * 竞技场API模块
 */
export const arenaApi = {
  /**
   * 获取Portfolio列表
   */
  getPortfolioList: (): Promise<{ items: PortfolioItem[] }> => {
    return request.get('/arena/portfolios')
  },

  /**
   * 获取Portfolio对比数据（净值曲线）
   */
  getComparison: (params: {
    uuids: string[]
    timeRange: '7d' | '30d' | '90d' | '1y'
  }): Promise<{
    netValues: {
      date: string[]
      values: Record<string, number>
    }
    statistics: Array<{
      uuid: string
      name: string
      return: number
      sharpe: number
      maxDrawdown: number
      winRate: number
    }>
  }> => {
    return request.post('/arena/comparison', params)
  },

  /**
   * 获取最新信号
   */
  getSignals: (params?: {
    limit?: number
    portfolioId?: string
  }): Promise<{ items: Signal[] }> => {
    return request.get('/arena/signals', { params })
  },

  /**
   * 获取最新资讯/通知
   */
  getNews: (params?: {
    limit?: number
    type?: string
  }): Promise<{ items: News[] }> => {
    return request.get('/arena/news', { params })
  },

  /**
   * 标记资讯为已读
   */
  markRead: (id: string): Promise<void> => {
    return request.post(`/arena/news/${id}/read`)
  },

  /**
   * 获取我的统计数据
   */
  getMyStats: (): Promise<{
    totalAsset: number
    totalAssetChange: number
    todayPnL: number
    todayPnLPercent: number
    positionCount: number
    marketCount: number
    runningStrategies: number
    online: boolean
  }> => {
    return request.get('/arena/mystats')
  },
}
```

#### index.ts - API统一导出

```typescript
// 统一导出所有API模块
export { stockInfoApi } from './modules/stockinfo'
export { componentApi } from './modules/components'
export { portfolioApi } from './modules/portfolio'
export { backtestApi } from './modules/backtest'
export { barsApi } from './modules/bars'
export { userApi } from './modules/users'
export { notificationApi } from './modules/notifications'
export { arenaApi } from './modules/arena'

// 导出类型
export type * from './types'
export type * from './modules/stockinfo'
export type * from './modules/components'
export type * from './modules/portfolio'
export type * from './modules/arena'
```

#### 页面中使用API

```vue
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { stockInfoApi } from '@/api'
import type { StockInfo, StockInfoQuery } from '@/api'

// ✅ 正确: 使用封装的API函数
const fetchStocks = async (params: StockInfoQuery) => {
  try {
    const result = await stockInfoApi.getList(params)
    stocks.value = result.items
    total.value = result.total
  } catch (error) {
    // 错误已在request拦截器中统一处理
    console.error('获取股票列表失败', error)
  }
}

// ❌ 错误: 禁止在页面中直接使用fetch/axios
// const fetchStocksBad = async () => {
//   const response = await fetch('/api/data/stockinfo')  // 禁止!
//   const data = await response.json()
// }

// 同步股票信息
const handleSync = async () => {
  await stockInfoApi.sync(true)
  fetchStocks({ page: 1, pageSize: 20 })
}

onMounted(() => {
  fetchStocks({ page: 1, pageSize: 20 })
})
</script>
```

### 1.5.7 完整Layout设计示例

#### DashboardLayout.vue - 仪表盘布局

```vue
<template>
  <div class="flex h-screen bg-gray-50">
    <!-- 侧边栏 -->
    <aside class="w-64 bg-white border-r border-gray-200 flex flex-col">
      <!-- Logo -->
      <div class="h-16 flex items-center px-6 border-b border-gray-200">
        <h1 class="text-xl font-bold text-primary">Ginkgo</h1>
      </div>

      <!-- 导航菜单 -->
      <nav class="flex-1 overflow-y-auto py-4">
        <a-menu
          v-model:selectedKeys="selectedKeys"
          mode="inline"
          :items="menuItems"
          @click="handleMenuClick"
        />
      </nav>

      <!-- 用户信息 -->
      <div class="p-4 border-t border-gray-200">
        <div class="flex items-center space-x-3">
          <a-avatar>U</a-avatar>
          <div class="flex-1">
            <p class="text-sm font-medium text-gray-900">Admin</p>
            <p class="text-xs text-gray-500">在线</p>
          </div>
        </div>
      </div>
    </aside>

    <!-- 主内容区 -->
    <main class="flex-1 flex flex-col overflow-hidden">
      <!-- 顶部栏 -->
      <header class="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-6">
        <div class="flex items-center space-x-4">
          <a-breadcrumb>
            <a-breadcrumb-item v-for="item in breadcrumbs" :key="item.path">
              {{ item.title }}
            </a-breadcrumb-item>
          </a-breadcrumb>
        </div>

        <div class="flex items-center space-x-4">
          <a-badge :count="notificationCount">
            <BellOutlined class="text-xl text-gray-600" />
          </a-badge>
          <a-button @click="handleLogout">退出</a-button>
        </div>
      </header>

      <!-- 页面内容 -->
      <div class="flex-1 overflow-auto p-6">
        <slot />
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { BellOutlined } from '@ant-design/icons-vue'

const router = useRouter()
const route = useRoute()

const selectedKeys = ref([route.path])
const notificationCount = ref(3)

const menuItems = [
  { key: '/dashboard', icon: () => h(DashboardOutlined), label: '仪表盘' },
  { key: '/backtest', icon: () => h(ExperimentOutlined), label: '策略回测' },
  { key: '/components', icon: () => h(AppstoreOutlined), label: '组件管理' },
  { key: '/data', icon: () => h(DatabaseOutlined), label: '数据管理' },
  { key: '/settings', icon: () => h(SettingOutlined), label: '系统设置' },
]

const breadcrumbs = computed(() => {
  // 根据当前路由生成面包屑
  return [{ title: '首页', path: '/' }, { title: '仪表盘', path: '/dashboard' }]
})

const handleMenuClick = ({ key }: { key: string }) => {
  router.push(key)
}

const handleLogout = () => {
  // 登出逻辑
}
</script>
```

#### ComponentLayout.vue - 组件管理布局

```vue
<template>
  <div class="h-screen flex bg-gray-50">
    <!-- 左侧: 组件分类导航 -->
    <aside class="w-64 bg-white border-r border-gray-200">
      <div class="p-4 border-b border-gray-200">
        <a-input-search placeholder="搜索组件" />
      </div>

      <a-menu
        v-model:selectedKeys="selectedCategory"
        mode="inline"
        @click="handleCategoryChange"
      >
        <a-menu-item key="all">
          <span>全部组件</span>
          <a-badge :count="componentCount.all" class="ml-2" />
        </a-menu-item>
        <a-menu-item key="STRATEGY">
          <span>策略组件</span>
          <a-badge :count="componentCount.STRATEGY" class="ml-2" />
        </a-menu-item>
        <a-menu-item key="SELECTOR">
          <span>选股器</span>
          <a-badge :count="componentCount.SELECTOR" class="ml-2" />
        </a-menu-item>
        <a-menu-item key="SIZER">
          <span>仓位管理</span>
          <a-badge :count="componentCount.SIZER" class="ml-2" />
        </a-menu-item>
        <a-menu-item key="RISKMANAGER">
          <span>风控组件</span>
          <a-badge :count="componentCount.RISKMANAGER" class="ml-2" />
        </a-menu-item>
        <a-menu-item key="ANALYZER">
          <span>分析器</span>
          <a-badge :count="componentCount.ANALYZER" class="ml-2" />
        </a-menu-item>
      </a-menu>
    </aside>

    <!-- 右侧: 组件列表/编辑器 -->
    <main class="flex-1 flex flex-col overflow-hidden">
      <slot />
    </main>
  </div>
</template>

<script setup lang="ts">
const selectedCategory = ref(['all'])
const componentCount = ref({
  all: 42,
  STRATEGY: 8,
  SELECTOR: 6,
  SIZER: 10,
  RISKMANAGER: 12,
  ANALYZER: 6,
})

const emit = defineEmits(['category-change'])

const handleCategoryChange = ({ key }: { key: string }) => {
  emit('category-change', key)
}
</script>
```

#### SettingsLayout.vue - 系统设置布局

```vue
<template>
  <div class="min-h-screen bg-gray-50">
    <!-- 顶部标题栏 -->
    <div class="bg-white border-b border-gray-200 px-6 py-4">
      <h1 class="text-2xl font-semibold text-gray-900">{{ pageTitle }}</h1>
      <p v-if="pageDescription" class="text-sm text-gray-500 mt-1">
        {{ pageDescription }}
      </p>
    </div>

    <!-- 内容区 -->
    <div class="p-6">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  pageTitle: string
  pageDescription?: string
}>()
</script>
```

### 1.5.8 完整页面使用示例

#### StockInfo.vue - 股票信息页面

```vue
<template>
  <SettingsLayout
    page-title="股票信息管理"
    page-description="查询和管理股票基础信息，支持数据同步和更新"
  >
    <!-- 统计卡片 -->
    <div class="grid grid-cols-4 gap-4 mb-6">
      <StatCard
        :config="{
          title: '股票总数',
          value: stats.total,
          icon: DatabaseOutlined,
        }"
      />
      <StatCard
        :config="{
          title: '今日更新',
          value: stats.todayUpdated,
          icon: SyncOutlined,
          trend: { direction: 'up', value: '12%' },
        }"
      />
      <StatCard
        :config="{
          title: '数据完整率',
          value: stats.completeness,
          format: 'percent',
          icon: CheckCircleOutlined,
        }"
      />
      <StatCard
        :config="{
          title: '最后更新时间',
          value: stats.lastUpdate,
          format: 'text',
          icon: ClockCircleOutlined,
        }"
      />
    </div>

    <!-- 操作栏 -->
    <ActionBar
      :config="{
        leftActions: [
          { label: '同步全部', type: 'primary', onClick: handleSyncAll },
          { label: '批量更新', onClick: handleBatchUpdate },
        ],
        rightActions: [
          { label: '导出', onClick: handleExport },
        ],
      }"
    />

    <!-- 筛选栏 -->
    <FilterBar
      :config="{
        fields: [
          { key: 'code', label: '股票代码', type: 'text' },
          { key: 'name', label: '股票名称', type: 'text' },
          { key: 'market', label: '市场', type: 'select', options: marketOptions },
          { key: 'dateRange', label: '更新日期', type: 'dateRange' },
        ],
      }"
      @search="handleFilter"
      @reset="handleResetFilter"
    />

    <!-- 数据表格 -->
    <DataTable
      :config="{
        columns: [
          { key: 'code', title: '代码', width: 120 },
          { key: 'name', title: '名称', width: 200 },
          { key: 'market', title: '市场', width: 100 },
          { key: 'industry', title: '行业', width: 150 },
          { key: 'updateTime', title: '更新时间', width: 180 },
        ],
        actions: [
          { label: '查看详情', onClick: (row) => router.push(`/data/stockinfo/${row.code}`) },
          { label: '更新', onClick: handleUpdateSingle },
        ],
        rowKey: 'code',
        pagination: true,
      }"
      :data="tableData"
      @page-change="handlePageChange"
    >
      <!-- 自定义列渲染示例 -->
      <template #code="{ text }">
        <a class="text-primary">{{ text }}</a>
      </template>
    </DataTable>
  </SettingsLayout>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  DatabaseOutlined,
  SyncOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons-vue'
import { useTable } from '@/composables/useTable'
import { stockInfoApi } from '@/api'  // ✅ 使用封装的API
import type { StockInfoQuery } from '@/api'

// 统计数据
const stats = ref({
  total: 5234,
  todayUpdated: 342,
  completeness: 98.5,
  lastUpdate: '2025-01-31 15:30:00',
})

// 市场选项
const marketOptions = [
  { label: '上海', value: 'SH' },
  { label: '深圳', value: 'SZ' },
  { label: '北京', value: 'BJ' },
]

// 表格数据 - ✅ 使用封装的API
const { data: tableData, loading, pagination, fetch, refresh } = useTable({
  fetchFn: async (params) => {
    return await stockInfoApi.getList(params)
  },
  immediate: true,
})

// 操作处理 - ✅ 使用封装的API
const handleSyncAll = async () => {
  await stockInfoApi.sync(true)
  refresh()
}

const handleBatchUpdate = async () => {
  const codes = tableData.value.slice(0, 10).map((s: StockInfo) => s.code)
  await stockInfoApi.batchUpdate(codes)
  refresh()
}

const handleExport = async () => {
  const blob = await stockInfoApi.export({ page: 1, pageSize: 9999 })
  // 下载文件
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `stockinfo_${Date.now()}.xlsx`
  a.click()
}

const handleFilter = (filters: any) => {
  fetch(filters)
}

const handleResetFilter = () => {
  fetch({})
}

const handleUpdateSingle = async (row: StockInfo) => {
  await stockInfoApi.sync(false)
  refresh()
}

const handlePageChange = ({ page, pageSize }: any) => {
  fetch({ page, pageSize })
}
</script>
```

---

## 2. 页面导航架构

### 2.1 导航结构图

```
                    ┌─────────────────┐
                    │   首页/仪表盘    │
                    │   /             │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┬────────────────────┐
        │                    │                    │                    │
        ▼                    ▼                    ▼                    ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│  实时监控      │   │  策略回测      │   │组件&Portfolio │   │  数据管理      │
│  /dashboard   │   │  /backtest    │   │  /components  │   │  /data        │
└───────┬───────┘   └───────┬───────┘   └───────┬───────┘   └───────┬───────┘
        │                   │                   │                   │
        │                   │                   │                   │
        ▼                   ▼                   ▼                   ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│ 持仓详情       │   │ 回测列表       │   │ 组件库         │   │ 股票信息       │
│ /portfolio    │   │ /backtest/list│   │ /components   │   │ /data/stockinfo│
└───────────────┘   └───────┬───────┘   └───────┬───────┘   └───────────────┘
┌───────────────┐           │                   │           ┌───────────────┐
│ 绩效分析       │           │                   ▼           │ K线数据        │
│ /performance  │           │   ┌───────────────┐           │ /data/bars     │
└───────────────┘           │   │Portfolio列表  │           └───────────────┘
┌───────────────┐           │   │/portfolio      │           ┌───────────────┐
│ 信号中心       │           │   └───────┬───────┘           │ Tick数据       │
│ /signals      │           │           │                   │ /data/ticks    │
└───────────────┘           │           ▼                   └───────────────┘
        │           │   ┌───────────────┐
        │           │   │新建Portfolio  │
        │           │   │/portfolio/new  │
        │           │   │(节点图编辑器)  │
        │           │   └───────────────┘
        │           │
        ▼           ▼
┌───────────────┐   ┌───────────────┐
│  系统设置      │   │  新建回测      │
│  /settings    │   │ /backtest/new  │
└───────┬───────┘   │(选Portfolio+参数)│
        ▼           └───────────────┘
┌───────────────┐
│ 用户配置       │
│ /settings/profile│
└───────────────┘
┌───────────────┐
│ 系统参数       │
│ /settings/system│
└───────────────┘
┌───────────────┐
│ 用户管理       │
│ /settings/users│
└───────────────┘
┌───────────────┐
│ 用户组         │
│ /settings/user-groups│
└───────────────┘
┌───────────────┐
│ 通知模板       │
│ /settings/notification-templates│
└───────────────┘
┌───────────────┐
│ 通知历史       │
│ /settings/notification-history│
└───────────────┘
┌───────────────┐
│ 日志查看       │
│ /settings/logs │
└───────────────┘
```

### 2.2 侧边栏导航菜单

```
┌─────────────────────────┐
│ Ginkgo量化交易系统      │
├─────────────────────────┤
│ 📊 首页                │
│   └─ /                  │
├─────────────────────────┤
│ 📈 实时监控            │
│   ├─ 持仓详情          │
│   ├─ 绩效分析          │
│   └─ 信号中心          │
├─────────────────────────┤
│ 🧩 组件&Portfolio      │
│   ├─ 组件库            │
│   ├─ 策略库 (Strategy)  │
│   ├─ 选股器 (Selector)  │
│   ├─ 仓管 (Sizer)       │
│   ├─ 风控 (RiskMgr)     │
│   ├─ 分析器 (Analyzer)  │
│   ├─ Portfolio列表     │
│   └─ 新建Portfolio      │
├─────────────────────────┤
│ 🧪 策略回测            │
│   ├─ 回测列表          │
│   ├─ 新建回测          │
│   └─ 回测对比          │
├─────────────────────────┤
│ 💾 数据管理            │
│   ├─ 股票信息          │
│   ├─ K线数据           │
│   ├─ Tick数据          │
│   └─ 数据质量          │
├─────────────────────────┤
│ ⚙️ 系统设置            │
│   ├─ 用户配置          │
│   ├─ 系统参数          │
│   ├─ 用户管理          │
│   ├─ 用户组            │
│   ├─ 通知模板          │
│   ├─ 通知历史          │
│   └─ 日志查看          │
└─────────────────────────┘
```

## 3. 页面详细架构

### 3.1 首页/仪表盘 (`/`)

**页面用途**: 系统总览，Portfolio竞技场对比，实时动态流

**功能分区**:
```
┌─────────────────────────────────────────────────────────────────────────┐
│ 顶部栏: Logo | 用户信息 | 设置 | 登出                                    │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │                    🏆 Portfolio 竞技场 🏆                        │  │
│  │  时间范围: [近7天] [近30天] [近90天] [近1年]  [+ 添加Portfolio]   │  │
│  │  已选择: [双均线策略] [动量突破] [RSI反转] [MACD金叉] [布林带]     │  │
│  │                                                                   │  │
│  │  ┌─────────────────────────────────────────┐ ┌─────────────────┐  │  │
│  │  │                                         │ │ 收益率排名      │  │  │
│  │  │     多Portfolio净值对比曲线图            │ │ ┌───────────┐   │  │  │
│  │  │                                         │ │ │🥇 双均线  │   │  │  │
│  │  │     [ECharts折线图]                     │ │ │  +28.5%  │   │  │  │
│  │  │     每条线代表一个Portfolio              │ │ └───────────┘   │  │  │
│  │  │     支持图例显示/隐藏                    │ │ ┌───────────┐   │  │  │
│  │  │     支持缩放/平移                        │ │ │🥈 动量突破│   │  │  │
│  │  │                                         │ │ │  +22.1%  │   │  │  │
│  │  │                                         │ │ └───────────┘   │  │  │
│  │  │                                         │ │      ...        │  │  │
│  │  └─────────────────────────────────────────┘ │ 夏普比率/最大回撤│  │  │
│  │                                            └─────────────────┘  │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                         │
│  ┌───────────────────────────────┐ ┌─────────────────────────────┐     │
│  │   📈 实时信号流 (最新10条)     │ │   📰 最新资讯/通知            │     │
│  │  ┌─────────────────────────┐ │ │  ┌───────────────────────┐  │     │
│  │  │ 🔔 15:30 双均线策略      │ │ │  │ 📢 系统通知            │  │     │
│  │  │    信号: LONG 000001.SZ │ │ │  │    数据更新完成        │  │     │
│  │  │    价格: 12.35 💚 +1.2% │ │ │  │    2分钟前            │  │     │
│  │  │    [查看] [忽略]        │ │ │  │    [详情]              │  │     │
│  │  ├─────────────────────────┤ │ │  ├───────────────────────┤  │     │
│  │  │ 🔔 15:28 RSI反转策略     │ │ │  │ ⚠️ 风险提醒            │  │     │
│  │  │    信号: SHORT 600519.SH│ │ │  │    000001.SZ 止损触发  │  │     │
│  │  │    价格: 1850.00 🔴 -0.5%│ │ │  │    5分钟前            │  │     │
│  │  │    [查看] [忽略]        │ │ │  │    [处理]              │  │     │
│  │  ├─────────────────────────┤ │ │  ├───────────────────────┤  │     │
│  │  │ 🔔 15:25 布林带策略      │ │ │  │ 📊 数据同步            │  │     │
│  │  │    信号: LONG 300750.SZ │ │ │  │    股票信息已更新      │  │     │
│  │  │    价格: 88.50 💚 +2.1% │ │ │  │    10分钟前           │  │     │
│  │  │    [查看] [忽略]        │ │ │  │    [查看]              │  │     │
│  │  └─────────────────────────┘ │ │  └───────────────────────┘  │     │
│  │  [查看全部信号 →]            │ │  [查看全部资讯 →]           │     │
│  └───────────────────────────────┘ └─────────────────────────────┘     │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                    📊 我的关键指标                               │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │   │
│  │  │总资产    │ │今日盈亏  │ │持仓数量  │ │运行策略  │           │   │
│  │  │¥128,500 │ │+¥1,250  │ │8个      │ │5个运行中 │           │   │
│  │  │💚 +2.1% │ │💚 +0.98% │ │          │ │🟢 在线   │           │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  底部栏: 系统状态 | Worker状态 | 数据延迟 | 最后更新: 15:30:25          │
└─────────────────────────────────────────────────────────────────────────┘
```

**包含组件**:
1. **Portfolio竞技场** (`ArenaRanking.vue`) - 核心组件
   - 多Portfolio净值对比曲线图（ECharts）
   - 时间范围切换（7天/30天/90天/1年）
   - Portfolio选择器（最多8个）
   - 收益率/夏普比率/最大回撤排名
   - 支持图例显示/隐藏、缩放、平移

2. **实时信号流** (`SignalStream.vue`)
   - 滚动显示最新10条信号
   - 实时推送（WebSocket）
   - 信号类型标识（LONG/SHORT）
   - 快捷操作（查看详情/忽略）

3. **最新资讯/通知** (`NewsFeed.vue`)
   - 系统通知
   - 风险提醒
   - 数据同步状态
   - 支持分类筛选

4. **我的关键指标** (`MyStats.vue`)
   - 总资产卡片
   - 今日盈亏卡片
   - 持仓数量卡片
   - 运行策略状态

**数据来源**:
- Portfolio列表: `GET /arena/portfolios`
- 对比数据: `POST /arena/comparison` (uuids[], timeRange)
- 实时信号: WebSocket `/ws/signals`
- 资讯通知: `GET /notifications/latest?limit=10`
- 我的统计: `GET /arena/mystats`

**竞技场特色功能**:
- 📊 一图对比多个Portfolio表现
- 🎯 支持动态添加/移除Portfolio
- ⚡ 数据每10秒自动刷新
- 🔍 支持缩放、平移查看细节
- 我的统计: `GET /portfolio/mystats`

**竞技场特色功能**:
- 🏆 策略对比：可选中2-5个策略进行性能对比
- 🔥 热门策略：显示当日访问量最高的策略
- 📊 详细分析：点击策略卡片跳转到详细分析页面
- ⚡ 实时更新：排行榜数据每10秒自动刷新

---

### 3.2 实时监控页面

#### 3.2.1 持仓详情 (`/dashboard/portfolio`)

**页面用途**: 查看完整的持仓信息和详情

**功能分区**:
```
┌─────────────────────────────────────────────────────────────┐
│ 面包屑: 首页 > 实时监控 > 持仓详情                            │
├─────────────────────────────────────────────────────────────┤
│  [持仓汇总区]                                               │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │持仓市值  │ │总盈亏    │ │今日盈亏  │ │持仓数量  │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
│                                                             │
│  [持仓列表区]                                               │
│  筛选: [市场▼] [行业▼] [搜索代码/名称_____] [刷新]          │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ 代码 | 名称 | 市场 | 数量 | 成本 | 现价 | 市值 | 盈亏% ││
│  │ [表格，支持排序、多选、批量操作]                        ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  [持仓详情区 - 点击行展开]                                   │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ 000001.SZ 平安银行                                      ││
│  │ ┌────────────┐ ┌────────────┐ ┌────────────┐          ││
│  │ │持仓明细    │ │盈亏曲线    │ │交易记录    │          ││
│  │ └────────────┘ └────────────┘ └────────────┘          ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

#### 3.2.2 绩效分析 (`/dashboard/performance`)

**页面用途**: 分析投资绩效和风险指标

**功能分区**:
```
┌─────────────────────────────────────────────────────────────┐
│ 面包屑: 首页 > 实时监控 > 绩效分析                            │
├─────────────────────────────────────────────────────────────┤
│  [时间选择器] [今日] [本周] [本月] [自定义]                  │
│                                                             │
│  [绩效指标卡片区]                                           │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │总收益率  │ │年化收益  │ │最大回撤  │ │夏普比率  │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │胜率      │ │盈亏比    │ │交易次数  │ │平均持仓  │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
│                                                             │
│  [图表区]                                                   │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ 净值曲线 + 回撤标记                                     ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌─────────────────────┐ ┌─────────────────────────────┐   │
│  │ 月度收益柱状图       │ │ 持仓分布饼图               │   │
│  └─────────────────────┘ └─────────────────────────────┘   │
│                                                             │
│  [交易记录区]                                               │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ 时间 | 代码 | 方向 | 价格 | 数量 | 盈亏                 ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

#### 3.2.3 信号中心 (`/dashboard/signals`)

**页面用途**: 统一展示策略信号和风控信号，支持实时查看和历史查询

**功能分区**:
```
┌─────────────────────────────────────────────────────────────┐
│ 面包屑: 首页 > 实时监控 > 信号中心                            │
│  Tab切换: [实时信号] [历史记录] [策略信号] [风控信号]          │
├─────────────────────────────────────────────────────────────┤
│  筛选: [来源:全部▼] [Portfolio:全部▼] [状态:全部▼] [时间▼]  │
│  [全部标记已处理] [导出]                                    │
│                                                             │
│  [信号列表区]                                               │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ ┌─────────────────────────────────────────────────────┐ ││
│  │ │ 🔴 [风控] 止损触发 - 000001.SZ 平安银行              │ ││
│  │ │ Portfolio: 测试组合A | 来源: StopLossRisk            │ ││
│  │ │ 2026-01-28 14:30:15 亏损-10.2% 建议平仓              │ ││
│  │ │ [查看详情] [标记处理]                                │ ││
│  │ └─────────────────────────────────────────────────────┘ ││
│  │ ┌─────────────────────────────────────────────────────┐ ││
│  │ │ 🟢 [策略] 买入信号 - 000002.SZ 万科A                │ ││
│  │ │ Portfolio: 测试组合A | 来源: SimpleBuyAndHold       │ ││
│  │ │ 2026-01-28 10:15:30 价格突破MA20                    │ ││
│  │ │ [查看详情] [标记处理]                                │ ││
│  │ └─────────────────────────────────────────────────────┘ ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  共123条记录  [◀ 1 2 3 ... 12 ▶]  每页 [20▼] 条               │
└─────────────────────────────────────────────────────────────┘
```

**功能说明**:
- 统一信号模型：策略信号（Strategy）和风控信号（RiskManager）在同一界面展示
- 实时信号Tab: 显示最新产生的信号，按时间倒序
- 历史记录Tab: 支持时间范围、来源、Portfolio等多维度筛选
- 信号来源标识：清晰区分信号来自哪个组件
- 操作: 标记处理、查看详情、导出记录

---

### 3.3 策略回测页面

#### 3.3.1 新建回测 (`/backtest/new`)

**页面用途**: 选择Portfolio并配置回测参数，启动回测任务

**功能分区**:
```
┌─────────────────────────────────────────────────────────────┐
│ 面包屑: 策略回测 > 新建回测                                  │
│                                    [保存配置] [启动回测]      │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  选择Portfolio (支持多选，用于回测对比)                       │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ ☑ 测试PortfolioA                                        ││
│  │   SimpleBuyAndHold + AllStockSelector + EqualWeight... ││
│  │                                                         ││
│  │ ☑ 测试PortfolioB                                        ││
│  │   MeanReversion + Top100Selector + FixedAmountSizer... ││
│  │                                                         ││
│  │ ☐ 测试PortfolioC                                        ││
│  │   Momentum + IndustrySelector + ATRSizer...           ││
│  │                                                         ││
│  │ [+ 选择更多Portfolio]                                   ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  回测参数配置                                               │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ 时间范围: [2023-01-01] 至 [2023-12-31]                 ││
│  │ 初始资金: [¥100,000]                                    ││
│  │ 数据频率: [日线 ▼] (日线/周线/月线/Tick)                ││
│  │ 股票池:   [Portfolio默认 ▼ 或 自定义__________]        ││
│  │ 交易费率: [0.0003] (万分之三)                           ││
│  │ 滑点设置: [0.0]                                         ││
│  │ 基准指数: [沪深300 ▼]                                   ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  [选择Portfolio并配置参数] [启动回测]                         │
└─────────────────────────────────────────────────────────────┘
```

**功能说明**:
- 从已创建的Portfolio列表中选择一个或多个进行回测
- 多选Portfolio自动启用回测对比功能
- 股票池默认使用Portfolio中Selector的配置，也可以自定义覆盖
- 回测参数（时间、资金、费率等）对选中的所有Portfolio生效

#### 3.3.2 回测列表 (`/backtest/list`)

**页面用途**: 查看和管理所有回测任务

**功能分区**:
```
┌─────────────────────────────────────────────────────────────┐
│ 面包屑: 策略回测 > 回测列表                                  │
│                      [新建回测] [批量删除] [刷新]            │
├─────────────────────────────────────────────────────────────┤
│  筛选: [状态:全部▼] [策略:全部▼] [时间范围▼] [搜索_______]   │
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ ┌─┬────┬──────────┬────────┬──────────┬────────┬────┐  ││
│  │ │☐│ID  │任务名称  │策略    │创建时间  │状态    │操作│  ││
│  │ ├─┼────┼──────────┼────────┼──────────┼────────┼────┤  ││
│  │ │☐│001 │测试回测1 │BuyHold │01-27 10:00│完成   │查看│  ││
│  │ │  │   │          │        │          │✓23.5% │删除│  ││
│  │ ├─┼────┼──────────┼────────┼──────────┼────────┼────┤  ││
│  │ │☐│002 │测试回测2 │MeanRev │01-27 11:00│运行中 │停止│  ││
│  │ │  │   │          │        │          │45%    │查看│  ││
│  │ └─┴────┴──────────┴────────┴──────────┴────────┴────┘  ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  状态说明: 🟢已完成 🟡运行中 🔴失败 ⚪等待中                 │
└─────────────────────────────────────────────────────────────┘
```

#### 3.3.3 回测详情 (`/backtest/detail/:id`)

**页面用途**: 查看单个回测的详细结果

**功能分区**:
```
┌─────────────────────────────────────────────────────────────┐
│ 面包屑: 策略回测 > 回测列表 > 测试回测1                       │
│                                    [导出] [克隆] [删除]      │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐│
│  │ 回测配置: 简单买入持有 | 2023-01-01 ~ 2023-12-31         ││
│  │ 初始资金: ¥100,000 → 最终净值: ¥123,456                  ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  [性能指标卡片]                                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │总收益率  │ │最大回撤  │ │夏普比率  │ │胜率      │      │
│  │+23.46%  │ │-8.5%    │ │1.25     │ │58.3%    │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │年化收益  │ │盈亏比    │ │交易次数  │ │平均持仓  │      │
│  │+25.1%   │ │1.82     │ │123      │ │5        │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
│                                                             │
│  [Tab切换: 概览 | 净值曲线 | 交易记录 | 持仓分析]            │
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                                                         ││
│  │  [图表/表格区域，根据Tab切换]                            ││
│  │                                                         ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

#### 3.3.4 回测对比 (`/backtest/compare`)

**页面用途**: 对比多个回测结果

**功能分区**:
```
┌─────────────────────────────────────────────────────────────┐
│ 面包屑: 策略回测 > 回测对比                                  │
├─────────────────────────────────────────────────────────────┤
│  选择回测: [添加回测]                                        │
│  ┌────────────────┐ ┌────────────────┐ ┌────────────────┐  │
│  │ ✗ 测试回测1    │ │ ✓ 测试回测2    │ │ ✓ 测试回测3    │  │
│  │   BuyHold      │ │   MeanRev      │ │   Momentum     │  │
│  │   +23.5%       │ │   +18.2%      │ │   +31.5%      │  │
│  └────────────────┘ └────────────────┘ └────────────────┘  │
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  [对比表格 - 多个回测的关键指标对比]                     ││
│  │  ┌──────────┬──────────┬──────────┬──────────┐        ││
│  │  │指标      │回测1     │回测2     │回测3     │        ││
│  │  ├──────────┼──────────┼──────────┼──────────┤        ││
│  │  │总收益率  │+23.5%   │+18.2%   │+31.5%   │        ││
│  │  │最大回撤  │-8.5%    │-6.2%    │-12.3%   │        ││
│  │  │夏普比率  │1.25     │1.42     │0.98     │        ││
│  │  └──────────┴──────────┴──────────┴──────────┘        ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  [对比图表 - 多条净值曲线叠加]                           ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

---

### 3.4 数据管理页面

#### 3.4.1 股票信息 (`/data/stockinfo`)

**页面用途**: 管理股票基础信息

**功能分区**:
```
┌─────────────────────────────────────────────────────────────┐
│ 面包屑: 数据管理 > 股票信息                                  │
│                           [更新全部] [导出] [批量操作]      │
├─────────────────────────────────────────────────────────────┤
│  筛选: [市场:全部▼] [行业:全部▼] [搜索代码/名称_____]        │
│                                                             │
│  [数据统计]                                                 │
│  总股票数: 5,234 | 沪深A股: 4,856 | 更新时间: 2026-01-27    │
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ ┌─┬──────┬──────┬────────┬────────┬────────┬────────┐  ││
│  │ │☐│代码  │名称  │市场    │行业    │更新时间│操作    │  ││
│  │ ├─┼──────┼──────┼────────┼────────┼────────┼────────┤  ││
│  │ │☐│000001│平安  │SZ      │金融    │01-27   │查看详情│  ││
│  │ │  │.SZ   │银行  │        │        │        │更新数据│  ││
│  │ └─┴──────┴──────┴────────┴────────┴────────┴────────┘  ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  共5,234条记录  [◀ 1 2 3 ... 52 ▶]  每页 [100▼] 条         │
└─────────────────────────────────────────────────────────────┘
```

#### 3.4.2 K线数据 (`/data/bars`)

**页面用途**: 查询和管理K线数据

**功能分区**:
```
┌─────────────────────────────────────────────────────────────┐
│ 面包屑: 数据管理 > K线数据                                   │
│                                    [更新] [导出] [下载]      │
├─────────────────────────────────────────────────────────────┤
│  股票: [000001.SZ ▼ 或 搜索_________]                        │
│  周期: [日线 ▼] (分钟/日线/周线/月线)                        │
│  范围: [2023-01-01] 至 [2024-01-01]                          │
│  [查询] [重置]                                               │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐│
│  │  数据质量报告                                           ││
│  │  总记录数: 1,234 | 缺失天数: 5 | 覆盖率: 98.2% | 质量:优秀││
│  │  ┌───────────────────────────────────────────────────┐  ││
│  │  │ 数据完整性: ████████████████████░░ 98.2%          │  ││
│  │  └───────────────────────────────────────────────────┘  ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  [K线图 - 可缩放、可拖动、支持十字线]                    ││
│  │  ┌───────────────────────────────────────────────────┐  ││
│  │  │   ╭───╮                                          │  ││
│  │  │  ╭╯   ╰─╮                                         │  ││
│  │  │ ╭╯      ╰╮                                        │  ││
│  │  │╭╯         ╰──╮                                    │  ││
│  │  │                 [ECharts K线图 + 成交量]           │  ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  数据预览 (最新100条)  [显示全部] [下载CSV]             ││
│  │  ┌──────────┬────────┬────────┬────────┬────────┬────┐ ││
│  │  │日期      │开盘    │最高    │最低    │收盘    │成交量│ ││
│  │  ├──────────┼────────┼────────┼────────┼────────┼────┤ ││
│  │  │2023-12-29│46.20   │46.80   │46.10   │46.50   │12M │ ││
│  │  │2023-12-28│45.80   │46.30   │45.60   │46.20   │10M │ ││
│  │  └──────────┴────────┴────────┴────────┴────────┴────┘ ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

#### 3.4.3 数据质量 (`/data/quality`)

**页面用途**: 查看数据质量报告

**功能分区**:
```
┌─────────────────────────────────────────────────────────────┐
│ 面包屑: 数据管理 > 数据质量                                  │
│                                    [检查全部] [导出报告]     │
├─────────────────────────────────────────────────────────────┤
│  筛选: [数据类型:全部▼] [质量:全部▼] [市场:全部▼]           │
│                                                             │
│  [质量概览卡片]                                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐      │
│  │股票总数  │ │优质数据  │ │数据缺失  │ │待修复    │      │
│  │5,234    │ │4,980    │ │254      │ │12       │      │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘      │
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  数据质量列表                                           ││
│  │  ┌──────┬──────┬────────┬────────┬────────┬────────┐   ││
│  │  │代码  │名称  │数据类型│覆盖率  │质量评分│操作    │   ││
│  │  ├──────┼──────┼────────┼────────┼────────┼────────┤   ││
│  │  │000001│平安  │K线日线 │98.2%   │优秀    │查看    │   ││
│  │  │.SZ   │银行  │        │        │        │修复    │   ││
│  │  └──────┴──────┴────────┴────────┴────────┴────────┘   ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

---

### 3.5 组件管理页面 (`/components`)

**页面用途**: 管理回测组件（Strategy/Selector/Sizer/RiskManager/Analyzer），支持查看、创建、编辑、删除自定义组件

#### 3.5.1 组件列表 (`/components`)

**功能分区**:
```
┌─────────────────────────────────────────────────────────────┐
│ 面包屑: 策略回测 > 组件管理                                  │
│                                    [新建组件] [批量操作]      │
├─────────────────────────────────────────────────────────────┤
│  筛选: [类型:全部▼] [状态:全部▼] [搜索代码/名称_______]      │
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ 类型标签栏                                             ││
│  │ ┌────┐────┐────┐────┐────┐────┐                           ││
│  │全部│策略│选股│仓管│风控│分析│                           ││
│  │12 │ 3 │ 4 │ 3 │ 5 │ 1 │                           ││
│  └────┴────┴────┴────┴────┴────┘                           ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ 组件列表                                               ││
│  │ ┌─────┬──────┬────────┬────────┬────────┬────────┐   ││
│  │名称  │类型  │状态    │版本    │创建时间│操作    │   ││
│  ├─────┼──────┼────────┼────────┼────────┼────────┤   ││
│  │Simple│Strategy│✓预置  │v1.2.3  │01-25   │查看|编辑│   ││
│  │BuyHold│       │        │        │        │复制|删除│   ││
│  ├─────┼──────┼────────┼────────┼────────┼────────┤   ││
│  │MeanRe│Strategy│📝自定义│v2.1.0  │01-27   │查看|编辑│   ││
│  │vers │       │        │        │        │复制|删除│   ││
│  └─────┴──────┴────────┴────────┴────────┴────────┘   ││
│  状态说明: ✓预置 (系统组件，只读) 📝自定义 (可编辑) 🔄使用中   ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  共32个组件  [◀ 1 2 3 ... 4 ▶]  每页 [20▼] 条               │
└─────────────────────────────────────────────────────────────┘
```

#### 3.5.2 组件编辑器 (`/components/:id/edit`)

**功能分区**:
```
┌─────────────────────────────────────────────────────────────┐
│ 面包屑: 组件&Portfolio > SimpleBuyAndHold > 编辑              │
│                         [保存] [运行测试] [版本历史] [返回]    │
├─────────────────────────────────────────────────────────────┤
│  Tab切换: [代码编辑] [组件测试]                                 │
│                                                             │
│  [Tab: 代码编辑]                                            │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ 组件信息                                               ││
│  │  ─────────────────────────────────────────────────────  ││
│  │  组件名称: [SimpleBuyAndHold________________________]    ││
│  │  组件类型: [Strategy ▼]                              ││
│  │  组件描述: [简单买入持有策略______________________]    ││
│  │  标签: [趋势跟踪] [动量]                              ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ 代码编辑器 (Monaco Editor风格)                          ││
│  │  ┌─────────────────────────────────────────────────────┐││
│  │  1 | import abc                                         │││
│  │  2 | class SimpleBuyAndHold(BaseStrategy):           │││
│  │  3 |     def cal(self, portfolio_info, event):         │││
│  │  4 |         # 获取价格数据                             │││
│  │  5 |         bars = self.data_feeder.get_bars(...)    ││││
│  │   │                                                 │││
││  │  6 |         # 策略逻辑实现                             │││
│  │  7 │                                                 │││
│  │  │  [代码编辑区域，支持Python语法高亮、自动缩进]    │││
│  │  │                                                 │││
│  │ 50 │                                                 │││
│  └─────────────────────────────────────────────────────┘│
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  语法检查: [✓ 通过] 或 [✗ 错误: 第5行语法错误]               │
│                                                             │
│  [Tab: 组件测试]                                            │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ 测试配置                                               ││
│  │  ─────────────────────────────────────────────────────  ││
│  │  测试数据: [快速验证▼] 或 [自定义_______]             ││
│  │  股票代码: [000001.SZ__________] (快速验证模式)        ││
│  │  时间范围: [2023-12-01] 至 [2023-12-31]                ││
│  │  预期输出: [可选，填入后自动对比]                        ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  [运行测试]                                                  │
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ 测试结果                                               ││
│  │  ─────────────────────────────────────────────────────  ││
│  │  状态: ✓ 通过 / ✗ 失败                                 ││
│  │  实际输出: Signal(...) 或 错误信息                      ││
│  │  预期输出: Signal(...) 或 [未设置]                     ││
│  │  对比结果: [✓ 匹配] 或 [✗ 不匹配: 差异说明]            ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**测试功能说明**:
- **快速验证模式**: 使用默认测试数据快速验证组件代码是否能运行
- **自定义数据模式**: 用户可输入特定的测试数据（价格序列、事件列表等）
- **预期输出对比**: 用户可填写预期输出，系统自动对比实际输出
- **结果展示**: 显示组件返回值（Signal列表、股票列表、订单数量等）
- **错误定位**: 如果测试失败，显示错误堆栈和定位到具体代码行

#### 3.5.3 新建组件 (`/components/new`)

**功能分区**:
```
┌─────────────────────────────────────────────────────────────┐
│ 面包屑: 策略回测 > 组件管理 > 新建组件                       │
│                         [创建] [取消]                     │
├─────────────────────────────────────────────────────────────┤
│  第1步: 基本信息                                           │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ 组件名称: [_______________________________]           ││
│  │ 组件类型: [Strategy ▼]                              ││
│  │   ├─ Strategy (策略)                                  ││
│  │   ├─ Selector (选股器)                               ││
│  │   ├─ Sizer (仓位管理)                                ││
│  │   ├─ RiskManager (风控)                              ││
│  │   └─ Analyzer (分析器)                               ││
│  │ 组件描述: [_______________________________________]     ││
│  │ 标签: [趋势] [动量] [均值回归] [+]                        ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  第2步: 模板选择 (可选)                                     ││
│  ┌─────────────────────────────────────────────────────────┐│
│  │ 选择模板: [空模板 ▼]                                   ││
│  │   ├─ 空模板 (从零开始)                               ││
│  │   ├─ SimpleBuyAndHold (简单买入持有)                   ││
│  │   └─ MeanReversion (均值回归)                         ││
│  └─────────────────────────────────────────────────────────┘│
│  [加载模板]                                                   │
│                                                             │
│  第3步: 代码编辑                                           │
│  │  [代码编辑器 - 同编辑器界面]                           │
│  │                                                          │
│  操作区: [验证语法] [创建组件] [返回]                      │
└─────────────────────────────────────────────────────────────┘
```

#### 3.5.4 组件详情 (`/components/:id`)

**功能分区**:
```
┌─────────────────────────────────────────────────────────────┐
│ 面包屑: 组件&Portfolio > SimpleBuyAndHold                          │
│                         [编辑] [复制] [删除] [运行测试] [返回]  │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐│
│  │ 组件概览                                               ││
│  │  ─────────────────────────────────────────────────────  ││
│  │  组件ID: comp_12345678                                   ││
│  │  名称: SimpleBuyAndHold                                  ││
│  │  类型: Strategy (策略)                                   ││
│  │  状态: 📝 自定义                                       ││
│  │  版本: v1.2.3 (最新更新: 2026-01-27 15:30)            ││
│  │  标签: 趋势跟踪, 动量                                   ││
│  │  创建者: ginkgo_admin                                   ││
│  │  描述: 简单买入持有策略，适合牛市环境                   ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ 代码预览 (只显示前30行)                                ││
│  │  ┌─────────────────────────────────────────────────────┐││
│  │  │ 1 | class SimpleBuyAndHold(BaseStrategy):          │││
│  │  │ 2 |     def cal(self, portfolio_info, event):        │││
│  │  │ 3 |         if event.type == EVENT_TYPES.TICK:     │││
│  │  │ 4 |             price = event.current_price           │││
│  │  │ 5 |             if price > self.ma:                 │││
│  │  │ 6 |                 return Signal(...)              ││
│  │  └─┴────────────────────────────────────────────────┘││
│  │  [查看完整代码]                                           ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ 使用统计                                               ││
│  │  ─────────────────────────────────────────────────────  ││
│  │  被回测使用: 12次                                       ││
│  │  被Portfolio使用: 3个                                    ││
│  │  最后使用: 2026-01-28 10:30                             ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ 版本历史                                               ││
│  │  ┌─────────────────────────────────────────────────────┐││
│  │  │ v1.2.3 (当前)  2026-01-27 15:30                      │││
│  │  │ v1.2.2        2026-01-25 10:15                      │││
│  │  │ v1.2.1        2026-01-20 14:00                      │││
│  │  └─────────────────────────────────────────────────────┘││
│  │  [查看差异] [回滚到此版本]                                 ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

---

### 3.6 Portfolio管理页面 (`/portfolio`)

#### 3.6.1 Portfolio列表 (`/portfolio`)

**页面用途**: 查看和管理所有已创建的Portfolio

**功能分区**:
```
┌─────────────────────────────────────────────────────────────┐
│ 面包屑: 组件&Portfolio > Portfolio列表                       │
│                                    [新建Portfolio] [导入]     │
├─────────────────────────────────────────────────────────────┤
│  筛选: [状态:全部▼] [搜索名称_______]                        │
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ ┌─┬────────┬──────────┬────────┬────────┬────────┐    ││
│  │ │☐│名称    │组件数    │创建时间│回测次数│操作    │    ││
│  │ ├─┼────────┼──────────┼────────┼────────┼────────┤    ││
│  │ │☐│测试组合A│ 4        │01-27   │ 12     │查看|编辑│    ││
│  │ │  │        │St+Sel+Si+│10:00   │        │回测|删除│    ││
│  │ │  │        │Rm        │        │        │        │    ││
│  │ ├─┼────────┼──────────┼────────┼────────┼────────┤    ││
│  │ │☐│测试组合B│ 5        │01-28   │ 8      │查看|编辑│    ││
│  │ │  │        │St+Sel+Si+│11:30   │        │回测|删除│    ││
│  │ │  │        │Rm+Ana    │        │        │        │    ││
│  │ └─┴────────┴──────────┴────────┴────────┴────────┘    ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  共5个Portfolio  [◀ 1 ▶]                                    │
└─────────────────────────────────────────────────────────────┘
```

#### 3.6.2 新建Portfolio - 节点图编辑器 (`/portfolio/new`)

**页面用途**: 通过节点图编辑器构建Portfolio，拖拽组件并通过接口连接

**功能分区**:
```
┌─────────────────────────────────────────────────────────────────┐
│ 面包屑: 组件&Portfolio > 新建Portfolio                           │
│                         [保存] [验证] [测试Portfolio] [运行回测] │
├─────────────────────────────────────────────────────────────────┤
│  Tab切换: [节点图] [测试结果]                                     │
│                                                                 │
│  [Tab: 节点图]                                                  │
│  [画布区域 - 可缩放、可拖动、右键弹出菜单]                         │
│                                                                 │
│              ┌─────────────────────┐                            │
│              │    Portfolio        │                            │
│              │  ─────────────────  │                            │
│              │  名称: [测试组合A_] │                            │
│              │  ─────────────────  │                            │
│              │  ○ 属性接口         │ ──→ 点击配置回测基本参数     │
│              │  ○ 策略接口         │                            │
│              │  ○ 选股器接口       │                            │
│              │  ○ 仓管接口         │                            │
│              │  ○ 风控接口         │                            │
│              │  ○ 分析器接口       │                            │
│              └─────────────────────┘                            │
│                       │    │    │    │                           │
│                       ▼    ▼    ▼    ▼                           │
│              ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐    │
│              │Strategy │ │Selector │ │ Sizer  │ │ RiskMgr │    │
│              │BuyHold  │ │AllStock │ │EqualWt │ │StopLoss│    │
│              │[测试]   │ │[测试]   │ │[测试]  │ │[测试]  │    │
│              └─────────┘ └─────────┘ └─────────┘ └─────────┘    │
│                                                                 │
│  [右键画布 → 弹出组件菜单]                                       │
│   ┌─────────────────┐                                          │
│   │ 📊 策略          │                                          │
│   │   ├─ BuyHold    │                                          │
│   │   └─ MeanRev    │                                          │
│   │ 🔍 选股器       │                                          │
│   │   ├─ AllStock   │                                          │
│   │   └─ Top100     │                                          │
│   │ ⚖️ 仓管         │                                          │
│   │ 🛡️ 风控         │                                          │
│   │ 📊 分析器       │                                          │
│   └─────────────────┘                                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│  [右侧参数配置面板 - 点击组件后显示]                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Strategy: SimpleBuyAndHold                                    │
│  ────────────────────────────────────────────────────────       │
│  参数名        │ 参数值                  │                       │
│  ─────────────┼─────────────────────────┤                       │
│  MA Short     │ [____5____]             │                       │
│  MA Long      │ [____20____]            │                       │
│  ─────────────┴─────────────────────────┘                       │
│                                                                 │
│  [应用] [重置] [测试此组件]                                      │
└─────────────────────────────────────────────────────────────────┘

│  [Tab: 测试结果]                                                │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ 测试配置                                                ││
│  │  ─────────────────────────────────────────────────────  ││
│  │  测试股票: [000001.SZ________]                          ││
│  │  测试时间: [2023-12-01] 至 [2023-12-31]                 ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ 组件测试状态                                            ││
│  │  ─────────────────────────────────────────────────────  ││
│  │  Strategy (SimpleBuyAndHold)  ✓ 通过                   ││
│  │  Selector (AllStockSelector)   ✓ 通过                   ││
│  │  Sizer (EqualWeightSizer)     ✓ 通过                   ││
│  │  RiskManager (StopLossRisk)    ✓ 通过                   ││
│  │                                                         ││
│  │  Portfolio整体: ✓ 所有组件验证通过                       ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  [运行测试]                                                  │
└─────────────────────────────────────────────────────────────┘
```

**交互方式**:
1. **右键画布** → 弹出组件菜单 → 选择组件 → 组件出现在画布上
2. **点击Portfolio接口** → 弹出该类型组件菜单 → 选择后自动创建并连线
3. **拖拽连线** → 从组件拖拽连线到Portfolio对应接口
4. **点击组件** → 右侧面板显示该组件的参数配置
5. **测试单个组件** → 点击组件上的[测试]按钮，验证组件逻辑
6. **测试整个Portfolio** → 点击顶部[测试Portfolio]，验证所有组件协同工作
7. **保存验证** → 检查必需接口（Strategy）是否已连接，参数是否完整

#### 3.6.3Portfolio详情 (`/portfolio/:id`)

**页面用途**: 查看Portfolio的完整配置、组件关系和使用统计

**功能分区**:
```
┌─────────────────────────────────────────────────────────────┐
│ 面包屑: 组件&Portfolio > 测试组合A                            │
│                         [编辑] [复制] [删除] [启动回测] [返回]  │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────────┐│
│  │ Portfolio概览                                          ││
│  │  ─────────────────────────────────────────────────────  ││
│  │ 名称: 测试组合A                                          ││
│  │ 组件数: 4 (Strategy + Selector + Sizer + RiskManager)   ││
│  │ 创建时间: 2026-01-27 15:30                               ││
│  │ 最后修改: 2026-01-28 10:30                               ││
│  │ 描述: 简单的均线突破策略组合                               ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ 组件关系图                                              ││
│  │  ─────────────────────────────────────────────────────  ││
│  │  Portfolio → Strategy (SimpleBuyAndHold)               ││
│  │            → Selector (AllStockSelector)               ││
│  │            → Sizer (EqualWeightSizer)                  ││
│  │            → RiskManager (StopLossRisk)                ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ 使用统计                                                ││
│  │  ─────────────────────────────────────────────────────  ││
│  │  被回测使用: 12次                                       ││
│  │  最后回测: 2026-01-28 10:30                             ││
│  │  最佳收益: +25.3% (回测#008)                            ││
│  │  平均收益: +18.5%                                       ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

---

### 3.8 系统设置页面

#### 3.7.1 用户配置 (`/settings/profile`)

**页面用途**: 用户个人配置

**功能分区**:
```
┌─────────────────────────────────────────────────────────────┐
│ 面包屑: 系统设置 > 用户配置                                  │
│                                    [保存]                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  基本信息                                               ││
│  │  ─────────────────────────────────────────────────────  ││
│  │  用户名: [ginkgo_admin____________]                     ││
│  │  邮箱:   [admin@example.com___________]                 ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  修改密码                                               ││
│  │  ─────────────────────────────────────────────────────  ││
│  │  当前密码: [_______________________]                    ││
│  │  新密码:   [_______________________]                    ││
│  │  确认密码: [_______________________]                    ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  界面偏好                                               ││
│  │  ─────────────────────────────────────────────────────  ││
│  │  主题:   [☐浅色 ☑深色 ○自动]                           ││
│  │  语言:   [简体中文 ▼]                                   ││
│  │  时区:   [Asia/Shanghai ▼]                              ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

#### 3.6.2系统参数 (`/settings/system`)

**页面用途**: 系统级参数配置

**功能分区**:
```
┌─────────────────────────────────────────────────────────────┐
│ 面包屑: 系统设置 > 系统参数                                  │
│                                    [保存] [重启服务]         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  数据源配置                                             ││
│  │  ─────────────────────────────────────────────────────  ││
│  │  Tushare Token:  [3*******************2]  [更新]       ││
│  │  数据更新时间:   [每天 02:00]                            ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  Worker配置                                             ││
│  │  ─────────────────────────────────────────────────────  ││
│  │  Worker数量:     [4____] 个                             ││
│  │  自动重启:       [✓ 已启用]                             ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  回测配置                                               ││
│  │  ─────────────────────────────────────────────────────  ││
│  │  最大并发回测:   [2____] 个                             ││
│  │  回测结果保留:   [30____] 天                            ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

#### 3.8.4 用户管理 (`/settings/users`)

**页面用途**: 管理系统用户及其联系方式

**功能分区**:
```
┌─────────────────────────────────────────────────────────────┐
│ 面包屑: 系统设置 > 用户管理                                  │
│                                    [新建用户] [批量导入]       │
├─────────────────────────────────────────────────────────────┤
│  筛选: [类型:全部▼] [状态:全部▼] [搜索_______]             │
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ ┌─┬──────┬────────┬────────┬────────┬────────┐      ││
│  │ │☐│名称  │类型    │状态    │联系方式│操作    │      ││
│  │ ├─┼──────┼────────┼────────┼────────┼────────┤      ││
│  │ │☐│Alice │个人    │✓激活   │2       │查看|编辑│      ││
│  │ │  │      │        │        │Email   │联系方式│      ││
│  │ │  │      │        │        │Webhook │删除    │      ││
│  │ ├─┼──────┼────────┼────────┼────────┼────────┤      ││
│  │ │☐│ traders│组织    │✓激活   │5       │查看|编辑│      ││
│  │ │  │      │        │        │Discord │联系方式│      ││
│  │ └─┴──────┴────────┴────────┴────────┴────────┘      ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  共10个用户  [◀ 1 2 ▶]                                        │
└─────────────────────────────────────────────────────────────┘
```

**用户详情弹窗**:
```
┌─────────────────────────────────────────────────────────────┐
│ 用户详情: Alice                                              │
│                                    [保存] [关闭]               │
├─────────────────────────────────────────────────────────────┤
│  基本信息                                                   │
│  ─────────────────────────────────────────────────────       │
│  名称: [Alice_________________] 用户类型: [个人▼]            │
│  描述: [量化交易员___________] 状态: [✓激活]              │
│                                                             │
│  联系方式                                                   │
│  ─────────────────────────────────────────────────────       │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ 类型       │ 地址                    │ 主用 │ 操作 │    │
│  │ ├───────────┼─────────────────────────┼──────┼──────┤    │
│  │ Email      │ alice@example.com        │ ☑   │编辑  │    │
│  │ Webhook    │ https://hook...         │ ☐   │编辑  │    │
│  │ Discord    │ alice#1234              │ ☐   │编辑  │    │
│  └───────────┴─────────────────────────┴──────┴──────┘    │
│  [+ 添加联系方式]                                           │
└─────────────────────────────────────────────────────────────┘
```

#### 3.8.5 用户组管理 (`/settings/user-groups`)

**页面用途**: 管理用户组，支持批量通知

**功能分区**:
```
┌─────────────────────────────────────────────────────────────┐
│ 面包屑: 系统设置 > 用户组管理                                │
│                                    [新建用户组]               │
├─────────────────────────────────────────────────────────────┤
│  筛选: [状态:全部▼] [搜索_______]                             │
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ ┌─┬──────────┬────────┬────────┬────────┐            ││
│  │ │☐│组名称    │用户数  │状态    │操作    │            ││
│  │ ├─┼──────────┼────────┼────────┼────────┤            ││
│  │ │☐│traders   │15      │✓激活   │查看成员│            ││
│  │ │  │          │        │        │编辑    │            ││
│  │ │  │          │        │        │删除    │            ││
│  │ ├─┼──────────┼────────┼────────┼────────┤            ││
│  │ │☐│admins    │3       │✓激活   │查看成员│            ││
│  │ └─┴──────────┴────────┴────────┴────────┘            ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

**用户组编辑弹窗**:
```
┌─────────────────────────────────────────────────────────────┐
│ 编辑用户组: traders                                         │
│                                    [保存] [取消]               │
├─────────────────────────────────────────────────────────────┤
│  组名称: [traders________________] 状态: [✓激活]              │
│  描述: [交易员组，接收交易信号通知___________]               │
│                                                             │
│  组成员                                                     │
│  ─────────────────────────────────────────────────────       │
│  已选成员 (15)                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ ✓ Alice      ✓ Bob      ✓ Charlie   ✓ David         │    │
│  │ ✓ Eve        ✓ Frank                      [+ 添加成员] │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  可选成员                                                   │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ ☐ Grace     ☐ Henry     ☐ Ivan     ☐ Jack          │    │
│  │ ☐ Kate                                 [搜索成员___] │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

#### 3.8.6 通知模板管理 (`/settings/notification-templates`)

**页面用途**: 管理通知模板，支持变量替换

**功能分区**:
```
┌─────────────────────────────────────────────────────────────┐
│ 面包屑: 系统设置 > 通知模板                                  │
│                                    [新建模板] [预览]         │
├─────────────────────────────────────────────────────────────┤
│  筛选: [类型:全部▼] [状态:全部▼] [搜索_______]             │
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ ┌─┬──────────┬────────┬────────┬────────┐            ││
│  │ │☐│模板名称  │类型    │状态    │操作    │            ││
│  │ ├─┼──────────┼────────┼────────┼────────┤            ││
│  │ │☐│trade_sig  │Markdown│✓启用  │查看|编辑│            ││
│  │ │  │          │        │        │复制|删除│            ││
│  │ ├─┼──────────┼────────┼────────┼────────┤            ││
│  │ │☐│alert     │Text    │✓启用  │查看|编辑│            ││
│  │ └─┴──────────┴────────┴────────┴────────┘            ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

**模板编辑弹窗**:
```
┌─────────────────────────────────────────────────────────────┐
│ 编辑模板: trade_signal                                     │
│                        [保存] [验证] [预览] [关闭]             │
├─────────────────────────────────────────────────────────────┤
│  模板ID: [trade_signal_________]                             │
│  模板名称: [交易信号通知________]                           │
│  模板类型: [Markdown▼]  状态: [✓启用]                       │
│  消息主题: [{{symbol}}交易信号_____________]                 │
│                                                             │
│  模板内容 (支持Jinja2语法)                                  │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ ## 交易信号通知                                        ││
│  │                                                         ││
│  │ **股票**: {{symbol}}                                  ││
│  │ **方向**: {% if direction == 'LONG' %}🟢做多{% else %}🔴做空{% endif %}││
│  │ **价格**: {{price}}                                     ││
│  │ **数量**: {{volume}}                                    ││
│  │ **策略**: {{strategy_name}}                             ││
│  │ **理由**: {{reason}}                                    ││
│  │                                                         ││
│  │ 时间: {{timestamp}}                                    ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  可用变量: {{symbol}}, {{direction}}, {{price}}, {{volume}}, {{strategy_name}}, {{reason}}, {{timestamp}}│
│                                                             │
│  预览效果                                                   │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ ## 交易信号通知                                        ││
│  │ **股票**: 000001.SZ                                    ││
│  │ **方向**: 🟢做多                                       ││
│  │ **价格**: 15.50                                        ││
│  │ ...                                                     ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

#### 3.8.7 通知历史 (`/settings/notification-history`)

**页面用途**: 查看所有通知发送记录

**功能分区**:
```
┌─────────────────────────────────────────────────────────────┐
│ 面包屑: 系统设置 > 通知历史                                  │
│                   [筛选] [搜索] [导出] [刷新]                   │
├─────────────────────────────────────────────────────────────┤
│  筛选: [状态:全部▼] [渠道:全部▼] [用户:全部▼] [时间:最近7天▼]  │
│  搜索: [___________________] [搜索]                          │
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │ ┌─────────────────────────────────────────────────────┐ ││
│  │ │ 🔔 交易信号 - 000001.SZ 做多                         │ ││
│  │ │ 2026-01-28 10:30:15  用户: Alice  渠道: Discord     │ ││
│  │ │ 状态: [✓ 已发送]  模板: trade_signal                  │ ││
│  │ │ [查看详情] [重新发送]                                 │ ││
│  │ └─────────────────────────────────────────────────────┘ ││
│  │ ┌─────────────────────────────────────────────────────┐ ││
│  │ │ ⚠️ 系统通知 - K线数据更新完成                          │ ││
│  │ │ 2026-01-28 10:15:30  用户组: traders  渠道: Email     │ ││
│  │ │ 状态: [✓ 已发送]  模板: data_update                   │ ││
│  │ │ [查看详情] [重新发送]                                 │ ││
│  │ └─────────────────────────────────────────────────────┘ ││
│  │ ┌─────────────────────────────────────────────────────┐ ││
│  │ │ ❌ 发送失败 - Webhook超时                              │ ││
│  │ │ 2026-01-28 09:45:00  用户: Bob  渠道: Webhook        │ ││
│  │ │ 状态: [✗ 失败]  错误: Connection timeout               │ ││
│  │ │ [查看详情] [重新发送]                                 │ ││
│  │ └─────────────────────────────────────────────────────┘ ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  共123条记录  [◀ 1 2 3 ... 12 ▶]  每页 [20▼] 条               │
└─────────────────────────────────────────────────────────────┘
```

**通知详情弹窗**:
```
┌─────────────────────────────────────────────────────────────┐
│ 通知详情                                                   │
│                                    [关闭] [重新发送]           │
├─────────────────────────────────────────────────────────────┤
│  消息ID: msg_12345678                                       │
│  状态: [✓ 已发送]  优先级: [普通]                          │
│  发送时间: 2026-01-28 10:30:15                              │
│                                                             │
│  收件人                                                     │
│  ─────────────────────────────────────────────────────       │
│  用户: Alice (alice@example.com)                            │
│  用户组: traders (15人)                                    │
│                                                             │
│  模板信息                                                   │
│  ─────────────────────────────────────────────────────       │
│  模板ID: trade_signal                                      │
│  模板变量: {"symbol": "000001.SZ", "direction": "LONG", ...} ││
│                                                             │
│  渠道结果                                                   │
│  ─────────────────────────────────────────────────────       │
│  Discord: ✓ 成功 (2026-01-28 10:30:16)                     │
│  Email: ✓ 成功 (2026-01-28 10:30:17)                       │
│  Webhook: ✗ 失败 (Connection timeout)                       │
│                                                             │
│  消息内容                                                   │
│  ─────────────────────────────────────────────────────       │
│  ## 交易信号通知                                           │
│  **股票**: 000001.SZ                                        │
│  **方向**: 🟢做多                                           │
│  ...                                                       │
└─────────────────────────────────────────────────────────────┘
```

#### 3.8.3 日志查看 (`/settings/logs`)

**页面用途**: 查看系统日志

**功能分区**:
```
┌─────────────────────────────────────────────────────────────┐
│ 面包屑: 系统设置 > 日志查看                                  │
│                   [筛选] [搜索] [导出] [清空] [刷新]         │
├─────────────────────────────────────────────────────────────┤
│  筛选: [级别:全部▼] [模块:全部▼] [时间:最近1小时▼]          │
│  搜索: [___________________] [搜索]                          │
│                                                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  [日志内容]                                             ││
│  │  2026-01-28 10:30:15 [INFO ] data_manager: 数据更新完成  ││
│  │  2026-01-28 10:30:12 [INFO ] bar_crud: 添加234条K线数据  ││
│  │  2026-01-28 10:30:10 [WARN ] data_worker: 延迟较高 500ms ││
│  │  2026-01-28 10:30:05 [ERROR] kafka: 连接失败             ││
│  │  2026-01-28 10:30:03 [INFO ] worker: Worker-2 任务完成   ││
│  │  ...                                                    ││
│  └─────────────────────────────────────────────────────────┘│
│                                                             │
│  共1,234条记录  自动刷新: [✓ 已启用]  间隔: [5▼] 秒        │
└─────────────────────────────────────────────────────────────┘
```

---

### 3.7 API文档页面 (`/api-docs`)

**页面用途**: 查看API接口文档

**功能分区**:
```
┌─────────────────────────────────────────────────────────────┐
│  Ginkgo API文档                                             │
│                   [尝试] [下载] [认证]                       │
├─────────────────────────────────────────────────────────────┤
│  ┌───────────────┬─────────────────────────────────────────┐│
│  │               │                                         ││
│  │  端点列表     │  详情区域                                ││
│  │               │                                         ││
│  │  📁 认证      │  POST /auth/login                       ││
│  │    ├─ POST    │                                         ││
│  │    │  /login  │  用户登录                               ││
│  │    └─ POST    │                                         ││
│  │       /logout │  请求体:                                ││
│  │               │  {                                      ││
│  │  📁 持仓      │    "username": "string",                ││
│  │    ├─ GET     │    "password": "string"                 ││
│  │    │  /pos    │  }                                      ││
│  │    └─ GET     │                                         ││
│  │       /summary│  响应:                                  ││
│  │               │  {                                      ││
│  │  📁 回测      │    "token": "xxx",                      ││
│  │    └─ ...     │    "expires": 3600                     ││
│  │               │  }                                      ││
│  │               │                                         ││
│  │               │  [Try it out]                           ││
│  │               │                                         ││
│  └───────────────┴─────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

## 4. 页面间导航关系

### 4.1 主要用户流程

**流程1: 查看持仓 → 分析绩效**
```
首页(/)
  → 点击持仓卡片
  → 持仓详情(/dashboard/portfolio)
  → 点击某一行
  → 展开/跳转到详情页
```

**流程2: 创建回测 → 查看结果**
```
首页(/)
  → 侧边栏[策略回测]
  → 回测列表(/backtest/list)
  → [新建回测]
  → 新建回测(/backtest/new)
  → 填写配置 → [启动回测]
  → 跳转回测列表
  → 点击某一行
  → 回测详情(/backtest/detail/:id)
```

**流程3: 查看数据 → 更新数据**
```
首页(/)
  → 侧边栏[数据管理]
  → 选择数据类型
  → K线数据(/data/bars)
  → 选择股票 → 查看数据
  → [更新数据]
  → 查看更新结果
```

**流程4: 风控警报 → 处理警报**
```
首页(/) - 看到警报提示
  → 点击警报
  → 警报中心(/dashboard/alerts)
  或
  → 侧边栏[风控管理]
  → 警报历史(/risk/alerts)
  → 查看详情
  → [标记处理]
```

### 4.2 面包屑导航

所有页面（除首页外）都显示面包屑导航，方便用户返回上级页面。

```
首页: 不显示面包屑
二级页面: 首页 > XXX
三级页面: 首页 > XXX > YYY
```

## 5. 响应式适配

### 5.1 桌面端 (>1200px)
- 完整侧边栏导航
- 多列布局
- 完整功能展示

### 5.2 平板端 (768px-1200px)
- 收缩侧边栏（图标模式）
- 调整为2列布局
- 保留核心功能

### 5.3 移动端 (<768px)
- 隐藏侧边栏（汉堡菜单）
- 单列布局
- 简化功能入口
- 触摸优化

## 6. 权限与安全

### 6.1 页面访问权限
- 所有页面需要登录后访问
- 公开页面: 仅登录页 (`/login`)
- 受保护页面: 所有功能页面

### 6.2 操作权限
- 查看权限: 所有登录用户
- 修改权限: 所有登录用户（单用户系统）
- 删除权限: 所有登录用户（单用户系统）
