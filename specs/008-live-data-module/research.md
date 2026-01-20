# 实盘数据模块技术选型研究报告

**Feature**: 008-live-data-module
**Date**: 2026-01-09
**Status**: Phase 0 完成

## 一、当前项目依赖分析

### 1.1 核心依赖概况

**已存在的相关依赖:**
- **`websockets==15.0.1`** - 已安装，异步WebSocket库
- **`websocket-client==1.8.0`** - 已安装，同步WebSocket库
- **`aiohttp==3.12.15`** - 已安装，异步HTTP客户端
- **`kafka-python-ng==2.2.3`** - 已安装，Kafka Python客户端（新版）
- **`redis==6.3.0`** - 已安装，Redis客户端
- **`pytz==2025.2`** - 已安装，时区处理

**缺失的关键依赖:**
- **`APScheduler`** - 未安装，需要添加用于定时任务调度

### 1.2 项目架构特点

**线程模型:**
- 基于多线程的LiveCore容器
- Scheduler使用`threading.Thread`实现单线程调度循环
- Kafka Consumer和Producer在独立线程中运行

**异步支持:**
- 现有`LiveDataFeeder`使用`websockets`和`asyncio`
- 使用`asyncio.run_coroutine_threadsafe`进行线程和事件循环桥接

**Kafka使用模式:**
- 使用`kafka-python-ng`（kafka-python的维护分支）
- Producer使用同步发送模式，带`future.get(timeout=10)`确认
- Consumer使用`max_poll_records=1`配置，逐条处理消息

---

## 二、APScheduler集成研究

### 2.1 多线程安全性分析

**结论: ✅ APScheduler在多线程环境中安全**

**关键配置:**
```python
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.executors.pool import ThreadPoolExecutor

# 线程安全配置
executors = {
    'default': ThreadPoolExecutor(max_workers=5)  # 限制并发任务数
}
job_defaults = {
    'coalesce': True,      # 合并错过的任务执行
    'max_instances': 1,    # 同一任务最多1个实例运行
    'misfire_grace_time': 300  # 错过任务后的宽限时间（秒）
}

scheduler = BackgroundScheduler(
    executors=executors,
    job_defaults=job_defaults,
    timezone='Asia/Shanghai'
)
```

**安全性保证:**
1. **BackgroundScheduler内部使用threading.Lock**保护共享状态
2. **ThreadPoolExecutor**确保任务在独立线程池执行，避免阻塞主线程
3. **max_instances=1**防止定时任务并发执行

### 2.2 Cron表达式和时区处理

**Cron表达式示例:**
```python
from apscheduler.triggers.cron import CronTrigger

# 数据更新任务：每天19:00触发
scheduler.add_job(
    func=data_update_task,
    trigger=CronTrigger(hour=19, minute=0, timezone='Asia/Shanghai'),
    id='data_update',
    name='Data Update Task'
)

# K线分析任务：每天21:00触发
scheduler.add_job(
    func=bar_analysis_task,
    trigger=CronTrigger(hour=21, minute=0, timezone='Asia/Shanghai'),
    id='bar_analysis',
    name='Bar Analysis Task'
)
```

**时区处理最佳实践:**
```python
import pytz
from datetime import datetime

# 统一使用项目配置的时区
TIMEZONE = 'Asia/Shanghai'  # 从GCONF读取

def get_timezone():
    """获取配置的时区对象"""
    return pytz.timezone(TIMEZONE)

# 任务函数内部使用时区感知的datetime
def scheduled_task():
    now = datetime.now(get_timezone())
    logger.info(f"Task executed at {now.isoformat()}")
```

### 2.3 与Kafka Consumer的兼容性

**架构模式: Thread-safe分离**

