# 实盘与历史Feeder整合架构分析

**Feature**: 008-live-data-module
**Date**: 2026-01-11
**Purpose**: 分析现有Feeder架构，设计实盘与历史数据源同时挂载的方案

---

## 一、现有架构发现

### 1.1 已实现的Feeder接口层次

```
IDataFeeder (基础接口)
    ├── initialize()
    ├── start()
    ├── stop()
    ├── get_status()
    ├── set_event_publisher()
    ├── set_time_provider()
    └── validate_time_access()

    ↓ 继承

IBacktestDataFeeder (回测接口)
    ├── advance_time() - 时间推进
    ├── get_historical_data() - 历史数据查询
    └── get_data_range() - 数据范围

    ↓ 实现
    BacktestFeeder (回测实现)

ILiveDataFeeder (实盘接口)
    ├── subscribe_symbols() - 订阅股票
    ├── unsubscribe_symbols() - 取消订阅
    ├── start_subscription() - 开始订阅
    ├── stop_subscription() - 停止订阅
    ├── get_connection_info() - 连接信息
    ├── reconnect() - 重连
    ├── set_rate_limiter() - 限流
    └── get_subscribed_symbols() - 已订阅列表

    ↓ 实现
    LiveDataFeeder (实盘实现)
```

### 1.2 关键发现

✅ **好消息**: Ginkgo已经有完善的接口设计！

- `ginkgo/trading/feeders/interfaces.py` - 统一接口定义
- `ginkgo/trading/feeders/backtest_feeder.py` - 回测实现
- `ginkgo/trading/feeders/live_feeder.py` - 实盘实现

⚠️ **008设计问题**: 我们在008中重复设计了LiveDataFeeder！

---

## 二、当前数据获取模式

### 2.1 回测模式

```
EngineHistoric
    ↓ 使用
BacktestFeeder
    ↓ 查询数据库
BarService.get_bars()
    ↓ 从ClickHouse读取
历史K线数据
    ↓ 推送事件
EventBarUpdate → Portfolio
```

### 2.2 实盘模式（007架构）

```
ExecutionNode
    ↓ 使用
LiveDataFeeder (已有实现！)
    ↓ WebSocket连接
外部数据源
    ↓ 接收Tick
EventPriceUpdate → Portfolio
```

### 2.3 实盘模式（008新增架构）

```
LiveCore
    ↓ 使用
DataManager (008新增)
    ├── LiveDataFeeder (新设计，与已有实现重复！)
    └── Queue消费者
```

**问题**: 008设计的LiveDataFeeder与现有的`ginkgo/trading/feeders/live_feeder.py`功能重叠！

---

## 三、同时挂载两种Feeder的架构设计

### 3.1 需求分析

**实盘时为什么需要历史数据？**

1. **策略初始化**: 需要加载历史K线计算指标（如MA、RSI）
2. **回测验证**: 实盘前回测验证策略参数
3. **数据补充**: 实时数据丢失时从历史数据补充
4. **盘后分析**: 收盘后使用历史K线进行盘后分析

**场景示例**:

```python
# 实盘策略启动时
class MyStrategy(BaseStrategy):
    def __init__(self):
        # 需要加载历史60日K线计算MA60
        historical_bars = self.backtest_feeder.get_historical_data(
            symbols=["000001.SZ"],
            start_time=now() - 60days,
            end_time=now()
        )
        self.ma60 = calculate_ma(historical_bars)

    def on_price_update(self, event):
        # 实时Tick更新
        current_price = event.price

        # 结合实时和历史数据
        if current_price > self.ma60:
            self.buy()
```

### 3.2 统一数据管理器设计

