# 统一环境切换 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `ginkgo config set debug on/off` 一条命令控制所有服务（本地 + Docker + Vector）的数据库指向。

**Architecture:** 将 docker-compose.yml 从 `.conf/` 移到项目根目录，数据库地址全部引用 `.env` 变量。CLI 切换 debug 时同步更新 `.env` 并重启有变化的 Docker 容器。Vector 的 ClickHouse endpoint 也引用同一变量。

**Tech Stack:** Python 3.12, Docker Compose, YAML, TOML, Typer CLI

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `docker-compose.yml` | Move from `.conf/` to root | 服务编排，路径从根目录出发 |
| `.env` | Move from `.conf/` to root | 密码 + 服务主机变量，compose 自动读取 |
| `.env.example` | Move from `.conf/` to root | 模板，补齐缺失变量 |
| `.conf/vector.toml` | Move from `deploy/vector/` | Vector 采集配置，endpoint 变量化 |
| `deploy/` | Delete | 清理空目录 |
| `install.py:619` | Modify | 更新 compose 文件路径引用 |
| `src/ginkgo/client/config_cli.py:86-89` | Modify | set_debug 增加 .env 更新 + docker compose |
| `src/ginkgo/client/config_cli.py:288-304` | Modify | 清理 docker-compose.worker.yml 死代码 |
| `src/ginkgo/libs/core/config.py` | Modify | 新增 COMPOSE_FILE_PATH 属性 |
| `.conf/nginx.conf:44,57` | Modify | 硬编码 IP 改为环境变量 |
| `tests/unit/libs/test_logging_pipeline.py:208-212` | Modify | 更新 vector.toml 路径 |

---

### Task 1: Move .env and .env.example to project root

**Files:**
- Move: `.conf/.env` → `.env`
- Move: `.conf/.env.example` → `.env.example`

This task is pure file moves with content updates. No tests needed (no code logic changed).

- [ ] **Step 1: Move .env to root**

```bash
cd /home/kaoru/Ginkgo
mv .conf/.env .env
```

- [ ] **Step 2: Move .env.example to root and update content**

The current `.env.example` is outdated — missing all GINKGO_* host variables, GINKGO_LOG_PATH, Grafana config, etc. Write the complete new version:

```bash
mv .conf/.env.example .env.example
```

Then replace `.env.example` content with:

```env
# ============================================
# 敏感信息配置 - 复制为 .env 并填入真实值
# cp .env.example .env
# ============================================

# Tushare API Token
TUSHARE_TOKEN=your_tushare_token

# MySQL 配置
MYSQL_ROOT_PASSWORD=your_root_password
MYSQL_USER=your_mysql_username
MYSQL_PASSWORD=your_mysql_password

# MongoDB 配置
MONGO_INITDB_ROOT_USERNAME=your_mongo_username
MONGO_INITDB_ROOT_PASSWORD=your_mongo_password

# ClickHouse 配置
CLICKHOUSE_USER=your_clickhouse_username
CLICKHOUSE_PASSWORD=your_clickhouse_password

# Feast MySQL 连接信息
FEAST_MYSQL_USER=your_mysql_username
FEAST_MYSQL_PASSWORD=your_mysql_password
FEAST_CLICKHOUSE_USER=your_clickhouse_username
FEAST_CLICKHOUSE_PASSWORD=your_clickhouse_password

# Feast WebUI 配置
FEAST_UI_HOST=0.0.0.0
FEAST_UI_PORT=9999

# Email SMTP 配置（可选，留空禁用）
EMAIL_SMTP_HOST=
EMAIL_SMTP_PORT=587
EMAIL_SMTP_USER=
EMAIL_SMTP_PASSWORD=
EMAIL_FROM_ADDRESS=
EMAIL_FROM_NAME=Ginkgo Notification

# ============================================
# Ginkgo Worker 通用配置
# ============================================

# Kafka
GINKGO_KAFKA_HOST=kafka1
GINKGO_KAFKA_PORT=9092

# Redis
GINKGO_REDIS_HOST=redis-master
GINKGO_REDIS_PORT=6379

# MySQL (由 CLI debug 命令自动切换)
GINKGO_MYSQL_HOST=mysql-test
GINKGO_MYSQL_PORT=3306

# ClickHouse (由 CLI debug 命令自动切换)
GINKGO_CLICKHOUSE_HOST=clickhouse-test
GINKGO_CLICKHOUSE_PORT=8123

# MongoDB
GINKGO_MONGODB_HOST=mongo-master
GINKGO_MONGODB_PORT=27017

# ============================================
# 日志配置（分布式日志采集）
# ============================================
GINKGO_LOG_PATH=/var/log/ginkgo
GINKGO_LOG_LEVEL_CONSOLE=INFO
GINKGO_LOG_LEVEL_FILE=INFO

# ============================================
# Grafana 配置
# ============================================
GRAFANA_ADMIN_USER=admin
GRAFANA_ADMIN_PASSWORD=admin123

# ============================================
# Nginx 反向代理配置
# ============================================
API_HOST=192.168.50.10
API_PORT=8000
```

- [ ] **Step 3: Verify .gitignore covers .env at root**

Run: `grep -n '\.env' /home/kaoru/Ginkgo/.gitignore`
Expected: `.env` is already listed (lines 112 and 168).

- [ ] **Step 4: Commit**

```bash
git add .env .env.example .conf/.env .conf/.env.example
git commit -m "chore: move .env and .env.example to project root for compose auto-read"
```

**Verification:**

```bash
# 1. 文件在新位置
ls -la .env .env.example
# Expected: 两个文件都存在

# 2. 旧位置已清理
ls .conf/.env .conf/.env.example 2>&1
# Expected: No such file or directory

# 3. .env.example 包含所有必需变量
grep -c 'GINKGO_CLICKHOUSE_HOST\|GINKGO_MYSQL_HOST\|GINKGO_MONGODB_HOST\|GINKGO_LOG_PATH\|API_HOST\|API_PORT' .env.example
# Expected: 6 (每个变量一行)

# 4. .env 不被 git 跟踪
git status .env
# Expected: 应在 .gitignore 中，不显示为 untracked
```

---

### Task 2: Move vector.toml to .conf/ and variable-ize endpoint

**Files:**
- Move: `deploy/vector/vector.toml` → `.conf/vector.toml`
- Delete: `deploy/` directory

- [ ] **Step 1: Move vector.toml**

```bash
cd /home/kaoru/Ginkgo
mv deploy/vector/vector.toml .conf/vector.toml
rmdir deploy/vector
rmdir deploy
```

- [ ] **Step 2: Update vector.toml endpoint to use env var**

In `.conf/vector.toml`, replace all three hardcoded `endpoint = "http://clickhouse-master:8123"` with `endpoint = "http://${CLICKHOUSE_HOST}:8123"`. There are three occurrences (lines 77, 88, 99 of the original file).

The three sinks should now read:

```toml
[sinks.clickhouse_backtest]
type = "clickhouse"
inputs = ["route_by_category.backtest"]
database = "ginkgo"
table = "ginkgo_logs_backtest"
endpoint = "http://${CLICKHOUSE_HOST}:8123"

[sinks.clickhouse_backtest.batch]
max_events = 100
timeout_secs = 5

[sinks.clickhouse_component]
type = "clickhouse"
inputs = ["route_by_category.component"]
database = "ginkgo"
table = "ginkgo_logs_component"
endpoint = "http://${CLICKHOUSE_HOST}:8123"

[sinks.clickhouse_component.batch]
max_events = 100
timeout_secs = 5

[sinks.clickhouse_performance]
type = "clickhouse"
inputs = ["route_by_category.performance"]
database = "ginkgo"
table = "ginkgo_logs_performance"
endpoint = "http://${CLICKHOUSE_HOST}:8123"

[sinks.clickhouse_performance.batch]
max_events = 100
timeout_secs = 5
```

