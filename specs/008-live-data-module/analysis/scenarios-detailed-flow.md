# 主要场景数据流详细分析

**Feature**: 008-live-data-module
**Date**: 2026-01-11
**Purpose**: 详细分析实盘数据、历史数据的完整流程和触发时机

---

## 场景概览

| 场景 | 触发时机 | 数据源 | 消费者 | 频率 |
|------|---------|--------|--------|------|
| **场景1**: 实盘启动初始化 | LiveCore启动 | 历史K线 | Strategy | 一次性 |
| **场景2**: 实时Tick数据推送 | 外部数据源推送 | 实时Tick | Portfolio | 实时 |
| **场景3**: Selector定时更新 | TaskTimer定时触发 | - | ExecutionNode | 每小时 |
| **场景4**: 盘后K线分析 | TaskTimer定时触发 | 历史K线 | Portfolio | 每天21:00 |
| **场景5**: 数据更新任务 | TaskTimer定时触发 | 外部API | DataManager | 每天19:00 |

---

## 场景1: 实盘启动初始化

### 触发时机
- **触发**: ExecutionNode启动时
- **目的**: 策略需要历史数据初始化（如计算MA、RSI等指标）

### 完整流程

```
┌─────────────────────────────────────────────────────────────┐
│ 1. ExecutionNode启动                                       │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. PortfolioProcessor初始化Portfolio                       │
│    portfolio = Portfolio(mode="live")                       │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Strategy.initialize() 需要历史数据                        │
│    class MyStrategy(BaseStrategy):                         │
│        def initialize(self):                                │
│            # 需要加载60日历史K线计算MA60                     │
│            bars = self.get_historical_bars(...)             │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. Portfolio调用BarService                                 │
│    from ginkgo import services                              │
│    bar_service = services.data.services.bar_service()        │
│    bars = bar_service.get(...)  # 从ClickHouse查询          │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 5. BarService查询ClickHouse                                │
│    SELECT * FROM bars WHERE code='000001.SZ'                │
│      AND timestamp >= NOW() - 60 DAYS                       │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 6. 返回历史Bar数据                                          │
│    bars = [bar1, bar2, ..., bar60]                         │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 7. Strategy初始化指标                                       │
│    self.ma60 = calculate_ma(bars, period=60)                │
│    self.rsi = calculate_rsi(bars, period=14)                │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ 8. 策略准备就绪，等待实时数据                               │
└─────────────────────────────────────────────────────────────┘
```

### 关键点

- **不涉及LiveCore**: 初始化时直接访问BarService
- **不涉及Kafka**: 这是本地调用，不需要通过Kafka
- **同步执行**: 阻塞等待数据返回

### 代码示例

```python
# ExecutionNode侧
class PortfolioProcessor(Thread):
    def __init__(self, portfolio):
        self.portfolio = portfolio

    def initialize(self):
        # 初始化策略
        self.portfolio.strategy.initialize()

# Strategy侧
class MyStrategy(BaseStrategy):
    def initialize(self):
        # 通过DataMixin获取历史数据
        bars = self.get_daybar(
            code="000001.SZ",
            date=datetime.now() - timedelta(days=60)
        )

        # 计算指标
        self.ma60 = bars['close'].mean()
```

---

## 场景2: 实时Tick数据推送

### 触发时机
- **触发**: 外部数据源推送（东方财富、FuShu等）
- **目的**: 实时交易信号生成

### 完整流程

