# ADR-026: GINKGO_ENV 与 DEBUGMODE 彻底解耦（集群选择单一旋钮）

**Status:** Accepted
**Date:** 2026-07-25
**关联:**建立在 [ADR-004](ADR-004-dual-db-debug.md)（双实例）、[ADR-024](ADR-024-db-port-injection-debug-semantics.md)（端口 + debug 语义）、[ADR-025](ADR-025-env-cluster-consistency-guard.md)（启动期护栏）之上；**Supersedes ADR-024 Decision 1/2**（+1 判据与 "DEBUGMODE 标记连哪个库"）、**Supersedes ADR-025 Decision 1**（护栏断言判据由 DEBUGMODE 改 IS_DEV_ENV）；复用仓库已存在的 `GINKGO_ENV` 读取点（`livecore/trade_gateway_adapter.py`）。关联 memory `arch_database_debug_mode`。

## Context

ADR-025 的启动期护栏只是**止血**——它不消除根因，只在错配发生时拒启。根因是 ADR-024/025 都默认接受的强耦合：**`DEBUGMODE` 是"三合一旋钮"**，一个布尔同时管 ① 日志/@retry 退避（ADR-013）② MySQL/ClickHouse host（master/test）③ 宿主客户端端口首位 +1。

三合一耦合 + `.env` 可变共享态 = 两类真实事故：

1. **忘翻 debug / `.env` 残留**：一次 `debug on` 把 `mysql-test` 写进 `.env`，忘翻回来，下次"真实运行"静默连测试库（ADR-025 能在下一次启动拦下，但运行中 worker env 烘焙不可变，护栏对实盘链路仍漏）。
2. **临时 `set_debug(True)` 隐式切库**：`engine run` / `core test` 为开日志调 `set_debug(True)`，**副作用是隐式切到 test 集群**——调用方本意是日志，却改了 DB。解耦后 `set_debug` 不再切库，这个隐式副作用消失，但**反向风险浮现**：解耦后 `set_debug(True)` 在 PRODUCTION env 下不再切库，回测会**直连 master 写数据**。

仓库已存在 `GINKGO_ENV`（`trade_gateway_adapter.py:297` 用 `os.getenv("GINKGO_ENV","development")=="production"` 判 MVP 模拟成交是否执行），但它是**裸读小写默认值、不经 GCONF、不触发 ADR-025 bridge**的孤岛读口，与新增的大写语义冲突。

判定三条全中（难逆转 / 反直觉 / 真实取舍），立本 ADR 彻底解耦。

## Decision

### 1. 新增 `GINKGO_ENV ∈ {PRODUCTION, DEVELOPMENT}` 为集群选择单一旋钮

`GCONF.ENV` property（`config.py`）读 `GINKGO_ENV` env，取值**大写**（`.upper()`），单一决定连 master 还是 test：

- `DEVELOPMENT` → test 集群（`*-test` host + 宿主客户端端口 +1）
- `PRODUCTION` → master 集群（`*-master` host + 原端口）

`IS_DEV_ENV = (ENV == "DEVELOPMENT")`。`DEBUGMODE` **退回 ADR-013 纯日志/@retry 退避语义**，不再决定 host、不再决定 +1。

### 2. bridge-default：未设时从 DEBUGMODE 推断（零行为变化迁移）

`GINKGO_ENV` 未显式设置时，`GCONF.ENV` bridge 推断 `"DEVELOPMENT" if self.DEBUGMODE else "PRODUCTION"` 并写回 `os.environ`（材料化）。这保证**首次启动零行为变化**：现存部署（未设 `GINKGO_ENV`）的集群选择与解耦前完全一致。一旦用户执行 `ginkgo config set env ...` 把 `GINKGO_ENV` 写进 `.env`，bridge 不再触发，env 成为显式部署态。

### 3. +1 守卫与启动护栏判据改用 IS_DEV_ENV（supersede ADR-024 D1 / ADR-025 D1）

