# TradeWinRate 设计文档

> 交易维度胜率分析器 — 每个完整仓位生命周期算一笔交易

## 背景

当前 `WinRate` 分析器统计的是**盈利天数占比**（日维度），不是**盈利交易笔数占比**（交易维度）。在量化交易中，胜率通常指后者。

## 方案

新增 `TradeWinRate` 分析器，监听 ORDERPARTIALLYFILLED 阶段，通过 `portfolio_info["positions"]` 检测完整平仓的 position，统计交易维度胜率。

### 前置修复：hook 触发时机

当前 ORDERPARTIALLYFILLED / ORDERFILLED / ORDERCANCELACK 的 hook 在业务逻辑**之前**触发，分析器看到的是旧状态。需要移到业务逻辑**之后**。

**移动位置：**

| Hook | 当前位置 | 移动到 | 变更 |
|------|---------|--------|------|
| ORDERPARTIALLYFILLED | L567（deal 之前） | L692 之后（update_worth/profit 之后） | 移动 |
| ORDERFILLED | L836（on_order_partially_filled 之前） | L843 之后（on_order_partially_filled 之后） | 移动 |
| ORDERCANCELACK | L764（unfreeze 之前） | L827 之后（update_worth/profit 之后） | 移动 |

**风险评估：**
- 没有现有分析器监听这三个阶段，零破坏风险
- 移动后 hook 不再对无效/失败的 fill 触发，语义更正确
- ENDDAY/NEWDAY 的 hook 已经在逻辑之后，不受影响

### clean_positions 实现

当前 `clean_positions()` 是空操作（方法未实现）。移到 ENDDAY hooks 之后执行：

```python
# ENDDAY 阶段（advance_time 中）
# 1. 业务逻辑（结算、信号重发等）
# 2. update_worth / update_profit
# 3. ENDDAY hooks（分析器触发，可看到当日平仓的 position）
# 4. clean_positions()（移除 total_position == 0 的 position）
# 5. NEWDAY hooks
```

### 交易维度胜率定义

一个 Position 从首次买入到完全清空（`total_position == 0`）= 一笔完整交易。
- `realized_pnl > 0` → 盈利
- `realized_pnl < 0` → 亏损
- `realized_pnl == 0` → 不计入
- `win_rate = 盈利笔数 / (盈利笔数 + 亏损笔数)`

### TradeWinRate 分析器

监听 ORDERPARTIALLYFILLED 阶段（hook 已移到 deal 之后），检查 positions dict 中是否有完整平仓：

```python
class TradeWinRate(BaseAnalyzer):
    def __init__(self):
        self.add_active_stage(RECORDSTAGE_TYPES.ORDERPARTIALLYFILLED)
        self.set_record_stage(RECORDSTAGE_TYPES.ENDDAY)
        self._counted_positions = set()
        self._win_count = 0
        self._loss_count = 0

    def _do_activate(self, stage, portfolio_info):
        positions = portfolio_info.get("positions", {})
        for code, pos in positions.items():
            if pos.total_position == 0 and pos.uuid not in self._counted_positions:
                self._counted_positions.add(pos.uuid)
                pnl = float(pos.realized_pnl)
                if pnl > 0:
                    self._win_count += 1
                elif pnl < 0:
                    self._loss_count += 1

        total = self._win_count + self._loss_count
        win_rate = self._win_count / total if total > 0 else 0.0
        self.add_data(win_rate)
```

### 为什么不在 ENDDAY 激活

- ENDDAY 时 clean_positions 已经执行，平仓的 position 已被移除
- ORDERPARTIALLYFILLED（移动后）在 deal 之后触发，position 还在 dict 中，total_position 已更新为 0
- 使用 `_counted_positions` set 避免同一 position 重复计数

### 边界情况

| 场景 | 处理 |
|------|------|
| 买入 1000 股，分 3 次卖完 | 前 2 次部分卖 total_position > 0 不计数，第 3 次清空时计为 1 笔 |
| 买入后加仓，一次卖完 | 算 1 笔，realized_pnl 基于加权平均成本 |
| 同日卖光再买入同一股票 | 旧 position 被 clean 清除，新 position 是新对象（新 uuid），不影响 |
| 回测结束仍有持仓 | 未平仓不计入（不是完整交易） |

## 受影响文件

```
src/ginkgo/trading/portfolios/t1backtest.py                    # 修改: hook 移位 + clean_positions 实现
src/ginkgo/trading/analysis/analyzers/trade_win_rate.py        # 新增: TradeWinRate 分析器
src/ginkgo/trading/bases/portfolio_base.py                     # 修改: DEFAULT_ANALYZER_SET 注册
src/ginkgo/trading/analysis/backtest_result_aggregator.py      # 修改: 读取 trade_win_rate 值
```

## 不做的事

- 不修改现有 WinRate 分析器（日维度胜率保留）
- 不修改 BaseAnalyzer
- 不修改 Vector/ClickHouse 配置
