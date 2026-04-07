# AaaS 平台架构设计决策记录

> 日期：2026-03-29
> 状态：初步设计
> 目标：将 AgentLoop Core 从可运行 demo 演进为可水平扩展的服务化平台

---

## 1. 平台解耦策略

### 1.1 核心原则

Agent 平台当作**对外 SaaS 开发**，云平台只是它的一个"客户"。Agent 平台零依赖云平台。

### 1.2 标准协议栈

| 协议 | 用途 | 说明 |
|------|------|------|
| OAuth 2.0 + OIDC | 认证授权 | Agent 平台签发 token，云平台通过 OAuth 关联 |
| OpenAPI 3.1 | API 契约 | 双方按 spec 开发，互不阻塞 |
| CloudEvents 1.0 | Webhook 格式 | 异步事件通知的标准信封 |
| postMessage | iframe 通信 | 父子页面跨域通信协议 |
| Portal 协议 | 弹窗提升 | Agent 内弹窗投射到父页面渲染 |

### 1.3 集成架构

```
云平台                              Agent 平台
┌─────────────┐     ┌──────────────────────┐
│  iframe 嵌入│◄───►│  Web UI（独立部署）   │
│  BFF 聚合   │◄───►│  REST API            │
│  Webhook接收│◄───►│  Webhook 发送        │
└─────────────┘     └──────────────────────┘
       ↑                    ↑
       └── OAuth Token ─────┘
```

---

## 2. 页面嵌入方案

### 2.1 iframe + postMessage

- Agent 平台独立部署，云平台通过 iframe 嵌入
- 跨窗口通信通过 postMessage，协议版本化（v1/agent/result）

### 2.2 Portal 协议（弹窗提升）

Agent 内需要全屏展示的组件（对话框、抽屉），通过 postMessage 让父页面渲染，避免 iframe 边界裁剪和 z-index 层级问题。

```typescript
interface PortalMessage {
  version: '1.0';
  type: 'PORTAL_REQUEST' | 'PORTAL_RESPONSE' | 'PORTAL_DISMISS';
  id: string;
  portal: 'dialog' | 'drawer' | 'toast' | 'fullscreen';
  payload: {
    title?: string;
    size?: 'sm' | 'md' | 'lg' | 'fullscreen';
    content?: unknown;
  };
}
```

### 2.3 降级原则

Agent 平台所有组件自带 fallback 渲染，独立运行时不依赖父页面。父页面只是"增强"。

---

## 3. 账号对接

### 3.1 混合模式

Agent 平台自有用户体系，同时支持 OAuth 关联外部平台。

```sql
CREATE TABLE users (
    id              UUID PRIMARY KEY,
    email           VARCHAR(255) UNIQUE,
    auth_type       ENUM('native', 'oauth'),
    oauth_provider  VARCHAR(64) DEFAULT NULL,
    external_user_id VARCHAR(64) DEFAULT NULL,
    created_at      TIMESTAMP
);
```

### 3.2 iframe Token 传递

iframe 内不能做 302 跳转，通过 postMessage 传递 token：

```
父页面获取 Agent token → postMessage → iframe 存储 → API 调用
token 过期 → postMessage 通知父页面 → 父页面刷新 → postMessage 返回新 token
```

---

## 4. 租户与项目

### 4.1 结构

```
Tenant（租户，组织级）
  └── Project（项目，工作空间级）
        └── Agent（智能体实例）
              └── Session（会话）
```

### 4.2 数据隔离

- 共享数据库 + tenant_id / project_id 字段隔离（推荐起步方案）
- 企业级客户需要更强隔离时升级到 Schema 隔离或数据库隔离

### 4.3 与云平台映射

Agent 平台有自己的租户模型，通过映射表关联外部系统：

```sql
CREATE TABLE tenant_mapping (
    cloud_tenant_id   VARCHAR(64),
    agent_tenant_id   UUID,
    mapped_at         TIMESTAMP
);
```

---

## 5. 技术栈

| 层 | 技术 |
|----|------|
| 网关 | Go |
| Agent 逻辑 / 服务 | Python |
| 热数据存储 | Redis |
| 持久化存储 | PostgreSQL |
| 消息队列 | Kafka（复用云平台） |
| 容器编排 | K8s（Namespace 隔离） |

---

## 6. AgentLoop 服务化架构

### 6.1 演进策略：模块化单体 → 渐进式拆分

Phase 1（现在）：所有模块在一个 Python 进程内，通过 Protocol 接口通信。
Phase 2（需要时）：将接口从本地调用替换为 HTTP 调用，模块变为独立服务。

### 6.2 核心模块与接口定义