- [ ] **Step 3: Update test file path**

In `tests/unit/libs/test_logging_pipeline.py`, update the vector.toml path from `deploy/vector/vector.toml` to `.conf/vector.toml`. The code at lines 207-209 currently reads:

```python
toml_path = os.path.normpath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "deploy", "vector", "vector.toml"
))
```

Change to:

```python
toml_path = os.path.normpath(os.path.join(
    os.path.dirname(__file__), "..", "..", "..", ".conf", "vector.toml"
))
```

- [ ] **Step 4: Run test to verify path change**

Run: `cd /home/kaoru/Ginkgo && python -m pytest tests/unit/libs/test_logging_pipeline.py::TestVectorConfigPathMatch -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add .conf/vector.toml deploy/ tests/unit/libs/test_logging_pipeline.py
git commit -m "chore: move vector.toml to .conf/ and variable-ize ClickHouse endpoint"
```

**Verification:**

```bash
# 1. 文件在新位置
ls -la .conf/vector.toml
# Expected: 存在

# 2. 旧位置已清理
ls deploy/ 2>&1
# Expected: No such file or directory

# 3. endpoint 已变量化
grep 'endpoint' .conf/vector.toml
# Expected: 所有 3 处都是 "http://${CLICKHOUSE_HOST}:8123"

# 4. 测试通过
python -m pytest tests/unit/libs/test_logging_pipeline.py::TestVectorConfigPathMatch -v
# Expected: PASS
```

---

### Task 3: Move and rewrite docker-compose.yml

**Files:**
- Move: `.conf/docker-compose.yml` → `docker-compose.yml`

