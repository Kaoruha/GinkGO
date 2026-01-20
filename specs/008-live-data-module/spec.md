# Feature Specification: 实盘数据模块完善

**Feature Branch**: `008-live-data-module`
**Created**: 2026-01-08
**Status**: Draft
**Input**: User description: "完善实盘的数据模块，要考虑接入多个外部接口，主要考虑两种情况，一种是以Tick数据为触发，一种是定时触发"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - 实时行情数据订阅与处理 (Priority: P1)

量化交易员需要实时接收市场行情数据（Tick级别），以便策略能够基于最新市场价格做出交易决策。

**Why this priority**: 实时行情数据是实盘交易的基础，所有交易策略都依赖及时、准确的市场数据。没有实时数据，实盘系统无法运行。

**Independent Test**: 可以通过模拟数据源发送实时Tick数据，验证DataManager能够正确接收、解析并发布到Kafka，ExecutionNode能够接收并触发Portfolio策略计算。

**Acceptance Scenarios**:

1. **Given** DataManager已启动并配置了数据源，**When** 数据源推送Tick数据，**Then** DataManager应该接收数据、验证格式、发布EventPriceUpdate到Kafka
2. **Given** DataManager与数据源连接断开，**When** 网络恢复，**Then** DataManager应该自动重连并恢复数据订阅
3. **Given** Tick数据包含异常值（如价格为零、时间戳倒流），**When** DataManager接收此类数据，**Then** 应该过滤异常数据并记录警告日志
4. **Given** 数据源推送频率超过系统处理能力，**When** 接收队列满载，**Then** 应该触发限流机制，优先处理最新数据

---

### User Story 2 - 定时控制命令发送 (Priority: P1)

量化交易员需要定时触发Portfolio执行特定操作（如Selector更新、K线快照分析等），以确保实盘系统按预期周期运行策略。

**Why this priority**: 实盘模式下，时间连续推进，需要定时触发机制来确保策略定期执行选股、盘后分析等任务。定时控制命令机制确保了TaskTimer（LiveCore）与Portfolio（ExecutionNode）的解耦。

**Independent Test**: 可以通过配置定时任务（如每1分钟），验证TaskTimer能够按计划发送控制命令到Kafka，触发ExecutionNode执行相应操作。

**Acceptance Scenarios**:

1. **Given** TaskTimer配置了定时任务（如每小时），**When** 到达触发时间，**Then** TaskTimer应该发送控制命令到Kafka Topic `ginkgo.live.control.commands`
2. **Given** TaskTimer发送控制命令时Kafka暂时不可用，**When** 发送失败，**Then** 应该记录错误并等待下次触发，不影响其他定时任务
3. **Given** 配置了多个定时任务（Selector更新、K线分析、数据更新），**When** 不同任务触发时间到达，**Then** 应该按照各自的cron表达式独立触发，互不影响
4. **Given** ExecutionNode接收到控制命令，**When** 命令类型为"bar_snapshot"，**Then** Portfolio应该自己调用BarService获取当日K线数据并执行分析

---

### User Story 3 - 多数据源统一接入 (Priority: P2)

量化交易员需要能够灵活切换或同时使用多个数据源（如Tushare、东方财富、同花顺等），以便优化数据质量、降低延迟或降低成本。

**Why this priority**: 实盘生产环境中，单一数据源可能存在延迟高、数据质量差、服务中断等问题。多数据源支持能够提高系统的可靠性和数据质量。

**Independent Test**: 可以通过配置多个数据源实例，验证DataManager能够根据配置自动选择数据源，或在主数据源故障时切换到备用数据源。

**Acceptance Scenarios**:

1. **Given** 配置了多个数据源（主数据源和备用数据源），**When** 主数据源正常工作，**Then** 应该优先使用主数据源获取数据
2. **Given** 主数据源连接失败或超时，**When** 检测到故障，**Then** 应该自动切换到备用数据源并记录切换日志
3. **Given** 不同数据源返回的数据格式存在差异，**When** 接收数据，**Then** 应该统一转换为Ginkgo标准格式（EventPriceUpdate、Bar等）
4. **Given** 同时订阅多个数据源相同标的的数据，**When** 接收数据，**Then** 应该能够去重并选择最优数据（如选择最早到达的数据）

---

### User Story 4 - 数据质量监控与告警 (Priority: P3)

系统运维人员需要实时监控数据质量（如延迟、缺失、异常值），以便及时发现数据问题并采取措施。

**Why this priority**: 数据质量问题可能导致策略错误决策或交易失败。监控告警能够及时发现问题，减少潜在损失。

**Independent Test**: 可以通过模拟各种数据质量问题（延迟、缺失、异常），验证监控模块能够检测并生成告警事件。

