# ADR-024: 数据库端口 +1 魔法加容器守卫 + Debug 模式语义重定义

**Status:** Proposed
**Date:** 2026-07-20
**关联:** 源自 `mysql-test` 连接根因排查（memory `project_schedule_data_update_broken`）+ config 统一重构（#6640）；细化并部分 supersede ADR-004（Docker 双实例与 Debug 模式）的端口约定；关联 ADR-013（Debug 改 @retry 退避语义，仍依赖 DEBUGMODE 标记）；关联 memory `arch_database_debug_mode` / `arch_docker_mysql_test_port_13306`。

## Context

ADR-004 确立 Docker 双实例：**Master（生产，内部 3306 / 宿主映射 3306）+ Test（调试，内部 3306 / 宿主映射 13306）**，Debug 模式切换连哪个实例。当前 debug 切换由**两处配合**完成：

- `config_cli.update_env_for_debug`（config_cli.py:34-38）切 `.env` 的 **HOST**：`mysql-master ↔ mysql-test`（mongo 恒 master，无 test 实例）。容器侧 debug 切实例靠它。
- `config.py` 的 `CLICKPORT`/`MYSQLPORT`（config.py:568-587）在 `DEBUGMODE=True` 时做 `"1"+port` 字符串拼接（3306→13306、8123→18123）切 **PORT**。宿主侧 debug 切端口靠它（宿主 CLI 的 `~/.ginkgo/config.yml` 无 mysql 节，port 全靠默认 + 此 +1 派生）。

`+1` 魔法的**意图**是正确的：宿主机经 Docker 映射端口访问 test 实例（`127.0.0.1:13306:3306`），宿主 CLI 该连 13306。

但**根因**（2026-07-20 实测，bar 停滞 8.5 个月的直接原因）：`+1` 在**应用层 `config.py`** 做端口映射算术，对**容器内服务**误用——容器内 `ginkgo-tasktimer` 跑在容器网络，连 `mysql-test` 应用**内部端口 3306**，但 `GCONF.MYSQLPORT` 被无差别 +1 到 13306 → 连 `mysql-test:13306` ECONNREFUSED → `create_mysql_connection` health_check 失败 3/3 → `_get_all_stock_codes()` 查 stockinfo 返空 → `bar_snapshot` 每日 "No stocks found, skipping" → bar/adjustfactor 停滞。

**铁证**：env / compose / .env 三处都写 `GINKGO_MYSQL_PORT=3306` 正确，唯独 `GCONF.MYSQLPORT` 读出 13306；socket 直连 `mysql-test:3306` 连续 10/10 通，13306 全失败；pymysql/SQLAlchemy 用 13306 全失败、3306 全成功。即"连不上"非网络/认证/资源，是 **GCONF 端口变换逻辑对容器内服务误用**。`CLICKPORT`（8123→18123）同 bug。

**深层**：`+1` 魔法把**基础设施层的事（Docker 端口映射）泄露进应用层（config.py）**，违反 ADR-002 分层。容器内外端口差异（容器内 3306 / 宿主映射 13306）是 Docker 端口映射的本质，应用层无差别 +1 无法区分"我是容器内服务（要原端口）"还是"我是宿主客户端（要映射端口）"，于是必然对一方误用。

判定三条全中（难逆转 / 反直觉 / 真实取舍），立本 ADR。

## Decision

### 1. +1 魔法加 `is_container_environment()` 守卫（不删，只对宿主生效）

曾考虑"完全删 +1，端口值对下沉注入层（compose 给容器 / config.yml 给宿主）"的最纯方案。但实测发现隐藏代价：**宿主 CLI 的 debug 切换当前完全依赖 +1 魔法**——`~/.ginkgo/config.yml` 无 mysql 节，port 全靠"默认 3306 + DEBUGMODE 时 +1"派生。完全删 +1 须同步给 config.yml 引入 mysql.port 字段 + 改造 `generate_config_file`/`set_debug` 写入端口值对 + 存量 config.yml 迁移——重构面大、有迁移风险，而收益（"config.py 对端口映射完全无知"的纯粹性）不足以抵消。

务实方案：**保留 +1 魔法，但加 `is_container_environment()` 守卫，仅宿主客户端 +1**。容器内服务（`is_container_environment()=True`）跳过 +1，原样读注入的内部端口 3306：

