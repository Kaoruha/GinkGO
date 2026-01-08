# API Gateway API Contracts

**Feature**: 007-live-trading-architecture
**Date**: 2026-01-04
**Version**: 1.0.0

本文档定义API Gateway提供的所有RESTful API接口。

---

## 认证机制

所有API请求必须包含认证信息：

### JWT认证（推荐）

```http
Authorization: Bearer <JWT_TOKEN>
```

### API Key认证

```http
X-API-Key: <API_KEY>
```

---

## 引擎控制 API

### 1. 启动实盘引擎

**Endpoint**: `POST /api/engine/live/start`

**请求**:
```json
{
  "engine_id": "live_engine_001",
  "config": {
    "broker_type": "simulation",  // simulation/real_broker
    "broker_config": {...}
  }
}
```

**响应**: `200 OK`
```json
{
  "success": true,
  "engine_id": "live_engine_001",
  "status": "starting",
  "message": "Engine start command sent"
}
```

---

### 2. 停止实盘引擎

**Endpoint**: `POST /api/engine/live/stop`

**请求**:
```json
{
  "engine_id": "live_engine_001"
}
```

**响应**: `200 OK`
```json
{
  "success": true,
  "engine_id": "live_engine_001",
  "status": "stopping",
  "message": "Engine stop command sent"
}
```

---

### 3. 查询引擎状态

**Endpoint**: `GET /api/engine/live/{engine_id}/status`

**响应**: `200 OK`
```json
{
  "engine_id": "live_engine_001",
  "status": "running",  // starting/running/stopping/stopped/error
  "portfolio_count": 5,
  "uptime": 3600,
  "last_heartbeat": "2026-01-04T10:00:00Z"
}
```

---

## Portfolio管理 API

### 4. 创建Portfolio

**Endpoint**: `POST /api/portfolio`

**请求**:
```json
{
  "name": "My Trading Portfolio",
  "user_id": "user_uuid",
  "initial_cash": 100000.00,
  "config": {
    "strategy": {
      "strategy_id": "strategy_uuid",
      "name": "TrendFollowStrategy",
      "params": {
        "short_period": 5,
        "long_period": 20
      }
    },
    "risk_managements": [
      {
        "risk_id": "risk_uuid",
        "name": "PositionRatioRisk",
        "params": {
          "max_position_ratio": 0.2
        }
      }
    ],
    "sizer": {
      "sizer_id": "sizer_uuid",
      "name": "FixedAmountSizer",
      "params": {
        "amount": 10000
      }
    }
  }
}
```

**响应**: `201 Created`
```json
{
  "success": true,
  "portfolio_id": "portfolio_uuid",
  "status": "created",
  "message": "Portfolio created successfully"
}
```

---

### 5. 更新Portfolio配置

**Endpoint**: `PUT /api/portfolio/{portfolio_id}`

**请求**:
```json
{
  "name": "My Trading Portfolio v2",
  "config": {
    "strategy": {
      "strategy_id": "strategy_uuid",
      "name": "TrendFollowStrategy",
      "params": {
        "short_period": 10,  // 更新参数
        "long_period": 30
      }
    }
  }
}
```

**响应**: `200 OK`
```json
{
  "success": true,
  "portfolio_id": "portfolio_uuid",
  "status": "reloading",
  "updated_at": "2026-01-04T10:00:00Z",
  "message": "Portfolio config updated, reload initiated"
}
```

**注意**: 此API会触发Portfolio优雅重启流程（详见information-flow.md路径3）

---

### 6. 查询Portfolio状态

**Endpoint**: `GET /api/portfolio/{portfolio_id}/status`

**响应**: `200 OK`
```json
{
  "portfolio_id": "portfolio_uuid",
  "name": "My Trading Portfolio",
  "status": "running",
  "cash": 95000.00,
  "total_value": 150000.00,
  "position_count": 5,
  "node_id": "execution_node_001",
  "updated_at": "2026-01-04T10:00:00Z"
}
```

---

### 7. 查询Portfolio持仓

**Endpoint**: `GET /api/portfolio/{portfolio_id}/positions`

**查询参数**:
- `code` (optional): 过滤特定股票
- `limit` (optional): 默认100，最大1000

