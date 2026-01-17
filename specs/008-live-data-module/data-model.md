# 数据模型设计文档

**Feature**: 008-live-data-module
**Date**: 2026-01-09
**Status**: Phase 1 设计

## 一、核心数据结构

### 1.1 DataManager核心数据结构

DataManager是实时数据管理器，负责维护订阅标的、管理LiveDataFeeder实例、通过Queue消费线程发布数据到Kafka。

```python
class DataManager(threading.Thread):
    """
    实时数据管理器

    职责：
    1. 订阅Kafka Topic "ginkgo.live.interest.updates"接收订阅更新
    2. 维护all_symbols内存集合（所有订阅标的）
    3. 按市场分发订阅到LiveDataFeeder实例
    4. 启动Queue消费者线程处理Tick数据
    """

    # 共享状态（线程安全）
    all_symbols: Set[str]              # 所有订阅标的
    _lock: threading.Lock               # 保护all_symbols的锁

    # Kafka Consumer
    consumer: GinkgoConsumer            # Kafka消费者（独立group_id）

    # LiveDataFeeder实例（硬编码）
    feeders: Dict[str, LiveDataFeeder]  # 按市场划分的Feeder实例
    queues: Dict[str, Queue]            # 每个Feeder对应的Queue
    queue_consumers: List[Thread]       # Queue消费者线程列表

    # 控制标志
    _stop_event: threading.Event        # 停止信号
```

**数据流**:
```
Kafka(interest.updates) → DataManager.all_symbols →
  按市场分发 → LiveDataFeeder.set_symbols() →
  LiveDataFeeder → Queue → Queue消费者 → PriceUpdateDTO →
  Kafka(market.data)
```

**市场映射配置**:
```python
MARKET_MAPPING = {
    "cn": [".SH", ".SZ"],  # A股市场
    "hk": [".HK"],          # 港股市场
    "us": []                # 美股市场（无后缀）
}
```

### 1.2 LiveDataFeeder状态机

LiveDataFeeder是数据源适配器基类，定义了统一的连接状态转换。

```python
class LiveDataFeederState(Enum):
    """Feeder连接状态"""
    DISCONNECTED = 0    # 未连接
    CONNECTING = 1      # 连接中
    CONNECTED = 2       # 已连接
    RECONNECTING = 3    # 重连中
    STOPPED = 4         # 已停止
```

**状态转换图**:
```
DISCONNECTED → CONNECTING → CONNECTED
     ↑              ↓              ↓
     └─────────────┴──────────────┘
           (连接失败/断开)

CONNECTED → RECONNECTING → CONNECTED
     ↑                           ↓
     └───────────────────────────┘
           (重连成功)

任何状态 → STOPPED (调用stop())
```

**状态转换触发条件**:
1. **DISCONNECTED → CONNECTING**: 调用`start()`
2. **CONNECTING → CONNECTED**: WebSocket/HTTP连接成功
3. **CONNECTING → RECONNECTING**: 连接失败，开始重连
4. **CONNECTED → RECONNECTING**: 检测到连接断开（心跳超时、网络错误）
5. **RECONNECTING → CONNECTED**: 重连成功
6. **任何状态 → STOPPED**: 调用`stop()`

### 1.3 Queue数据流模型

Queue生产者-消费者模式，解耦数据接收和Kafka发布。

```python
class TickConsumer(threading.Thread):
    """
    Tick数据消费者（从Queue消费并发布到Kafka）

    数据流：
    LiveDataFeeder → Queue → TickConsumer → PriceUpdateDTO → Kafka

    Queue配置：
    - maxsize: 10000（有界队列）
    - 满时策略: 丢弃当前数据（warn日志）

    线程安全：
    - Queue.put() 非阻塞（设置timeout）
    - Queue.get() 阻塞等待（设置timeout检查停止标志）
    """

    # Queue配置
    queue: Queue                    # Tick数据队列
    market: str                     # 市场标识（cn/hk/us）

    # Kafka Producer
    producer: GinkgoProducer        # Kafka生产者

    # 控制标志
    _stop_event: threading.Event    # 停止信号
```

