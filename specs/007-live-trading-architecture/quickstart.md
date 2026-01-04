# Quickstart Guide: 实盘多Portfolio架构支持

**Feature**: 007-live-trading-architecture
**Date**: 2026-01-04
**Version**: 1.0.0

本文档提供实盘交易系统的快速开始指南，包括部署、配置和使用示例。

---

## 前置条件

### 软件依赖

| 软件 | 版本要求 | 用途 |
|------|---------|------|
| **Python** | 3.12.8+ | 主要开发语言 |
| **MySQL** | 8.0+ | Portfolio配置存储 |
| **ClickHouse** | 23.0+ | 时序数据存储 |
| **Redis** | 7.0+ | 状态存储和缓存 |
| **MongoDB** | 4.4+ | 通知记录存储 |
| **Kafka** | 2.8+ | 消息总线 |
| **ZooKeeper** | 3.6+ | Kafka依赖 |

### Python依赖

```bash
# 安装Ginkgo核心依赖
pip install -e .

# 实盘交易额外依赖
pip install kafka-python redis-py pymongo clickhouse-driver
```

---

## 快速开始（5分钟）

### 1. 启动基础设施服务

使用Docker Compose快速启动所有服务：

```bash
# 启动所有基础设施服务
cd deployments/docker
docker-compose up -d

# 验证服务状态
docker-compose ps
```

服务包括：
- MySQL (port 3306)
- ClickHouse (port 8123)
- Redis (port 6379)
- MongoDB (port 27017)
- Kafka (port 9092)
- ZooKeeper (port 2181)

---

### 2. 初始化数据库

```bash
# 启用调试模式（数据库操作必须）
ginkgo system config set --debug on

# 初始化所有数据库
ginkgo data init

# 验证数据库连接
ginkgo mongo status
ginkgo mysql status
ginkgo clickhouse status
ginkgo redis status
```

---

### 3. 创建第一个Portfolio

使用Python API创建Portfolio：

```python
from ginkgo import services
from ginkgo.data.models import MPortfolio
from datetime import datetime

# 获取Portfolio CRUD
portfolio_crud = services.trading.cruds.portfolio()

# 创建Portfolio配置
portfolio = MPortfolio(
    name="My First Live Portfolio",
    user_id="user_uuid",
    initial_cash=100000.00,
    status="created",
    config={
        "strategy": {
            "strategy_id": "trend_follow_strategy_uuid",
            "name": "TrendFollowStrategy",
            "params": {
                "short_period": 5,
                "long_period": 20
            }
        },
        "risk_managements": [
            {
                "risk_id": "position_ratio_risk_uuid",
                "name": "PositionRatioRisk",
                "params": {
                    "max_position_ratio": 0.2,
                    "max_total_position_ratio": 0.8
                }
            },
            {
                "risk_id": "loss_limit_risk_uuid",
                "name": "LossLimitRisk",
                "params": {
                    "loss_limit": 10.0
                }
            }
        ],
        "sizer": {
            "sizer_id": "fixed_amount_sizer_uuid",
            "name": "FixedAmountSizer",
            "params": {
                "amount": 10000
            }
        }
    },
    created_at=datetime.now()
)

# 保存到数据库
portfolio_id = portfolio_crud.add_portfolio(portfolio)
print(f"Portfolio created: {portfolio_id}")
```

或者使用CLI：

```bash
ginkgo portfolio create \
  --name "My First Live Portfolio" \
  --user-id user_uuid \
  --initial-cash 100000 \
  --strategy-id trend_follow_strategy_uuid \
  --risk-id position_ratio_risk_uuid \
  --sizer-id fixed_amount_sizer_uuid
```

---

### 4. 启动ExecutionNode

**方式一：开发调试模式（CLI前台运行）**

```bash
# 在前台启动ExecutionNode（用于开发调试）
ginkgo worker start --type execution_node \
  --node-id execution_node_001 \
  --max-portfolios 5 \
  --kafka-bootstrap-servers localhost:9092 \
  --redis-host localhost \
  --redis-port 6379
```

输出：
```
[INFO] Starting ExecutionNode: execution_node_001
[INFO] Connecting to Kafka: localhost:9092
[INFO] Connecting to Redis: localhost:6379
[INFO] Loading Portfolios from database...
[INFO] Found 1 Portfolio to load
[INFO] Starting Kafka consumer for topic: ginkgo.live.market.data
[INFO] Starting PortfolioProcessor threads...
[INFO] PortfolioProcessor-portfolio_uuid started
[INFO] ExecutionNode ready, processing events...
^C[INFO] Received SIGINT, gracefully stopping...
[INFO] Waiting for queues to drain...
[INFO] ExecutionNode stopped
```

