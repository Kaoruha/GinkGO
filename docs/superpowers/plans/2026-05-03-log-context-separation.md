# Log Context Separation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将日志 context 从 dict 值绑定改为 EngineContext 引用绑定 + 事件字段通过 structlog kwargs 传入，消除上下文累积污染。

**Architecture:** 三层数据通道——任务级字段通过 EngineContext 引用动态读取，事件级字段通过 structlog `_ginkgo` kwargs 单条传入，追踪级字段保持独立 ContextVar。

**Tech Stack:** Python 3.12, structlog, contextvars

---

## File Structure

| File | Responsibility |
|------|---------------|
| `src/ginkgo/trading/context/engine_context.py` | 添加 time_provider 引用和 business_timestamp 动态属性 |
| `src/ginkgo/libs/core/logger.py` | 重写 ginkgo_processor、bind_context、clear_context、19 个 log_*_event 方法，移除诊断代码 |
| `src/ginkgo/trading/engines/time_controlled_engine.py` | 装配时绑定 time_provider 到 EngineContext，删除 bind_context(business_timestamp) |
| `src/ginkgo/trading/engines/event_engine.py` | main_loop 中绑定 EngineContext 引用 |
| `src/ginkgo/workers/backtest_worker/task_processor.py` | 绑定 PortfolioContext 引用，移除诊断代码 |

---

### Task 1: EngineContext 扩展

**Files:**
- Modify: `src/ginkgo/trading/context/engine_context.py:38-92`

- [ ] **Step 1: 添加 `_time_provider` 属性和 `business_timestamp` 动态属性**

在 `__init__` 中添加 `_time_provider = None`，添加 `set_time_provider()` 方法和 `business_timestamp` property：

```python
def __init__(self, engine_id: str):
    self._engine_id = engine_id
    self._task_id: Optional[str] = None
    self._source_type: int = SOURCE_TYPES.OTHER
    self._time_provider = None  # 新增：ITimeProvider 引用

def set_time_provider(self, provider) -> None:
    """绑定时间提供者引用（仅 Engine 应调用）"""
    self._time_provider = provider

@property
def time_provider(self):
    """时间提供者引用"""
    return self._time_provider

@property
def business_timestamp(self):
    """动态读取当前业务时间（从 time_provider.now() 获取）"""
    if self._time_provider:
        return self._time_provider.now()
    return None
```

- [ ] **Step 2: 更新 `__repr__`**

```python
def __repr__(self) -> str:
    has_tp = "Y" if self._time_provider else "N"
    return f"EngineContext(engine_id={self._engine_id[:8]}..., task_id={self._task_id[:8] if self._task_id else None}..., tp={has_tp})"
```

- [ ] **Step 3: Commit**

```bash
git add src/ginkgo/trading/context/engine_context.py
git commit -m "refactor: add time_provider reference and business_timestamp property to EngineContext"
```

---

### Task 2: 重写核心日志基础设施

**Files:**
- Modify: `src/ginkgo/libs/core/logger.py:34-36` (ContextVar 类型)
- Modify: `src/ginkgo/libs/core/logger.py:160-200` (ginkgo_processor)
- Modify: `src/ginkgo/libs/core/logger.py:878-938` (bind_context/clear_context)

- [ ] **Step 1: 修改 `_business_context_ctx` 类型注解**

将 line 34-36 从 `Dict[str, Any]` 改为 `Optional[Any]`，default 从 `{}` 改为 `None`：

```python
_business_context_ctx: contextvars.ContextVar[Optional[Any]] = contextvars.ContextVar(
    "business_context", default=None
)
```

- [ ] **Step 2: 重写 `ginkgo_processor`（line 160-200）**

替换整个函数体。新逻辑：从 EngineContext 引用读取任务级字段，从 `_ginkgo` 读取事件级字段：

