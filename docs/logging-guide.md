# GLOG 日志使用指南

## 两种日志类型

Ginkgo有两种日志记录方式，各有不同的用途和使用场景。

### 1. 操作日志 (self.log / GLOG.INFO)

**用途**：开发调试、问题排查、实时监控

**输出位置**：
- 控制台（Rich格式化）
- 日志文件（JSON格式，供Vector采集后发送到其他系统）

**使用场景**：
```python
# 调试信息 - 了解程序执行流程
self.log("DEBUG", f"Processing {len(signals)} signals")

# 正常信息 - 记录关键操作节点
self.log("INFO", "Portfolio initialized with 100000 capital")

# 警告信息 - 潜在问题
self.log("WARN", "Data cache miss, fetching from database")

# 错误信息 - 程序异常
self.log("ERROR", f"Failed to load data: {e}")

# 临时打印
print(f"[DEBUG] Current price: {price}")
```

**何时使用**：
- ✅ 需要实时查看运行状态
- ✅ 调试程序执行流程
- ✅ 记录异常堆栈信息
- ✅ 临时性的调试输出

**何时不使用**：
- ❌ 记录持久化的业务数据（用GLOG.backtest.*）
- ❌ 结构化事件查询（用GLOG.backtest.*）

---

### 2. 业务事件日志 (GLOG.backtest.*)

**用途**：业务分析、审计追踪、历史数据查询

**输出位置**：
- 日志文件（JSON格式）
- Vector采集 → ClickHouse（持久化存储）

**使用场景**：
```python
# 交易流程事件 - 记录核心业务链路
GLOG.backtest.trade.signal(symbol="000001.SZ", direction="LONG")
GLOG.backtest.trade.fill(order_id=order.uuid, price=10.52, volume=1000)
GLOG.backtest.trade.position(symbol="000001.SZ", volume=1000)
GLOG.backtest.trade.capital(total=100000, cash=50000)

# 订单异常事件 - 记录异常处理
GLOG.backtest.order.reject(order_id=order.uuid, code="INSUFFICIENT", reason="资金不足")
GLOG.backtest.order.cancel(order_id=order.uuid, reason="用户取消")
GLOG.backtest.order.expire(order_id=order.uuid, reason="已过期")

# 系统事件 - 记录引擎状态
GLOG.backtest.system.start(engine_id=self.uuid)
GLOG.backtest.system.complete(engine_id=self.uuid)

# 风控事件 - 记录风控触发
GLOG.backtest.system.risk(risk_type="POSITIONLIMIT", reason="持仓超限")
```

**何时使用**：
- ✅ 记录业务关键事件（信号、订单、成交等）
- ✅ 需要持久化存储的历史数据
- ✅ 需要查询分析的业务数据
- ✅ 审计追踪需求

**何时不使用**：
- ❌ 临时调试信息（用self.log）
- ❌ 详细的技术实现细节（用self.log）

---

## 使用对照表

| 场景 | 使用方法 | 示例 |
|------|----------|------|
| 程序启动/初始化 | `self.log("INFO")` | `self.log("INFO", "Engine started")` |
| 引擎启动事件 | `GLOG.backtest.system.start()` | `GLOG.backtest.system.start(engine_id=...)` |
| 调试变量值 | `print()` 或 `self.log("DEBUG")` | `print(f"Price: {price}")` |
| 信号生成 | `GLOG.backtest.trade.signal()` | `GLOG.backtest.trade.signal(symbol, direction)` |
| 订单处理进度 | `self.log("INFO")` | `self.log("INFO", "Processing order...")` |
| 订单提交事件 | `GLOG.backtest.trade.order()` | `GLOG.backtest.trade.order(order_id=...)` |
| 数据加载失败 | `self.log("ERROR")` | `self.log("ERROR", f"Load failed: {e}")` |
| 订单拒绝事件 | `GLOG.backtest.order.reject()` | `GLOG.backtest.order.reject(...)` |
| 性能监控 | `self.log("INFO")` | `self.log("INFO", f"Processed in {elapsed}s")` |
| 风控触发 | `GLOG.backtest.system.risk()` | `GLOG.backtest.system.risk(...)` |

---

## 最佳实践

### 1. 双重记录模式

对于关键业务事件，建议同时记录两种日志：

```python
def on_order_filled(self, event):
    # 操作日志 - 实时监控
    self.log("INFO", f"Order {event.order_id[:8]} filled: {event.transaction_volume}@{event.transaction_price}")

    # 业务事件 - 持久化存储
    GLOG.backtest.trade.fill(
        order_id=event.order_id,
        price=event.transaction_price,
        volume=event.transaction_volume
    )
```

### 2. 异常处理

```python
try:
    # 业务逻辑
    result = process_data()
except Exception as e:
    # 错误日志 - 详细信息
    self.log("ERROR", f"Process failed: {e}")
    import traceback
    self.log("ERROR", f"Traceback: {traceback.format_exc()}")

    # 如果是业务异常，也记录到ClickHouse
    GLOG.backtest.system.error(
        error_code=type(e).__name__,
        error_message=str(e)
    )
    raise
```

### 3. 调试代码规范

临时调试代码使用print，正式代码使用self.log：

```python
# ❌ 临时调试代码（不要提交）
print(f"DEBUG: value={value}")

# ✅ 正式调试代码
self.log("DEBUG", f"Processing value: {value}")

# ✅ 业务事件
GLOG.backtest.trade.position(symbol, volume)
```

---

## 日志级别选择

| 级别 | 使用场景 | 示例 |
|------|----------|------|
| DEBUG | 详细的调试信息 | 变量值、循环计数、中间状态 |
| INFO | 正常业务流程 | 方法开始/结束、处理结果 |
| WARN | 潜在问题 | 缓存未命中、使用默认值 |
| ERROR | 错误但可恢复 | 数据加载失败、重试操作 |

---

## 迁移指南

如果你的代码中混合使用了两种日志，按以下原则整理：

1. **保留self.log()** 用于：
   - 方法入口/出口日志
   - 调试信息
   - 异常处理
   - 性能监控

2. **添加GLOG.backtest.*()** 用于：
   - 业务事件（信号、订单、成交、持仓、资金）
   - 系统事件（启动、暂停、完成、错误）
   - 风控事件
   - 需要查询分析的数据

3. **删除print()** 或改为self.log("DEBUG")
