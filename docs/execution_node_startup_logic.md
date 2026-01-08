# ExecutionNode 启动逻辑详解

## 概述

ExecutionNode 是 Portfolio 的运行容器，负责运行多个 Portfolio 实例并处理来自 Kafka 的事件。

---

## 启动流程

### 1. 初始化阶段（`__init__`）

```python
ExecutionNode(node_id: str)
```

**核心组件初始化**：

```python
# Portfolio 管理
self.portfolios: Dict[str, PortfolioProcessor] = {}          # {portfolio_id: PortfolioProcessor}
self.portfolio_lock = Lock()                                  # 线程安全锁
self._portfolio_instances: Dict[str, PortfolioLive] = {}     # Portfolio 实例持有

# 路由优化（Phase 4）
self.interest_map: InterestMap = InterestMap()               # 股票代码 → Portfolio ID 列表

# Kafka 连接
self.market_data_consumer: Optional[GinkgoConsumer] = None   # 市场数据消费者
self.order_feedback_consumer: Optional[GinkgoConsumer] = None # 订单反馈消费者
self.schedule_updates_consumer: Optional[GinkgoConsumer] = None  # 调度更新消费者（Phase 5）
self.order_producer = GinkgoProducer()                       # 订单生产者

# 线程管理
self.market_data_thread: Optional[Thread] = None
self.order_feedback_thread: Optional[Thread] = None
self.schedule_updates_thread: Optional[Thread] = None       # 调度更新线程（Phase 5）
self.heartbeat_thread: Optional[Thread] = None              # 心跳线程（Phase 5）

# 运行状态
self.is_running = False

# 心跳配置（Phase 5）
self.heartbeat_interval = 10   # 10秒发送一次心跳
self.heartbeat_ttl = 30        # 心跳 TTL 30秒

# 背压统计
self.backpressure_count = 0
self.dropped_event_count = 0
self.total_event_count = 0
```

**关键点**：
- ✅ 初始化阶段**不启动任何线程**
- ✅ 初始化阶段**不连接 Kafka**
- ✅ 只准备数据结构和配置

---

### 2. 启动阶段（`start()`）

```python
def start(self):
    """启动ExecutionNode"""
```

**启动流程**：

```python
# 1. 状态检查
if self.is_running:
    print(f"[WARNING] ExecutionNode {self.node_id} is already running")
    return

# 2. 设置运行标志
self.is_running = True
print(f"Starting ExecutionNode {self.node_id}")

# 3. 启动心跳上报线程（Phase 5）
self._start_heartbeat_thread()

# 4. 启动调度更新订阅线程（Phase 5）
self._start_schedule_updates_thread()

# 5. TODO: 启动Kafka消费线程（Phase 4实现）
# TODO: 订阅market.data和orders.feedback topics
```

**关键点**：
- ✅ 启动**心跳线程**（Phase 5）
- ✅ 启动**调度更新订阅线程**（Phase 5）
- ⏳ **待实现**：启动市场数据和订单反馈消费线程（Phase 4）

---

### 3. 心跳线程（Phase 5）

#### 启动心跳线程

```python
def _start_heartbeat_thread(self):
    """启动心跳上报线程"""
    self.heartbeat_thread = Thread(
        target=self._heartbeat_loop,
        daemon=True,                      # 守护线程，主线程退出时自动结束
        name=f"heartbeat_{self.node_id}"
    )
    self.heartbeat_thread.start()
```

#### 心跳循环

```python
def _heartbeat_loop(self):
    """心跳上报循环（每10秒发送一次）"""
    while self.is_running:
        try:
            # 1. 发送心跳到 Redis
            self._send_heartbeat()

            # 2. 更新性能指标到 Redis
            self._update_node_metrics()

        except Exception as e:
            logger.error(f"Heartbeat error: {e}")

        # 3. 等待下一次心跳
        time.sleep(self.heartbeat_interval)  # 10秒
```

#### 发送心跳