```python
def ginkgo_processor(logger, log_method, event_dict):
    """
    Ginkgo 业务字段处理器

    三层数据通道：
    1. 任务级：从 EngineContext 引用动态读取（task_id, engine_id, portfolio_id, business_timestamp）
    2. 事件级：从 _ginkgo kwargs 读取（event_type, symbol, order_id 等，每条日志独立）
    3. 追踪级：从独立 ContextVar 读取（trace_id, span_id）
    """
    if "ginkgo" not in event_dict:
        event_dict["ginkgo"] = {}

    # 1. 从 EngineContext 引用动态读取任务级字段
    engine_ctx = _business_context_ctx.get()
    if engine_ctx is not None:
        if hasattr(engine_ctx, 'task_id') and engine_ctx.task_id:
            event_dict["ginkgo"]["task_id"] = engine_ctx.task_id
        if hasattr(engine_ctx, 'engine_id') and engine_ctx.engine_id:
            event_dict["ginkgo"]["engine_id"] = engine_ctx.engine_id
        if hasattr(engine_ctx, 'source_type') and engine_ctx.source_type is not None:
            event_dict["ginkgo"]["source_type"] = engine_ctx.source_type
        if hasattr(engine_ctx, 'business_timestamp') and engine_ctx.business_timestamp:
            event_dict["ginkgo"]["business_timestamp"] = engine_ctx.business_timestamp
        if hasattr(engine_ctx, 'portfolio_id') and engine_ctx.portfolio_id:
            event_dict["ginkgo"]["portfolio_id"] = engine_ctx.portfolio_id

    # 2. 从 _ginkgo 读取事件级字段（单条日志传入）
    event_fields = event_dict.pop("_ginkgo", {})
    event_dict["ginkgo"].update(event_fields)

    # 3. log_category
    log_category = _log_category_ctx.get()
    if log_category:
        event_dict["ginkgo"]["log_category"] = log_category

    # 4. trace_id / span_id（独立 ContextVar）
    trace_id = _trace_id_ctx.get()
    span_id = _span_id_ctx.get()
    if trace_id or span_id:
        event_dict["trace"] = {}
        if trace_id:
            event_dict["trace"]["id"] = trace_id
        if span_id:
            event_dict["trace"]["span_id"] = span_id

    return event_dict
```

- [ ] **Step 3: 重写 `bind_context`（line 878-912）**

替换整个方法。只接受 EngineContext/PortfolioContext 引用：

```python
def bind_context(self, engine_context=None) -> None:
    """
    绑定引擎上下文引用

    Args:
        engine_context: EngineContext 或 PortfolioContext 实例引用
    """
    if engine_context is not None:
        from ginkgo.trading.context.engine_context import EngineContext
        from ginkgo.trading.context.portfolio_context import PortfolioContext
        if not isinstance(engine_context, (EngineContext, PortfolioContext)):
            raise TypeError(
                f"bind_context only accepts EngineContext/PortfolioContext, got {type(engine_context).__name__}"
            )
        _business_context_ctx.set(engine_context)
```

- [ ] **Step 4: 重写 `clear_context`（line 930-938）**

```python
def clear_context(self) -> None:
    """清除上下文引用和日志类别"""
    _business_context_ctx.set(None)
    _log_category_ctx.set(None)
```

- [ ] **Step 5: 删除 `unbind_context`（line 914-928）**

整个方法删除（引用模式下无需逐字段解绑）。

- [ ] **Step 6: Commit**

```bash
git add src/ginkgo/libs/core/logger.py
git commit -m "refactor: rewrite ginkgo_processor and bind_context for EngineContext reference model"
```

---

### Task 3: 转换 log_*_event 方法

**Files:**
- Modify: `src/ginkgo/libs/core/logger.py:961-1474` (19 个方法)

所有方法从 `bind_context + INFO/ERROR/WARN` 改为 `structlog.get_logger().info(msg, _ginkgo={...})`。

