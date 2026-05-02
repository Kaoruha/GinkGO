# 日志上下文分层重构设计

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将日志 context 从单一的 dict 值绑定改为引用绑定 + 事件字段直接传入，消除上下文累积污染。

**Architecture:** 三层数据通道——任务级字段通过 EngineContext 引用动态读取，事件级字段通过 structlog `_ginkgo` kwargs 单条传入，追踪级字段保持独立 ContextVar。

**Tech Stack:** Python 3.12, structlog, contextvars

---

## 问题

当前 `bind_context(**kwargs)` 将所有字段以值存入 `_business_context_ctx` dict，通过 `dict.update()` 原地修改：

1. **字段累积**：`log_signal_event` 绑定 `event_type/symbol/direction` 后，后续所有日志都携带这些字段，直到被覆盖
2. **值拷贝**：`business_timestamp` 每次推进需要 `bind_context(business_timestamp=target_time)` 重复写入
3. **职责混淆**：`bind_context` 同时承载任务级（task_id）和事件级（order_id）字段，没有边界

## 设计

### 三层数据通道

| 层级 | 传递方式 | 字段 | 生命周期 |
|------|---------|------|---------|
| 任务级 | EngineContext 引用 | task_id, portfolio_id, engine_id, source_type, business_timestamp | 整个任务 |
| 事件级 | structlog `_ginkgo` kwargs | event_type, symbol, order_id, signal_volume, ... | 单条日志 |
| 追踪级 | 独立 ContextVar（不变） | trace_id, span_id | 按需嵌套 |

### 1. EngineContext 扩展

**文件：** `src/ginkgo/trading/context/engine_context.py`

添加 `time_provider` 引用和 `business_timestamp` 动态属性：

在现有 `EngineContext` 基础上添加（不使用 `__slots__`，保持现有风格）：

```python
# __init__ 中新增
self._time_provider = None

# 新增属性和方法
@property
def time_provider(self):
    return self._time_provider

def set_time_provider(self, provider) -> None:
    self._time_provider = provider

@property
def business_timestamp(self):
    if self._time_provider:
        return self._time_provider.now()
    return None
```

引擎装配时绑定引用：
```python
self._engine_context.set_time_provider(self._time_provider)
```

之后引擎推进时间时只需 `self._time_provider.set_current_time(target_time)`，无需额外通知 logger。`ginkgo_processor` 动态读取 `engine_ctx.business_timestamp` 始终获取最新值。

### 2. bind_context 改为引用绑定

**文件：** `src/ginkgo/libs/core/logger.py`

`_business_context_ctx` 从存散列值改为存 EngineContext/PortfolioContext 引用：

```python
def bind_context(self, engine_context=None) -> None:
    """绑定引擎上下文引用（仅接受 EngineContext/PortfolioContext）"""
    if engine_context is not None:
        _business_context_ctx.set(engine_context)

def clear_context(self) -> None:
    """清除上下文引用"""
    _business_context_ctx.set(None)
    _log_category_ctx.set(None)
```

白名单通过类型检查强制：只接受 `EngineContext`/`PortfolioContext` 实例，拒绝 dict 或其他类型。

### 3. ginkgo_processor 读取逻辑

```python
def ginkgo_processor(logger, log_method, event_dict):
    event_dict.setdefault("ginkgo", {})

    # 1. 从 EngineContext 引用动态读取任务级字段
    engine_ctx = _business_context_ctx.get()
    if engine_ctx:
        event_dict["ginkgo"]["task_id"] = engine_ctx.task_id
        event_dict["ginkgo"]["engine_id"] = engine_ctx.engine_id
        event_dict["ginkgo"]["source_type"] = engine_ctx.source_type
        if engine_ctx.business_timestamp:
            event_dict["ginkgo"]["business_timestamp"] = engine_ctx.business_timestamp
        if isinstance(engine_ctx, PortfolioContext):
            event_dict["ginkgo"]["portfolio_id"] = engine_ctx.portfolio_id

    # 2. 从 _ginkgo 读取事件级字段（单条日志传入）
    event_fields = event_dict.pop("_ginkgo", {})
    event_dict["ginkgo"].update(event_fields)

    # 3. log_category（不变）
    category = _log_category_ctx.get()
    if category:
        event_dict["ginkgo"]["log_category"] = category

    # 4. trace_id / span_id（不变，独立 ContextVar）
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

### 4. log_*_event 便利方法改为 structlog kwargs

所有 15 个 `log_*_event` 方法从 `bind_context + INFO` 改为直接调用 structlog：

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
```

