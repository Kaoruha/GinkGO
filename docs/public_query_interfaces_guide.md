# 公共查询接口使用指南

## 概述

为了解决测试中的断言合理性问题，Ginkgo引擎现在提供了分层的公共查询接口，替代对私有属性的依赖。

## 接口架构

### 分层设计

```
BaseEngine (基础层)
├── get_engine_status() -> EngineStatus
├── get_event_stats() -> EventStats
└── get_queue_info() -> QueueInfo

EventEngine (事件层)
├── get_registered_handlers_count() -> int
├── get_handler_distribution() -> Dict[str, int]
├── get_event_processing_stats() -> Dict[str, Any]
└── 重写父类查询方法以提供更详细信息

TimeControlledEventEngine (时间同步层)
├── get_time_info() -> TimeInfo
├── get_component_sync_info(component_id) -> ComponentSyncInfo
├── get_all_components_sync_info() -> Dict[str, ComponentSyncInfo]
├── get_time_provider_info() -> Dict[str, Any]
├── is_component_synced(component_id) -> bool
└── get_sync_summary() -> Dict[str, Any]
```

## 使用示例

### 1. 引擎状态查询

```python
from ginkgo.trading.engines.time_controlled_engine import TimeControlledEventEngine

# 创建引擎
engine = TimeControlledEventEngine(
    name="TestEngine",
    mode=EXECUTION_MODE.BACKTEST
)

# 获取引擎基础状态
status = engine.get_engine_status()
print(f"引擎运行状态: {status.is_running}")
print(f"当前时间: {status.current_time}")
print(f"执行模式: {status.execution_mode}")
print(f"已处理事件数: {status.processed_events}")
print(f"队列大小: {status.queue_size}")
```

### 2. 事件处理统计

```python
# 获取事件统计信息
event_stats = engine.get_event_stats()
print(f"已处理事件数: {event_stats.processed_events}")
print(f"已注册处理器数: {event_stats.registered_handlers}")
print(f"队列大小: {event_stats.queue_size}")
print(f"处理速率: {event_stats.processing_rate:.2f} 事件/秒")

# 获取详细的事件处理统计
detailed_stats = engine.get_event_processing_stats()
print(f"总事件数: {detailed_stats['total_events']}")
print(f"成功事件数: {detailed_stats['completed_events']}")
print(f"失败事件数: {detailed_stats['failed_events']}")
print(f"成功率: {detailed_stats['success_rate']:.2%}")

# 获取处理器分布
distribution = engine.get_handler_distribution()
print(f"专用处理器: {distribution['type_specific']}")
print(f"通用处理器: {distribution['general']}")
print(f"定时器处理器: {distribution['timer']}")
```

### 3. 队列状态监控

```python
# 获取队列信息
queue_info = engine.get_queue_info()
print(f"当前队列大小: {queue_info.queue_size}")
print(f"最大队列容量: {queue_info.max_size}")
print(f"队列是否已满: {queue_info.is_full}")
print(f"队列是否为空: {queue_info.is_empty}")
```

### 4. 时间相关信息查询

```python
# 获取时间信息
time_info = engine.get_time_info()
print(f"当前时间: {time_info.current_time}")
print(f"时间模式: {time_info.time_mode}")
print(f"时间提供者类型: {time_info.time_provider_type}")
print(f"是否为逻辑时间: {time_info.is_logical_time}")
print(f"逻辑开始时间: {time_info.logical_start_time}")
print(f"时间推进次数: {time_info.time_advancement_count}")

# 获取时间提供者详细信息
provider_info = engine.get_time_provider_info()
print(f"提供者类型: {provider_info['provider_type']}")
print(f"是否支持时间控制: {provider_info['supports_time_control']}")
print(f"是否支持监听器: {provider_info['supports_listeners']}")
```

### 5. 组件同步状态查询