**Acceptance Scenarios**:

1. **Given** 正在接收实时行情数据，**When** 数据延迟超过阈值（如1秒），**Then** 应该生成延迟告警事件并发布到Kafka
2. **Given** 正在接收实时行情数据，**When** 检测到数据缺失（如预期Tick未到达），**Then** 应该生成缺失告警并尝试从备用数据源获取
3. **Given** 接收到价格异常数据（如涨跌幅超过10%），**When** 检测到异常，**Then** 应该生成异常告警事件，策略可选择是否忽略该数据
4. **Given** 数据源连接失败，**When** 重连次数超过阈值，**Then** 应该生成严重告警并通知运维人员介入

---

### Edge Cases

- **数据源并发限流**: 当多个策略同时订阅同一数据源时，如何避免触发数据源的并发限制？
- **时间戳不一致**: 不同数据源的时间戳可能存在时区差异或时钟偏差，如何统一时间基准？
- **市场异常时段**: 如开盘/收盘集合竞价、涨跌停停牌等特殊时段，数据推送频率和格式可能变化，如何处理？
- **网络抖动与丢包**: 网络不稳定可能导致数据包乱序或丢失，如何检测和恢复？
- **系统重启恢复**: 系统重启后如何快速恢复数据订阅并补充缺失的历史数据？
- **多数据源冲突**: 当多个数据源对同一时刻的数据存在不一致时，如何选择和仲裁？
- **数据源降级**: 当所有数据源都不可用时，系统是否应该进入安全模式（暂停交易）？

## Architecture Design *(confirmed)*

### 设计目标

支持两种触发模式：
1. **实时触发**: Tick数据推送 → 策略生成信号
2. **定时触发**: 盘后K线数据 → 策略生成信号

### 核心架构

```
┌─────────────────────────────────────────────────────────────┐
│                      LiveCore (数据层)                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           DataManager (数据管理器)                    │   │
│  │                                                      │   │
│  │  管理多个数据源:                                       │   │
│  │  ┌──────────────────────────────────────────────┐   │   │
│  │  │  BacktestFeeder (历史K线数据)                  │   │   │
│  │  │  - 现有实现: ginkgo/trading/feeders/        │   │   │
│  │  │  - 数据源: ClickHouse                         │   │   │
│  │  │  - 用途: 策略初始化、盘后分析                 │   │   │
│  │  └──────────────────────────────────────────────┘   │   │
│  │  ┌──────────────────────────────────────────────┐   │   │
│  │  │  LiveDataFeeder (实时Tick数据)                  │   │   │
│  │  │  - 现有实现: ginkgo/trading/feeders/        │   │   │
│  │  │  - 数据源: WebSocket (东方财富等)              │   │   │
│  │  │  - 用途: 实时交易信号                           │   │   │
│  │  └──────────────────────────────────────────────┘   │   │
│  │                                                      │   │
│  │  数据转换 → Kafka发布                                 │   │
│  │  └── 订阅管理 (从Kafka接收订阅更新)                  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           TaskTimer (定时任务调度器)                 │   │
│  │                                                      │   │
│  │  - APScheduler: Cron表达式调度                       │   │
│  │  - 订阅: ginkgo.live.interest.updates                 │   │
│  │  - 任务:                                             │   │
│  │    ├── Selector更新任务 (每小时)                      │   │
│  │    ├── 数据更新任务 (每天19:00)                      │   │
│  │    └── K线分析任务 (每天21:00)                       │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                          ↓ Kafka Topics
┌─────────────────────────────────────────────────────────────┐
│                 Kafka (事件总线)                             │
│                                                              │
│  - ginkgo.live.control.commands  (控制命令)                 │
│  - ginkgo.live.interest.updates  (订阅更新)                │
│  - ginkgo.live.market.data       (市场数据)                 │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│                ExecutionNode (执行层)                       │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           PortfolioProcessor                           │   │
│  │    - 订阅 control.commands (接收控制命令)              │   │
│  │    - 订阅 market.data (接收市场数据)                   │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │           Portfolio (交易逻辑)                         │   │
│  │    - Selector: 选股逻辑                                │   │
│  │    - Strategy: 策略计算                                │   │
│  │    - RiskManager: 风控管理                             │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 架构分层说明

| 层次 | 组件 | 职责 | 数据源 |
|------|------|------|--------|
| **LiveCore (数据层)** | DataManager | 管理实时数据源、转换格式、发布Kafka | LiveDataFeeder |
| **LiveCore (数据层)** | TaskTimer | 定时任务调度、触发Selector更新 | BarService |
| **Kafka (事件总线)** | Topics | 解耦LiveCore和ExecutionNode | - |
| **ExecutionNode (执行层)** | Portfolio | 交易逻辑、策略计算 | 从Kafka消费 |

### 数据流

#### 场景1: 实盘启动初始化（一次性）

```
ExecutionNode启动
    ↓