**方式二：生产环境模式（Docker Compose）**

```bash
# 使用Docker Compose启动所有服务（包括ExecutionNode）
cd deployments/docker
docker-compose up -d

# 查看ExecutionNode日志
docker-compose logs -f execution_node_1

# 停止所有服务
docker-compose down
```

输出：
```
[INFO] Starting ExecutionNode: execution_node_001
[INFO] Connecting to Kafka: localhost:9092
[INFO] Connecting to Redis: localhost:6379
[INFO] Loading Portfolios from database...
[INFO] Found 1 Portfolio to load
[INFO] Starting Kafka consumer for topic: ginkgo.live.market.data
[INFO] Starting PortfolioProcessor threads...
[INFO] PortfolioProcessor-portfolio_uuid started
[INFO] ExecutionNode ready, processing events...
```

---

### 5. 启动LiveCore服务

```bash
# 启动LiveCore（Data + TradeGateway + LiveEngine + Scheduler）
ginkgo livecore start \
  --kafka-bootstrap-servers localhost:9092 \
  --redis-host localhost \
  --redis-port 6379 \
  --data-source tushare \
  --broker-type simulation
```

输出：
```
[INFO] Starting LiveCore services...
[INFO] Starting Data module...
[INFO] Subscribing to market data: Tushare
[INFO] Starting TradeGateway...
[INFO] Broker type: simulation
[INFO] Starting LiveEngine...
[INFO] Subscribing to Kafka topic: ginkgo.live.orders.submission
[INFO] Starting Scheduler...
[INFO] Scheduling interval: 30s
[INFO] LiveCore ready
```

---

### 6. 观察实盘运行

**开发调试模式（CLI前台运行）**：

ExecutionNode在前台运行时，日志实时输出到终端，可以直接观察：
```
[INFO] PortfolioProcessor-portfolio_uuid processing EventPriceUpdate: 000001.SZ @ 10.50
[INFO] Signal generated: BUY 000001.SZ, volume=1000
[INFO] Order submitted: order_uuid, BUY 000001.SZ, volume=1000
[INFO] Order filled: order_uuid, volume=1000, price=10.50
[INFO] Portfolio updated: cash=89500.00, position_value=10500.00
```

**生产环境模式（Docker Compose）**：

```bash
# 查看ExecutionNode实时日志
docker-compose logs -f execution_node_1

# 查询Portfolio状态（从数据库）
ginkgo portfolio status portfolio_uuid

# 查询Portfolio持仓
ginkgo portfolio positions portfolio_uuid

# 查询所有ExecutionNode状态（从Redis）
redis-cli
> KEYS execution_node:*:info
> HGETALL execution_node:execution_node_001:info
```

输出：
```
Portfolio: portfolio_uuid
Name: My First Live Portfolio
Status: running
Cash: 95000.00
Total Value: 150000.00
Position Count: 5
Node: execution_node_001
Last Update: 2026-01-04 10:00:00

Positions:
- 000001.SZ: LONG 1000 shares @ 10.00, current 10.50, P/L +500.00
- 000002.SZ: LONG 2000 shares @ 20.00, current 21.00, P/L +2000.00
...
```

---

## 配置指南

### 1. 数据库配置

编辑 `~/.ginkgo/config.yaml`:

```yaml
# MySQL配置
mysql:
  host: localhost
  port: 3306
  user: ginkgo
  password: ginkgo_password
  database: ginkgo

# ClickHouse配置
clickhouse:
  host: localhost
  port: 8123
  user: default
  password: ""
  database: ginkgo

# Redis配置
redis:
  host: localhost
  port: 6379
  db: 0
  password: ""

# MongoDB配置
mongodb:
  host: localhost
  port: 27017
  user: ""
  password: ""
  database: ginkgo

# Kafka配置
kafka:
  bootstrap_servers:
    - localhost:9092
  group_id: execution_node_group
  auto_offset_reset: earliest
  enable_auto_commit: false
```

---

### 2. 数据源配置

编辑 `~/.ginkgo/data_sources.yml`:

```yaml
sources:
  tushare:
    token: YOUR_TUSHARE_TOKEN
    pro_api: https://api.tushare.pro

  simulation:
    initial_prices:
      000001.SZ: 10.00
      000002.SZ: 20.00
```

---

