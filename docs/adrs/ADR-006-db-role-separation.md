# ADR-006: 多数据库角色分工

**Status:** Accepted
**Date:** 2026-06-13

## Context

Ginkgo 同时处理海量时序行情、关系型实体、热缓存、非结构化文档。单一数据库无法同时满足这四类负载，混存会导致查询模型扭曲、性能互损。

## Decision

按数据特征分库，各司其职：

| 数据库 | 角色 | 存什么 |
|---|---|---|
| ClickHouse | 时序 | K线、Tick、行情、回测逐笔 |
| MySQL | 关系 | Portfolio、组件、回测记录、用户配置 |
| Redis | 缓存 | 热数据、会话、跨进程快取 |
| MongoDB | 文档 | 非结构化/半结构化文档 |

## Rationale

- **ClickHouse** 的列存与向量化查询天然适配海量时序扫描，MySQL 做同等规模会崩。
- **MySQL** 的强事务与关系约束保证 Portfolio/订单等核心实体的完整性。
- **Redis** 承担读多写少的 hot path，隔离慢查询对主库的冲击。
- **MongoDB** 收纳 schema 易变的文档，避免频繁 ALTER 关系表。

## Consequences

- 新增数据时，先按特征选库（时序→CH、关系→MySQL、热取→Redis、文档→Mongo），不要"哪里方便塞哪里"。
- 跨库关联只能在 Service 层用 ID 引用拼接，不在 DB 层做跨库 join。
- **装饰器缓存与 Redis 缓存是有意分层的**（局部函数缓存 vs 跨进程共享），不合并。
