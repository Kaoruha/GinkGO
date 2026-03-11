# Quickstart: 分布式日志系统优化重构

**Feature**: 011-distributed-logging
**Date**: 2026-03-10
**Version**: 1.0.0

## Overview

本文档提供分布式日志系统的快速入门指南，包括环境配置、基本使用和常见问题。

---

## 前置条件

1. Python 3.12.8
2. ClickHouse 服务运行中
3. Docker（用于 Vector 部署）

---

## 安装步骤

### 1. 安装 Python 依赖

```bash
# 安装 structlog
pip install structlog

# 安装 ClickHouse 客户端
pip install clickhouse-sqlalchemy
```

---

### 2. 创建 ClickHouse 日志表

```bash
# 使用 ginkgo CLI 初始化日志表
ginkgo system config set --debug on
ginkgo data init

# 或手动执行初始化脚本
python scripts/init_logging_tables.py
```

---

### 3. 配置 Vector 采集器

创建 `vector.toml` 配置文件：

```toml
# vector.toml

[sources.ginkgo_logs]
type = "file"
include = ["/var/log/ginkgo/**/*.log"]

[transforms.route_by_category]
inputs = ["ginkgo_logs"]
type = "route"
route.backtest = '.log_category == "backtest"'
route.component = '.log_category == "component"'
route.performance = '.log_category == "performance"'

[sinks.clickhouse_backtest]
inputs = ["route_by_category.backtest"]
type = "clickhouse"
database = "ginkgo"
table = "ginkgo_logs_backtest"
endpoint = "http://clickhouse-server:8123"
batch.max_events = 100
batch.timeout_secs = 5

[sinks.clickhouse_component]
inputs = ["route_by_category.component"]
type = "clickhouse"
database = "ginkgo"
table = "ginkgo_logs_component"
endpoint = "http://clickhouse-server:8123"
batch.max_events = 100
batch.timeout_secs = 5

[sinks.clickhouse_performance]
inputs = ["route_by_category.performance"]
type = "clickhouse"
database = "ginkgo"
table = "ginkgo_logs_performance"
endpoint = "http://clickhouse-server:8123"
batch.max_events = 100
batch.timeout_secs = 5
```

---

### 4. 启动 Vector

```bash
# Docker 方式
docker run -d \
  -v ./vector.toml:/etc/vector/vector.toml \
  -v /var/log/ginkgo:/var/log/ginkgo \
  timberio/vector:latest

# 或使用 Docker Compose
docker-compose up -d vector
```

---

## 基本使用

### 日志输出

```python
from ginkgo.libs import GLOG

# 基础日志输出
GLOG.info("这是一条信息日志")
GLOG.error("这是一条错误日志")

# 绑定业务上下文
GLOG.bind_context(portfolio_id="portfolio-001", strategy_id="strategy-ma")
GLOG.info("信号生成成功")

# 设置追踪 ID
GLOG.set_trace_id("trace-abc-123")
GLOG.info("处理订单")

# 记录性能日志
GLOG.log_performance(
    duration_ms=123.45,
    function_name="calculate_signals",
    memory_mb=256.78,
    cpu_percent=45.6
)

# 清理上下文
GLOG.clear_context()
```

---

### 日志查询

```python
from ginkgo import services

# 获取日志查询服务
log_service = services.logging.log_service

# 查询回测日志
logs = log_service.query_backtest_logs(
    portfolio_id="portfolio-001",
    level="ERROR",
    limit=50
)

# 按追踪 ID 查询完整链路日志
logs = log_service.query_by_trace_id("trace-abc-123")

# 查询性能日志
logs = log_service.query_performance_logs(
    min_duration=100.0,
    limit=50
)

# 关键词搜索
logs = log_service.search_logs(
    keyword="数据库连接失败",
    level="ERROR"
)
```

---

### 动态日志级别管理

```bash
# CLI 命令方式
ginkgo logging set-level DEBUG --module backtest
ginkgo logging get-level
ginkgo logging reset-level
```

```python
# Python API 方式
from ginkgo import services
from ginkgo.enums import LEVEL_TYPES

level_service = services.logging.level_service

# 设置日志级别
level_service.set_level("backtest", LEVEL_TYPES.DEBUG)

# 获取日志级别
level = level_service.get_level("backtest")

# 重置日志级别
level_service.reset_levels()
```

---

## 配置说明

### GCONF 配置项

在 `~/.ginkgo/config.yaml` 中添加：