```python
# 检查特定组件同步状态
component_id = "portfolio_001"
is_synced = engine.is_component_synced(component_id)
print(f"组件 {component_id} 同步状态: {is_synced}")

# 获取详细组件同步信息
sync_info = engine.get_component_sync_info(component_id)
if sync_info:
    print(f"组件ID: {sync_info.component_id}")
    print(f"组件类型: {sync_info.component_type}")
    print(f"是否已同步: {sync_info.is_synced}")
    print(f"最后同步时间: {sync_info.last_sync_time}")
    print(f"同步次数: {sync_info.sync_count}")
    print(f"同步错误次数: {sync_info.sync_error_count}")
    print(f"是否已注册: {sync_info.is_registered}")

# 获取所有组件同步状态
all_sync_info = engine.get_all_components_sync_info()
for comp_id, info in all_sync_info.items():
    print(f"组件 {comp_id} ({info.component_type}): {'已同步' if info.is_synced else '未同步'}")

# 获取同步状态摘要
summary = engine.get_sync_summary()
print(f"总组件数: {summary['total_components']}")
print(f"已同步组件数: {summary['synced_components']}")
print(f"同步率: {summary['sync_rate']:.2%}")
print(f"组件类型分布: {summary['components_by_type']}")
```

## 在测试中的应用

### 替代私有属性断言

**之前（不合理）:**
```python
# 直接访问私有属性 - 不推荐
assert engine._is_running == True
assert engine._event_queue.qsize() == 0
assert engine._time_provider.now() == expected_time
```

**现在（推荐）:**
```python
# 使用公共查询接口 - 推荐
status = engine.get_engine_status()
assert status.is_running == True

queue_info = engine.get_queue_info()
assert queue_info.queue_size == 0

time_info = engine.get_time_info()
assert time_info.current_time == expected_time
```

### 业务闭环测试示例

```python
def test_complete_trading_workflow():
    """完整的交易业务流程测试"""
    engine = TimeControlledEventEngine(mode=EXECUTION_MODE.BACKTEST)

    # 启动引擎
    engine.start()

    # 模拟价格更新事件
    price_event = EventPriceUpdate(...)
    engine.put(price_event)

    # 等待事件处理完成
    time.sleep(0.1)

    # 验证事件处理结果
    event_stats = engine.get_event_stats()
    assert event_stats.processed_events > 0
    assert event_stats.processing_rate > 0

    # 验证组件同步状态
    sync_summary = engine.get_sync_summary()
    assert sync_summary.sync_rate > 0.8  # 至少80%组件已同步

    # 验证时间推进
    time_info = engine.get_time_info()
    assert time_info.time_advancement_count > 0

    # 停止引擎
    engine.stop()

    # 验证最终状态
    final_status = engine.get_engine_status()
    assert final_status.is_running == False
```

## 数据类结构

### EngineStatus
```python
@dataclass
class EngineStatus:
    is_running: bool                    # 引擎是否在运行
    current_time: Optional[datetime]    # 当前时间
    execution_mode: Optional[EXECUTION_MODE] = None  # 执行模式
    processed_events: int = 0           # 已处理事件数
    queue_size: int = 0                  # 事件队列大小
```

### EventStats
```python
@dataclass
class EventStats:
    processed_events: int               # 已处理事件数
    registered_handlers: int           # 已注册处理器数
    queue_size: int                     # 事件队列大小
    processing_rate: float = 0.0        # 处理速率（事件/秒）
```

### QueueInfo
```python
@dataclass
class QueueInfo:
    queue_size: int                      # 队列大小
    max_size: int                        # 队列最大容量
    is_full: bool = False                # 队列是否已满
    is_empty: bool = True               # 队列是否为空
```

### TimeInfo
```python
@dataclass
class TimeInfo:
    current_time: Optional[datetime]       # 当前时间（逻辑或实时）
    time_mode: TIME_MODE                  # 时间模式
    time_provider_type: str               # 时间提供者类型
    is_logical_time: bool                 # 是否为逻辑时间
    logical_start_time: Optional[datetime] = None  # 逻辑时间开始时间
    time_advancement_count: int = 0       # 时间推进次数
```

### ComponentSyncInfo
```python
@dataclass
class ComponentSyncInfo:
    component_id: str                    # 组件ID
    component_type: str                  # 组件类型
    is_synced: bool                      # 是否已同步
    last_sync_time: Optional[datetime]   # 最后同步时间
    sync_count: int = 0                  # 同步次数
    sync_error_count: int = 0            # 同步错误次数
    is_registered: bool = True           # 是否已注册
```

## 最佳实践

1. **优先使用公共接口**: 避免直接访问私有属性，使用提供的查询接口
2. **分层查询**: 根据需要的信息类型选择合适的查询层级
3. **结构化断言**: 使用数据类的字段进行精确断言
4. **业务导向**: 关注业务结果而非内部实现细节
5. **性能考虑**: 查询接口设计为轻量级，可以频繁调用

这些接口确保了测试的稳定性和可维护性，同时提供了丰富的引擎状态监控能力。