**Queue数据流示意图**:
```
LiveDataFeeder (生产者线程)
    ↓
  Queue.put(tick)
    ↓
Queue (有界队列, maxsize=10000)
    ↓
  Queue.get(tick) [阻塞等待]
    ↓
TickConsumer (消费者线程)
    ↓
PriceUpdateDTO.from_tick(tick)
    ↓
Kafka Producer.send("ginkgo.live.market.data", dto)
```

**满时处理策略**:
```python
def put_tick_nonblocking(self, tick: Tick):
    """非阻塞put，队列满时丢弃当前数据"""
    try:
        self.queue.put(tick, block=False)
    except queue.Full:
        logger.warning(f"Queue full (maxsize=10000), dropping tick for {tick.code}")
        # 丢弃当前数据，不阻塞Feeder
```

### 1.4 TaskTimer任务模型

TaskTimer是定时任务调度器，使用APScheduler执行硬编码任务。

```python
class TaskTimer(threading.Thread):
    """
    定时任务调度器

    职责：
    1. 订阅Kafka Topic "ginkgo.live.interest.updates"接收订阅更新
    2. 维护all_symbols内存集合
    3. 使用APScheduler执行定时任务

    任务类型：
    - 数据更新任务（19:00触发）
    - K线分析任务（21:00触发）
    """

    # 共享状态（线程安全）
    all_symbols: Set[str]              # 所有订阅标的
    _lock: threading.Lock               # 保护all_symbols的锁

    # Kafka Consumer
    consumer: GinkgoConsumer            # Kafka消费者（独立group_id）

    # APScheduler
    scheduler: BackgroundScheduler      # 后台调度器
    jobs: Dict[str, Job]                # 定时任务字典

    # 控制标志
    _stop_event: threading.Event        # 停止信号
```

**任务定义**:

| 任务ID | Cron表达式 | 触发时间 | 功能描述 |
|--------|-----------|---------|---------|
| `data_update` | `0 19 * * *` | 每天19:00 | 触发外部数据源更新数据（如调用数据源API刷新日K线） |
| `bar_analysis` | `0 21 * * *` | 每天21:00 | 发送当日K线数据到Kafka，触发策略分析 |

**任务执行流程**:
```
APScheduler触发 → 任务函数 →
  访问all_symbols（加锁） →
  调用BarService.get_daily_bars(symbols, date) →
  转换为BarDTO →
  发布到Kafka("ginkgo.live.market.data")
```

---

## 二、DTO数据传输对象

### 2.1 InterestUpdateDTO - 订阅更新消息

**用途**: Portfolio通过Kafka发送订阅标的更新

```python
from pydantic import BaseModel, Field
from typing import List
from datetime import datetime

class InterestUpdateDTO(BaseModel):
    """
    订阅更新DTO

    用途：Portfolio通过Kafka发送订阅标的更新到DataManager和TaskTimer
    Topic: ginkgo.live.interest.updates
    """

    portfolio_id: str = Field(..., description="Portfolio ID")
    node_id: str = Field(..., description="ExecutionNode ID")
    symbols: List[str] = Field(..., description="订阅标的列表（如['000001.SZ', '600000.SH']）")
    timestamp: datetime = Field(default_factory=datetime.now, description="更新时间戳")

    class Config:
        json_schema_extra = {
            "example": {
                "portfolio_id": "portfolio_001",
                "node_id": "node_001",
                "symbols": ["000001.SZ", "600000.SH", "00700.HK"],
                "timestamp": "2026-01-09T19:00:00"
            }
        }
```

### 2.2 PriceUpdateDTO - 实时Tick数据

**用途**: DataManager发布实时Tick数据到Kafka

