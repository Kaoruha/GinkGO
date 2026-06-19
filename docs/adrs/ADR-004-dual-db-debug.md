# ADR-004: Docker 双实例与 Debug 模式

**Status:** Accepted
**Date:** 2026-06-13

## Context

开发/调试时直连生产（master）数据库会污染真实数据、误删生产记录。需要一种机制让"调试态"自动连到隔离实例，且无需改代码、无需改配置分支。

## Decision

Docker 部署两套数据库（ClickHouse + MySQL），用端口前缀区分：

| 实例 | 用途 | ClickHouse | MySQL |
|---|---|---|---|
| master | 非 Debug（生产） | 8123 | 3306 |
| test | Debug（开发/测试） | 18123 | 13306 |

- Debug 模式下 `GCONF.CLICKPORT` 端口首位 +1（8123 → 18123），自动指向 test 实例。
- `.env` 默认 `GINKGO_CLICKHOUSE_HOST=clickhouse-test`。
- Vector 默认连 `clickhouse-test`，与 Worker/API 保持一致。
- 开启 Debug：`ginkgo system config set --debug on`。

## Rationale

- **数据隔离**：Debug 连 test，杜绝开发误操作命中 master。
- **零代码切换**：靠端口偏移而非配置分支，同一份代码在 Debug on/off 下自动选实例。
- **Vector 对齐**：数据写入端（Vector）与读取端（Worker/API）连同一实例，避免"写 master 读 test"的幽灵数据。

## Consequences

- 排查数据问题时，**第一步永远是确认当前连的是 master 还是 test**，不要假设。
- 新增依赖数据库的服务，其默认连接串必须遵循 test/master 双端口约定。
- 数据库操作前若未开 Debug 会连到 master，务必先 `--debug on`。
