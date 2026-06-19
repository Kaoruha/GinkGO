# ADR-014: core/database.py 半 gitignore + api 层禁裸 SQL

**Status:** Accepted
**Date:** 2026-06-19

## Context

`api/core/database.py`（及其同名模式文件）是一个**本地存在、但从不入库**的模块：

- `.gitignore:192` 用通配符 `database.*` 屏蔽所有 `database.*` 模式文件。
- `git ls-files | grep core/database` 为空——该文件**从未被 master 跟踪**，仅存在于开发者本地。
- `#6177` / PR `#6179`（`550e8e55`，merge `581908ce`，2026-06-19）：api 层清理对已弃用 `core.database` 的引用，改走服务层。

核心矛盾（也是本决策要防的坑）：**本地 `import core.database` 能跑，CI 必崩**。因为 master / CI 上根本没有该文件，任何 api 源文件 `import` 它都会在 import 阶段抛 `ModuleNotFoundError`，导致 `ginkgo serve api` 启动失败。

这条纪律不是靠口头约定，而是靠**守护测试**落地：`tests/api/test_core_database_cleanup.py:1` 注释明示"api 层不得再引用已弃用且被 gitignore 的 core.database 模块"，扫描 api 源文件，命中 `import` 即红灯。迁移范例：producer 端 `progress_tracker.py` 走 `BacktestTaskService`；`api/services/backtest_progress_consumer.py:19` 注释保留决策痕迹——"获取 BacktestTaskService 实例（走服务层，替代 core.database 裸 SQL）"。

## Decision

1. **`core/database.py` 维持 gitignore**：作为本地 debug 便利文件存在，不入库（含本地连接串 / 环境特定配置）。
2. **api 层禁裸 SQL**：`src/ginkgo/interfaces/api/` 禁止 `import core.database`，数据访问一律走 `ginkgo.data.containers.container` / 对应 Service。
3. **以守护测试执行纪律**：`tests/api/test_core_database_cleanup.py` 扫描 api 源文件，命中 `core.database` 引用即红灯。

## Rationale

- **为何 gitignore 而非删除**：本地直连裸 SQL 对 debug 友好，但含本地连接串 / 环境配置，入库会污染仓库；gitignore 保留本地便利，同时保证 CI 环境干净。
- **为何禁 api 层裸 SQL**：两层理由叠加——(1) 分层架构（ADR-002）规定 `API→Service→CRUD→DB`，api 层跨过 Service 直连裸 SQL 破坏分层；(2) `core.database` 不入库，api 一旦依赖它，"本地能跑、CI 必崩"的分裂必然重现。
- **已排除 A：把 `core.database` 提交入库**——含本地配置，且会鼓励 api 层直连，违背分层。
- **已排除 B：彻底删除本地文件**——牺牲本地 debug 体验，且本地 debug 仍有真实价值。

## Consequences

- **难逆转**：gitignore + 守护测试 + 已完成迁移三重锁定；`grep -rn 'core.database' src/ginkgo/interfaces/` 当前为空。
- **反直觉**：本地 `import core.database` 能跑、CI 必崩——典型"本地 / CI 分裂"陷阱。无本文档，下次有人想"顺手把 database.py 提交上来"时无人能引先例。
- **验证方式**：`tests/api/test_core_database_cleanup.py` 绿灯；`git ls-files | grep core/database` 为空；api 层 `grep core.database` 为空。
- **交叉引用**：ADR-002（分层架构 API→Service→CRUD→DB；本 ADR 是分层纪律在"不可入库的本地文件"这一具体场景的执行化）。

## 判定标准自检

- ① **难逆转**：gitignore + 守护测试 + 迁移三重锁定——满足。
- ② **反直觉**：本地能跑 / CI 必崩的分裂——满足。
- ③ **真实权衡**：本地直连裸 SQL（debug 快）vs 服务层（一致、可移植）——满足。
