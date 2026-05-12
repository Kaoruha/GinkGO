# ExecutionNode 心跳上报信息详解

## 概述

ExecutionNode 每 10 秒发送一次心跳，向 Redis 上报两类信息：
1. **心跳信息** (`heartbeat:node:{node_id}`) - 证明节点存活
2. **性能指标** (`node:metrics:{node_id}`) - 节点运行状态

---

## 心跳发送流程

```python
# 心跳线程每10秒执行一次
def _heartbeat_loop(self):
    while self.is_running:
        self._send_heartbeat()        # 发送心跳
        self._update_node_metrics()    # 更新指标
        time.sleep(10)                # 等待10秒
```

---

## 1. 心跳信息 (heartbeat:node:{node_id})

### Redis 键结构

```
Key:   heartbeat:node:{node_id}
Type:  String
TTL:   30秒（自动过期）
Value: ISO 8601 时间戳
```

### 示例

```python
redis_client.setex(
    "heartbeat:node:my_node_1",
    30,  # TTL 30秒
    "2026-01-06T12:30:45.123456"  # 当前时间
)
```

### Redis CLI 查看

```bash
# 查看心跳值
127.0.0.1:6379> GET heartbeat:node:my_node_1
"2026-01-06T12:30:45.123456"

# 查看心跳TTL
127.0.0.1:6379> TTL heartbeat:node:my_node_1
(integer) 25  # 还剩25秒过期

# 检查心跳是否存在
127.0.0.1:6379> EXISTS heartbeat:node:my_node_1
(integer) 1  # 存在 = 节点在线
```

### 用途

- ✅ **存活证明**：键存在 = 节点在线
- ✅ **离线检测**：键不存在或TTL过期 = 节点离线
- ✅ **时间戳**：最后一次心跳时间

---

## 2. 性能指标 (node:metrics:{node_id})

### Redis 键结构

```
Key:   node:metrics:{node_id}
Type:  Hash
TTL:   无（手动删除或节点停止时清理）
Fields: 7个指标字段
```

### 指标详情

| 字段 | 类型 | 说明 | 示例值 |
|------|------|------|--------|
| `portfolio_count` | String | 当前运行的 Portfolio 数量 | `"3"` |
| `queue_size` | String | 所有 Portfolio 的平均队列大小 | `"15"` |
| `cpu_usage` | String | CPU 使用率（预留） | `"0.0"` |
| `memory_usage` | String | 内存使用（预留） | `"0"` |
| `total_events` | String | 总处理事件数 | `"15000"` |
| `backpressure_count` | String | 背压发生次数 | `"5"` |
| `dropped_events` | String | 丢弃事件数 | `"2"` |

### 代码实现

```python
metrics = {
    "portfolio_count": str(len(self.portfolios)),
    "queue_size": str(self._get_average_queue_size()),
    "cpu_usage": "0.0",                      # 预留
    "memory_usage": "0",                     # 预留
    "total_events": str(self.total_event_count),
    "backpressure_count": str(self.backpressure_count),
    "dropped_events": str(self.dropped_event_count)
}

redis_client.hset(f"node:metrics:{self.node_id}", mapping=metrics)
```

### Redis CLI 查看

```bash
# 查看所有指标
127.0.0.1:6379> HGETALL node:metrics:my_node_1
{
  "portfolio_count": "3",
  "queue_size": "15",
  "cpu_usage": "0.0",
  "memory_usage": "0",
  "total_events": "15000",
  "backpressure_count": "5",
  "dropped_events": "2"
}

# 查看单个指标
127.0.0.1:6379> HGET node:metrics:my_node_1 portfolio_count
"3"

# 查看所有指标键
127.0.0.1:6379> KEYS node:metrics:*
1) "node:metrics:node_1"
2) "node:metrics:node_2"
3) "node:metrics:node_3"
```

---

## 指标详细说明

### portfolio_count
```python
"portfolio_count": str(len(self.portfolios))
```
- **含义**：当前加载的 Portfolio 数量
- **用途**：Scheduler 用于负载均衡决策
- **范围**：0 ~ max_portfolios（默认5）

### queue_size
```python
"queue_size": str(self._get_average_queue_size())
```
- **含义**：所有 Portfolio 的平均队列大小
- **用途**：检测节点负载，背压预警
- **计算**：所有 Portfolio 队列大小之和 / Portfolio 数量

### cpu_usage
```python
"cpu_usage": "0.0"  # 预留
```
- **含义**：CPU 使用率（百分比）
- **状态**：⏳ 预留，未来实现
- **计划**：使用 psutil 库获取实际 CPU 使用率

### memory_usage
```python
"memory_usage": "0"  # 预留
```
- **含义**：内存使用量（MB）
- **状态**：⏳ 预留，未来实现
- **计划**：使用 psutil 库获取实际内存使用

### total_events
```python
"total_events": str(self.total_event_count)
```
- **含义**：自启动以来处理的累计事件数
- **更新**：每次处理事件时递增
- **用途**：监控节点工作量

### backpressure_count
```python
"backpressure_count": str(self.backpressure_count)
```
- **含义**：背压发生的累计次数
- **触发**：当队列满时触发背压
- **用途**：评估节点性能瓶颈

### dropped_events
```python
"dropped_events": str(self.dropped_event_count)
```
- **含义**：丢弃事件的累计数量
- **触发**：背压无法缓解时丢弃事件
- **用途**：监控数据丢失情况

