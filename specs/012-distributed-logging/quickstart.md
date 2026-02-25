# 快速开始：容器化分布式日志系统 (Loki Only)

**Feature**: 012-distributed-logging
**Last Updated**: 2026-02-26

## 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                    应用代码                                  │
│                  GLOG.INFO("...")                            │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│                structlog → JSON                             │
└─────────────────────┬───────────────────────────────────────┘
                      │
        ┌─────────────┴─────────────┐
        ▼                             ▼
┌───────────────────┐        ┌─────────────────┐
│   宿主机本地模式    │        │    容器模式      │
├───────────────────┤        ├─────────────────┤
│ • 文件日志         │        │ • JSON stdout   │
│ • Rich 控制台      │        │ • Promtail      │
└───────────────────┘        └────────┬────────┘
                                     │
                                     ▼
                          ┌──────────────────────┐
                          │        Loki           │
                          │  • 日志存储           │
                          │  • 标签索引           │
                          └──────────┬───────────┘
                                     │
                                     ▼
                          ┌──────────────────────┐
                          │       Grafana         │
                          │  • 日志查询           │
                          │  • Dashboard          │
                          └──────────────────────┘
```

## 安装

```bash
pip install structlog>=24.0.0
```

## 配置

编辑 `~/.ginkgo/config.yaml`:

```yaml
logging:
  # 日志模式（推荐 auto）
  mode: auto              # auto: 自动检测容器环境
                           # container: 强制容器模式
                           # local: 强制本地模式

  # 日志格式
  format: json            # json: 结构化日志（容器/查询）
                           # plain: 纯文本（仅本地模式）

  # 日志级别
  level:
    console: INFO         # 控制台级别
    file: DEBUG           # 文件级别（本地模式）

  # 容器模式配置
  container:
    enabled: true         # 启用容器模式
    json_output: true     # JSON 输出

  # 本地模式配置
  local:
    file_enabled: true    # 启用文件日志
    file_path: "ginkgo.log"

  # 敏感字段脱敏（可选）
  mask_fields:
    - password
    - secret
    - token
```

## 基本使用

### 1. 系统级日志

```python
from ginkgo.libs import GLOG

# 基本日志（完全兼容现有代码）
GLOG.DEBUG("Detailed debugging info")
GLOG.INFO("Engine started")
GLOG.WARN("High memory usage")
GLOG.ERROR("Database connection failed")
GLOG.CRITICAL("System shutdown")
```

### 2. 业务级日志（回测）

```python
# 设置日志类别
GLOG.set_log_category("backtest")

# 绑定业务上下文（自动添加到所有后续日志）
GLOG.bind_context(
    strategy_id=strategy.uuid,
    portfolio_id=portfolio.uuid
)

# 业务日志（自动包含策略和组合信息）
GLOG.INFO(f"Signal generated: BUY {symbol}")

# 清除上下文
GLOG.clear_context()
```

### 3. 分布式追踪

```python
# 方式1: 手动设置
token = GLOG.set_trace_id("trace-123")
GLOG.INFO("Processing request")
GLOG.clear_trace_id(token)

# 方式2: 上下文管理器（推荐）
with GLOG.with_trace_id("trace-456"):
    GLOG.INFO("Step 1")
    GLOG.INFO("Step 2")
# trace_id 自动清除

# 获取当前 trace_id
current_trace = GLOG.get_trace_id()
```

### 4. 跨服务追踪

```python
# Service A: 发起请求
def process_request():
    trace_id = f"trace-{uuid.uuid4()}"
    GLOG.set_trace_id(trace_id)
    GLOG.INFO("Request started")

    # 在 HTTP header 中传递 trace_id
    headers = {"X-Trace-ID": trace_id}
    response = requests.post(url, headers=headers)

    GLOG.INFO("Request completed")

# Service B: 接收请求
def handle_request():
    # 从 header 中获取 trace_id
    trace_id = request.headers.get("X-Trace-ID")
    if trace_id:
        GLOG.set_trace_id(trace_id)
    GLOG.INFO("Processing in Service B")
