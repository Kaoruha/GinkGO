# ADR-002: 分层架构 API/CLI → Service → CRUD → DB

**Status:** Accepted
**Date:** 2026-06-13

## Context

API 层若直接调用 CRUD，业务规则会散落在路由里，难以复用、难以测试；CRUD 实例（含 DB session）一旦被泄漏到上层，会造成生命周期失控和跨层悬挂引用。

## Decision

严格四层单向调用：

```
API / CLI → Service → CRUD → DB
```

规则：

1. **API 禁止直接调 CRUD**，必须通过 Service。
2. **Service 禁止暴露 CRUD 实例**，只返回业务结果或数据传输对象。
3. **CRUD 返回 `ModelList`**（ORM 模型集合），由调用方按需转换；不在 CRUD 层做 DTO 序列化。

## Rationale

- 业务规则集中在 Service 层，API / CLI / Web-UI 三种入口共享同一套规则。
- CRUD 实例不外泄，DB session 生命周期完全由 CRUD 内部管理。
- CRUD 返回 `ModelList` 保持数据层"纯读写"，转换职责上推，避免 CRUD 被各种 DTO 形态污染。

## Consequences

- 新增 API 端点前，先确认对应 Service 方法是否存在；不存在则先补 Service。
- 禁止为了"省一层"在 API 里 `from ...crud import xxx`。
- 新建 facade 时应替换同模块的 CRUD 直调（保持 facade 一致性）。
