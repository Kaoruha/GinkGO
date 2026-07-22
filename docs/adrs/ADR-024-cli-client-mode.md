# ADR-024 CLI Client 模式（混合架构：数据面直连 DB + 控制面 API + JWT）

- **Status**: Accepted
- **Date**: 2026-07-22（2026-07-23 修订：纯瘦客户端 → 混合架构）
- **Related**: ADR-002（分层架构）、ADR-009（全局服务容器 service_hub）、ADR-022（不静默）

## Context

远端用户（机器 B）想用 `ginkgo` CLI 管理和使用服务器实例（机器 A）。关键约束：

- **B 装了 ginkgo 源码（含引擎），但没有本地数据**——"拉取全数据才是最费事的"，B 不复制 A 的数据。
- B 与 A 网络可达。A 跑全栈（API + Docker DB + workers）。
- **DB 是直连，没有专门的 DB 账号**——B 复用 A 现有 DB 凭据连 A 的库（无法靠 DB 权限做细粒度管控）。
- 危险操作（建表 / migrate / schema 变更）在 B 侧必须禁止。

由此分出两条平面：

- **数据面**：引擎内部对 bar / result 的读写（回测热路径）。
- **控制面**：命令 / 任务 / 认证（人类面向的管理操作）。

现状有利条件：
- API 侧已有完整 JWT 登录：`POST /api/v1/auth/login`（bcrypt + 节流）+ `JWTAuthMiddleware` + `create_access_token`。
- 分布式派发已就绪：`backtest_task_service` → `BACKTEST_ASSIGNMENTS` → BacktestWorker；`POST /backtest/{uuid}/start` 已能触发派发。
- 数据获取是**每交易日批量**（`backtest_feeder._fetch_day_bars_batch` 一次 `bar_service.get(code=None, ...)`），结果回写是**每事件单记录**（`t1backtest._save_order_record` → `result_service.create_order_record`）——两者对远端友好。

## Decision

### 1. 混合架构（两条平面，两种连接）

| 平面 | 内容 | B 的连接方式 | 代码改动 |
|---|---|---|---|
| 数据面 | 引擎 bar 读取 / result 回写 | **直连 A 的 DB**（`GCONF` database 段指向 A 的 IP/端口） | **零代码改**（service 读配置的库） |
| 控制面 | 命令 / 任务 / 认证 | **经 A 的 API**（JWT） | container seam 远端代理 |

- A 的 API host 与 DB host 是**同一台机（A）**，故 client 配置把数据面 DB 与控制面 API 指向同一个 `api_host`。
- `GCONF` 新增字段：`mode`（`local` \| `client`）、`api_host`/`api_port`/`api_tls`/`api_base`（env-backed：`GINKGO_MODE` / `GINKGO_API_*`）。

### 2. container seam：控制面 CRUD 走远端代理，数据面 service 不动

- **控制面 CRUD**（如 `portfolio_service`）：client 模式经 `providers.Selector` 返回**远端代理 service**（同接口签名，内部 httpx 打 API）→ 命令体零改。
- **数据面 service**（`bar_service` / `result_service` / assembly 用的 DB crud）：**保持本地 Singleton 直连 DB**，不做 Selector——这正是"数据面零代码改"，引擎读写的就是 `GCONF` 指向的 A 的库。

### 3. `backtest run`：默认本地引擎，`--remote` 提交 server

- **默认**（无 flag）：B 本地跑引擎。引擎经 datafeeder 读 A 的 DB（数据面）、经 `result_service` 写 A 的 DB。client 模式与 local 模式**同一执行路径**，仅 `GCONF` 指向的库不同。
- **`--remote`**：走控制面 API，`POST /backtest/{uuid}/start`（server Kafka 派发 BacktestWorker）+ 客户端轮询到 completed + `cat` 结果。适合重任务想借用 server 算力。
- `run` 是 UseCase 编排（`orchestrator + progress + aggregator`），**非单一 service 方法**，无法代理 → **命令级分支**（`--remote` flag），不走 Selector（ADR-022 §3 不静默）。

### 4. install 二态化（client 仍装引擎）

- `--server`：全量后端（Docker + 本地 DB + config/secure）。
- **默认（不带 `--server`）= client**：
  - **装 ginkgo 包（含引擎）**——支持默认本地 `backtest run`。**不是"不装引擎的瘦客户端"。**
  - 不起 Docker / 不建本地 DB 卷。
  - 写 **client 版 config.yml**：`mode: client` + 数据面 DB 指向 A（`mysql_host`/`clickhouse_host`/`redis_host` = `api_host` 等）+ 控制面 API（`api_host`/`api_port`/`api_tls`）。
  - 写 **secure.yml**（共享 DB 凭据——B 复用 A 的库账号；安装期占位，装完 `ginkgo config set` 填 A 的真实凭据）。
  - 交互式问 `api_host`（即 A 的地址，同时作数据面 DB 与控制面 API 的端点）。

