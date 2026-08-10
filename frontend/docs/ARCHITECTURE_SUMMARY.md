# Web-UI 架构重构总结

## 📦 组件库

### 数据展示组件
| 组件 | 路径 | 功能 |
|------|------|------|
| DataTable | `@/components/data/DataTable.vue` | 通用表格，支持分页、筛选、排序、工具栏插槽 |
| StatisticCard | `@/components/data/StatisticCard.vue` | 统计卡片，支持图标、趋势、前缀后缀 |

### 表单组件
| 组件 | 路径 | 功能 |
|------|------|------|
| ProForm | `@/components/form/ProForm.vue` | 增强表单，统一验证、可配置提交取消按钮 |

### 业务组件
| 组件 | 路径 | 功能 |
|------|------|------|
| FactorSelector | `@/components/business/FactorSelector.vue` | 因子选择器 |
| DateRangePicker | `@/components/business/DateRangePicker.vue` | 日期范围选择器 |
| StrategyCard | `@/components/business/StrategyCard.vue` | 策略卡片 |
| SignalGenerator | `@/components/business/SignalGenerator.vue` | 信号生成器 |
| OrderBook | `@/components/business/OrderBook.vue` | 订单簿 |
| PositionChart | `@/components/business/PositionChart.vue` | 持仓图表 |
| TrendChart | `@/components/business/TrendChart.vue` | 趋势图表 |
| TradeStatus | `@/components/business/TradeStatus.vue` | 交易状态 |

### 通用组件
| 组件 | 路径 | 功能 |
|------|------|------|
| EmptyState | `@/components/common/EmptyState.vue` | 空状态占位 |
| LoadingOverlay | `@/components/common/LoadingOverlay.vue` | 加载遮罩层 |

## 🔧 Composables

| Composable | 路径 | 功能 |
|-----------|------|------|
| useApiError | `@/composables/useApiError.ts` | API 错误处理 |
| useCrudStore | `@/composables/useCrudStore.ts` | 通用 CRUD Store 模式 |
| useRealtime | `@/composables/useRealtime.ts` | 实时数据推送 (SSE) |
| useErrorHandler | `@/composables/useErrorHandler.ts` | 错误处理 |
| useLoading | `@/composables/useLoading.ts` | Loading 状态管理 |
| useWebSocket | `@/composables/useWebSocket.ts` | WebSocket 连接管理 |
| useTable | `@/composables/useTable.ts` | 表格状态管理 |
| useComponentList | `@/composables/useComponentList.ts` | 组件列表管理 |
| useNodeGraph | `@/composables/useNodeGraph.ts` | 节点图管理 |
| useRequestCancelable | `@/composables/useRequestCancelable.ts` | 可取消请求 |

## 📡 API 模块

### 核心模块
| 模块 | 路径 | 功能 |
|------|------|------|
| request.ts | `@/api/modules/core/request.ts` | Axios 配置、拦截器 |
| common.ts | `@/api/modules/common.ts` | 通用 API 方法包装 |

### 业务 API
| 模块 | 路径 | 功能 |
|------|------|------|
| research.ts | `@/api/modules/business/research.ts` | 研究相关 API |
| backtest.ts | `@/api/modules/business/backtest.ts` | 回测相关 API |
| portfolio.ts | `@/api/modules/business/portfolio.ts` | 投资组合相关 API |

### 类型定义
| 文件 | 路径 |
|------|------|
| common.ts | `@/api/types/common.ts` |

## 📄 文档

| 文档 | 路径 |
|------|------|
| 组件使用指南 | `frontend/USAGE_GUIDE.md` |
| 架构总结 | `frontend/docs/ARCHITECTURE_SUMMARY.md` |

## 🎯 重构完成清单

- [x] 核心请求模块封装
- [x] 通用类型定义
- [x] 通用业务 API 模块
- [x] StatisticCard 组件
- [x] DataTable 组件
- [x] ProForm 组件
- [x] EmptyState 组件
- [x] LoadingOverlay 组件
- [x] 业务组件库 (FactorSelector, DateRangePicker, etc.)
- [x] useApiError Composable
- [x] useCrudStore Composable
- [x] useRealtime Composable
- [x] Composables 统一导出
- [x] BacktestList 页面重构
- [x] PortfolioList 页面重构
- [x] Dashboard 页面完整实现
