# MCP Server 托管服务设计文档

> 基于 Kubernetes Pod 的 MCP Server 托管平台详细设计

## 1. 概述

本设计实现一个基于 K8s 的 MCP Server 托管服务。用户通过控制面 API 创建 MCP Server，平台自动完成 K8s 资源的部署和路由配置，用户只需关注 MCP Server 本身的业务逻辑。

### 1.1 核心原则

- **应用与网络解耦**：Deployment 管应用，Service 管入口，Ingress 管外部路由
- **用户隔离**：每个用户只能访问自己创建的 MCP Server
- **API 驱动**：所有操作通过控制面 API 完成，用户无需接触 K8s

## 2. 整体架构

```
MCP Client
    │
    │ HTTP (Streamable HTTP)
    ▼
┌─────────────────────────────────────────────────────┐
│  Ingress (Wildcard + Lua/OpenResty 动态路由)        │
│  *.mcp.example.com → Lua 查询 Redis 路由表         │
│  proxy-buffering: off / timeout: 3600s              │
└─────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────┐
│  Auth Service (External Auth)                       │
│  校验 API Key → 提取 user_id → 注入 X-Validated-User│
└─────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────────────────┐
│              MCP Server Pool                        │
│                                                     │
│  Server A (Deployment) ─── Service A                │
│  Server B (Deployment) ─── Service B                │
│  Server C (Deployment) ─── Service C                │
│                                                     │
│  镜像来源：Harbor                                   │
└─────────────────────────────────────────────────────┘

路由存储：Redis（user_id:server_name → service_name 映射）
```

### 2.1 访问模式

| 模式 | 适用场景 | 链路 | 是否过 Ingress |
|------|---------|------|---------------|
| 公网访问 | 外部客户端、第三方集成 | Client → LB → Ingress → Auth → MCP Server | 是 |
| 内网访问 | 同集群 Agent Pod 调用 MCP Server | Agent Pod → K8s Service → MCP Server | 否 |

**内网访问优势**：跳过 Ingress 层，零网络开销，无公网暴露风险。

**内网访问地址**：
```
http://mcp-svc-{user_id}-{server_name}.mcp-hosting.svc.cluster.local:80
```

### 2.2 组件职责

| 组件 | 职责 | 技术选型 |
|------|------|---------|
| Ingress | 泛域名入口，Lua 动态路由，无需修改 Ingress YAML | nginx-ingress + Lua/OpenResty |
| Auth Service | API Key 认证，用户身份提取，请求头注入 | External Auth（nginx auth-url） |
| Route Registry | 维护 user_id + server_name → Service 的路由映射 | Redis |
| Deployment | 管理 MCP Server Pod 生命周期 | K8s Deployment |
| Service | Pod 内部稳定入口和负载均衡 | K8s Service |
| Harbor | MCP Server 镜像存储 | 已有 Harbor |

## 3. K8s 资源模型

每个 MCP Server 对应一组 K8s 资源：

### 3.0 资源规格（Flavor）

用户不能随意填写 CPU/Memory，控制面提供标准化规格：

| 规格名称 | CPU Request / Limit | Memory Request / Limit | 适用场景 |
|---------|-------------------|----------------------|---------|
| **nano** | 50m / 200m | 128Mi / 256Mi | API 转发型工具（天气、搜索） |
| **standard** | 200m / 500m | 512Mi / 1Gi | 本地 RAG、小型 DuckDB 处理 |
| **heavy** | 500m / 2000m | 2Gi / 4Gi | Python 解释器、复杂自动化脚本 |

创建 Server 时指定 `flavor` 字段，控制面映射为 K8s resources：

```json
POST /api/mcp/servers
{ "name": "weather", "flavor": "nano" }
```

> **注意**：requests 留足空间，防止 MCP Server 启动时资源峰值导致 Node 节点争抢。

### 3.1 Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mcp-{user_id}-{server_name}
  namespace: mcp-hosting
  labels:
    user: {user_id}
    server: {server_name}
spec:
  replicas: 1
  selector:
    matchLabels:
      user: {user_id}
      server: {server_name}
  template:
    metadata:
      labels:
        user: {user_id}
        server: {server_name}
    spec:
      containers:
      - name: mcp-server
        image: harbor.example.com/mcp/{image}:{tag}
        ports:
        - containerPort: 8080
        resources:                             # 由 flavor 决定，此处以 nano 为例
          requests:
            cpu: "50m"
            memory: "128Mi"
          limits:
            cpu: "200m"
            memory: "256Mi"
        startupProbe:
          httpGet:
            path: /health
            port: 8080
          failureThreshold: 30        # 最多等待 30 × 10s = 300s 冷启动
          periodSeconds: 10
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 30
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 10
```

### 3.2 Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: mcp-svc-{user_id}-{server_name}
  namespace: mcp-hosting
spec:
  selector:
    user: {user_id}
    server: {server_name}
  ports:
  - port: 80
    targetPort: 8080
```

### 3.3 Ingress（泛域名 + 动态路由）

采用泛域名 Ingress + Lua 脚本动态路由，避免频繁修改 Ingress YAML 触发 Nginx Reload：

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: mcp-ingress
  namespace: mcp-hosting
  annotations:
    # 长连接超时（MCP 工具调用可能持续数分钟）
    nginx.ingress.kubernetes.io/proxy-read-timeout: "3600"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "3600"
    # 关键：禁用代理缓存，支持流式响应（Streamable HTTP）
    nginx.ingress.kubernetes.io/proxy-buffering: "off"
    # 关键：保持长连接
    nginx.ingress.kubernetes.io/connection-proxy-header: "keep-alive"
    # HTTP/2：MCP 流式响应在 H2 下性能和稳定性远超 H1.1
    nginx.ingress.kubernetes.io/use-http2: "true"
    # External Auth：请求先转发到 Auth Service 校验
    nginx.ingress.kubernetes.io/auth-url: "http://auth-svc.mcp-hosting/verify"
    nginx.ingress.kubernetes.io/auth-response-headers: "X-Validated-User"