- [ ] **Step 1: 转换信号和订单类方法（line 961-1043）**

```python
def log_signal_event(self, symbol: str, direction: str, **kwargs):
    self.set_log_category("backtest")
    structlog.get_logger(self.logger_name).info(
        f"Signal generated: {direction} {symbol}",
        _ginkgo={
            "event_type": "SIGNALGENERATION",
            "symbol": symbol,
            "direction": direction,
            **kwargs
        }
    )

def log_order_event(self, order_id: str, **kwargs):
    self.set_log_category("backtest")
    structlog.get_logger(self.logger_name).info(
        f"Order submitted: {order_id}",
        _ginkgo={
            "event_type": "ORDERSUBMITTED",
            "order_id": order_id,
            **kwargs
        }
    )

def log_order_fill_event(self, order_id: str, price: Number, volume: int, **kwargs):
    self.set_log_category("backtest")
    structlog.get_logger(self.logger_name).info(
        f"Order filled: {order_id} @ {price} x{volume}",
        _ginkgo={
            "event_type": "ORDERFILLED",
            "order_id": order_id,
            "transaction_price": price,
            "transaction_volume": volume,
            **kwargs
        }
    )
```

- [ ] **Step 2: 转换持仓和资金类方法（line 1045-1096）**

```python
def log_position_event(self, symbol: str, volume: int, **kwargs):
    self.set_log_category("backtest")
    structlog.get_logger(self.logger_name).info(
        f"Position updated: {symbol} {volume} shares",
        _ginkgo={
            "event_type": "POSITIONUPDATE",
            "position_code": symbol,
            "position_volume": volume,
            **kwargs
        }
    )

def log_capital_event(self, total_value: Number, available_cash: Number, **kwargs):
    self.set_log_category("backtest")
    structlog.get_logger(self.logger_name).info(
        f"Capital updated: total={total_value}, cash={available_cash}",
        _ginkgo={
            "event_type": "CAPITALUPDATE",
            "total_value": total_value,
            "available_cash": available_cash,
            **kwargs
        }
    )
```

- [ ] **Step 3: 转换风控和组件类方法（line 1098-1161）**

```python
def log_risk_event(self, risk_type: str, risk_reason: str, **kwargs):
    self.set_log_category("backtest")
    structlog.get_logger(self.logger_name).warning(
        f"Risk event: {risk_type} - {risk_reason}",
        _ginkgo={
            "event_type": "RISKBREACH",
            "risk_type": risk_type,
            "risk_reason": risk_reason,
            **kwargs
        }
    )

def log_component_event(self, component_name: str, message: str, **kwargs):
    self.set_log_category("component")
    structlog.get_logger(self.logger_name).info(
        message,
        _ginkgo={
            "component_name": component_name,
            **kwargs
        }
    )

def log_performance_event(self, function_name: str, duration_ms: float, **kwargs):
    self.set_log_category("performance")
    structlog.get_logger(self.logger_name).info(
        f"Performance: {function_name} took {duration_ms}ms",
        _ginkgo={
            "function_name": function_name,
            "duration_ms": duration_ms,
            **kwargs
        }
    )
```

- [ ] **Step 4: 转换订单异常类方法（line 1165-1258）**

