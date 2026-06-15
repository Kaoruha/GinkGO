# 架构决策记录 (ADR)

本目录记录 Ginkgo 中**难以逆转、不看背景会反直觉、且经过真实权衡**的架构决策。
目的：让团队成员和 AI agent 在触碰这些区域时先读 ADR，避免把刻意设计当 bug 修复，或反复重开已定的问题。

## 格式

- 编号：`ADR-0xx-slug.md`，顺序递增（新决策取当前最大编号 +1）。
- 结构：标题 + `Status` / `Date` + `Context`（背景）+ `Decision`（决策）+ `Rationale`（为什么）；必要时加 `Consequences`。
- 判定标准：**三条全中**才收录——① 难以逆转 ② 不看背景会觉得反直觉 ③ 存在真实备选且做了取舍。不满足的决策不立 ADR。

## 索引

| 编号 | 标题 | 状态 | 日期 |
|---|---|---|---|
| ADR-001 | [组件边界与单向流动](ADR-001-component-boundary.md) | Accepted | 2026-06-13 |
| ADR-002 | [分层架构 API→Service→CRUD→DB](ADR-002-layered-architecture.md) | Accepted | 2026-06-13 |
| ADR-003 | [引擎二态简化](ADR-003-engine-two-mode.md) | Implemented | 2026-03-28 |
| ADR-004 | [Docker 双实例与 Debug 模式](ADR-004-dual-db-debug.md) | Accepted | 2026-06-13 |
| ADR-005 | [组件参数序列化对称](ADR-005-param-serialization.md) | Accepted | 2026-06-13 |
| ADR-006 | [多数据库角色分工](ADR-006-db-role-separation.md) | Accepted | 2026-06-13 |
| ADR-007 | [表结构 Model 驱动，禁止手动 ALTER](ADR-007-schema-model-driven.md) | Accepted | 2026-06-13 |
| ADR-008 | [策略框架能力边界](ADR-008-strategy-framework-capacity.md) | Accepted | 2026-06-03 |
| ADR-009 | [全局服务容器 service_hub](ADR-009-global-service-hub.md) | Accepted | 2026-06-13 |
| ADR-010 | [数据对象三层角色分离 Entity/ORM/DTO](ADR-010-entity-orm-dto-separation.md) | Accepted | 2026-06-13 |
| ADR-011 | [信号发射统一 Seam（Strategy + Risk）](ADR-011-signal-emission-seam.md) | Accepted | 2026-06-15 |

## 如何新增 / 修订

1. **新增**：取最大编号 +1，先过三标准自检，不满足则不立。
2. **修订既有决策**：**不删旧 ADR**，新建一篇并在旧文顶部标注 `Status: Superseded by ADR-0xx`，保持决策演进可追溯。
3. 代码里引用决策时，写 `详见 docs/adr/ADR-0xx-*.md`，建立"代码 ↔ 决策"双向链。
