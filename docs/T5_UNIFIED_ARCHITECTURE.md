# T5 统一事件驱动架构文档

## 概述

T5统一事件驱动架构是Ginkgo量化交易系统的核心重构项目，旨在建立统一的时间控制、事件处理和执行抽象，实现回测和实盘交易的架构统一。

## 架构原则

### 核心设计理念
- **单一时间权威**: 统一的时间语义，支持逻辑时间(回测)和系统时间(实盘)
- **事件驱动**: 完整的 `PriceUpdate → Strategy → Signal → Portfolio → Order → Fill` 事件链路
- **接口抽象**: Broker接口抽象支持模拟、纸质交易和实盘交易
- **智能路由**: 企业级事件路由系统，支持负载均衡和容错机制

## 核心组件

### 1. 时间控制系统 (`ginkgo.trading.time`)

#### ITimeProvider接口
```python
from ginkgo.trading.time import SystemTimeProvider, LogicalTimeProvider

# 系统时间 - 实盘交易
system_provider = SystemTimeProvider()
current_time = system_provider.now()

# 逻辑时间 - 回测
initial_time = datetime(2023, 1, 1, 9, 30, 0)
logical_provider = LogicalTimeProvider(initial_time)
logical_provider.advance_time_to(datetime(2023, 1, 1, 15, 30, 0))
```

#### 关键特性
- **时间统一性**: 统一时间接口，支持时间推进和设置
- **时区感知**: 内置时区处理，避免时间混乱
- **防倒退保护**: 逻辑时间不允许倒退，保证时间序列一致性

### 2. 执行结果系统 (`ginkgo.trading.execution.results`)

#### ExecutionResult标准化
```python
from ginkgo.trading.execution.results import ExecutionResult, ExecutionStatus, ErrorCode

# 成功结果
success_result = ExecutionResult(
    success=True,
    status=ExecutionStatus.COMPLETED,
    data={"order_id": "12345", "filled_qty": 1000}
)

# 失败结果
error_result = ExecutionResult(
    success=False,
    status=ExecutionStatus.FAILED,
    error_code=ErrorCode.VALIDATION_ERROR,
    error_message="Invalid order parameters"
)
```

#### 统一错误处理
- **标准化状态**: 7种执行状态(PENDING, RUNNING, COMPLETED等)
- **错误码分类**: 按域分类的错误码(VALIDATION, EXECUTION, NETWORK等)
- **结构化数据**: 统一的成功/失败数据结构

### 3. Broker接口系统 (`ginkgo.trading.brokers`)

#### IBroker抽象接口
```python
from ginkgo.trading.brokers.interfaces import IBroker, TradingOrder, OrderSide, OrderType
from ginkgo.trading.brokers.base_broker import BaseBroker

class MyBroker(BaseBroker):
    async def connect(self) -> bool:
        # 实现连接逻辑
        pass
    
    async def submit_order(self, order: TradingOrder) -> TradingOrder:
        # 实现订单提交逻辑
        pass
```

#### 核心数据结构
- **TradingOrder**: 标准化订单结构
- **Position**: 持仓信息管理
- **Trade**: 成交记录
- **AccountBalance**: 账户余额信息
- **BrokerStats**: 代理统计数据

### 4. 事件路由系统 (`ginkgo.trading.execution.routing`)

#### EventRoutingCenter核心
```python
from ginkgo.trading.execution.routing import (
    EventRoutingCenter, RouteTarget, RoutingRule, RoutingStrategy
)

# 创建路由中心
center = EventRoutingCenter("trading_center")
await center.initialize()

# 注册路由目标
target = RouteTarget(
    target_id="strategy_processor",
    target_type="strategy",
    target_instance=my_strategy,
    weight=10,
    circuit_breaker_enabled=True
)
await center.register_target(target)

# 添加路由规则
rule = RoutingRule(
    rule_id="price_update_rule",
    name="Price Update Routing",
    event_type_pattern="price_update",
    targets=["strategy_processor"],
    strategy=RoutingStrategy.WEIGHTED
)
await center.add_routing_rule(rule)

# 路由事件
targets = await center.route_event(price_update_event)
```

#### 负载均衡策略

1. **RoundRobinBalancer**: 轮询分配
2. **WeightedBalancer**: 权重分配
3. **LeastConnectionsBalancer**: 最少连接数
4. **HashBasedBalancer**: 一致性哈希
5. **PriorityBasedBalancer**: 优先级路由
6. **BroadcastBalancer**: 广播所有目标
7. **FailoverBalancer**: 故障转移
8. **ConditionalBalancer**: 条件路由

