# 实盘数据模块快速入门指南

**Feature**: 008-live-data-module
**Date**: 2026-01-17
**Purpose**: 快速上手实盘数据模块的使用和开发

---

## 一、环境准备

### 1.1 安装依赖

```bash
# 安装APScheduler（新增依赖）
pip install apscheduler>=3.10.0

# 其他依赖已安装：
# - websockets==15.0.1
# - kafka-python-ng==2.2.3
# - pytz==2025.2
```

### 1.2 配置Kafka

**确保Kafka已启动并创建Topic**:

```bash
# 创建Kafka Topic
kafka-topics.sh --create \
  --bootstrap-server localhost:9092 \
  --topic ginkgo.live.interest.updates \
  --partitions 24 \
  --replication-factor 3

kafka-topics.sh --create \
  --bootstrap-server localhost:9092 \
  --topic ginkgo.live.market.data \
  --partitions 24 \
  --replication-factor 3
```

### 1.3 配置数据源

**创建配置文件**: `~/.ginkgo/data_sources.yml`

```yaml
data_sources:
  eastmoney:
    websocket_uri: "wss://push2.eastmoney.com/ws/qt/stock/klt.min"
    ping_interval: 30
    ping_timeout: 60

  fushu:
    http_uri: "https://api.fushu.com/v1/tick"
    poll_interval: 5

  alpaca:
    api_key: "${ALPACA_API_KEY}"
    api_secret: "${ALPACA_API_SECRET}"
    websocket_uri: "wss://stream.data.alpaca.markets/v2/iex"
```

**设置环境变量**:

```bash
# ~/.bashrc 或 ~/.zshrc
export ALPACA_API_KEY="your_api_key"
export ALPACA_API_SECRET="your_api_secret"
```

---

## 二、DataManager使用示例

### 2.1 启动DataManager

```python
from ginkgo.livecore.data_manager import DataManager

# 创建DataManager实例（可选择数据源：eastmoney/fushu/alpaca）
data_manager = DataManager(feeder_type="eastmoney")

# 启动DataManager（后台线程）
data_manager.start()

# 订阅实时数据
data_manager.subscribe_live_data(symbols=["000001.SZ", "600000.SH"])

# 等待停止信号
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    # 停止DataManager
    data_manager.stop()
    data_manager.join()
```

**说明**:
- DataManager使用`@retry`装饰器（max_try=3, backoff_factor=2）实现Kafka发布重试
- 支持三种数据源：`eastmoney`（A股WebSocket）、`fushu`（港股HTTP轮询）、`alpaca`（美股WebSocket）
- 从`~/.ginkgo/data_sources.yml`读取API密钥（非敏感配置）和从`secure.yml`读取敏感凭证

### 2.2 发送订阅更新

**通过Kafka发送订阅更新**:

```python
from ginkgo.interfaces.dtos import InterestUpdateDTO
from ginkgo.interfaces.kafka_topics import KafkaTopics
from datetime import datetime

# 创建订阅更新DTO
dto = InterestUpdateDTO(
    portfolio_id="portfolio_001",
    node_id="node_001",
    symbols=["000001.SZ", "600000.SH", "00700.HK"],
    timestamp=datetime.now()
)

# 发布到Kafka
kafka_producer.send(
    topic=KafkaTopics.INTEREST_UPDATES,
    message=dto.model_dump_json()
)
```

### 2.3 接收实时数据

**ExecutionNode接收实时数据**:

```python
from ginkgo.interfaces.dtos import PriceUpdateDTO
from ginkgo.interfaces.kafka_topics import KafkaTopics

# Kafka Consumer订阅实时数据
consumer = GinkgoConsumer(
    topic=KafkaTopics.MARKET_DATA,
    group_id="execution_node_group"
)

# 消费实时数据
for message in consumer:
    # 解析PriceUpdateDTO
    dto = PriceUpdateDTO.model_validate_json(message.value)

    # 触发策略计算
    portfolio.on_price_update(dto)
```

---

## 三、TaskTimer使用示例

### 3.1 启动TaskTimer

```python
from ginkgo.livecore.task_timer import TaskTimer

# 创建TaskTimer实例（默认使用~/.ginkgo/task_timer.yml配置）
task_timer = TaskTimer()

# 启动TaskTimer（后台线程）
task_timer.start()

# 等待停止信号
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    # 停止TaskTimer
    task_timer.stop()
    task_timer.join()
```