Portfolio.initialize()
    ↓
Strategy.initialize() 需要历史数据
    ↓
BarService.get_bars() → ClickHouse (直接调用，不经过LiveCore)
    ↓
返回历史Bar数据
    ↓
Strategy计算指标 (MA60、RSI等)
```

**关键说明**:
- Strategy初始化直接访问BarService，不经过LiveCore
- 同步调用，阻塞等待数据返回
- 仅启动时执行一次

#### 场景2: 实时Tick数据推送（实时，持续）

```
外部数据源 (WebSocket)
    ↓ Tick数据
[LiveCore] LiveDataFeeder (现有实现: ginkgo/trading/feeders/live_feeder.py)
    ↓ EventPriceUpdate
[LiveCore] DataManager (通过事件回调)
    ↓ 转换为PriceUpdateDTO
    ↓ Kafka Producer
Topic: ginkgo.live.market.data
    ↓
[ExecutionNode] Kafka Consumer
    ↓ PriceUpdateDTO
    ↓ EventPriceUpdate
    ↓ Portfolio.on_price_update()
    ↓ Strategy.cal() → 生成交易信号
```

**关键说明**:
- LiveDataFeeder使用现有实现，不重复开发
- 实时数据通过WebSocket异步推送
- 通过Kafka解耦LiveCore和ExecutionNode

#### 场景3: Selector定时更新（每小时）

```
[LiveCore] TaskTimer (每小时整点)
    ↓ 发送控制命令
Kafka Producer → Topic: ginkgo.live.control.commands
    ↓ 命令: {"command": "update_selector"}
    ↓
[ExecutionNode] Kafka Consumer
    ↓ PortfolioProcessor._handle_control_command()
    ↓ PortfolioProcessor._update_selectors()
    ↓ for selector in portfolio._selectors:
    ↓   selector.pick(time) → selected_codes
    ↓   EventInterestUpdate → engine_put
    ↓ Portfolio._interested()
    ↓ Kafka Producer → Topic: ginkgo.live.interest.updates
    ↓
[LiveCore] DataManager 订阅更新
    ↓ update_subscriptions(symbols)
    ↓ LiveDataFeeder.subscribe_symbols(symbols)
    ↓ WebSocket发送订阅消息
```

**关键说明**:
- TaskTimer不直接访问Portfolio，通过Kafka解耦
- ExecutionNode执行Selector逻辑
- 订阅更新通过Kafka返回DataManager

#### 场景4: 盘后K线分析（每天21:00）

```
[LiveCore] TaskTimer (21:00触发)
    ↓ 发送控制命令
Kafka Producer → Topic: ginkgo.live.control.commands
    ↓ {"command": "bar_snapshot"}
    ↓
[LiveCore] DataManager 订阅控制命令
    ↓ 接收 bar_snapshot 命令
    ↓ 从BarService获取所有兴趣标的当日K线
    ↓ 封装为PriceUpdateDTO
    ↓ Kafka Producer → Topic: ginkgo.live.market.data
    ↓
[ExecutionNode] Kafka Consumer
    ↓ Portfolio.on_price_update()  ← 复用现有方法！
    ↓ Strategy.cal(当日K线) 执行盘后分析
    ↓ 生成调仓信号
```

**关键说明**:
- TaskTimer只发送控制命令，不获取数据
- DataManager接收bar_snapshot命令后，从BarService获取当日K线并推送
- Portfolio复用on_price_update()处理K线数据，无需新增方法
- 实时Tick和盘后K线走相同的事件处理流程

#### 场景5: 数据更新任务（每天19:00）

```
[LiveCore] TaskTimer (19:00触发)
    ↓ 发送控制命令 {"command": "update_data"}
    ↓ Kafka Producer → Topic: ginkgo.live.control.commands
    ↓
[外部服务] DataUpdateService (或DataManager)
    ↓ 调用外部API更新数据
    ↓ Tushare/东方财富 API
    ↓
