# Data Worker - Quick Start Guide

**Feature**: 009-data-worker
**Date**: 2025-01-23
**Status**: Implementation Complete

## 概述

Data Worker是Ginkgo量化交易系统的数据采集微服务，以容器方式部署，通过Kafka接收控制命令，从外部数据源获取市场数据并写入ClickHouse。

**架构模式**: 容器即进程，每个容器运行一个Worker实例，通过Kafka consumer group实现负载均衡。

---

## 前置条件

- Docker 和 Docker Compose 已安装
- Kafka 集群正常运行
- Redis 集群正常运行
- ClickHouse 数据库已初始化
- 数据源API密钥已配置（如Tushare Token）

---

## 5分钟快速开始

### 1. 启动Data Worker

```bash
# 方式1: 使用Docker Compose（推荐）
cd /home/kaoru/Ginkgo
docker-compose -f .conf/docker-compose.yml -p ginkgo up -d data-worker

# 方式2: 使用CLI命令
ginkgo worker start --data

# 方式3: 使用CLI with debug模式
ginkgo worker start --data --debug
```

### 2. 验证运行状态

```bash
# 检查容器状态
docker-compose -f .conf/docker-compose.yml -p ginkgo ps data-worker

# 查看日志
docker-compose -f .conf/docker-compose.yml -p ginkgo logs -f data-worker

# 检查Redis心跳
redis-cli KEYS "heartbeat:data_worker:*"
redis-cli GET "heartbeat:data_worker:data_worker_12345" | jq

# 检查Kafka消费组
kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
  --group data_worker_group --describe
```

### 3. 发送测试命令

```bash
# 使用Kafka生产者发送控制命令
kafka-console-producer.sh --bootstrap-server localhost:9092 \
  --topic ginkgo.live.control.commands

# 发送bar_snapshot命令（K线快照采集）
{
    "command": "bar_snapshot",
    "source": "tasktimer",
    "timestamp": "2025-01-23T15:30:00Z",
    "params": {
        "code": "000001.SZ",
        "force": false,
        "full": false
    }
}

# 发送heartbeat_test命令（心跳测试）
{
    "command": "heartbeat_test",
    "source": "manual",
    "timestamp": "2025-01-23T15:30:00Z",
    "params": {}
}
```

---

## 扩容操作

### 调整Worker实例数

```bash
# 扩展到4个实例
docker-compose -f .conf/docker-compose.yml -p ginkgo up -d --scale data-worker=4

# 缩减到2个实例
docker-compose -f .conf/docker-compose.yml -p ginkgo up -d --scale data-worker=2

# 查看当前实例数
docker-compose -f .conf/docker-compose.yml -p ginkgo ps data-worker
```

Kafka consumer group会自动分配分区给各个实例，无需额外配置。

---

## 控制命令格式

Data Worker订阅 `ginkgo.live.control.commands` 主题，支持以下命令：

### bar_snapshot - K线快照采集

```json
{
    "command": "bar_snapshot",
    "source": "tasktimer",
    "timestamp": "2025-01-23T15:30:00Z",
    "params": {
        "code": "000001.SZ",
        "force": false,
        "full": false
    }
}
```

**参数说明**:
- `code`: 股票代码（如 000001.SZ）
- `force`: 是否强制覆盖（true=全量重新获取，false=智能增量）
- `full`: 是否全量同步（true=从上市日期开始，false=增量同步）

### update_data - 更新数据

```json
{
    "command": "update_data",
    "source": "tasktimer",
    "timestamp": "2025-01-23T15:30:00Z",
    "params": {
        "code": "000001.SZ",
        "force": false,
        "full": false
    }
}
```

### update_selector - 更新选股器

```json
{
    "command": "update_selector",
    "source": "execution_node",
    "timestamp": "2025-01-23T15:30:00Z",
    "params": {}
}
```

### heartbeat_test - 心跳测试

```json
{
    "command": "heartbeat_test",
    "source": "manual",
    "timestamp": "2025-01-23T15:30:00Z",
    "params": {}
}
```

---

## 监控和告警

### 查看Worker状态