#### 断路器保护
```python
from ginkgo.trading.execution.routing.circuit_breaker import CircuitBreaker, CircuitBreakerConfig

# 配置断路器
config = CircuitBreakerConfig(
    failure_threshold=5,          # 失败阈值
    failure_rate_threshold=0.5,   # 失败率阈值
    recovery_timeout=60,          # 恢复超时
    half_open_max_calls=3        # 半开状态最大调用数
)

circuit_breaker = CircuitBreaker("target_id", config)
```

## 事件类型扩展

### 新增事件类型(24种)
```python
from ginkgo.enums import EVENT_TYPES

# 订单生命周期事件
EVENT_TYPES.ORDER_ACK                    # 订单确认
EVENT_TYPES.ORDER_PARTIALLY_FILLED       # 订单部分成交
EVENT_TYPES.ORDER_COMPLETELY_FILLED      # 订单完全成交
EVENT_TYPES.ORDER_CANCELLED              # 订单取消
EVENT_TYPES.ORDER_REJECTED               # 订单拒绝

# 风控事件
EVENT_TYPES.RISK_LIMIT_EXCEEDED          # 风险限制超出
EVENT_TYPES.POSITION_LIMIT_WARNING       # 持仓限制警告
EVENT_TYPES.STOP_LOSS_TRIGGERED          # 止损触发

# 系统事件
EVENT_TYPES.ENGINE_STARTED               # 引擎启动
EVENT_TYPES.ENGINE_STOPPED               # 引擎停止
EVENT_TYPES.ENGINE_ERROR                 # 引擎错误
EVENT_TYPES.CONNECTION_LOST              # 连接丢失
EVENT_TYPES.CONNECTION_RESTORED          # 连接恢复

# 策略事件
EVENT_TYPES.STRATEGY_SIGNAL              # 策略信号
EVENT_TYPES.STRATEGY_ERROR               # 策略错误
EVENT_TYPES.STRATEGY_STATE_CHANGED       # 策略状态变化

# 数据事件
EVENT_TYPES.MARKET_DATA_UPDATE           # 市场数据更新
EVENT_TYPES.REFERENCE_DATA_UPDATE        # 参考数据更新
EVENT_TYPES.DATA_QUALITY_WARNING         # 数据质量警告

# 系统监控事件
EVENT_TYPES.HEALTH_CHECK_PASSED          # 健康检查通过
EVENT_TYPES.HEALTH_CHECK_FAILED          # 健康检查失败
EVENT_TYPES.PERFORMANCE_WARNING          # 性能警告
EVENT_TYPES.RESOURCE_EXHAUSTED           # 资源耗尽

# 审计事件
EVENT_TYPES.AUDIT_LOG                    # 审计日志
EVENT_TYPES.COMPLIANCE_VIOLATION         # 合规违规
```

## 集成工作流示例

### 完整交易工作流
```python
import asyncio
from datetime import datetime, timedelta
from ginkgo.trading.time import LogicalTimeProvider
from ginkgo.trading.brokers.base_broker import BaseBroker
from ginkgo.trading.execution.routing import EventRoutingCenter

async def integrated_trading_workflow():
    # 1. 设置逻辑时间控制
    time_provider = LogicalTimeProvider(datetime(2023, 6, 1, 9, 30, 0))
    
    # 2. 初始化Broker
    broker = MyBroker()
    await broker.connect()
    
    # 3. 设置事件路由
    routing_center = EventRoutingCenter("main")
    await routing_center.initialize()
    
    # 注册策略处理器
    await routing_center.register_target(RouteTarget(
        target_id="strategy_engine",
        target_type="strategy",
        target_instance=strategy_processor
    ))
    
    # 4. 模拟交易流程
    # 价格更新 -> 策略信号 -> 订单提交 -> 订单成交
    
    # 价格更新事件
    price_event = PriceUpdateEvent(symbol="000001.SZ", price=10.50)
    await routing_center.route_event(price_event)
    
    # 推进时间
    time_provider.advance_time_by(timedelta(seconds=1))
    
    # 策略信号事件
    signal_event = StrategySignalEvent(symbol="000001.SZ", action="BUY")
    await routing_center.route_event(signal_event)
    
    # 订单提交
    order = TradingOrder(
        symbol="000001.SZ",
        side=OrderSide.BUY,
        order_type=OrderType.LIMIT,
        quantity=Decimal('1000'),
        price=Decimal('10.50')
    )
    
    result = await broker.submit_order(order)
    
    # 清理资源
    await broker.disconnect()
    await routing_center.shutdown()
```