[ClickHouse] 数据被更新到数据库
```

**关键说明**:
- 异步任务，不阻塞实盘交易
- 确保ClickHouse有最新历史数据

### LiveDataFeeder基类

**接口**:
- `set_symbols(symbols: Set[str])` - 增量更新订阅
- `start()` - 启动（异步连接）
- `stop()` - 停止（标志位）
- `_connect()` - 连接数据源（websocket/http）
- `_subscribe()` - 订阅标的
- `_unsubscribe()` - 取消订阅

**市场过滤**:
```python
MARKET_MAPPING = {
    "cn": [".SH", ".SZ"],
    "hk": [".HK"],
    "us": []  # 无后缀
}
```

### LiveDataFeeder多态设计

**设计目标**: 通过多态直接挂载不同LiveDataFeeder实现，配置写死在代码中，敏感信息从secure.yml读取。

**多态挂载**:
```python
class DataManager(Thread):
    def __init__(self, feeder_type: str = "eastmoney"):
        # 多态挂载点：根据类型直接创建Feeder
        self.live_feeder = self._create_feeder(feeder_type)

    def _create_feeder(self, feeder_type: str) -> ILiveDataFeeder:
        """创建LiveDataFeeder实例（多态）"""
        if feeder_type == "eastmoney":
            return EastMoneyFeeder()
        elif feeder_type == "fushu":
            return FuShuFeeder()
        # ... 添加新数据源
```

**Feeder实现示例**:
```python
class EastMoneyFeeder(ILiveDataFeeder):
    """东方财富WebSocket数据源（A股）"""

    def __init__(self):
        super().__init__()

        # 写死的配置
        self.websocket_uri = "wss://push2.eastmoney.com/ws/qt/stock/klt.min"
        self.ping_interval = 30

        # 敏感配置从 secure.yml 读取
        self.api_key = GCONF.get("data_sources.eastmoney.api_key")
```

**收益**:
- ✅ 架构简单，无需工厂模式
- ✅ 灵活性通过多态实现（切换不同Feeder类）
- ✅ 敏感配置统一在secure.yml管理
- ✅ 易于测试（可注入MockFeeder）

### 回测模式 vs 实盘模式的Selector触发机制

**核心差异**: 回测模式下时间按Bar推进（通常按天），实盘模式下时间连续推进（每秒），导致Selector触发机制需要不同实现。

**关键架构决策**: TaskTimer运行在LiveCore，Portfolio运行在ExecutionNode，两者通过Kafka解耦。

#### 回测模式（已实现）

```
EventBarUpdate (每根K线)
    ↓
Portfolio._on_time_advance(new_time)
    ↓
for selector in self._selectors:
    selector.advance_time(new_time)  # 封装了 pick() 和事件发布
```

**特点**: 每根K线触发一次Selector，频率合理（每天1次），适合回测。

#### 实盘模式（需实现）

**问题**:
1. 时间连续推进，无法每次都触发Selector（每秒触发会导致过载）
2. TaskTimer(LiveCore) 无法直接访问 Portfolio(ExecutionNode)

**解决方案**: 通过Kafka控制命令解耦

**TaskTimer实现（LiveCore）**:
```python
class TaskTimer(Thread):
    def __init__(self):
        self.kafka_producer = GinkgoProducer()

    def _selector_update_job(self):
        """定时发送Selector更新触发命令"""
        # 发送控制命令到所有ExecutionNode
        command = {
            "command": "update_selector",
            "timestamp": datetime.now().isoformat()
        }

        self.kafka_producer.send(
            topic=KafkaTopics.CONTROL_COMMANDS,
            message=command
        )

    # 配置定时任务
    scheduler.add_job(
        func=self._selector_update_job,
        trigger=CronTrigger(minute="0"),  # 每小时触发一次
        id='selector_update'
    )
```

**ExecutionNode实现（接收端）**:
```python
class PortfolioProcessor(Thread):
    def _handle_control_command(self, command: dict):
        """处理控制命令"""
        if command["command"] == "update_selector":
            self._update_selectors()

    def _update_selectors(self):
        """调用所有Selector的pick方法"""
        for selector in self.portfolio._selectors:
            # 直接调用 pick() 获取选股结果
            selected_codes = selector.pick(time=datetime.now())

            # 创建 EventInterestUpdate
            event = EventInterestUpdate(
                portfolio_id=self.portfolio.uuid,
                codes=selected_codes,
                timestamp=datetime.now()
            )

            # 发布到 Kafka
            self.portfolio.engine_put(event)