```
┌─────────────────────────────────────────────────────────────┐
│ [外部数据源] 东方财富WebSocket                               │
│  实时推送Tick数据                                           │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ [LiveCore] LiveDataFeeder (EastMoneyFeeder)                │
│  1. 接收WebSocket消息                                        │
│     websocket.recv()                                        │
│                                                              │
│  2. 解析Tick数据                                            │
│     tick = parse_message(message)                           │
│     tick = Tick(                                             │
│         code="000001.SZ",                                   │
│         price=10.50,                                        │
│         volume=10000,                                       │
│         timestamp=now()                                     │
│     )                                                       │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ [LiveCore] DataManager (通过事件回调)                       │
│  1. LiveDataFeeder设置事件发布器                             │
│     live_feeder.set_event_publisher(                        │
│         data_manager._on_live_data_received                 │
│     )                                                       │
│                                                              │
│  2. 接收实时Tick事件                                         │
│     def _on_live_data_received(self, event):                │
│         # event: EventPriceUpdate                           │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ [LiveCore] DataManager转换为DTO                             │
│  dto = PriceUpdateDTO.from_event(event)                     │
│                                                              │
│  dto = PriceUpdateDTO(                                       │
│      symbol="000001.SZ",                                    │
│      price=10.50,                                          │
│      volume=10000,                                         │
│      timestamp=now(),                                      │
│      bid_price=10.49,                                      │
│      ask_price=10.51,                                      │
│      ...                                                    │
│  )                                                         │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ [LiveCore] DataManager发布到Kafka                           │
│  kafka_producer.send(                                       │
│      topic="ginkgo.live.market.data",                       │
│      message=dto.model_dump_json()                          │
│  )                                                         │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ [Kafka] Topic: ginkgo.live.market.data                     │
│  持久化消息                                                 │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ [ExecutionNode] Kafka Consumer订阅                          │
│  consumer = GinkgoConsumer(                                 │
│      topic="ginkgo.live.market.data",                       │
│      group_id="execution_node_group"                        │
│  )                                                         │
│                                                              │
│  for message in consumer:                                   │
│      dto = PriceUpdateDTO.model_validate_json(message.value)│
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ [ExecutionNode] PortfolioProcessor转发给Portfolio           │
│  def _handle_market_data(self, dto):                        │
│      event = EventPriceUpdate.from_dto(dto)                 │
│      self.portfolio.put(event)                              │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ [ExecutionNode] Portfolio处理事件                           │
│  portfolio.on_price_update(event)                            │
│      ↓                                                       │
│  strategy.cal(portfolio_info, event)                        │
│      ↓                                                       │
│  生成交易信号 Signal                                        │
└─────────────────────────────────────────────────────────────┘
```

### 关键点

- **实时推送**: 由外部数据源主动推送，不是轮询
- **异步处理**: 通过WebSocket异步接收
- **Kafka解耦**: LiveCore和ExecutionNode通过Kafka解耦
- **事件驱动**: Portfolio通过事件驱动模型处理数据

### 代码示例

```python
# LiveCore侧
class DataManager(Thread):
    def __init__(self):
        # 创建LiveDataFeeder
        self.live_feeder = EastMoneyFeeder(queue=None)

        # 设置事件发布器（回调）
        self.live_feeder.set_event_publisher(self._on_live_data_received)

        # 启动LiveDataFeeder
        self.live_feeder.start()

    def _on_live_data_received(self, event):
        """实时数据回调"""
        # 转换为DTO
        dto = PriceUpdateDTO.from_event(event)

        # 发布到Kafka
        self.kafka_producer.send(
            topic="ginkgo.live.market.data",
            message=dto.model_dump_json()
        )

# ExecutionNode侧
class PortfolioProcessor(Thread):
    def __init__(self, portfolio):
        self.portfolio = portfolio

        # 订阅市场数据
        self.market_consumer = GinkgoConsumer(
            topic="ginkgo.live.market.data",
            group_id="execution_node_group"
        )

    def run(self):
        for message in self.market_consumer:
            dto = PriceUpdateDTO.model_validate_json(message.value)
            event = EventPriceUpdate.from_dto(dto)
            self.portfolio.put(event)
```

---

## 场景3: Selector定时更新

### 触发时机
- **触发**: TaskTimer定时任务（每小时整点）
- **目的**: 更新选股结果，调整订阅标的

### 完整流程

