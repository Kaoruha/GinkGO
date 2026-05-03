# 结构化日志管道补全设计

## Context

回测日志有三个关键维度需要完整链路：
- **task_id**：追踪一次回测任务
- **portfolio_id**：在同一 task 下区分多个 portfolio
- **event_type**：按事件类型分类查询

当前状态：
1. t1backtest.py 的 45 处 `GLOG.log_*_event` 调用没有注入 `portfolio_id`（只有 `self.blog.*` 的 9 处注入了）
2. Vector 只提取了 24 个字段到 ClickHouse，30+ 字段（error_code、available_cash、limit_price 等）丢失
3. API endpoint 读到 `portfolio_id` 但没传给查询方法

## 方案

### 1. blog proxy 扩展（`context_mixin.py`）

在 `_LogChain.__call__` 中增加路由：路径首元素以 `log_` 开头时，路由到 `GLOG` 直接调用 `log_*_event` 方法；否则走原有 `GLOG.backtest.*` 命名空间。

```python
def __call__(self, *args, **kwargs):
    pid = object.__getattribute__(self, '_pid')
    if pid:
        kwargs.setdefault('portfolio_id', pid)
    from ginkgo.libs import GLOG
    path = object.__getattribute__(self, '_path')
    if path[0].startswith('log_'):
        obj = GLOG
    else:
        obj = GLOG.backtest
    for attr in path:
        obj = getattr(obj, attr)
    return obj(*args, **kwargs)
```

**可行性验证**：
- `_BacktestLogNamespace` 的属性名（trade/order/system/signal/fill/risk）不以 `log_` 开头，无歧义
- `log_*_event` 方法都接受 `**kwargs`，`portfolio_id` 自然流入 `_ginkgo`
- `ginkgo_processor` 中 `_ginkgo.update()` 在 ContextVar 读取之后执行，kwargs 值优先
- 新增的 5 个方法（log_t1_settlement_event 等）没有 namespace 包装，必须走此路由

### 2. t1backtest.py 转换（45 处）

`GLOG.log_*` → `self.blog.log_*`，纯查找替换。自动注入 portfolio_id。

### 3. Vector 字段补全（`.conf/vector.toml`）

在 `normalize_fields` transform 中补全 30+ 字段的提取映射。所有映射格式为 `if exists(.ginkgo.xxx) { .xxx = .ginkgo.xxx }`。

补全字段清单：
- **信号**：signal_weight, signal_confidence
- **订单**：order_type, limit_price, frozen_money, ack_message, order_status, remain_volume, trade_id
- **过期/取消**：expire_reason, cancelled_quantity, expired_quantity
- **持仓**：position_cost, position_price
- **资金**：total_value, available_cash, frozen_cash, net_value, drawdown, pnl
- **风控**：risk_limit_value, risk_actual_value
- **引擎**：engine_status, progress, error_code, error_message
- **执行确认**：tracking_id, expected_price, actual_price, expected_volume, actual_volume, price_deviation, volume_deviation, delay_seconds
- **追踪**：source（从 ginkgo.source_type 映射）

### 4. API 筛选修复（`api/api/backtest.py`）

在 `get_backtest_logs` 的 kwargs 中加入 `portfolio_id=portfolio_id`。

## 不改的

- ClickHouse 表结构（列已足够）
- Analyzer 日志
- Engine 级日志（不加 portfolio_id，只加 event_type）
- GLOG 内部的 log_*_event 方法签名

## 验证

1. 运行回测，检查 bt_*.log JSON 中 `ginkgo.portfolio_id` 在 `log_*_event` 产出的日志中非空
2. ClickHouse：`SELECT portfolio_id, event_type, count() FROM ginkgo_logs_backtest WHERE task_id='...' GROUP BY portfolio_id, event_type` — portfolio_id 应非空
3. ClickHouse：`SELECT error_code, count() FROM ginkgo_logs_backtest WHERE event_type='ENGINEERROR' GROUP BY error_code` — error_code 应有值（之前为 NULL）
4. API：`GET /{uuid}/logs?event_type=ENGINEERROR` 返回带 portfolio_id 和 error_code 的日志
5. WebUI：日志详情中 ENGINEERROR 事件显示 error_code 和 error_message