```

## 多线程与并发使用

### contextvars 线程隔离保证

**重要**: `contextvars` 是**线程隔离**的，每个线程有自己独立的上下文存储，多线程环境下**不会串**。

### 多线程回测示例

```python
from ginkgo.libs import GLOG
import threading

def process_backtest(portfolio_id, strategy_id):
    """每个线程处理一个回测"""
    # 设置业务上下文（每个线程独立）
    GLOG.set_log_category("backtest")
    GLOG.bind_context(
        portfolio_id=portfolio_id,
        strategy_id=strategy_id
    )

    # 这个线程的所有日志都有正确的上下文
    GLOG.INFO(f"Processing {portfolio_id}")

    # 模拟耗时操作
    import time
    time.sleep(1)

    # 依然正确（不会和其他线程串）
    GLOG.INFO(f"Completed {portfolio_id}")

    # 清理上下文
    GLOG.clear_context()

# 启动多个线程处理不同回测
threads = [
    threading.Thread(
        target=process_backtest,
        args=("portfolio-aaa", "strategy-1")
    ),
    threading.Thread(
        target=process_backtest,
        args=("portfolio-bbb", "strategy-1")
    ),
    threading.Thread(
        target=process_backtest,
        args=("portfolio-ccc", "strategy-2")
    ),
]

for t in threads:
    t.start()

for t in threads:
    t.join()

# Loki 中每个日志都有正确的 portfolio_id，不会串
```

### 线程池示例

```python
from concurrent.futures import ThreadPoolExecutor

def process_task(task_id):
    # 每个任务独立绑定上下文
    GLOG.bind_context(task_id=task_id)
    GLOG.INFO(f"Processing task {task_id}")
    # 执行任务...
    GLOG.unbind_context("task_id")

# 线程池中也是安全的
with ThreadPoolExecutor(max_workers=4) as executor:
    futures = [
        executor.submit(process_task, f"task-{i}")
        for i in range(10)
    ]
```

### 多进程说明

```python
from multiprocessing import Process

def worker(trace_id):
    GLOG.set_trace_id(trace_id)
    GLOG.INFO(f"Worker with {trace_id}")

# 多进程中每个进程有独立的 context，自然隔离
processes = [
    Process(target=worker, args=("trace-A",)),
    Process(target=worker, args=("trace-B",)),
]

for p in processes:
    p.start()
```

### 异步代码（async/await）

```python
import asyncio

async def handle_request(trace_id):
    # 在异步函数中设置
    token = GLOG.set_trace_id(trace_id)

    # 自动传播到所有 await 的子函数
    await step1()
    await step2()

    GLOG.clear_trace_id(token)

async def step1():
    # 可以获取到 caller 的 trace_id
    trace = GLOG.get_trace_id()
    GLOG.INFO(f"step1: trace_id = {trace}")

async def step2():
    # 也可以获取到
    trace = GLOG.get_trace_id()
    GLOG.INFO(f"step2: trace_id = {trace}")
```

### 并发场景的最佳实践

| 场景 | 是否安全 | 注意事项 |
|------|---------|----------|
| **多线程** | ✅ 安全 | 每个 Thread 独立 context，结束后清理 |
| **async/await** | ✅ 安全 | context 自动传播到子协程 |
| **多进程** | ✅ 安全 | 进程间天然隔离 |
| **线程池** | ✅ 安全 | 每个任务独立 context |
| **混合模式** | ✅ 安全 | 混用也安全，各线程/进程独立 |

### 回测场景推荐写法

```python
# 回测引擎中使用（支持多策略并行）
class EngineHistoric:
    def run(self, portfolio):
        # 在引擎入口绑定上下文
        GLOG.set_log_category("backtest")
        GLOG.bind_context(
            portfolio_id=portfolio.uuid,
            engine_id=self.uuid
        )

        try:
            GLOG.info("Engine started")
            self._run_backtest()
            GLOG.info("Engine completed")
        finally:
            # 务必清理上下文
            GLOG.clear_context()