**响应**: `200 OK`
```json
{
  "portfolio_id": "portfolio_uuid",
  "positions": [
    {
      "code": "000001.SZ",
      "direction": "long",
      "volume": 1000,
      "available_volume": 1000,
      "cost_price": 10.00,
      "current_price": 10.50,
      "market_value": 10500.00,
      "profit_loss": 500.00,
      "profit_loss_ratio": 0.05
    }
  ],
  "total_count": 5
}
```

---

### 8. 查询Portfolio历史

**Endpoint**: `GET /api/portfolio/{portfolio_id}/history`

**查询参数**:
- `start_date` (required): 开始日期，格式`YYYY-MM-DD`
- `end_date` (required): 结束日期，格式`YYYY-MM-DD`
- `limit` (optional): 默认1000

**响应**: `200 OK`
```json
{
  "portfolio_id": "portfolio_uuid",
  "history": [
    {
      "timestamp": "2026-01-04T10:00:00Z",
      "cash": 95000.00,
      "total_value": 150000.00,
      "daily_pnl": 1500.00,
      "position_count": 5
    }
  ],
  "total_count": 1000
}
```

---

## 调度管理 API

### 9. 查询调度计划

**Endpoint**: `GET /api/schedule/plan`

**响应**: `200 OK`
```json
{
  "plans": [
    {
      "node_id": "execution_node_001",
      "portfolio_ids": ["portfolio_001", "portfolio_002", "portfolio_003"],
      "portfolio_count": 3
    },
    {
      "node_id": "execution_node_002",
      "portfolio_ids": ["portfolio_004", "portfolio_005"],
      "portfolio_count": 2
    }
  ],
  "total_nodes": 2,
  "total_portfolios": 5
}
```

---

### 10. 手动迁移Portfolio

**Endpoint**: `POST /api/schedule/migrate`

**请求**:
```json
{
  "portfolio_id": "portfolio_001",
  "source_node": "execution_node_001",
  "target_node": "execution_node_002"
}
```

**响应**: `200 OK`
```json
{
  "success": true,
  "portfolio_id": "portfolio_001",
  "status": "migrating",
  "source_node": "execution_node_001",
  "target_node": "execution_node_002",
  "estimated_time": 30
}
```

---

## Node管理 API

### 11. 查询所有ExecutionNode

**Endpoint**: `GET /api/nodes`

**响应**: `200 OK`
```json
{
  "nodes": [
    {
      "node_id": "execution_node_001",
      "host": "192.168.1.10",
      "port": 8001,
      "status": "active",
      "portfolio_count": 3,
      "last_heartbeat": "2026-01-04T10:00:00Z"
    },
    {
      "node_id": "execution_node_002",
      "host": "192.168.1.11",
      "port": 8001,
      "status": "active",
      "portfolio_count": 2,
      "last_heartbeat": "2026-01-04T10:00:00Z"
    }
  ],
  "total_count": 2
}
```

---

### 12. 查询Node详情

**Endpoint**: `GET /api/nodes/{node_id}`

**响应**: `200 OK`
```json
{
  "node_id": "execution_node_001",
  "host": "192.168.1.10",
  "port": 8001,
  "status": "active",
  "portfolio_count": 3,
  "portfolios": [
    {
      "portfolio_id": "portfolio_001",
      "status": "running",
      "interest_count": 100
    }
  ],
  "last_heartbeat": "2026-01-04T10:00:00Z",
  "uptime": 86400
}
```

---

### 13. 禁用Node

**Endpoint**: `POST /api/nodes/{node_id}/disable`

**请求**:
```json
{
  "reason": "Maintenance",
  "migrate_portfolios": true
}
```

**响应**: `200 OK`
```json
{
  "success": true,
  "node_id": "execution_node_001",
  "status": "disabled",
  "portfolio_migration_started": true,
  "message": "Node disabled, portfolios are being migrated"
}
```

---

## 监控查询 API

### 14. 查询系统健康状态

**Endpoint**: `GET /api/health`

**响应**: `200 OK`
```json
{
  "status": "healthy",
  "components": {
    "api_gateway": "healthy",
    "livecore": {
      "data": "healthy",
      "trade_gateway": "healthy",
      "live_engine": "healthy",
      "scheduler": "healthy"
    },
    "kafka": "healthy",
    "redis": "healthy",
    "mysql": "healthy",
    "clickhouse": "healthy"
  },
  "timestamp": "2026-01-04T10:00:00Z"
}
```

