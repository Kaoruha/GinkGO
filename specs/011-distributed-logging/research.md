# Research: 分布式日志系统优化重构

**Feature**: 011-distributed-logging
**Date**: 2026-03-10
**Status**: Complete

## Overview

本文档记录分布式日志系统重构的技术调研结果，包括技术选型决策、最佳实践研究和架构设计确认。

---

## 1. 日志框架选型：structlog

### Decision: 使用 structlog 作为底层日志框架

**Rationale**:
- structlog 原生支持 JSON 输出格式，无需额外配置
- 内置 contextvars 支持，自动处理异步上下文传播
- 提供丰富的处理器链，可灵活定制日志格式
- 与现有 GLOG API 兼容性好，可保持向后兼容
- 社区活跃，文档完善，性能优秀

**Alternatives Considered**:
1. **标准 logging 模块**: 不支持原生 JSON 输出，context 管理复杂
2. **loguru**: 功能丰富但配置较重，与现有代码集成成本高
3. **自定义 JSON logger**: 开发成本高，维护负担重

**Implementation Notes**:
```python
import structlog
from contextvars import ContextVar

# contextvar 用于追踪上下文传播
trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")

# structlog 配置
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)
```

---

## 2. 日志采集架构：Vector + ClickHouse

### Decision: Vector 采集 + ClickHouse 存储（分表设计）

**Rationale**:
- **应用解耦**: 应用只输出 JSON 日志到文件/stdout，Vector 负责采集和存储
- **高性能**: Rust 编写的 Vector 内存占用低、吞吐量高（>10000 条/秒）
- **可靠性**: 支持断点续传、磁盘缓存、自动重试机制
- **灵活路由**: 通过 log_category 字段路由到不同 ClickHouse 表
- **查询优化**: ClickHouse 列式存储天然适合高基数字段查询（portfolio_id、trace_id）
- **TTL 管理**: ClickHouse 原生支持 TTL 自动清理过期数据

**Alternatives Considered**:
1. **Loki**: 高基数字段查询性能差，不适合回测日志分析场景
2. **Elasticsearch**: 资源占用高，运维复杂，成本高昂
3. **应用直写 ClickHouse**: 应用与存储强耦合，ClickHouse 不可用影响业务

**Vector 配置要点**:
```toml
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
```

---

## 3. ClickHouse 表结构设计：三表分离

### Decision: 三张独立日志表（backtest、component、performance）

**Rationale**:
- **查询优化**: 每张表针对特定查询场景优化索引和分区
- **TTL 差异**: 不同类型日志保留策略不同（backtest 180天、component 90天、performance 30天）
- **字段隔离**: 避免无效字段占用存储空间（如 performance 表的 duration_ms 对其他表无意义）
- **维护便利**: 可独立对每张表进行优化、备份、清理操作

**表结构设计原则**:
1. **分区策略**: `(toDate(timestamp), 业务字段)` 复合分区，提升查询性能
2. **排序键**: `(timestamp, trace_id, 业务键)` 优化时序查询和关联查询
3. **TTL 配置**: 通过 GCONF 动态配置，支持运行时调整
4. **字段类型**: 使用 String 存储枚举名称（可读性强），Int8 存储枚举值

**Alternatives Considered**:
1. **单表 + log_category 字段**: 索引效率低、TTL 配置复杂、存储浪费
2. **Loki + ClickHouse 混合**: 架构复杂、运维成本高、数据一致性难保证

---

## 4. SQLAlchemy Model 类设计

### Decision: 创建 MBacktestLog、MComponentLog、MPerformanceLog 三个 Model 类

**Rationale**:
- **表结构文档化**: Model 类即表结构文档，代码即文档
- **类型安全**: 编译时类型检查，减少运行时错误
- **CREATE TABLE 生成**: 支持通过 Model 类自动生成建表语句
- **与现有代码一致**: 项目已有大量 Model 类（MBar、MTick 等），保持模式统一
- **字段校验**: Model 类可作为 GLOG 输出前的字段校验器