### 3. 券商接口配置

编辑 `~/.ginkgo/brokers.yml`:

```yaml
brokers:
  simulation:
    type: simulation
    commission_rate: 0.0003
    slippage_rate: 0.001

  real_broker:
    type: real
    broker_name: your_broker
    api_key: YOUR_API_KEY
    api_secret: YOUR_API_SECRET
    password: YOUR_PASSWORD
```

---

## 使用场景

### 场景1: 更新Portfolio配置

```bash
# 更新策略参数
curl -X PUT http://localhost:8000/api/portfolio/portfolio_uuid \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "config": {
      "strategy": {
        "strategy_id": "trend_follow_strategy_uuid",
        "name": "TrendFollowStrategy",
        "params": {
          "short_period": 10,
          "long_period": 30
        }
      }
    }
  }'
```

响应：
```json
{
  "success": true,
  "portfolio_id": "portfolio_uuid",
  "status": "reloading",
  "updated_at": "2026-01-04T10:00:00Z",
  "message": "Portfolio config updated, reload initiated"
}
```

**内部流程**:
1. API Gateway更新MySQL（`updated_at`字段）
2. API Gateway发送Kafka消息到`ginkgo.live.control.commands`
3. ExecutionNode收到消息，触发优雅重启
4. 状态: RUNNING → STOPPING → RELOADING → RUNNING
5. 整个流程 < 30秒

---

### 场景2: 查询实时持仓

```python
from ginkgo import services

# 获取Portfolio CRUD
portfolio_crud = services.trading.cruds.portfolio()

# 查询Portfolio状态
status = portfolio_crud.get_portfolio_status(portfolio_id)
print(f"Cash: {status['cash']}")
print(f"Total Value: {status['total_value']}")

# 查询持仓
positions = portfolio_crud.get_portfolio_positions(portfolio_id)
for pos in positions:
    print(f"{pos.code}: {pos.direction} {pos.volume} @ {pos.cost_price}")
```

---

### 场景3: 手动迁移Portfolio

```bash
# 将Portfolio从Node-1迁移到Node-2
curl -X POST http://localhost:8000/api/schedule/migrate \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "portfolio_id": "portfolio_uuid",
    "source_node": "execution_node_001",
    "target_node": "execution_node_002"
  }'
```

响应：
```json
{
  "success": true,
  "portfolio_id": "portfolio_uuid",
  "status": "migrating",
  "source_node": "execution_node_001",
  "target_node": "execution_node_002",
  "estimated_time": 30
}
```

**内部流程**:
1. Scheduler发送MIGRATE_OUT命令到Node-1
2. Node-1优雅停止Portfolio（处理完Queue中消息）
3. Node-1保存Portfolio状态到数据库
4. Scheduler发送MIGRATE_IN命令到Node-2
5. Node-2从数据库加载Portfolio状态
6. Node-2创建Portfolio实例和线程
7. 总耗时 < 30秒

---

### 场景4: 监控系统告警

```bash
# 查询告警历史
curl -X GET "http://localhost:8000/api/alerts?start_time=1640000000&end_time=1640086400&limit=100" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

响应：
```json
{
  "alerts": [
    {
      "alert_id": "alert_uuid",
      "alert_type": "queue_full",
      "severity": "critical",
      "source": "execution_node_001",
      "message": "Portfolio portfolio_001 queue is 95% full",
      "details": {
        "portfolio_id": "portfolio_001",
        "queue_size": 950,
        "queue_max": 1000
      },
      "timestamp": "2026-01-04T10:00:00Z"
    }
  ],
  "total_count": 50
}
```

---

### 场景5: 高可用测试（模拟ExecutionNode上线下线）

使用CLI前台命令测试Scheduler心跳检测和Portfolio自动迁移功能。

**测试步骤**：

**1. 启动多个ExecutionNode**：

终端1：
```bash
# 启动ExecutionNode-1
ginkgo worker start --type execution_node --node-id test_node_001 \
  --kafka-bootstrap-servers localhost:9092 \
  --redis-host localhost
```

终端2：
```bash
# 启动ExecutionNode-2
ginkgo worker start --type execution_node --node-id test_node_002 \
  --kafka-bootstrap-servers localhost:9092 \
  --redis-host localhost
