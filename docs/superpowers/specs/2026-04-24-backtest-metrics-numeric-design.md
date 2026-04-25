# backtest_task 指标字段 String → Float 迁移设计

## Context

`MBacktestTask` 的 6 个指标字段（`total_pnl`, `max_drawdown`, `sharpe_ratio`, `annual_return`, `win_rate`, `final_portfolio_value`）从创建之初就是 `String(32)`，没有刻意的设计决策。`progress` 字段此前已从 String 迁移为 Integer（commit `bad93987`）。String 类型导致无法数值比较/排序、前端需要 parseFloat、容易存入脏值。

## 决策

- **类型**：全部改为 `Float`（用户选择）
- **策略**：一次性切换，不保留兼容层（无外部 API 消费者）

## 修改清单

### 1. 模型层 — `src/ginkgo/data/models/model_backtest_task.py`
- 第 90-95 行：`String(32), default="0"` → `Float, default=0.0`，类型 `Mapped[Optional[float]]`
- 第 120-125 行 `update()` 方法：参数 `str = "0"` → `float = 0.0`
- 第 206-217 行 `update(Series)` 方法：去掉 `str()` 包装
- 第 241-266 行 `finish_task()` 方法：参数 `str = "0"` → `float = 0.0`

### 2. CRUD 层 — `src/ginkgo/data/crud/backtest_task_crud.py`
- 第 91-96 行：`kwargs.get(..., "0")` → `kwargs.get(..., 0.0)`

### 3. 汇总器 — `src/ginkgo/trading/analysis/backtest_result_aggregator.py`
- 第 203-210 行：metrics 初始化 `"0"` → `0.0`，返回类型 → `Dict[str, float]`
- 第 228-287 行：去掉 `str()` 包装
- 第 110-121 行：`metrics.get(..., "0")` → `metrics.get(..., 0.0)`

### 4. Worker — `src/ginkgo/workers/backtest_worker/progress_tracker.py`
- 第 226-237 行：`str(result.get(..., "0"))` → `result.get(..., 0.0)`
- 第 253 行 WebSocket 通知：`str(result.get(..., "0"))` → `result.get(..., 0.0)`

### 5. API 层 — `api/api/backtest.py`
- `BacktestTaskSummary`（第 64-83 行）：`str = "0"` → `float = 0.0`
- `BacktestTaskDetail`（第 86-111 行）：同上
- 列表 endpoint（第 375-383 行）：`getattr(task, ..., '0') or '0'` → `getattr(task, ..., 0.0) or 0.0`
- 详情 endpoint（第 510-525 行）：同上

### 6. 数据库迁移 — `migrations/mysql/versions/` 新增脚本
```sql
ALTER TABLE backtest_tasks MODIFY COLUMN final_portfolio_value FLOAT DEFAULT 0.0;
ALTER TABLE backtest_tasks MODIFY COLUMN total_pnl FLOAT DEFAULT 0.0;
ALTER TABLE backtest_tasks MODIFY COLUMN max_drawdown FLOAT DEFAULT 0.0;
ALTER TABLE backtest_tasks MODIFY COLUMN sharpe_ratio FLOAT DEFAULT 0.0;
ALTER TABLE backtest_tasks MODIFY COLUMN annual_return FLOAT DEFAULT 0.0;
ALTER TABLE backtest_tasks MODIFY COLUMN win_rate FLOAT DEFAULT 0.0;
```

## 验证
1. `alembic upgrade head` 执行迁移
2. 运行一个回测任务，确认完成后 DB 中指标字段为数值
3. `GET /api/v1/backtests/` 确认返回 JSON 中指标为 number 而非 string
4. 前端回测列表页面正确显示各项指标
