# API 版本控制指南

## 概述

Ginkgo API Server 现已采用统一的 API 路径命名规范和版本控制。所有 API 端点均使用 `/api/v1` 前缀，并采用 RESTful 风格的复数资源名称。

## 版本配置

API 版本信息定义在 `core/version.py` 文件中：

```python
from core.version import API_VERSION, API_PREFIX, get_api_path

# 当前版本
API_VERSION = "v1"
API_PREFIX = "/api/v1"

# 生成标准化API路径
get_api_path('portfolio', 'list')      # /api/v1/portfolios
get_api_path('backtest', 'detail', '123')  # /api/v1/backtests/123
```

## 路径对照表

| 模块 | 旧路径 | 新路径 | 说明 |
|------|--------|--------|------|
| **Portfolio** | `/portfolio` | `/api/v1/portfolios` | 投资组合管理 |
| **Backtest** | `/backtest` | `/api/v1/backtests` | 回测任务管理 |
| **NodeGraph** | `/api/node-graphs` | `/api/v1/node-graphs` | 节点图配置 |
| **Dashboard** | `/api/dashboard` | `/api/v1/dashboards` | 仪表盘统计 |
| **Components** | `/api/components` | `/api/v1/components` | 组件管理 |
| **Data** | `/api/data` | `/api/v1/data` | 数据管理 |
| **Arena** | `/api/arena` | `/api/v1/arena` | 竞技场对比 |
| **Settings** | `/api/settings` | `/api/v1/settings` | 系统设置 |
| **Auth** | `/api/auth` | `/api/v1/auth` | 认证授权 |

## 特殊端点

以下端点不使用版本控制：

- `/health` - 健康检查
- `/api/health` - API 健康检查（用于前端代理）
- `/docs` - Swagger UI 文档
- `/redoc` - ReDoc 文档
- `/openapi.json` - OpenAPI 规范
- `/ws/*` - WebSocket 连接

## SSE 端点

服务器发送事件（SSE）端点遵循版本控制：

```typescript
// 回测进度推送
EventSource('/api/v1/backtests/{uuid}/events')
```

## 前端迁移指南

### 已更新的 API 模块

所有前端 API 模块已更新为使用新的路径前缀：

- `api/modules/auth.ts`
- `api/modules/backtest.ts`
- `api/modules/portfolio.ts`
- `api/modules/nodeGraph.ts`
- `api/modules/components.ts`
- `api/modules/settings.ts`

### 使用示例

```typescript
import { portfolioApi } from '@/api/modules/portfolio'

// 获取投资组合列表
const portfolios = await portfolioApi.list({ mode: 'BACKTEST' })

// 创建投资组合
const portfolio = await portfolioApi.create({
  name: 'My Strategy',
  initial_cash: 100000,
  mode: 'BACKTEST',
  // ...
})
```

## 后端开发指南

### 创建新的 API 路由

1. 在 `api/` 目录下创建路由文件
2. 使用标准化的路由装饰器

```python
from fastapi import APIRouter
from core.version import API_PREFIX

router = APIRouter()

# 在 main.py 中注册时使用统一前缀
# app.include_router(router, prefix=f"{API_PREFIX}/resources", tags=["resources"])
```

### 路由命名规范

- **列表**: `GET /api/v1/resources`
- **详情**: `GET /api/v1/resources/{uuid}`
- **创建**: `POST /api/v1/resources`
- **更新**: `PUT /api/v1/resources/{uuid}`
- **删除**: `DELETE /api/v1/resources/{uuid}`
- **子资源**: `GET /api/v1/resources/{uuid}/subresource`

### 版本升级流程

当需要发布 v2 版本时：

1. 在 `core/version.py` 中更新版本常量
2. 创建新的路由文件或复制现有路由
3. 在 `main.py` 中注册新版本路由

```python
# main.py
app.include_router(v1_router, prefix="/api/v1", tags=["v1"])
app.include_router(v2_router, prefix="/api/v2", tags=["v2"])
```

## 测试

### 测试 API 路径

使用 curl 测试新路径：

```bash
# 健康检查
curl http://localhost:8000/health

# 获取投资组合列表
curl http://localhost:8000/api/v1/portfolios

# 获取回测任务详情
curl http://localhost:8000/api/v1/backtests/{uuid}
```

### 测试 SSE 连接

```bash
# 监听回测进度
curl -N http://localhost:8000/api/v1/backtests/{uuid}/events
```

## 兼容性

### 向后兼容策略

- v1 版本将保持稳定，不进行破坏性更改
- 新功能首先在 v1 中添加
- 重大变更将在 v2 中引入，v1 继续维护

### 弃用通知

当某个端点需要弃用时：

1. 在响应头中添加 `Deprecation` 警告
2. 在文档中标记为已弃用
3. 提供迁移指南和替代方案

```python
@router.get("/old-endpoint")
async def old_endpoint():
    return {
        "message": "This endpoint is deprecated",
        "alternative": "/api/v1/new-endpoint"
    }
```

## 相关文件

- `/home/kaoru/Ginkgo/apiserver/core/version.py` - 版本配置
- `/home/kaoru/Ginkgo/apiserver/main.py` - 路由注册
- `/home/kaoru/Ginkgo/apiserver/api/` - API 路由实现
- `/home/kaoru/Ginkgo/web-ui/src/api/modules/` - 前端 API 模块

## 参考资源

- [FastAPI 版本控制最佳实践](https://fastapi.tiangolo.com/advanced/sub-applications/)
- [RESTful API 设计指南](https://restfulapi.net/)
- [OpenAPI 规范](https://swagger.io/specification/)