```
┌─────────────────────────────────────────────────────────────┐
│ [LiveCore] TaskTimer.APScheduler                            │
│  Cron: "0 * * * *" (每小时整点触发)                         │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ [LiveCore] TaskTimer._selector_update_job()                 │
│  1. 创建控制命令                                            │
│     command = {                                             │
│         "command": "update_selector",                       │
│         "timestamp": now().isoformat()                      │
│     }                                                       │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ [LiveCore] TaskTimer发布到Kafka                             │
│  kafka_producer.send(                                       │
│      topic="ginkgo.live.control.commands",                   │
│      message=json.dumps(command)                            │
│  )                                                         │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ [Kafka] Topic: ginkgo.live.control.commands                 │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ [ExecutionNode] PortfolioProcessor订阅控制命令               │
│  control_consumer = GinkgoConsumer(                         │
│      topic="ginkgo.live.control.commands",                  │
│      group_id="execution_node_control_group"                 │
│  )                                                         │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ [ExecutionNode] PortfolioProcessor._handle_control_command() │
│  def _handle_control_command(self, command):                │
│      if command["command"] == "update_selector":            │
│          self._update_selectors()                           │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ [ExecutionNode] PortfolioProcessor._update_selectors()       │
│  def _update_selectors(self):                                │
│      for selector in self.portfolio._selectors:            │
│          # 调用Selector选股                                 │
│          selected_codes = selector.pick(time=now())         │
│                                                                 │
│          # 创建EventInterestUpdate                           │
│          event = EventInterestUpdate(                        │
│              portfolio_id=self.portfolio.uuid,              │
│              codes=selected_codes,                            │
│              timestamp=now()                                 │
│          )                                                   │
│                                                                 │
│          # 发布到EventEngine                                │
│          self.portfolio.engine_put(event)                    │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ [ExecutionNode] Portfolio._interested (钩子方法)              │
│  def _interested(self, event):                               │
│      # 更新订阅集合                                          │
│      self._interested_symbols = set(event.codes)             │
│                                                                 │
│      # 发布EventInterestUpdate到Kafka                       │
│      self._publish_to_kafka(event)                           │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ [Kafka] Topic: ginkgo.live.interest.updates                  │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ [LiveCore] DataManager订阅订阅更新                          │
│  interest_consumer = GinkgoConsumer(                         │
│      topic="ginkgo.live.interest.updates",                   │
│      group_id="data_manager_group"                           │
│  )                                                         │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ [LiveCore] DataManager.update_subscriptions()               │
│  def update_subscriptions(self, symbols: Set[str]):         │
│      # 更新全局订阅集合                                      │
│      self.all_symbols = symbols                              │
│                                                                 │
│      # 更新LiveDataFeeder订阅                               │
│      self.live_feeder.subscribe_symbols(list(symbols))       │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ [LiveCore] LiveDataFeeder更新订阅                           │
│  WebSocket.send({                                            │
│      "cmd": "sub",                                           │
│      "symbols": ["000001.SZ", "600000.SH", ...]            │
│  })                                                         │
└─────────────────────────────────────────────────────────────┘
```

### 关键点

- **定时触发**: TaskTimer通过APScheduler定时触发
- **Kafka解耦**: TaskTimer不直接访问Portfolio
- **双向通信**:
  - TaskTimer → ExecutionNode (控制命令)
  - ExecutionNode → DataManager (订阅更新)
- **增量更新**: 只订阅变更部分

### 代码示例

```python
# TaskTimer侧
class TaskTimer(Thread):
    def _selector_update_job(self):
        """每小时更新Selector"""
        command = {
            "command": "update_selector",
            "timestamp": datetime.now().isoformat()
        }
        self.kafka_producer.send(
            topic="ginkgo.live.control.commands",
            message=json.dumps(command)
        )

# PortfolioProcessor侧
class PortfolioProcessor(Thread):
    def _update_selectors(self):
        """执行Selector选股"""
        for selector in self.portfolio._selectors:
            selected_codes = selector.pick(time=datetime.now())

            event = EventInterestUpdate(
                portfolio_id=self.portfolio.uuid,
                codes=selected_codes,
                timestamp=datetime.now()
            )

            self.portfolio.engine_put(event)

    def _publish_to_kafka(self, event):
        """发布订阅更新到Kafka"""
        dto = InterestUpdateDTO(
            portfolio_id=event.portfolio_id,
            node_id=self.node_id,
            codes=event.codes,
            timestamp=event.timestamp
        )

        self.kafka_producer.send(
            topic="ginkgo.live.interest.updates",
            message=dto.model_dump_json()
        )

# DataManager侧
class DataManager(Thread):
    def update_subscriptions(self, symbols: Set[str]):
        """更新订阅标的"""
        self.all_symbols = symbols
        self.live_feeder.subscribe_symbols(list(symbols))
```

---

## 场景4: 盘后K线分析

### 触发时机
- **触发**: TaskTimer定时任务（每天21:00）
- **目的**: 发布当日K线数据，触发策略盘后分析

### 完整流程