### 5. 认证：复用 JWT，新增 CLI 登录命令（保留 Phase1）

- 复用 API 既有 JWT；`ginkgo user login [USERNAME]`（getpass 隐藏密码）、`logout`、`whoami`。
- JWT 存 `$GINKGO_DIR/auth.json`（**chmod 600**）：`api_base / token / expires_at / user{...}`。**密码不落盘**。
- 新增 `POST /api/v1/auth/refresh`（凭近过期 JWT 换新）；`ApiClient` 在近过期 / 401 时自动 refresh 写回。
- 免登命令（`user login/logout/whoami`、`version`、`help`）无 token 放行。

### 6. 危险操作拦截（client 模式禁止 DDL / schema 变更）

- **CLI 层**：client 模式下 `ginkgo init` / `ginkgo migrate` 等 DDL / schema 类命令直接拒绝，明确提示"在 server（A）执行"。
- **API 层（纵深防御）**：API 拒绝 client 发起的 DDL / schema 变更请求——不信 client 自报角色，`is_admin` 也不放行 DDL（白名单 + JWTAuthMiddleware 双层）。
- **诚实限制**：DB 无专门账号，无法靠 DB 权限拦 DDL；绕过 CLI 直接连 A 的 DB 做 DDL **无法阻止**（B 本就有共享 DB 凭据）。拦截是"提高门槛 + 明确意图"，非绝对墙。

### 7. 代理边界（沿用，关键反直觉点）

- **CRUD / 读类命令**（portfolio create/list、backtest create/cat）：单一 service 方法 → service-seam 代理干净，命令体零改。
- **UseCase 编排类**（`backtest run`）：`orchestrator + progress + aggregator` 组合 → 命令级分支（`--remote`），不伪装代理。

## Rationale

- **为何混合而非纯瘦客户端**：用户场景是"B 装了引擎、只是没数据"。让 B 本地跑回测（读 A 的库）比每次提交 server 排队更直接；数据面直连 DB **零代码改**（复用现有 service）。纯瘦客户端（旧方案）把算力全压 server，既浪费 B 的引擎，又须为 bar/result 造回写 API 端点——得不偿失。
- **为何数据面直连 DB 不走 API**：bar/result 是引擎热路径，直连 DB 复用现有 service 零改；走 API 须造端点 + 逐事件 HTTP（虽"先别管性能"，但端点成本仍高）。本地算的结果写 A 的库，**归属明确**（A 的库），无信任歧义。
- **为何控制面走 API**：命令 / 任务管理须认证 + 拦截危险操作（DDL），API 是天然控制点；直连 DB 做控制面会绕过认证、无法拦 DDL。
- **为何危险操作拦截在 API 而非 DB**：DB 无专门账号，无法靠 DB 权限拦；依赖 API 层（+ CLI 路由）。诚实承认绕过 CLI 的直连 DDL 无法阻止。
- **为何复用 JWT 不造静态 token**：API 基础设施已就绪；静态 token 须新造一套且无用户隔离、无撤销。
- **为何 service-seam 代理有边界**：container 是现成 DI 注入点，CRUD 类零改；但 UseCase 编排不是 service 方法，命令级分支比伪装代理更诚实（ADR-022 §3）。

## Consequences

- **正向**：B 瘦装（无 Docker）即可本地回测读 A 数据 + 经 API 管理；数据面零代码改；复用 JWT / 分布式派发；危险操作有明确拦截。
- **成本**：
  - B 须配置 A 的 DB 直连（共享凭据，安装期占位、装完填）。
  - 控制面命令依赖 A 的 API 可用性；client 本地回测须能连 A 的 DB。
  - 须为白名单控制面 service 逐个写远端代理（MVP 先 portfolio；backtest 走命令级 `--remote`）。
  - 长任务（`--remote` 轮询）中途 token 过期须中止 + 提示重登重跑（不假成功）。
- **诚实限制**：B 持共享 DB 凭据，绕过 CLI 直连做 DDL 无法阻止；拦截是"提高门槛 + 明确意图"。
- **未来扩展**：纯瘦客户端（零本地算、全部提交 server）可作为 `--remote`-by-default 的可选配置，不进 MVP。