```python
class TaskTimer(threading.Thread):
    """定时任务调度器（Kafka Consumer + APScheduler）"""

    def __init__(self):
        super().__init__()
        # Kafka Consumer（独立线程）
        self.consumer = GinkgoConsumer(
            topic="ginkgo.live.interest.updates",
            group_id="task_timer_group"
        )

        # APScheduler（线程安全）
        self.scheduler = BackgroundScheduler(
            timezone='Asia/Shanghai',
            executors={'default': ThreadPoolExecutor(max_workers=3)}
        )

        # 共享状态（线程安全）
        self.all_symbols = set()  # 订阅标的集合
        self._lock = threading.Lock()

    def run(self):
        """主循环：Kafka消费 + APScheduler启动"""
        # 1. 启动APScheduler
        self.scheduler.start()

        # 2. 添加定时任务
        self._add_jobs()

        # 3. Kafka消费循环（在主线程）
        try:
            for message in self.consumer:
                self._handle_message(message)
        except Exception as e:
            logger.error(f"Consumer error: {e}")
        finally:
            self.scheduler.shutdown()

    def _data_update_task(self):
        """定时任务：数据更新（在ThreadPoolExecutor中执行）"""
        with self._lock:  # 访问共享状态时加锁
            symbols = list(self.all_symbols)

        logger.info(f"Starting data update for {len(symbols)} symbols")

        # 调用BarService获取K线数据
        bars = self.bar_service.get_daily_bars(symbols, date.today())

        # 发布到Kafka（线程安全）
        self.kafka_producer.send(
            topic="ginkgo.live.market.data",
            msg=[bar.to_dict() for bar in bars]
        )
```

**兼容性要点:**
1. **Kafka Consumer在主线程运行**，避免poll()和APScheduler任务冲突
2. **APScheduler任务在ThreadPoolExecutor执行**，不阻塞Consumer
3. **共享状态使用threading.Lock保护**，确保线程安全
4. **停止顺序**: 先shutdown() APScheduler，再close() Consumer

### 2.4 依赖添加

```toml
# pyproject.toml
dependencies = [
    # ... 现有依赖
    "apscheduler>=3.10.0",  # 新增：定时任务调度
]
```

---

## 三、WebSocket客户端选型对比

### 3.1 三种主流方案对比

| 特性 | **websocket-client** | **websockets** | **aiohttp** |
|------|---------------------|---------------|------------|
| **类型** | 同步 | 异步 | 异步 |
| **线程模型** | 阻塞式 | asyncio | asyncio |
| **API简洁度** | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| **性能** | 低 | 高 | 高 |
| **线程安全性** | 需自行管理 | asyncio保证 | asyncio保证 |
| **重连机制** | 手动实现 | 手动实现 | 手动实现 |
| **心跳检测** | 需手动实现 | 内置ping/pong | 内置ping/pong |
| **项目现状** | 已安装1.8.0 | 已安装15.0.1 | 已安装3.12.15 |
| **推荐度** | ⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

### 3.2 推荐方案: **websockets（异步） + run_coroutine_threadsafe**

**选型理由:**

1. **现有代码已使用websockets**
   - `src/ginkgo/trading/feeders/live_feeder.py:25`已经导入并使用websockets
   - 已有成熟的异步WebSocket连接管理实现

2. **性能优势**
   - 基于asyncio，支持高并发连接
   - 单线程处理多个连接，避免线程切换开销
   - 适合实时Tick数据推送（延迟<100ms）

3. **线程安全桥接**
   - 使用`asyncio.run_coroutine_threadsafe`与多线程环境集成
   - LiveDataFeeder已有成熟实现（第472-505行）

4. **内置心跳机制**
   ```python
   await websockets.connect(
       uri,
       ping_interval=30,  # 30秒发送一次ping
       ping_timeout=60,   # 60秒未收到pong则断开
       close_timeout=10   # 关闭握手超时
   )
   ```

### 3.3 实现示例

