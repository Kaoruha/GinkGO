# Phase 2: Foundational (核心基础设施)

**状态**: ⚪ 未开始
**开始日期**: 待定
**预计完成**: 待定
**依赖**: Phase 1完成
**任务总数**: 8

---

## 📋 验收标准

- [ ] Kafka Producer/Consumer可以正常发送和接收消息
- [ ] 实盘交易事件类（EventControlCommand）已创建
- [ ] 数据模型（MPortfolio扩展, MPosition复用）已就绪
- [ ] Portfolio基类已扩展支持实盘交易

---

## 🎯 活跃任务 (最多5个)

> 根据Constitution任务管理原则，从下面的任务池中选择最多5个任务作为当前活跃任务

**当前活跃任务**: (暂无，请从待办任务池中选择)

---

## 📥 待办任务池 (8个)

### T009 [P] 验证EventPriceUpdate和EventOrderPartiallyFilled可复用
- **文件**: `src/ginkgo/trading/events/`
- **依赖**: 无
- **并行**: 是
- **描述**: 验证现有EventPriceUpdate和EventOrderPartiallyFilled可复用于实盘交易，无需创建新事件
- **详细步骤**:
  1. 读取 `src/ginkgo/trading/events/price_update.py`，验证EventPriceUpdate包含必要字段：
     - `code`: 股票代码
     - `timestamp`: 时间戳
     - `price`: 价格
     - `volume`: 成交量
  2. 读取 `src/ginkgo/trading/events/order_lifecycle_events.py`，验证EventOrderPartiallyFilled包含必要字段：
     - `order_id`: 订单ID
     - `filled_volume`: 成交数量
     - `filled_price`: 成交价格
     - `timestamp`: 时间戳
  3. 确认事件类已实现必要的序列化/反序列化方法（用于Kafka传输）
- **验收**: EventPriceUpdate和EventOrderPartiallyFilled包含实盘交易所需的所有字段

---

### T010 [P] 创建EventControlCommand事件类
- **文件**: `src/ginkgo/trading/events/event_control_command.py`
- **依赖**: 无
- **并行**: 是
- **描述**: 创建EventControlCommand事件类，用于Kafka控制命令传输
- **详细步骤**:
  1. 创建文件 `src/ginkgo/trading/events/event_control_command.py`
  2. 实现EventControlCommand类：
     ```python
     from dataclasses import dataclass
     from typing import Optional, Dict, Any
     from datetime import datetime

     @dataclass
     class EventControlCommand:
         """控制命令事件，用于Kafka传输"""
         command_type: str  # portfolio.create/delete/reload/start/stop, engine.start/stop
         target_id: str    # 目标组件ID（portfolio_id或engine_id）
         params: Optional[Dict[str, Any]] = None  # 命令参数
         timestamp: datetime = None

         def __post_init__(self):
             if self.timestamp is None:
                 self.timestamp = datetime.now()

         def to_dict(self) -> Dict[str, Any]:
             """序列化为字典（用于Kafka JSON序列化）"""
             return {
                 "command_type": self.command_type,
                 "target_id": self.target_id,
                 "params": self.params or {},
                 "timestamp": self.timestamp.isoformat()
             }

         @classmethod
         def from_dict(cls, data: Dict[str, Any]) -> "EventControlCommand":
             """从字典反序列化"""
             return cls(
                 command_type=data["command_type"],
                 target_id=data["target_id"],
                 params=data.get("params"),
                 timestamp=datetime.fromisoformat(data["timestamp"])
             )
     ```
  3. 添加必要的单元测试
- **验收**: EventControlCommand类创建成功，支持序列化/反序列化

---

### T011 [P] 验证MPortfolio和MPortfolioFileMapping可支持实盘交易
- **文件**: `src/ginkgo/data/models/model_portfolio.py`
- **依赖**: 无
- **并行**: 是
- **描述**: 验证现有MPortfolio和MPortfolioFileMapping模型已包含实盘交易所需字段
- **详细步骤**:
  1. 读取 `src/ginkgo/data/models/model_portfolio.py`
  2. 验证MPortfolio包含以下字段：
     - `is_live`: bool字段，区分回测和实盘
     - `name`: Portfolio名称
     - `strategy_id`: 策略ID
     - `sizer_id`: Sizer ID
     - `initial_cash`: 初始资金
  3. 验证MPortfolioFileMapping支持配置文件关联：
     - `portfolio_id`: Portfolio ID
     - `file_type`: 配置文件类型（strategy/sizer/risk）
     - `file_path`: 配置文件路径
  4. 确认模型支持CRUD操作
- **验收**: MPortfolio和MPortfolioFileMapping包含实盘交易所需的所有字段

---

### T012 [P] 验证PortfolioCRUD可支持实盘交易
- **文件**: `src/ginkgo/data/crud/portfolio_crud.py`
- **依赖**: 无
- **并行**: 是
- **描述**: 验证现有PortfolioCRUD已支持实盘交易操作
- **详细步骤**:
  1. 读取 `src/ginkgo/data/crud/portfolio_crud.py`
  2. 验证CRUD类继承BaseCRUD
  3. 验证支持`is_live`字段的增删改查：
     - `add_portfolio()`: 支持is_live参数
     - `get_portfolio_by_id()`: 支持is_live过滤
     - `update_portfolio()`: 支持is_live字段更新
     - `delete_portfolio()`: 支持is_live过滤
  4. 确认使用正确的数据库连接（MySQL）