```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class PriceUpdateDTO(BaseModel):
    """
    实时Tick价格更新DTO（完整版）

    用途：DataManager将Tick数据发布到Kafka，触发ExecutionNode策略计算
    Topic: ginkgo.live.market.data
    """

    # 基础字段
    symbol: str = Field(..., description="标的代码（如'000001.SZ'）")
    price: float = Field(..., description="最新价格")
    volume: int = Field(..., description="成交量")
    amount: float = Field(..., description="成交额")

    # 五档行情
    bid_price: Optional[float] = Field(None, description="买一价")
    ask_price: Optional[float] = Field(None, description="卖一价")
    bid_volume: Optional[int] = Field(None, description="买一量")
    ask_volume: Optional[int] = Field(None, description="卖一量")

    # 当日行情
    open_price: Optional[float] = Field(None, description="开盘价")
    high_price: Optional[float] = Field(None, description="最高价")
    low_price: Optional[float] = Field(None, description="最低价")

    # 时间戳
    timestamp: datetime = Field(..., description="Tick时间戳")

    class Config:
        json_schema_extra = {
            "example": {
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
        }

    @classmethod
    def from_tick(cls, tick: Tick) -> "PriceUpdateDTO":
        """
        从Tick对象转换为PriceUpdateDTO

        Args:
            tick: Tick对象（来自LiveDataFeeder）

        Returns:
            PriceUpdateDTO实例
        """
        return cls(
            symbol=tick.code,
            price=tick.price,
            volume=tick.volume,
            amount=getattr(tick, 'amount', 0.0),
            bid_price=getattr(tick, 'bid_price', None),
            ask_price=getattr(tick, 'ask_price', None),
            bid_volume=getattr(tick, 'bid_volume', None),
            ask_volume=getattr(tick, 'ask_volume', None),
            open_price=getattr(tick, 'open_price', None),
            high_price=getattr(tick, 'high_price', None),
            low_price=getattr(tick, 'low_price', None),
            timestamp=tick.timestamp
        )
```

### 2.3 BarDTO - K线数据

**用途**: TaskTimer发布K线数据到Kafka

```python
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class BarDTO(BaseModel):
    """
    K线数据DTO（完整版）

    用途：TaskTimer将K线数据发布到Kafka，触发策略分析
    Topic: ginkgo.live.market.data
    """

    # 基础字段
    symbol: str = Field(..., description="标的代码（如'000001.SZ'）")
    period: str = Field(..., description="周期（如'day', '1min', '5min'）")

    # OHLCV
    open: float = Field(..., description="开盘价")
    high: float = Field(..., description="最高价")
    low: float = Field(..., description="最低价")
    close: float = Field(..., description="收盘价")
    volume: int = Field(..., description="成交量")
    amount: float = Field(..., description="成交额")

    # 扩展字段
    turnover: Optional[float] = Field(None, description="换手率")
    change: Optional[float] = Field(None, description="涨跌额")
    change_pct: Optional[float] = Field(None, description="涨跌幅(%)")

    # 时间戳
    timestamp: datetime = Field(..., description="K线时间戳")

    class Config:
        json_schema_extra = {
            "example": {
                "symbol": "000001.SZ",
                "period": "day",
                "open": 10.30,
                "high": 10.60,
                "low": 10.25,
                "close": 10.50,
                "volume": 1000000,
                "amount": 10500000.0,
                "turnover": 0.5,
                "change": 0.20,
                "change_pct": 1.94,
                "timestamp": "2026-01-09T00:00:00"
            }
        }

    @classmethod
    def from_bar(cls, bar: Bar) -> "BarDTO":
        """
        从Bar对象转换为BarDTO

        Args:
            bar: Bar对象（来自BarService）

        Returns:
            BarDTO实例
        """
        return cls(
            symbol=bar.code,
            period=bar.period,
            open=bar.open_price,
            high=bar.high_price,
            low=bar.low_price,
            close=bar.close_price,
            volume=bar.volume,
            amount=bar.amount,
            turnover=getattr(bar, 'turnover', None),
            change=getattr(bar, 'change', None),
            change_pct=getattr(bar, 'change_pct', None),
            timestamp=bar.timestamp
        )
```

---

## 三、数据转换关系

### 3.1 LiveDataFeeder数据转换

**数据源格式 → Tick对象 → PriceUpdateDTO → Kafka**

```python
# 示例：EastMoneyFeeder数据转换流程

# 1. 接收WebSocket消息（EastMoney格式）
ws_message = {
    "code": "000001",
    "market": 0,
    "price": 10.50,
    "volume": 10000,
    "amount": 105000.0,
    "timestamp": 1704789000
}

# 2. 转换为Tick对象
tick = Tick(
    code="000001.SZ",  # 添加市场后缀
    price=10.50,
    volume=10000,
    amount=105000.0,
    timestamp=datetime.fromtimestamp(1704789000)
)

# 3. 发布到Queue
self.queue.put(tick)

# 4. Queue消费者转换为PriceUpdateDTO
dto = PriceUpdateDTO.from_tick(tick)

# 5. 发布到Kafka
kafka_producer.send("ginkgo.live.market.data", dto.model_dump_json())
```