```python
import asyncio
import threading
import websockets
from typing import Optional, Set

class EastMoneyFeeder:
    """东方财富数据源（A股WebSocket）"""

    def __init__(self):
        self.all_symbols: Set[str] = set()
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None

    def set_symbols(self, symbols: Set[str]):
        """增量更新订阅标的（线程安全）"""
        self.all_symbols.update(symbols)

        # 如果已连接，触发订阅更新
        if self.loop and self.websocket:
            asyncio.run_coroutine_threadsafe(
                self._subscribe(symbols),
                self.loop
            )

    def start(self):
        """启动WebSocket连接（在独立线程运行事件循环）"""
        self.thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """停止WebSocket连接"""
        self._stop_event.set()

        if self.loop and self.websocket:
            asyncio.run_coroutine_threadsafe(
                self.websocket.close(),
                self.loop
            )

        if self.thread:
            self.thread.join(timeout=5)

    def _run_event_loop(self):
        """运行异步事件循环"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        try:
            self.loop.run_until_complete(self._async_main())
        finally:
            self.loop.close()

    async def _async_main(self):
        """异步主循环"""
        uri = "wss://push2.eastmoney.com/ws/qt/stock/klt.min"

        try:
            # 建立连接（内置心跳机制）
            async with websockets.connect(
                uri,
                ping_interval=30,  # 30秒ping
                ping_timeout=60,   # 60秒pong超时
                close_timeout=10
            ) as websocket:
                self.websocket = websocket

                # 订阅初始标的
                await self._subscribe(self.all_symbols)

                # 消息接收循环
                while not self._stop_event.is_set():
                    try:
                        message = await asyncio.wait_for(
                            websocket.recv(),
                            timeout=1.0  # 1秒超时，便于检查_stop_event
                        )
                        await self._handle_message(message)
                    except asyncio.TimeoutError:
                        continue
                    except websockets.exceptions.ConnectionClosed:
                        logger.warning("WebSocket connection closed, reconnecting...")
                        break

        except Exception as e:
            logger.error(f"WebSocket error: {e}")

    async def _subscribe(self, symbols: Set[str]):
        """订阅标的"""
        if not symbols:
            return

        # 构建订阅消息（东方财富格式）
        subscribe_msg = {
            "cmd": "sub",
            "param": {
                "symbols": list(symbols)
            }
        }

        await self.websocket.send(json.dumps(subscribe_msg))
        logger.info(f"Subscribed to {len(symbols)} symbols")

    async def _handle_message(self, message: str):
        """处理接收到的消息"""
        try:
            data = json.loads(message)

            # 转换为Tick对象
            tick = self._parse_tick(data)

            # 发布到Queue（后续由Queue消费者线程处理）
            self.queue.put(tick)

        except Exception as e:
            logger.error(f"Failed to handle message: {e}")

    def _parse_tick(self, data: dict) -> Tick:
        """解析Tick数据"""
        return Tick(
            code=data['code'],
            price=float(data['price']),
            volume=int(data['volume']),
            timestamp=datetime.now()
        )
```

### 3.4 断线重连机制

```python
async def _auto_reconnect(self, max_attempts=5, base_delay=2):
    """自动重连逻辑（指数退避）"""
    for attempt in range(1, max_attempts + 1):
        try:
            await self._async_main()
            return  # 连接成功，退出重连

        except Exception as e:
            logger.warning(f"Reconnect attempt {attempt}/{max_attempts} failed: {e}")

            if attempt < max_attempts:
                # 指数退避：2秒、4秒、8秒、16秒
                delay = base_delay ** attempt
                await asyncio.sleep(delay)
            else:
                logger.error(f"Max reconnect attempts ({max_attempts}) reached")
                raise
```

---

## 四、Kafka Consumer多线程模式

### 4.1 当前使用情况

**项目现状:**
- 使用`kafka-python-ng==2.2.3`（kafka-python的维护分支）
- Producer配置：
  - `acks='all'` - 等待所有ISR副本确认
  - `enable_idempotence=True` - 启用幂等性
  - `retries=3` - 自动重试3次
- Consumer配置：
  - `max_poll_records=1` - 逐条处理
  - `session_timeout_ms=30000` - 30秒会话超时
  - `heartbeat_interval_ms=3000` - 3秒心跳

### 4.2 多Consumer订阅同一Topic的行为

**实验结论:**