This is the largest task. The compose file moves to root and all relative paths change. There are NO code tests for this (it's YAML), so verification is by `docker compose config` validation.

- [ ] **Step 1: Write the new docker-compose.yml at project root**

Create `docker-compose.yml` at `/home/kaoru/Ginkgo/docker-compose.yml` with all the changes below. Then delete `.conf/docker-compose.yml`.

Changes from the original:
1. Replace `x-project-name: 'ginkgo'` with `name: ginkgo` (top-level, Docker reads this)
2. All `./` volume paths (same dir) → `.conf/` prefix
3. All `../` volume paths (parent dir) → remove `../` prefix
4. All `build.context: ..` → `build.context: .`
5. Vector volume: `../deploy/vector/vector.toml` → `.conf/vector.toml`
6. Grafana volume: `../.conf/grafana-provisioning` → `.conf/grafana-provisioning`
7. Add `CLICKHOUSE_HOST: ${GINKGO_CLICKHOUSE_HOST:-clickhouse-test}` env var to vector service
8. nginx.conf: use `${API_HOST}` and `${API_PORT}` env vars (via `envsubst`)

The complete new file:

```yaml
name: ginkgo
services:
  # webui:
  #   image: ginkgo/webui:latest
  #   container_name: ginkgo-web-ui
  #   restart: always
  #   logging:
  #     driver: "json-file"
  #     options:
  #       max-size: "100m"
  #       max-file: "3"
  #   build:
  #     context: .
  #     dockerfile: .conf/Dockerfile.web
  #   ports:
  #     - '80:80'
  #   volumes:
  #     - .conf/nginx.conf:/etc/nginx/nginx.conf
  kafka1:
    image: apache/kafka:4.0.0
    restart: always
    container_name: ginkgo-kafka1
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "3"
    ports:
      - '9092:9092'
      - '9093:9093'
    environment:
      - KAFKA_PROCESS_ROLES=broker,controller
      - KAFKA_NODE_ID=1
      - KAFKA_CONTROLLER_QUORUM_VOTERS=1@kafka1:9093,2@kafka2:9093,3@kafka3:9093
      - KAFKA_LISTENERS=PLAINTEXT://0.0.0.0:19092,CONTROLLER://:9093,PLAINTEXT_HOST://0.0.0.0:9092
      - KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://kafka1:19092,PLAINTEXT_HOST://localhost:9092
      - KAFKA_LISTENER_SECURITY_PROTOCOL_MAP=CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT
      - KAFKA_INTER_BROKER_LISTENER_NAME=PLAINTEXT
      - KAFKA_CONTROLLER_LISTENER_NAMES=CONTROLLER
      - KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=3
      - KAFKA_AUTO_CREATE_TOPICS_ENABLE=true
      - KAFKA_HEAP_OPTS=-Xmx512M -Xms256M
      - KAFKA_LOG_RETENTION_HOURS=2
      - KAFKA_LOG_RETENTION_CHECK_INTERVAL_MS=300000
      - KAFKA_LOG_SEGMENT_BYTES=1073741824
      - KAFKA_LOG_CLEANUP_POLICY=delete
    volumes:
      - .db/kafka1_data:/var/lib/kafka/data
  kafka2:
    image: apache/kafka:4.0.0
    restart: always
    container_name: ginkgo-kafka2
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "3"
    ports:
      - '9094:9092'
      - '9095:9093'
    environment:
      - KAFKA_PROCESS_ROLES=broker,controller
      - KAFKA_NODE_ID=2
      - KAFKA_CONTROLLER_QUORUM_VOTERS=1@kafka1:9093,2@kafka2:9093,3@kafka3:9093
      - KAFKA_LISTENERS=PLAINTEXT://0.0.0.0:19092,CONTROLLER://:9093,PLAINTEXT_HOST://0.0.0.0:9092
      - KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://kafka2:19092,PLAINTEXT_HOST://localhost:9094
      - KAFKA_LISTENER_SECURITY_PROTOCOL_MAP=CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT
      - KAFKA_INTER_BROKER_LISTENER_NAME=PLAINTEXT
      - KAFKA_CONTROLLER_LISTENER_NAMES=CONTROLLER
      - KAFKA_LOG_RETENTION_HOURS=2
      - KAFKA_LOG_RETENTION_CHECK_INTERVAL_MS=300000
      - KAFKA_LOG_SEGMENT_BYTES=1073741824
      - KAFKA_LOG_CLEANUP_POLICY=delete
      - KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=3
      - KAFKA_AUTO_CREATE_TOPICS_ENABLE=true
      - KAFKA_HEAP_OPTS=-Xmx512M -Xms256M
    volumes:
      - .db/kafka2_data:/var/lib/kafka/data
  kafka3:
    image: apache/kafka:4.0.0
    restart: always
    container_name: ginkgo-kafka3
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "3"
    ports:
      - '9096:9092'
      - '9097:9093'
    environment:
      - KAFKA_PROCESS_ROLES=broker,controller
      - KAFKA_NODE_ID=3
      - KAFKA_CONTROLLER_QUORUM_VOTERS=1@kafka1:9093,2@kafka2:9093,3@kafka3:9093
      - KAFKA_LISTENERS=PLAINTEXT://0.0.0.0:19092,CONTROLLER://:9093,PLAINTEXT_HOST://0.0.0.0:9092
      - KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://kafka3:19092,PLAINTEXT_HOST://localhost:9096
      - KAFKA_LISTENER_SECURITY_PROTOCOL_MAP=CONTROLLER:PLAINTEXT,PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT
      - KAFKA_INTER_BROKER_LISTENER_NAME=PLAINTEXT
      - KAFKA_CONTROLLER_LISTENER_NAMES=CONTROLLER
      - KAFKA_LOG_RETENTION_HOURS=2
      - KAFKA_LOG_RETENTION_CHECK_INTERVAL_MS=300000
      - KAFKA_LOG_SEGMENT_BYTES=1073741824
      - KAFKA_LOG_CLEANUP_POLICY=delete
      - KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=3
      - KAFKA_AUTO_CREATE_TOPICS_ENABLE=true
      - KAFKA_HEAP_OPTS=-Xmx512M -Xms256M
    volumes:
      - .db/kafka3_data:/var/lib/kafka/data
  redis-master:
    image: redis:alpine3.18
    container_name: ginkgo-redis-master
    restart: always
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "3"
    ports:
      - "6379:6379"
    volumes:
      - .conf/redis.conf:/etc/redis/redis.conf
      - .db/redis/data:/data
    command: redis-server /etc/redis/redis.conf --maxmemory 20480mb
  mysql-master:
    image: mysql:8.2.0
    container_name: ginkgo-mysql-master
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "3"
    command:
      --max_connections=1000
      --character-set-server=utf8mb4
      --collation-server=utf8mb4_general_ci
      --default-time-zone='+08:00'
    restart: always
    ports:
      - "3306:3306"
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_DATABASE: ginkgo
      MYSQL_USER: ${MYSQL_USER}
      MYSQL_PASSWORD: ${MYSQL_PASSWORD}
      TZ: Asia/Shanghai
    volumes:
      - .logs/mysql:/logs
      - .db/mysql:/var/lib/mysql
      - .conf/mysql_entrypoint:/docker-entrypoint-initdb.d

  mysql-test:
    image: mysql:8.2.0
    container_name: ginkgo-mysql-test
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "3"
    command:
      --max_connections=1000
      --character-set-server=utf8mb4
      --collation-server=utf8mb4_general_ci
      --default-time-zone='+08:00'
    restart: always
    ports:
      - "13306:3306"
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_DATABASE: ginkgo
      MYSQL_USER: ${MYSQL_USER}
      MYSQL_PASSWORD: ${MYSQL_PASSWORD}
      TZ: Asia/Shanghai
    volumes:
      - .logs/mysql_test:/logs
      - .db/mysql_test:/var/lib/mysql
      - .conf/mysql_entrypoint:/docker-entrypoint-initdb.d
    deploy:
      resources:
        limits:
          cpus: '2.00'
          memory: 4096M

  clickhouse-master:
    image: clickhouse/clickhouse-server:24.8.4.13-alpine
    container_name: ginkgo-clickhouse-master
    restart: always
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "3"
    ports:
      - "8123:8123"
      - "9000:9000"
      - "9009:9009"
    volumes:
      - .logs/clickhouse:/var/log/clickhouse-server
      - .conf/clickhouse_users.xml:/etc/clickhouse-server/users.xml
      - .conf/clickhouse_log_config.xml:/etc/clickhouse-server/config.d/logger.xml:ro
      - .db/clickhouse:/var/lib/clickhouse:rw
    ulimits:
      nproc: 65546
      nofile:
        soft: 262144
        hard: 262144
    environment:
      CLICKHOUSE_DB: ginkgo
      SHOW: 'true'

  clickhouse-test:
    image: clickhouse/clickhouse-server:24.8.4.13-alpine
    container_name: ginkgo-clickhouse-test
    restart: always
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "3"
    ports:
      - "18123:8123"
      - "19000:9000"
      - "19009:9009"
    volumes:
      - .logs/clickhouse_test:/var/log/clickhouse-server
      - .conf/clickhouse_users.xml:/etc/clickhouse-server/users.xml
      - .conf/clickhouse_log_config.xml:/etc/clickhouse-server/config.d/logger.xml:ro
      - .db/clickhouse_test:/var/lib/clickhouse:rw
    ulimits:
      nproc: 65546
      nofile:
        soft: 262144
        hard: 262144
    environment:
      CLICKHOUSE_DB: ginkgo
      SHOW: 'true'
    deploy:
      resources:
        limits:
          cpus: '2.00'
          memory: 4096M

  grafana:
    image: grafana/grafana:main-ubuntu
    container_name: ginkgo-grafana
    restart: always
    user: "472"
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "3"
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_USER=${GRAFANA_ADMIN_USER:-admin}
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD:-admin}
      - GF_SERVER_ROOT_URL=http://localhost:3000
      - GF_INSTALL_PLUGINS=grafana-clickhouse-datasource
    volumes:
      - grafana-storage:/var/lib/grafana
      - .conf/grafana-provisioning:/etc/grafana/provisioning:ro
    deploy:
      resources:
        limits:
          cpus: '0.50'
          memory: 512M
        reservations:
          cpus: '0.10'
          memory: 128M

  # Vector - Log collection and routing to ClickHouse
  vector:
    image: timberio/vector:0.39.0-alpine
    container_name: ginkgo-vector
    restart: always
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "3"
    ports:
      - "8686:8686"
    volumes:
      - .conf/vector.toml:/etc/vector/vector.toml:ro
      - /home/kaoru/.ginkgo/logs:/var/log/ginkgo:ro
      - vector-data:/vector-data
    command: --config /etc/vector/vector.toml
    environment:
      - GINKGO_LOG_PATH=/var/log/ginkgo
      - CLICKHOUSE_HOST=${GINKGO_CLICKHOUSE_HOST:-clickhouse-test}
    depends_on:
      - clickhouse-master
    deploy:
      resources:
        limits:
          cpus: '0.50'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
    healthcheck:
      test: ["CMD-SHELL", "wget --no-verbose --tries=1 --spider http://localhost:8686/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 30s

  # Mongo
  mongo-master:
    image: 'mongo:6.0.27-jammy'
    container_name: ginkgo-mongo-master
    restart: always
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "3"
    ports:
      - '27017:27017'
    environment:
      MONGO_INITDB_ROOT_USERNAME: ${MONGO_INITDB_ROOT_USERNAME}
      MONGO_INITDB_ROOT_PASSWORD: ${MONGO_INITDB_ROOT_PASSWORD}
    volumes:
      - .db/mongo:/data/db
      - .logs/mongo:/var/log/mongodb
      - .conf/mongo_entrypoint:/docker-entrypoint-initdb.d
  # Feast Feature Server
  feast-server:
    build:
      context: .
      dockerfile: .conf/Dockerfile.feast
    image: feast:0.51.click.redis.mysql
    container_name: ginkgo-feast-server
    restart: always
    depends_on:
      - redis-master
      - clickhouse-master
      - mysql-master
    environment:
      LOG_LEVEL: info
      FEAST_SERVE_HOST: 0.0.0.0
      FEAST_SERVE_PORT: 6566
      FEAST_MYSQL_HOST: mysql-master
      FEAST_MYSQL_PORT: 3306
      FEAST_MYSQL_USER: ${FEAST_MYSQL_USER}
      FEAST_MYSQL_PASSWORD: ${FEAST_MYSQL_PASSWORD}
      FEAST_MYSQL_DATABASE: feast
      FEAST_REDIS_HOST: redis-master
      FEAST_REDIS_PORT: 6379
      FEAST_CLICKHOUSE_HOST: clickhouse-master
      FEAST_CLICKHOUSE_PORT: 8123
      FEAST_CLICKHOUSE_USER: ${FEAST_CLICKHOUSE_USER}
      FEAST_CLICKHOUSE_PASSWORD: ${FEAST_CLICKHOUSE_PASSWORD}
      FEAST_CLICKHOUSE_DATABASE: ginkgo
      PYTHONPATH: /feast
      PYTHONUNBUFFERED: 1
    ports:
      - "6566:6566"
    working_dir: /feast
    healthcheck:
      test: ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:6566/health')\" || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  feast-ui:
    build:
      context: .
      dockerfile: .conf/Dockerfile.feast
    image: feast:0.51.click.redis.mysql
    container_name: ginkgo-feast-ui
    restart: always
    depends_on:
      - redis-master
      - clickhouse-master
      - mysql-master
    environment:
      LOG_LEVEL: info
      FEAST_UI_HOST: ${FEAST_UI_HOST}
      FEAST_UI_PORT: ${FEAST_UI_PORT}
      FEAST_MYSQL_HOST: mysql-master
      FEAST_MYSQL_PORT: 3306
      FEAST_MYSQL_USER: ${FEAST_MYSQL_USER}
      FEAST_MYSQL_PASSWORD: ${FEAST_MYSQL_PASSWORD}
      FEAST_MYSQL_DATABASE: feast
      FEAST_REDIS_HOST: redis-master
      FEAST_REDIS_PORT: 6379
      FEAST_CLICKHOUSE_HOST: clickhouse-master
      FEAST_CLICKHOUSE_PORT: 8123
      FEAST_CLICKHOUSE_USER: ${FEAST_CLICKHOUSE_USER}
      FEAST_CLICKHOUSE_PASSWORD: ${FEAST_CLICKHOUSE_PASSWORD}
      FEAST_CLICKHOUSE_DATABASE: ginkgo
      PYTHONPATH: /feast
      PYTHONUNBUFFERED: 1
    ports:
      - "9999:9999"
    working_dir: /feast
    command: ["/feast/start-feast-ui.sh"]
    healthcheck:
      test: ["CMD-SHELL", "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:9999')\" || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Notification Worker
  notify-worker:
    build:
      context: .
      dockerfile: .conf/Dockerfile.ginkgo
    image: ginkgo/worker:latest
    container_name: ginkgo-notify-worker
    command: ["python", "main.py", "serve", "worker-notify"]
    restart: always
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "3"
    depends_on:
      - kafka1
      - redis-master
      - mysql-test
      - clickhouse-test
      - mongo-master
    environment:
      GINKGO_KAFKA_HOST: kafka1
      GINKGO_KAFKA_PORT: 9092
      GINKGO_MYSQL_HOST: ${GINKGO_MYSQL_HOST:-mysql-test}
      GINKGO_MYSQL_PORT: ${GINKGO_MYSQL_PORT:-3306}
      GINKGO_MYSQL_USER: ${MYSQL_USER}
      GINKGO_MYSQL_PASSWORD: ${MYSQL_PASSWORD}
      GINKGO_MYSQL_DATABASE: ginkgo
      GINKGO_REDIS_HOST: redis-master
      GINKGO_REDIS_PORT: 6379
      GINKGO_CLICKHOUSE_HOST: ${GINKGO_CLICKHOUSE_HOST:-clickhouse-test}
      GINKGO_CLICKHOUSE_PORT: ${GINKGO_CLICKHOUSE_PORT:-8123}
      GINKGO_CLICKHOUSE_USER: ${CLICKHOUSE_USER:-default}
      GINKGO_CLICKHOUSE_PASSWORD: ${CLICKHOUSE_PASSWORD:-""}
      GINKGO_CLICKHOUSE_DATABASE: ginkgo
      GINKGO_MONGODB_HOST: ${GINKGO_MONGODB_HOST:-mongo-master}
      GINKGO_MONGODB_PORT: ${GINKGO_MONGODB_PORT:-27017}
      GINKGO_MONGODB_USERNAME: ${MONGO_INITDB_ROOT_USERNAME}
      GINKGO_MONGODB_PASSWORD: ${MONGO_INITDB_ROOT_PASSWORD}
      GINKGO_MONGODB_DATABASE: ginkgo
      WORKER_GROUP_ID: notification_worker_group
      GINKGO_DEBUG_MODE: "False"
      LOG_LEVEL: INFO
      LOGGING_MODE: container
      GINKGO_LOG_PATH: ${GINKGO_LOG_PATH:-/var/log/ginkgo}
      LOG_LEVEL_CONSOLE: ${GINKGO_LOG_LEVEL_CONSOLE:-INFO}
      LOG_LEVEL_FILE: ${GINKGO_LOG_LEVEL_FILE:-INFO}
      PYTHONUNBUFFERED: 1
      GINKGO_NOTIFICATION_DISCORD_TIMEOUT: 3
      GINKGO_NOTIFICATION_EMAIL_TIMEOUT: 10
      GINKGO_NOTIFICATION_DISCORD_MAX_RETRIES: 3
      GINKGO_NOTIFICATION_EMAIL_MAX_RETRIES: 3
      GINKGO_SMTP_HOST: ${EMAIL_SMTP_HOST}
      GINKGO_SMTP_PORT: ${EMAIL_SMTP_PORT}
      GINKGO_SMTP_USER: ${EMAIL_SMTP_USER}
      GINKGO_SMTP_PASSWORD: ${EMAIL_SMTP_PASSWORD}
      GINKGO_FROM_ADDRESS: ${EMAIL_FROM_ADDRESS}
      GINKGO_FROM_NAME: ${EMAIL_FROM_NAME:-Ginkgo Notification}
    volumes:
      - /home/kaoru/.ginkgo/logs:/var/log/ginkgo
    deploy:
      resources:
        limits:
          cpus: '1.00'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
    healthcheck:
      test: ["CMD-SHELL", "cat /proc/1/cmdline | tr '\\0' ' ' | grep -q 'python main.py serve worker-notify' || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # TaskTimer
  tasktimer:
    build:
      context: .
      dockerfile: .conf/Dockerfile.ginkgo
    image: ginkgo/worker:latest
    container_name: ginkgo-tasktimer
    command: ["python", "main.py", "serve", "tasktimer"]
    restart: always
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "3"
    depends_on:
      - kafka1
      - redis-master
      - mongo-master
      - mysql-test
    environment:
      GINKGO_KAFKA_HOST: kafka1
      GINKGO_KAFKA_PORT: 9092
      GINKGO_REDIS_HOST: redis-master
      GINKGO_REDIS_PORT: 6379
      GINKGO_MONGODB_HOST: ${GINKGO_MONGODB_HOST:-mongo-master}
      GINKGO_MONGODB_PORT: ${GINKGO_MONGODB_PORT:-27017}
      GINKGO_MONGODB_USERNAME: ${MONGO_INITDB_ROOT_USERNAME}
      GINKGO_MONGODB_PASSWORD: ${MONGO_INITDB_ROOT_PASSWORD}
      GINKGO_MONGODB_DATABASE: ginkgo
      GINKGO_MYSQL_HOST: ${GINKGO_MYSQL_HOST:-mysql-test}
      GINKGO_MYSQL_PORT: ${GINKGO_MYSQL_PORT:-3306}
      GINKGO_MYSQL_USER: ${MYSQL_USER}
      GINKGO_MYSQL_PASSWORD: ${MYSQL_PASSWORD}
      GINKGO_MYSQL_DATABASE: ginkgo
      GINKGO_DEBUG_MODE: "False"
      LOG_LEVEL: INFO
      LOGGING_MODE: container
      GINKGO_LOG_PATH: ${GINKGO_LOG_PATH:-/var/log/ginkgo}
      LOG_LEVEL_CONSOLE: ${GINKGO_LOG_LEVEL_CONSOLE:-INFO}
      LOG_LEVEL_FILE: ${GINKGO_LOG_LEVEL_FILE:-INFO}
      PYTHONUNBUFFERED: 1
    volumes:
      - ${HOME}/.ginkgo/task_timer.yml:/root/.ginkgo/task_timer.yml:ro
      - /home/kaoru/.ginkgo/logs:/var/log/ginkgo
    deploy:
      resources:
        limits:
          cpus: '0.50'
          memory: 256M
        reservations:
          cpus: '0.10'
          memory: 128M
    healthcheck:
      test: ["CMD-SHELL", "cat /proc/1/cmdline | tr '\\0' ' ' | grep -q 'python main.py serve tasktimer' || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # LiveCore
  livecore:
    build:
      context: .
      dockerfile: .conf/Dockerfile.ginkgo
    image: ginkgo/worker:latest
    container_name: ginkgo-livecore
    command: ["python", "main.py", "serve", "livecore"]
    restart: always
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "3"
    depends_on:
      - kafka1
      - redis-master
      - mysql-master
      - clickhouse-master
      - mongo-master
    environment:
      GINKGO_KAFKA_HOST: kafka1
      GINKGO_KAFKA_PORT: 9092
      GINKGO_REDIS_HOST: redis-master
      GINKGO_REDIS_PORT: 6379
      GINKGO_MONGODB_HOST: ${GINKGO_MONGODB_HOST:-mongo-master}
      GINKGO_MONGODB_PORT: ${GINKGO_MONGODB_PORT:-27017}
      GINKGO_MONGODB_USERNAME: ${MONGO_INITDB_ROOT_USERNAME}
      GINKGO_MONGODB_PASSWORD: ${MONGO_INITDB_ROOT_PASSWORD}
      GINKGO_MONGODB_DATABASE: ginkgo
      GINKGO_MYSQL_HOST: ${GINKGO_MYSQL_HOST:-mysql-test}
      GINKGO_MYSQL_PORT: ${GINKGO_MYSQL_PORT:-3306}
      GINKGO_MYSQL_USER: ${MYSQL_USER}
      GINKGO_MYSQL_PASSWORD: ${MYSQL_PASSWORD}
      GINKGO_MYSQL_DATABASE: ginkgo
      GINKGO_CLICKHOUSE_HOST: ${GINKGO_CLICKHOUSE_HOST:-clickhouse-test}
      GINKGO_CLICKHOUSE_PORT: ${GINKGO_CLICKHOUSE_PORT:-8123}
      GINKGO_CLICKHOUSE_USER: ${CLICKHOUSE_USER:-default}
      GINKGO_CLICKHOUSE_PASSWORD: ${CLICKHOUSE_PASSWORD:-""}
      GINKGO_CLICKHOUSE_DATABASE: ginkgo
      GINKGO_DEBUG_MODE: "False"
      LOG_LEVEL: INFO
      LOGGING_MODE: container
      GINKGO_LOG_PATH: ${GINKGO_LOG_PATH:-/var/log/ginkgo}
      LOG_LEVEL_CONSOLE: ${GINKGO_LOG_LEVEL_CONSOLE:-INFO}
      LOG_LEVEL_FILE: ${GINKGO_LOG_LEVEL_FILE:-INFO}
      PYTHONUNBUFFERED: 1
      TZ: Asia/Shanghai
    volumes:
      - ${HOME}/.ginkgo/task_timer.yml:/root/.ginkgo/task_timer.yml:ro
      - /home/kaoru/.ginkgo/logs:/var/log/ginkgo
    deploy:
      resources:
        limits:
          cpus: '1.00'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
    healthcheck:
      test: ["CMD-SHELL", "cat /proc/1/cmdline | tr '\\0' ' ' | grep -q 'python main.py serve livecore' || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # Data Worker
  data-worker:
    build:
      context: .
      dockerfile: .conf/Dockerfile.ginkgo
    image: ginkgo/worker:latest
    command: ["python", "main.py", "serve", "worker-data"]
    restart: always
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "3"
    depends_on:
      - kafka1
      - redis-master
      - mongo-master
      - clickhouse-test
    environment:
      GINKGO_KAFKA_HOST: kafka1
      GINKGO_KAFKA_PORT: 9092
      GINKGO_REDIS_HOST: redis-master
      GINKGO_REDIS_PORT: 6379
      GINKGO_MONGODB_HOST: ${GINKGO_MONGODB_HOST:-mongo-master}
      GINKGO_MONGODB_PORT: ${GINKGO_MONGODB_PORT:-27017}
      GINKGO_MONGODB_USERNAME: ${MONGO_INITDB_ROOT_USERNAME}
      GINKGO_MONGODB_PASSWORD: ${MONGO_INITDB_ROOT_PASSWORD}
      GINKGO_MONGODB_DATABASE: ginkgo
      GINKGO_CLICKHOUSE_HOST: ${GINKGO_CLICKHOUSE_HOST:-clickhouse-test}
      GINKGO_CLICKHOUSE_PORT: ${GINKGO_CLICKHOUSE_PORT:-8123}
      GINKGO_CLICKHOUSE_USER: ${CLICKHOUSE_USER:-default}
      GINKGO_CLICKHOUSE_PASSWORD: ${CLICKHOUSE_PASSWORD:-""}
      GINKGO_CLICKHOUSE_DATABASE: ginkgo
      GINKGO_MYSQL_HOST: ${GINKGO_MYSQL_HOST:-mysql-test}
      GINKGO_MYSQL_PORT: ${GINKGO_MYSQL_PORT:-3306}
      GINKGO_MYSQL_USER: ${MYSQL_USER}
      GINKGO_MYSQL_PASSWORD: ${MYSQL_PASSWORD}
      GINKGO_MYSQL_DATABASE: ginkgo
      WORKER_GROUP_ID: data-worker-group
      GINKGO_DEBUG_MODE: "False"
      LOG_LEVEL: INFO
      LOGGING_MODE: container
      GINKGO_LOG_PATH: ${GINKGO_LOG_PATH:-/var/log/ginkgo}
      PYTHONUNBUFFERED: 1
      TZ: Asia/Shanghai
      TUSHARE_TOKEN: ${TUSHARE_TOKEN}
    volumes:
      - /home/kaoru/.ginkgo/logs:/var/log/ginkgo
    deploy:
      resources:
        limits:
          cpus: '1.00'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
    healthcheck:
      test: ["CMD-SHELL", "cat /proc/1/cmdline | tr '\\0' ' ' | grep -q 'python main.py serve worker-data' || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # ExecutionNode
  execution-node:
    build:
      context: .
      dockerfile: .conf/Dockerfile.ginkgo
    image: ginkgo/worker:latest
    command: ["python", "main.py", "serve", "execution"]
    restart: always
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "3"
    depends_on:
      - kafka1
      - redis-master
      - mongo-master
      - mysql-test
      - clickhouse-test
    environment:
      GINKGO_KAFKA_HOST: kafka1
      GINKGO_KAFKA_PORT: 9092
      GINKGO_REDIS_HOST: redis-master
      GINKGO_REDIS_PORT: 6379
      GINKGO_MONGODB_HOST: ${GINKGO_MONGODB_HOST:-mongo-master}
      GINKGO_MONGODB_PORT: ${GINKGO_MONGODB_PORT:-27017}
      GINKGO_MONGODB_USERNAME: ${MONGO_INITDB_ROOT_USERNAME}
      GINKGO_MONGODB_PASSWORD: ${MONGO_INITDB_ROOT_PASSWORD}
      GINKGO_MONGODB_DATABASE: ginkgo
      GINKGO_CLICKHOUSE_HOST: ${GINKGO_CLICKHOUSE_HOST:-clickhouse-test}
      GINKGO_CLICKHOUSE_PORT: ${GINKGO_CLICKHOUSE_PORT:-8123}
      GINKGO_CLICKHOUSE_USER: ${CLICKHOUSE_USER:-default}
      GINKGO_CLICKHOUSE_PASSWORD: ${CLICKHOUSE_PASSWORD:-""}
      GINKGO_CLICKHOUSE_DATABASE: ginkgo
      GINKGO_MYSQL_HOST: ${GINKGO_MYSQL_HOST:-mysql-test}
      GINKGO_MYSQL_PORT: ${GINKGO_MYSQL_PORT:-3306}
      GINKGO_MYSQL_USER: ${MYSQL_USER}
      GINKGO_MYSQL_PASSWORD: ${MYSQL_PASSWORD}
      GINKGO_MYSQL_DATABASE: ginkgo
      GINKGO_DEBUG_MODE: "False"
      LOG_LEVEL: INFO
      LOGGING_MODE: container
      GINKGO_LOG_PATH: ${GINKGO_LOG_PATH:-/var/log/ginkgo}
      LOG_LEVEL_CONSOLE: ${GINKGO_LOG_LEVEL_CONSOLE:-INFO}
      LOG_LEVEL_FILE: ${GINKGO_LOG_LEVEL_FILE:-INFO}
      PYTHONUNBUFFERED: 1
      TZ: Asia/Shanghai
    volumes:
      - /home/kaoru/.ginkgo/logs:/var/log/ginkgo
    deploy:
      resources:
        limits:
          cpus: '1.00'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
    healthcheck:
      test: ["CMD-SHELL", "cat /proc/1/cmdline | tr '\\0' ' ' | grep -q 'python main.py serve execution' || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

volumes:
  grafana-storage:
    driver: local
  vector-data:
    driver: local
```

- [ ] **Step 2: Delete old compose file**

```bash
rm /home/kaoru/Ginkgo/.conf/docker-compose.yml
```

- [ ] **Step 3: Validate compose config**

```bash
cd /home/kaoru/Ginkgo
docker compose config --quiet
```

Expected: no output (valid). If errors, fix volume paths.

- [ ] **Step 4: Commit**

```bash
git add docker-compose.yml .conf/docker-compose.yml
git commit -m "chore: move docker-compose.yml to project root with name:ginkgo and variable-ized paths"
```

**Verification:**

```bash
# 1. compose 语法正确
docker compose config --quiet
# Expected: 无输出（验证通过）

# 2. 项目名正确
docker compose config --format json | python -m json.tool | grep name
# Expected: "ginkgo"

# 3. 无残留的 ../ 路径
grep '\.\./' docker-compose.yml
# Expected: 无匹配

# 4. build context 全部指向当前目录
grep 'context:' docker-compose.yml
# Expected: 所有都是 "context: ."

# 5. vector 的 CLICKHOUSE_HOST 引用变量
grep 'CLICKHOUSE_HOST' docker-compose.yml
# Expected: vector 服务中有 CLICKHOUSE_HOST=${GINKGO_CLICKHOUSE_HOST:-clickhouse-test}

# 6. Worker 服务引用变量化主机
grep 'GINKGO_CLICKHOUSE_HOST\|GINKGO_MYSQL_HOST\|GINKGO_MONGODB_HOST' docker-compose.yml | head -6
# Expected: notify-worker, tasktimer, livecore, data-worker, execution-node 都用 ${GINKGO_*_HOST:-default}

# 7. 旧文件已删除
ls .conf/docker-compose.yml 2>&1
# Expected: No such file or directory
```

---

### Task 4: Update nginx.conf hardcoded IP

**Files:**
- Modify: `.conf/nginx.conf`

Nginx does NOT natively support environment variable substitution in config files. The standard approach is to use `envsubst` in the container entrypoint. However, since the webui service is currently commented out, we only need to prepare the template.

- [ ] **Step 1: Update nginx.conf to use template variables**

Replace `.conf/nginx.conf` content. The variables `${API_HOST}` and `${API_PORT}` will be substituted by `envsubst` when the container starts.

```nginx
user  nginx;
worker_processes  auto;

error_log  /var/log/nginx/error.log notice;
pid        /var/run/nginx.pid;


events {
    worker_connections  1024;
}


http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    log_format  main  '$remote_addr - $remote_user [$time_local] "$request" '
                      '$status $body_bytes_sent "$http_referer" '
                      '"$http_user_agent" "$http_x_forwarded_for"';

    access_log  /var/log/nginx/access.log  main;

    sendfile        on;

    keepalive_timeout  65;

    server {
        listen 80 default_server;
        listen [::]:80 default_server;
        server_name localhost;


        location / {
            root /usr/share/nginx/html;
            try_files $uri $uri/ /index.html;
        }

        location /stream {
            proxy_pass http://${API_HOST}:${API_PORT}/stream/v1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            proxy_http_version 1.1;
            proxy_set_header Connection "upgrade";
            proxy_read_timeout 3600s;
            proxy_send_timeout 3600s;
        }

        location /api {
            proxy_pass http://${API_HOST}:${API_PORT}/api/v1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

    }

    include /etc/nginx/conf.d/*.conf;
}
```

Note: When the webui service is uncommented in compose, it should mount this as a template and use `envsubst`:

```yaml
# Future webui service should use:
# volumes:
#   - .conf/nginx.conf:/etc/nginx/templates/default.conf.template:ro
# environment:
#   - API_HOST=${API_HOST:-192.168.50.10}
#   - API_PORT=${API_PORT:-8000}
```

- [ ] **Step 2: Commit**

```bash
git add .conf/nginx.conf
git commit -m "fix: replace hardcoded IP in nginx.conf with env vars"
```

**Verification:**

```bash
# 1. 无硬编码 IP
grep -n '192\.168\|10\.\|172\.' .conf/nginx.conf
# Expected: 无匹配

# 2. 使用了变量
grep 'API_HOST\|API_PORT' .conf/nginx.conf
# Expected: 两处 proxy_pass 引用 ${API_HOST}:${API_PORT}
```

---

### Task 5: Add COMPOSE_FILE_PATH to GinkgoConfig and update install.py

**Files:**
- Modify: `src/ginkgo/libs/core/config.py:357-361` (after WORKING_PATH)
- Modify: `install.py:619`

- [ ] **Step 1: Add COMPOSE_FILE_PATH property to GinkgoConfig**

In `src/ginkgo/libs/core/config.py`, after the `set_work_path` method (around line 361), add:

```python
    @property
    def COMPOSE_FILE_PATH(self) -> str:
        working = self.WORKING_PATH
        if working:
            return os.path.join(working, "docker-compose.yml")
        return ""
```

- [ ] **Step 2: Update install.py path reference**

In `install.py`, line 619, change:

```python
    path_dockercompose = f"{working_directory}/.conf/docker-compose.yml"
```

to:

```python
    path_dockercompose = f"{working_directory}/docker-compose.yml"
```

- [ ] **Step 3: Commit**

```bash
git add src/ginkgo/libs/core/config.py install.py
git commit -m "feat: add COMPOSE_FILE_PATH property and update install.py path"
```

**Verification:**

```python
# 在 Python 中验证 COMPOSE_FILE_PATH 属性
python -c "
from ginkgo.libs import GCONF
path = GCONF.COMPOSE_FILE_PATH
print(f'COMPOSE_FILE_PATH: {path}')
assert path.endswith('docker-compose.yml'), f'Expected docker-compose.yml, got {path}'
print('OK')
"
# Expected: OK
```

```bash
# install.py 路径正确
grep 'path_dockercompose' install.py
# Expected: path_dockercompose = f"{working_directory}/docker-compose.yml"
```

---

### Task 6: Write tests for CLI .env update logic

**Files:**
- Create: `tests/unit/client/test_env_switching.py`

This task writes the tests FIRST for the .env update logic that Task 7 will implement.

- [ ] **Step 1: Write test file**

Create `tests/unit/client/test_env_switching.py`:

```python
"""
统一环境切换测试

验证 ginkgo config set debug on/off 自动更新 .env 文件：
- debug=on → CLICKHOUSE_HOST=clickhouse-test, MYSQL_HOST=mysql-test
- debug=off → CLICKHOUSE_HOST=clickhouse-master, MYSQL_HOST=mysql-master
- .env 不存在时自动创建
- docker compose up -d 被调用
"""

import os
import pytest
from unittest.mock import patch, MagicMock


@pytest.mark.unit
class TestEnvUpdateLogic:
    """验证 update_env_for_debug 函数的核心逻辑"""

    def test_debug_on_sets_test_hosts(self, tmp_path):
        """debug=on 时写入 test 环境主机"""
        from ginkgo.client.config_cli import update_env_for_debug

        env_file = str(tmp_path / ".env")
        update_env_for_debug(env_file, debug_on=True)

        with open(env_file) as f:
            content = f.read()

        assert "GINKGO_CLICKHOUSE_HOST=clickhouse-test" in content
        assert "GINKGO_MYSQL_HOST=mysql-test" in content

    def test_debug_off_sets_master_hosts(self, tmp_path):
        """debug=off 时写入 master 环境主机"""
        from ginkgo.client.config_cli import update_env_for_debug

        env_file = str(tmp_path / ".env")
        update_env_for_debug(env_file, debug_on=False)

        with open(env_file) as f:
            content = f.read()

        assert "GINKGO_CLICKHOUSE_HOST=clickhouse-master" in content
        assert "GINKGO_MYSQL_HOST=mysql-master" in content

    def test_preserves_other_env_vars(self, tmp_path):
        """更新时保留其他环境变量"""
        from ginkgo.client.config_cli import update_env_for_debug

        env_file = str(tmp_path / ".env")
        with open(env_file, "w") as f:
            f.write("MYSQL_ROOT_PASSWORD=hellomysql\n")
            f.write("GINKGO_CLICKHOUSE_HOST=clickhouse-test\n")
            f.write("SOME_OTHER_VAR=keep_me\n")

        update_env_for_debug(env_file, debug_on=False)

        with open(env_file) as f:
            content = f.read()

        assert "MYSQL_ROOT_PASSWORD=hellomysql" in content
        assert "SOME_OTHER_VAR=keep_me" in content
        assert "GINKGO_CLICKHOUSE_HOST=clickhouse-master" in content

    def test_creates_env_file_if_not_exists(self, tmp_path):
        """.env 不存在时自动创建"""
        from ginkgo.client.config_cli import update_env_for_debug

        env_file = str(tmp_path / ".env")
        assert not os.path.exists(env_file)

        update_env_for_debug(env_file, debug_on=True)

        assert os.path.exists(env_file)

    def test_debug_mapping_table(self, tmp_path):
        """验证完整的 debug → 数据库映射"""
        from ginkgo.client.config_cli import update_env_for_debug

        env_file = str(tmp_path / ".env")

        # debug=on
        update_env_for_debug(env_file, debug_on=True)
        with open(env_file) as f:
            content_on = f.read()
        assert "GINKGO_CLICKHOUSE_HOST=clickhouse-test" in content_on
        assert "GINKGO_MYSQL_HOST=mysql-test" in content_on
        assert "GINKGO_MONGODB_HOST=mongo-master" in content_on

        # debug=off
        update_env_for_debug(env_file, debug_on=False)
        with open(env_file) as f:
            content_off = f.read()
        assert "GINKGO_CLICKHOUSE_HOST=clickhouse-master" in content_off
        assert "GINKGO_MYSQL_HOST=mysql-master" in content_off
        assert "GINKGO_MONGODB_HOST=mongo-master" in content_off
```

- [ ] **Step 2: Run tests to verify they fail (Red)**

Run: `cd /home/kaoru/Ginkgo && python -m pytest tests/unit/client/test_env_switching.py -v`
Expected: FAIL — `ImportError: cannot import name 'update_env_for_debug'`

- [ ] **Step 3: Commit**

```bash
git add tests/unit/client/test_env_switching.py
git commit -m "test: add env switching tests (red phase)"
```

**Verification (Red):**

```bash
# 测试应全部失败（函数未实现）
python -m pytest tests/unit/client/test_env_switching.py -v 2>&1 | tail -20
# Expected: ImportError or FAILED — update_env_for_debug not found
```

---

### Task 7: Implement CLI .env update + docker compose restart

**Files:**
- Modify: `src/ginkgo/client/config_cli.py`

- [ ] **Step 1: Add update_env_for_debug function and enhance set_debug**

In `src/ginkgo/client/config_cli.py`, add the `update_env_for_debug` function before the `set` command function (before `@app.command()` around line 68). Then modify the `set` command's debug handling.

Add this function at the top of the file (after imports, before the app):

```python
def update_env_for_debug(env_file: str, debug_on: bool) -> None:
    """更新 .env 文件中的数据库主机变量以匹配 debug 模式。

    Args:
        env_file: .env 文件路径
        debug_on: True=测试环境, False=生产环境
    """
    host_mapping = {
        "GINKGO_CLICKHOUSE_HOST": "clickhouse-test" if debug_on else "clickhouse-master",
        "GINKGO_MYSQL_HOST": "mysql-test" if debug_on else "mysql-master",
        "GINKGO_MONGODB_HOST": "mongo-master",  # MongoDB 不切换
    }

    # 读取现有变量
    existing = {}
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    existing[key.strip()] = value.strip()

    # 更新需要切换的变量
    existing.update(host_mapping)

    # 写回文件
    with open(env_file, "w") as f:
        for key, value in existing.items():
            f.write(f"{key}={value}\n")
```

Then modify the `set` command's debug handling. The current code at lines 86-89 is:

```python
        if key.lower() == 'debug':
            debug_value = value.lower() in ['on', 'true', '1', 'yes']
            GCONF.set_debug(debug_value)
            console.print(f":white_check_mark: Set {key} = {debug_value}")
```

Replace with:

```python
        if key.lower() == 'debug':
            debug_value = value.lower() in ['on', 'true', '1', 'yes']
            GCONF.set_debug(debug_value)
            console.print(f":white_check_mark: Set {key} = {debug_value}")

            # 更新 .env 文件中的数据库主机
            env_file = GCONF.COMPOSE_FILE_PATH
            if env_file:
                env_path = os.path.join(os.path.dirname(env_file), ".env")
                try:
                    update_env_for_debug(env_path, debug_on=debug_value)
                    console.print(f":white_check_mark: Updated .env: {os.path.basename(env_path)}")
                except Exception as e:
                    console.print(f":warning: Failed to update .env: {e}")

            # 重启有变化的 Docker 容器
            if env_file and os.path.exists(env_file):
                import subprocess
                try:
                    compose_dir = os.path.dirname(env_file)
                    result = subprocess.run(
                        ["docker", "compose", "up", "-d"],
                        cwd=compose_dir,
                        capture_output=True, text=True, timeout=60,
                    )
                    if result.returncode == 0:
                        console.print(":white_check_mark: Docker containers restarted")
                    else:
                        console.print(f":warning: Docker compose: {result.stderr.strip()}")
                except FileNotFoundError:
                    pass  # Docker not installed, ignore
                except subprocess.TimeoutExpired:
                    console.print(":warning: Docker compose timed out")
                except Exception as e:
                    console.print(f":warning: Docker compose: {e}")
```

- [ ] **Step 2: Run tests to verify they pass (Green)**

Run: `cd /home/kaoru/Ginkgo && python -m pytest tests/unit/client/test_env_switching.py -v`
Expected: All 5 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add src/ginkgo/client/config_cli.py
git commit -m "feat: CLI set debug auto-updates .env and restarts docker compose"
```

**Verification:**

```bash
# 1. 测试全部通过
python -m pytest tests/unit/client/test_env_switching.py -v
# Expected: 5 passed

# 2. 端到端验证：用 CLI 切换 debug 并检查 .env 变化
# 先记录当前 .env 值
grep 'GINKGO_CLICKHOUSE_HOST' .env

# 切换到 production
ginkgo config set debug off
grep 'GINKGO_CLICKHOUSE_HOST' .env
# Expected: GINKGO_CLICKHOUSE_HOST=clickhouse-master

# 切换到 test
ginkgo config set debug on
grep 'GINKGO_CLICKHOUSE_HOST' .env
# Expected: GINKGO_CLICKHOUSE_HOST=clickhouse-test

# 3. 其他变量未被删除
grep 'MYSQL_ROOT_PASSWORD\|TUSHARE_TOKEN' .env
# Expected: 原有变量仍存在
```

---

### Task 8: Clean up dead code in config_cli.py

**Files:**
- Modify: `src/ginkgo/client/config_cli.py:288-304`

- [ ] **Step 1: Remove docker-compose.worker.yml dead code**

In `src/ginkgo/client/config_cli.py`, find the `deploy` action handler (lines 288-304):

```python
        elif action == "deploy":
            console.print(":rocket: Deploying worker services...")

            # 检查docker-compose文件
            compose_file = "docker-compose.worker.yml"
            try:
                import os
                if os.path.exists(compose_file):
                    console.print(f":clipboard: Using compose file: {compose_file}")
                    console.print(":whale: docker-compose up -d")
                else:
                    console.print(":memo: Creating default compose file...")
                    console.print(":bulb: Consider creating docker-compose.worker.yml")
            except Exception as e:
                GLOG.ERROR(f"Failed to check compose file: {e}")

            console.print(":white_check_mark: Deployment completed")
```

Replace with a simple message pointing to the unified compose:

```python
        elif action == "deploy":
            console.print(":rocket: Deploying worker services...")
            from ginkgo.libs import GCONF

            compose_path = GCONF.COMPOSE_FILE_PATH
            if compose_path and os.path.exists(compose_path):
                console.print(f":whale: docker compose up -d (from {compose_path})")
                import subprocess
                try:
                    result = subprocess.run(
                        ["docker", "compose", "up", "-d"],
                        cwd=os.path.dirname(compose_path),
                        capture_output=True, text=True, timeout=120,
                    )
                    if result.returncode == 0:
                        console.print(":white_check_mark: Deployment completed")
                    else:
                        console.print(f":x: Deploy failed: {result.stderr.strip()}")
                except FileNotFoundError:
                    console.print(":x: Docker is not installed")
            else:
                console.print(":x: docker-compose.yml not found")
```

- [ ] **Step 2: Commit**

```bash
git add src/ginkgo/client/config_cli.py
git commit -m "fix: replace dead docker-compose.worker.yml reference with unified compose"
```

**Verification:**

```bash
# 无残留引用
grep -r 'docker-compose.worker' src/
# Expected: 无匹配
```

---

### Task 9: End-to-end smoke test — compose 启动验证

这是最终验收。所有改动完成后，从项目根目录启动 compose，验证所有容器与改动前行为一致。

- [ ] **Step 1: 停掉当前所有 ginkgo 容器**

```bash
cd /home/kaoru/Ginkgo
# 如果旧容器还在用 -f 启动的，先停掉
docker compose -f .conf/docker-compose.yml down 2>/dev/null || true
# 清理旧项目名的容器（如果存在）
docker ps -a --filter "name=ginkgo-" --format "{{.Names}}" | xargs -r docker rm -f
```

- [ ] **Step 2: 从根目录启动 compose**

```bash
cd /home/kaoru/Ginkgo
docker compose up -d
```

- [ ] **Step 3: 验证项目名和网络一致**

```bash
docker compose ps --format "table {{.Name}}\t{{.Status}}"
# Expected: 所有容器名以 ginkgo- 开头，状态为 running 或 healthy

docker network ls | grep ginkgo
# Expected: ginkgo_default 网络（不再是 conf_default）
```

- [ ] **Step 4: 验证基础设施服务健康**

```bash
# MySQL
docker exec ginkgo-mysql-master mysqladmin ping -h 127.0.0.1 -u root -phellomysql 2>/dev/null
# Expected: mysqld is alive

docker exec ginkgo-mysql-test mysqladmin ping -h 127.0.0.1 -u root -phellomysql 2>/dev/null
# Expected: mysqld is alive

# ClickHouse
curl -s http://localhost:8123/ping
# Expected: Ok.

curl -s http://localhost:18123/ping
# Expected: Ok.

# Redis
docker exec ginkgo-redis-master redis-cli ping
# Expected: PONG

# Kafka
docker exec ginkgo-kafka1 kafka-metadata.sh --version 2>/dev/null || docker exec ginkgo-kafka1 bash -c "echo ok"
# Expected: 无报错

# MongoDB
docker exec ginkgo-mongo-master mongosh --eval "db.runCommand({ping:1})" -u ginkgoadm -p hellomongo 2>/dev/null
# Expected: { ok: 1 }
```

- [ ] **Step 5: 验证 Vector 连接正确的 ClickHouse**

```bash
# 当前 .env 设置
grep 'GINKGO_CLICKHOUSE_HOST' .env

# 检查 Vector 日志确认连接目标
docker logs ginkgo-vector 2>&1 | tail -20
# Expected: 无 connection refused 错误

# 验证 Vector health
curl -s http://localhost:8686/health
# Expected: ok 或 HTTP 200
```

- [ ] **Step 6: 验证 CLI 切换 debug 后容器重建**

```bash
# 记录当前 vector 容器 ID
VECTOR_ID_BEFORE=$(docker ps -q --filter "name=ginkgo-vector")

# 切换到 production
ginkgo config set debug off

# 检查 .env 已更新
grep 'GINKGO_CLICKHOUSE_HOST' .env
# Expected: clickhouse-master

# 验证 vector 容器已重建（ID 变化）
VECTOR_ID_AFTER=$(docker ps -q --filter "name=ginkgo-vector")
echo "Before: $VECTOR_ID_BEFORE  After: $VECTOR_ID_AFTER"
# Expected: ID 不同（容器被重建）

# 切回 test
ginkgo config set debug on
grep 'GINKGO_CLICKHOUSE_HOST' .env
# Expected: clickhouse-test
```

- [ ] **Step 7: 验证数据可查询（端到端）**

```bash
# 通过 ClickHouse test 端口查询（debug=on 对应 18123）
curl -s "http://localhost:18123/?query=SELECT+count()+FROM+ginkgo.ginkgo_logs_backtest"
# Expected: 返回数字（非错误）

# 通过 ClickHouse master 端口查询
curl -s "http://localhost:8123/?query=SELECT+count()+FROM+ginkgo.ginkgo_logs_backtest"
# Expected: 返回数字（非错误）
```

- [ ] **Step 8: Commit all verification results (if any fixups were needed)**

If any issues were found and fixed during verification, commit the fixups:

```bash
git add -A
git commit -m "fix: address issues found during end-to-end smoke test"
```

---

## Self-Review

### Spec coverage check:
1. ✅ compose 固定项目名 → Task 3 (`name: ginkgo`)
2. ✅ compose 变量化 → Task 3 (all host vars use `${GINKGO_*_HOST:-default}`)
3. ✅ .env 文件 → Task 1 (move to root)
4. ✅ Vector endpoint 变量化 → Task 2 (`${CLICKHOUSE_HOST}`)
5. ✅ CLI 增强 → Task 7 (update_env_for_debug + docker compose up)
6. ✅ compose 移到根目录 → Task 3
7. ✅ debug 映射表 → Task 6 tests, Task 7 implementation
8. ✅ .env 合并 → Task 1
9. ✅ config_cli.py 死代码 → Task 8
10. ✅ nginx.conf 硬编码 IP → Task 4
11. ✅ install.py 路径更新 → Task 5
12. ✅ config.py COMPOSE_FILE_PATH → Task 5

### Placeholder scan: No TBD/TODO/placeholders found.

### Type consistency: `update_env_for_debug(env_file: str, debug_on: bool)` matches test imports and CLI usage.
