# TradeWinRate 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增 TradeWinRate 分析器（交易维度胜率），修复 hook 触发时机，实现 clean_positions。

**Architecture:** 前置修复 hook 时序（ORDERPARTIALLYFILLED/FILLED/CANCELACK 移到逻辑后）→ 实现 clean_positions（ENDDAY 后清理）→ 新增 TradeWinRate 分析器 → 注册到默认分析器集 → 端到端验证。

**Tech Stack:** Python 3.12, 现有 BaseAnalyzer 框架, Position.realized_pnl

---

### Task 1: 修复 hook 触发时机 — 移到业务逻辑之后

**Files:**
- Modify: `src/ginkgo/trading/portfolios/t1backtest.py`

**风险：零。** 没有现有分析器监听 ORDERPARTIALLYFILLED / ORDERFILLED / ORDERCANCELACK。

- [ ] **Step 1: 移动 ORDERPARTIALLYFILLED hooks**

将 L567-570 的 hook 调用移到 L692 之后（update_worth/update_profit 之后）。

当前位置（L567-570）删除：
```python
            for func in self._analyzer_activate_hook[RECORDSTAGE_TYPES.ORDERPARTIALLYFILLED]:
                func(RECORDSTAGE_TYPES.ORDERPARTIALLYFILLED, self.get_info())
            for func in self._analyzer_record_hook[RECORDSTAGE_TYPES.ORDERPARTIALLYFILLED]:
                func(RECORDSTAGE_TYPES.ORDERPARTIALLYFILLED, self.get_info())
```

移到 L692（`self.update_profit()` 之后）插入：
```python
            # 分析器 hooks：在 fill 处理完成后触发，确保 portfolio_info 包含最新状态
            for func in self._analyzer_activate_hook[RECORDSTAGE_TYPES.ORDERPARTIALLYFILLED]:
                func(RECORDSTAGE_TYPES.ORDERPARTIALLYFILLED, self.get_info())
            for func in self._analyzer_record_hook[RECORDSTAGE_TYPES.ORDERPARTIALLYFILLED]:
                func(RECORDSTAGE_TYPES.ORDERPARTIALLYFILLED, self.get_info())
```

- [ ] **Step 2: 移动 ORDERFILLED hooks**

在 `on_order_filled` 方法中，将 hooks 移到 `self.on_order_partially_filled(event)` 之后。

当前位置（L836-839）删除：
```python
            for func in self._analyzer_activate_hook.get(RECORDSTAGE_TYPES.ORDERFILLED, []):
                func(RECORDSTAGE_TYPES.ORDERFILLED, self.get_info())
            for func in self._analyzer_record_hook.get(RECORDSTAGE_TYPES.ORDERFILLED, []):
                func(RECORDSTAGE_TYPES.ORDERFILLED, self.get_info())
```

移到 `self.on_order_partially_filled(event)` 调用之后插入：
```python
            # 分析器 hooks：在完整成交处理完成后触发
            for func in self._analyzer_activate_hook.get(RECORDSTAGE_TYPES.ORDERFILLED, []):
                func(RECORDSTAGE_TYPES.ORDERFILLED, self.get_info())
            for func in self._analyzer_record_hook.get(RECORDSTAGE_TYPES.ORDERFILLED, []):
                func(RECORDSTAGE_TYPES.ORDERFILLED, self.get_info())
```

- [ ] **Step 3: 移动 ORDERCANCELACK hooks**

将 ORDERCANCELED 和 ORDERCANCELACK 的 hooks 移到 `update_worth/update_profit` 之后。

当前位置（L765-774）删除：
```python
            for func in self._analyzer_activate_hook[RECORDSTAGE_TYPES.ORDERCANCELED]:
                func(RECORDSTAGE_TYPES.ORDERCANCELED, self.get_info())
            for func in self._analyzer_record_hook[RECORDSTAGE_TYPES.ORDERCANCELED]:
                func(RECORDSTAGE_TYPES.ORDERCANCELED, self.get_info())

            # 处理ORDERCANCELACK阶段的hooks
            for func in self._analyzer_activate_hook[RECORDSTAGE_TYPES.ORDERCANCELACK]:
                func(RECORDSTAGE_TYPES.ORDERCANCELACK, self.get_info())
            for func in self._analyzer_record_hook[RECORDSTAGE_TYPES.ORDERCANCELACK]:
                func(RECORDSTAGE_TYPES.ORDERCANCELACK, self.get_info())
```