```python
@property
def MYSQLPORT(self) -> int:
    self._ensure_env_vars()
    port = os.environ.get("GINKGO_MYSQL_PORT", "3306")
    from ginkgo.libs.utils.log_utils import is_container_environment
    if (self.DEBUGMODE
            and not is_container_environment()      # 容器内服务不加前缀
            and not str(port).startswith("1")):      # 幂等：已是映射端口不重复加
        port = f"1{port}"
    return int(port)
```

`CLICKPORT` 同理。惰性 import 规避 `config ↔ log_utils` 包初始化循环。

**守卫的语义**：`+1` 规则从"无差别对所有调用方生效"收窄为"仅对宿主客户端（经 Docker 映射端口访问 test 实例）生效"。容器内外差异由 `is_container_environment()` 三重检测（env `DOCKER_CONTAINER`/`KUBERNETES_SERVICE_HOST` + `/proc/1/cgroup` + `/.dockerenv`）判定，应用层据此选行为，不再无差别误用。

### 2. DEBUGMODE 保留为"当前连哪个库"的语义标记

`DEBUGMODE` 属性保留（读 `GINKGO_DEBUG_MODE` env 或 config.yml `debug` 字段），语义不变：标记当前连 test 还是 master 实例。仍用于：

- 触发宿主客户端的 +1 端口派生（Decision 1，仅宿主）
- 日志/状态标注（当前操作落 test 还是生产库）
- ADR-013 的 `@retry` 退避语义（debug 下加速退避）
- `ginkgo debug on/off` 的切换状态机（`set_debug` 写 config.yml `debug` 布尔，宿主侧一键切换）

### 3. Debug 切换机制不变（保留一键切换）

宿主 CLI：`ginkgo debug on/off` 改 config.yml `debug` 布尔 → `DEBUGMODE` 变 → +1 守卫生效/失效 → port 切 13306/3306（HOST 恒 localhost）。**一键切换保留，机制不变**。

容器内服务：`config_cli.update_env_for_debug` 切 `.env` 的 HOST（mysql-master↔mysql-test），PORT 恒内部 3306（+1 被守卫跳过）。**容器侧切换也不变**。

| 场景 | debug off（生产/master） | debug on（测试/test） |
|---|---|---|
| 容器内服务 | `(mysql-master, 3306)` | `(mysql-test, 3306)` —— 切 HOST，+1 守卫跳过 |
| 宿主 CLI / api-server | `(localhost, 3306)` | `(localhost, 13306)` —— +1 守卫生效，HOST 恒 localhost |

### 4. 远程访问经 api-server 单端口，DB 零暴露

所有 DB 端口（mysql / clickhouse / redis / mongo / kafka）保持绑 `127.0.0.1`，**远程不直连 DB**。远程访问经 api-server 单端口（`0.0.0.0:8000` 或 nginx 8080 反代 + TLS），api-server 在本地代为查 DB。`config.py` 的 DB 配置只服务于"直连 DB 的实体"（容器服务 + 宿主 CLI + api-server 本身），远程 CLI 是 API 客户端，不在 DB 配置管辖内（另立配置项 `GINKGO_API_URL`，见下）。

### 5. CLI 双模（本地直连 / 外部 API）—— 关联方向，另立 ADR

同一 `ginkgo` CLI 二进制，`Backend` 适配层按 `GINKGO_API_URL` 切：未设 → `LocalBackend` 直连 Service/DB（本地运维特权，含 bootstrap 元命令、长任务、调试）；设为 URL → `HTTPBackend` 打 api-server（外部/远程）。bootstrap 元命令（`init` / `debug` / `serve` / `status`）锁定本地模式（api-server 依赖 DB，逻辑上先于 api-server）。此为独立大工程，**本 ADR 仅记录方向，实施细节另立 ADR-025**。

## Rationale

