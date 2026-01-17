# DataManager多数据源架构设计

**Feature**: 008-live-data-module
**Date**: 2026-01-11
**Purpose**: 设计DataManager同时管理历史和实时数据源的架构

---

## 一、架构理解纠正

### 1.1 正确的架构理解

```
┌─────────────────────────────────────────────────────────────┐
│                      LiveCore (数据层)                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           DataManager (实时数据管理器)                │   │
│  │                                                      │   │
│  │  ┌──────────────────────────────────────────────┐   │   │
│  │  │  实时数据源管理                                │   │   │
│  │  │  ┌──────────────┐                             │   │   │
│  │  │  │LiveDataFeeder │                             │   │   │
│  │  │  │  (实时数据)   │                             │   │   │
│  │  │  │WebSocket     │                             │   │   │
│  │  │  └──────────────┘                             │   │   │
│  │  │         ↓                                      │   │   │
│  │  │    实时Tick数据                                 │   │   │
│  │  │         ↓                                      │   │   │
│  │  │    转换为PriceUpdateDTO                         │   │   │
│  │  │         ↓                                      │   │   │
│  │  │    Kafka Producer                              │   │   │
│  │  └──────────────────────────────────────────────┘   │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────┐         ┌──────────────────────┐         │
│  │  TaskTimer   │         │    BarService         │         │
│  │  (定时任务)   │         │  (历史K线数据)         │         │
│  └──────────────┘         └──────────────────────┘         │
└─────────────────────────────────────────────────────────────┘
                              ↓
                        Kafka Topics
                    (ginkgo.live.market.data)
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    ExecutionNode (执行层)                   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         Portfolio (无需管理数据源)                    │   │
│  │                                                      │   │
│  │  ┌────────────┐  ┌────────────┐  ┌──────────────┐   │   │
│  │  │  Selector  │  │  Strategy  │  │RiskManager   │   │   │
│  │  └────────────┘  └────────────┘  └──────────────┘   │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 核心设计原则

**职责分离**:
- **LiveCore.DataManager**: 管理所有数据源，对外统一提供数据
- **ExecutionNode.Portfolio**: 专注交易逻辑，不关心数据来源

**数据流**:
```
数据源 (多个)
    ↓
DataManager (统一管理、转换、发布)
    ↓
Kafka (事件总线)
    ↓
ExecutionNode (消费数据)
```

---

## 二、DataManager多数据源设计

### 2.1 数据源类型

| 数据源类型 | 用途 | 实现类 | 数据格式 |
|-----------|------|--------|---------|
| **实时Tick数据** | 实时交易信号 | LiveDataFeeder | Tick (price/volume) |
| **历史K线数据** | 策略初始化、盘后分析 | BarService | Bar (OHLCV) |

**说明**:
- DataManager只管理实时数据源（LiveDataFeeder）
- 历史数据通过BarService直接获取（ServiceHub模式）
- 策略和TaskTimer直接调用BarService获取历史K线

### 2.2 DataManager类设计

```python
from typing import Dict, Set, Optional
from threading import Thread, Lock
from datetime import datetime

from ginkgo.trading.feeders.interfaces import ILiveDataFeeder, DataFeedStatus
from ginkgo.trading.feeders.live_feeder import LiveDataFeeder
from ginkgo.interfaces.dtos import PriceUpdateDTO, InterestUpdateDTO