- **验收**: PortfolioCRUD支持实盘交易的所有CRUD操作

---

### T013 [P] 验证MPosition模型可复用于实盘交易
- **文件**: `src/ginkgo/data/models/model_position.py`
- **依赖**: 无
- **并行**: 是
- **描述**: 验证现有MPosition模型已包含实盘交易所需字段
- **详细步骤**:
  1. 读取 `src/ginkgo/data/models/model_position.py`
  2. 验证MPosition包含以下字段：
     - `portfolio_id`: Portfolio ID
     - `code`: 股票代码
     - `volume`: 持仓数量
     - `available_volume`: 可用数量
     - `cost_price`: 成本价
     - `current_price`: 当前价
     - `timestamp`: 时间戳
  3. 确认模型支持ClickHouse存储（继承MClickBase）
- **验收**: MPosition包含实盘交易所需的所有字段

---

### T014 验证GinkgoProducer可支持实盘交易
- **文件**: `src/ginkgo/data/drivers/ginkgo_kafka.py`
- **依赖**: 无
- **并行**: 否
- **描述**: 验证现有GinkgoProducer，需改造acks=1为acks=all确保可靠性
- **详细步骤**:
  1. 读取 `src/ginkgo/data/drivers/ginkgo_kafka.py`
  2. 验证GinkgoProducer类实现
  3. **确认改造需求**：当前acks=1，需改为acks="all"
  4. 验证Producer支持幂等性（enable.idempotence=True）
  5. 验证支持重试机制
  6. **注意**: 此任务为验证任务，实际改造在T030执行
- **验收**: GinkgoProducer已实现，确认需要改造acks配置

---

### T015 验证GinkgoConsumer可支持实盘交易
- **文件**: `src/ginkgo/data/drivers/ginkgo_kafka.py`
- **依赖**: 无
- **并行**: 否
- **描述**: 验证现有GinkgoConsumer已支持实盘交易
- **详细步骤**:
  1. 读取 `src/ginkgo/data/drivers/ginkgo_kafka.py`
  2. 验证GinkgoConsumer类实现
  3. 验证支持手动提交offset（enable.auto.commit=false）
  4. 验证支持从指定topic消费
  5. 验证支持消息反序列化
- **验收**: GinkgoConsumer已实现，支持实盘交易所需的所有功能

---

### T016 编写Kafka集成测试
- **文件**: `tests/network/live/test_kafka_integration.py`
- **依赖**: T014, T015
- **并行**: 否
- **描述**: 编写Kafka集成测试，验证Producer和Consumer可以正确发送接收消息
- **详细步骤**:
  1. 创建测试文件 `tests/network/live/test_kafka_integration.py`
  2. 实现端到端测试：
     ```python
     import pytest
     import json
     from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer, GinkgoConsumer

     @pytest.mark.network
     def test_kafka_producer_consumer_e2e():
         """测试Kafka Producer和Consumer端到端通信"""
         topic = "ginkgo.live.market.data"
         test_message = {
             "code": "000001.SZ",
             "timestamp": "2026-01-04T10:00:00",
             "price": 10.5,
             "volume": 1000
         }

         # Producer发送消息
         producer = GinkgoProducer(bootstrap_servers="localhost:9092")
         producer.produce(topic, json.dumps(test_message))
         producer.flush()

         # Consumer接收消息
         consumer = GinkgoConsumer(
             topic=topic,
             bootstrap_servers="localhost:9092",
             group_id="test_group"
         )
         messages = consumer.consume(timeout_ms=5000, max_messages=1)

         assert len(messages) == 1
         received_message = json.loads(messages[0])
         assert received_message["code"] == "000001.SZ"
         assert received_message["price"] == 10.5

         consumer.close()
         producer.close()
     ```
  3. 添加更多测试用例（多消息、错误处理等）
- **验收**: 测试通过，Kafka Producer和Consumer正常工作

---

## ✅ 已完成任务 (0个)

*(暂无)*

---

## 📊 进度跟踪

| 指标 | 数值 |
|------|------|
| 总任务数 | 8 |
| 已完成 | 0 |
| 进行中 | 0 |
| 待办 | 8 |
| 完成进度 | 0% |

---

## 🔗 依赖关系

```
Phase 1: Setup
    ↓
Phase 2: Foundational (本阶段)
    ↓
Phase 3: User Story 1 - 单Portfolio实盘运行
```

---

## 📝 备注

- 本阶段主要验证现有组件是否可复用于实盘交易
- T009-T013可以并行执行（都是验证任务）
- T016依赖T014和T015，需最后执行
- 本阶段完成后，即可开始Phase 3的MVP开发

---

**文档版本**: 1.0.0
**最后更新**: 2026-01-04