```python
# 场景：DataManager和TaskTimer都订阅 ginkgo.live.interest.updates

# DataManager Consumer
consumer1 = KafkaConsumer(
    "ginkgo.live.interest.updates",
    group_id="data_manager_group",  # 不同的group_id
    auto_offset_reset="latest"
)

# TaskTimer Consumer
consumer2 = KafkaConsumer(
    "ginkgo.live.interest.updates",
    group_id="task_timer_group",  # 不同的group_id
    auto_offset_reset="latest"
)

# 结果：每个Consumer都会收到完整的消息副本（广播模式）
# 原因：Kafka的Consumer Group机制，不同group_id各自独立消费
```

**关键特性:**
1. **不同group_id** → 每个Consumer接收全部消息（广播）
2. **相同group_id** → 负载均衡（每个分区只能被一个group内consumer消费）
3. **分区数24** → 最多支持24个并行consumer（同一group内）

### 4.3 多线程最佳实践

**推荐架构: 每个组件独立Consumer + 独立线程**

```python
class DataManager(threading.Thread):
    """实时数据管理器（Consumer + LiveDataFeeder + Queue消费者）"""

    def __init__(self):
        super().__init__()

        # Kafka Consumer（独立连接）
        self.consumer = GinkgoConsumer(
            topic="ginkgo.live.interest.updates",
            group_id="data_manager_group"  # 独立group
        )

        # LiveDataFeeder实例（硬编码）
        self.feeders = {
            'cn': EastMoneyFeeder(),
            'hk': FuShuFeeder(),
            'us': AlpacaFeeder()
        }

        # Queue消费者线程
        self.queue_consumers = []
        for market in ['cn', 'hk', 'us']:
            queue = Queue(maxsize=10000)
            consumer_thread = TickConsumer(queue, market)
            self.queue_consumers.append(consumer_thread)

        # 共享状态
        self.all_symbols = set()
        self._lock = threading.Lock()

    def run(self):
        """主循环：消费Kafka消息"""
        # 1. 启动所有Feeder
        for feeder in self.feeders.values():
            feeder.start()

        # 2. 启动Queue消费者
        for consumer in self.queue_consumers:
            consumer.start()

        # 3. Kafka消费循环（主线程）
        try:
            for message in self.consumer:
                self._handle_interest_update(message)
        except Exception as e:
            logger.error(f"Consumer error: {e}")
        finally:
            self._cleanup()

    def _handle_interest_update(self, message):
        """处理订阅更新消息"""
        symbols = set(message['symbols'])

        with self._lock:
            self.all_symbols.update(symbols)

        # 按市场分发订阅
        for market, feeder in self.feeders.items():
            market_symbols = self._filter_by_market(symbols, market)
            if market_symbols:
                feeder.set_symbols(market_symbols)

    def _cleanup(self):
        """清理资源"""
        # 停止Feeder
        for feeder in self.feeders.values():
            feeder.stop()

        # 等待Queue消费完
        for consumer in self.queue_consumers:
            consumer.join(timeout=10)

        # 关闭Consumer
        self.consumer.close()


class TaskTimer(threading.Thread):
    """定时任务调度器（Consumer + APScheduler）"""

    def __init__(self):
        super().__init__()

        # Kafka Consumer（独立连接）
        self.consumer = GinkgoConsumer(
            topic="ginkgo.live.interest.updates",
            group_id="task_timer_group"  # 独立group，不冲突
        )

        # APScheduler
        self.scheduler = BackgroundScheduler(timezone='Asia/Shanghai')

        self.all_symbols = set()
        self._lock = threading.Lock()

    def run(self):
        """主循环：消费Kafka消息 + 运行APScheduler"""
        self.scheduler.start()
        self._add_jobs()

        try:
            for message in self.consumer:
                self._handle_interest_update(message)
        except Exception as e:
            logger.error(f"Consumer error: {e}")
        finally:
            self.scheduler.shutdown()
            self.consumer.close()
```

### 4.4 启动和停止顺序