**Model 类设计要点**:
```python
class MBacktestLog(MClickBase):
    """回测日志表 Model"""
    __tablename__ = "ginkgo_logs_backtest"
    __table_args__ = (
        engines.MergeTree(
            partition_by="(toDate(timestamp), portfolio_id)",
            order_by=("timestamp", "portfolio_id", "trace_id")
        ),
        {"extend_existing": True},
    )

    # 基础字段
    level: Mapped[str] = mapped_column(String(), default="INFO")
    message: Mapped[str] = mapped_column(String(), default="")
    logger_name: Mapped[str] = mapped_column(String(), default="")

    # 追踪字段
    trace_id: Mapped[Optional[str]] = mapped_column(String(), default=None)
    span_id: Mapped[Optional[str]] = mapped_column(String(), default=None)

    # 业务字段
    portfolio_id: Mapped[Optional[str]] = mapped_column(String(), default=None)
    strategy_id: Mapped[Optional[str]] = mapped_column(String(), default=None)
    # ... 更多字段
```

**Alternatives Considered**:
1. **仅提供 DDL SQL**: 难以维护、容易与实际表结构不一致
2. **手动维护文档**: 文档容易过时、无法自动化校验

---

## 5. 日志级别枚举设计

### Decision: 添加 LEVEL_TYPES 枚举到 `enums.py`

**Rationale**:
- 与项目现有枚举模式一致（EnumBase、validate_input、from_int）
- 支持枚举与整数双向转换，数据库存储整数节省空间
- 提供 Level 名称到值的映射，便于日志输出和查询

**枚举定义**:
```python
class LEVEL_TYPES(EnumBase):
    VOID = -1
    DEBUG = 0
    INFO = 1
    WARNING = 2
    ERROR = 3
    CRITICAL = 4
```

---

## 6. 日志类别枚举设计

### Decision: 添加 LOG_CATEGORY_TYPES 枚举到 `enums.py`

**Rationale**:
- 明确区分日志类型，用于 Vector 路由决策
- 支持扩展新的日志类别（如 security、audit）
- 与现有枚举模式保持一致

**枚举定义**:
```python
class LOG_CATEGORY_TYPES(EnumBase):
    VOID = -1
    BACKTEST = 0      # 回测业务日志
    COMPONENT = 1     # 组件运行日志
    PERFORMANCE = 2   # 性能监控日志
```

---

## 7. Trace ID 传播机制

### Decision: 基于 contextvars 的上下文传播

**Rationale**:
- contextvars 是 Python 3.7+ 标准库，无需额外依赖
- 天然支持异步上下文传播（async/await）
- 线程隔离，每个线程有独立上下文
- structlog 原生支持 contextvars 绑定

**实现模式**:
```python
from contextvars import ContextVar
import uuid

_trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")

def set_trace_id(trace_id: str = None) -> str:
    """设置当前线程/协程的 trace_id"""
    if trace_id is None:
        trace_id = str(uuid.uuid4())
    _trace_id_var.set(trace_id)
    return trace_id

def get_trace_id() -> str:
    """获取当前线程/协程的 trace_id"""
    return _trace_id_var.get()
```

**跨容器传播**:
- LiveCore 通过 Kafka 消息携带 trace_id
- ExecutionNode 从 Kafka 消息中恢复 trace_id
- ClickHouse 按 trace_id 查询关联所有日志

---

## 8. 容器环境检测

### Decision: 多重检测机制（环境变量 + 文件标志）

**Rationale**:
- 兼容 Docker 和 Kubernetes 环境
- 提供降级机制，检测失败默认使用 local 模式
- 支持强制模式配置（通过 GCONF.LOGGING_MODE）

