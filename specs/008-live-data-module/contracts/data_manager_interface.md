# DataManager接口契约

**Component**: DataManager
**Module**: `src/ginkgo/livecore/data_manager.py`
**Version**: 1.0.0
**Date**: 2026-01-09

## 一、组件概述

### 1.1 职责定义

DataManager是实时数据管理器，作为LiveCore的控制平面组件运行，负责：

1. **订阅管理**: 订阅Kafka Topic `ginkgo.live.interest.updates`接收Portfolio订阅更新
2. **标的分发**: 按市场分发订阅标的到对应的LiveDataFeeder实例
3. **数据转发**: 通过Queue消费者线程将Tick数据发布到Kafka
4. **生命周期管理**: 管理LiveDataFeeder和Queue消费者的启动和停止

### 1.2 架构定位

```
Portfolio → Kafka(interest.updates) → DataManager → LiveDataFeeder → Queue → Kafka(market.data)
```

**六边形架构定位**: DataManager作为 **Driven Adapter**，负责外部数据源（WebSocket/HTTP）与系统内部（Kafka）的适配。

### 1.3 依赖关系

**Upstream**:
- `ginkgo.interfaces.kafka_topics` - Kafka Topic常量定义
- `ginkgo.livecore.data_feeders.base_feeder` - LiveDataFeeder基类
- `ginkgo.livecore.queue_consumers.tick_consumer` - Tick消费者

**Downstream**:
- `Kafka Topic: ginkgo.live.interest.updates` - 订阅更新Topic（Consumer）
- `Kafka Topic: ginkgo.live.market.data` - 实时行情Topic（Producer）
- `LiveDataFeeder实例` - 数据源适配器（EastMoneyFeeder、FuShuFeeder、AlpacaFeeder）

---

## 二、公共接口定义

### 2.1 类定义

```python
from threading import Thread, Lock, Event
from typing import Dict, Set, List
from queue import Queue

class DataManager(Thread):
    """
    实时数据管理器

    职责：
    1. 订阅Kafka Topic "ginkgo.live.interest.updates"接收订阅更新
    2. 维护all_symbols内存集合（所有订阅标的）
    3. 按市场分发订阅到LiveDataFeeder实例
    4. 启动Queue消费者线程处理Tick数据

    线程模型：
    - 主线程：Kafka Consumer循环
    - 子线程：每个LiveDataFeeder（WebSocket/HTTP连接）
    - 子线程：每个Queue消费者（Tick → DTO → Kafka）

    启动顺序：
    1. 启动Queue消费者线程
    2. 启动LiveDataFeeder实例
    3. 启动Kafka Consumer（主循环）

    停止顺序：
    1. 停止LiveDataFeeder
    2. 等待Queue消费完
    3. 停止Kafka Consumer
    """

    def __init__(self):
        """
        初始化DataManager

        初始化状态：
        - all_symbols: 空集合
        - feeders: 空字典（在start()时创建实例）
        - queue_consumers: 空列表（在start()时创建）
        - _stop_event: 未设置状态
        """
        super().__init__()

    # ========================================
    # 生命周期管理接口
    # ========================================

    def start(self) -> None:
        """
        启动DataManager

        执行步骤：
        1. 创建LiveDataFeeder实例（硬编码：cn/hk/us）
        2. 创建Queue消费者线程
        3. 启动所有Queue消费者
        4. 启动所有LiveDataFeeder
        5. 启动Kafka Consumer（调用run()方法）

        异常处理：
        - LiveDataFeeder启动失败：记录错误日志，继续启动其他Feeder
        - Queue消费者启动失败：记录错误日志，抛出DataManagerStartupException
        - Kafka Consumer启动失败：记录错误日志，抛出DataManagerStartupException

        线程安全：无需加锁（start()仅在主线程调用一次）
        """
        pass

    def stop(self) -> None:
        """
        停止DataManager

        执行步骤：
        1. 设置_stop_event标志（通知所有线程停止）
        2. 停止所有LiveDataFeeder（调用feeder.stop()）
        3. 等待Queue消费者消费完（调用consumer.join(timeout=10)）
        4. 关闭Kafka Consumer

        超时处理：
        - Queue消费者join超时：记录警告日志，强制关闭
        - LiveDataFeeder停止超时：记录警告日志，强制关闭

        线程安全：无需加锁（stop()仅在主线程调用一次）
        """
        pass

    def run(self) -> None:
        """
        主循环（Thread.run()实现）

        执行步骤：
        1. 启动Kafka Consumer订阅" ginkgo.live.interest.updates"
        2. 进入消费循环，逐条处理消息
        3. 检查_stop_event标志，如果设置则退出循环
        4. 清理资源（调用_cleanup()）

        异常处理：
        - Kafka消费异常：记录错误日志，退出循环
        - 消息解析异常：记录警告日志，跳过该消息

        线程安全：无需加锁（run()在独立线程执行）
        """
        pass

    # ========================================
    # 内部方法（私有接口）
    # ========================================

    def _handle_interest_update(self, message: dict) -> None:
        """
        处理订阅更新消息

        Args:
            message: Kafka消息（dict格式），包含：
                - portfolio_id: str - Portfolio ID
                - node_id: str - ExecutionNode ID
                - symbols: List[str] - 订阅标的列表
                - timestamp: datetime - 更新时间戳

        执行步骤：
        1. 提取symbols列表
        2. 加锁更新all_symbols
        3. 按市场分发订阅到LiveDataFeeder

        线程安全：加锁访问all_symbols（使用self._lock）

        异常处理：
        - 消息格式错误：记录警告日志，跳过该消息
        - LiveDataFeeder.set_symbols()失败：记录错误日志
        """
        pass

    def _filter_by_market(self, symbols: Set[str], market: str) -> Set[str]:
        """
        按市场过滤标的

        Args:
            symbols: 标的集合
            market: 市场标识（"cn", "hk", "us"）

        Returns:
            过滤后的标的集合

        过滤规则：
        - cn市场: 后缀为".SH"或".SZ"
        - hk市场: 后缀为".HK"
        - us市场: 无后缀

        线程安全：无需加锁（纯函数，无共享状态）
        """
        pass

    def _cleanup(self) -> None:
        """
        清理资源

        执行步骤：
        1. 停止所有LiveDataFeeder
        2. 等待Queue消费者消费完
        3. 关闭Kafka Consumer

        线程安全：无需加锁（仅在run()退出时调用）
        """
        pass
```