移到 `update_worth/update_profit` 之后（L827 附近）插入：
```python
            # 分析器 hooks：在取消处理完成后触发
            for func in self._analyzer_activate_hook[RECORDSTAGE_TYPES.ORDERCANCELED]:
                func(RECORDSTAGE_TYPES.ORDERCANCELED, self.get_info())
            for func in self._analyzer_record_hook[RECORDSTAGE_TYPES.ORDERCANCELED]:
                func(RECORDSTAGE_TYPES.ORDERCANCELED, self.get_info())
            for func in self._analyzer_activate_hook[RECORDSTAGE_TYPES.ORDERCANCELACK]:
                func(RECORDSTAGE_TYPES.ORDERCANCELACK, self.get_info())
            for func in self._analyzer_record_hook[RECORDSTAGE_TYPES.ORDERCANCELACK]:
                func(RECORDSTAGE_TYPES.ORDERCANCELACK, self.get_info())
```

- [ ] **Step 4: 验证现有分析器不受影响**

```bash
grep -rn 'ORDERPARTIALLYFILLED\|ORDERFILLED\|ORDERCANCELACK' src/ginkgo/trading/analysis/analyzers/
```

预期：只在 `portfolio_base.py` 的 DEFAULT_ANALYZER_SET 定义中出现（注册空列表），无分析器实际监听。

- [ ] **Step 5: Commit**

```bash
git add src/ginkgo/trading/portfolios/t1backtest.py
git commit -m "fix: move ORDERPARTIALLYFILLED/FILLED/CANCELACK hooks to post-logic"
```

---

### Task 2: 实现 clean_positions + 移到 ENDDAY

**Files:**
- Modify: `src/ginkgo/trading/portfolios/t1backtest.py`

- [ ] **Step 1: 在 advance_time 的 ENDDAY hooks 之后添加 clean_positions**

在 `advance_time` 方法中，ENDDAY record hooks 之后、NEWDAY hooks 之前（约 L203 之后），添加：

```python
        # 清理已完成平仓的 position（total_position == 0）
        self._clean_closed_positions()
```

- [ ] **Step 2: 实现 _clean_closed_positions 方法**

在 t1backtest.py 中新增方法：

```python
    def _clean_closed_positions(self):
        """清理 total_position == 0 的持仓"""
        closed_codes = [
            code for code, pos in self._positions.items()
            if pos.total_position == 0
        ]
        for code in closed_codes:
            del self._positions[code]
```

- [ ] **Step 3: 移除 SHORT fill 路径中的 clean_positions 调用**

将 L685 和 L905 的 `self.clean_positions()` 调用移除（现在由 ENDDAY 统一清理）。

- [ ] **Step 4: Commit**

```bash
git add src/ginkgo/trading/portfolios/t1backtest.py
git commit -m "feat: implement clean_positions at ENDDAY stage"
```

---

### Task 3: 新增 TradeWinRate 分析器

**Files:**
- Create: `src/ginkgo/trading/analysis/analyzers/trade_win_rate.py`

- [ ] **Step 1: 创建 TradeWinRate 分析器**

```python
# src/ginkgo/trading/analysis/analyzers/trade_win_rate.py

from ginkgo.trading.analysis.analyzers.base_analyzer import BaseAnalyzer
from ginkgo.enums import RECORDSTAGE_TYPES


class TradeWinRate(BaseAnalyzer):
    """交易维度胜率分析器

    每个完整仓位生命周期（买入→全部卖出）算一笔交易。
    win_rate = 盈利笔数 / (盈利笔数 + 亏损笔数)
    """

    __abstract__ = False

    def __init__(self, name: str = "trade_win_rate", *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        self.add_active_stage(RECORDSTAGE_TYPES.ORDERPARTIALLYFILLED)
        self.set_record_stage(RECORDSTAGE_TYPES.ENDDAY)

        self._counted_positions = set()
        self._win_count = 0
        self._loss_count = 0

    def _do_activate(self, stage, portfolio_info, *args, **kwargs):
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

    @property
    def win_count(self) -> int:
        return self._win_count

    @property
    def loss_count(self) -> int:
        return self._loss_count

    @property
    def total_trades(self) -> int:
        return self._win_count + self._loss_count
```