class DataManager(Thread):
    """
    实时数据管理器

    职责：
    1. 管理实时数据源（LiveDataFeeder）
    2. 接收实时Tick数据并转换为DTO
    3. 发布实时数据到Kafka
    4. 管理订阅标的（从Kafka接收InterestUpdate）

    数据源：
    - LiveDataFeeder: 实时Tick数据（WebSocket）

    输出：
    - Kafka Topic: ginkgo.live.market.data (PriceUpdateDTO)

    输入：
    - Kafka Topic: ginkgo.live.interest.updates (InterestUpdateDTO)
    """

    def __init__(self, config: dict = None):
        super().__init__()

        # LiveDataFeeder管理
        self.live_feeder: Optional[ILiveDataFeeder] = None
        self._feeder_status: DataFeedStatus = DataFeedStatus.IDLE
        self._lock = Lock()

        # Kafka发布器
        self.kafka_producer = GinkgoProducer()

        # 订阅管理
        self.all_symbols: Set[str] = set()

        # 初始化LiveDataFeeder
        self._initialize_live_feeder(config)

    def _initialize_live_feeder(self, config: dict) -> None:
        """
        初始化LiveDataFeeder

        Args:
            config: 配置字典
                {
                    "live": {
                        "enabled": true,
                        "config": {...}
                    }
                }
        """
        if config.get("live", {}).get("enabled", True):
            live_config = config.get("live", {}).get("config", {})
            self.live_feeder = LiveDataFeeder(
                host=live_config.get("host", ""),
                port=live_config.get("port", 0),
                api_key=live_config.get("api_key", "")
            )
            self._feeder_status = DataFeedStatus.IDLE
            self.log("INFO", "LiveDataFeeder initialized")

    # ========================================
    # LiveDataFeeder管理
    # ========================================

    def start_live_feeder(self) -> bool:
        """启动LiveDataFeeder"""
        with self._lock:
            if self.live_feeder is None:
                self.log("ERROR", "LiveDataFeeder not initialized")
                return False

            try:
                if not self.live_feeder.initialize():
                    self.log("ERROR", "Failed to initialize LiveDataFeeder")
                    return False

                if not self.live_feeder.start():
                    self.log("ERROR", "Failed to start LiveDataFeeder")
                    return False

                self._feeder_status = self.live_feeder.get_status()
                self.log("INFO", "LiveDataFeeder started successfully")
                return True

            except Exception as e:
                self.log("ERROR", f"Failed to start LiveDataFeeder: {e}")
                return False

    def stop_live_feeder(self) -> bool:
        """停止LiveDataFeeder"""
        with self._lock:
            if self.live_feeder is None:
                return False

            success = self.live_feeder.stop()
            self._feeder_status = DataFeedStatus.DISCONNECTED
            return success

    def get_feeder_status(self) -> DataFeedStatus:
        """获取LiveDataFeeder状态"""
        return self._feeder_status

    # ========================================
    # 实时数据订阅
    # ========================================

    def subscribe_live_data(self, symbols: List[str]) -> None:
        """
        订阅实时Tick数据

        Args:
            symbols: 股票代码列表
        """
        if self.live_feeder is None:
            self.log("ERROR", "LiveDataFeeder not available")
            return

        # 设置事件发布器（接收实时数据后发布到Kafka）
        self.live_feeder.set_event_publisher(self._on_live_data_received)

        # 订阅股票
        self.live_feeder.subscribe_symbols(symbols, data_types=["price_update"])

        # 开始订阅
        self.live_feeder.start_subscription()

        self.log("INFO", f"Subscribed to live data for {len(symbols)} symbols")

    def _on_live_data_received(self, event) -> None:
        """
        实时数据接收回调

        Args:
            event: 数据事件 (EventPriceUpdate)
        """
        try:
            # 转换为DTO
            if isinstance(event, EventPriceUpdate):
                dto = PriceUpdateDTO.from_event(event)
            else:
                self.log("WARN", f"Unknown event type: {type(event)}")
                return

            # 发布到Kafka
            self.kafka_producer.send(
                topic=KafkaTopics.MARKET_DATA,
                message=dto.model_dump_json()
            )

            self.log("DEBUG", f"Published PriceUpdateDTO to Kafka")

        except Exception as e:
            self.log("ERROR", f"Failed to process live data: {e}")

    # ========================================
    # 订阅管理（从Kafka接收订阅更新）
    # ========================================

    def update_subscriptions(self, symbols: Set[str]) -> None:
        """
        更新订阅标的

        从Kafka Topic: ginkgo.live.interest.updates 接收订阅更新

        Args:
            symbols: 新的订阅标的集合
        """
        with self._lock:
            # 更新全局订阅集合
            self.all_symbols = symbols

            # 更新LiveDataFeeder订阅
            if self.live_feeder is not None:
                self.live_feeder.subscribe_symbols(list(symbols))

            self.log("INFO", f"Updated subscriptions: {len(symbols)} symbols")

    # ========================================
    # 主循环
    # ========================================

    def run(self) -> None:
        """
        主循环

        订阅Kafka Topic: ginkgo.live.interest.updates
        接收订阅更新消息
        """
        # 创建Kafka Consumer
        consumer = GinkgoConsumer(
            topic=KafkaTopics.INTEREST_UPDATES,
            group_id="data_manager_group"
        )

        # 消费订阅更新
        for message in consumer:
            try:
                # 解析InterestUpdateDTO
                dto = InterestUpdateDTO.model_validate_json(message.value)

                # 更新订阅
                self.update_subscriptions(set(dto.symbols))

            except Exception as e:
                self.log("ERROR", f"Failed to process interest update: {e}")

    def start(self) -> None:
        """启动DataManager"""
        # 启动LiveDataFeeder
        self.start_live_feeder()

        # 启动Kafka订阅
        super().start()

        self.log("INFO", "DataManager started (real-time data only)")

    def stop(self) -> None:
        """停止DataManager"""
        # 停止LiveDataFeeder
        self.stop_live_feeder()

        # 停止主线程
        self.join(timeout=10)

        self.log("INFO", "DataManager stopped")