```yaml
# 日志配置
logging:
  # 日志模式：container/local/auto
  mode: auto

  # 是否输出 JSON 格式
  json_output: true

  # 日志文件路径
  file_path: /var/log/ginkgo

  # TTL 配置（天）
  ttl_backtest: 180
  ttl_component: 90
  ttl_performance: 30

  # DEBUG 日志采样率
  sampling_rate: 0.1

  # 模块级别配置
  level_modules:
    backtest: INFO
    trading: INFO
    data: INFO
    analysis: INFO

  # 允许动态调整的模块白名单
  level_whitelist:
    - backtest
    - trading
    - data
    - analysis

  # 告警配置
  alerts:
    dingtalk:
      webhook_url: "https://oapi.dingtalk.com/robot/send?access_token=xxx"
      secret: "SECxxx"
    wechat:
      webhook_url: "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"
    email:
      smtp_host: "smtp.gmail.com"
      smtp_port: 587
      smtp_user: "alert@ginkgo.com"
      smtp_password: "xxx"
      from_addr: "alert@ginkgo.com"
      to_addrs:
        - "admin@ginkgo.com"
```

---

## 本地开发模式

在本地非容器环境开发时，GLOG 自动使用本地文件日志和控制台输出：

```python
# GLOG 自动检测环境
# 容器环境：JSON 格式输出到 /var/log/ginkgo/*.log
# 本地环境：Rich 格式输出到控制台 + ~/.ginkgo/logs/*.log

# 强制使用本地模式
import os
os.environ["LOGGING_MODE"] = "local"

from ginkgo.libs import GLOG
GLOG.info("本地开发日志")  # Rich 格式控制台输出
```

---

## 常见问题

### Q1: 日志没有写入 ClickHouse

**排查步骤**:
1. 检查 Vector 是否正常运行：`docker ps | grep vector`
2. 检查 Vector 日志：`docker logs vector`
3. 检查 ClickHouse 连接：`ginkgo clickhouse test`
4. 检查日志文件是否存在：`ls -la /var/log/ginkgo/`

---

### Q2: 动态日志级别不生效

**排查步骤**:
1. 检查模块是否在白名单中：`GCONF.LOGGING_LEVEL_WHITELIST`
2. 检查模块名称是否正确：使用 `ginkgo logging get-level` 查看
3. 核心模块（libs、services）不支持动态调整

---

### Q3: Trace ID 丢失

**排查步骤**:
1. 确保在请求入口处调用 `GLOG.set_trace_id()`
2. 检查跨容器调用是否通过 Kafka 消息携带 trace_id
3. 异步任务中确保使用 contextvars 传播上下文

---

### Q4: 日志查询慢

**优化建议**:
1. 缩小时间范围查询
2. 使用更精确的过滤条件（portfolio_id、strategy_id）
3. 增加 ClickHouse 分区粒度
4. 使用 LIMIT 限制返回结果数量

---

## 示例场景

### 场景 1: 回测日志追踪

```python
from ginkgo.libs import GLOG
from ginkgo import services

# 设置追踪 ID
trace_id = GLOG.set_trace_id()

# 绑定业务上下文
GLOG.bind_context(portfolio_id="portfolio-001", strategy_id="strategy-ma")

# 执行回测
GLOG.info("开始回测")
# ... 回测逻辑 ...

# 查询回测日志
log_service = services.logging.log_service
logs = log_service.query_backtest_logs(
    portfolio_id="portfolio-001"
)

# 清理上下文
GLOG.clear_context()
```

---

### 场景 2: 跨服务请求追踪

```python
# LiveCore（数据层）
from ginkgo.libs import GLOG

trace_id = GLOG.set_trace_id()
GLOG.info("Price update received")

# 通过 Kafka 消息携带 trace_id
kafka_message = {"trace_id": trace_id, "data": {...}}

# ExecutionNode（执行层）
trace_id = kafka_message["trace_id"]
GLOG.set_trace_id(trace_id)
GLOG.info("Processing order")  # 相同的 trace_id
```

---

### 场景 3: 性能监控

```python
from ginkgo.libs import GLOG
import time

def calculate_signals():
    start_time = time.time()

    # ... 业务逻辑 ...

    duration_ms = (time.time() - start_time) * 1000
    GLOG.log_performance(
        duration_ms=duration_ms,
        function_name="calculate_signals",
        module_name="ginkgo.core.strategies"
    )
```

---

### 场景 4: 日志告警配置

```python
from ginkgo import services

alert_service = services.logging.alert_service

# 添加告警规则
alert_service.add_alert_rule(
    rule_name="high_error_rate",
    pattern="ERROR",
    threshold=10,
    time_window=5,
    alert_channel="dingtalk"
)

# 定期检查告警（如每分钟执行一次）
alerts = alert_service.check_error_patterns()
for alert in alerts:
    alert_service.send_alert(alert["message"], alert["channel"])
```

---

## 下一步

- 查看完整 API 文档：[contracts/](contracts/)
- 了解数据模型：[data-model.md](data-model.md)
- 阅读技术调研：[research.md](research.md)
- 查看功能规格：[spec.md](spec.md)