- `CLICKPORT`/`MYSQLPORT` +1 条件（ADR-024 Decision 1）：`self.DEBUGMODE` → `self.IS_DEV_ENV`。容器守卫（`is_container_environment()`）与幂等（`startswith("1")`）保留不变。
- `_assert_cluster_consistency` 断言判据（ADR-025 Decision 1）：期望后缀 `-test`/`-master` 对应 `IS_DEV_ENV` True/False（即 DEVELOPMENT/PRODUCTION），错误提示改 `ginkgo config set env DEVELOPMENT|PRODUCTION`。横幅 label 与颜色来源同步改 IS_DEV_ENV。

### 4. 回测/测试防误连：PRODUCTION env 下拒跑（防反向风险）

解耦后 `set_debug(True)` 不再切库，反向风险是回测在 PRODUCTION env 下直连 master 写数据。故在 `engine_cli.py`（engine run）、`core_cli.py`（backtest run / core test）的 `set_debug(True)` **之前**加守卫：`if GCONF.ENV == "PRODUCTION": 拒绝 + 提示 ginkgo config set env DEVELOPMENT; raise typer.Exit(1)`。`set_debug(True)` 仍保留（开日志）。`ginkgo debug on/off` 输出加 hint「集群选择请用 `ginkgo config set env`」。

### 5. CLI 闸门：`set env` 写 .env + 重启；`set debug` 退纯日志

- 新增 `ginkgo config set env DEVELOPMENT|PRODUCTION`（别名 DEV/PROD，normalize 大写）：`update_env_for_env` 写 `.env` 的 `GINKGO_ENV` + CLICKHOUSE/MYSQL host（DEVELOPMENT→`*-test` / PRODUCTION→`*-master`，Mongo 恒 master）+ `set_env` 同步本进程 + `docker compose up -d` 重启使 worker env 重新插值。
- `ginkgo config set debug on/off` **移除** `.env` 改写与 compose 重启副作用，仅 `set_debug` 写 config.yml（退纯日志）。

### 6. set_env 持久层是 .env 而非 config.yml

`set_env` 只同步本进程 `os.environ`，**不写 config.yml**。理由：① compose 需 `${GINKGO_ENV:-DEVELOPMENT}` 插值注入容器，持久值必须在 `.env`；② config.yml 在容器内 `:ro` 挂载（`docker-compose.yml` worker volume），容器侧不可写。`GINKGO_ENV` 是**部署态**（prod/dev），与 config.yml 的**用户偏好态**（debug 日志、cpu_ratio、路径）分层不同。

### 7. 统一读口：trade_gateway_adapter 改走 GCONF.ENV

`trade_gateway_adapter.py:297` 的 `os.getenv("GINKGO_ENV","development")=="production"` 改为 `GCONF.ENV == "PRODUCTION"`。消除孤岛读口（裸读小写默认、不经 GCONF、不触发 bridge）与大小写冲突。`system_service` status 上报新增 `env` 字段。

## Rationale