```python
def _send_heartbeat(self):
    """发送心跳到 Redis"""
    redis_client = self._get_redis_client()

    # Redis Key: heartbeat:node:{node_id}
    heartbeat_key = f"heartbeat:node:{self.node_id}"
    heartbeat_value = datetime.now().isoformat()

    # 设置心跳并附带 TTL（30秒）
    redis_client.setex(
        heartbeat_key,
        self.heartbeat_ttl,        # TTL = 30秒
        heartbeat_value
    )
```

**心跳机制**：
- 📡 每 **10 秒**发送一次心跳
- ⏰ TTL **30 秒**（超过 30 秒无心跳认为节点离线）
- 💾 存储到 Redis Key: `heartbeat:node:{node_id}`
- 🔍 Scheduler 通过检查 TTL 判断节点健康状态

#### 更新节点指标

```python
def _update_node_metrics(self):
    """更新节点性能指标到 Redis"""
    metrics = {
        "portfolio_count": str(len(self.portfolios)),
        "queue_size": str(self._get_average_queue_size()),
        "cpu_usage": "0.0",                    # 预留
        "memory_usage": "0",                   # 预留
        "total_events": str(self.total_event_count),
        "backpressure_count": str(self.backpressure_count),
        "dropped_events": str(self.dropped_event_count)
    }

    # Redis Key: node:metrics:{node_id} (Hash)
    metrics_key = f"node:metrics:{self.node_id}"
    redis_client.hset(metrics_key, mapping=metrics)
```

**性能指标**：
- 📊 Portfolio 数量
- 📈 平均队列大小
- 🔢 总事件数
- ⚠️ 背压次数
- ❌ 丢弃事件数

---

### 4. 调度更新订阅线程（Phase 5）

#### 启动调度更新线程

```python
def _start_schedule_updates_thread(self):
    """启动调度更新订阅线程"""
    self.schedule_updates_thread = Thread(
        target=self._schedule_updates_loop,
        daemon=True,
        name=f"schedule_updates_{self.node_id}"
    )
    self.schedule_updates_thread.start()
```

#### 调度更新循环

```python
def _schedule_updates_loop(self):
    """调度更新消费循环"""
    # 创建 Kafka 消费者
    topic = "schedule.updates"
    self.schedule_updates_consumer = GinkgoConsumer(
        topic=topic,
        group_id=f"execution_node_{self.node_id}",
        offset="latest"                    # 从最新消息开始消费
    )

    logger.info(f"Subscribed to {topic} for node {self.node_id}")

    # 消费循环
    while self.is_running:
        try:
            # 从 Kafka 拉取消息
            messages = self.schedule_updates_consumer.consumer.poll(timeout_ms=1000)

            for tp, records in messages.items():
                for msg in records:
                    # 处理调度命令
                    self._handle_schedule_update(msg)

        except Exception as e:
            logger.error(f"Schedule updates loop error: {e}")

    # 清理
    if self.schedule_updates_consumer:
        self.schedule_updates_consumer.close()
        logger.info("Schedule updates consumer closed")
```

**订阅机制**：
- 📡 订阅 Kafka Topic: `schedule.updates`
- 👥 Group ID: `execution_node_{node_id}`
- 🆕 `offset="latest"`：只消费新消息（启动后的命令）

#### 处理调度命令

```python
def _handle_schedule_update(self, msg):
    """处理调度更新命令"""
    command_data = msg.value  # GinkgoConsumer 已反序列化
    command = command_data.get("command")
    portfolio_id = command_data.get("portfolio_id")

    # 路由到具体处理器
    if command == "portfolio.reload":
        self._handle_portfolio_reload(portfolio_id, command_data)

    elif command == "portfolio.migrate":
        self._handle_portfolio_migrate(portfolio_id, command_data)

    elif command == "node.shutdown":
        self._handle_node_shutdown(command_data)

    else:
        logger.warning(f"Unknown command: {command}")
```

**支持的命令**：
- 🔄 `portfolio.reload`：重载 Portfolio 配置
- 📦 `portfolio.migrate`：迁移 Portfolio 到其他节点
- 🛑 `node.shutdown`：关闭节点

---

## 停止流程