```
┌─────────────────────────────────────────────────────────────┐
│ [LiveCore] TaskTimer.APScheduler                            │
│  Cron: "0 21 * * *" (每天21:00触发)                         │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ [LiveCore] TaskTimer._bar_analysis_job()                    │
│  1. 获取当前订阅标的                                        │
│     symbols = list(self.all_symbols)  # 从DataManager获取   │
│                                                              │
│  2. 查询当日K线数据                                         │
│     bars = bar_service.get_bars(                            │
│         symbols=symbols,                                    │
│         start_date=now().replace(hour=0, minute=0),          │
│         end_date=now()                                       │
│     )                                                       │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ [LiveCore] TaskTimer查询ClickHouse                          │
│  SELECT * FROM bars                                         │
│  WHERE code IN ('000001.SZ', ...)                           │
│    AND timestamp >= TODAY()                                 │
│    AND timestamp < NOW()                                    │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ [LiveCore] TaskTimer转换为BarDTO                            │
│  for symbol, bars in bars_data.items():                     │
│      for bar in bars:                                        │
│          dto = BarDTO.from_bar(bar)                          │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ [LiveCore] TaskTimer发布到Kafka                             │
│  kafka_producer.send(                                       │
│      topic="ginkgo.live.market.data",                       │
│      message=dto.model_dump_json()                          │
│  )                                                         │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ [Kafka] Topic: ginkgo.live.market.data                     │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ [ExecutionNode] PortfolioProcessor接收                      │
│  for message in market_consumer:                            │
│      dto = parse_message(message)                            │
│      if isinstance(dto, BarDTO):                            │
│          event = EventBar.from_dto(dto)                     │
│          self.portfolio.put(event)                          │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ [ExecutionNode] Portfolio盘后分析                           │
│  portfolio.on_bar_update(event)                              │
│      ↓                                                       │
│  strategy.cal(portfolio_info, event)                        │
│      ↓                                                       │
│  生成调仓信号 Signal                                        │
└─────────────────────────────────────────────────────────────┘
```

### 关键点

- **使用BarService**: TaskTimer直接调用BarService查询ClickHouse
- **批量查询**: 一次查询所有订阅标的当日K线
- **K线数据**: 发布的是BarDTO，不是Tick数据
- **盘后分析**: 策略可以基于完整K线做分析决策

### 代码示例

```python
# TaskTimer侧
class TaskTimer(Thread):
    def __init__(self):
        # 订阅DataManager的订阅更新
        self.interest_consumer = GinkgoConsumer(
            topic="ginkgo.live.interest.updates"
        )

        # 维护订阅标的集合
        self.all_symbols = set()

    def run(self):
        # 订阅订阅更新
        for message in self.interest_consumer:
            dto = InterestUpdateDTO.model_validate_json(message.value)
            self.all_symbols = set(dto.symbols)

    def _bar_analysis_job(self):
        """每天21:00执行K线分析"""
        bar_service = services.data.services.bar_service()

        # 查询当日K线
        today_start = datetime.now().replace(hour=0, minute=0, second=0)
        bars = bar_service.get(
            symbols=list(self.all_symbols),
            start_date=today_start.date(),
            end_date=datetime.now().date()
        )

        # 发布到Kafka
        for bar in bars:
            dto = BarDTO.from_bar(bar)
            self.kafka_producer.send(
                topic="ginkgo.live.market.data",
                message=dto.model_dump_json()
            )
```

---

## 场景5: 数据更新任务

### 触发时机
- **触发**: TaskTimer定时任务（每天19:00）
- **目的**: 触发外部数据源更新数据（如调用数据源API刷新日K线）

### 完整流程

```
┌─────────────────────────────────────────────────────────────┐
│ [LiveCore] TaskTimer.APScheduler                            │
│  Cron: "0 19 * * *" (每天19:00触发)                         │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ [LiveCore] TaskTimer._data_update_job()                     │
│  1. 创建数据更新命令                                        │
│     command = {                                             │
│         "command": "update_data",                           │
│         "data_type": "daily_bar",                           │
│         "date": today().isoformat()                         │
│     }                                                       │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ [LiveCore] TaskTimer发布到Kafka                             │
│  kafka_producer.send(                                       │
│      topic="ginkgo.live.control.commands",                   │
│      message=json.dumps(command)                            │
│  )                                                         │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ [LiveCore] DataManager订阅控制命令 (可选)                   │
│  或由专门的DataUpdateService处理                             │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ [外部数据源] 调用API更新数据                                 │
│  - Tushare API: daily()                                    │
│  - 东方财富API: 刷新日K线                                    │
└─────────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────────┐
│ [ClickHouse] 数据被更新到数据库                              │
└─────────────────────────────────────────────────────────────┘
```

### 关键点

- **异步任务**: 数据更新是异步任务，不阻塞实盘交易
- **外部触发**: 通过Kafka命令触发，或直接调用外部API
- **数据刷新**: 确保ClickHouse中有最新的历史数据

