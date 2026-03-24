# GLOG 结构化日志 API 使用指南

## API 分层结构

```
GLOG
├── backtest.*       # 回测业务日志
│   ├── trade.*      # 交易流程事件
│   ├── order.*      # 订单异常事件
│   └── system.*     # 系统事件（引擎状态、风控、错误）
├── execution.*      # 实盘执行日志
├── component.*      # 组件日志
└── performance.*    # 性能日志
```

## 1. 回测业务日志 (GLOG.backtest.*)

### 1.1 交易流程事件 (GLOG.backtest.trade.*)

```python
# 信号生成
GLOG.backtest.trade.signal(symbol="000001.SZ", direction="LONG")

# 订单提交
GLOG.backtest.trade.order(order_id=order.uuid)

# 订单成交
GLOG.backtest.trade.fill(order_id=order.uuid, price=10.52, volume=1000)

# 持仓更新
GLOG.backtest.trade.position(symbol="000001.SZ", volume=1000)

# 资金更新
GLOG.backtest.trade.capital(total=100000.0, cash=50000.0)
```

### 1.2 订单异常事件 (GLOG.backtest.order.*)

```python
# 订单拒绝
GLOG.backtest.order.reject(order_id=order.uuid, code="INSUFFICIENT", reason="资金不足")

# 订单取消
GLOG.backtest.order.cancel(order_id=order.uuid, reason="用户取消")

# 订单过期
GLOG.backtest.order.expire(order_id=order.uuid, reason="已过期")

# 订单确认（实盘）
GLOG.backtest.order.ack(order_id=order.uuid, broker_order_id="broker-123")
```

### 1.3 系统事件 (GLOG.backtest.system.*)

#### 引擎状态事件

```python
# 引擎启动
GLOG.backtest.system.start(
    engine_id=engine.uuid,
    run_id=run.uuid,
    portfolio_id=portfolio.uuid
)

# 引擎暂停
GLOG.backtest.system.pause(
    reason="用户暂停",
    engine_id=engine.uuid,
    progress=0.5
)

# 引擎恢复
GLOG.backtest.system.resume(
    engine_id=engine.uuid,
    run_id=run.uuid
)

# 引擎完成
GLOG.backtest.system.complete(
    engine_id=engine.uuid,
    run_id=run.uuid,
    duration_seconds=3600,
    final_capital=110000.0,
    total_return=0.1
)
```

#### 错误和风控事件

```python
# 风控事件
GLOG.backtest.system.risk(
    risk_type="POSITIONLIMIT",
    reason="持仓超限",
    risk_actual_value=0.25,
    risk_limit_value=0.20
)

# 引擎错误
GLOG.backtest.system.error(
    error_code="DATA_ERROR",
    error_message="数据加载失败"
)
```

### 1.4 快捷访问

```python
GLOG.backtest.signal(symbol, direction)      # 信号
GLOG.backtest.fill(order_id, price, volume)  # 成交
GLOG.backtest.risk(risk_type, reason)        # 风控
```

## 2. 实盘执行日志 (GLOG.execution.*)

```python
GLOG.execution.confirm(tracking_id, exp_price, act_price, exp_vol, act_vol)
GLOG.execution.reject(tracking_id, reason)
GLOG.execution.timeout(tracking_id)
GLOG.execution.cancel(tracking_id, reason)
```

## 3. 组件日志 (GLOG.component.*)

```python
GLOG.component.info(name="Strategy", message="初始化完成")
```

## 4. 性能日志 (GLOG.performance.*)

```python
GLOG.performance.metric(func="calculate_signals", duration_ms=125.5)
```

## 完整事件覆盖

| 类别 | 事件类型 | API路径 |
|------|---------|---------|
| **引擎状态** | ENGINESTART | `backtest.system.start()` |
| | ENGINEPAUSE | `backtest.system.pause()` |
| | ENGINERESUME | `backtest.system.resume()` |
| | ENGINECOMPLETE | `backtest.system.complete()` |
| **交易流程** | SIGNALGENERATION | `backtest.trade.signal()` |
| | ORDERSUBMITTED | `backtest.trade.order()` |
| | ORDERFILLED | `backtest.trade.fill()` |
| | POSITIONUPDATE | `backtest.trade.position()` |
| | CAPITALUPDATE | `backtest.trade.capital()` |
| **订单异常** | ORDERREJECTED | `backtest.order.reject()` |
| | ORDERCANCELACK | `backtest.order.cancel()` |
| | ORDEREXPIRED | `backtest.order.expire()` |
| | ORDERACK | `backtest.order.ack()` |
| **实盘执行** | EXECUTIONCONFIRMATION | `execution.confirm()` |
| | EXECUTIONREJECTION | `execution.reject()` |
| | EXECUTIONTIMEOUT | `execution.timeout()` |
| | EXECUTIONCANCELLATION | `execution.cancel()` |
| **风控错误** | RISKBREACH | `backtest.system.risk()` |
| | ENGINEERROR | `backtest.system.error()` |