**说明**:
- TaskTimer使用`@retry`装饰器（max_try=3, backoff_factor=2）实现Kafka发布重试
- 使用`safe_job_wrapper`装饰器实现任务崩溃隔离
- 从`~/.ginkgo/task_timer.yml`加载定时任务配置

### 3.2 定时任务配置

**配置文件**: `~/.ginkgo/task_timer.yml`

```yaml
# 定时任务配置
scheduled_tasks:
  # K线快照任务：每天21:00触发
  - name: "bar_snapshot"
    cron: "0 21 * * *"  # 分 时 日 月 周
    command: "bar_snapshot"
    enabled: true

  # Selector更新任务：每小时触发
  - name: "update_selector"
    cron: "0 * * * *"
    command: "update_selector"
    enabled: true

  # 数据更新任务：每天19:00触发
  - name: "update_data"
    cron: "0 19 * * *"
    command: "update_data"
    enabled: false  # 默认禁用
```

**Cron表达式格式**: `分 时 日 月 周`

**示例**:
- `0 21 * * *` - 每天21:00
- `0 */1 * * *` - 每小时
- `0 9-15 * * 1-5` - 工作日9点到15点每小时
- `*/30 * * * *` - 每30分钟

### 3.3 接收K线数据

**ExecutionNode接收K线数据**:

```python
from ginkgo.interfaces.dtos import BarDTO

# Kafka Consumer订阅K线数据
consumer = GinkgoConsumer(
    topic=KafkaTopics.MARKET_DATA,
    group_id="execution_node_group"
)

# 消费K线数据
for message in consumer:
    # 解析DTO
    try:
        dto = PriceUpdateDTO.model_validate_json(message.value)
        portfolio.on_price_update(dto)
    except ValidationError:
        # 可能是BarDTO
        dto = BarDTO.model_validate_json(message.value)
        portfolio.on_bar_update(dto)
```

---

## 四、LiveDataFeeder实现示例

**已实现的LiveDataFeeder**:

项目已包含三种数据源实现（多态模式，无需工厂）：

| Feeder | 文件路径 | 市场 | 协议 |
|--------|----------|------|------|
| EastMoneyFeeder | `src/ginkgo/trading/feeders/eastmoney_feeder.py` | A股 | WebSocket |
| FuShuFeeder | `src/ginkgo/trading/feeders/fushu_feeder.py` | 港股 | HTTP轮询 |
| AlpacaFeeder | `src/ginkgo/trading/feeders/alpaca_feeder.py` | 美股 | WebSocket |

**使用方式**:
```python
# DataManager通过多态创建Feeder
data_manager = DataManager(feeder_type="eastmoney")  # 或 "fushu", "alpaca"
```

**扩展新数据源**:
```python
# 继承ILiveDataFeeder接口
from ginkgo.trading.feeders.interfaces import ILiveDataFeeder

class MyCustomFeeder(ILiveDataFeeder):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 实现WebSocket/HTTP连接逻辑

    # 实现接口方法...
```

**配置说明**:
- API密钥从`~/.ginkgo/secure.yml`读取（通过GCONF）
- WebSocket URI在Feeder类中写死（硬编码配置）
- 支持的数据源类型在`DataManager._create_feeder()`中注册

---

## 五、ExecutionNode扩展（实盘模式Selector触发）

### 5.1 PortfolioProcessor控制命令处理

PortfolioProcessor已扩展支持Kafka控制命令消费：

**文件路径**: `src/ginkgo/workers/execution_node/portfolio_processor.py`

**新增功能**:
- 订阅`ginkgo.live.control.commands` topic
- 处理`update_selector`命令，触发selector.pick()
- 发布`EventInterestUpdate`到Kafka

**数据流**:
```
TaskTimer → Kafka(ControlCommandDTO: update_selector)
         → PortfolioProcessor._handle_control_command()
         → PortfolioProcessor._update_selectors()
         → selector.pick()
         → EventInterestUpdate → Kafka(ginkgo.live.interest.updates)
         → DataManager更新订阅
```

### 5.2 控制命令类型

