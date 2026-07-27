# 统一 API 响应格式

> ADR-025 第③步 HTTP ResponseMapper 基座。本文档与 `api/core/response.py` 实现逐字段对齐。

## Wire 形状

所有业务端点统一返回同一信封（前端 `web-ui/src/api/request.ts` + `types/api.ts` 已锁此形状）：

```json
{
  "code": 0,
  "data": "<业务数据, 成功时为实际值, 失败时为 null>",
  "message": "ok",
  "meta": { "page": 1, "page_size": 20, "total": 100, "total_pages": 5 },
  "trace_id": "a1b2c3d4e5f67890"
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | `int` | **0 = 成功**；非零 = HTTP 错误状态码（404/400/409/...） |
| `data` | `T \| null` | 业务数据；失败时为 `null`；即便 `None` 也保留该 key |
| `message` | `str` | 成功默认 `"ok"`；失败为错误描述 |
| `meta` | `PaginationMeta \| 省略` | **仅分页或显式传 meta 时出现**；普通响应省略此 key |
| `trace_id` | `str` | 请求追踪 ID（16 位 hex），便于日志关联 |

> **关键**：`meta` 是条件出现的 key——非分页响应**没有** `meta` 字段。这与前端 `types/api.ts` 中 `meta?: PaginationMeta`（可选）一致。

## 后端：构造响应

### Helper 函数（`api/core/response.py`）

```python
from core.response import ok, fail, paginated, pagination_meta
```

```python
# 成功
return ok(data={"id": 1})
return ok(data=portfolio_dict, message="created")

# 失败（一般用 raise 异常, 见下; fail 用于手动构造)
return fail(404, "Portfolio not found")

# 分页
return paginated(items=item_dicts, total=100, page=1, page_size=20)
```

### 响应信封泛型（ADR-025 第③步新增）

`ok()/fail()/paginated()` 运行期返回 **plain dict**——FastAPI 据此无法在 OpenAPI 中生成响应 schema。基座补 pydantic 信封泛型，端点声明 `response_model` 即得 schema + 响应字段裁剪，**wire 不变**：

```python
from core.response import APIResponse, PaginatedResponse

class PortfolioDTO(BaseModel):
    uuid: str
    name: str

@router.get("/{uuid}", response_model=APIResponse[PortfolioDTO])
async def get_portfolio(uuid: str):
    return ok(data=portfolio_dict)   # 仍返 dict, FastAPI 按 response_model 校验/序列化

@router.get("/", response_model=PaginatedResponse)
async def list_portfolios(page: int = 1, page_size: int = 20):
    return paginated(items=..., total=..., page=page, page_size=page_size)
```

- `APIResponse[T]`：泛型。`data: Optional[T]` 仅在声明 `APIResponse[ConcreteDTO]` 时起**类型化**作用；序列化形状与 `ok()` 逐字段一致（`meta` 非 None 才出现）。
- `PaginatedResponse`：`data` 为 items 列表、`meta` 为 `PaginationMeta`。若需 item 级强类型，改声明 `APIResponse[List[ItemDTO]]` 并手填 `meta`。

> **迁移进度**：基座已落地泛型，端点尚未接线。后续按域 PR（backtest → portfolio → ...）逐步给端点加 `response_model`，每个 PR 零 wire 变更。

## 异常 → 信封

业务错误**raise 异常**，由全局 handler 统一转信封（`api/main.py:105-110` 注册 `global_error_handler` 于 `Exception`/`APIError`/`HTTPException`）：

```python
from core.exceptions import NotFoundError, ValidationError, BusinessError, ConflictError

raise NotFoundError("Portfolio", uuid)          # → code 404
raise ValidationError("Invalid date", field="start_date")  # → code 400
raise BusinessError("Cannot delete running backtest")      # → code 400
raise ConflictError("Name exists", resource_type="Portfolio", resource_id=uid)  # → 409
```

`APIError.to_dict()` 输出 `{code, data: null, message, trace_id}`（不带 `meta`）。handler 据异常类型映射 HTTP 状态码与 envelope `code`。

### 错误码（= HTTP 状态码）

| 异常类 | code / HTTP | 说明 |
|---|---|---|
| `ValidationError` | 400 | 请求参数验证失败 |
| `BusinessError` | 400（可自定义） | 业务逻辑错误 |
| `UnauthorizedError` | 401 | 未授权 |
| `ForbiddenError` | 403 | 禁止访问 |
| `NotFoundError` | 404 | 资源未找到 |
| `ConflictError` | 409 | 资源冲突 |
| `RateLimitError` | 429 | 请求频率超限 |
| `ServiceUnavailableError` | 503 | 服务不可用 |
| `APIError`（基类） | 500 | 内部错误（默认） |

## 前端契约

`web-ui/src/api/request.ts` 响应拦截器自动解包：

```typescript
// request.ts:28 — code !== 0 抛错, 否则返回完整信封
if (data && typeof data.code === 'number' && data.code !== 0) {
  throw new Error(data.message || '操作失败')
}
return data  // 调用方拿到的就是 {code, data, message, meta?, trace_id}
```

类型（`web-ui/src/types/api.ts`）：

```typescript
interface APIResponse<T> { code: number; data: T; message: string; meta?: PaginationMeta; trace_id: string }
function isOk<T>(r: APIResponse<T>): r is APIResponse<T> & { code: 0 }  // code === 0 类型收窄
```

调用方无需手动判 `success` 字段——拦截器已把非零 `code` 转为异常，业务代码直接用 `response.data`。

## 例外（不走统一信封）

以下端点保持各自格式，**不要**套用本信封：

1. **健康检查** `/health`、`/api/health`：探活格式
2. **SSE** 端点：流式响应
3. **WebSocket**：双向消息协议

## 测试

```bash
# 信封 helper + 异常类
/home/kaoru/.ginkgo/.venv/bin/python -m pytest tests/api/test_response_format.py -v

# 信封泛型 + response_model 契约 (ADR-025 第③步)
/home/kaoru/.ginkgo/.venv/bin/python -m pytest tests/api/test_response_envelope.py -v
```

## 文件清单

- `api/core/response.py` — `ok/fail/paginated/pagination_meta` helper + `APIResponse[T]/PaginatedResponse` 泛型
- `api/core/exceptions.py` — `APIError` 家族 + `to_dict()`
- `api/middleware/error_handler.py` — 全局 `global_error_handler`（异常 → 信封）
- `web-ui/src/api/request.ts` — 响应拦截器（解包 `code`）
- `web-ui/src/types/api.ts` — `APIResponse<T>` / `PaginationMeta` 类型
- `tests/api/test_response_format.py` — helper + 异常测试
- `tests/api/test_response_envelope.py` — 泛型 + response_model 契约测试
