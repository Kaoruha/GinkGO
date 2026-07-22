# ADR-024 CLI Client 模式（瘦客户端 + 远端 API + JWT）

- **Status**: Accepted
- **Date**: 2026-07-22
- **Related**: ADR-002（分层架构）、ADR-009（全局服务容器 service_hub）

## Context

当前 `ginkgo` CLI **没有 client 模式**：所有子命令经 `container.xxx_service()` 进程内调本地 Service，走 `CLI → Service → CRUD → DB`，操作的是**本机** DB。

- `install.py` 的 `--server` 只是"起 Docker 全栈后端"，不带 `--server` 是**半套本地**（装完仍需自己起 docker + `ginkgo init` 才能用），并非 client。
- CLI 全 `client/` 包唯一的 HTTP 调用是 `interactive_cli.ask_ollama` 连本地 Ollama，与业务无关。

**需求**：远端用户用 CLI 管理远端 Ginkgo 实例——拥有大部分能力（管理类禁止），**不在本地起 DB、不占本地算力**。

现状有利条件（决定方案可行性的关键）：
- API 侧已有**完整 JWT 登录**：`POST /api/v1/auth/login`（bcrypt + per-username 节流）+ `JWTAuthMiddleware`（Bearer 校验 + `PUBLIC_PATHS`）+ `create_access_token`。
- **分布式派发已就绪**：`backtest_task_service` → `BACKTEST_ASSIGNMENTS` → BacktestWorker；API `POST /backtest/{uuid}/start` 已能触发派发。
- 读端点存在：`GET /api/v1/data/bars` 等。

## Decision

### 1. install 二态化
- `--server`：全量后端（Docker + wait + 可选 kafkainit + 写本地 config/secure）。
- **默认（不带 `--server`）= client**：瘦装，跳过 docker/wait/init，写 **client 版 config.yml**（见下），**不写 secure.yml**（无本地 DB 密码）。砍掉原"半套本地"中间态。
- client 安装交互式问 `api.host`，支持不传用占位符、装完 `ginkgo config set` 改。

### 2. 模式判定 + 注入点（container seam，最小侵入）
- `GCONF` 新增字段：`mode`（`local` | `client`）、`api.host`、`api.port`、`api.tls`（env-backed：`GINKGO_MODE` / `GINKGO_API_HOST` / `GINKGO_API_PORT` / `GINKGO_API_TLS`）。
- CLI 命令体不动，仍调 `container.xxx_service()`；client 模式下 container 返回**远程代理 service**（同接口签名，内部 httpx 打 API），无代理的 service 直接 `raise ClientModeDisabled`。

### 3. 认证：复用 JWT，新增 CLI 登录命令
- 复用 API 既有 JWT；新增 `ginkgo user login [USERNAME]`（交互式 username + getpass 隐藏密码 + host 占位符兜底）、`logout`、`whoami`。
- JWT 存 `$GINKGO_DIR/auth.json`（**chmod 600**）：`api_base / token / expires_at / user{uuid,username,is_admin}`。
- **密码不落盘**（仅 login 执行时内存，POST 完即丢）；落盘的是 bearer token。理由见 Rationale。

### 4. 续期：新增 `/auth/refresh`（无感续期）
- 新增 `POST /api/v1/auth/refresh`：校验传入 JWT（允许近过期）→ 重签新 JWT。
- `ApiClient` 在 `expires_at - now < 5min` 或收到 401 时**自动 refresh** 写回 auth.json，业务调用透明；refresh 失败再提示重登。
- 免登命令（`user login/logout/whoami`、`version`、`help`）无 token 放行。

### 5. 算力：纯 client，零本地计算
- client **从不本地跑算力**。`backtest run` → `POST /backtest/{uuid}/start`（服务端 Kafka 派发 BacktestWorker）+ 客户端轮询 `GET /backtest/{uuid}` 到 completed + `cat` 结果。client **不 import `BacktestOrchestrator`**。
- 算力三分工：回测=BacktestWorker、实盘/模拟盘执行=ExecutionNode、数据=DataWorker，全在服务端。

### 6. 能力边界（白名单允许 / 黑名单管理类禁止）
- **允许**（读 + 业务写）：portfolio / backtest / deploy / data 查询 / component / record / compare / status / version。
- **禁止**（管理类，client 模式启动期注册即拦截）：serve / init / debug / config set / test / dev / logging 写 / kafka / worker / livecore / migrate。
- 纵深防御：`is_admin=true` 也不放行管理端点——靠白名单代理 + JWTAuthMiddleware 双层，不信客户端自报角色。

### 7. 代理边界（关键反直觉点）
- **CRUD/读类命令**（portfolio create/list、backtest create/cat/list）：单一 service 方法 → **service-seam 代理干净**，命令体零改动。
- **UseCase 编排类**（`backtest run`）：是 `orchestrator + progress + aggregator` 组合，**不是单一 service 方法**，无法代理 → **命令体按模式分支**（client 走提交 + 轮询）。强行代理等于重写 orchestrator，不诚实。

## Rationale

- **为何复用 JWT 不造静态 token**：API 基础设施（login/bcrypt/中间件/节流）已就绪；静态 token 反而要新造一套且无用户隔离、无细粒度撤销。
- **为何密码不落盘、token 落盘**：token 是 bearer，到期前可撤销（`logout` 清本地、JWT 过期失效）；存密码=泄露即永久冒充。续期靠 refresh 端点（凭近过期 JWT 换新），**非存密码自动重登**。
- **为何 service-seam 代理有边界**：container 是现成 DI 注入点，CRUD 类零改动；但 UseCase 编排不是 service 方法，命令体分支比伪装代理更诚实（ADR-022 §3 不静默）。
- **为何纯 client 不本地算**：瘦 client 的价值=提交即走 + 结果权威在 server + 不占本地。`GET /data/bars` 虽存在，但本地算会破三个边界：**信任边界**（server 须信任 client 上传结果）、**结果归属**（本地算的回测算谁的）、**瘦 client**（须装引擎运行时）。得不偿失。
- **为何不在 CLI 命令体统一加 HTTP 分支**：会让每个命令体都背负双路径；container seam 把 CRUD 类的双路径收敛到一处。

## Consequences

- **正向**：远端用户瘦装即可管理；算力集中 server；API 侧几乎零改（仅加 `/auth/refresh` + 补代理所需端点）；复用现有 JWT/分布式派发。
- **成本**：须为白名单 service 逐个写 RemoteService 代理（MVP 先 portfolio + backtest）；client 依赖 server 可用性；refresh 端点须定有效期/撤销策略；长任务（backtest 轮询）中途 token 过期须中止 + 提示重登重跑（不假成功）。
- **未来扩展**：`hybrid` 模式（本地算 + 远端数据）作为**可选第三态**或 `backtest run --local` 开关，**不进 MVP**——opt-in 用户接受数据拉取/结果回写/装 runtime 的成本。