### 2.2 常量定义

```python
# 市场映射配置
MARKET_MAPPING = {
    "cn": [".SH", ".SZ"],  # A股市场
    "hk": [".HK"],          # 港股市场
    "us": []                # 美股市场（无后缀）
}

# Queue配置
QUEUE_MAXSIZE = 10000  # 有界队列最大长度

# Kafka配置
INTEREST_UPDATES_TOPIC = "ginkgo.live.interest.updates"  # 订阅更新Topic
MARKET_DATA_TOPIC = "ginkgo.live.market.data"            # 市场数据Topic

# Consumer配置
CONSUMER_GROUP_ID = "data_manager_group"  # Consumer Group ID
```

---

## 三、输入输出契约

### 3.1 Kafka输入契约

**Topic**: `ginkgo.live.interest.updates`

**消息格式**:
```json
{
  "portfolio_id": "portfolio_001",
  "node_id": "node_001",
  "symbols": ["000001.SZ", "600000.SH", "00700.HK"],
  "timestamp": "2026-01-09T09:30:00"
}
```

**字段说明**:
- `portfolio_id` (str, required): Portfolio唯一标识
- `node_id` (str, required): ExecutionNode唯一标识
- `symbols` (List[str], required): 订阅标的列表（如["000001.SZ", "600000.SH"]）
- `timestamp` (datetime, required): 更新时间戳（ISO 8601格式）

**消息频率**: 不定期（Portfolio订阅变更时发送）

**处理策略**:
- 消息格式错误：记录警告日志，跳过该消息
- 重复订阅：合并到all_symbols集合
- 取消订阅：暂不支持（MVP阶段）

### 3.2 Kafka输出契约

**Topic**: `ginkgo.live.market.data`

**消息格式** (PriceUpdateDTO):
```json
{
  "symbol": "000001.SZ",
  "price": 10.50,
  "volume": 10000,
  "amount": 105000.0,
  "bid_price": 10.49,
  "ask_price": 10.51,
  "bid_volume": 5000,
  "ask_volume": 8000,
  "open_price": 10.30,
  "high_price": 10.60,
  "low_price": 10.25,
  "timestamp": "2026-01-09T09:30:00.123456"
}
```

**字段说明**:
- `symbol` (str, required): 标的代码（如"000001.SZ"）
- `price` (float, required): 最新价格
- `volume` (int, required): 成交量
- `amount` (float, required): 成交额
- `bid_price` (float, optional): 买一价
- `ask_price` (float, optional): 卖一价
- `bid_volume` (int, optional): 买一量
- `ask_volume` (int, optional): 卖一量
- `open_price` (float, optional): 开盘价
- `high_price` (float, optional): 最高价
- `low_price` (float, optional): 最低价
- `timestamp` (datetime, required): Tick时间戳（ISO 8601格式）

**消息频率**: 实时（Tick数据到达时立即发布）

**发布策略**:
- 发布失败：重试3次（指数退避）
- 所有重试失败：记录错误日志，发送告警通知
- Queue满时：丢弃当前数据，记录警告日志

---

## 四、错误处理契约

### 4.1 异常定义