```

**关键点**:
- TaskTimer**不直接访问**Portfolio，只发送触发命令
- ExecutionNode接收命令后，PortfolioProcessor调用 `selector.pick()`
- EventInterestUpdate由ExecutionNode发布到Kafka
- DataManager订阅 `ginkgo.live.interest.updates` 接收更新
- 符合事件驱动架构，组件完全解耦

### Queue设计

- **有界队列**: `Queue(maxsize=10000)`
- **满时策略**: 丢弃当前数据（warn日志）
- **消费者**: 阻塞等待（一个Queue对应一个消费线程）
- **转换**: Queue消费者将Tick转换为DTO后发布Kafka

### Kafka Topics (统一管理)

定义于 `src/ginkgo/interfaces/kafka_topics.py`:

- `ginkgo.live.interest.updates` - 订阅更新
- `ginkgo.live.market.data` - 实时行情
- `ginkgo.live.orders.submission` - 订单提交
- `ginkgo.live.orders.feedback` - 订单回报
- `ginkgo.live.control.commands` - 控制命令
- `ginkgo.live.schedule.updates` - 调度更新
- `ginkgo.live.system.events` - 系统事件
- `ginkgo.notifications` - 通知

### DTO定义

**InterestUpdateDTO**: 订阅更新消息
```python
{
    "portfolio_id": str,
    "node_id": str,
    "symbols": List[str],
    "timestamp": datetime
}
```

**PriceUpdateDTO**: 实时Tick（完整版）
```python
{
    "symbol", "price", "volume", "amount",
    "bid_price", "ask_price", "bid_volume", "ask_volume",
    "open_price", "high_price", "low_price",
    "timestamp"
}
```

**BarDTO**: K线数据（完整版）
```python
{
    "symbol", "period",
    "open", "high", "low", "close", "volume", "amount",
    "turnover", "change", "change_pct",
    "timestamp"
}
```

### 配置策略

- **配置文件**: TaskTimer规则通过 `~/.ginkgo/task_timer.yml` 配置，敏感密钥通过 `~/.ginkgo/secure.yml` 管理
- **环境变量**: Kafka/Redis地址、数据源API Token（支持 ${VAR_NAME} 格式）
- **硬编码**: LiveDataFeeder WebSocket URI、市场映射（MARKET_MAPPING）
- **重用现有组件**: LiveDataFeeder基类使用现有实现 `ginkgo/trading/feeders/live_feeder.py`
- **新建组件**: DataManager、TaskTimer、多市场Feeder适配器（EastMoneyFeeder、FuShuFeeder等）
- **未来扩展**: 定时任务配置化（TaskTimer支持多种任务类型）

### 定时任务说明

**数据更新任务** (19:00触发):
- 目的: 触发外部数据源更新数据（如调用数据源API刷新日K线）
- 实现: 发送控制命令到Kafka `ginkgo.live.control.commands`

**K线触发分析任务** (21:00触发):
- 目的: 发送当日K线数据到Kafka，触发策略分析
- 实现: 从ClickHouse查询当日K线，通过BarService获取，发布到Kafka

### 启动顺序

```python
1. DataManager.start()
   ├── 启动Kafka Consumer
   ├── 启动Queue消费者线程
   └── 启动各LiveDataFeeder
2. TaskTimer.start()
   ├── 启动Kafka Consumer
   └── 启动APScheduler
3. Scheduler.start() (007已实现)
```

### 停止顺序（反向）

```python
1. Scheduler.stop()
2. TaskTimer.stop()
3. DataManager.stop()
   ├── 停止各LiveDataFeeder
   ├── 停止Consumer
   ├── 等待Queue消费完
   └── 关闭Kafka
