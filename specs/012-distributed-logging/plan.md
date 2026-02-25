# Implementation Plan: 容器化分布式日志系统 (Loki Only)

**Branch**: `012-distributed-logging` | **Date**: 2026-02-26 | **Spec**: [spec.md](spec.md)

## Summary

重构 GLOG 日志模块，从本地文件写入模式迁移到支持容器环境的分布式日志系统。使用 structlog 作为底层框架，实现 JSON 结构化日志输出到 stdout/stderr，由 Promtail 采集到 Loki，通过 Grafana 查询。保持现有 API 兼容性。TDD 驱动开发。

**架构决策**: 采用 Loki Only 架构，简化实现，未来可扩展 ClickHouse。

## Technical Context

**Language/Version**: Python 3.12.8
**Primary Dependencies**: structlog (新增), Rich (控制台), contextvars (trace_id)
**Storage**: Loki (日志数据库，通过 Promtail 采集)
**Testing**: pytest + TDD workflow, 测试覆盖率 > 85%
**Target Platform**: Linux server (容器化部署) + 宿主机 (开发调试)
**Project Type**: single (Python量化交易库)
**Performance Goals**:
- 日志序列化开销 < 0.1ms（JSON 格式化）
- stdout/stderr 写入不阻塞业务逻辑

**Constraints**:
- 保持现有 GLOG API 完全兼容
- 容器环境禁用本地文件写入
- 遵循事件驱动架构
- TDD 驱动，先写测试再实现

**Scope**:
- 当前实现: Loki Only（简化架构）
- 未来扩展: ClickHouse（复杂业务查询）

## Constitution Check

*GATE: Must pass before Phase 0 research.*

### 安全与合规原则
- [x] 敏感文件检查
- [x] 配置管理
- [x] .gitignore 配置

### 架构设计原则
- [x] 事件驱动架构
- [x] ServiceHub（日志模块不涉及服务注册）
- [x] 职责分离

### 代码质量原则
- [x] 装饰器使用
- [x] 类型注解
- [x] 命名规范

### 测试原则
- [x] TDD 流程
- [x] 测试分类
- [x] 真实环境测试（structlog 配置测试）

### 性能原则
- [x] 非阻塞 I/O（stdout/stderr）
- [x] 序列化优化

### 文档原则
- [x] 中文文档
- [x] API 示例

### 代码注释同步原则
- [x] 头部注释同步

**Gate Status**: ✅ PASSED

## Project Structure

### Documentation

```text
specs/012-distributed-logging/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (日志字段结构)
├── quickstart.md        # Phase 1 output
└── checklists/          # Quality checklists
    └── requirements.md
```

### Source Code

```text
src/ginkgo/
├── libs/
│   ├── core/
│   │   └── logger.py           # GLOG 重写（基于 structlog）
│   └── utils/
│       └── log_utils.py        # 日志工具（容器检测、元数据采集）
└── config/
    └── logging_config.py       # 日志配置扩展（GCONF）

src/ginkgo/services/logging/
├── __init__.py                 # Service 注册
├── log_service.py              # LogService（封装 Loki 查询 API）
└── clients/
    └── loki_client.py          # Loki HTTP 客户端

tests/unit/libs/
├── test_core_logger.py         # GLOG 单元测试
└── test_log_utils.py           # 日志工具测试

tests/unit/services/logging/
├── test_log_service.py         # LogService 单元测试
└── test_loki_client.py         # Loki 客户端测试
```

**Structure Decision**:
- 修改 `libs/core/logger.py` 基于 structlog 重写 GLOG
- 新增 `services/logging/log_service.py` 封装 Loki 查询 API（供 Web UI 调用）
- 新增 `services/logging/clients/loki_client.py` Loki HTTP 客户端实现

## Phase 0: Research

### Research Tasks

1. **structlog 集成方案研究**
   - 决策: 使用 structlog.stdlib.rebind_chars()
   - 理由: 与标准 logging 兼容，支持 context 绑定

2. **容器环境检测研究**
   - 决策: 环境变量 > /proc/1/cgroup > /.dockerenv
   - 理由: 多层检测确保准确性

3. **contextvars trace_id 传播研究**
   - 决策: 使用 contextvars.ContextVar
   - 理由: Python 标准库，原生支持异步

4. **ECS 字段映射研究**
   - 决策: ECS 基础字段 + ginkgo.* 扩展
   - 理由: 兼容标准，支持业务字段

## Phase 1: Design

### 数据模型

**structlog Event Dict (日志字段)**:

```python
{
    # ECS 标准字段
    "@timestamp": "2026-02-26T10:30:00.123456Z",
    "log": {"level": "info", "logger": "ginkgo.engine"},
    "message": "Engine started",

    # 容器元数据
    "host": {"hostname": "ginkgo-pod-abc123"},
    "process": {"pid": 12345},
    "container": {"id": "docker://abc123..."},
    "kubernetes": {
        "pod": {"name": "ginkgo-worker-0"},
        "namespace": "production"
    },

    # 追踪上下文
    "trace": {"id": "trace-123"},
    "span": {"id": "span-456"},

    # Ginkgo 业务字段
    "ginkgo": {
        "log_category": "system",  # system / backtest
        "strategy_id": "550e8400-...",
        "portfolio_id": "550e8400-...",
        "event_type": "ENGINE_STARTED",
        "symbol": "000001.SZ"
    }
}
```

### API Contracts

**GLOG API（保持兼容）**:

```python
class GinkgoLogger:
    # 日志记录
    def DEBUG(self, msg: str) -> None
    def INFO(self, msg: str) -> None
    def WARN(self, msg: str) -> None
    def ERROR(self, msg: str) -> None
    def CRITICAL(self, msg: str) -> None

    # 级别控制
    def set_level(self, level: str, handler_type: str = 'all') -> None
    def get_current_levels(self) -> Dict[str, str]

    # 追踪上下文
    def set_trace_id(self, trace_id: str) -> contextvars.Token
    def get_trace_id(self) -> Optional[str]
    def clear_trace_id(self, token: contextvars.Token) -> None
    def with_trace_id(self, trace_id: str) -> ContextManager

    # 业务上下文
    def set_log_category(self, category: str) -> None
    def bind_context(self, **kwargs) -> None
    def unbind_context(self, *keys: str) -> None
    def clear_context(self) -> None

    # 错误统计
    def get_error_stats(self) -> Dict[str, Any]
    def clear_error_stats(self) -> None
```

**LogService API（Loki 查询）**:

```python
class LogService:
    def query_logs(
        self,
        portfolio_id: Optional[str] = None,
        strategy_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        level: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]: ...

    def query_by_portfolio(self, portfolio_id: str, **kwargs) -> List[Dict]: ...
    def query_by_trace_id(self, trace_id: str) -> List[Dict]: ...
    def query_errors(self, portfolio_id: Optional[str] = None, **kwargs) -> List[Dict]: ...
    def get_log_count(self, portfolio_id: Optional[str] = None, level: Optional[str] = None) -> int: ...
```

### Configuration Schema

```yaml
# ~/.ginkgo/config.yaml
logging:
  mode: auto              # auto / container / local
  format: json            # json / plain (仅 local)
  level:
    console: INFO
    file: DEBUG
  container:
    enabled: true
    json_output: true
  local:
    file_enabled: true
    file_path: "ginkgo.log"
  mask_fields:            # 敏感字段脱敏
    - password
    - secret
    - token
```

## Implementation Phases

### Phase 0: Research ✅
- [x] Spec 澄清完成
- [x] 架构决策完成（Loki Only）

### Phase 1: Design ✅
- [x] 生成 research.md
- [x] 生成 data-model.md
- [x] 生成 contracts/log-api-contract.md
- [x] 生成 quickstart.md
- [x] 添加 LogService 架构设计

### Phase 2: Implementation (via /speckit.tasks)
- [ ] GLOG 重写（structlog 适配）
- [ ] 容器环境检测
- [ ] trace_id 上下文管理
- [ ] 业务上下文绑定
- [ ] 错误流量控制迁移
- [ ] 配置扩展（GCONF）
- [ ] **LogService 实现**（封装 Loki 查询 API）
  - [ ] Loki HTTP 客户端实现
  - [ ] LogQL 查询封装
  - [ ] 分页和过滤支持
  - [ ] 错误处理（Loki 不可用）
- [ ] **ServiceHub 注册**（log_service）
- [ ] 测试（TDD，覆盖率 > 85%）

## Dependencies

**新增依赖**:
- `structlog>=24.0.0`
- `requests>=2.31.0` - Loki HTTP 客户端（现有依赖，复用）

**现有依赖复用**:
- `rich` - 控制台输出（本地模式）
- `pydantic` - LogService 响应模型验证

## Risks & Mitigations

| 风险 | 缓解措施 |
|------|----------|
| structlog 性能开销 | 性能测试验证 |
| 向后兼容性破坏 | 严格 API 兼容测试 |
| contextvars 兼容性 | 异步测试覆盖 |
| Loki 不可用影响查询 | LogService 优雅降级，返回友好错误 |
| Loki API 变更 | 封装客户端层，降低变更影响 |

## Success Metrics

- [ ] 所有现有 GLOG 调用无需修改
- [ ] 容器环境日志以 JSON 格式输出到 stdout/stderr
- [ ] 100% 的日志包含容器元数据
- [ ] 95% 的请求日志可通过 trace_id 关联
- [ ] 测试覆盖率 > 85%