spec:
  rules:
  - host: "*.mcp.example.com"
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: mcp-dynamic-router   # Lua 路由 Service
            port:
              number: 80
```

### 3.4 动态路由（Lua + Redis）

控制面创建/删除 Server 时，同步更新 Redis 路由表：

```
# Redis 路由映射
HSET mcp:routes "{user_id}:{server_name}" "mcp-svc-{user_id}-{server_name}"
```

Lua 脯本从请求路径提取 user_id 和 server_name，查询 Redis 获取目标 Service，直接转发：

```lua
-- Lua 路由逻辑（含本地缓存防惊群）
local redis = require "resty.redis"
local route_cache = ngx.shared.route_cache          -- lua_shared_dict，TTL 30s

local user_id, server_name = extract_from_path(ngx.var.uri)
local cache_key = user_id .. ":" .. server_name

-- L1: 本地内存缓存
local service_name = route_cache:get(cache_key)

if not service_name then
    -- L2: Redis 查询
    local red = redis:new()
    service_name = red:hget("mcp:routes", cache_key)

    if service_name then
        route_cache:set(cache_key, service_name, 30)  -- 缓存 30s
    end
end

if service_name then
    proxy_pass("http://" .. service_name)
else
    ngx.exit(404)
end
```

**Nginx 配置**（在 nginx.conf 中声明共享字典）：

```nginx
lua_shared_dict route_cache 10m;     # 10MB 本地缓存，约可存 10 万条路由
```

**防惊群效果**：Redis 抖动或大规模更新路由时，本地缓存在 30s 内继续提供 Stale 数据，不会全站 404。

**优势**：新增/删除 Server 只需更新 Redis，不触发 Nginx Reload，零流量抖动。

### 3.5 Redis 持久化与可靠性

Redis 存储路由表和 API Key 映射，是数据面关键路径。

#### 3.5.1 数据持久化（RDB + AOF 混合）【MVP】

```conf
# redis.conf
appendonly yes
appendfsync everysec                     # AOF 每秒刷盘，最多丢 1s
aof-use-rdb-preamble yes                 # 混合持久化：RDB 快照 + AOF 增量
save 900 1                               # RDB: 15分钟内至少1个写操作则触发快照
save 300 10                              # RDB: 5分钟内至少10个写操作
save 60 10000                            # RDB: 1分钟内至少10000个写操作
```

| 机制 | 作用 | 恢复速度 |
|------|------|---------|
| RDB | 定时内存快照 | 快（直接加载二进制） |
| AOF | 记录每次写操作 | 数据完整性高（最多丢 1s） |
| 混合模式 | 先加载 RDB 再重放 AOF | 兼顾速度和完整性 |

#### 3.5.2 K8s 部署：StatefulSet + PV【MVP】

Redis 不能用 Deployment，Pod 重启会丢失容器可写层数据：

```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: redis
  namespace: mcp-hosting
spec:
  serviceName: redis-headless
  replicas: 1
  template:
    spec:
      containers:
      - name: redis
        image: redis:7
        ports:
        - containerPort: 6379
        volumeMounts:
        - name: redis-data
          mountPath: /data
  volumeClaimTemplates:
  - metadata:
      name: redis-data
    spec:
      accessModes: [ReadWriteOnce]
      storageClassName: essd              # 高性能云盘（ESSD / EBS）
      resources:
        requests:
          storage: 10Gi
```

Pod 漂移到其他节点时，K8s 自动重新挂载 PV，Redis 读取磁盘上的 RDB/AOF 文件原地恢复。

#### 3.5.3 穿透回源【MVP】

数据库是路由数据的真理源（Source of Truth），Redis 是加速索引镜像。Auth Service 在 Redis 未命中时，自动查数据库并写回缓存：

```
请求 → 查 Redis → 未命中 → 查数据库 → 写回 Redis → 返回结果
                        → 命中 → 直接返回