- **为何彻底解耦（而非继续守卫优先）**：ADR-024/025 的守卫/护栏是"够好的修复"，但根因（三合一耦合）仍在，事故会以新形态复发（本次发现的"临时 set_debug 隐式切库"反向风险即是）。`GINKGO_ENV` 读取点仓库已存在，解耦的边际成本主要是 config.py 一个 property + CLI 一个分支 + 判据替换，远小于 ADR-024 当初评估的"重构 config.yml 结构 + 存量迁移"——因为 bridge-default 把迁移成本降到了零（未设 env 时行为不变）。这是 ADR-025 Consequences 明确点名的"未来彻底解耦"增量。
- **bridge-default 的取舍**：备选是"强制所有部署显式设 GINKGO_ENV，不设就拒启"。但现存部署全未设，强制会大面积红。bridge 以零行为变化换取平滑迁移：现存部署继续工作，用户主动 `set env` 后才材料化为显式态。代价是 bridge 期间（env 未设）DEBUGMODE 仍间接影响集群（经 bridge）——但这是迁移期不可避免的过渡，且 ADR-025 护栏仍兜底。
- **为何回测拒跑生产而非仅警告**：回测写数据到 DB（signal/order/position 落库）。PRODUCTION env 下回测 = 写生产库，是真实数据污染。警告会被忽略（CLAUDE.md 归因纪律：宁可响亮报错不留静默兜底）。拒跑是 fail-loud，用户须显式 `set env DEVELOPMENT` 才能跑——一次明确的认知动作消除整个事故类。
- **为何 +1 判据用 IS_DEV_ENV 单判（不保留 DEBUGMODE 兜底）**：宿主 CLI 工作流是 localhost + env 决定集群。若保留 `DEBUGMODE or IS_DEV_ENV` 双判，DEBUGMODE=True 但 env=PRODUCTION 时仍会 +1，与"env 单一决定"矛盾且 reintroduce 耦合。单判 IS_DEV_ENV 让端口严格跟随集群，可预测。
- **secure.yml host 旁路**：`config.py:120` 的 `setdefault` 块是 host 的另一写入源（`~/.ginkgo/secure.yml`）。worker 容器不挂 secure.yml（`_has_local_secure=False`），整段跳过，host 全来自 env——故 secure.yml 不是 worker 连库来源，本 ADR 不动它。宿主侧 secure.yml 若显式设了 host，会覆盖 env 推断，此时以 secure.yml 为准（与解耦前行为一致）。

## Consequences

- **`ginkgo config set env DEVELOPMENT|PRODUCTION` 成为切换集群的唯一命令**；`ginkgo config set debug on/off` 仅切日志。两者正交。
- **ADR-024 Decision 1/2 superseded**：+1 判据改 IS_DEV_ENV；DEBUGMODE 不再是"连哪个库"的语义标记（退纯日志）。ADR-024 Decision 3（切换机制）实质由本 ADR 的 `set env` 接管。ADR-024 顶部标注演进说明。
- **ADR-025 Decision 1 superseded**：断言判据改 IS_DEV_ENV。ADR-025 护栏本身保留（横幅 + 逃生口 + 幂等不变），仍是错配兜底。ADR-025 顶部标注演进说明。
- **worker env 烘焙问题仍未根治**：`set env` 改 `.env` + `docker compose up -d` 重建容器才生效；**运行中** worker 带旧 env 仍连错。彻底解法是 worker 启动期读最新配置而非烘焙（ADR-024 Decision 5 范畴），本 ADR 不涉及。
- **Redis/Mongo 仍恒 master**：`update_env_for_env` 只切 MySQL/ClickHouse host（compose 无 `redis-test`/`mongo-test` 实例）。DEVELOPMENT env 下这两库仍打 master——已知坑，未变。
- **回测/测试在 PRODUCTION env 下被拒**：所有依赖 `engine run` / `core test` 的工作流须先 `set env DEVELOPMENT`。这是有意的行为变化（防误连生产）。
- **bridge 期 DEBUGMODE 仍间接影响集群**：env 未显式设时，bridge 从 DEBUGMODE 推断——故此期间改 DEBUGMODE 仍会经 bridge 切集群。材料化（`set env` 写 .env）后此间接影响消失。

## 判定标准自检

- ① **难逆转**：集群选择旋钮从布尔 DEBUGMODE 改为枚举 GINKGO_ENV，触及 config.py 核心 + CLI 闸门 + 守卫判据 + 回测准入——高。
- ② **反直觉**：①"debug 不再切库"对老用户反直觉；② bridge-default"未设 env 时从 debug 推断"是隐藏迁移逻辑；③回测在 PRODUCTION 被拒跑——满足。
- ③ **真实权衡**：彻底解耦（本 ADR，bridge 降迁移成本到零）vs 继续守卫优先（ADR-024/025，根因不除事故复发）vs 强制显式 env（大面积红）——有取舍支撑——满足。