```bash
# Redis心跳键格式: heartbeat:data_worker:{node_id}
redis-cli KEYS "heartbeat:data_worker:*"

# 解析心跳数据
redis-cli GET "heartbeat:data_worker:data_worker_12345" | jq

# 输出示例
{
    "node_id": "data_worker_12345",
    "status": "WORKER_STATUS_TYPES.RUNNING",
    "timestamp": "2025-01-23T10:30:00.123456",
    "stats": {
        "messages_processed": 1523,
        "bars_written": 45600,
        "errors": 2,
        "last_heartbeat": 1705980600.123
    }
}
```

### Docker健康检查

```bash
# 检查容器健康状态
docker inspect --format='{{.State.Health.Status}}' ginkgo-data-worker-1

# 手动触发健康检查
docker exec ginkgo-data-worker-1 python -c "
from ginkgo.data.worker.worker import DataWorker
print('Worker is healthy')
"
```

---

## 故障排查

### Worker无法启动

```bash
# 检查日志
docker-compose -f .conf/docker-compose.yml -p ginkgo logs data-worker

# 常见问题:
# 1. Kafka连接失败 → 检查GINKGO_KAFKA_HOST/PORT环境变量
# 2. Redis连接失败 → 检查GINKGO_REDIS_HOST/PORT环境变量
# 3. ClickHouse连接失败 → 检查GINKGO_CLICKHOUSE_HOST/PORT环境变量
```

### Worker没有处理消息

```bash
# 检查Kafka消费组状态
kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
  --group data_worker_group --describe

# 检查topic分区
kafka-topics.sh --bootstrap-server localhost:9092 \
  --topic ginkgo.live.control.commands --describe

# 检查Worker日志是否有错误
docker-compose -f .conf/docker-compose.yml -p ginkgo logs -f data-worker | grep ERROR
```

### 数据未写入ClickHouse

```bash
# 检查ClickHouse连接
curl "http://localhost:8123/ping"

# 检查表是否存在
curl "http://localhost:8123/?query=SHOW%20TABLES"

# 查询K线数据
curl "http://localhost:8123/?query=SELECT%20count()%20FROM%20ginkgo.bars"
```

---

## 常用命令

```bash
# 启动
docker-compose -f .conf/docker-compose.yml -p ginkgo up -d data-worker
ginkgo worker start --data

# 停止
docker-compose -f .conf/docker-compose.yml -p ginkgo stop data-worker
# (Ctrl+C in CLI mode)

# 重启
docker-compose -f .conf/docker-compose.yml -p ginkgo restart data-worker

# 查看状态
docker-compose -f .conf/docker-compose.yml -p ginkgo ps data-worker

# 查看日志
docker-compose -f .conf/docker-compose.yml -p ginkgo logs -f data-worker

# 扩容到4实例
docker-compose -f .conf/docker-compose.yml -p ginkgo up -d --scale data-worker=4

# 缩容到1实例
docker-compose -f .conf/docker-compose.yml -p ginkgo up -d --scale data-worker=1
```

---

## CLI选项

```bash
# 启动data worker
ginkgo worker start --data

# 指定consumer group
ginkgo worker start --data --group-id custom_group

# 指定auto offset策略
ginkgo worker start --data --auto-offset latest

# 启用debug模式（详细日志）
ginkgo worker start --data --debug
```

---

## 架构说明

### 数据流向

```
TaskTimer → Kafka (ginkgo.live.control.commands) → DataWorker → bar_service → ClickHouse
                                                         ↓
                                                      Redis (heartbeat)
```

### Worker状态机

```
STOPPED → STARTING → RUNNING → STOPPING → STOPPED
                   ↓
                  ERROR
```

### 心跳机制

- **键格式**: `heartbeat:data_worker:{node_id}`
- **TTL**: 30秒
- **间隔**: 10秒
- **内容**: node_id, status, timestamp, stats

---

## 下一步

- 查看架构设计: `.specify/specs/009-default/plan.md`
- 查看实现任务: `.specify/specs/009-default/tasks.md`
- 查看源码: `src/ginkgo/data/worker/worker.py`