```

**2. 观察Scheduler检测到新Node**：

在两个终端中都能看到：
```
[INFO] Starting ExecutionNode: test_node_001
[INFO] Connecting to Kafka: localhost:9092
[INFO] Connecting to Redis: localhost:6379
[INFO] Starting heartbeat sender (interval: 10s)
[INFO] ExecutionNode ready
[INFO] Heartbeat sent to Redis: heartbeat:node:test_node_001
```

Scheduler日志会显示：
```
[INFO] Detected new ExecutionNode: test_node_001
[INFO] Detected new ExecutionNode: test_node_002
[INFO] Assigning Portfolios to available nodes...
```

**3. 模拟Node故障（Ctrl+C停止test_node_001）**：

在终端1按Ctrl+C：
```bash
^C[INFO] Received SIGINT, gracefully stopping...
[INFO] Waiting for queues to drain (0 messages remaining)
[INFO] Stopping heartbeat sender
[INFO] ExecutionNode stopped
```

**4. 观察Portfolio自动迁移**：

Scheduler日志会显示（心跳超时30秒后）：
```
[WARNING] ExecutionNode test_node_001 heartbeat timeout (30s)
[INFO] Triggering Portfolio migration from test_node_001 to test_node_002
[INFO] Portfolio portfolio_uuid migrated successfully
[INFO] Migration completed in 15.2s
```

**5. 验证迁移成功**：

在test_node_002终端可以看到：
```
[INFO] Received MIGRATE_IN command for portfolio: portfolio_uuid
[INFO] Loading Portfolio state from database
[INFO] PortfolioProcessor-portfolio_uuid started
[INFO] Portfolio is now running on test_node_002
```

**6. 重新启动test_node_001**：

```bash
# 重新启动test_node_001，验证Scheduler重新检测到它
ginkgo worker start --type execution_node --node-id test_node_001 \
  --kafka-bootstrap-servers localhost:9092 \
  --redis-host localhost
```

Scheduler日志：
```
[INFO] ExecutionNode test_node_001 is back online
[INFO] Rebalancing Portfolio assignments...
```

**验证要点**：
- [ ] Node上线后10秒内Scheduler检测到
- [ ] Node下线后30秒内Scheduler检测到
- [ ] Portfolio自动迁移到健康Node（< 60秒）
- [ ] 迁移过程中消息不丢失（暂存在Kafka）
- [ ] Node重新上线后Scheduler重新平衡负载

---

## 故障排查

### 问题1: ExecutionNode无法连接Kafka

**错误信息**:
```
[ERROR] Failed to connect to Kafka: No brokers available
```

**解决方案**:
```bash
# 检查Kafka服务状态
docker-compose ps kafka

# 检查Kafka日志
docker-compose logs kafka

# 验证Kafka连接
telnet localhost 9092
```

---

### 问题2: Portfolio状态未更新

**错误信息**:
```
[WARNING] Portfolio portfolio_uuid status not updated for 60s
```

**解决方案**:

**开发调试模式**：
- 检查前台运行的ExecutionNode日志输出
- 查看是否有错误信息或Kafka连接问题

**生产环境模式**：
```bash
# 检查ExecutionNode心跳
redis-cli
> GET heartbeat:node:execution_node_001

# 检查Portfolio状态
> GET portfolio:portfolio_uuid:state

# 检查ExecutionNode日志
docker-compose logs -f execution_node_1
```

---

### 问题3: Queue满导致消息丢弃

**错误信息**:
```
[CRITICAL] Portfolio portfolio_001 queue is 95% full, dropping messages
```

**解决方案**:
1. 增加Queue大小（配置`max_queue_size`）
2. 优化Portfolio处理速度（策略计算优化）
3. 增加ExecutionNode实例（负载分散）

---

## 性能优化

### 1. Kafka分区优化

```yaml
# 增加市场数据Topic分区数（提高并行度）
kafka:
  topics:
    ginkgo.live.market.data:
      partitions: 20  # 默认10，增加到20
      replication_factor: 3
```

---

### 2. Redis缓存优化

```python
# 启用Redis缓存
from ginkgo.libs.decorators import cache_with_expiration

@cache_with_expiration(60)
def get_portfolio_status(portfolio_id: str):
    # 缓存Portfolio状态60秒
    return portfolio_crud.get_portfolio_status(portfolio_id)
```

---

### 3. ClickHouse批量写入

```python
# 批量插入持仓记录（每100条或每10秒）
from ginkgo.libs.decorators import time_logger, retry

@time_logger
@retry(max_try=3)
def batch_insert_positions(positions: List[MPosition]):
    client.execute("INSERT INTO positions VALUES", positions)