```

### 2.3 配置示例

**文件**: `~/.ginkgo/data_manager.yml`

```yaml
# DataManager配置（只管理实时数据源）
data_sources:
  # 实时数据源配置
  live:
    enabled: true
    description: "实时Tick数据（WebSocket）"
    config:
      host: "api.example.com"
      port: 8080
      api_key: "${LIVE_DATA_API_KEY}"
      enable_rate_limit: true
      rate_limit_per_second: 10.0

# Kafka配置
kafka:
  bootstrap_servers: "localhost:9092"
  topics:
    market_data: "ginkgo.live.market.data"
    interest_updates: "ginkgo.live.interest.updates"
  consumer_group_id: "data_manager_group"
  producer_config:
    max_retries: 3
    acks: "all"
```

---

## 三、使用场景

### 3.1 场景1: 实时数据接收

```python
# LiveDataFeeder接收实时Tick
LiveDataFeeder
    ↓ (WebSocket)
Tick数据
    ↓ (事件回调)
DataManager._on_live_data_received()
    ↓ (转换为DTO)
PriceUpdateDTO
    ↓ (发布到Kafka)
Topic: ginkgo.live.market.data
    ↓
ExecutionNode消费
```

### 3.2 场景2: 盘后K线分析

```python
# TaskTimer定时任务（每天21:00）
class TaskTimer:
    def _bar_snapshot_job(self):
        """K线快照任务"""
        # 发送控制命令到Kafka
        command = ControlCommandDTO(
            command="bar_snapshot",
            payload={"timestamp": datetime.now().isoformat()},
            timestamp=datetime.now()
        )

        self.kafka_producer.send(
            topic=KafkaTopics.CONTROL_COMMANDS,
            message=command.model_dump_json()
        )

# ExecutionNode接收控制命令
class PortfolioProcessor:
    def _handle_control_command(self, command: ControlCommandDTO):
        if command.command == "bar_snapshot":
            self.portfolio.on_bar_snapshot()

# Portfolio自己获取当日K线
class Portfolio:
    def on_bar_snapshot(self):
        # 使用BarService获取当日K线
        from ginkgo import services
        bar_crud = services.data.cruds.bar()

        start_time = datetime.now().replace(hour=0, minute=0, second=0)
        end_time = datetime.now()

        for symbol in self._interested_symbols:
            bars = bar_crud.get_bars_page_filtered(
                code=symbol,
                start=start_time.strftime("%Y%m%d"),
                end=end_time.strftime("%Y%m%d")
            )

            # 策略计算
            self.strategy.cal(bars)
```

**说明**:
- TaskTimer只发送控制命令，不获取数据
- Portfolio自己调用BarService获取当日K线
- 保持与Selector更新机制的一致性

---

## 四、数据流完整示例

### 4.1 启动流程

```
1. LiveCore启动
   ↓
2. DataManager初始化
   ├── 创建BacktestFeeder (历史数据源)
   ├── 创建LiveDataFeeder (实时数据源)
   └── 订阅Kafka: ginkgo.live.interest.updates
   ↓