```

## Loki 日志查询

### 1. Grafana 查询界面

访问 Grafana → Explore → 选择 Loki 数据源

### 2. LogQL 查询示例

```logql
# 查看所有日志
{}

# 按日志类别过滤
{log_category="backtest"}

# 按级别过滤
{level="error"}

# 按 trace_id 过滤
{trace_id="trace-123"}

# 内容搜索
{log_category="system"} |= "Engine"

# 组合查询
{log_category="backtest", level="error"} |= "database"

# 时间范围
{level="error"} [1h]

# 正则匹配
{log_category="backtest"} |= "~.*Signal.*"
```

### 3. 常用查询场景

```logql
# 1. 查看最近的错误日志
{level="error"} |= "" [1h]

# 2. 查看特定回测的日志
{strategy_id="550e8400-..."} [1d]

# 3. 查看完整的请求链路
{trace_id="trace-123"}

# 4. 按组件查看日志
{logger_name="ginkgo.engine"} [1h]

# 5. 统计错误数量
count_over_time({level="error"}[1h])

# 6. 按类别统计
count by (log_category) ({}) [1d]
```

## Service 层日志查询

### 1. 基本查询

```python
from ginkgo import services

log_service = services.logging.log_service()

# 查询某个回测的所有日志
logs = log_service.query_by_portfolio(
    portfolio_id=str(portfolio.uuid),
    limit=200
)

# 遍历日志
for log in logs:
    print(f"[{log['level']}] {log['message']}")
```

### 2. 条件过滤查询

```python
# 查询错误日志
errors = log_service.query_logs(
    portfolio_id=str(portfolio.uuid),
    level="error",
    limit=50
)

# 查询特定时间范围的日志
from datetime import datetime, timedelta

logs = log_service.query_logs(
    portfolio_id=str(portfolio.uuid),
    start_time=datetime.now() - timedelta(hours=1),
    end_time=datetime.now()
)

# 分页查询
page1 = log_service.query_by_portfolio(
    portfolio_id=str(portfolio.uuid),
    limit=100,
    offset=0
)
page2 = log_service.query_by_portfolio(
    portfolio_id=str(portfolio.uuid),
    limit=100,
    offset=100
)
```

### 3. 追踪链路查询

```python
# 查询完整的请求链路
trace_logs = log_service.query_by_trace_id(trace_id="trace-123")

# 链路日志按时间排序
trace_logs.sort(key=lambda x: x['timestamp'])
```

### 4. 错误日志专用查询

```python
# 查询某个回测的所有错误
errors = log_service.query_errors(
    portfolio_id=str(portfolio.uuid),
    limit=100
)

# 统计错误数量
error_count = log_service.get_log_count(
    portfolio_id=str(portfolio.uuid),
    level="error"
)
```

### 5. Web UI 集成示例

```python
from fastapi import APIRouter
from ginkgo import services

router = APIRouter()
log_service = services.logging.log_service()

@router.get("/api/backtests/{portfolio_id}/logs")
async def get_backtest_logs(
    portfolio_id: str,
    level: str = None,
    limit: int = 100,
    offset: int = 0
):
    """获取回测日志API"""
    try:
        logs = log_service.query_logs(
            portfolio_id=portfolio_id,
            level=level,
            limit=limit,
            offset=offset
        )
        return {"success": True, "data": logs}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

### 6. 错误处理

```python
from ginkgo.libs.exceptions import ServiceUnavailable

try:
    logs = log_service.query_by_portfolio(portfolio_id="xxx")
except ServiceUnavailable:
    # Loki 不可用时的处理
    print("无法连接到日志服务")
    logs = []
```

## 容器环境使用

### 1. Docker Compose 配置