| 命令 | 触发者 | 处理者 | 说明 |
|------|--------|--------|------|
| `bar_snapshot` | TaskTimer (21:00) | DataManager | 推送当日K线数据 |
| `update_selector` | TaskTimer (每小时) | PortfolioProcessor | 触发selector.pick() |
| `update_data` | TaskTimer (19:00) | DataManager | 数据更新命令 |

---

## 六、LiveCore集成示例

### 6.1 启动LiveCore

```python
from ginkgo.livecore.data_manager import DataManager
from ginkgo.livecore.task_timer import TaskTimer

# 创建DataManager实例
data_manager = DataManager(feeder_type="eastmoney")
data_manager.start()

# 创建TaskTimer实例
task_timer = TaskTimer()
task_timer.start()

# 等待停止信号
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    # 停止LiveCore
    task_timer.stop()
    data_manager.stop()
```

### 6.2 启动顺序

**正确的启动顺序**:
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

### 6.3 停止顺序

**正确的停止顺序**:
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

---

## 七、调试和监控

### 7.1 日志配置

```python
from ginkgo.libs import GLOG

# 使用GLOG进行结构化日志记录
GLOG.info("DataManager started")
GLOG.debug(f"Processing tick: {symbol}")
GLOG.error(f"Failed to publish to Kafka: {e}")
```

### 7.2 性能监控

**监控实时数据延迟**:
```python
import time

def measure_latency(tick: Tick):
    """测量数据延迟"""
    latency = (datetime.now() - tick.timestamp).total_seconds()
    if latency > 0.1:  # 超过100ms
        logger.warning(f"Data latency {latency:.3f}s exceeds threshold")
```

**监控Queue深度**:
```python
def monitor_queue_depth(queue: Queue):
    """监控Queue深度"""
    depth = queue.qsize()
    if depth > 8000:  # 超过80%容量
        logger.warning(f"Queue depth {depth} exceeds 80% capacity")
```

### 7.3 告警通知

**发送告警通知**:
```python
def send_alert(message: str, level: str = "ERROR"):
    """发送告警通知"""
    # 发布到Kafka通知Topic
    kafka_producer.send(
        topic="ginkgo.notifications",
        message={
            "level": level,
            "message": message,
            "timestamp": datetime.now().isoformat()
        }
    )
```

---

## 八、常见问题

### Q1: WebSocket连接频繁断开？

**原因**: 网络不稳定或心跳超时

**解决方案**:
```python
# 增加心跳超时时间
await websockets.connect(
    uri,
    ping_interval=30,
    ping_timeout=120,  # 增加到120秒
    close_timeout=10
)

# 实现自动重连
async def _auto_reconnect(self, max_attempts=10):
    for attempt in range(1, max_attempts + 1):
        try:
            await self._connect_and_receive()
            return
        except Exception as e:
            delay = min(2 ** attempt, 60)  # 最大60秒
            logger.warning(f"Reconnect attempt {attempt} failed, retry in {delay}s")
            await asyncio.sleep(delay)
```

### Q2: Queue满导致数据丢失？

**原因**: Queue消费者处理速度跟不上生产者

**解决方案**:
```python
# 增加Queue大小
queue = Queue(maxsize=20000)  # 从10000增加到20000

# 增加消费者线程数
for i in range(2):  # 创建2个消费者线程
    consumer = TickConsumer(queue, market)
    consumer.start()
```

### Q3: Kafka发布失败？

**原因**: Kafka集群不可用或网络问题

**解决方案**:
```python
# 实现发布重试
def _publish_with_retry(self, dto, max_retry=3):
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
                time.sleep(2 ** attempt)

    # 所有重试失败
    logger.error(f"Failed to publish after {max_retry} attempts")
    send_alert("Kafka发布失败，可能存在数据丢失")
```

---

## 九、下一步

1. **运行测试**: 执行单元测试和集成测试，验证功能正确性
2. **配置数据源**: 设置`~/.ginkgo/data_sources.yml`和`~/.ginkgo/secure.yml`
3. **启动Kafka**: 确保Kafka集群运行并创建所需Topics
4. **配置定时任务**: 编辑`~/.ginkgo/task_timer.yml`
5. **启动LiveCore**: 按正确顺序启动DataManager和TaskTimer

---

**快速入门指南完成时间**: 2026-01-17
**版本**: 1.0
