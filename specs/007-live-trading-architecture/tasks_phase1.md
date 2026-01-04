# Phase 1: Setup (项目初始化)

**状态**: ⚪ 未开始
**开始日期**: 待定
**预计完成**: 待定
**负责人**: 待定
**任务总数**: 8

---

## 📋 验收标准

- [ ] 所有依赖库已安装（kafka-python, redis-py, pymongo, clickhouse-driver, fastapi, uvicorn）
- [ ] Kafka集群可以连接并创建topic
- [ ] MySQL/ClickHouse/Redis/MongoDB数据库可以连接
- [ ] 项目结构已创建（workers/execution_node/, livecore/）

---

## 🎯 活跃任务 (最多5个)

> 根据Constitution任务管理原则，从下面的任务池中选择最多5个任务作为当前活跃任务

**当前活跃任务**: (暂无，请从待办任务池中选择)

```markdown
示例：
- [ ] T001 安装Python依赖库
- [ ] T002 [P] 创建实盘交易模块目录结构
- [ ] T003 [P] 创建Kafka topic配置脚本
- [ ] T004 [P] 编写Kafka连接测试脚本
- [ ] T005 [P] 创建数据库配置模板
```

---

## 📥 待办任务池 (8个)

### T001 安装Python依赖库
- **文件**: `requirements.txt`
- **依赖**: 无
- **并行**: 否
- **描述**: 安装kafka-python, redis-py, pymongo, clickhouse-driver, fastapi, uvicorn到requirements.txt
- **详细步骤**:
  1. 编辑requirements.txt，添加以下依赖：
     ```text
     kafka-python>=2.0.2
     redis-py>=5.0.0
     pymongo>=4.6.0
     clickhouse-driver>=0.2.6
     fastapi>=0.109.0
     uvicorn>=0.27.0
     ```
  2. 运行 `pip install -r requirements.txt` 验证安装
- **验收**: pip install -r requirements.txt 成功无错误

---

### T002 [P] 创建实盘交易模块目录结构
- **文件**:
  - 新增: `src/ginkgo/workers/execution_node/`
  - 新增: `src/ginkgo/livecore/`
  - 复用: `src/ginkgo/trading/engines/` (engine_live.py)
  - 复用: `src/ginkgo/trading/gateway/` (trade_gateway.py)
  - 复用: `src/ginkgo/trading/events/`
  - 复用: `api/`
- **依赖**: 无
- **并行**: 是
- **描述**:
  - 创建workers/execution_node/目录，用于ExecutionNode Worker（独立进程）
  - 创建livecore/目录，用于LiveCore容器（多线程）
  - 复用现有trading/engines/目录中的engine_live.py
  - 复用现有trading/gateway/目录中的trade_gateway.py
  - 复用现有trading/events/目录中的事件类（EventPriceUpdate, EventOrderPartiallyFilled等）
  - 复用现有api/目录用于API Gateway
  - 为所有新目录创建__init__.py文件
- **详细步骤**:
  1. 创建目录结构：
     ```bash
     mkdir -p src/ginkgo/workers/execution_node
     mkdir -p src/ginkgo/livecore
     ```
  2. 创建所有必要的__init__.py文件（使目录成为Python包）：
     ```bash
     touch src/ginkgo/workers/__init__.py
     touch src/ginkgo/workers/execution_node/__init__.py
     touch src/ginkgo/livecore/__init__.py
     ```
  3. 验证复用目录存在：
     - `src/ginkgo/trading/engines/engine_live.py`
     - `src/ginkgo/trading/gateway/trade_gateway.py`
     - `src/ginkgo/trading/events/`
     - `api/`
- **验收**: 所有目录存在且包含__init__.py，复用目录已确认存在

---