```

## Requirements *(mandatory)*

### Functional Requirements

**Ginkgo 架构约束**:
- **FR-001**: System MUST 遵循事件驱动架构 (DataManager → Kafka EventPriceUpdate → ExecutionNode → Portfolio)
- **FR-002**: System MUST 使用ServiceHub模式，通过`from ginkgo import services`访问数据服务
- **FR-003**: System MUST 严格分离数据层、策略层、执行层、服务层职责
- **FR-004**: System MUST 使用`@time_logger`、`@retry`、`@cache_with_expiration`装饰器进行性能优化
- **FR-005**: System MUST 遵循六边形架构约束，DataManager作为Driven Adapter不应包含业务逻辑

**量化交易特有需求**:
- **FR-006**: System MUST 支持Tick级别实时数据推送（延迟 < 100ms）
- **FR-007**: System MUST 支持定时控制命令发送（支持秒级到小时级间隔配置）
- **FR-008**: System MUST 支持多数据源统一接入（Tushare、东方财富、同花顺等）
- **FR-009**: System MUST 实现数据源自动切换和故障恢复
- **FR-010**: System MUST 提供数据质量监控（延迟、缺失、异常值检测）

**实时数据触发模式**:
- **FR-011**: DataManager MUST 支持WebSocket长连接接收实时Tick数据推送
- **FR-012**: DataManager MUST 实现断线重连机制（指数退避算法，最大重试次数可配置）
- **FR-013**: DataManager MUST 实现心跳检测机制（定期发送ping/pong消息保持连接）
- **FR-014**: DataManager MUST 实现数据订阅管理（动态添加/删除订阅标的）
- **FR-015**: DataManager MUST 实现数据解析和格式转换（将数据源格式转为Ginkgo标准事件）
- **FR-016**: DataManager MUST 实现限流机制（防止数据源过载或系统过载）

**实盘模式Selector触发机制**:
- **FR-022**: System MUST 区分回测模式和实盘模式的Selector触发机制
- **FR-023**: 回测模式下，Selector通过Portfolio._on_time_advance()调用advance_time()触发（每根K线）
- **FR-024**: 实盘模式下，TaskTimer(LiveCore)发送Kafka控制命令触发Selector更新
- **FR-025**: TaskTimer MUST 支持定时发送"update_selector"控制命令（通过cron表达式配置触发频率）
- **FR-025-1**: TaskTimer MUST 支持多个定时规则，每个规则使用独立的cron表达式配置
- **FR-025-2**: TaskTimer MUST 支持常用cron表达式（每分钟、每小时、每天、每周）
- **FR-026**: ExecutionNode MUST 订阅Kafka Topic `ginkgo.live.control.commands`接收控制命令
- **FR-027**: ExecutionNode的PortfolioProcessor MUST 实现`_update_selectors()`方法调用selector.pick()
- **FR-028**: ExecutionNode MUST 负责创建EventInterestUpdate并发布到Kafka Topic
- **FR-029**: System MUST 支持通过Kafka控制命令手动触发Selector更新

**多数据源管理**:
- **FR-030**: DataManager MUST 使用多态模式创建LiveDataFeeder实例（直接实例化EastMoneyFeeder等）
- **FR-031**: DataManager MUST 支持从secure.yml读取数据源API密钥（通过GCONF.get()）
- **FR-032**: LiveDataFeeder配置写死在代码中（WebSocket URI、轮询间隔等）
- **FR-033**: DataManager MUST 重用现有LiveDataFeeder基类（ginkgo/trading/feeders/live_feeder.py）
- **FR-034**: DataManager MUST 支持扩展新Feeder类（继承ILiveDataFeeder接口）
- **FR-035**: DataManager MUST 实现数据格式统一转换（不同数据源转为统一DTO格式）

**数据质量控制**:
- **FR-039**: DataManager MUST 实现数据延迟监控（测量数据从产生到接收的时间差）
- **FR-040**: DataManager MUST 实现数据缺失检测（检测预期数据未到达）
- **FR-041**: DataManager MUST 实现异常值过滤（过滤价格、成交量的异常值）
- **FR-042**: DataManager MUST 实现数据去重（避免重复处理相同数据）
- **FR-043**: DataManager MUST 实现数据时间戳校验（检测时间倒流或时区错误）

**Kafka集成**:
- **FR-044**: DataManager MUST 将实时数据发布到Kafka Topic `ginkgo.live.market.data`
- **FR-045**: DataManager MUST 使用统一DTO格式（PriceUpdateDTO、BarDTO等）
- **FR-046**: DataManager MUST 实现Kafka发布失败重试（避免数据丢失）
- **FR-047**: DataManager MUST 支持批量发布（提高吞吐量）

**配置管理**:
- **FR-048**: DataManager MUST 支持运行时动态修改订阅标的（通过Kafka控制命令）

**代码维护与文档需求**:
- **FR-049**: Code files MUST include three-line headers (Upstream/Downstream/Role) for AI understanding
- **FR-050**: LiveDataFeeder只需实现逻辑，不需要编写具体测试（由实际使用验证）
- **FR-051**: 其他组件（DataManager、TaskTimer、DTO等）必须包含完整的TDD测试

**性能与可靠性**:
- **FR-052**: 实时数据处理延迟 MUST < 100ms（从接收到发布到Kafka）
- **FR-053**: 每个定时规则触发精度 MUST < 1秒（误差范围）
- **FR-054**: 数据源切换时间 MUST < 5秒（从检测故障到切换完成）
- **FR-055**: DataManager MUST 支持至少10个并发数据源订阅
- **FR-056**: DataManager MUST 保证数据零丢失（Kafka发布失败必须重试）

### Key Entities *(include if feature involves data)*

- **DataManager**: 实时数据管理器，负责管理LiveDataFeeder、接收实时Tick数据、转换为DTO并发布到Kafka
  - 管理LiveDataFeeder（多态挂载：EastMoneyFeeder/FuShuFeeder/AlpacaFeeder）
  - 订阅 `ginkgo.live.interest.updates` 接收ExecutionNode的订阅更新
  - 订阅 `ginkgo.live.control.commands` 接收TaskTimer的控制命令
  - 收到bar_snapshot命令后，从BarService获取当日K线并推送
  - 发布到 `ginkgo.live.market.data`
- **TaskTimer**: 定时任务调度器（运行在LiveCore）
  - 支持多个定时规则，每个规则使用独立的cron表达式配置
  - 定时发送控制命令到Kafka（update_selector、bar_snapshot、update_data）
  - 配置文件：`~/.ginkgo/task_timer.yml`
  - 使用APScheduler进行任务调度
- **Selector**: Portfolio的选股组件，通过pick()方法决定关注列表（非Strategy）
  - `pick(time)`: 执行选股逻辑，返回股票代码列表
  - `advance_time(time)`: 封装 pick() 和事件发布（回测模式使用）
- **EventInterestUpdate**: 关注列表更新事件，包含portfolio_id、codes、timestamp
- **PortfolioProcessor**: Portfolio运行控制器（运行在ExecutionNode）
  - 订阅 `ginkgo.live.control.commands` 接收控制命令
  - 实现 `_update_selectors()` 方法调用 selector.pick()
  - 负责创建 EventInterestUpdate 并发布到Kafka
- **LiveDataFeeder**: 实时数据源接口（现有实现: `ginkgo/trading/feeders/live_feeder.py`）
  - 使用现有 `ILiveDataFeeder` 接口，不重复开发
  - 支持WebSocket连接、自动重连、心跳检测、限流
  - 多市场适配器继承此基类：
    - `EastMoneyFeeder`: 东方财富WebSocket适配器（A股）
    - `FuShuFeeder`: FuShu HTTP轮询适配器（港股）
    - `AlpacaFeeder`: Alpaca WebSocket适配器（美股）
  - 配置：写死在代码中，敏感信息从 `~/.ginkgo/secure.yml` 读取
- **DataQualityMonitor**: 数据质量监控器，监控延迟、缺失、异常值等
- **PriceUpdateDTO**: 价格更新DTO（Kafka消息格式）
- **BarDTO**: K线数据DTO（Kafka消息格式）
- **InterestUpdateDTO**: 订阅更新DTO（Kafka消息格式）
- **ControlCommandDTO**: 控制命令DTO（Kafka消息格式）

## Success Criteria *(mandatory)*

### Measurable Outcomes

**性能与响应指标**:
- **SC-001**: 实时Tick数据端到端延迟 < 100ms（从数据源产生到ExecutionNode接收）
- **SC-002**: 定时任务触发精度误差 < 1秒
- **SC-003**: 数据源自动切换时间 < 5秒
- **SC-004**: 支持至少10个并发数据源订阅
- **SC-005**: Kafka数据发布吞吐量 > 10,000 messages/sec

**量化交易特有指标**:
- **SC-006**: 数据可用性 > 99.9%（月度统计）
- **SC-007**: 数据零丢失（Kafka发布失败必须重试成功）
- **SC-008**: 数据延迟告警准确率 > 95%（延迟超过阈值时触发告警）
- **SC-009**: 异常数据过滤率 > 99%（价格、成交量异常值被正确过滤）

**系统可靠性指标**:
- **SC-010**: 数据源连接断开后自动重连成功率 > 95%
- **SC-011**: DataManager进程平均无故障时间(MTBF) > 72小时
- **SC-012**: 代码测试覆盖率 > 85%（单元测试+集成测试）
- **SC-013**: 所有数据源适配器必须通过TDD测试流程

**业务与用户体验指标**:
- **SC-014**: 新数据源接入时间 < 2小时（实现标准接口并测试通过）
- **SC-015**: 配置修改生效时间 < 10秒（热更新订阅标的）
- **SC-016**: 数据质量问题告警响应时间 < 30秒（从检测到告警发布）

**实盘模式Selector触发机制指标**:
- **SC-017**: TaskTimer定时发送控制命令精度误差 < 5秒
- **SC-018**: ExecutionNode接收控制命令到执行selector.pick()响应时间 < 2秒
- **SC-019**: EventInterestUpdate发布到Kafka延迟 < 100ms
- **SC-020**: ExecutionNode的selector.pick()执行时间 < 1秒（避免阻塞）
- **SC-021**: 端到端延迟（TaskTimer发送命令 → EventInterestUpdate发布）< 5秒

## Assumptions

1. **现有架构依赖**: 基于已实现的实盘架构（007-live-trading-architecture）
2. **组件部署**: TaskTimer运行在LiveCore，Portfolio运行在ExecutionNode，两者通过Kafka通信
3. **Selector机制**: Portfolio已实现Selector组件，通过pick()方法决定关注列表（非Strategy）
4. **回测模式触发**: 回测模式下，Selector通过Portfolio._on_time_advance()调用advance_time()触发（每根K线，已实现）
5. **实盘模式触发**: 实盘模式下，通过Kafka控制命令解耦TaskTimer和ExecutionNode（需实现）
6. **TaskTimer职责**: TaskTimer只负责发送定时触发信号，不直接访问Portfolio或获取数据
7. **ExecutionNode职责**: ExecutionNode接收控制命令后，PortfolioProcessor调用selector.pick()并发布EventInterestUpdate
8. **LiveDataFeeder重用**: 使用现有 `ginkgo/trading/feeders/live_feeder.py` 实现，不重复开发
9. **多态模式**: LiveDataFeeder通过多态直接挂载，配置写死在代码中，敏感信息从secure.yml读取
10. **Kafka基础设施**: Kafka集群已部署并可正常使用，Topic已创建
11. **数据源API**: 假设主要数据源（Tushare、东方财富等）提供稳定的实时数据API或WebSocket接口
12. **网络环境**: 生产环境具有稳定的网络连接，网络延迟 < 50ms
13. **时间同步**: 所有服务器已配置NTP服务，时间误差 < 100ms
14. **TaskTimer配置**: TaskTimer配置文件路径为 `~/.ginkgo/task_timer.yml`
15. **数据源认证**: API Key等敏感信息存储在 `~/.ginkgo/secure.yml`
16. **去重策略**: 使用 `(symbol_code, timestamp)` 作为唯一标识进行数据去重
17. **Selector更新频率**: 实盘模式下，TaskTimer支持多个定时规则，每个规则通过cron表达式配置触发频率（每分钟、每小时、每天等）
18. **复用现有方法**: Portfolio复用on_price_update()处理实时Tick和盘后K线数据，无需新增特殊方法

### TaskTimer配置示例

**文件**: `~/.ginkgo/task_timer.yml`

```yaml
# TaskTimer定时任务配置
scheduled_tasks:
  # 规则1: 每小时更新Selector（用于选股）
  - name: "update_selector_hourly"
    description: "每小时更新选股结果"
    cron: "0 * * * *"  # 每小时整点
    command:
      type: "update_selector"
      payload: {}
    enabled: true

  # 规则2: 每天21:00执行K线分析
  - name: "bar_analysis_daily"
    description: "每天盘后K线分析"
    cron: "0 21 * * *"  # 每天21:00
    command:
      type: "bar_snapshot"
      payload:
        include_current_day: true
    enabled: true

  # 规则3: 每天19:00更新数据
  - name: "data_update_daily"
    description: "每天更新历史数据"
    cron: "0 19 * * *"  # 每天19:00
    command:
      type: "update_data"
      payload:
        sources: ["tushare", "eastmoney"]
    enabled: true

  # 规则4: 每分钟监控（可选，用于高频监控）
  - name: "monitor_every_minute"
    description: "每分钟检查系统状态"
    cron: "* * * * *"  # 每分钟
    command:
      type: "health_check"
      payload: {}
    enabled: false  # 默认禁用

