# 分段稳定性动态指标选择 设计

## 概述

分段稳定性验证页面支持动态指标选择 — 用户从回测已有的分析器中选择指标进行分段对比，而非固定 4 个指标。

## 背景

当前 `SegmentStability.vue` 和后端 `ValidationService` 固定计算 4 个指标（收益率、夏普比率、最大回撤、胜率），均基于 `net_value` 分析器数据重新计算。

系统有 21 个分析器（SortinoRatio、Volatility、CalmarRatio、TradeWinRate、ProfitFactor 等），分析器时序数据已存储在 ClickHouse `analyzer_record` 表中。用户希望自由选择关注的分析器进行分段对比。

## 变更范围

| 文件 | 变更 |
|------|------|
| `api/api/validation.py` | 新增 `/available-metrics` 端点，修改 `/segment-stability` 接受 `metrics` 参数 |
| `src/ginkgo/data/services/validation_service.py` | 新增 `get_available_metrics()` 方法，修改 `segment_stability()` 按指定分析器聚合 |
| `web-ui/src/api/modules/validation.ts` | 新增 `availableMetrics()` 接口和 `SegmentStabilityConfig` 增加 `metrics` 字段 |
| `web-ui/src/views/portfolio/validation/SegmentStability.vue` | 新增指标 tag 多选器，概览图/详情图根据选中指标动态渲染 |

## 新增依赖

无

## API 设计

### 1. 获取可用指标

```
GET /api/v1/validation/available-metrics?task_id=xxx&portfolio_id=xxx
```

**后端逻辑：**
- 查询 `analyzer_record` 表，按 `task_id` + `portfolio_id` 过滤
- `SELECT DISTINCT name FROM analyzer_record WHERE task_id = ? AND portfolio_id = ?`
- 返回去重的分析器名称列表，附带中文标签

**响应：**
```json
{
  "metrics": [
    { "name": "net_value", "label": "净值" },
    { "name": "sharpe_ratio", "label": "夏普比率" },
    { "name": "max_drawdown", "label": "最大回撤" },
    { "name": "win_rate", "label": "胜率" },
    { "name": "sortino_ratio", "label": "Sortino 比率" },
    { "name": "volatility", "label": "波动率" }
  ]
}
```

**分析器名称 → 中文标签映射**（后端硬编码映射表，21 个分析器）：
| analyzer_name | 中文标签 |
|---|---|
| net_value | 净值 |
| ProfitAna | 每日盈亏 |
| annualized_return | 年化收益 |
| sharpe_ratio | 夏普比率 |
| max_drawdown | 最大回撤 |
| win_rate | 胜率 |
| hold_pct | 仓位占比 |
| order_count | 订单数 |
| signal_count | 信号数 |
| sortino_ratio | Sortino 比率 |
| calmar_ratio | Calmar 比率 |
| volatility | 波动率 |
| underwater_time | 水下时间 |
| var_cvar | VaR |
| skew_kurtosis | 偏度/峰度 |
| consecutive_pnl | 连续盈亏 |
| trade_win_rate | 交易胜率 |
| avg_win_loss_ratio | 盈亏比 |
| profit_factor | 利润因子 |
| avg_holding_period | 平均持仓天数 |
| max_consecutive_losses | 最大连亏次数 |

### 2. 修改分段稳定性接口

```
POST /api/v1/validation/segment-stability
```

**新增请求参数：** `metrics: Optional[List[str]]` — 分析器名称列表，默认 `["annualized_return", "sharpe_ratio", "max_drawdown", "win_rate"]`

**后端逻辑变更：**
- 现有 `_calc_segment_metrics()` 仅基于 net_value 重新计算 4 个固定指标 → **废弃**
- 新逻辑：对 `metrics` 列表中的每个分析器，从 `analyzer_record` 查询时序数据，按时间段分组取均值
- 返回格式变更：`segments` 中每段的指标为动态 key

**响应：**
```json
{
  "windows": [
    {
      "n_segments": 4,
      "stability_score": 0.72,
      "segments": [
        {
          "annualized_return": 0.15,
          "sharpe_ratio": 1.2,
          "max_drawdown": -0.08,
          "win_rate": 0.55
        }
      ],
      "available_metrics": ["annualized_return", "sharpe_ratio", "max_drawdown", "win_rate"]
    }
  ]
}
```

## 前端设计

### 交互流程

1. 用户选择回测任务
2. 前端调用 `available-metrics` 获取指标列表
3. 指标 tag 多选器渲染，默认选中 4 个核心指标（annualized_return, sharpe_ratio, max_drawdown, win_rate）
4. 用户选择分段数 + 指标 → 点击"开始分析"
5. 后端按段聚合所选分析器的时序数据（段内均值）
6. 概览图/详情图根据选中指标动态渲染折线

### 指标选择器 UI

样式与现有分段数 tag 选择器一致：
- 多行 tag 布局，选中态为蓝色高亮
- 底部显示"已选 N / M 个指标"
- 未选择任务时显示占位提示"请先选择任务"

### 图表渲染

**概览图：** 为每个选中的指标生成一条折线，多 Y 轴（最多 3 个 Y 轴，超过 3 个指标时共用轴）。颜色从预设调色板循环取。

**详情图：** 每段分析卡片内，所有选中指标共用一张折线图。数据表格列动态生成。

**稳定性评分：** 基于 `annualized_return` 计算各段收益的标准差/均值比（保持现有逻辑），不受指标选择影响。

## 后端实现要点

### ValidationService 变更

```python
def get_available_metrics(self, task_id: str, portfolio_id: str) -> list[dict]:
    """查询 analyzer_record 表中该任务实际存在的分析器名称"""
    records = self._analyzer_record_crud.get_by_task_id(
        task_id=task_id,
        portfolio_id=portfolio_id,
    )
    names = set(r.name for r in records)
    return [{"name": n, "label": ANALYZER_LABELS.get(n, n)} for n in sorted(names)]

def segment_stability(self, task_id, portfolio_id, n_segments_list, metrics):
    """按指定分析器分段聚合"""
    # 1. 获取回测时间范围（从 net_value 记录）
    # 2. 对每个 n_segments，等分时间段
    # 3. 对每个 metric，查询 analyzer_record 时序数据
    # 4. 按时间段分组取均值
    # 5. 计算稳定性评分（基于 annualized_return）
```

### 分析器标签映射

```python
ANALYZER_LABELS = {
    "net_value": "净值",
    "ProfitAna": "每日盈亏",
    "annualized_return": "年化收益",
    "sharpe_ratio": "夏普比率",
    "max_drawdown": "最大回撤",
    "win_rate": "胜率",
    "hold_pct": "仓位占比",
    "order_count": "订单数",
    "signal_count": "信号数",
    "sortino_ratio": "Sortino 比率",
    "calmar_ratio": "Calmar 比率",
    "volatility": "波动率",
    "underwater_time": "水下时间",
    "var_cvar": "VaR",
    "skew_kurtosis": "偏度/峰度",
    "consecutive_pnl": "连续盈亏",
    "trade_win_rate": "交易胜率",
    "avg_win_loss_ratio": "盈亏比",
    "profit_factor": "利润因子",
    "avg_holding_period": "平均持仓天数",
    "max_consecutive_losses": "最大连续亏损",
}
```

## 不做的事

- 不新增分析器，仅使用回测已有的分析器数据
- 不修改分析器注册或计算逻辑
- 不修改 `analyzer_record` 表结构
- 不支持自定义分析器指标的中文标签配置（硬编码映射表）
- 稳定性评分计算逻辑不变（基于 annualized_return）