**启动顺序（避免数据丢失）:**
```python
def start_livecore():
    """LiveCore启动流程"""
    # 1. 先启动DataManager（准备数据接收）
    data_manager = DataManager()
    data_manager.start()

    # 2. 再启动TaskTimer（定时任务）
    task_timer = TaskTimer()
    task_timer.start()

    # 3. 最后启动Scheduler（策略调度）
    scheduler = Scheduler()
    scheduler.start()

    return [data_manager, task_timer, scheduler]
```

**停止顺序（确保优雅关闭）:**
```python
def stop_livecore(components):
    """LiveCore停止流程"""
    data_manager, task_timer, scheduler = components

    # 1. 先停止Scheduler（停止策略调度）
    scheduler.stop()
    scheduler.join(timeout=30)

    # 2. 再停止TaskTimer（停止定时任务）
    task_timer.stop()
    task_timer.join(timeout=30)

    # 3. 最后停止DataManager（等待数据消费完）
    data_manager.stop()
    data_manager.join(timeout=30)
```

### 4.5 是否需要confluent-kafka?

**结论: ❌ 不需要替换kafka-python-ng**

**理由:**
1. **kafka-python-ng已满足需求**
   - 支持多线程环境
   - 支持多Consumer广播模式
   - 性能满足实时性要求（<100ms延迟）

2. **confluent-kafka优势不明显**
   - 基于librdkafka（C库），性能更高
   - 但实时数据模块不是性能瓶颈（Kafka发布不是关键路径）
   - 增加C库依赖复杂度

3. **切换成本高**
   - API完全不同，需要重写所有Kafka相关代码
   - 需要安装librdkafka系统库
   - 当前kafka-python-ng运行稳定

**建议保持现状，除非遇到性能瓶颈**

---

## 五、潜在技术风险和缓解方案

### 5.1 风险清单

| 风险 | 影响 | 概率 | 缓解方案 |
|------|------|------|---------|
| **APScheduler任务崩溃导致整个调度器停止** | 高 | 中 | 使用`try-except`包裹任务函数，记录错误日志，避免任务间相互影响 |
| **WebSocket连接频繁断开** | 高 | 中 | 实现指数退避重连，最大重试次数可配置，重连成功后自动恢复订阅 |
| **Kafka消息积压导致延迟** | 中 | 低 | 使用`maxsize=10000`有界队列，满时丢弃当前数据并记录告警 |
| **多线程死锁** | 高 | 低 | 避免嵌套锁，使用`with self._lock`上下文管理器，设置锁超时 |
| **APScheduler与Consumer线程竞争** | 中 | 低 | Consumer在主线程，Scheduler任务在ThreadPoolExecutor，共享状态加锁保护 |
| **时区配置错误导致任务触发时间错误** | 高 | 中 | 统一使用`pytz.timezone('Asia/Shanghai')`，任务函数打印实际执行时间 |
| **Queue消费者线程阻塞导致内存泄漏** | 高 | 低 | Queue设置timeout，`get(timeout=1)`定期检查停止标志 |

### 5.2 具体缓解实现

**APScheduler任务崩溃隔离:**
```python
def safe_job_wrapper(func):
    """任务装饰器：隔离任务崩溃"""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Job {func.__name__} failed: {e}", exc_info=True)
            # 发送告警通知
            notify(f"定时任务 {func.__name__} 执行失败", level="ERROR")
            return None
    return wrapper

@safe_job_wrapper
def data_update_task():
    """带崩溃隔离的数据更新任务"""
    # 任务逻辑
    pass
```

**WebSocket重连退避:**
```python
async def _auto_reconnect(self, max_attempts=5, base_delay=2):
    """指数退避重连"""
    for attempt in range(1, max_attempts + 1):
        try:
            await self._async_main()
            logger.info("Reconnected successfully")
            return

        except Exception as e:
            delay = min(base_delay ** attempt, 60)  # 最大60秒
            logger.warning(f"Reconnect attempt {attempt} failed, retry in {delay}s")
            await asyncio.sleep(delay)

    logger.error("Max reconnect attempts reached, giving up")
    notify("WebSocket连接失败，已达到最大重试次数", level="ERROR")
```