```python
class ToolExecutor(Protocol):
    """工具执行接口"""
    async def execute(self, tool_name: str, params: dict) -> ToolResult: ...

class SandboxManager(Protocol):
    """沙盒管理接口"""
    async def create(self, session_id: str) -> SandboxInfo: ...
    async def execute(self, sandbox_id: str, code: str) -> ExecutionResult: ...
    async def destroy(self, sandbox_id: str) -> None: ...

class ProviderRegistry(Protocol):
    """模型 Provider 管理接口"""
    def register(self, provider_id: str, config: ProviderConfig) -> None: ...
    def get(self, provider_id: str) -> LLMProvider: ...
    def list(self) -> list[ProviderInfo]: ...

class PermissionChecker(Protocol):
    """权限检查接口"""
    async def check(self, user_id: str, action: str, resource: str) -> bool: ...

class StateStore(Protocol):
    """状态存储接口"""
    async def load(self, session_id: str) -> SessionState: ...
    async def save(self, session_id: str, state: SessionState, persist: bool = False) -> None: ...
```

### 6.3 工具执行分发

工具自己声明执行模式，ToolDispatcher 按模式分发，Core 不硬编码：

```
ExecutionMode.INLINE   → Python 主进程内（轻量工具）
ExecutionMode.WORKER   → Worker 进程（有副作用的 I/O）
ExecutionMode.SANDBOX  → 独立沙盒服务（不可信代码执行）
```

```python
class Tool(Protocol):
    name: str
    execution_mode: ExecutionMode
    async def execute(self, params: dict) -> ToolResult: ...
```

---

## 7. 状态管理

### 7.1 两层存储

```
AgentLoop ──高频读写──► Redis（热数据，TTL 1h）
    ↕ 关键节点同步
PostgreSQL（持久化 + 外部查询）
```

### 7.2 落盘策略：事件驱动

不是定时落盘，而是在关键节点标记 `persist=True`：

```
收到用户输入     → persist=True（创建/加载 session）
step 执行中间    → persist=False（只写 Redis）
step 执行完成    → persist=True（落盘到 PG）
session 关闭    → persist=True + 归档
```

### 7.3 StateService 完整职责

```python
class StateService:
    # 基础读写
    async def load(session_id) -> SessionState
    async def save(session_id, state, persist=False)

    # 生命周期
    async def create(session_id, init_config) -> SessionState
    async def checkpoint(session_id)           # Redis → PG 快照
    async def destroy(session_id)              # 清理 Redis + 归档 PG

    # 查询（走 PG）
    async def list_by_user(user_id) -> list[SessionSummary]
    async def get_active_sessions() -> list[SessionSummary]

    # 监控
    async def get_heartbeat(session_id) -> bool
```

### 7.4 崩溃恢复

```
重启 → 查 Redis → 有则恢复 ✓
                 → 无则查 PG → 有则回填 Redis ✓
                            → 无则 session 丢失，告知用户
最坏情况：丢失当前未完成的 step，下次重新执行（LLM 调用幂等）
```

---

## 8. AgentLoop Core 改造要点

### 8.1 状态外置

将 Core 内散落的状态变量（messages、context 等）抽成 `SessionState` 类，读写通过 `StateStore` 接口。AgentLoop 实例本身无状态，可水平扩展。

### 8.2 接口抽象

所有模块交互通过 Protocol 接口，不直接依赖具体实现。Phase 1 本地调用，Phase 2 按需切换为 HTTP 调用。

### 8.3 Core 改造前后对比

```python
# 改造前：状态在实例上
class AgentLoop:
    def __init__(self):
        self.messages = []
        self.context = {}

# 改造后：状态外置，依赖注入
@dataclass
class SessionState:
    messages: list
    context: dict
    current_step: int

class AgentLoop:
    def __init__(self, state_store: StateStore):
        self.state_store = state_store
```

---

## 9. K8s 部署

K8s 只解决部署运维，不改变系统架构。Namespace 做环境隔离：

```
K8s 集群
├── namespace: cloud       → 云平台
├── namespace: aaas        → Agent 平台
│   ├── agent-api (3 replicas)
│   ├── agent-worker (2 replicas)
│   └── agent-scheduler (1 replica)
└── namespace: infra       → 共享基础设施（PG、Redis、Kafka）
```

---

## 10. 并行推进计划

```
Owner（你）
  │
  ├── [阻塞项] 定义接口契约（1-2天）
  │     输出：Protocol 定义 + 数据结构 + OpenAPI spec
  │
  ├── [并行] Go Gateway
  │     依赖：API 路由和请求/响应格式
  │
  ├── [并行] Web Frontend
  │     依赖：OpenAPI spec + mock 数据
  │
  └── [并行] 基础设施
        Docker / DB Schema / CI/CD
```

**当前卡点：接口契约未定义。这是所有并行工作的前提。**