```python
class UnifiedDataManager:
    """
    统一数据管理器

    职责：
    1. 管理BacktestFeeder和LiveDataFeeder
    2. 根据查询类型自动路由到合适的Feeder
    3. 支持实盘模式下查询历史数据
    """

    def __init__(
        self,
        backtest_feeder: IBacktestDataFeeder,
        live_feeder: ILiveDataFeeder = None
    ):
        self.backtest_feeder = backtest_feeder
        self.live_feeder = live_feeder

        # 数据获取策略
        self.data_source_strategy = self._auto_detect_strategy()

    def _auto_detect_strategy(self) -> str:
        """
        自动检测数据获取策略

        Returns:
            "backtest_only": 仅使用历史数据（回测模式）
            "live_only": 仅使用实时数据（纯实盘模式）
            "hybrid": 混合模式（实盘+历史数据）
        """
        if self.live_feeder is None:
            return "backtest_only"
        elif self.backtest_feeder is None:
            return "live_only"
        else:
            return "hybrid"

    def get_bars(
        self,
        symbols: List[str],
        start_time: datetime,
        end_time: datetime,
        prefer_live: bool = False
    ) -> Dict[str, List[Bar]]:
        """
        获取K线数据（智能路由）

        Args:
            symbols: 股票代码
            start_time: 开始时间
            end_time: 结束时间
            prefer_live: 优先使用实时数据（仅实盘模式）

        Returns:
            K线数据

        路由策略：
        - 如果end_time < now() → 使用BacktestFeeder（历史数据）
        - 如果prefer_live=True → 使用LiveDataFeeder（实时数据）
        - 如果数据在两个Feeder都存在 → 合并返回
        """
        now = datetime.now()

        # 判断数据类型
        if end_time < now:
            # 历史数据 → BacktestFeeder
            return self.backtest_feeder.get_historical_data(
                symbols, start_time, end_time
            )
        elif prefer_live and self.live_feeder:
            # 实时数据 → LiveDataFeeder
            return self._get_live_bars(symbols)
        else:
            # 混合数据
            return self._merge_bars(symbols, start_time, end_time)

    def _get_live_bars(self, symbols: List[str]) -> Dict[str, List[Bar]]:
        """
        从LiveDataFeeder获取当前实时K线

        注意：LiveDataFeeder主要提供Tick，需要内部聚合成K线
        """
        # 订阅实时数据
        self.live_feeder.subscribe_symbols(symbols, data_types=["bar"])

        # 等待数据到达...
        # （需要实现K线聚合逻辑）

    def _merge_bars(
        self,
        symbols: List[str],
        start_time: datetime,
        end_time: datetime
    ) -> Dict[str, List[Bar]]:
        """
        合并历史和实时数据

        策略：
        1. 历史部分：start_time → now() - 1min （BacktestFeeder）
        2. 实时部分：now() - 1min → end_time （LiveDataFeeder）
        3. 合并去重
        """
        now = datetime.now()
        split_time = now - timedelta(minutes=1)

        # 历史数据
        historical = self.backtest_feeder.get_historical_data(
            symbols, start_time, split_time
        )

        # 实时数据
        live = self._get_live_bars(symbols)

        # 合并
        return self._merge_data(historical, live)
```

### 3.3 Portfolio集成

```python
class Portfolio:
    """
    Portfolio（统一数据模式）
    """

    def __init__(
        self,
        data_manager: UnifiedDataManager,
        mode: str = "live"  # "backtest" or "live"
    ):
        self.data_manager = data_manager
        self.mode = mode

    def initialize_strategy(self, strategy: BaseStrategy):
        """
        策略初始化

        实盘模式下：
        1. 使用BacktestFeeder加载历史数据
        2. 计算技术指标
        3. 策略准备就绪
        """
        if self.mode == "live":
            # 加载历史数据用于初始化
            symbols = strategy.get_symbols()
            bars = self.data_manager.get_bars(
                symbols=symbols,
                start_time=datetime.now() - timedelta(days=60),
                end_time=datetime.now()
            )

            # 策略初始化
            strategy.on_initialize(bars)

    def on_price_update(self, event: EventPriceUpdate):
        """
        实时价格更新（实盘模式）
        """
        # 更新当前价格
        current_price = event.price

        # 策略计算
        signals = self.strategy.cal(current_price)
```

---

## 四、008架构调整建议

### 4.1 重用现有LiveDataFeeder

**当前问题**: 008设计了新的LiveDataFeeder

**建议方案**:

```python
# 008 DataManager使用现有LiveDataFeeder
from ginkgo.trading.feeders.live_feeder import LiveDataFeeder

class DataManager(Thread):
    """
    DataManager（使用现有LiveDataFeeder）
    """

    def __init__(self):
        # 使用现有的LiveDataFeeder
        self.live_feeder = LiveDataFeeder(
            host=config.websocket_host,
            port=config.websocket_port,
            api_key=config.api_key
        )

        # 创建Kafka发布器
        self.kafka_producer = GinkgoProducer()

        # 设置事件发布器
        self.live_feeder.set_event_publisher(self._publish_to_kafka)

    def _publish_to_kafka(self, event: EventBase):
        """
        将事件发布到Kafka
        """
        if isinstance(event, EventPriceUpdate):
            dto = PriceUpdateDTO.from_event(event)
            self.kafka_producer.send(
                topic=KafkaTopics.MARKET_DATA,
                message=dto.model_dump_json()
            )
```

### 4.2 使用UnifiedDataManager