```python
class DataManagerException(Exception):
    """DataManager基础异常"""
    pass

class DataManagerStartupException(DataManagerException):
    """DataManager启动异常"""
    pass

class FeederException(DataManagerException):
    """LiveDataFeeder异常"""
    pass
```

### 4.2 异常处理策略

| 异常场景 | 处理策略 | 日志级别 | 告警 |
|---------|---------|---------|-----|
| Kafka Consumer启动失败 | 抛出DataManagerStartupException，停止DataManager | ERROR | 发送告警 |
| LiveDataFeeder启动失败 | 记录错误日志，继续启动其他Feeder | ERROR | 发送告警 |
| Queue消费者启动失败 | 抛出DataManagerStartupException，停止DataManager | ERROR | 发送告警 |
| Kafka消费异常 | 记录错误日志，退出消费循环 | ERROR | 发送告警 |
| 消息解析异常 | 记录警告日志，跳过该消息 | WARNING | 不告警 |
| LiveDataFeeder订阅更新失败 | 记录错误日志，跳过该Feeder | ERROR | 不告警 |
| Queue消费者异常 | 记录错误日志，重启消费者 | ERROR | 不告警 |
| Kafka发布失败 | 重试3次，失败后记录错误日志 | ERROR | 发送告警 |

### 4.3 恢复策略

**自动恢复**:
- LiveDataFeeder断线：自动重连（指数退避，最大5次）
- Kafka Consumer连接失败：自动重连（由kafka-python-ng处理）
- Queue消费者异常：自动重启

**手动恢复**:
- DataManager启动失败：检查配置文件和依赖服务，手动重启
- 所有重试失败：发送告警通知，运维人员介入

---

## 五、性能约束

### 5.1 延迟约束

- **实时数据处理延迟**: < 100ms（从LiveDataFeeder接收Tick到Kafka发布完成）
- **订阅更新延迟**: < 1s（从接收Kafka订阅消息到更新LiveDataFeeder订阅）

### 5.2 吞吐量约束

- **Kafka发布吞吐量**: > 10,000 messages/sec
- **支持并发订阅**: >= 10个LiveDataFeeder实例

### 5.3 资源约束

- **内存占用**: < 500MB（Queue + all_symbols + Feeder实例）
- **CPU占用**: < 20%（单核，正常负载）
- **网络带宽**: < 10Mbps（Tick数据流量）

---

## 六、测试契约

### 6.1 单元测试

**测试类**: `tests/unit/livecore/test_data_manager.py`

**测试用例**:
1. `test_data_manager_initialization` - 测试DataManager初始化
2. `test_handle_interest_update` - 测试订阅更新处理
3. `test_filter_by_market` - 测试市场过滤逻辑
4. `test_start_stop_sequence` - 测试启动停止顺序
5. `test_concurrent_symbol_update` - 测试并发订阅更新

### 6.2 集成测试

**测试类**: `tests/integration/livecore/test_data_manager_integration.py`

**测试用例**:
1. `test_kafka_consumer_integration` - 测试Kafka Consumer集成
2. `test_feeder_integration` - 测试LiveDataFeeder集成
3. `test_queue_consumer_integration` - 测试Queue消费者集成
4. `test_end_to_end_flow` - 测试端到端数据流

### 6.3 网络测试

**测试类**: `tests/network/livecore/test_data_manager_network.py`

**测试用例**:
1. `test_websocket_reconnect` - 测试WebSocket断线重连
2. `test_kafka_connection_failure` - 测试Kafka连接失败处理
3. `test_network_partition` - 测试网络分区场景

---

## 七、配置契约

### 7.1 环境变量

| 变量名 | 类型 | 必需 | 默认值 | 说明 |
|-------|------|------|-------|------|
| `KAFKA_BOOTSTRAP_SERVERS` | str | 是 | - | Kafka集群地址 |
| `KAFKA_CONSUMER_GROUP_ID` | str | 否 | "data_manager_group" | Consumer Group ID |
| `QUEUE_MAXSIZE` | int | 否 | 10000 | Queue最大长度 |
| `LOG_LEVEL` | str | 否 | "INFO" | 日志级别 |

### 7.2 配置文件

**路径**: `~/.ginkgo/data_sources.yml`

**格式**:
```yaml
data_sources:
  eastmoney:
    api_token: "${EASTMONEY_TOKEN}"  # 从环境变量读取
    websocket_uri: "wss://push2.eastmoney.com/ws/qt/stock/klt.min"

  fushu:
    api_token: "${FUSHU_TOKEN}"
    http_uri: "https://api.fushu.com/v1/tick"

  alpaca:
    api_key: "${ALPACA_API_KEY}"
    api_secret: "${ALPACA_API_SECRET}"
    websocket_uri: "wss://stream.data.alpaca.markets/v2/iex"
```

---

## 八、版本历史

| 版本 | 日期 | 变更说明 |
|------|------|---------|
| 1.0.0 | 2026-01-09 | 初始版本 |