- **守卫 vs 完全删除的取舍**：完全删 +1 是最纯方案（config.py 对端口映射零知识），但宿主 debug 切换当前依赖 +1（config.yml 无 port 字段），删它须同步引入 config.yml port 注入 + 存量迁移，重构面大。守卫方案以最小改动（config.py 两处 +1 加条件 + compose 注入确定性身份信号）达到**同等根因修复**（容器不再误 +1）+ **保留宿主 debug 一键切换**（机制不变）。纯粹性的收益不足以抵消重构成本——这是"够好的修复"对"理想架构"的务实取舍。
- **`is_container_environment()` 是正确的判别点**：容器内外端口差异的根源正是"是否在容器内"。三重检测（env + cgroup + dockerenv）覆盖主流部署，compose 显式注入 `DOCKER_CONTAINER=true` 提供确定性信号（不依赖隐式 `/.dockerenv`）。应用层据此选行为，符合"应用感知部署上下文而非硬编码基础设施细节"。
- **+1 规则保留的合理性**：`+1` 编码的是"宿主经 Docker 映射端口访问 test 实例"这个真实约定（Master 内部 3306 / Test 宿主映射 13306，首位 +1）。它是 Docker 端口映射 + 双实例命名约定的派生，对宿主客户端成立。加守卫后只在正确的场景生效，不再是 bug 源。
- **debug 切换的方便性保留**：用户核心诉求是"方便切换 test/生产库"。守卫方案下切换机制完全不变（config.yml debug 布尔一键），可预测性不变。
- **删除测试**：守卫后，容器内服务 `is_container=True` 跳过 +1 → 读注入的 3306 正确连通；宿主 `is_container=False` + DEBUGMODE → +1 → 13306 正确连通。根因从结构上消失。
- **远程 DB 零暴露是分层必然**：远程属于 API 之上，按 ADR-002 不该碰 CRUD/DB 层。暴露 6 类 DB 端口到公网是安全灾难，且 api-server 单端口已能覆盖所有远程操作。

## Consequences

- **config.py:568-587** 改：`CLICKPORT`/`MYSQLPORT` 的 +1 条件加 `not is_container_environment()` 守卫（惰性 import）。
- **docker-compose.yml** 改：`worker-env` anchor 注入 `DOCKER_CONTAINER: "true"`，确定性触发容器身份检测，覆盖所有 `<<: *worker-common` 的 ginkgo 服务（tasktimer/livecore/execution-node/notify-worker/data-worker/backtest-worker）。
- **config_cli.update_env_for_debug** **不变**：容器侧仍切 `.env` HOST（mysql-master↔mysql-test），宿主侧靠 config.yml debug 布尔 + 守卫 +1。
- **set_debug / generate_config_file** **不变**：宿主 config.yml 结构无改动（仍无 mysql 节，port 靠默认 + 守卫 +1 派生）。
- **supersede ADR-004 端口约定部分**：ADR-004 的双实例概念（Master/Test）保留，"+1 端口派生"约定**收窄为仅宿主客户端**（加容器守卫），不再是无差别规则。ADR-004 顶部标注 `部分 supersede by ADR-024`。
- **DEBUGMODE 不变之处**：ADR-013（@retry 退避）、日志标注、宿主 +1 触发仍用 DEBUGMODE，本 ADR 不动这些。
- **关联 memory 更新**：`arch_database_debug_mode`（+1 加容器守卫）、`project_schedule_data_update_broken`（根因实施修复指向本 ADR）。
- **未决（与本 ADR 正交）**：CLI 双模（Decision 5）的实施、api-server REST 端点对 CLI 命令的覆盖率——另立 ADR-025 + 工程，不阻塞本 ADR 的 config 止血。
- **未来增量（非本 ADR 强制）**：若后续 config.yml 引入显式 mysql 节（port 字段），可进一步完全删 +1（config.py 零端口知识），本 ADR 的守卫是通往该终态的增量第一步。

## 判定标准自检

- ① **难逆转**：`config.py` 核心端口逻辑 + 容器身份检测引入 + ADR-004 端口约定收窄——中高。
- ② **反直觉**：+1 魔法"一份 .env 通吃"看似巧妙，加守卫而非删它也反直觉（"为什么不彻底删"）；根因极隐蔽（容器内服务静默失败 8.5 个月才定位）——满足。
- ③ **真实权衡**：完全删 +1（最纯，但 config.yml 重构 + 迁移代价大）vs +1 加守卫（务实，最小改动同等修复 + 保留切换）——有删除测试与代价对比支撑——满足。