```python
def log_order_rejected_event(self, order_id: str, reject_code: str, reject_reason: str, **kwargs):
    self.set_log_category("backtest")
    structlog.get_logger(self.logger_name).error(
        f"Order rejected: {order_id} - {reject_code}: {reject_reason}",
        _ginkgo={
            "event_type": "ORDERREJECTED",
            "order_id": order_id,
            "reject_code": reject_code,
            "reject_reason": reject_reason,
            **kwargs
        }
    )

def log_order_cancelled_event(self, order_id: str, cancel_reason: str, **kwargs):
    self.set_log_category("backtest")
    structlog.get_logger(self.logger_name).warning(
        f"Order cancelled: {order_id} - {cancel_reason}",
        _ginkgo={
            "event_type": "ORDERCANCELACK",
            "order_id": order_id,
            "cancel_reason": cancel_reason,
            **kwargs
        }
    )

def log_order_ack_event(self, order_id: str, broker_order_id: str, **kwargs):
    self.set_log_category("backtest")
    structlog.get_logger(self.logger_name).info(
        f"Order acknowledged: {order_id} -> {broker_order_id}",
        _ginkgo={
            "event_type": "ORDERACK",
            "order_id": order_id,
            "broker_order_id": broker_order_id,
            **kwargs
        }
    )

def log_order_expired_event(self, order_id: str, expire_reason: str, **kwargs):
    self.set_log_category("backtest")
    structlog.get_logger(self.logger_name).warning(
        f"Order expired: {order_id} - {expire_reason}",
        _ginkgo={
            "event_type": "ORDEREXPIRED",
            "order_id": order_id,
            "expire_reason": expire_reason,
            **kwargs
        }
    )
```

- [ ] **Step 5: 转换执行类方法（line 1260-1364）**

```python
def log_execution_rejected_event(self, tracking_id: str, reject_reason: str, **kwargs):
    self.set_log_category("backtest")
    structlog.get_logger(self.logger_name).error(
        f"Execution rejected: {tracking_id} - {reject_reason}",
        _ginkgo={
            "event_type": "EXECUTIONREJECTION",
            "tracking_id": tracking_id,
            "reject_reason": reject_reason,
            **kwargs
        }
    )

def log_execution_timeout_event(self, tracking_id: str, **kwargs):
    self.set_log_category("backtest")
    structlog.get_logger(self.logger_name).error(
        f"Execution timeout: {tracking_id}",
        _ginkgo={
            "event_type": "EXECUTIONTIMEOUT",
            "tracking_id": tracking_id,
            **kwargs
        }
    )

def log_execution_confirm_event(
    self, tracking_id: str, expected_price: Number, actual_price: Number,
    expected_volume: int, actual_volume: int, **kwargs
):
    self.set_log_category("backtest")
    structlog.get_logger(self.logger_name).info(
        f"Execution confirmed: {tracking_id}",
        _ginkgo={
            "event_type": "EXECUTIONCONFIRMATION",
            "tracking_id": tracking_id,
            "expected_price": expected_price,
            "actual_price": actual_price,
            "expected_volume": expected_volume,
            "actual_volume": actual_volume,
            **kwargs
        }
    )

def log_execution_cancel_event(self, tracking_id: str, cancel_reason: str, **kwargs):
    self.set_log_category("backtest")
    structlog.get_logger(self.logger_name).warning(
        f"Execution cancelled: {tracking_id} - {cancel_reason}",
        _ginkgo={
            "event_type": "EXECUTIONCANCELLATION",
            "tracking_id": tracking_id,
            "cancel_reason": cancel_reason,
            **kwargs
        }
    )
```

- [ ] **Step 6: 转换引擎状态方法（line 1366-1474）**

```python
def log_engine_error_event(self, error_code: str, error_message: str, **kwargs):
    self.set_log_category("backtest")
    structlog.get_logger(self.logger_name).error(
        f"Engine error: [{error_code}] {error_message}",
        _ginkgo={
            "event_type": "ENGINEERROR",
            "error_code": error_code,
            "error_message": error_message,
            **kwargs
        }
    )

def log_engine_start_event(self, **kwargs):
    self.set_log_category("backtest")
    structlog.get_logger(self.logger_name).info(
        "Engine started",
        _ginkgo={
            "event_type": "ENGINESTART",
            **kwargs
        }
    )

def log_engine_pause_event(self, reason: str = "", **kwargs):
    self.set_log_category("backtest")
    structlog.get_logger(self.logger_name).warning(
        f"Engine paused: {reason if reason else 'No reason'}",
        _ginkgo={
            "event_type": "ENGINEPAUSE",
            "pause_reason": reason,
            **kwargs
        }
    )

def log_engine_resume_event(self, **kwargs):
    self.set_log_category("backtest")
    structlog.get_logger(self.logger_name).info(
        "Engine resumed",
        _ginkgo={
            "event_type": "ENGINERESUME",
            **kwargs
        }
    )

def log_engine_complete_event(self, **kwargs):
    self.set_log_category("backtest")
    structlog.get_logger(self.logger_name).info(
        "Engine completed",
        _ginkgo={
            "event_type": "ENGINECOMPLETE",
            **kwargs
        }
    )
```