```

MVP 阶段保证：Redis 宕机后数据不丢失（RDB+AOF+PV），恢复后可从数据库重建。

#### 3.5.4 高可用进阶【Phase 2】

| 手段 | 解决的问题 |
|------|-----------|
| 控制面预热（DB → Redis PIPELINE） | Redis 彻底清空后秒级重建路由表 |
| 多级缓存（L1 本地内存 + L2 Redis + L3 DB） | Redis 恢复瞬间防止流量冲击 |
| Redis Sentinel | 主节点宕机自动故障转移 |
| Redis Cluster | 百万级路由数据，分片 + 多副本冗余 |

### 3.6 MCP 协议支持

- 传输协议：**Streamable HTTP**（MCP 2025-03 标准）
- 基于 HTTP POST，支持流式响应
- 关闭 proxy-buffering，确保流式数据实时推送，不经过 Nginx 缓冲
- Keep-Alive 保持长连接，Auth Service 层处理心跳检测
- 工具暴露由 MCP Server 自身的 `list_tools` 能力决定，控制面不干预

### 3.7 MCP 镜像规范

所有 MCP Server 镜像**必须实现** `/health` 端点：

```json
GET /health
{
  "status": "ready",
  "tools_loaded": 5
}
```

返回 `tools_loaded` 数量，便于 Probe 判断 Server 是否完成初始化（如加载外部工具、索引等）。

> **注意**：MVP 阶段不要求 `/metrics` 端点，Phase 2 由 Sidecar 统一提供监控能力。

## 4. 认证鉴权

### 4.1 认证方案

采用独立的 **MCP API Key** 机制，与平台 API Key 隔离：

- 泄露只影响 MCP 服务访问，不影响平台其他功能
- 独立轮转，独立限流

### 4.2 鉴权时序

```
Client                   Ingress              Auth Service          Redis            MCP Server
  │                         │                      │                  │                  │
  │ POST /mcp/user-123/     │                      │                  │                  │
  │ weather (API Key)       │                      │                  │                  │
  │────────────────────────►│                      │                  │                  │
  │                         │ auth-url 校验         │                  │                  │
  │                         │─────────────────────►│                  │                  │
  │                         │                      │ 查询 API Key     │                  │
  │                         │                      │─────────────────►│                  │
  │                         │                      │ key.owner="u-123"│                  │
  │                         │                      │◄─────────────────│                  │
  │                         │                      │                  │                  │
  │                         │    key.owner !=      │                  │                  │
  │                         │    路径中的 user_id?  │                  │                  │
  │                         │                      │                  │                  │
  │                         │  200 + X-Validated-  │                  │                  │
  │                         │  User: user-123      │                  │                  │
  │                         │◄─────────────────────│                  │                  │
  │                         │                      │                  │                  │
  │                         │ Lua 查 Redis 路由    │                  │                  │
  │                         │─────────────────────────────────────────►│                  │
  │                         │ service=mcp-svc-u123-weather            │                  │
  │                         │◄─────────────────────────────────────────│                  │
  │                         │                      │                  │                  │
  │                         │ 转发至 MCP Server    │                  │                  │
  │                         │──────────────────────────────────────────────────────────►│
  │                         │                      │                  │                  │
  │                         │              ◄── 403 (如果 user_id 不匹配，直接拒绝)       │
```

**流程说明**：
1. Client 携带 MCP API Key（Header: `Authorization` 或 `X-MCP-Key`）发起请求
2. Ingress 通过 `auth-url` 将请求转发至 Auth Service 校验
3. Auth Service 从 Redis 查询 API Key 对应的 user_id
4. 如果 `key.owner != 路径中的 user_id`，直接返回 403 Forbidden
5. 校验通过，Auth Service 返回 200 并注入 `X-Validated-User: user-123`
6. Ingress Lua 脚本查询 Redis 路由表，获取目标 Service 并转发

### 4.3 隔离模型

用户天然隔离：每个 MCP Server 路径包含 user_id，认证中间件确保用户只能访问自己的 Server。

## 5. 数据模型

```
User (平台已有)
├── id
├── mcp_api_key          — MCP 专属 API Key
└── ...

QuotaGroup (平台已有)
├── id
├── name
├── resource_limits       — CPU/内存/数量限制
└── ...

MCPServer (新增)
├── id
├── user_id               — 所属用户
├── group_id              — 所属配额组
├── name                  — Server 名称（唯一标识）
├── image                 — Harbor 镜像地址
├── tag                   — 镜像版本
├── replicas              — 副本数（默认 1）
├── status                — running / stopped / error
├── endpoint              — 公网访问路径 /mcp/{user_id}/{name}
├── internal_endpoint     — 内网访问地址 mcp-svc-{user_id}-{name}.mcp-hosting.svc.cluster.local
├── created_at
└── updated_at
```

### 5.1 配额校验

创建 Server 时，校验所属 QuotaGroup 的资源配额（三个维度）：

| 资源维度 | 计算方式 | 目的 |
|---------|---------|------|
| CPU/Memory | `SUM(server.request.cpu/memory)` | 物理资源保证 |
| Max Servers | `COUNT(server_id)` | 防止恶意占坑 |
| Streamable HTTP 并发连接数 | 实时长连接计数 | 防止单用户耗尽 Ingress 连接池 |

```
QuotaGroup 已用资源 + 新申请资源 ≤ 限额
    → 通过：部署
    → 超限：拒绝，返回 429
```

## 6. 控制面 API

### 6.1 接口列表

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/mcp/servers | 创建 MCP Server |
| GET | /api/mcp/servers | 列出当前用户的 Server |
| GET | /api/mcp/servers/{id} | 查看详情（含 endpoint） |
| PUT | /api/mcp/servers/{id} | 更新配置（镜像、副本数等） |
| DELETE | /api/mcp/servers/{id} | 删除 MCP Server |

### 6.2 接口详情

#### POST /api/mcp/servers — 创建 Server

请求：
```json
{
  "name": "weather",
  "image": "harbor.example.com/mcp/weather",
  "tag": "v1.0.0",
  "flavor": "nano",
  "replicas": 1,
  "group_id": "quota-group-001"
}
```

响应：
```json
{
  "id": "srv-uuid-001",
  "name": "weather",
  "image": "harbor.example.com/mcp/weather:v1.0.0",
  "status": "deploying",
  "endpoint": "/mcp/user-123/weather",
  "internal_endpoint": "mcp-svc-user-123-weather.mcp-hosting.svc.cluster.local",
  "created_at": "2026-04-10T10:00:00Z"
}
```

#### GET /api/mcp/servers — 列出 Server

响应：
```json
{
  "servers": [
    {
      "id": "srv-uuid-001",
      "name": "weather",
      "status": "running",
      "endpoint": "/mcp/user-123/weather",
      "internal_endpoint": "mcp-svc-user-123-weather.mcp-hosting.svc.cluster.local",
      "created_at": "2026-04-10T10:00:00Z"
    }
  ]
}
```

#### GET /api/mcp/servers/{id} — 查看详情

响应：
```json
{
  "id": "srv-uuid-001",
  "user_id": "user-123",
  "group_id": "quota-group-001",
  "name": "weather",
  "image": "harbor.example.com/mcp/weather:v1.0.0",
  "replicas": 1,
  "status": "running",
  "endpoint": "/mcp/user-123/weather",
  "internal_endpoint": "mcp-svc-user-123-weather.mcp-hosting.svc.cluster.local",
  "created_at": "2026-04-10T10:00:00Z",
  "updated_at": "2026-04-10T10:05:00Z"
}
```

#### PUT /api/mcp/servers/{id} — 更新配置

请求（支持部分更新）：
```json
{
  "tag": "v1.1.0",
  "flavor": "standard",
  "replicas": 2
}
```

#### DELETE /api/mcp/servers/{id} — 删除 Server

删除时清理对应 K8s 资源：Deployment、Service，同时从 Redis 删除路由映射。

## 7. Server 生命周期

```
创建请求 → 配额校验 → 创建 K8s 资源（Deployment + Service）→ 写入 Redis 路由
                                  │
                                  ▼
                            deploying
                                  │
                          startupProbe 等待冷启动
                                  │
                          readinessProbe 通过 → running
                          livenessProbe 失败 → error（通知用户）
                                  │
                            更新请求 → rolling update → 更新 Redis 路由
                                  │
                            删除请求 → 清理 K8s 资源 + 删除 Redis 路由