### 3.2 BarService数据转换

**ClickHouse → Bar对象 → BarDTO → Kafka**

```python
# 示例：TaskTimer K线数据转换流程

# 1. 从ClickHouse查询Bar对象（通过BarService）
bars = bar_service.get_daily_bars(
    symbols=["000001.SZ", "600000.SH"],
    date=date(2026, 1, 9)
)

# 2. 转换为BarDTO列表
dtos = [BarDTO.from_bar(bar) for bar in bars]

# 3. 发布到Kafka
kafka_producer.send("ginkgo.live.market.data", [dto.model_dump_json() for dto in dtos])
```

---

## 四、线程安全设计

### 4.1 DataManager线程安全

**共享状态保护**:
```python
class DataManager(threading.Thread):
    def __init__(self):
        super().__init__()
        self.all_symbols = set()
        self._lock = threading.Lock()

    def _handle_interest_update(self, message):
        """处理Kafka消息（线程安全）"""
        symbols = set(message['symbols'])

        # 加锁更新all_symbols
        with self._lock:
            self.all_symbols.update(symbols)
            symbols_copy = set(self.all_symbols)  # 复制一份，避免长时间持锁

        # 释放锁后进行分发操作
        for market, feeder in self.feeders.items():
            market_symbols = self._filter_by_market(symbols_copy, market)
            if market_symbols:
                feeder.set_symbols(market_symbols)
```

**锁使用原则**:
1. **最小持锁时间**: 只在访问共享状态时加锁，避免在锁内进行耗时操作
2. **避免嵌套锁**: DataManager不调用其他需要加锁的方法，避免死锁
3. **复制共享状态**: 锁内复制共享状态，锁外使用副本

### 4.2 TaskTimer线程安全

**任务函数线程安全**:
```python
class TaskTimer(threading.Thread):
    def _data_update_job(self):
        """定时任务（在ThreadPoolExecutor中执行）"""
        # 加锁访问all_symbols
        with self._lock:
            symbols = list(self.all_symbols)

        # 释放锁后执行耗时操作
        bars = self.bar_service.get_daily_bars(symbols, date.today())
        self.kafka_producer.send("ginkgo.live.market.data", bars)
```

**APScheduler线程安全**:
- **BackgroundScheduler**内部使用threading.Lock保护共享状态
- **ThreadPoolExecutor**确保任务在独立线程池执行
- **max_instances=1**防止同一任务并发执行

### 4.3 Queue线程安全

**Queue内置线程安全**:
```python
from queue import Queue

# Queue内部使用threading.Lock和threading.Condition
queue = Queue(maxsize=10000)

# 生产者（LiveDataFeeder）
queue.put(tick)  # 自动加锁

# 消费者（TickConsumer）
tick = queue.get()  # 自动加锁
```

**非阻塞put**:
```python
def put_tick_nonblocking(self, tick):
    """非阻塞put，避免阻塞Feeder线程"""
    try:
        self.queue.put(tick, block=False)
    except queue.Full:
        logger.warning(f"Queue full, dropping tick for {tick.code}")
```

---

## 五、性能优化设计

### 5.1 批量发布优化

**Kafka批量发布**:
```python
class TickConsumer(threading.Thread):
    def _publish_batch(self, dtos: List[PriceUpdateDTO]):
        """批量发布DTO到Kafka（提高吞吐量）"""
        batch_size = 100
        for i in range(0, len(dtos), batch_size):
            batch = dtos[i:i + batch_size]
            self.kafka_producer.send(
                topic="ginkgo.live.market.data",
                messages=[dto.model_dump_json() for dto in batch]
            )
```

### 5.2 内存优化

**Queue大小控制**:
```python
# 有界队列，防止内存无限增长
queue = Queue(maxsize=10000)

# 队列满时丢弃策略（保证<100ms延迟）
if queue.full():
    logger.warning("Queue full, dropping oldest data")
    queue.get_nowait()  # 丢弃最旧数据（可选策略）
```

**符号集优化**:
```python
# 使用Set存储符号（O(1)查找）
all_symbols: Set[str] = set()

# 定期清理无效符号（避免内存泄漏）
def _cleanup_invalid_symbols(self):
    """清理无效符号（定期调用）"""
    valid_symbols = set()
    for symbol in self.all_symbols:
        if self._is_valid_symbol(symbol):
            valid_symbols.add(symbol)

    with self._lock:
        self.all_symbols = valid_symbols
```