同理适用于：
- `log_order_event` → event_type=ORDERSUBMITTED
- `log_order_fill_event` → event_type=ORDERFILLED
- `log_position_event` → event_type=POSITIONUPDATE
- `log_capital_event` → event_type=CAPITALUPDATE
- `log_risk_event` → event_type=RISKBREACH
- `log_order_rejected_event` → event_type=ORDERREJECTED
- `log_order_cancelled_event` → event_type=ORDERCANCELACK
- `log_order_ack_event` → event_type=ORDERACK
- `log_order_expired_event` → event_type=ORDEREXPIRED
- `log_engine_start` → event_type=ENGINESTART
- `log_engine_pause` → event_type=ENGINEPAUSE
- `log_engine_complete` → event_type=ENGINECOMPLETE

### 5. 调用方变更

**task_processor.py** (line 94-98):
```python
# 改前
GLOG.bind_context(
    task_id=self.task.task_uuid,
    portfolio_id=self.task.portfolio_uuid,
    engine_id=self.task.task_uuid,
)

# 改后：绑定 PortfolioContext 引用
portfolio_context = PortfolioContext(
    portfolio_id=self.task.portfolio_uuid,
    engine_context=self._engine._engine_context
)
GLOG.bind_context(engine_context=portfolio_context)
```

**time_controlled_engine.py** (line 484):
```python
# 改前
GLOG.bind_context(business_timestamp=target_time)

# 改后：删除此行，time_provider 已绑定到 EngineContext，动态读取
```

**event_engine.py** (line 203-207):
```python
# 改前
GLOG.bind_context(task_id=..., engine_id=..., portfolio_id=...)

# 改后：绑定 EngineContext 引用
GLOG.bind_context(engine_context=self._engine_context)
```

### 6. 不动的部分

- `INFO/ERROR/WARN/DEBUG/CRITICAL` 方法签名不变（只接受字符串）
- `trace_id`/`span_id` 独立 ContextVar 机制不变
- `set_log_category` 机制不变
- Vector/ClickHouse 配置和表结构不变
- `_BacktestLogNamespace`/`_BacktestTradeNamespace` 等命名空间的调用接口不变（内部委托到 `log_*_event`）
- Diagnostic 代码（DIAG-INIT/DIAG-BIND/DIAG-PROC）在本次重构中一并移除

## 改动文件清单

| 文件 | 改动范围 |
|------|---------|
| `src/ginkgo/trading/context/engine_context.py` | 添加 `_time_provider`、`business_timestamp` 属性 |
| `src/ginkgo/libs/core/logger.py` | 重写 `bind_context`、`clear_context`、`ginkgo_processor`、15 个 `log_*_event` 方法，移除诊断代码 |
| `src/ginkgo/trading/engines/time_controlled_engine.py` | 装配时绑定 time_provider，删除 line 484 bind_context |
| `src/ginkgo/workers/backtest_worker/task_processor.py` | 绑定 PortfolioContext 引用，移除诊断代码 |
| `src/ginkgo/trading/engines/event_engine.py` | 绑定 EngineContext 引用 |

## 验证

1. 运行回测任务，检查 ClickHouse 日志无重复字段
2. business_timestamp 正确显示（非 1970-01-01）
3. 事件级字段（event_type, symbol, order_id）只在对应事件日志中出现
4. 任务级字段（task_id, portfolio_id, engine_id）在所有日志中一致
5. WebUI 日志页面正常显示
