# ExecutionNode 启动逻辑详解（简化版）

## 概述

ExecutionNode 的启动逻辑非常简单：**启动时立即发送一次心跳**，让 Scheduler 可以立即发现节点。

---

## 核心逻辑

### 启动流程

```python
ExecutionNode(node_id="my_node")
    ↓
node.start()
    ↓
① 设置 is_running = True
② 记录启动时间 started_at
③ 【立即】_send_heartbeat()          ← 关键！
④ 启动心跳线程（每10秒发送一次）
⑤ 启动调度更新订阅线程
```

### 立即发送心跳

```python
def start(self):
    self.is_running = True
    self.started_at = datetime.now().isoformat()

    # 立即发送一次心跳（让 Scheduler 立即发现节点）
    self._send_heartbeat()  # ← 关键！

    # 启动心跳线程（后续每10秒发送一次）
    self._start_heartbeat_thread()
```

---

## 发现机制

### ExecutionNode 端

```
启动时立即：
    _send_heartbeat()
        ↓
    redis_client.setex(
        f"heartbeat:node:{node_id}",
        ttl=30,
        value=datetime.now().isoformat()
    )
        ↓
    Scheduler 立即可发现节点！

启动后持续：
    心跳线程每10秒执行：
        _send_heartbeat()
        _update_node_metrics()
```

### Scheduler 端

```python
def _get_healthy_nodes(self):
    # 扫描所有心跳键
    heartbeat_keys = redis_client.keys("heartbeat:node:*")

    for key in heartbeat_keys:
        node_id = key.replace("heartbeat:node:", "")
        metrics = _get_node_metrics(node_id)
        # 节点在线！
```

---

## 时间线对比

### 之前（延迟发现）

```
T=0s:   ExecutionNode 启动
        ↓
T=10s:  第1次心跳 ← 延迟！
        ↓
        Scheduler 可以发现
```

### 现在（立即发现）

```
T=0s:   ExecutionNode 启动
        ↓
        立即发送心跳 ← 0秒延迟！
        ↓
        Scheduler 立即可以发现
T=10s:  第2次心跳（心跳线程第1次）
```

---

## 停止流程

```python
node.stop()
    ↓
① 设置 is_running = False
② 停止心跳线程（不再发送心跳）
③ 停止所有 PortfolioProcessor
④ 停止消费线程
⑤ 关闭 Kafka 连接
    ↓
心跳不再发送，30秒后TTL过期
    ↓
Scheduler 检测到节点离线
```

---

## Redis 键结构

### 唯一的键：心跳

| 键 | 类型 | TTL | 说明 |
|---|------|-----|------|
| `heartbeat:node:{node_id}` | String | 30秒 | 节点心跳 |

### 节点指标（由心跳线程维护）

| 键 | 类型 | TTL | 说明 |
|---|------|-----|------|
| `node:metrics:{node_id}` | Hash | 无 | 性能指标 |

---

## 简化优势

### ✅ 之前（自我注册）
- 需要 `node:info:{node_id}`（基本信息）
- 需要 `node:capabilities:{node_id}`（能力信息）
- 需要 `heartbeat:node:{node_id}`（心跳）
- 需要 `node:metrics:{node_id}`（指标）
- 启动时注册，停止时注销
- **复杂**：4个键，两套逻辑

### ✅ 现在（只有心跳）
- 只需要 `heartbeat:node:{node_id}`（心跳）
- `node:metrics:{node_id}`（指标，可选）
- **简单**：1-2个键，一套逻辑
- 启动时立即发送，停止时自然过期

---

## 关键要点

### 1. 启动时立即发送心跳
```python
def start(self):
    self._send_heartbeat()  # ← 立即发送！
    self._start_heartbeat_thread()  # 后续每10秒
```

### 2. 停止时无需注销
```python
def stop(self):
    self.is_running = False  # 停止心跳线程
    # 心跳不再发送
    # 30秒后TTL自动过期
    # Scheduler自动检测到离线
```

### 3. 心跳既是发现机制也是存活证明
- **发现**：Scheduler 通过扫描心跳键发现节点
- **存活**：心跳持续更新 = 节点在线
- **离线**：心跳过期 = 节点离线

---

## 总结

**ExecutionNode 启动逻辑核心**：
1. 启动时立即发送心跳（0秒延迟）
2. 心跳线程每10秒维持心跳
3. 停止时心跳自然过期（无需注销）

**Scheduler 发现逻辑**：
1. 扫描 `heartbeat:node:*` 键
2. 键存在 = 节点在线
3. 键不存在 = 节点离线

**简单、可靠、高效**！