# Kafka配置
kafka:
  bootstrap_servers: "localhost:9092"
  topic: "ginkgo.live.control.commands"
  producer_config:
    max_retries: 3
    acks: "all"

# APScheduler配置
scheduler:
  timezone: "Asia/Shanghai"
  coalesce: true  # 合并错过的任务
  max_instances: 1  # 每个任务最多同时运行1个实例
```

## Out of Scope

1. **数据存储**: DataManager不负责数据持久化，仅负责接收和发布到Kafka（数据持久化由独立的数据服务处理）
2. **策略计算**: DataManager不包含任何交易策略逻辑，仅负责数据分发
3. **Selector实现**: 本功能不涉及Selector的具体选股逻辑实现（如PE筛选、RSI指标等），仅负责触发机制
4. **Portfolio修改**: Portfolio复用现有on_price_update()方法处理实时Tick和盘后K线，无需新增特殊方法
5. **PortfolioProcessor修改**: PortfolioProcessor的基础实现已在007架构完成，本功能无需修改
6. **历史数据回测**: 本功能专注于实盘数据，不涉及历史数据回测场景
7. **数据源开发**: 不负责开发新的数据源API（仅适配现有数据源）
8. **复杂事件处理**: 不支持复杂事件处理(CEP)引擎（如窗口计算、模式匹配等）
9. **数据加密**: 不在DataManager层进行数据加密（假设使用TLS等传输层安全）
10. **数据交易**: 不涉及付费数据源的计费和授权管理
11. **跨市场数据**: MVP阶段仅支持单一市场（如A股），跨市场（港股、美股）支持在后续阶段实现