---

## 使用场景

### Scheduler 发现节点

```python
# Scheduler 扫描所有心跳键
heartbeat_keys = redis_client.keys("heartbeat:node:*")

for key in heartbeat_keys:
    node_id = key.replace("heartbeat:node:", "")

    # 检查 TTL（心跳新鲜度）
    ttl = redis_client.ttl(key)
    if ttl > 0:
        # 节点在线
        metrics = redis_client.hgetall(f"node:metrics:{node_id}")
        portfolio_count = metrics.get(b'portfolio_count', b'0')
        print(f"节点 {node_id}: 在线, Portfolio数={portfolio_count}")
```

### CLI 显示节点状态

```bash
$ ginkgo scheduler nodes

                            🖥 ExecutionNode Status
┏━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━━┳━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
┃ Node ID               ┃ Portfolios ┃ Queue Size ┃ CPU Usage ┃ Last Heartbeat ┃
┡━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━━╇━━━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
│ test_node_1           │          3 │         15 │      0.0% │ 25s ago        │
│ test_node_2           │          2 │         10 │      0.0% │ 18s ago        │
└───────────────────────┴────────────┴────────────┴───────────┴────────────────┘
```

### 负载均衡决策

```python
# Scheduler 根据指标选择节点

def select_node_for_portfolio(healthy_nodes):
    # 选择 portfolio_count 最少的节点
    min_count = float('inf')
    selected_node = None

    for node in healthy_nodes:
        count = int(node['metrics']['portfolio_count'])
        if count < min_count:
            min_count = count
            selected_node = node['node_id']

    return selected_node
```

---

## 心跳时间线

```
T=0s:   ExecutionNode 启动
        ↓
        立即发送第1次心跳
        heartbeat:node:xxx = "2026-01-06T12:00:00" (TTL=30)

T=10s:  心跳线程第1次循环
        ↓
        发送第2次心跳
        heartbeat:node:xxx = "2026-01-06T12:00:10" (TTL=30)

T=20s:  心跳线程第2次循环
        ↓
        发送第3次心跳
        heartbeat:node:xxx = "2026-01-06T12:00:20" (TTL=30)

T=30s:  心跳线程第3次循环
        ↓
        发送第4次心跳
        heartbeat:node:xxx = "2026-01-06T12:00:30" (TTL=30)

...

如果节点停止：
        不再发送心跳
        ↓
T=X+30s: TTL 过期，键自动删除
        ↓
        Scheduler 检测到离线
```

---

## 调试和监控

### 查看所有心跳

```bash
# 查看所有心跳键
redis-cli KEYS "heartbeat:node:*"

# 查看所有节点的心跳时间
for key in $(redis-cli KEYS "heartbeat:node:*"); do
    echo "$key: $(redis-cli GET $key)"
done
```

### 查看所有指标

```bash
# 查看所有指标键
redis-cli KEYS "node:metrics:*"

# 查看特定节点的所有指标
redis-cli HGETALL "node:metrics:test_node_1"
```

### 实时监控脚本

```python
import time
from ginkgo.data.crud import RedisCRUD

def monitor_nodes():
    redis_crud = RedisCRUD()
    redis_client = redis_crud.redis

    while True:
        print("\n" + "="*70)
        print("  ExecutionNode 监控面板")
        print("="*70)

        # 获取所有心跳
        heartbeat_keys = redis_client.keys("heartbeat:node:*")

        if not heartbeat_keys:
            print("⚠️  没有在线节点")
        else:
            for key in heartbeat_keys:
                node_id = key.decode('utf-8').replace("heartbeat:node:", "")

                # 心跳时间
                heartbeat_value = redis_client.get(key).decode('utf-8')
                ttl = redis_client.ttl(key)

                # 节点指标
                metrics_key = f"node:metrics:{node_id}"
                metrics = redis_client.hgetall(metrics_key)

                if metrics:
                    portfolio_count = metrics.get(b'portfolio_count', b'0').decode('utf-8')
                    queue_size = metrics.get(b'queue_size', b'0').decode('utf-8')
                else:
                    portfolio_count = "0"
                    queue_size = "0"

                print(f"\n📊 节点: {node_id}")
                print(f"   💓 心跳: {heartbeat_value} (TTL: {ttl}s)")
                print(f"   📦 Portfolio: {portfolio_count}")
                print(f"   📋 队列: {queue_size}")

        time.sleep(5)  # 每5秒刷新
```

---

## 总结

### 心跳上报的信息

| 信息类型 | Redis 键 | 数据类型 | 频率 | 用途 |
|---------|---------|---------|------|------|
| **心跳** | `heartbeat:node:{id}` | String + TTL | 每10秒 | 存活证明 |
| **指标** | `node:metrics:{id}` | Hash | 每10秒 | 性能监控 |

### 核心指标

```
✅ 实时指标（当前使用）：
   - portfolio_count: Portfolio 数量
   - queue_size: 队列大小
   - total_events: 总事件数
   - backpressure_count: 背压次数
   - dropped_events: 丢弃事件数

⏳ 预留指标（未来实现）：
   - cpu_usage: CPU 使用率
   - memory_usage: 内存使用
```

### 特点

- ✅ **简单**：只有2个键，1个心跳 + 1个指标
- ✅ **高效**：每10秒更新一次
- ✅ **可靠**：Redis TTL 自动处理离线
- ✅ **完整**：涵盖节点状态的关键指标
