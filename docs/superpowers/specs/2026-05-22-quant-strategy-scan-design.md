# 量化策略研究系统化扫描方案

**日期**: 2026-05-22
**状态**: 已批准

## 目标

通过系统化回测扫描，找到能在 A股主板（沪深300/中证500）和数字货币（Binance）市场稳定盈利的策略组合。

## 市场范围

| 市场 | 品种 | 数据源 | 基准 |
|------|------|--------|------|
| A股主板 | 沪深300成分股 + 中证500 | Tushare / AKShare | 沪深300指数 |
| 数字货币 | BTC/USDT, ETH/USDT | Yahoo Finance / AKShare | Binance指数 |

## 研究流程

### Phase 1: 环境验证
- 确认历史K线数据可用（A股日线、数字货币4H/日线）
- 验证CLI回测全链路可跑通

### Phase 2: 全策略批量回测
所有策略组件与选股器两两组合，3个月历史数据：

| 策略 | 选股器 | Sizer | 风控 |
|------|--------|-------|------|
| RandomSignalStrategy | FixedSelector | FixedSizer | NoRisk |
| MovingAverageCrossover | CNAllSelector | ATRSizer | PositionRatioRisk |
| MeanReversion | MomentumSelector | RatioSizer | LossLimitRisk |
| Momentum | PopularitySelector | ... | ... |
| TrendFollow | ... | ... | ... |
| DualThrust | ... | ... | ... |

评估指标：胜率、夏普比率、最大回撤、盈亏比、净值曲线

### Phase 3: Top策略深度验证
- Top 3 策略延伸回测至12个月
- 模拟盘验证（Paper Replay）
- 有意思的结果提GitHub Issue记录

### Phase 4: Issue驱动开发
- 遇到工具缺失、功能bug、策略缺陷 → 直接提Issue
- 优先修复影响研究进度的Issue

## 工具清单

| 工具 | 用途 | 状态 |
|------|------|------|
| ginkgo data update --stockinfo | 更新A股股票列表 | 可用 |
| ginkgo backtest create/run | 回测全流程 | 可用 |
| ginkgo portfolio bind-component | 组件绑定 | 可用 |
| ginkgo worker | 模拟盘Worker | 可用 |
| GinkgoYahoo (数字货币) | 数字货币数据 | 需验证 |
| GinkgoAkShare (Binance) | Binance K线 | 需验证 |

## 已知风险

1. **数字货币数据源**：Yahoo Finance和AKShare对Binance支持度需实测
2. **数据质量**：A股日线Tushare需要认证，AKShare作为备选
3. **回测速度**：全策略组合可能耗时较长，分批执行

## 输出

- 回测结果汇总表（MD/CSV）
- 稳定盈利策略清单及参数
- GitHub Issue列表（工具缺失、功能bug）
- 下一步研究计划