# ADR-025: 启动期集群一致性护栏（防 debug/host 漂移静默连错库）

**Status:** Accepted
**Date:** 2026-07-25
**关联:** 源自 #6756 / PR #6773；建立在 [ADR-004](ADR-004-dual-db-debug.md)（双实例）与 [ADR-024](ADR-024-db-port-injection-debug-semantics.md)（端口 + debug 语义）之上；关联 memory `arch_database_debug_mode`。

## Context

ADR-004/024 确立的机制下，`DEBUGMODE` 是**"三合一旋钮"**——一个布尔同时决定多件事：

| 维度 | debug=on（测试） | debug=off（生产） |
|---|---|---|
| MySQL host | `mysql-test` | `mysql-master` |
| ClickHouse host | `clickhouse-test` | `clickhouse-master` |
| Redis host | `redis-master`（**不切**） | `redis-master` |
| MongoDB host | `mongo-master`（**不切**） | `mongo-master` |
| 宿主客户端端口 | 首位 +1（`13306`/`18123`） | 原始（`3306`/`8123`） |
| 日志 / @retry 退避 | debug 态（ADR-013） | 生产态 |

切换由 `ginkgo config set debug on/off` 完成：写 config 文件 `debug` 字段 + `update_env_for_debug` 改写 `.env` 的 MYSQL/CLICKHOUSE host + `docker compose up` 重启。Redis/Mongo **无 `-test` 实例**，恒连 master（docker-compose 仅 `redis-master`/`mongo-master`）。

**脆弱点**：`.env` 是**可变共享态**——一次 `debug on` 把 `mysql-test` 写进去，忘翻回来，下次"真实运行"就**静默连测试库**，无报错、无提示。更糟：worker env **烘焙不可变**（ADR-024），改 `.env` + 重启对**已活着的 worker** 不一定生效，等于这层护栏对实盘链路是漏的。"真实运行经常配到测试环境却无人察觉"——这正是本 ADR 要止血的。

## Decision

在 `GCONF.MYSQLHOST`/`CLICKHOST` 首次访问时**惰性**做一致性校验 + 打集群横幅（`_assert_cluster_consistency()`，幂等）：

1. **断言**：host 落 `*-master`/`*-test` 体系时，后缀必须与 `DEBUGMODE` 一致（debug=on 期望 `-test`，off 期望 `-master`），否则 `RuntimeError` 拒启，并提示 `ginkgo config set debug on/off` 重对齐。
2. **横幅**：每进程首行 stderr 打印 `=== [PROD] MySQL=… / ClickHouse=… ===`（prod 红 / test 绿），一眼可辨。
3. **不误伤**：localhost / 外部域名不在 master/test 体系 → 断言跳过（外部部署、单测直传 localhost 不受影响）。
4. **逃生口**：`GINKGO_SKIP_CLUSTER_GUARD=1` 仅跳断言、横幅照打（测试环境 / 特殊部署）。
5. **幂等**：`GinkgoConfig._cluster_guard_done` 类属性保证每进程只执行一次。
6. **范围**：只校验 MySQL + ClickHouse（这两才随 debug 切）；Redis/Mongo 恒 master，不校验。

## Rationale

- **为何不彻底解耦（独立 `GINJKGO_ENV` 选库 + debug 退回纯日志开关）**：与 ADR-024「守卫优先于彻底删 +1」同思路——彻底解耦须重构 config.yml 结构 + `set_debug` + 存量迁移，面大、有迁移风险；最小护栏（一个 property 内的断言）以 ~30 行达到**同等止血**（错配不再静默）。纯粹性的收益不足以抵消重构成本。彻底解耦留作未来增量（见 Consequences）。
- **为何放 property 惰性触发**：覆盖所有走 `GCONF.MYSQLHOST/CLICKHOST` 建连接的入口（serve/worker/CLI/回测），无需改各入口；测试里直传 host 的 driver 不经 property，天然不受影响。
- **逃生口的必要性**：测试与外部部署 host 不在 master/test 体系，强制断言会大面积红；逃生口让横幅照打（仍声明实际连接）、断言可跳，平衡"治本"与"不破坏现有测试"。
- **横幅走 stderr 而非 GLOG**：property 在进程极早期被访问，GLOG 此刻可能未就绪，stderr 最稳且始终可见。

## Consequences

- **冲突部署首次启动会被拦**：现存 `.env` 若与 config 文件 `debug` 字段不一致，serve/worker 启动即 `RuntimeError`。这是**预期行为**（暴露现存漂移），修复方式是 `ginkgo config set debug on/off` 重对齐后重启。
- **Redis/Mongo 不切是已知坑**：debug=on 时这两库仍打 master（compose 无 `-test` 实例）。护栏不覆盖它们——若需隔离须先补 test 实例。
- **未来彻底解耦时本护栏可精简**：引入 `GINJKGO_ENV` 后 host 与 env 一致性天然成立，断言变冗余可删；横幅仍保留（声明性输出有价值）。
- **worker env 烘焙问题未根治**：护栏能在 worker**下次重启**时拦下错配，但对**运行中**的 worker 仍无效（env 已烘焙）。彻底解法是 worker 启动期读最新配置而非烘焙——属 ADR-024 Decision 5（CLI 双模 / 配置注入）范畴。

## 判定标准自检

- ① **难逆转**：启动期拒启是 behavioral change，所有部署首次升级都受影响——中。
- ② **反直觉**：debug off 却连 `-test` 被拒启，不理解 debug/host 耦合的人会困惑"为什么不让我启动"——满足。
- ③ **真实权衡**：彻底解耦（`GINJKGO_ENV`，重构大）vs 最小护栏（断言，~30 行同等止血）+ 逃生口取舍——满足。
