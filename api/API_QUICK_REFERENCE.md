# API 路径快速参考

## 版本信息
- **当前版本**: v1
- **基础前缀**: `/api/v1`
- **配置文件**: `core/version.py`

## 快速查找表

### 投资组合 (Portfolio)
```bash
# 列表
GET    /api/v1/portfolios

# 详情
GET    /api/v1/portfolios/{uuid}

# 创建
POST   /api/v1/portfolios

# 更新
PUT    /api/v1/portfolios/{uuid}

# 删除
DELETE /api/v1/portfolios/{uuid}
```

### 回测 (Backtest)
```bash
# 任务列表
GET    /api/v1/backtests

# 任务详情
GET    /api/v1/backtests/{uuid}

# 创建任务
POST   /api/v1/backtests

# 启动任务
POST   /api/v1/backtests/{uuid}/start

# 停止任务
POST   /api/v1/backtests/{uuid}/stop

# 删除任务
DELETE /api/v1/backtests/{uuid}

# 进度推送 (SSE)
GET    /api/v1/backtests/{uuid}/events

# 获取引擎列表
GET    /api/v1/backtests/engines

# 获取分析器列表
GET    /api/v1/backtests/analyzers
```

### 节点图 (NodeGraph)
```bash
# 图列表
GET    /api/v1/node-graphs

# 图详情
GET    /api/v1/node-graphs/{uuid}

# 创建图
POST   /api/v1/node-graphs

# 更新图
PUT    /api/v1/node-graphs/{uuid}

# 删除图
DELETE /api/v1/node-graphs/{uuid}

# 复制图
POST   /api/v1/node-graphs/{uuid}/duplicate

# 验证图
POST   /api/v1/node-graphs/{uuid}/validate

# 编译图
POST   /api/v1/node-graphs/{uuid}/compile

# 从回测创建图
POST   /api/v1/node-graphs/from-backtest/{backtest_uuid}

# 获取投资组合映射
GET    /api/v1/node-graphs/{portfolio_uuid}/mappings

# 添加文件到投资组合
POST   /api/v1/node-graphs/{portfolio_uuid}/files

# 从投资组合移除文件
DELETE /api/v1/node-graphs/{portfolio_uuid}/files/{file_id}
```

### 组件 (Components)
```bash
# 组件列表
GET    /api/v1/components

# 组件详情
GET    /api/v1/components/{uuid}

# 创建组件
POST   /api/v1/components

# 更新组件
PUT    /api/v1/components/{uuid}

# 删除组件
DELETE /api/v1/components/{uuid}
```

### 数据 (Data)
```bash
# 数据统计
GET    /api/v1/data/stats

# 股票信息列表
GET    /api/v1/data/stockinfo

# K线数据列表
GET    /api/v1/data/bars

# Tick数据列表
GET    /api/v1/data/ticks

# 复权因子列表
GET    /api/v1/data/adjustfactors

# 触发数据更新
POST   /api/v1/data/update

# 获取数据源状态
GET    /api/v1/data/sources
```

### 仪表盘 (Dashboard)
```bash
# 获取统计数据
GET    /api/v1/dashboards
```

### 竞技场 (Arena)
```bash
# 获取投资组合列表
GET    /api/v1/arena/portfolios

# 获取对比数据
POST   /api/v1/arena/comparison
```

### 设置 (Settings)
```bash
# 用户管理
GET    /api/v1/settings/users
POST   /api/v1/settings/users
PUT    /api/v1/settings/users/{uuid}
DELETE /api/v1/settings/users/{uuid}

# 用户组管理
GET    /api/v1/settings/user-groups
POST   /api/v1/settings/user-groups
PUT    /api/v1/settings/user-groups/{uuid}
DELETE /api/v1/settings/user-groups/{uuid}

# 通知管理
GET    /api/v1/settings/notifications/templates
POST   /api/v1/settings/notifications/templates
PUT    /api/v1/settings/notifications/templates/{uuid}
DELETE /api/v1/settings/notifications/templates/{uuid}

# API密钥管理
GET    /api/v1/settings/api-keys
POST   /api/v1/settings/api-keys
DELETE /api/v1/settings/api-keys/{key_id}
```

### 认证 (Auth)
```bash
# 用户登录
POST   /api/v1/auth/login

# 用户登出
POST   /api/v1/auth/logout

# 验证Token
GET    /api/v1/auth/verify
```

### 系统端点（无版本）
```bash
# 健康检查
GET    /health
GET    /api/health

# API文档
GET    /docs
GET    /redoc
GET    /openapi.json

# WebSocket连接
WS     /ws/portfolio
WS     /ws/system
```

## 前端使用示例

### TypeScript
```typescript
import { portfolioApi, backtestApi } from '@/api/modules'

// 获取投资组合列表
const portfolios = await portfolioApi.list({ mode: 'BACKTEST' })

// 创建回测任务
const backtest = await backtestApi.create({
  name: 'My Strategy',
  portfolio_uuids: ['portfolio-uuid'],
  engine_config: {
    start_date: '2024-01-01',
    end_date: '2024-12-31',
    // ...
  }
})

// 监听回测进度
const eventSource = backtestApi.subscribeProgress(
  backtest.uuid,
  (progress) => console.log(progress),
  (result) => console.log('Complete', result),
  (error) => console.error('Error', error)
)
```

### curl 示例
```bash
# 获取投资组合列表
curl http://localhost:8000/api/v1/portfolios

# 创建回测任务
curl -X POST http://localhost:8000/api/v1/backtests \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","portfolio_uuids":["uuid"],"engine_config":{...}}'

# 监听回测进度
curl -N http://localhost:8000/api/v1/backtests/{uuid}/events
```

## 错误代码

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 201 | 创建成功 |
| 204 | 删除成功 |
| 400 | 请求参数错误 |
| 401 | 未认证 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 422 | 验证错误 |
| 500 | 服务器错误 |

## 响应格式

### 成功响应
```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "message": "操作成功"
}
```

### 错误响应
```json
{
  "success": false,
  "data": null,
  "error": "错误信息",
  "message": "操作失败"
}
```

### 分页响应
```json
{
  "items": [ ... ],
  "total": 100,
  "page": 1,
  "page_size": 20,
  "total_pages": 5
}
```

## 常见问题

**Q: 为什么要使用 `/api/v1` 前缀？**
A: 为了实现 API 版本控制，便于未来升级和维护。

**Q: 旧路径还能用吗？**
A: 不能，所有旧路径已迁移到新路径，请更新客户端代码。

**Q: 如何监听回测进度？**
A: 使用 SSE 端点 `/api/v1/backtests/{uuid}/events`。

**Q: WebSocket 路径有变化吗？**
A: WebSocket 路径保持不变，仍使用 `/ws/*`。

---

**更新时间**: 2026-02-08
**API版本**: v1.0.0