## 性能特性

### 并发处理
- **异步架构**: 全面使用asyncio异步处理
- **并发限制**: 可配置的并发路由限制
- **线程池**: 计算密集型任务使用线程池

### 缓存机制
- **路由缓存**: TTL缓存机制，减少重复路由计算
- **指标缓存**: 性能指标缓存，提高查询效率
- **健康检查缓存**: 减少健康检查频率

### 监控指标
```python
# 获取路由指标
metrics = await routing_center.get_routing_metrics()
print(f"总事件数: {metrics.total_events}")
print(f"成功路由: {metrics.successful_routes}")
print(f"失败路由: {metrics.failed_routes}")
print(f"平均路由时间: {metrics.avg_routing_time}")
print(f"吞吐量: {metrics.throughput_per_second}")

# 获取断路器统计
circuit_stats = circuit_breaker.get_statistics()
print(f"断路器状态: {circuit_stats['state']}")
print(f"失败率: {circuit_stats['failure_rate']}")
```

## 测试策略

### 单元测试覆盖
- **时间提供者测试**: 时间设置、推进、时区处理
- **Broker接口测试**: 订单生命周期、账户管理
- **路由系统测试**: 负载均衡、断路器、健康监控
- **执行结果测试**: 状态转换、错误处理

### 集成测试
- **端到端工作流**: 完整交易流程测试
- **容错测试**: 故障注入和恢复机制
- **性能测试**: 高并发场景下的系统表现

## 迁移指南

### 向后兼容性
T5架构保持与现有代码的向后兼容:

1. **现有Event系统**: 继续工作，新事件类型为可选
2. **时间获取**: 现有`datetime.now()`调用无需修改
3. **Broker实现**: 现有Broker可渐进式迁移到新接口

### 迁移步骤
1. **第一阶段**: 引入时间提供者，替换关键时间调用
2. **第二阶段**: 实现新Broker接口，保持旧接口并存
3. **第三阶段**: 引入事件路由，优化高频事件处理
4. **第四阶段**: 完整切换到T5架构

## 最佳实践

### 时间控制
```python
# ✅ 推荐: 使用时间提供者
time_provider = get_time_provider()  # 从配置获取
current_time = time_provider.now()

# ❌ 避免: 直接使用系统时间
current_time = datetime.now()  # 在回测中会有问题
```

### 错误处理
```python
# ✅ 推荐: 使用ExecutionResult
result = await some_operation()
if result.success:
    process_data(result.data)
else:
    handle_error(result.error_code, result.error_message)

# ❌ 避免: 抛出原始异常
try:
    data = await some_operation()
    process_data(data)
except Exception as e:
    # 异常信息不结构化
    print(f"Error: {e}")
```

### 事件路由
```python
# ✅ 推荐: 使用模式匹配
rule = RoutingRule(
    rule_id="order_events",
    event_type_pattern="order_*",  # 匹配所有订单事件
    targets=["order_processor"],
    strategy=RoutingStrategy.ROUND_ROBIN
)

# ✅ 推荐: 启用断路器保护
target = RouteTarget(
    target_id="critical_processor",
    target_instance=processor,
    circuit_breaker_enabled=True  # 启用保护
)
```

## 故障排除

### 常见问题

1. **时间不一致**
   - 问题: 回测和实盘时间处理不同
   - 解决: 统一使用ITimeProvider接口

2. **事件丢失**
   - 问题: 高频事件在路由中丢失
   - 解决: 检查并发限制和目标健康状态

3. **断路器误触发**
   - 问题: 正常波动触发断路器
   - 解决: 调整失败阈值和检测窗口

4. **内存泄漏**
   - 问题: 长时间运行后内存增长
   - 解决: 检查事件历史和缓存配置

### 调试工具
```python
# 启用详细日志
GLOG.set_debug(True)

# 获取路由中心状态
health = await routing_center.health_check()
print(f"路由中心状态: {health}")

# 监控断路器
stats = circuit_breaker_manager.get_all_statistics()
for target_id, stat in stats.items():
    print(f"{target_id}: {stat['state']} (失败率: {stat['failure_rate']:.2%})")
```

## 总结

T5统一事件驱动架构为Ginkgo量化交易系统提供了:

- **时间统一性**: 回测和实盘的时间语义统一
- **接口抽象**: 清晰的Broker抽象层
- **智能路由**: 企业级事件分发机制  
- **容错保护**: 断路器和健康监控
- **性能优化**: 异步处理和智能缓存

这个架构为构建可靠、高性能的量化交易系统奠定了坚实基础。