**检测逻辑**:
```python
def is_container_environment() -> bool:
    """检测是否运行在容器环境中"""
    # 环境变量检测
    if os.getenv("DOCKER_CONTAINER") == "true":
        return True
    if os.getenv("KUBERNETES_SERVICE_HOST"):
        return True

    # 文件标志检测
    if os.path.exists("/.dockerenv"):
        return True
    if os.path.exists("/proc/1/cgroup"):
        with open("/proc/1/cgroup") as f:
            if "docker" in f.read() or "kubepods" in f.read():
                return True

    return False
```

---

## 9. 动态日志级别管理

### Decision: 基于 structlog 的标准日志处理器动态调整

**Rationale**:
- structlog 基于标准 logging 模块，可动态调整 handler 级别
- 无需重启服务，立即生效
- 支持按模块分别设置不同级别
- 通过 GCONF 配置模块白名单，防止误操作

**实现要点**:
```python
def set_module_level(module_name: str, level: LEVEL_TYPES) -> None:
    """动态设置模块日志级别"""
    logger = logging.getLogger(module_name)
    logger.setLevel(level.to_int())

def get_all_levels() -> Dict[str, int]:
    """获取所有模块的当前日志级别"""
    return {
        name: logging.getLogger(name).level
        for name in logging.root.manager.loggerDict
    }
```

---

## 10. Vector 部署模式

### Decision: Docker Compose 部署（单实例）

**Rationale**:
- 单个 Vector 实例可采集多个日志文件（通配符支持）
- 支持断点续传，无需主备高可用
- 部署简单，资源占用低（< 200MB）
- 通过 Docker Compose 与 ClickHouse、应用容器协同部署

**Docker Compose 配置**:
```yaml
services:
  vector:
    image: timberio/vector:latest
    volumes:
      - ./vector.toml:/etc/vector/vector.toml
      - /var/log/ginkgo:/var/log/ginkgo
      - vector_data:/vector_data
    depends_on:
      - clickhouse
```

---

## 11. 日志采样策略

### Decision: 基于日志级别的智能采样

**Rationale**:
- 生产环境 DEBUG 日志量大，采样率 10% 减少存储和查询压力
- ERROR 和 CRITICAL 日志 100% 记录，确保问题排查能力
- 通过 GCONF.LOGGING_SAMPLING_RATE 配置采样率
- structlog 支持自定义采样处理器

**采样实现**:
```python
class SamplingProcessor:
    def __init__(self, sampling_rate: float = 0.1):
        self.sampling_rate = sampling_rate

    def __call__(self, logger, method_name, event_dict):
        if event_dict["level"] == "debug":
            if random.random() > self.sampling_rate:
                raise DropEvent  # 丢弃日志
        return event_dict
```

---

## 12. 告警抑制机制

### Decision: 基于时间窗口的告警去重

**Rationale**:
- 避免告警风暴，相同错误 5 分钟内只发送一次
- ClickHouse 查询统计错误频率，超过阈值触发告警
- Redis 存储告警发送记录（TTL 5 分钟）
- 告警渠道失败不影响应用运行

**实现要点**:
```python
def should_send_alert(error_pattern: str) -> bool:
    """检查是否应该发送告警"""
    key = f"alert:{error_pattern}"
    if redis_client.exists(key):
        return False
    redis_client.setex(key, 300, "1")  # 5分钟TTL
    return True
```

---

## 总结

本调研完成了分布式日志系统重构的关键技术决策：

1. **日志框架**: structlog（JSON 输出、contextvars 支持）
2. **采集架构**: Vector + ClickHouse（应用解耦、高性能）
3. **存储设计**: 三表分离（backtest、component、performance）
4. **Model 类**: SQLAlchemy Model 类（MBacktestLog、MComponentLog、MPerformanceLog）
5. **枚举类型**: LEVEL_TYPES、LOG_CATEGORY_TYPES
6. **追踪机制**: contextvars + trace_id
7. **部署模式**: Docker Compose 单实例 Vector

所有技术选型均基于项目现有架构模式，确保与 Ginkgo 量化交易库的无缝集成。
