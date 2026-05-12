# Portfolio 列表绩效展示设计

> 日期: 2026-05-13
> 状态: 已确认

## 目标

在组合列表页一眼看到每个组合的回测/模拟/实盘表现，并能对比关联组合的指标偏差。

## 现状问题

1. 列表卡片只显示"净值"（hardcoded 1.0）和"初始资金"，无任何绩效指标
2. 必须点进详情页 → 查看回测才能知道表现
3. deploy 出的模拟/实盘组合与源回测组合之间在列表页无任何关联展示

## 设计决策

### 1. 每个卡片独立，关系用摘要条展示

Portfolio 之间是平级关联关系，不是树形上下游。列表保持一维平铺，关联信息通过底部摘要条展示。

### 2. 指标按 Mode 区分数据来源

| Mode | 数据来源 | 主指标名 |
|------|---------|---------|
| BACKTEST | `backtest_task` 最新 completed 记录 | 年化收益 |
| PAPER | `MPortfolio` 自身字段（Worker 实时更新） | 累计收益 |
| LIVE | `MPortfolio` 自身字段（实盘交易实时更新） | 累计收益 |

### 3. 回测完成时同步写 Portfolio

当前 `aggregate_and_save()` 只写 `BacktestTask`，不写 `MPortfolio`。在末尾新增一步，将绩效指标同步写入 `MPortfolio`，使列表 API 无需额外查询即可返回指标。

## 卡片 UI

### 主指标区（2x2 网格）

替换现有"净值/初始资金"，显示：

| 位置 | 指标 | 颜色规则 |
|------|------|---------|
| 左上 | 年化收益(BACKTEST) / 累计收益(PAPER/LIVE) | 正值绿，负值红 |
| 右上 | Sharpe 比率 | 正值绿，负值红，<0.5 橙 |
| 左下 | 最大回撤 | 始终红色（取绝对值） |
| 右下 | 胜率 | >50% 绿，<50% 橙 |

无数据时显示灰色 `--`。

### 底部信息栏

| Mode | 显示内容 |
|------|---------|
| BACKTEST | 最近回测日期 · 回测次数 |
| PAPER | 运行天数 |
| LIVE | 运行天数 · 交易所/环境 |

### 关联摘要条

有 deploy 关系的卡片底部显示关联组合的紧凑指标（2 个核心指标：收益 + 回撤）。

**方向规则：**
- BACKTEST 卡片：并排显示已部署的 PAPER / LIVE 摘要
- PAPER/LIVE 卡片：显示来源 BACKTEST 摘要 + 同组其他关联组合

**摘要条样式：** 按 Mode 颜色区分边框和标签（蓝=回测，橙=模拟，绿=实盘），可点击跳转到对应 portfolio 详情。

无关联的卡片底部不显示摘要条区域。

## 筛选

保持现有 Mode filter + 关键词搜索，行为不变：
- Mode 筛选：简单过滤，只显示对应 mode 的卡片
- 关键词搜索：按名称匹配
- 两者叠加取交集

摘要条始终显示（不受筛选影响），提供完整的关联上下文。

## 后端改动

### 1. API 列表接口返回绩效指标

**文件:** `api/api/portfolio.py` — `GET /api/v1/portfolios/`

响应增加字段：
```python
{
    "uuid": str,
    "name": str,
    "mode": str,
    "state": str,
    # 新增绩效指标
    "annual_return": float | None,
    "sharpe_ratio": float | None,
    "max_drawdown": float | None,
    "win_rate": float | None,
    # 新增关联信息
    "related": [
        {"uuid": str, "name": str, "mode": str, "state": str,
         "annual_return": float | None, "max_drawdown": float | None,
         "relation": "source" | "deploy_paper" | "deploy_live"}
    ],
    # 新增元信息
    "backtest_count": int,       # BACKTEST mode: 回测次数
    "last_backtest_date": str,   # BACKTEST mode: 最近回测日期
    "running_days": int,         # PAPER/LIVE mode: 运行天数
}
```

**实现逻辑：**
- BACKTEST mode：查 `backtest_task` 表取最新 completed 记录的指标
- PAPER/LIVE mode：直接读 `MPortfolio` 字段
- 关联信息：通过 `deployment` 表或 `source_portfolio_id` 查找关联组合，取其指标

### 2. 回测完成时同步写 Portfolio

**文件:** `src/ginkgo/trading/analysis/backtest_result_aggregator.py`

在 `aggregate_and_save()` 方法末尾新增：
```python
# 同步指标到 MPortfolio
portfolio_service = container.services.portfolio()
portfolio_service.update_performance(
    portfolio_id=portfolio_id,
    annual_return=metrics.get("annual_return", 0.0),
    sharpe_ratio=metrics.get("sharpe_ratio", 0.0),
    max_drawdown=metrics.get("max_drawdown", 0.0),
    win_rate=metrics.get("trade_win_rate", metrics.get("win_rate", 0.0)),
)
```

### 3. Portfolio Service 新增 update_performance 方法

**文件:** `src/ginkgo/data/services/portfolio_service.py`

新增方法，接收绩效指标并更新 `MPortfolio` 记录。

## 前端改动

### 文件: `web-ui/src/views/portfolio/PortfolioList.vue`

1. 卡片 body 替换为 2x2 绩效网格
2. 卡片底部新增关联摘要条区域
3. 颜色规则：正值绿 / 负值红 / 中性橙 / 无数据灰

### 文件: `web-ui/src/stores/portfolio.ts`

处理列表 API 返回的新字段（绩效指标 + 关联信息）。

## 涉及文件

| 文件 | 改动 |
|------|------|
| `api/api/portfolio.py` | 列表 API 返回绩效指标 + 关联摘要 |
| `src/ginkgo/trading/analysis/backtest_result_aggregator.py` | 回测完成时同步写 Portfolio |
| `src/ginkgo/data/services/portfolio_service.py` | 新增 `update_performance()` |
| `web-ui/src/views/portfolio/PortfolioList.vue` | 卡片绩效网格 + 关联摘要条 |
| `web-ui/src/stores/portfolio.ts` | 处理新字段 |

## 不做的事

- 不做树形/分组布局
- 不做 tab 切换
- 不修改 MPortfolio 模型（字段已存在）
- 不改变筛选逻辑（保持现有行为）