```

## 8. 错误处理

| 场景 | HTTP 状态码 | 说明 |
|------|------------|------|
| API Key 无效 | 401 | 认证失败 |
| 路径 user_id 与 Key 不匹配 | 403 | 越权访问 |
| 配额超限 | 429 | QuotaGroup 资源不足 |
| Server 不存在 | 404 | 查询/删除不存在的 Server |
| 镜像拉取失败 | 500 | Harbor 不可达或镜像不存在 |

## 9. 安全考虑

- MCP API Key 通过 HTTPS 传输，服务端存储加密（bcrypt/scrypt）
- 用户间资源隔离：认证中间件强制校验 user_id 归属
- 容器资源限制：通过 K8s resources 字段限制 CPU/内存，防止资源抢占
- 命名空间隔离：所有 MCP Server 部署在 `mcp-hosting` 命名空间
- NetworkPolicy 网络隔离：MCP Server Pod 严禁访问 K8s API Server 及其他用户的 MCP Pod

### 9.1 NetworkPolicy（默认拒绝）

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: mcp-server-default-deny
  namespace: mcp-hosting
spec:
  podSelector:
    matchLabels:
      app: mcp-server                  # 匹配所有 MCP Server Pod
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: mcp-hosting            # 只允许同命名空间内访问（Ingress/Auth Service）
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: mcp-hosting
  - to:                                # 允许拉取镜像
    - ipBlock:
        cidr: 0.0.0.0/0
    ports:
    - port: 443
    protocol: TCP
  # 注意：未显式放行 K8s API Server（默认拒绝）
```

## 10. 进阶：CRD + Operator 一致性保障（Phase 2）

### 10.1 动机

当前方案中，控制面 API 需要同时管理数据库记录、K8s 资源（Deployment/Service）和 Redis 路由表三者的状态一致性。任何一步失败都会导致状态不一致：

- 数据库有记录，但 K8s 资源未创建
- K8s 资源存在，但 Redis 路由未写入
- Pod 被 K8s 自动重建，但数据库状态未同步

Operator 模式通过 **声明式 + Reconcile 循环** 天然解决这个问题。

### 10.2 CRD 定义

```yaml
apiVersion: mcp.example.com/v1alpha1
kind: MCPServer
metadata:
  name: mcp-user123-weather
  namespace: mcp-hosting
  labels:
    user: user-123
    quota-group: quota-group-001
spec:
  userId: user-123
  imageName: harbor.example.com/mcp/weather
  imageTag: v1.0.0
  replicas: 1
  resources:
    cpu: "500m"
    memory: "512Mi"
status:
  phase: running              # deploying / running / error / stopped
  endpoint: /mcp/user-123/weather
  internalEndpoint: mcp-svc-user-123-weather.mcp-hosting.svc.cluster.local
  observedGeneration: 3       # Operator 已处理到第几代
  conditions:
  - type: Ready
    status: "True"
    lastTransitionTime: "2026-04-10T10:05:00Z"
```

### 10.3 Operator Reconcile 逻辑

```
Loop（每 5s 或事件触发）:
  │
  ├─ 1. 读取 MCPServer CR 的 spec.desiredState
  ├─ 2. 查询实际状态（K8s Deployment/Service 是否存在、Redis 路由是否有值）
  ├─ 3. 对比 diff
  │     ├─ Deployment 不存在 → 创建
  │     ├─ Deployment 存在但 spec 不一致 → 更新（Rolling Update）
  │     ├─ Redis 路由缺失 → 写入
  │     └─ 一切一致 → 更新 status.phase = running
  └─ 4. 写回 status（ observedGeneration、conditions、phase）
```

**关键特性**：Reconcile 是幂等的，无论从哪个状态中断，重新执行都能收敛到期望状态。

### 10.4 架构变化

```
变更前：
  控制面 API → 直接操作 K8s API + Redis + DB（命令式，需自己保证一致性）

变更后：
  控制面 API → 创建/更新 MCPServer CR（声明式）
  Operator   → Watch CR → Reconcile → 同步 K8s 资源 + Redis 路由（自动一致性）
```

### 10.5 控制面 API 职责简化

引入 Operator 后，控制面 API 只需操作 CRD：