```yaml
version: '3.8'

services:
  ginkgo:
    image: ginkgo:latest
    environment:
      - LOGGING_MODE=container
      - LOGGING_FORMAT=json
    # 日志由容器平台捕获
    depends_on:
      - loki

  # Promtail: 日志采集器
  promtail:
    image: grafana/promtail:latest
    volumes:
      - /var/log:/var/log:ro
      - ./promtail-config.yml:/etc/promtail/config.yml
    command: -config.file=/etc/promtail/config.yml

  # Loki: 日志数据库
  loki:
    image: grafana/loki:latest
    ports:
      - "3100:3100"

  # Grafana: 可视化
  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
```

### 2. Promtail 配置

```yaml
# promtail-config.yml
server:
  http_listen_port: 9080

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: ginkgo-logs
    docker_engine:
      host_filter: localhost
      relabel_configs:
        - source_labels:
            - __meta_docker_container_name
          target_label: container_name
        - regex: __meta_docker_container_name;^(?<pod_name>[^_]+)_(?<namespace>[^_]+)_(?<container_id>[^_]+)$
        - target_label: pod_name
        - target_label: namespace
        - target_label: container_id
```

### 3. Grafana 数据源配置

1. 打开 Grafana → Configuration → Data Sources
2. 添加 Loki 数据源
3. URL: `http://loki:3100`
4. 保存并测试

## 开发调试

### 1. 本地开发模式

```python
# 设置本地模式
import os
os.environ["LOGGING_MODE"] = "local"

from ginkgo.libs import GLOG

GLOG.INFO("Local log")  # 输出到文件和控制台
```

### 2. 调试模式

```python
GLOG.set_level("DEBUG", "console")
GLOG.DEBUG("Detailed info")
```

### 3. 错误统计

```python
stats = GLOG.get_error_stats()
print(f"错误模式数: {stats['total_error_patterns']}")
print(f"总错误次数: {stats['total_error_count']}")
```

## 常见问题

### Q1: 日志没有出现在 Loki

**检查**:
1. Promtail 是否运行：`docker logs promtail`
2. Promtail 配置是否正确
3. 容器日志路径是否存在：`ls /var/log/containers/`

### Q2: trace_id 没有关联日志

**检查**:
1. 是否设置了 trace_id：`GLOG.get_trace_id()`
2. 日志中是否包含 trace 字段

### Q3: JSON 格式不对

**检查**:
1. 配置: `GCONF.LOGGING_FORMAT == "json"`
2. 容器环境检测：`is_container_environment()` 返回值

### Q4: 性能问题

**解决**:
1. 减少日志级别（DEBUG → INFO）
2. 启用错误流量控制（已内置）

## 最佳实践

### 1. 日志级别使用

| 级别 | 使用场景 |
|------|----------|
| DEBUG | 详细调试信息 |
| INFO | 一般信息 |
| WARNING | 警告信息 |
| ERROR | 错误但可恢复 |
| CRITICAL | 严重错误 |

### 2. 业务上下文绑定

```python
def handle_backtest(strategy_id, portfolio_id):
    GLOG.set_log_category("backtest")
    GLOG.bind_context(
        strategy_id=strategy_id,
        portfolio_id=portfolio_id
    )
    try:
        GLOG.INFO("Starting backtest")
        run_backtest()
        GLOG.INFO("Backtest completed")
    finally:
        GLOG.clear_context()
```

### 3. 分布式追踪

```python
def handle_request(request_id):
    trace_id = generate_trace_id(request_id)
    with GLOG.with_trace_id(trace_id):
        GLOG.INFO("Request started")
        process_request()
        GLOG.INFO("Request completed")
```

## 进阶使用

### 1. 自定义 Processor

```python
import structlog

def custom_processor(logger, log_method, event_dict):
    # 添加自定义字段
    event_dict["app_name"] = "Ginkgo"
    event_dict["env"] = os.getenv("ENVIRONMENT", "dev")
    return event_dict

structlog.configure(processors=[..., custom_processor, ...])
```

### 2. 日志采样

```python
import random

def sampling_processor(sample_rate=0.1):
    def processor(logger, log_method, event_dict):
        if log_method == "info" and random.random() > sample_rate:
            raise structlog.DropEvent
        return event_dict
    return processor
```