3. 启动数据源
   ├── BacktestFeeder.start() (连接ClickHouse)
   └── LiveDataFeeder.start() (连接WebSocket)
   ↓
4. TaskTimer发送 "update_selector" 命令
   ↓
5. ExecutionNode执行 Selector.pick()
   ↓
6. EventInterestUpdate → Kafka
   ↓
7. DataManager接收订阅更新
   ├── 更新all_symbols
   └── 调用LiveDataFeeder.subscribe_symbols()
```

### 4.2 运行时数据流

```
[实时数据流]
外部数据源 (WebSocket)
    ↓ Tick
LiveDataFeeder.receive_message()
    ↓ EventPriceUpdate
DataManager._on_live_data_received()
    ↓ PriceUpdateDTO
Kafka (ginkgo.live.market.data)
    ↓
ExecutionNode消费
    ↓
Portfolio.on_price_update()

[历史数据流] (按需调用)
TaskTimer定时任务 (21:00)
    ↓ 调用
DataManager.get_historical_bars()
    ↓ 路由到
BacktestFeeder.get_historical_data()
    ↓ 查询
ClickHouse
    ↓ Bar数据
DataManager._convert_to_bar_dto()
    ↓ BarDTO
Kafka (ginkgo.live.market.data)
    ↓
ExecutionNode消费
    ↓
Portfolio.on_bar_update()
```

---

## 五、关键设计决策

### 5.1 为什么DataManager管理多个数据源？

| 方案 | 优点 | 缺点 |
|------|------|------|
| **DataManager管理多数据源** (✅ 推荐) | • 符合单一职责原则<br>• 数据层统一管理<br>• ExecutionNode无需关心数据来源 | • DataManager较复杂 |
| Portfolio管理多数据源 | • 灵活性高 | • 违反职责分离<br>• Portfolio应该专注交易逻辑<br>• 难以统一管理 |

### 5.2 数据源路由策略

**固定路由**（简单直接）:
- `get_historical_bars()` → 总是路由到 BacktestFeeder（历史K线数据）
- `get_live_tick()` → 总是路由到 LiveDataFeeder（实时Tick数据，推送模式）

**说明**: 实盘模式下不需要跨时间边界的数据合并，因为：
- 历史数据查询总是截止到"今天"，不会查询未来
- 实时数据通过推送模式获取，不需要主动查询

---

## 六、实施清单

- [ ] 创建DataManager多数据源版本
- [ ] 集成现有BacktestFeeder
- [ ] 集成现有LiveDataFeeder
- [ ] 实现数据源状态管理
- [ ] 实现固定路由逻辑（get_historical_bars → BacktestFeeder，get_live_tick → LiveDataFeeder）
- [ ] 实现数据转换（Bar → BarDTO, Tick → PriceUpdateDTO）
- [ ] 实现Kafka发布逻辑
- [ ] 实现订阅管理（从Kafka接收更新）
- [ ] 编写单元测试
- [ ] 编写集成测试
- [ ] 更新文档

---

## 七、总结

### 7.1 核心架构

```
LiveCore.DataManager
├── 管理多个数据源
│   ├── BacktestFeeder (历史K线)
│   └── LiveDataFeeder (实时Tick)
├── 统一数据格式
└── 发布到Kafka

ExecutionNode.Portfolio
├── 从Kafka消费数据
└── 专注交易逻辑
```

### 7.2 关键优势

1. ✅ **职责清晰**: DataManager管理数据，Portfolio管理交易
2. ✅ **松耦合**: 通过Kafka解耦，ExecutionNode无需知道数据来源
3. ✅ **灵活扩展**: 可轻松添加新数据源
4. ✅ **统一接口**: 对外统一提供DTO格式

### 7.3 与008原设计的差异

| 原设计 | 新设计 |
|--------|--------|
| DataManager创建新的LiveDataFeeder | DataManager使用现有LiveDataFeeder |
| LiveDataFeeder直接放Queue | LiveDataFeeder通过事件回调 |
| Queue消费者线程转换数据 | DataManager直接转换并发布Kafka |
| DataManager作为LiveCore组件 | DataManager管理多个数据源 |

---

**设计完成时间**: 2026-01-11
**下一步**: 实施DataManager多数据源版本