**Queue消费者防阻塞:**
```python
class TickConsumer(threading.Thread):
    """Tick数据消费者（防阻塞）"""

    def run(self):
        while not self._stop_event.is_set():
            try:
                # 阻塞获取，但设置1秒超时
                tick = self.queue.get(timeout=1.0)
                self._process_tick(tick)

            except queue.Empty:
                continue  # 超时，继续循环

            except Exception as e:
                logger.error(f"Failed to process tick: {e}")

    def _process_tick(self, tick):
        """处理Tick数据"""
        dto = PriceUpdateDTO.from_tick(tick)
        self.kafka_producer.send("ginkgo.live.market.data", dto.to_dict())
```

---

## 六、选型总结

### 6.1 最终选型

| 组件 | 选择 | 版本 | 理由 |
|------|------|------|------|
| **定时任务调度** | APScheduler | >=3.10.0 | BackgroundScheduler线程安全，Cron表达式丰富，与Kafka Consumer兼容 |
| **WebSocket客户端** | websockets | 15.0.1（已安装） | 异步高性能，现有代码已使用，内置心跳机制 |
| **Kafka客户端** | kafka-python-ng | 2.2.3（已安装） | 满足多线程需求，稳定可用，无需切换 |

### 6.2 需要添加的依赖

```toml
# pyproject.toml
dependencies = [
    # 新增
    "apscheduler>=3.10.0",

    # 现有（无需变更）
    "websockets>=15.0.1",
    "websocket-client>=1.8.0",
    "kafka-python-ng>=2.2.3",
]
```

### 6.3 实施建议

1. **Phase 0: 技术验证** ✅
   - ✅ APScheduler + Kafka Consumer的兼容性验证
   - ✅ WebSocket连接稳定性研究
   - ✅ 多Consumer广播模式验证

2. **Phase 1: 组件设计** (下一步)
   - 设计DataManager（Kafka Consumer + LiveDataFeeder）
   - 设计TaskTimer（Kafka Consumer + APScheduler）
   - 设计Queue消费者线程

3. **Phase 2: TDD实现**
   - 先实现DataManager（Kafka Consumer + LiveDataFeeder）
   - 再实现TaskTimer（Kafka Consumer + APScheduler）
   - 最后实现Queue消费者线程

4. **Phase 3: 集成测试**
   - 测试启动/停止顺序
   - 测试异常场景（网络断开、Kafka宕机）
   - 性能测试（<100ms延迟验证）

---

## 七、附录：关键代码示例

### A. APScheduler完整示例

```python
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.executors.pool import ThreadPoolExecutor
import threading

class TaskTimer(threading.Thread):
    """定时任务调度器完整实现"""

    def __init__(self, kafka_producer):
        super().__init__()
        self.kafka_producer = kafka_producer
        self.scheduler = None
        self.all_symbols = set()
        self._lock = threading.Lock()
        self._stop_event = threading.Event()

    def run(self):
        """主循环"""
        # 初始化APScheduler
        self.scheduler = BackgroundScheduler(
            timezone='Asia/Shanghai',
            executors={
                'default': ThreadPoolExecutor(max_workers=3)
            },
            job_defaults={
                'coalesce': True,
                'max_instances': 1,
                'misfire_grace_time': 300
            }
        )

        # 添加定时任务
        self.scheduler.add_job(
            func=self._data_update_job,
            trigger=CronTrigger(hour=19, minute=0),
            id='data_update',
            name='Data Update Job'
        )

        self.scheduler.add_job(
            func=self._bar_analysis_job,
            trigger=CronTrigger(hour=21, minute=0),
            id='bar_analysis',
            name='Bar Analysis Job'
        )

        # 启动调度器
        self.scheduler.start()

        # 等待停止信号
        self._stop_event.wait()

        # 优雅关闭
        self.scheduler.shutdown()

    def _data_update_job(self):
        """数据更新任务（19:00触发）"""
        try:
            with self._lock:
                symbols = list(self.all_symbols)

            logger.info(f"Starting data update for {len(symbols)} symbols")

            # 调用数据更新服务
            # bar_service.update_daily_bars(symbols)

        except Exception as e:
            logger.error(f"Data update job failed: {e}")

    def _bar_analysis_job(self):
        """K线分析任务（21:00触发）"""
        try:
            with self._lock:
                symbols = list(self.all_symbols)

            logger.info(f"Starting bar analysis for {len(symbols)} symbols")

            # 获取当日K线并发布到Kafka
            # bars = bar_service.get_daily_bars(symbols, date.today())
            # kafka_producer.send("ginkgo.live.market.data", bars)

        except Exception as e:
            logger.error(f"Bar analysis job failed: {e}")

    def stop(self):
        """停止调度器"""
        self._stop_event.set()
```

