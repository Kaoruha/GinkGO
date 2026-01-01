# Notification Worker 使用指南

## 概述

NotificationWorker 是 Ginkgo 通知系统的 Kafka 消费者，负责从 `notifications` topic 消费消息并调用相应渠道（Discord Webhook、Email 等）发送通知。

## 快速开始

### 1. 启动 Worker

```bash
# 使用默认配置启动
python start_notification_worker.py

# 使用自定义 group_id 启动
python start_notification_worker.py --group-id my_worker_group

# 从最新的 offset 开始消费
python start_notification_worker.py --auto-offset latest

# 每 30 秒输出一次状态
python start_notification_worker.py --status-interval 30
```

### 2. 发送测试消息

```bash
# 发送 5 条 Webhook 测试消息
python send_test_notification.py --type webhook --count 5

# 发送 10 条交易信号
python send_test_notification.py --type trading --count 10

# 发送多渠道消息
python send_test_notification.py --type multi --count 3

# 快速发送（无间隔）
python send_test_notification.py --type webhook --count 100 --delay 0
```

## 命令行参数

### start_notification_worker.py

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--group-id` | Consumer Group ID | notification_worker_group |
| `--auto-offset` | Offset 重置策略 | earliest |
| `--status-interval` | 状态输出间隔（秒） | 60 |
| `--initial-delay` | 首次状态输出延迟（秒） | 5 |

### send_test_notification.py

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--type` | 消息类型 | webhook |
| `--count` | 发送数量 | 5 |
| `--delay` | 发送间隔（秒） | 1.0 |

消息类型：
- `webhook` - Webhook 通知（Discord）
- `email` - Email 通知
- `multi` - 多渠道通知
- `trading` - 交易信号通知
- `alert` - 系统告警通知

## 运行示例

### 场景1：单 Worker 测试

```bash
# 终端1：启动 Worker
python start_notification_worker.py

# 终端2：发送测试消息
python send_test_notification.py --type webhook --count 10
```

### 场景2：多 Worker 负载均衡

```bash
# 终端1：启动 Worker 1
python start_notification_worker.py --group-id prod_workers

# 终端2：启动 Worker 2
python start_notification_worker.py --group-id prod_workers

# 终端3：启动 Worker 3
python start_notification_worker.py --group-id prod_workers

# 终端4：发送消息（会自动负载均衡到3个 Worker）
python send_test_notification.py --type webhook --count 100
```

### 场景3：监控模式

```bash
# 每 10 秒输出一次状态
python start_notification_worker.py --status-interval 10
```

## Worker 状态说明

```
============================================================
  Worker Status Report - 2026-01-01 12:00:00
============================================================
  Status:           RUNNING
  Is Running:       True
  Group ID:         notification_worker_group
  Topic:            notifications
------------------------------------------------------------
  Messages Consumed:    1,234
  Messages Sent:        1,200
  Messages Failed:      30
  Messages Retried:     4
------------------------------------------------------------
  Uptime:            2h 15m 30s
  Last Message:      2026-01-01T12:00:00
  Success Rate:      97.2%
============================================================
```

| 指标 | 说明 |
|------|------|
| Messages Consumed | 从 Kafka 消费的消息总数 |
| Messages Sent | 全部渠道发送成功 |
| Messages Failed | 全部渠道发送失败 |
| Messages Retried | 重试次数 |
| Success Rate | 成功率 = Sent / Consumed |

## 信号处理

Worker 支持优雅关闭：

```bash
# Ctrl+C 或 SIGTERM
python start_notification_worker.py
^CReceived SIGINT, shutting down gracefully...
Stopping worker...
Worker stopped successfully in 1.23s
```

## 故障排查

### Worker 无法启动

```bash
# 1. 检查 Kafka 是否运行
docker ps | grep kafka

# 2. 检查配置
ginkgo system config show

# 3. 启用调试模式
ginkgo system config set --debug on
```

### 消息发送失败

```bash
# 1. 检查 Kafka 可用性
python -c "from ginkgo.notifier.core.message_queue import MessageQueue; print(MessageQueue().is_available)"

# 2. 查看 Worker 日志
# Worker 会输出详细的错误信息
```

### 消息未被消费

```bash
# 1. 检查 Worker 是否运行
# 查看状态输出中的 "Is Running"

# 2. 检查 Group ID 是否匹配
# Worker 和 Producer 应该使用不同的 Group ID

# 3. 检查 Topic 是否存在
# 如果 auto_offset_reset=latest，不会消费旧消息
```

## 性能优化

### 提高吞吐量

1. **增加 Worker 实例**（推荐）
   ```bash
   # 启动多个 Worker 负载均衡
   python start_notification_worker.py --group-id workers &
   python start_notification_worker.py --group-id workers &
   python start_notification_worker.py --group-id workers &
   ```

2. **调整批量大小**
   修改 `notification_worker.py` 中的 `max_poll_records`

3. **减少状态输出频率**
   ```bash
   python start_notification_worker.py --status-interval 300
   ```

## 配置文件

Worker 使用 `~/.ginkgo/config.yaml` 中的 Kafka 配置：

```yaml
kafka:
  host: localhost
  port: 9092
```

## 日志

Worker 日志输出到：
- 控制台（实时）
- Ginkgo 日志系统（可配置文件输出）

启用详细日志：
```bash
ginkgo system config set --debug on
```

## 监控集成

### Prometheus 指标

Worker 的统计信息可以导出为 Prometheus 指标：

```python
stats = worker.stats
# metrics.gauge('ginkgo_worker_messages_consumed', stats['messages_consumed'])
# metrics.gauge('ginkgo_worker_messages_sent', stats['messages_sent'])
```

### 健康检查

```python
health = worker.get_health_status()
if not health['is_running']:
    alert("Worker is down!")
```

## 最佳实践

1. **生产环境**
   - 使用 Supervisor 或 systemd 管理 Worker 进程
   - 配置自动重启
   - 使用独立的 Group ID 隔离环境

2. **开发环境**
   - 使用 `--auto-offset latest` 只消费新消息
   - 减少状态输出频率
   - 使用小批量测试

3. **监控告警**
   - 监控 Success Rate（应 > 95%）
   - 监控 Messages Retried（重试过多表示有问题）
   - 监控 Worker 运行状态

## 相关文件

- `src/ginkgo/notifier/workers/notification_worker.py` - Worker 实现
- `src/ginkgo/notifier/core/message_queue.py` - 消息队列
- `tests/unit/notifier/workers/` - 单元测试
- `tests/integration/notifier/` - 集成测试

## 获取帮助

```bash
python start_notification_worker.py --help
python send_test_notification.py --help
```
