# GLOG 结构化日志集成记录

本文档记录了trading模块中所有已添加的GLOG结构化日志调用位置。

## 1. 引擎层

### event_engine.py
- `start()` - 引擎启动时调用 `GLOG.backtest.system.start()`
- `pause()` - 引擎暂停时调用 `GLOG.backtest.system.pause()`
- `stop()` - 引擎停止时调用 `GLOG.backtest.system.complete()`

## 2. 策略层

### moving_average_crossover.py
- `_detect_crossover()` - 信号生成时调用 `GLOG.backtest.signal()`

## 3. 组合层

### t1backtest.py

#### 订单事件处理
- `on_order_rejected()` - 订单拒绝时调用 `GLOG.backtest.order.reject()`
- `on_order_cancel_ack()` - 订单取消时调用 `GLOG.backtest.order.cancel()`
- `on_order_expired()` - 订单过期时调用 `GLOG.backtest.order.expire()`
- `on_order_partially_filled()` - 订单成交时调用 `GLOG.backtest.fill()`

#### 持仓和资金事件
- `add_position()` - 持仓更新时调用 `GLOG.backtest.trade.position()`
- `deal_long_filled()` - LONG成交完成后调用 `GLOG.backtest.trade.capital()`
- `deal_short_filled()` - SHORT成交完成后调用 `GLOG.backtest.trade.capital()`

## 4. 网关层

### trade_gateway.py
- `on_order_ack()` - 订单确认时调用 `GLOG.backtest.order.ack()`

## 5. 风控层

### position_ratio_risk.py
- `cal()` - 仓位限制触发时调用 `GLOG.backtest.risk()`

### loss_limit_risk.py
- `generate_signals()` - 止损触发时调用 `GLOG.backtest.risk()`

### profit_target_risk.py
- `generate_signals()` - 止盈触发时调用 `GLOG.backtest.risk()`

## API调用模式

### 交易流程事件
```python
GLOG.backtest.trade.signal(symbol, direction, **kwargs)
GLOG.backtest.trade.order(order_id, **kwargs)
GLOG.backtest.trade.fill(order_id, price, volume, **kwargs)
GLOG.backtest.trade.position(symbol, volume, **kwargs)
GLOG.backtest.trade.capital(total, cash, **kwargs)
```

### 订单异常事件
```python
GLOG.backtest.order.reject(order_id, code, reason, **kwargs)
GLOG.backtest.order.cancel(order_id, reason, **kwargs)
GLOG.backtest.order.expire(order_id, reason, **kwargs)
GLOG.backtest.order.ack(order_id, broker_order_id, **kwargs)
```

### 系统事件
```python
GLOG.backtest.system.start(**kwargs)
GLOG.backtest.system.pause(reason, **kwargs)
GLOG.backtest.system.complete(**kwargs)
GLOG.backtest.system.risk(risk_type, reason, **kwargs)
GLOG.backtest.system.error(code, message, **kwargs)
```

## 待补充位置

以下位置可以考虑添加GLOG调用：

1. **策略初始化** - BaseStrategy.initialize()
2. **策略完成** - BaseStrategy.finalize()
3. **时间推进** - advance_time()
4. **K线收盘** - EventBarClose处理
5. **数据加载** - 数据加载成功/失败
6. **更多风控类型** - 其他风控模块

## 注意事项

1. **try-except包裹** - 所有GLOG调用都应包含在try-except中，避免日志异常影响业务流程
2. **参数传递** - 使用**kwargs传递额外字段，便于扩展
3. **ID关联** - 确保传递engine_id, portfolio_id, run_id等关联字段
4. **类型转换** - 枚举类型使用.value转换为字符串