### B. WebSocket完整示例

```python
import asyncio
import websockets
import threading
import json
from typing import Set

class EastMoneyFeeder:
    """东方财富数据源（完整实现）"""

    def __init__(self, queue):
        self.queue = queue
        self.all_symbols: Set[str] = set()
        self.loop = None
        self.thread = None
        self.websocket = None
        self._stop_event = threading.Event()
        self._reconnect_event = asyncio.Event()

    def start(self):
        """启动Feeder"""
        self.thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self.thread.start()

    def stop(self):
        """停止Feeder"""
        self._stop_event.set()

        if self.loop and self.websocket:
            asyncio.run_coroutine_threadsafe(
                self.websocket.close(),
                self.loop
            )

        if self.thread:
            self.thread.join(timeout=5)

    def set_symbols(self, symbols: Set[str]):
        """更新订阅标的"""
        self.all_symbols.update(symbols)

        if self.loop and self.websocket:
            asyncio.run_coroutine_threadsafe(
                self._subscribe(symbols),
                self.loop
            )

    def _run_event_loop(self):
        """运行事件循环"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

        try:
            self.loop.run_until_complete(self._auto_reconnect())
        finally:
            self.loop.close()

    async def _auto_reconnect(self, max_attempts=5):
        """自动重连"""
        for attempt in range(1, max_attempts + 1):
            try:
                await self._connect_and_receive()
                return  # 连接成功，退出

            except Exception as e:
                logger.warning(f"Reconnect attempt {attempt} failed: {e}")
                if attempt < max_attempts:
                    await asyncio.sleep(2 ** attempt)

        logger.error("Max reconnect attempts reached")

    async def _connect_and_receive(self):
        """连接并接收消息"""
        uri = "wss://push2.eastmoney.com/ws/qt/stock/klt.min"

        async with websockets.connect(
            uri,
            ping_interval=30,
            ping_timeout=60,
            close_timeout=10
        ) as websocket:
            self.websocket = websocket

            # 订阅初始标的
            await self._subscribe(self.all_symbols)

            # 接收消息
            while not self._stop_event.is_set():
                try:
                    message = await asyncio.wait_for(
                        websocket.recv(),
                        timeout=1.0
                    )
                    await self._handle_message(message)

                except asyncio.TimeoutError:
                    continue
                except websockets.exceptions.ConnectionClosed:
                    logger.warning("Connection closed")
                    break

    async def _subscribe(self, symbols: Set[str]):
        """订阅标的"""
        if not symbols:
            return

        msg = {
            "cmd": "sub",
            "param": {"symbols": list(symbols)}
        }

        await self.websocket.send(json.dumps(msg))
        logger.info(f"Subscribed to {len(symbols)} symbols")

    async def _handle_message(self, message: str):
        """处理消息"""
        try:
            data = json.loads(message)
            tick = self._parse_tick(data)
            self.queue.put(tick)
        except Exception as e:
            logger.error(f"Failed to handle message: {e}")

    def _parse_tick(self, data: dict):
        """解析Tick数据"""
        return Tick(
            code=data['code'],
            price=float(data['price']),
            volume=int(data['volume']),
            timestamp=datetime.now()
        )
```

---

**Phase 0 完成时间:** 2026-01-09
**下一步:** 执行Phase 1 - 创建data-model.md和contracts/