### T003 [P] 创建Kafka topic配置脚本
- **文件**: `scripts/setup_kafka_topics.sh`
- **依赖**: 无
- **并行**: 是
- **描述**: 创建Kafka topic配置脚本，创建7个topic用于实盘交易
- **详细步骤**:
  1. 创建脚本文件 `scripts/setup_kafka_topics.sh`
  2. 实现以下topic创建逻辑：
     ```bash
     #!/bin/bash
     # Kafka Topics for Live Trading Architecture

     KAFKA_BROKER=localhost:9092

     # Market Data Topics
     kafka-topics.sh --create --topic ginkgo.live.market.data --bootstrap-server $KAFKA_BROKER --partitions 3 --replication-factor 1
     kafka-topics.sh --create --topic ginkgo.live.market.data.hk --bootstrap-server $KAFKA_BROKER --partitions 1 --replication-factor 1
     kafka-topics.sh --create --topic ginkgo.live.market.data.us --bootstrap-server $KAFKA_BROKER --partitions 1 --replication-factor 1
     kafka-topics.sh --create --topic ginkgo.live.market.data.futures --bootstrap-server $KAFKA_BROKER --partitions 1 --replication-factor 1

     # Order Topics
     kafka-topics.sh --create --topic ginkgo.live.orders.submission --bootstrap-server $KAFKA_BROKER --partitions 3 --replication-factor 1
     kafka-topics.sh --create --topic ginkgo.live.orders.feedback --bootstrap-server $KAFKA_BROKER --partitions 3 --replication-factor 1

     # Control Topics
     kafka-topics.sh --create --topic ginkgo.live.control.commands --bootstrap-server $KAFKA_BROKER --partitions 1 --replication-factor 1
     kafka-topics.sh --create --topic ginkgo.live.schedule.updates --bootstrap-server $KAFKA_BROKER --partitions 1 --replication-factor 1
     kafka-topics.sh --create --topic ginkgo.live.system.events --bootstrap-server $KAFKA_BROKER --partitions 1 --replication-factor 1

     # Alert Topic (Global)
     kafka-topics.sh --create --topic ginkgo.alerts --bootstrap-server $KAFKA_BROKER --partitions 1 --replication-factor 1

     echo "Kafka topics created successfully!"
     ```
  3. 添加执行权限：`chmod +x scripts/setup_kafka_topics.sh`
- **验收**: 脚本可执行，成功创建所有topic

---

### T004 [P] 编写Kafka连接测试脚本
- **文件**: `tests/network/live/test_kafka_connection.py`
- **依赖**: 无
- **并行**: 是
- **描述**: 编写测试脚本验证Kafka连接和topic创建
- **详细步骤**:
  1. 创建测试文件 `tests/network/live/test_kafka_connection.py`
  2. 实现以下测试逻辑：
     ```python
     import pytest
     from kafka import KafkaProducer, KafkaConsumer
     from kafka.errors import KafkaError

     @pytest.mark.network
     def test_kafka_producer_connection():
         """测试Kafka Producer连接"""
         try:
             producer = KafkaProducer(
                 bootstrap_servers=['localhost:9092'],
                 acks='all',
                 value_serializer=lambda v: v.encode('utf-8')
             )
             # 发送测试消息
             future = producer.send('ginkgo.live.market.data', key=b'test', value=b'connection_test')
             record_metadata = future.get(timeout=10)
             producer.close()
             assert record_metadata.topic == 'ginkgo.live.market.data'
         except KafkaError as e:
             pytest.fail(f"Kafka producer connection failed: {e}")

     @pytest.mark.network
     def test_kafka_consumer_connection():
         """测试Kafka Consumer连接"""
         try:
             consumer = KafkaConsumer(
                 'ginkgo.live.market.data',
                 bootstrap_servers=['localhost:9092'],
                 auto_offset_reset='earliest',
                 enable_auto_commit=True
             )
             consumer.close()
         except KafkaError as e:
             pytest.fail(f"Kafka consumer connection failed: {e}")

     @pytest.mark.network
     def test_kafka_topics_exist():
         """测试所有必需的topic是否已创建"""
         from kafka.admin import KafkaAdminClient, NewTopic

         admin_client = KafkaAdminClient(
             bootstrap_servers="localhost:9092"
         )

         required_topics = [
             'ginkgo.live.market.data',
             'ginkgo.live.market.data.hk',
             'ginkgo.live.market.data.us',
             'ginkgo.live.market.data.futures',
             'ginkgo.live.orders.submission',
             'ginkgo.live.orders.feedback',
             'ginkgo.live.control.commands',
             'ginkgo.live.schedule.updates',
             'ginkgo.live.system.events',
             'ginkgo.alerts'
         ]

         existing_topics = admin_client.list_topics()
         for topic in required_topics:
             assert topic in existing_topics, f"Topic {topic} not found"

         admin_client.close()
     ```
  3. 添加pytest标记：在`tests/network/live/__init__.py`中配置