```python
def stop(self):
    """停止ExecutionNode"""
    if not self.is_running:
        return

    print(f"Stopping ExecutionNode {self.node_id}")
    self.is_running = False

    # 1. 停止心跳线程
    if self.heartbeat_thread and self.heartbeat_thread.is_alive():
        logger.info("Stopping heartbeat thread...")
        self.heartbeat_thread.join(timeout=5)

    # 2. 停止所有 PortfolioProcessor
    with self.portfolio_lock:
        processors_to_stop = list(self.portfolios.values())

    for processor in processors_to_stop:
        processor.stop()

    # 3. 等待消费线程结束
    if self.schedule_updates_thread and self.schedule_updates_thread.is_alive():
        self.schedule_updates_thread.join(timeout=5)

    # 4. 关闭 Kafka 连接
    if self.schedule_updates_consumer:
        self.schedule_updates_consumer.close()

    logger.info(f"ExecutionNode {self.node_id} stopped")
```

**停止顺序**：
1. 设置 `is_running = False`（所有循环线程检测到后退出）
2. 等待心跳线程结束
3. 停止所有 PortfolioProcessor
4. 等待消费线程结束
5. 关闭 Kafka 连接

---

## 线程架构

```
ExecutionNode 主线程
    │
    ├─ 心跳线程（heartbeat_thread）
    │   └─ _heartbeat_loop()
    │       ├─ _send_heartbeat()        [每 10 秒]
    │       └─ _update_node_metrics()    [每 10 秒]
    │
    ├─ 调度更新线程（schedule_updates_thread）
    │   └─ _schedule_updates_loop()
    │       ├─ Kafka poll()
    │       └─ _handle_schedule_update()
    │
    ├─ 市场数据消费线程（market_data_thread）[TODO]
    │   └─ _market_data_loop()
    │
    └─ 订单反馈消费线程（order_feedback_thread）[TODO]
        └─ _order_feedback_loop()
```

**线程特性**：
- 🔒 线程安全：使用 `Lock` 保护共享数据
- 👻 守护线程：`daemon=True`，主线程退出时自动结束
- 🛑 优雅停止：通过 `is_running` 标志控制

---

## 启动时机

### 手动启动

```python
from ginkgo.workers.execution_node.node import ExecutionNode

# 创建节点
node = ExecutionNode(node_id="my_node")

# 启动节点
node.start()
```

### LiveCore 启动（集成）

```python
# LiveCore 启动时会自动启动 ExecutionNode
from ginkgo.livecore.main import LiveCore

livecore = LiveCore()
livecore.start()  # 会启动 ExecutionNode 和 Scheduler
```

---

## 关键配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `heartbeat_interval` | 10 秒 | 心跳发送间隔 |
| `heartbeat_ttl` | 30 秒 | 心跳过期时间（TTL） |
| `is_running` | `False` | 运行标志 |
| `daemon_threads` | `True` | 守护线程 |

---

## 总结

### ExecutionNode 启动逻辑核心要点：

1. **延迟启动**：初始化和启动分离，`__init__` 只准备数据结构
2. **线程分离**：心跳、调度更新、市场数据、订单反馈各独立线程
3. **心跳机制**：每 10 秒上报，TTL 30 秒，支持故障检测
4. **调度订阅**：从 Kafka 接收调度命令（reload/migrate/shutdown）
5. **优雅停止**：通过 `is_running` 标志控制所有线程退出
6. **线程安全**：使用 `Lock` 保护 Portfolio 列表等共享数据

### 启动后自动执行的任务：

✅ **心跳上报**（每 10 秒）
- Redis: `heartbeat:node:{node_id}` (TTL=30s)
- Redis: `node:metrics:{node_id}` (Hash)

✅ **调度更新监听**（持续消费）
- Kafka: `schedule.updates` topic
- 处理 reload/migrate/shutdown 命令

⏳ **市场数据消费**（待实现 Phase 4）
- Kafka: `market.data` topic

⏳ **订单反馈消费**（待实现 Phase 4）
- Kafka: `orders.feedback` topic