---

## 关键数据流对比

### 数据流对比表

| 维度 | 场景1: 初始化 | 场景2: 实时Tick | 场景3: Selector更新 | 场景4: 盘后K线 |
|------|-------------|---------------|-------------------|---------------|
| **触发** | ExecutionNode启动 | 外部数据源推送 | TaskTimer定时 | TaskTimer定时 |
| **数据源** | BarService → ClickHouse | LiveDataFeeder → WebSocket | Selector.pick() | BarService → ClickHouse |
| **数据格式** | Bar (历史) | Tick (实时) | codes列表 | Bar (当日) |
| **传输方式** | 直接调用 | WebSocket回调 | Kafka命令 | Kafka发布 |
| **Topic** | 无 | ginkgo.live.market.data | ginkgo.live.control.commands<br>ginkgo.live.interest.updates | ginkgo.live.market.data |
| **消费者** | Strategy | Portfolio | Portfolio → DataManager | Portfolio |
| **频率** | 一次性 | 实时（毫秒级） | 每小时 | 每天21:00 |

### Kafka Topic使用总结

| Topic | 发布者 | 订阅者 | 用途 | 数据类型 |
|-------|--------|--------|------|---------|
| **ginkgo.live.control.commands** | TaskTimer | ExecutionNode | Selector触发、数据更新 | 控制命令 |
| **ginkgo.live.interest.updates** | ExecutionNode | DataManager, TaskTimer | 订阅标的更新 | InterestUpdateDTO |
| **ginkgo.live.market.data** | DataManager, TaskTimer | ExecutionNode | 实时行情数据 | PriceUpdateDTO, BarDTO |

---

## 完整时序图

### 实盘运行时序

```
时间轴 →

[T0] LiveCore启动
      ├── DataManager启动
      │   ├── BacktestFeeder初始化（可选）
      │   └── LiveDataFeeder启动（WebSocket连接）
      └── TaskTimer启动
          └── APScheduler启动

[T1] ExecutionNode启动
      ├── Portfolio初始化
      │   └── Strategy.initialize()需要历史数据
      │       └── BarService.get_bars() → ClickHouse [场景1]
      └── Kafka Consumer启动
          ├── 订阅 market.data
          └── 订阅 control.commands

[T2] TaskTimer定时触发 (每小时)
      └── 发送 "update_selector" 命令 [场景3]
          ↓ Kafka
          ExecutionNode接收命令
          ├── Selector.pick()
          ├── EventInterestUpdate → Kafka
          └── DataManager订阅更新
              └── LiveDataFeeder更新订阅

[T3] 实时Tick数据到达 (持续)
      └── 外部数据源推送 [场景2]
          ↓ LiveDataFeeder
          ↓ DataManager
          ↓ Kafka (market.data)
          ↓ ExecutionNode
          └── Portfolio.on_price_update()

[T4] TaskTimer定时触发 (21:00)
      └── 查询当日K线 [场景4]
          ├── BarService.get_bars() → ClickHouse
          ├── 转换为BarDTO
          └── Kafka (market.data)
              ↓ ExecutionNode
              └── Portfolio.on_bar_update()

[T5] TaskTimer定时触发 (19:00)
      └── 数据更新任务 [场景5]
          └── 触发外部数据源更新ClickHouse
```

---

## 总结

### 核心架构原则

1. **LiveCore = 数据层**
   - DataManager: 管理所有数据源
   - TaskTimer: 定时任务调度

2. **ExecutionNode = 执行层**
   - Portfolio: 交易逻辑
   - 无需关心数据来源

3. **Kafka = 事件总线**
   - 解耦LiveCore和ExecutionNode
   - 支持多消费者

4. **数据源分离**
   - 历史数据: BarService → ClickHouse
   - 实时数据: LiveDataFeeder → WebSocket

### 关键设计决策

✅ **Strategy初始化直接访问BarService**
- 不通过LiveCore
- 不通过Kafka
- 同步调用

✅ **实时数据通过LiveDataFeeder接收**
- 异步WebSocket推送
- 通过DataManager转换
- 发布到Kafka

✅ **Selector更新通过Kafka控制命令**
- TaskTimer不直接访问Portfolio
- ExecutionNode执行Selector
- 订阅更新通过Kafka返回

✅ **盘后K线通过BarService查询**
- TaskTimer定时查询
- 批量发布到Kafka
- Portfolio进行盘后分析

---

**分析完成时间**: 2026-01-11