- **验收**: 运行pytest测试通过，Kafka连接正常，所有topic存在

---

### T005 [P] 创建数据库配置模板
- **文件**: `~/.ginkgo/config.yaml`
- **依赖**: 无
- **并行**: 是
- **描述**: 在~/.ginkgo/config.yaml添加kafka、redis、mysql、clickhouse、mongodb配置
- **详细步骤**:
  1. 编辑或创建 `~/.ginkgo/config.yaml`
  2. 添加以下配置节：
     ```yaml
     # Kafka Configuration
     kafka:
       bootstrap_servers: "localhost:9092"
       consumer_group: "ginkgo_live_trading"
       auto_offset_reset: "earliest"
       enable_auto_commit: false

     # Redis Configuration
     redis:
       host: "localhost"
       port: 6379
       db: 0
       password: null
       socket_timeout: 5
       socket_connect_timeout: 5

     # MySQL Configuration
     mysql:
       host: "localhost"
       port: 3306
       user: "ginkgo"
       password: "your_password"
       database: "ginkgo"
       charset: "utf8mb4"

     # ClickHouse Configuration
     clickhouse:
       host: "localhost"
       port: 9000
       user: "default"
       password: ""
       database: "ginkgo"
       settings:
         use_numpy: true

     # MongoDB Configuration
     mongodb:
       host: "localhost"
       port: 27017
       username: ""
       password: ""
       database: "ginkgo"
       auth_source: "admin"
     ```
  3. 确保文件权限正确：`chmod 600 ~/.ginkgo/config.yaml`
- **验收**: 配置文件存在，包含所有必需的配置节

---

### T006 [P] 编写数据库连接测试脚本
- **文件**: `tests/network/live/test_database_connection.py`
- **依赖**: 无
- **并行**: 是
- **描述**: 编写测试脚本验证MySQL/ClickHouse/Redis/MongoDB连接
- **详细步骤**:
  1. 创建测试文件 `tests/network/live/test_database_connection.py`
  2. 实现以下测试逻辑：
     ```python
     import pytest
     import redis
     from clickhouse_driver import Client as ClickHouseClient
     import pymysql
     from pymongo import MongoClient

     @pytest.mark.network
     def test_redis_connection():
         """测试Redis连接"""
         try:
             r = redis.Redis(host='localhost', port=6379, db=0)
             r.ping()
             r.close()
         except redis.ConnectionError as e:
             pytest.fail(f"Redis connection failed: {e}")

     @pytest.mark.network
     def test_mysql_connection():
         """测试MySQL连接"""
         try:
             conn = pymysql.connect(
                 host='localhost',
                 user='ginkgo',
                 password='your_password',
                 database='ginkgo'
             )
             cursor = conn.cursor()
             cursor.execute("SELECT 1")
             cursor.close()
             conn.close()
         except pymysql.Error as e:
             pytest.fail(f"MySQL connection failed: {e}")

     @pytest.mark.network
     def test_clickhouse_connection():
         """测试ClickHouse连接"""
         try:
             client = ClickHouseClient(host='localhost', port=9000)
             result = client.execute('SELECT 1')
             assert result[0][0] == 1
             client.disconnect()
         except Exception as e:
             pytest.fail(f"ClickHouse connection failed: {e}")

     @pytest.mark.network
     def test_mongodb_connection():
         """测试MongoDB连接"""
         try:
             client = MongoClient('localhost', 27017, serverSelectionTimeoutMS=2000)
             client.server_info()
             client.close()
         except Exception as e:
             pytest.fail(f"MongoDB connection failed: {e}")
     ```
  3. 添加pytest标记
- **验收**: 运行pytest测试通过，所有数据库连接正常

---

