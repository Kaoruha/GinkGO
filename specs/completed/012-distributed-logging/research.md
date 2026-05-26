# Research: 容器化分布式日志系统 (Loki Only)

**Date**: 2026-02-26
**Feature**: 012-distributed-logging
**Status**: Completed

## 技术决策总结

### 1. 架构决策：Loki Only

**决策**: 当前实现采用 Loki Only 架构，不实现 ClickHouse 写入

**理由**:
- 架构简单，易于维护
- 日志写入路径：GLOG → structlog → JSON → stdout/stderr → Promtail → Loki
- 日志查询路径：
  - 运维监控：Grafana 直接查询 Loki
  - 业务查询：LogService 封装 Loki API，供 Web UI 调用
- 满足个人系统的运维监控和日志查询需求
- 未来可扩展 ClickHouse 用于复杂业务查询

**数据流**:
```
# 写入路径
GLOG.INFO() → structlog → JSON → stdout/stderr → Promtail → Loki

# 查询路径
运维监控: Grafana → Loki
业务查询: Web UI → LogService → Loki API
```

### 2. structlog 集成方案

**决策**: 使用 structlog.stdlib 配置

**实现方案**:
```python
import structlog

# 配置 structlog
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer,
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        ecs_processor,              # ECS 字段映射
        ginkgo_processor,           # ginkgo.* 业务字段
        container_metadata_processor, # 容器元数据
        error_control_processor,    # 错误流量控制
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)
```

### 3. 容器环境检测

**决策**: 多层检测策略

```python
def is_container_environment() -> bool:
    # 1. 环境变量
    if os.getenv("DOCKER_CONTAINER"): return True
    if os.getenv("KUBERNETES_SERVICE_HOST"): return True

    # 2. /proc/1/cgroup
    try:
        with open("/proc/1/cgroup") as f:
            return any(x in f.read() for x in ["docker", "kubepods"])
    except:
        pass

    # 3. /.dockerenv
    return os.path.exists("/.dockerenv")
```

### 4. contextvars trace_id 传播

**决策**: 使用 contextvars.ContextVar

```python
_trace_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "trace_id", default=None
)

class GinkgoLogger:
    def set_trace_id(self, trace_id: str) -> contextvars.Token:
        return _trace_id_ctx.set(trace_id)

    def get_trace_id(self) -> Optional[str]:
        return _trace_id_ctx.get()
```

### 5. ECS + ginkgo.* 字段映射

**ECS 字段**:
- @timestamp, log.level, log.logger, message
- process.pid, host.hostname
- container.id, kubernetes.pod.name, kubernetes.namespace
- trace.id, span.id

**ginkgo.* 扩展字段**:
- ginkgo.log_category (system/backtest)
- ginkgo.strategy_id (UUID)
- ginkgo.portfolio_id (UUID)
- ginkgo.event_type (string)
- ginkgo.symbol (string)

### 6. LogService 架构决策

**决策**: 在 Service 层提供 LogService，封装 Loki LogQL 查询 API

**理由**:
- 统一 API 入口：Web UI 通过 services.logging.log_service() 访问
- 业务友好：提供按 portfolio_id、strategy_id 等业务字段查询的方法
- 优雅降级：处理 Loki 不可用的情况，返回友好错误

**实现方案**:
```python
# Loki HTTP 客户端
class LokiClient:
    def query(self, logql: str, limit: int = 100) -> List[Dict]:
        """调用 Loki HTTP API 查询日志"""
        response = requests.get(
            f"{self.base_url}/loki/api/v1/query",
            params={"query": logql, "limit": limit}
        )
        return self._parse_response(response)

# LogService 封装
class LogService:
    def query_logs(
        self,
        portfolio_id: Optional[str] = None,
        strategy_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        level: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """构造 LogQL 查询并调用 Loki API"""
        logql = self._build_logql(
            portfolio_id, strategy_id, trace_id, level
        )
        return self.loki_client.query(logql, limit)

    def _build_logql(self, **filters) -> str:
        """构建 LogQL 查询字符串"""
        # {log_category="backtest", portfolio_id="xxx"} |= "" [1h]
        pass
```

## 未来扩展：ClickHouse

当需要以下功能时，可考虑添加 ClickHouse：

1. 复杂统计分析（错误率、性能分析）
2. 与订单/持仓数据 JOIN
3. 自定义报表
4. 批量数据导出

**扩展点设计**:
```python
# 未来扩展点
class GinkgoLogger:
    def INFO(self, msg: str):
        log_entry = self._format_log("INFO", msg)

        # 当前: 只输出到 stdout/stderr
        print(json.dumps(log_entry))

        # 未来扩展: 可选写入 ClickHouse
        # if self.config.clickhouse_enabled:
        #     self.async_writer.write(log_entry)
```