```python
class LiveCore:
    """
    LiveCore（统一数据管理）
    """

    def __init__(self, mode: str = "live"):
        # 创建历史数据Feeder
        self.backtest_feeder = BacktestFeeder()

        # 创建实时数据Feeder（如果需要）
        if mode == "live":
            self.live_feeder = LiveDataFeeder(
                host=config.websocket_host,
                port=config.websocket_port
            )
        else:
            self.live_feeder = None

        # 创建统一数据管理器
        self.data_manager = UnifiedDataManager(
            backtest_feeder=self.backtest_feeder,
            live_feeder=self.live_feeder
        )
```

---

## 五、实现方案对比

### 5.1 方案A: 分别挂载（推荐）

**架构**:
```python
portfolio = Portfolio(
    backtest_feeder=BacktestFeeder(),  # 历史数据
    live_feeder=LiveDataFeeder()       # 实时数据
)

# 策略中根据情况选择
class MyStrategy(BaseStrategy):
    def initialize(self):
        # 使用历史数据初始化
        bars = self.backtest_feeder.get_historical_data(...)

    def on_tick(self, tick):
        # 使用实时数据
        pass
```

**优点**:
- ✅ 清晰分离历史和实时数据
- ✅ 易于理解和维护
- ✅ 符合现有接口设计

**缺点**:
- ⚠️ 策略需要知道使用哪个Feeder

### 5.2 方案B: 统一管理器（高级）

**架构**:
```python
portfolio = Portfolio(
    data_manager=UnifiedDataManager(
        backtest_feeder=BacktestFeeder(),
        live_feeder=LiveDataFeeder()
    )
)

# 策略中无需关心数据来源
class MyStrategy(BaseStrategy):
    def get_bars(self, symbols, start, end):
        # 自动路由到合适的Feeder
        return self.data_manager.get_bars(symbols, start, end)
```

**优点**:
- ✅ 策略无需关心数据来源
- ✅ 自动路由，简化使用
- ✅ 支持数据合并

**缺点**:
- ⚠️ 增加抽象层复杂度
- ⚠️ 可能影响性能（路由开销）

---

## 六、推荐实施方案

### 6.1 短期方案（008 Phase 2）

1. **重用现有LiveDataFeeder**
   - 删除008中新设计的LiveDataFeeder
   - 使用`ginkgo/trading/feeders/live_feeder.py`
   - DataManager作为中间层：LiveDataFeeder → Kafka

2. **Portfolio同时挂载两种Feeder**
   ```python
   portfolio = Portfolio()
   portfolio.bind_feeder("backtest", BacktestFeeder())
   portfolio.bind_feeder("live", LiveDataFeeder())
   ```

3. **策略根据场景选择**
   ```python
   class MyStrategy(BaseStrategy):
       def initialize(self):
           # 使用历史数据
           bars = self.portfolio.get_feeder("backtest").get_historical_data(...)

       def on_tick(self, tick):
           # 使用实时数据
           pass
   ```

### 6.2 长期方案（008 Phase 3+）

1. **实现UnifiedDataManager**
   - 智能路由数据请求
   - 自动合并历史和实时数据
   - 对策略透明

2. **扩展接口**
   - 添加`IDataProvider`接口
   - 支持多种数据源组合
   - 提供缓存机制

3. **优化性能**
   - 数据预加载
   - 智能缓存
   - 异步查询

---

## 七、结论

### 7.1 回答用户问题

> 实盘datafeeder与历史datafeeder现在可以同时挂载并根据情况调用么？

**答案**: ✅ **可以，但需要整合设计**

**当前状态**:
- ✅ 接口已经统一（IDataFeeder, IBacktestDataFeeder, ILiveDataFeeder）
- ✅ BacktestFeeder和LiveDataFeeder已经实现
- ⚠️ 008设计的LiveDataFeeder与现有实现重复
- ⚠️ 缺少统一管理器来协调两种Feeder

**实施建议**:
1. **立即**: 重用现有的`ginkgo/trading/feeders/live_feeder.py`
2. **短期**: Portfolio同时挂载两种Feeder，策略根据场景选择
3. **长期**: 实现UnifiedDataManager，提供透明路由

### 7.2 架构优先级

| 优先级 | 任务 | 说明 |
|--------|------|------|
| 🔴 P0 | 重用现有LiveDataFeeder | 避免重复实现 |
| 🟡 P1 | Portfolio支持多Feeder | 同时挂载历史和实盘Feeder |
| 🟢 P2 | 实现UnifiedDataManager | 智能路由和数据合并 |
| 🔵 P3 | 性能优化和缓存 | 提高数据访问效率 |

---

**分析完成时间**: 2026-01-11
**下一步**: 调整008架构，重用现有LiveDataFeeder实现
