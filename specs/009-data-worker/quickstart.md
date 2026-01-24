# Data Worker - Quick Start Guide

**Feature**: 009-data-worker
**Date**: 2025-01-23
**Status**: Phase 1 Design

## 概述

Data Worker是Ginkgo量化交易系统的数据采集微服务，以容器方式部署，通过Kafka接收控制命令，从外部数据源获取市场数据并写入ClickHouse。

---

## 前置条件

- Docker 和 Docker Compose 已安装
- Kafka 集群正常运行
- Redis 集群正常运行
- ClickHouse 数据库已初始化
- 数据源API密钥已配置（如Tushare Token）

---

## 5分钟快速开始

### 1. 配置数据源

创建或编辑 `~/.ginkgo/data_worker.yml`:

```yaml
# 数据源配置
data_source:
  source_type: tushare  # 支持: tushare, yahoo, akshare, baostock, tdx
  api_token: ${TUSHARE_TOKEN}  # 从环境变量读取
  rate_limit:
    requests_per_minute: 200
    backoff_factor: 2
  enabled: true

# 日志配置
logging:
  level: INFO  # DEBUG, INFO, WARNING, ERROR
  file: /ginkgo/.logs/dataworker.log

# Worker配置
worker:
  heartbeat_interval: 10  # 心跳间隔（秒）
  heartbeat_ttl: 30       # 心跳TTL（秒）
  batch_size: 1000        # ClickHouse批量写入大小
  retry_attempts: 3       # 失败重试次数
```

### 2. 设置环境变量

```bash
# Kafka连接
export GINKGO_KAFKA_HOST=kafka1
export GINKGO_KAFKA_PORT=9092

# Redis连接（心跳存储）
export GINKGO_REDIS_HOST=redis-master
export GINKGO_REDIS_PORT=6379

# ClickHouse连接（数据写入）
export GINKGO_CLICKHOUSE_HOST=clickhouse-test
export GINKGO_CLICKHOUSE_PORT=8123
export GINKGO_CLICKHOUSE_USER=default
export GINKGO_CLICKHOUSE_PASSWORD=""
export GINKGO_CLICKHOUSE_DATABASE=ginkgo

# 数据源密钥
export TUSHARE_TOKEN=your_token_here

# Worker配置
export WORKER_GROUP_ID=data_worker_group
export LOG_LEVEL=INFO
```

### 3. 启动Data Worker

```bash
# 方式1: 使用Docker Compose（推荐）
cd /home/kaoru/Ginkgo
docker-compose up -d data-worker

# 方式2: 使用CLI命令
ginkgo data-worker start

# 方式3: 直接运行Python
python -m ginkgo.livecore.data_worker
```

### 4. 验证运行状态

```bash
# 检查容器状态
docker-compose ps data-worker

# 查看日志
docker-compose logs -f data-worker

# 检查Redis心跳
redis-cli GET "heartbeat:data_worker:data-worker-1"

# 检查Kafka消费组
kafka-consumer-groups.sh --bootstrap-server localhost:9092 \
  --group data_worker_group --describe
```

### 5. 发送测试命令

```bash
# 方式1: 使用CLI
ginkgo tasktimer run bar_snapshot --codes 000001.SZ --start 20250101 --end 20250123

# 方式2: 使用Kafka生产者
kafka-console-producer.sh --bootstrap-server localhost:9092 \
  --topic ginkgo.live.control.commands

# 然后输入JSON消息
{
    "command": "bar_snapshot",
    "timestamp": "2025-01-23T15:30:00Z",
    "request_id": "550e8400-e29b-41d4-a716-446655440000",
    "params": {
        "codes": ["000001.SZ"],
        "start_date": "20250101",
        "end_date": "20250123",
        "frequency": "1d"
    }
}
```

---

## 扩容操作

### 调整Worker实例数

```bash
# 扩展到4个实例
docker-compose up -d --scale data-worker=4

# 缩减到2个实例
docker-compose up -d --scale data-worker=2

# 查看当前实例数
docker-compose ps data-worker
```

Kafka consumer group会自动分配分区给各个实例，无需额外配置。

---

## 配置热重载

修改配置文件后，发送reload命令：

```bash
# 方式1: 发送Kafka消息
{
    "command": "reload",
    "timestamp": "2025-01-23T10:00:00Z",
    "request_id": "...",
    "params": {}
}

# 方式2: 使用CLI（如果实现）
ginkgo data-worker reload
```

Worker会重新加载配置文件，无需重启容器。

---

## 监控和告警

### 查看Worker状态

```bash
# Redis心跳
redis-cli KEYS "heartbeat:data_worker:*"

# 解析心跳数据
redis-cli GET "heartbeat:data_worker:data-worker-1" | jq

# 输出示例
{
    "timestamp": "2025-01-23T10:30:00",
    "component_type": "data_worker",
    "component_id": "data-worker-1",
    "host": "ginkgo-server",
    "pid": 12345,
    "status": {
        "code": 2,
        "name": "RUNNING"
    },
    "stats": {
        "messages_processed": 1523,
        "messages_failed": 2,
        "bars_collected": 45600,
        "bars_written": 45598
    }
}
```

### 数据质量报告

Data Worker会向 `ginkgo.notifications` 主题发送数据质量报告：

```bash
# 消费通知消息
kafka-console-consumer.sh --bootstrap-server localhost:9092 \
  --topic ginkgo.notifications --from-beginning

# 报告示例
{
    "type": "data_quality_report",
    "timestamp": "2025-01-23T15:35:00Z",
    "source": "data_worker_1",
    "data": {
        "report_id": "uuid-v4",
        "task_type": "bar_snapshot",
        "records_expected": 1000,
        "records_actual": 998,
        "success_rate": 0.998,
        "duration_seconds": 45.2
    }
}
```

---

## 故障排查

### Worker无法启动

```bash
# 检查日志
docker-compose logs data-worker

# 常见问题:
# 1. Kafka连接失败 → 检查GINKGO_KAFKA_HOST/PORT
# 2. Redis连接失败 → 检查GINKGO_REDIS_HOST/PORT
# 3. 配置文件格式错误 → 检查YAML语法
# 4. API Token无效 → 检查环境变量
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
docker-compose logs -f data-worker | grep ERROR
```

### 数据未写入ClickHouse

```bash
# 检查ClickHouse连接
curl "http://localhost:8123/ping"

# 检查表是否存在
curl "http://localhost:8123/?query=SHOW%20TABLES"

# 检查Worker日志中的写入错误
docker-compose logs data-worker | grep "Failed to write"
```

---

## 常用命令

```bash
# 启动
docker-compose up -d data-worker
ginkgo data-worker start

# 停止
docker-compose stop data-worker
ginkgo data-worker stop

# 重启
docker-compose restart data-worker
ginkgo data-worker restart

# 查看状态
docker-compose ps data-worker
ginkgo data-worker status

# 查看日志
docker-compose logs -f data-worker
ginkgo data-worker logs

# 扩容
docker-compose up -d --scale data-worker=4

# 缩容
docker-compose up -d --scale data-worker=1
```

---

## 下一步

- 阅读完整API文档: `docs/data_worker_api.md`
- 查看架构设计: `specs/009-data-worker/research.md`
- 了解数据模型: `specs/009-data-worker/data-model.md`
- 配置监控告警: `docs/monitoring_setup.md`