- [ ] **Step 7: Commit**

```bash
git add src/ginkgo/libs/core/logger.py
git commit -m "refactor: convert 19 log_*_event methods to use structlog _ginkgo kwargs"
```

---

### Task 4: 更新引擎调用方

**Files:**
- Modify: `src/ginkgo/trading/engines/time_controlled_engine.py:207-210,484`
- Modify: `src/ginkgo/trading/engines/event_engine.py:201-207`
- Modify: `src/ginkgo/workers/backtest_worker/task_processor.py:63-98`

- [ ] **Step 1: time_controlled_engine.py — 绑定 time_provider 到 EngineContext**

在 `_initialize_components()` 中创建 `_time_provider` 之后（约 line 210），添加：

```python
self._time_provider = SystemTimeProvider()

# 绑定 time_provider 到 EngineContext（logger 动态读取 business_timestamp）
self._engine_context.set_time_provider(self._time_provider)
```

在回测模式分支中也添加（line 207 之后）：

```python
self._time_provider = LogicalTimeProvider(self._logical_time_start)

# 绑定 time_provider 到 EngineContext
self._engine_context.set_time_provider(self._time_provider)
```

- [ ] **Step 2: time_controlled_engine.py — 删除 bind_context(business_timestamp)**

删除 line 483-484：

```python
# 删除这两行：
# 1.5 同步business_timestamp到日志上下文
GLOG.bind_context(business_timestamp=target_time)
```

- [ ] **Step 3: event_engine.py — main_loop 绑定 EngineContext 引用**

将 line 201-207 从：

```python
# 在引擎线程中绑定业务上下文（contextvars 不跨线程传播）
portfolio_id = self.portfolios[0].portfolio_id if self.portfolios else ""
GLOG.bind_context(
    task_id=self.task_id or "",
    engine_id=self.engine_id,
    portfolio_id=portfolio_id,
)
```

改为：

```python
# 在引擎线程中绑定 EngineContext 引用（contextvars 不跨线程传播）
GLOG.bind_context(engine_context=self._engine_context)
```

- [ ] **Step 4: task_processor.py — 绑定 PortfolioContext 引用**

将 line 63-98 从：

```python
# DIAG: 排查线程启动时的上下文状态
import threading
from ginkgo.libs.core.logger import _business_context_ctx
initial_ctx = _business_context_ctx.get()
if initial_ctx:
    import sys
    print(f"[DIAG-INIT] thread={threading.current_thread().name} "
          f"task={self.task.task_uuid[:8]} "
          f"inherited_keys={sorted(initial_ctx.keys())} "
          f"task_id_in_ctx={initial_ctx.get('task_id','NONE')}",
          file=sys.stderr, flush=True)

# 清除继承的上下文，防止上一个任务的残留数据污染
GLOG.clear_context()
GLOG.set_log_category("component")

try:
    GLOG.INFO(f"[{self.task.task_uuid[:8]}] Starting backtest task: {self.task.name}")

    ...

    # 绑定业务上下文到日志（portfolio_id/task_id/engine_id 写入每条日志）
    GLOG.bind_context(
        task_id=self.task.task_uuid,
        portfolio_id=self.task.portfolio_uuid,
        engine_id=self.task.task_uuid,
    )
```

改为：