### 5.3 连接复用

**WebSocket连接复用**:
```python
class EastMoneyFeeder:
    """每个Feeder维护一个长连接"""
    def __init__(self):
        self.websocket = None  # 复用同一连接

    async def _connect_and_receive(self):
        """建立连接后持续接收消息"""
        async with websockets.connect(uri) as ws:
            self.websocket = ws
            while not self._stop_event.is_set():
                message = await ws.recv()
                await self._handle_message(message)
```

---

## 六、错误处理设计

### 6.1 WebSocket断线重连

**指数退避重连**:
```python
async def _auto_reconnect(self, max_attempts=5, base_delay=2):
    """指数退避重连"""
    for attempt in range(1, max_attempts + 1):
        try:
            await self._connect_and_receive()
            logger.info("Reconnected successfully")
            return

        except Exception as e:
            delay = min(base_delay ** attempt, 60)  # 最大60秒
            logger.warning(f"Reconnect attempt {attempt} failed, retry in {delay}s")
            await asyncio.sleep(delay)

    logger.error("Max reconnect attempts reached")
    notify("WebSocket连接失败，已达到最大重试次数", level="ERROR")
```

### 6.2 Kafka发布失败重试

**Kafka发布重试**:
```python
class TickConsumer:
    def _publish_to_kafka(self, dto: PriceUpdateDTO, max_retry=3):
        """发布到Kafka（带重试）"""
        for attempt in range(1, max_retry + 1):
            try:
                self.kafka_producer.send(
                    topic="ginkgo.live.market.data",
                    message=dto.model_dump_json()
                )
                return  # 成功，退出重试

            except Exception as e:
                logger.warning(f"Kafka publish attempt {attempt} failed: {e}")
                if attempt < max_retry:
                    time.sleep(2 ** attempt)  # 指数退避

        # 所有重试失败，记录错误
        logger.error(f"Failed to publish to Kafka after {max_retry} attempts")
        notify("Kafka发布失败，可能存在数据丢失", level="ERROR")
```

### 6.3 任务崩溃隔离

**任务装饰器**:
```python
def safe_job_wrapper(func):
    """任务装饰器：隔离任务崩溃"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Job {func.__name__} failed: {e}", exc_info=True)
            notify(f"定时任务 {func.__name__} 执行失败", level="ERROR")
            return None
    return wrapper

@safe_job_wrapper
def data_update_task():
    """带崩溃隔离的数据更新任务"""
    # 任务逻辑
    pass
```

---

## 七、监控与告警设计

### 7.1 数据质量监控

**延迟监控**:
```python
class DataQualityMonitor:
    def __init__(self):
        self.latency_threshold = 1.0  # 1秒阈值

    def check_latency(self, tick: Tick):
        """检查数据延迟"""
        latency = (datetime.now() - tick.timestamp).total_seconds()
        if latency > self.latency_threshold:
            logger.warning(f"Data latency {latency}s exceeds threshold")
            notify(f"数据延迟 {latency}s 超过阈值", level="WARNING")
```

**缺失检测**:
```python
class DataQualityMonitor:
    def check_missing(self, symbol: str, expected_time: datetime):
        """检查数据缺失"""
        if not self._has_data(symbol, expected_time):
            logger.warning(f"Missing data for {symbol} at {expected_time}")
            notify(f"{symbol} 数据缺失 {expected_time}", level="WARNING")
```

**异常值过滤**:
```python
class DataQualityMonitor:
    def filter_abnormal(self, tick: Tick) -> bool:
        """过滤异常数据"""
        # 价格为零或负数
        if tick.price <= 0:
            logger.warning(f"Invalid price {tick.price} for {tick.code}")
            return False

        # 成交量为负数
        if tick.volume < 0:
            logger.warning(f"Invalid volume {tick.volume} for {tick.code}")
            return False

        # 涨跌幅超过10%（A股限制）
        change_pct = self._calculate_change_pct(tick)
        if abs(change_pct) > 10:
            logger.warning(f"Abnormal change {change_pct}% for {tick.code}")
            return False

        return True
```

---

**Phase 1 设计完成时间:** 2026-01-09
**下一步:** 创建contracts/目录和API契约文档
