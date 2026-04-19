# 统一 API 响应格式指南

## 概述

Ginkgo API Server 现在使用统一的响应格式，确保所有端点返回一致的数据结构。这提高了前端开发体验，并使错误处理更加标准化。

## 响应格式

### 成功响应

```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "message": "Operation completed successfully"
}
```

### 错误响应

```json
{
  "success": false,
  "data": null,
  "error": "ERROR_CODE",
  "message": "Error message description"
}
```

### 分页响应

```json
{
  "success": true,
  "data": {
    "items": [ ... ],
    "total": 100,
    "page": 1,
    "page_size": 20,
    "total_pages": 5
  },
  "message": "Data retrieved successfully"
}
```

## 后端使用指南

### 1. 导入响应模型

```python
from core.response import APIResponse, PaginatedResponse, success_response, error_response, paginated_response
from core.exceptions import NotFoundError, ValidationError, BusinessError
```

### 2. 在路由中使用

```python
@router.get("/items", response_model=APIResponse[list[Item]])
async def list_items():
    items = await get_items()
    return {
        "success": True,
        "data": items,
        "error": None,
        "message": "Items retrieved successfully"
    }

# 或使用辅助函数
@router.get("/items", response_model=APIResponse[list[Item]])
async def list_items():
    items = await get_items()
    return success_response(data=items, message="Items retrieved successfully")
```

### 3. 分页响应

```python
@router.get("/items", response_model=PaginatedResponse[Item])
async def list_items(page: int = 1, page_size: int = 20):
    items, total = await get_paginated_items(page, page_size)
    return paginated_response(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )
```

### 4. 错误处理

```python
@router.get("/items/{uuid}")
async def get_item(uuid: str):
    item = await db.get_item(uuid)
    if not item:
        raise NotFoundError("Item", uuid)
    return success_response(data=item)

@router.post("/items")
async def create_item(data: ItemCreate):
    if not data.name:
        raise ValidationError("Name is required", "name")
    # ...
```

### 5. 自定义业务错误

```python
# 使用预定义错误
raise BusinessError("Cannot delete running backtest")

# 使用自定义错误码
raise BusinessError("Insufficient funds", "INSUFFICIENT_FUNDS")
```

## 前端使用指南

### 1. 导入类型

```typescript
import type { APIResponse, PaginatedResponse } from '@/types/api'
import { extractData, isSuccessResponse } from '@/types/api'
```

### 2. API 调用

```typescript
// 获取数据
const response = await portfolioApi.list()
if (response.success && response.data) {
  const portfolios = response.data
  // 使用数据
}

// 使用辅助函数提取数据
try {
  const portfolios = extractData(await portfolioApi.list())
  // 使用数据
} catch (error) {
  console.error('API Error:', error)
}
```

### 3. 分页数据

```typescript
const response = await backtestApi.list({ page: 1, page_size: 20 })
if (response.success && response.data) {
  const { items, total, page, total_pages } = response.data
  // 使用分页数据
}
```

### 4. 错误处理

```typescript
try {
  const result = await backtestApi.create(data)
} catch (error) {
  // 检查是否为 API 错误
  if (isErrorResponse(error)) {
    console.error(`Error: ${error.error} - ${error.message}`)
  }
}
```

## 错误码参考

| 错误码 | HTTP状态码 | 说明 |
|--------|-----------|------|
| `NOT_FOUND` | 404 | 资源未找到 |
| `VALIDATION_ERROR` | 400 | 请求参数验证失败 |
| `BUSINESS_ERROR` | 400 | 业务逻辑错误 |
| `CONFLICT` | 409 | 资源冲突 |
| `UNAUTHORIZED` | 401 | 未授权 |
| `FORBIDDEN` | 403 | 禁止访问 |
| `RATE_LIMIT_EXCEEDED` | 429 | 请求频率超限 |
| `INTERNAL_ERROR` | 500 | 内部服务器错误 |
| `SERVICE_UNAVAILABLE` | 503 | 服务不可用 |

## 迁移指南

### 现有端点迁移步骤

1. 更新 `response_model` 为 `APIResponse[T]` 或 `PaginatedResponse[T]`
2. 将返回值包装在新的响应格式中
3. 将 `HTTPException` 替换为对应的自定义异常
4. 更新前端 API 模块类型定义

### 迁移前

```python
@router.get("/items")
async def list_items():
    items = await get_items()
    return items
```

### 迁移后

```python
@router.get("/items", response_model=APIResponse[list[Item]])
async def list_items():
    items = await get_items()
    return success_response(data=items, message="Items retrieved")
```

## 测试

运行响应格式测试：

```bash
cd /home/kaoru/Ginkgo/apiserver
pytest tests/test_response_format.py -v
```

## 文件清单

### 后端文件
- `/home/kaoru/Ginkgo/apiserver/core/response.py` - 响应模型定义
- `/home/kaoru/Ginkgo/apiserver/core/exceptions.py` - 异常类定义
- `/home/kaoru/Ginkgo/apiserver/middleware/error_handler.py` - 全局错误处理器
- `/home/kaoru/Ginkgo/apiserver/api/backtest.py` - 已更新使用新格式
- `/home/kaoru/Ginkgo/apiserver/api/portfolio.py` - 已更新使用新格式

### 前端文件
- `/home/kaoru/Ginkgo/web-ui/src/types/api.ts` - 类型定义
- `/home/kaoru/Ginkgo/web-ui/src/api/modules/backtest.ts` - 已更新类型
- `/home/kaoru/Ginkgo/web-ui/src/api/modules/portfolio.ts` - 已更新类型

### 测试文件
- `/home/kaoru/Ginkgo/apiserver/tests/test_response_format.py` - 响应格式测试

## 注意事项

1. **向后兼容性**：健康检查端点 (`/health`, `/api/health`) 保持原有格式
2. **SSE 端点**：Server-Sent Events 端点保持原有格式，因为是流式响应
3. **WebSocket**：WebSocket 连接不受影响
4. **渐进迁移**：可以逐步迁移现有端点，无需一次性全部更新