### T007 创建.env.example模板文件
- **文件**: `.env.example`
- **依赖**: 无
- **并行**: 否
- **描述**: 创建.env.example模板文件，包含Kafka、Redis、数据库连接字符串
- **详细步骤**:
  1. 创建 `.env.example` 文件
  2. 添加以下内容：
     ```bash
     # Kafka
     KAFKA_BOOTSTRAP_SERVERS=localhost:9092
     KAFKA_CONSUMER_GROUP=ginkgo_live_trading

     # Redis
     REDIS_HOST=localhost
     REDIS_PORT=6379
     REDIS_DB=0

     # MySQL
     MYSQL_HOST=localhost
     MYSQL_PORT=3306
     MYSQL_USER=ginkgo
     MYSQL_PASSWORD=your_password
     MYSQL_DATABASE=ginkgo

     # ClickHouse
     CLICKHOUSE_HOST=localhost
     CLICKHOUSE_PORT=9000
     CLICKHOUSE_USER=default
     CLICKHOUSE_DATABASE=ginkgo

     # MongoDB
     MONGODB_HOST=localhost
     MONGODB_PORT=27017
     MONGODB_DATABASE=ginkgo
     ```
- **验收**: .env.example文件存在，包含所有环境变量示例

---

### T008 编写Docker Compose配置文件
- **文件**: `docker-compose.yml`
- **依赖**: 无
- **并行**: 否
- **描述**: 编写Docker Compose配置文件用于本地开发环境
- **详细步骤**:
  1. 创建或编辑 `docker-compose.yml`
  2. 添加以下服务：
     ```yaml
     version: '3.8'

     services:
       # Kafka
       zookeeper:
         image: confluentinc/cp-zookeeper:7.4.0
         environment:
           ZOOKEEPER_CLIENT_PORT: 2181
         ports:
           - "2181:2181"

       kafka:
         image: confluentinc/cp-kafka:7.4.0
         depends_on:
           - zookeeper
         ports:
           - "9092:9092"
         environment:
           KAFKA_BROKER_ID: 1
           KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
           KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:29092,PLAINTEXT_HOST://localhost:9092
           KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT
           KAFKA_INTER_BROKER_LISTENER_NAME: PLAINTEXT
           KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR: 1

       # Redis
       redis:
         image: redis:7-alpine
         ports:
           - "6379:6379"
         command: redis-server --appendonly yes

       # MySQL
       mysql:
         image: mysql:8.0
         ports:
           - "3306:3306"
         environment:
           MYSQL_ROOT_PASSWORD: root_password
           MYSQL_DATABASE: ginkgo
           MYSQL_USER: ginkgo
           MYSQL_PASSWORD: ginkgo_password
         volumes:
           - mysql_data:/var/lib/mysql

       # ClickHouse
       clickhouse:
         image: clickhouse/clickhouse-server:23
         ports:
           - "8123:8123"
           - "9000:9000"
         volumes:
           - clickhouse_data:/var/lib/clickhouse

       # MongoDB
       mongodb:
         image: mongo:7
         ports:
           - "27017:27017"
         environment:
           MONGO_INITDB_DATABASE: ginkgo
         volumes:
           - mongodb_data:/data/db

     volumes:
       mysql_data:
       clickhouse_data:
       mongodb_data:
     ```
  3. 验证配置：`docker-compose config`
- **验收**: docker-compose up -d 可以启动所有服务

---

## ✅ 已完成任务 (0个)

*(暂无)*

---

## 📊 进度跟踪

| 指标 | 数值 |
|------|------|
| 总任务数 | 8 |
| 已完成 | 0 |
| 进行中 | 0 |
| 待办 | 8 |
| 完成进度 | 0% |

---

## 🔗 依赖关系

```
Phase 1: Setup (本阶段)
    ↓
Phase 2: Foundational
```

---

## 📝 备注

- 本阶段所有任务都是基础设施搭建，完成后即可开始Phase 2
- 建议优先完成T001-T006，T007-T008可以稍后补充
- 所有并行任务（标记[P]）可以同时进行，提高效率

---

**文档版本**: 1.0.0
**最后更新**: 2026-01-04