---

### 15. 查询性能指标

**Endpoint**: `GET /api/metrics`

**查询参数**:
- `component` (optional): 过滤特定组件
- `start_time` (required): 开始时间戳
- `end_time` (required): 结束时间戳

**响应**: `200 OK`
```json
{
  "metrics": [
    {
      "component": "execution_node_001",
      "metric_name": "portfolio.queue_size",
      "value": 500,
      "timestamp": "2026-01-04T10:00:00Z"
    },
    {
      "component": "execution_node_001",
      "metric_name": "portfolio.processing_time_ms",
      "value": 150,
      "timestamp": "2026-01-04T10:00:00Z"
    }
  ],
  "total_count": 1000
}
```

---

### 16. 查询告警历史

**Endpoint**: `GET /api/alerts`

**查询参数**:
- `severity` (optional): 过滤严重级别（critical/warning/info）
- `source` (optional): 过滤来源（如execution_node_001）
- `start_time` (required): 开始时间戳
- `end_time` (required): 结束时间戳
- `limit` (optional): 默认100，最大1000

**响应**: `200 OK`
```json
{
  "alerts": [
    {
      "alert_id": "alert_uuid",
      "alert_type": "queue_full",
      "severity": "critical",
      "source": "execution_node_001",
      "message": "Portfolio portfolio_001 queue is 95% full",
      "details": {
        "portfolio_id": "portfolio_001",
        "queue_size": 950,
        "queue_max": 1000
      },
      "timestamp": "2026-01-04T10:00:00Z"
    }
  ],
  "total_count": 50
}
```

---

## 错误响应格式

所有API错误响应遵循统一格式：

**4xx 客户端错误**:
```json
{
  "error": true,
  "code": "INVALID_PARAMETER",
  "message": "Parameter 'initial_cash' must be positive",
  "details": {
    "field": "initial_cash",
    "value": -1000
  },
  "timestamp": "2026-01-04T10:00:00Z"
}
```

**5xx 服务器错误**:
```json
{
  "error": true,
  "code": "DATABASE_ERROR",
  "message": "Failed to update portfolio configuration",
  "details": {
    "portfolio_id": "portfolio_uuid",
    "reason": "Connection timeout"
  },
  "timestamp": "2026-01-04T10:00:00Z"
}
```

---

## 通用错误码

| 错误码 | HTTP状态 | 说明 |
|--------|---------|------|
| `UNAUTHORIZED` | 401 | 认证失败 |
| `FORBIDDEN` | 403 | 权限不足 |
| `NOT_FOUND` | 404 | 资源不存在 |
| `INVALID_PARAMETER` | 400 | 参数错误 |
| `DATABASE_ERROR` | 500 | 数据库错误 |
| `KAFKA_ERROR` | 500 | Kafka错误 |
| `REDIS_ERROR` | 500 | Redis错误 |
| `INTERNAL_ERROR` | 500 | 内部错误 |

---

## Rate Limiting

所有API请求受Rate Limiting限制：

- **默认限制**: 100请求/分钟/IP
- **认证用户**: 1000请求/分钟/用户
- **超限响应**: `429 Too Many Requests`

**响应头**:
```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1640000000
```

---

## CORS配置

API Gateway支持跨域请求：

**允许的来源**:
- `http://localhost:3000` (开发环境)
- `https://yourdomain.com` (生产环境)

**允许的方法**: `GET`, `POST`, `PUT`, `DELETE`, `OPTIONS`

**允许的头部**: `Authorization`, `Content-Type`, `X-API-Key`

---

## 总结

### API分类

1. **引擎控制 API**: 启动/停止/查询引擎状态
2. **Portfolio管理 API**: CRUD操作 + 状态查询 + 持仓查询
3. **调度管理 API**: 查询调度计划 + 手动迁移
4. **Node管理 API**: 查询Node + 禁用Node
5. **监控查询 API**: 健康状态 + 性能指标 + 告警历史

### 认证方式

- JWT认证（推荐）
- API Key认证

### 限制

- Rate Limiting: 100请求/分钟/IP（认证用户1000请求/分钟）
- 分页查询默认100条，最大1000条

### 错误处理

- 统一错误响应格式
- 标准错误码定义

---

**下一步**: 参考`quickstart.md`了解API使用示例。
