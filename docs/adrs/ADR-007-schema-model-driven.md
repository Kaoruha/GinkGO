# ADR-007: 表结构 Model 驱动，禁止手动 ALTER

**Status:** Accepted
**Date:** 2026-06-13

## Context

手动 `ALTER TABLE` 改表会破坏 master/test 双实例的一致性（见 ADR-004），且会被后续的 init 建表覆盖，导致"改了又消失"的幽灵问题。

## Decision

- **所有表由 SQLAlchemy Model 定义**，通过 `ginkgo init` 自动创建。
- **新增字段**：先改 Model，再重新 `ginkgo init`。
- **禁止任何形式的手动 `ALTER TABLE`**。

## Rationale

- Model 是表结构的**单一真相源**，代码即 schema，避免"表结构和代码定义不一致"。
- `ginkgo init` 重建时，手动 ALTER 的改动必然丢失；Model 驱动则幂等可重现。
- 保持 master/test 用同一套 Model 生成，杜绝双实例漂移。

## Consequences

- 缺字段时，**改 Model 然后重 init**，不要手动补列。
- 排查 Vector 400 错误时，检查目标表（master/test）的列是否与 Vector 输出字段匹配——若不匹配，是 Model 落后，改 Model。
- 新表的测试必须在测试后清理 metadata，避免污染后续用例。