| 操作 | API 行为 | Operator 自动处理 |
|------|---------|------------------|
| 创建 | 创建 MCPServer CR + 写数据库 | 创建 Deployment/Service + 写 Redis 路由 |
| 更新 | 更新 MCPServer CR spec | Rolling Update + 更新 Redis |
| 删除 | 删除 MCPServer CR + 删除数据库记录 | 清理 Deployment/Service + 删除 Redis 路由 |
| 状态查询 | 读取 CR status | 持续同步 Pod 状态到 CR status |

### 10.6 一致性保障对比

| 场景 | 无 Operator | 有 Operator |
|------|------------|------------|
| 创建中途 API 崩溃 | 状态不一致，需人工修复 | Reconcile 自动补全 |
| Pod 被 K8s 意外删除 | Deployment 会重建，但 DB/Redis 不知道 | Operator 感知并同步 status |
| Redis 路由丢失 | 请求 404 | Reconcile 检测到缺失，重新写入 |
| 手动 kubectl 改了 Deployment | API 不知道 | Operator 检测到 drift，回退或同步 |

### 10.7 推荐实施路径

**Phase 1（MVP）**：控制面 API 直接操作 K8s + Redis，不加 Operator，快速上线验证。

**Phase 2（稳定后）**：引入 CRD + Operator，替换命令式操作，获得自动一致性和自愈能力。