```

---

## 生产环境部署

### 1. 使用Docker Compose

```yaml
# docker-compose.yml
version: '3.8'
services:
  api_gateway:
    image: ginkgo/api_gateway:latest
    ports:
      - "8000:8000"
    environment:
      - KAFKA_BOOTSTRAP_SERVERS=kafka:9092
      - REDIS_HOST=redis
      - MYSQL_HOST=mysql
    depends_on:
      - kafka
      - redis
      - mysql

  livecore:
    image: ginkgo/livecore:latest
    environment:
      - KAFKA_BOOTSTRAP_SERVERS=kafka:9092
      - REDIS_HOST=redis
    depends_on:
      - kafka
      - redis

  execution_node_1:
    image: ginkgo/execution_node:latest
    environment:
      - NODE_ID=execution_node_001
      - KAFKA_BOOTSTRAP_SERVERS=kafka:9092
      - REDIS_HOST=redis
    depends_on:
      - kafka
      - redis

  execution_node_2:
    image: ginkgo/execution_node:latest
    environment:
      - NODE_ID=execution_node_002
      - KAFKA_BOOTSTRAP_SERVERS=kafka:9092
      - REDIS_HOST=redis
    depends_on:
      - kafka
      - redis
```

启动：
```bash
docker-compose up -d
```

---

### 2. 使用Kubernetes

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: execution-node
spec:
  replicas: 10  # 10个ExecutionNode
  selector:
    matchLabels:
      app: execution-node
  template:
    metadata:
      labels:
        app: execution-node
    spec:
      containers:
      - name: execution-node
        image: ginkgo/execution_node:latest
        env:
        - name: NODE_ID
          valueFrom:
            fieldRef:
              fieldPath: metadata.name
        - name: KAFKA_BOOTSTRAP_SERVERS
          value: "kafka-service:9092"
        - name: REDIS_HOST
          value: "redis-service"
```

部署：
```bash
kubectl apply -f k8s/deployment.yaml
```

---

## 下一步

### 学习资源

1. **架构文档**: `/specs/007-live-trading-architecture/spec.md`
2. **信息流转**: `/specs/007-live-trading-architecture/information-flow.md`
3. **数据模型**: `/specs/007-live-trading-architecture/data-model.md`
4. **API契约**: `/specs/007-live-trading-architecture/contracts/`
5. **技术决策**: `/specs/007-live-trading-architecture/research.md`

### 高级主题

- **自定义策略**: 开发自己的交易策略
- **风控配置**: 配置多种风控模块
- **监控告警**: 集成Prometheus和Grafana
- **性能调优**: 优化系统性能和延迟

---

## 常见问题 (FAQ)

### Q1: 如何备份Portfolio数据？

```bash
# 导出Portfolio配置
ginkgo portfolio export portfolio_uuid --output portfolio_backup.json

# 导入Portfolio配置
ginkgo portfolio import portfolio_uuid --input portfolio_backup.json
```

### Q2: 如何回测实盘策略？

```bash
# 使用Portfolio配置进行回测
ginkgo backtest run \
  --portfolio-id portfolio_uuid \
  --start-date 2023-01-01 \
  --end-date 2023-12-31
```

### Q3: 如何停止所有实盘交易？

**开发调试模式**：
```bash
# 前台运行的ExecutionNode：按Ctrl+C优雅停止
# CLI会等待Queue清空后退出
```

**生产环境模式**：
```bash
# 停止LiveEngine（通过API）
curl -X POST http://localhost:8000/api/engine/live/stop \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"

# 停止所有ExecutionNode（Docker Compose）
cd deployments/docker
docker-compose down
```

---

## 总结

### 核心概念

1. **三大容器**: API Gateway + LiveCore + ExecutionNode
2. **Kafka通信**: 7个Topic，事件驱动架构
3. **无状态设计**: 所有状态持久化到数据库
4. **水平扩展**: ExecutionNode可扩展至10+实例

### 关键操作

1. **创建Portfolio**: 通过API或CLI
2. **启动ExecutionNode**: 运行Portfolio实例
3. **启动LiveCore**: 数据源 + 交易网关 + 引擎 + 调度
4. **监控状态**: 实时查询Portfolio和Node状态

### 性能目标

- **PriceUpdate → Signal**: < 200ms
- **配置变更切换**: < 30秒
- **故障恢复**: < 60秒

---

**恭喜！** 你已经完成了实盘交易系统的快速开始。现在可以开始创建自己的Portfolio并进行实盘交易了。

有问题？查看 `/specs/007-live-trading-architecture/` 目录下的详细文档。