```python
GLOG.clear_context()
GLOG.set_log_category("component")

try:
    GLOG.INFO(f"[{self.task.task_uuid[:8]}] Starting backtest task: {self.task.name}")

    ...

    # 绑定 PortfolioContext 引用（task_id/engine_id/portfolio_id 动态读取）
    from ginkgo.trading.context.portfolio_context import PortfolioContext
    portfolio_context = PortfolioContext(
        portfolio_id=self.task.portfolio_uuid,
        engine_context=self._engine._engine_context
    )
    GLOG.bind_context(engine_context=portfolio_context)
```

- [ ] **Step 5: Commit**

```bash
git add src/ginkgo/trading/engines/time_controlled_engine.py src/ginkgo/trading/engines/event_engine.py src/ginkgo/workers/backtest_worker/task_processor.py
git commit -m "refactor: update engine callers to use EngineContext reference binding"
```

---

### Task 5: 移除诊断代码

**Files:**
- Modify: `src/ginkgo/libs/core/logger.py` (bind_context 中的 DIAG-BIND, ginkgo_processor 中的 DIAG-PROC)

- [ ] **Step 1: 确认 bind_context 诊断已移除**

在 Task 2 中已重写 `bind_context`，DIAG-BIND 代码已不存在。确认无残留。

- [ ] **Step 2: 确认 ginkgo_processor 诊断已移除**

在 Task 2 中已重写 `ginkgo_processor`，DIAG-PROC 代码已不存在。确认无残留。

- [ ] **Step 3: 确认 task_processor 诊断已移除**

在 Task 4 Step 4 中已删除 DIAG-INIT 代码。确认无残留。

- [ ] **Step 4: Commit（如有改动）**

```bash
git add -A
git commit -m "chore: remove diagnostic logging (DIAG-INIT/DIAG-BIND/DIAG-PROC)"
```

---

### Task 6: 集成验证

**Files:** 无代码改动

- [ ] **Step 1: 重新构建 Docker 镜像**

```bash
docker compose build ginkgo-backtest-worker
```

- [ ] **Step 2: 重启 worker**

```bash
docker compose up -d ginkgo-backtest-worker
```

- [ ] **Step 3: 通过 WebUI 运行一次回测**

使用默认组合运行回测，等待完成。

- [ ] **Step 4: 检查 ClickHouse 日志**

验证以下查询：

```sql
-- 1. business_timestamp 正确（非 1970-01-01）
SELECT task_id, business_timestamp, message
FROM ginkgo.ginkgo_logs_backtest
WHERE task_id = '<task_uuid>'
ORDER BY timestamp DESC LIMIT 10;

-- 2. 事件级字段只在对应事件日志中出现
SELECT event_type, symbol, order_id, message
FROM ginkgo.ginkgo_logs_backtest
WHERE task_id = '<task_uuid>' AND event_type != ''
ORDER BY timestamp DESC LIMIT 20;

-- 3. 任务级字段在所有日志中一致
SELECT task_id, engine_id, portfolio_id, count()
FROM ginkgo.ginkgo_logs_backtest
WHERE task_id = '<task_uuid>'
GROUP BY task_id, engine_id, portfolio_id;

-- 4. 无重复日志（同一 timestamp + message 只出现一次）
SELECT timestamp, message, count() as cnt
FROM ginkgo.ginkgo_logs_backtest
WHERE task_id = '<task_uuid>'
GROUP BY timestamp, message
HAVING cnt > 1;
```

预期结果：
- `business_timestamp` 显示正确的回测日期
- `event_type` 只在对应事件行有值（SIGNALGENERATION 行有 symbol，ORDERFILLED 行有 order_id）
- 所有日志的 `task_id/engine_id/portfolio_id` 一致
- 无重复日志

- [ ] **Step 5: 检查 WebUI 日志页面**

在 WebUI 中打开回测详情的日志页面，确认日志正常显示。