- [ ] **Step 2: Commit**

```bash
git add src/ginkgo/trading/analysis/analyzers/trade_win_rate.py
git commit -m "feat: add TradeWinRate analyzer for trade-level win rate"
```

---

### Task 4: 注册到默认分析器集

**Files:**
- Modify: `src/ginkgo/trading/bases/portfolio_base.py`

- [ ] **Step 1: 在 _ANALYZER_CLASS_MAP 中注册 TradeWinRate**

在 `portfolio_base.py` 的 `_ANALYZER_CLASS_MAP` 字典中添加：

```python
'trade_win_rate': TradeRateWinRate,
```

以及对应的 import。

- [ ] **Step 2: 在 DEFAULT_ANALYZER_SET.STANDARD 列表中添加**

将 `'trade_win_rate'` 加入 STANDARD 分析器集的列表中。

- [ ] **Step 3: Commit**

```bash
git add src/ginkgo/trading/bases/portfolio_base.py
git commit -m "feat: register TradeWinRate in default analyzer set"
```

---

### Task 5: BacktestResultAggregator 读取 trade_win_rate

**Files:**
- Modify: `src/ginkgo/trading/analysis/backtest_result_aggregator.py`

- [ ] **Step 1: 添加 ANALYZER_TRADE_WIN_RATE 常量**

在现有常量旁添加：
```python
ANALYZER_TRADE_WIN_RATE = "trade_win_rate"
```

- [ ] **Step 2: 在 _aggregate_metrics 中读取 trade_win_rate 值**

在现有的 `ANALYZER_WIN_RATE` 读取逻辑之后，添加对 `ANALYZER_TRADE_WIN_RATE` 的读取，覆盖 `metrics["win_rate"]`（优先使用交易维度的胜率）。

```python
            # 获取交易维度胜率（优先覆盖日维度胜率）
            trade_win_rate_result = self._analyzer_service.get_by_task_id(
                task_id=task_id,
                portfolio_id=portfolio_id,
                analyzer_name=self.ANALYZER_TRADE_WIN_RATE,
                limit=1000
            )
            df = self._get_dataframe(trade_win_rate_result)
            if df is not None and len(df) > 0:
                trade_win_rate = float(df['value'].iloc[0])
                metrics["trade_win_rate"] = trade_win_rate
```

- [ ] **Step 3: 在 backtest_task 表中存储 trade_win_rate**

确认 `backtest_task` model 是否有 `trade_win_rate` 字段。如果没有，用现有的 `win_rate` 字段存储（两个胜率可以都保留）。

- [ ] **Step 4: Commit**

```bash
git add src/ginkgo/trading/analysis/backtest_result_aggregator.py
git commit -m "feat: aggregate trade_win_rate in BacktestResultAggregator"
```

---

### Task 6: 端到端验证

**Files:** 无代码变更

- [ ] **Step 1: 运行 CLI 回测**

```bash
ginkgo backtest create --portfolio bb739b51f0634fb0b4403298443b516d --start 2024-01-01 --end 2024-03-31 --name "TradeWinRate验证"
ginkgo backtest run <uuid>
```

- [ ] **Step 2: 验证 trade_win_rate 分析器有数据**

```sql
SELECT * FROM ginkgo_analyzer_record
WHERE name = 'trade_win_rate' AND task_id = '<uuid>'
ORDER BY timestamp DESC LIMIT 5
```

预期：有记录，value 为 0.0~1.0 之间的胜率值。

- [ ] **Step 3: 验证 backtest_task 的 win_rate 字段**

```bash
ginkgo backtest cat <uuid>
```

预期：Win Rate 字段有合理的非零值（基于交易维度）。

- [ ] **Step 4: 对比日维度和交易维度胜率**

通过 analyzer 记录分别查看 `win_rate`（日维度）和 `trade_win_rate`（交易维度），确认两者数值不同且交易维度值合理。

- [ ] **Step 5: Commit 验证结果（如有修复）**