**技术选型**：Go 编写 Operator，使用 [kubebuilder](https://book.kubebuilder.io/) 或 [operator-sdk](https://sdk.operatorframework.io/) 脚手架生成基础代码。

### 10.8 Sidecar 注入（降低用户镜像开发门槛）

Phase 2 引入标准 Sidecar，由平台统一处理 `/health`、`/metrics` 和本地 API Key 校验，用户镜像只需专注业务逻辑。

```
┌──────────── MCP Pod ────────────┐
│                                  │
│  ┌──────────┐    ┌────────────┐ │
│  │ User      │    │ Platform   │ │
│  │ Container │◄──►│ Sidecar    │ │
│  │ (业务)    │    │ (健康/指标) │ │
│  └──────────┘    └────────────┘ │
│       ↑                ↑        │
│  用户自己开发       平台自动注入  │
└──────────────────────────────────┘
```

**Sidecar 职责**：

| 能力 | 实现方 | 说明 |
|------|--------|------|
| `/health` 健康检查 | Sidecar | 探测用户容器端口是否可连，返回 tools_loaded 数量 |
| `/metrics` 指标暴露 | Sidecar | 统一暴露 Prometheus 格式指标，用户无需集成 SDK |
| 本地 API Key 校验 | Sidecar | 内网访问时在 Pod 级别二次校验，防止同集群越权 |
| 请求日志 | Sidecar | 自动记录每个 MCP 调用的 tool_name、duration、status |

**用户容器要求（简化后）**：
- 监听一个本地端口（如 8080）
- 实现 MCP Streamable HTTP 协议
- 无需集成健康检查、Prometheus SDK、日志框架

**Deployment 示例（Sidecar 注入后）**：

```yaml
spec:
  containers:
  - name: mcp-server
    image: harbor.example.com/mcp/weather:v1.0.0
    ports: [{containerPort: 8080}]
    # 用户容器无需 livenessProbe/readinessProbe，由 Sidecar 代理
  - name: mcp-sidecar                # 平台自动注入
    image: harbor.example.com/platform/mcp-sidecar:v1
    ports:
    - {containerPort: 9090}          # /health + /metrics
    env:
    - name: USER_CONTAINER_PORT
      value: "8080"
    livenessProbe:
      httpGet: {path: /health, port: 9090}
    readinessProbe:
      httpGet: {path: /health, port: 9090}
```

## 11. 指标监控（Phase 2）

### 11.1 监控架构

```
MCP Server Pod ──► Prometheus ──► Grafana（大盘）
                     │
Ingress Controller ──►
Auth Service ────────►
Redis ───────────────►
Operator ────────────►
```

### 11.2 核心监控指标

| 层级 | 指标 | 类型 | 说明 |
|------|------|------|------|
| **MCP Server** | mcp_request_total | Counter | 请求总量（按 user_id、server_name 维度） |
| | mcp_request_duration_seconds | Histogram | 请求延迟分布（P50/P95/P99） |
| | mcp_active_connections | Gauge | 当前活跃 Streamable HTTP 长连接数 |
| | mcp_tool_calls_total | Counter | 工具调用次数（按 tool_name 维度） |
| | mcp_tool_errors_total | Counter | 工具调用失败次数 |
| | mcp_tools_loaded | Gauge | 已加载工具数量（来自 /health） |
| **K8s 资源** | pod_cpu/memory_usage | Gauge | Pod 资源使用量 |
| | pod_restart_total | Counter | Pod 重启次数（异常告警） |
| | deployment_replicas | Gauge | 期望 vs 实际副本数 |
| **平台层** | mcp_servers_total | Gauge | 运行中的 Server 总数（按 user_id 分组） |
| | mcp_server_create_total | Counter | Server 创建次数 |
| | mcp_server_error_total | Counter | Server 进入 error 状态次数 |
| | quota_usage_ratio | Gauge | QuotaGroup 资源使用率 |

### 11.3 指标暴露（Phase 2 Sidecar）

Phase 2 由 Sidecar 统一暴露 `/metrics` 端点，用户无需集成 Prometheus SDK。采集目标为 Sidecar 端口（9090）：

```yaml
annotations:
  prometheus.io/scrape: "true"
  prometheus.io/port: "9090"
  prometheus.io/path: "/metrics"
```

### 11.4 告警规则

```yaml
groups:
- name: mcp-server-alerts
  rules:
  - alert: MCPServerDown
    expr: up{job="mcp-server"} == 0
    for: 2m
    labels:
      severity: critical
    annotations:
      summary: "MCP Server {{ $labels.instance }} 不可用"

  - alert: MCPHighLatency
    expr: histogram_quantile(0.99, mcp_request_duration_seconds_bucket) > 30
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "MCP Server P99 延迟超过 30s"

  - alert: MCPServerCrashLoop
    expr: rate(kube_pod_container_status_restarts_total{namespace="mcp-hosting"}[5m]) > 0.1
    for: 3m
    labels:
      severity: critical
    annotations:
      summary: "MCP Server Pod 频繁重启"

  - alert: QuotaUsageHigh
    expr: quota_usage_ratio > 0.9
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "QuotaGroup {{ $labels.group_id }} 资源使用率超过 90%"
```

### 11.5 Grafana 大盘

建议监控面板：

| 面板 | 内容 |
|------|------|
| Server 总览 | 运行中/错误/部署中数量，总请求量趋势 |
| 请求延迟 | P50/P95/P99 延迟曲线，按 Server 分组 |
| 连接数 | 活跃 SSE 连接数趋势，按 User 分组 |
| 工具调用 | Top 10 调用量工具，错误率排行 |
| 资源使用 | 各 Pod CPU/内存使用率，Quota 剩余量 |

## 12. 日志聚合（Phase 2）

### 12.1 日志架构

```
MCP Server Pod (stdout/stderr)
       │
       ▼
  Filebeat / Fluent Bit（DaemonSet，每个 Node 一个）
       │
       ▼
  Kafka（日志缓冲，削峰）
       │
       ▼
  Logstash / Vector（解析、结构化）
       │
       ├──► ClickHouse（长期存储，支持 SQL 查询）
       └──► Elasticsearch（全文检索，备选方案）
              │
              ▼
         Grafana / Kibana（可视化查询）
```

### 12.2 日志格式规范

MCP Server 输出的日志必须为 **JSON 结构化格式**，包含以下标准字段：

```json
{
  "timestamp": "2026-04-10T10:05:00.000Z",
  "level": "INFO",
  "message": "Tool execution completed",
  "user_id": "user-123",
  "server_name": "weather",
  "request_id": "req-uuid-001",
  "tool_name": "get_weather",
  "tool_duration_ms": 150,
  "client_ip": "10.244.1.5"
}
```

**必填字段**：`timestamp`、`level`、`message`、`user_id`、`server_name`

**选填字段**：`request_id`、`tool_name`、`tool_duration_ms`、`error_code`、`error_message`

### 12.3 日志追踪

所有经过 Ingress 的请求，Auth Service 注入 trace 上下文：

```
X-Request-ID: req-uuid-001
X-Validated-User: user-123
```

MCP Server 读取并透传这些 Header，整条链路日志可通过 `request_id` 或 `trace_id` 串联：

```
Ingress 日志: request_id=req-001 user=user-123 path=/mcp/user-123/weather
Auth 日志:    request_id=req-001 auth=passed user=user-123
MCP 日志:     request_id=req-001 tool=get_weather duration=150ms
```

### 12.4 日志保留策略

| 日志级别 | 保留时间 | 存储位置 |
|---------|---------|---------|
| ERROR | 90 天 | ClickHouse 热存储 |
| WARN | 30 天 | ClickHouse 热存储 |
| INFO | 7 天 | ClickHouse 温存储 |
| DEBUG | 1 天 | ClickHouse 冷存储 |

### 12.5 日志查询接口

控制面 API 提供日志查询能力（复用平台日志服务）：

```python
# 按用户查询
GET /api/mcp/servers/{id}/logs?level=ERROR&limit=50

# 按请求追踪
GET /api/mcp/servers/{id}/logs?request_id=req-uuid-001

# 按时间范围
GET /api/mcp/servers/{id}/logs?start=2026-04-10T00:00:00Z&end=2026-04-10T23:59:59Z
```

### 12.6 实施路径

**Phase 1（MVP）**：stdout 日志 + K8s 原生 `kubectl logs`，先跑通基本流程。

**Phase 2**：引入 Fluent Bit + ClickHouse，实现结构化存储和查询。

**Phase 3**：接入 Grafana 日志面板，配置告警规则。

---

## 附录：实施路线图

### Phase 1（MVP）— 核心可用

目标：跑通"创建 → 部署 → 访问 → 删除"完整链路。

| 能力 | 对应章节 |
|------|---------|
| K8s 部署模型（Deployment + Service + Ingress） | 3.1 ~ 3.3 |
| 泛域名 + Lua 动态路由 + 本地缓存防惊群 | 3.3 ~ 3.4 |
| Redis RDB+AOF 混合持久化 + StatefulSet+PV + 穿透回源 | 3.5.1 ~ 3.5.3 |
| MCP Streamable HTTP 协议支持（proxy-buffering off、HTTP/2） | 3.6 |
| MCP 镜像规范（/health） | 3.7 |
| Flavor 资源规格化（nano / standard / heavy） | 3.0 |
| MCP API Key 认证 + 鉴权时序 | 4.1 ~ 4.2 |
| 数据模型（User / QuotaGroup / MCPServer） | 5 |
| 配额校验（CPU/Memory/Max Servers/SSE 并发连接） | 5.1 |
| 控制面 API（CRUD 5 个接口） | 6 |
| Server 生命周期管理 | 7 |
| 错误处理 | 8 |
| 安全：NetworkPolicy 网络隔离 | 9.1 |
| 公网 + 内网双访问模式 | 2.1 |

**不在 MVP 范围内**：Operator、监控大盘、日志聚合、Sidecar、Sentinel/Cluster。

---

### Phase 2 — 稳定与可观测

目标：生产级可靠性 + 全链路可观测。

| 能力 | 对应章节 |
|------|---------|
| Redis 高可用（预热、多级缓存、Sentinel） | 3.5.4 |
| CRD + Operator（声明式管理 + 自动一致性） | 10.1 ~ 10.7 |
| Sidecar 注入（/health、/metrics、本地鉴权由平台统一处理） | 10.8 |
| 指标监控（Prometheus + Grafana 大盘 + 告警） | 11 |
| 日志聚合（Fluent Bit + ClickHouse + 结构化日志） | 12 |

---

### Phase 3 — 规模化与进阶

目标：支持大规模部署 + 高级功能。

| 能力 | 说明 |
|------|------|
| Redis Cluster | 百万级路由数据，分片 + 多副本 |
| 多 Region 部署 | 跨可用区容灾 |
| MCP Server 版本管理 | 多版本共存、灰度发布 |
| 自定义域名绑定 | 用户绑定自有域名到 MCP Server |
| 计费系统 | 按量/按月计费，对接平台计费 |

---

## 附录：竞品对比分析

### 市场分类

当前 MCP 生态中提供托管运行能力的平台按定位分为四类：

| 类别 | 代表产品 | 核心定位 | 用户自定义 Server |
|------|---------|---------|-----------------|
| **MCP 托管 PaaS** | Smithery | 发现 + 托管 + 分发一体化 | 支持（Docker 上传） |
| **综合 MCP 平台** | 火山引擎 AgentKit | 托管 + API→MCP 转换 + LLM 集成 | 支持（stdio 上传自动转 Remote） |
| **云厂商 LLM 平台** | 阿里云（百炼） | LLM 集成 + 官方 MCP 云部署 | 仅官方预置 Server |
| **Agent 部署平台** | LangSmith Deployment | Agent 全生命周期托管 | 框架绑定（LangGraph） |
| **纯发现/注册** | Glama.ai, mcp.so | MCP Server 索引和排名 | 不托管 |

### 竞品详情

#### 1. Smithery（smithery.ai）— 最成熟的 MCP 托管平台

**方案**：发现 + 托管 + 分发一体化，用户通过 CLI 发布 MCP Server，Smithery 在云端运行并提供独立 URL。

**部署方式（四种 release type）**：

| 类型 | 说明 | 适用场景 |
|------|------|---------|
| `hosted` | JS/Python 模块上传，Smithery 容器化运行 | 轻量 Server |
| `repo` | 从 GitHub 仓库自动构建 | 开源项目 |
| `external` | 用户自托管，Smithery 做发现/代理 | 已有基础设施 |
| `docker` | 上传自定义 Docker 容器（高级模式） | 复杂依赖/非 JS/Python |

**技术细节**：
- 运行时：Cloudflare Workers 边缘计算
- 发布后获得独立 URL：`https://{slug}.run.tools`
- 传输协议：Streamable HTTP（通过 Smithery Connect 网关）
- 内置能力：OAuth 凭证管理、自动扩缩容、负载均衡、运行时日志查看
- 监控：`cpuMs` / `wallMs` 指标

**定价**：Free（个人）/ $30/mo Pro / 企业级 Custom

**与本方案对比**：

| 维度 | Smithery | 本方案（K8s Pod） |
|------|----------|------------------|
| 运行时 | Cloudflare Workers（边缘） | K8s Pod（自有集群） |
| 资源控制 | 不透明，受 Workers 限制 | Flavor 三档可配置（nano/standard/heavy） |
| GPU/大内存 | 不支持 | 支持（heavy 规格或自定义） |
| 重度计算 | 不适合 | 适合 |
| 发现/分发 | 内置（一体化核心优势） | 不含（需外部集成） |
| 数据主权 | 数据经过 Smithery 基础设施 | 完全在自有集群内 |
| OAuth | 内置 | 需自行实现 |

#### 2. 阿里云（百炼平台）

**方案**：百炼 MCP 市场 + 官方 MCP Server 云部署，支持 stdio/SSE/Streamable HTTP 三种传输模式。SSE 和 Streamable HTTP 模式意味着平台在云端运行 MCP Server 实例。

| 维度 | 说明 |
|------|------|
| 云部署流程 | 市场选择 Server → 开通 → 授权 RAM 角色 → 选择地域 → 生成 `server_url` |
| 传输协议 | stdio（本地，Agent 子进程启动，非托管）、SSE（远程托管）、Streamable HTTP（远程托管） |
| 官方 MCP Server | 10+ 个（CloudOps、ACK、可观测、云效 DevOps、RDS、DataWorks 等） |
| 自定义 Server | Docker/Helm 部署到**用户自己的 ACK 集群**，非百炼托管 |
| 认证机制 | AccessKey / STS Token / 默认凭据链 / Header 注入 |
| 集成方式 | 智能体应用（技能）、工作流应用（MCP 节点） |
| 定价 | 模型 Token 计费，MCP 托管费用未公开 |

**与本方案对比**：百炼的云部署能力完善（三种传输模式、RAM 授权、地域选择），但仅覆盖阿里云官方 MCP Server。用户自定义 Server 需部署到自己的 ACK 集群——这正是本方案要解决的问题：让没有 K8s 集群的用户也能托管自定义 MCP Server。

#### 3. 火山引擎 AgentKit — 综合型 MCP 服务管理平台

**方案**：提供三种 MCP 服务创建方式，覆盖托管、导入和协议转换。

| 创建方式 | 说明 | 等价能力 |
|---------|------|---------|
| **部署自研/公开 MCP 服务** | 上传 MCP Server，支持 Local MCP 自动转换为 Remote MCP | **托管运行**（stdio 进程 → 平台容器化 → 暴露 HTTP endpoint） |
| **导入存量 MCP 服务** | 填入已有 Remote MCP 的 URL | 注册/发现 |
| **存量 API 一键转 MCP** | 给定现有 HTTP API（如 REST/OpenAPI spec），自动包装为 MCP Server | **协议转换**（HTTP API → MCP 协议适配层） |

**核心能力**：
- **Local → Remote 自动转换**：将 stdio 模式的 MCP Server（本地进程）在平台托管运行，自动暴露为 Remote MCP（Streamable HTTP endpoint）。用户无需自行处理容器化、网络暴露
- **API → MCP 一键转换**：基于 API 规范文件（OpenAPI spec），自动包装为 MCP Server。用户只需提供 API 地址或 spec 文件
- **集成火山方舟**：创建的 MCP 服务可直接接入豆包大模型，通过 Responses API 调用
- **MarketPlace**：272 个预集成 MCP 服务，支持"体验中心"免安装

**架构洞察**（从官方文档导航结构提取）：
- **MCP服务 = 网关代理**：MCP服务是一个 Gateway 层，前端暴露 MCP endpoint，后端路由到用户的真实服务（「更新后端服务」菜单确认）
- **MCP服务 vs MCP工具集**：两者是独立概念。MCP服务 = 托管 endpoint（含鉴权、后端、日志）；MCP工具集 = 工具集合（可独立配置调用模式）
- **平台级鉴权**：「入站身份认证」在网关层配置，非 MCP Server 自身实现
- **完整 CRUD API**：`CreateMCPService`/`UpdateMCPService`/`UpdateMCPTools`/`DeleteMCPService` 等，支持工具级别的独立更新

**与本方案对比**：

| 维度 | AgentKit | 本方案（K8s Pod） |
|------|----------|------------------|
| 托管方式 | 平台托管（Local→Remote 自动转换） | 自有 K8s 集群 Pod 托管 |
| 部署入口 | 上传 stdio Server / 导入 URL / API 转换 | 上传 Docker 镜像 |
| API→MCP 转换 | ✅ 一键转换 | ❌ 不支持 |
| Local→Remote | ✅ 自动转换 | ❌ 用户需自行容器化 |
| 资源控制 | 不透明（平台管理） | Flavor 三档可配置（nano/standard/heavy） |
| 数据主权 | 数据经过火山引擎基础设施 | 完全在自有集群内 |
| LLM 集成 | ✅ 内置豆包大模型 | ❌ 通过 endpoint 对接外部 |
| 适用场景 | 快速接入 MCP 生态、无 K8s 集团、需要 API→MCP | 数据敏感、需要资源可控、有自有 K8s 集群 |

**差异化**：AgentKit 在**易用性**上优势明显（无需容器化、支持 API 直转 MCP、内置 LLM 集成），适合快速试错和中小规模使用。本方案在**可控性**上优势明显（Flavor 规格、数据主权、NetworkPolicy 隔离），适合企业级生产环境和数据敏感场景。

#### 4. LangSmith Deployment（langchain.com）

**方案**：Agent 全生命周期托管平台，支持 MCP 和 A2A 协议。

| 维度 | 说明 |
|------|------|
| 定位 | Agent Server 部署，非裸 MCP Server 托管 |
| 框架绑定 | LangGraph Agent |
| 内置能力 | 内存管理、对话线程、持久化检查点、人类-in-the-loop |
| 定价 | 企业级，联系销售 |

**与本方案对比**：LangSmith 在更高抽象层（Agent）提供托管，适合 LangGraph 生态用户。本方案在更低抽象层（MCP Server 容器）提供托管，不绑定特定 Agent 框架。

#### 5. 纯发现平台（Glama.ai / mcp.so）

不托管运行，仅提供索引、排名和协议转换。

| 平台 | 说明 |
|------|------|
| **Glama.ai** | MCP 目录 + ChatGPT 式 UI + API 网关，扫描/排名 15000+ Server |
| **mcp.so** | MCP 市场，收录 19794 个 Server，纯目录 |

### 竞品能力矩阵

```
                        发现/分发      用户自定义 Server 托管    API→MCP 转换    LLM 集成
                        ────────      ────────────────────    ────────────    ────────
Smithery               ✅ 一体化       ✅ Docker/CLI/GitHub     ❌             ❌
火山引擎 AgentKit       ✅ 272 个       ✅ stdio→Remote 自动     ✅ 一键转换     ✅ 豆包
阿里云百炼              ✅ 10+ 官方     ⚠️ 仅官方预置           ❌             ✅ 智能体/工作流
LangSmith              ❌             ✅ (Agent 级)            ❌             ✅ (内置)
Glama.ai / mcp.so      ✅ 纯目录       ❌                      ❌             ❌
本方案 (K8s Pod)       ❌             ✅ 任意镜像+Flavor        ❌             ❌ (endpoint 对接)
```

### 本方案的差异化定位

市场上已有成熟的 MCP 托管方案（Smithery、AgentKit），本方案的核心差异在于**可控性**和**数据主权**：

| 空白 | 说明 |
|------|------|
| **资源可控** | Smithery 基于 Cloudflare Workers，AgentKit 资源不透明；本方案 Flavor 三档可配置 |
| **数据主权** | Smithery/AgentKit 数据经过第三方基础设施；本方案完全在自有集群内 |
| **网络隔离** | 本方案 NetworkPolicy 默认拒绝，企业安全合规 |
| **重度计算** | Smithery/AgentKit 不支持 GPU/大内存；本方案 heavy 规格支持 |

AgentKit 的**易用性优势**（无需容器化、API→MCP 一键转换）适合快速接入场景。本方案适合**已有 K8s 集群、数据敏感、需要生产级可控性**的企业场景。两者互补而非替代——本方案托管的 endpoint 同样可以作为 `server_url` 接入 AgentKit 或百炼的 LLM 平台。
