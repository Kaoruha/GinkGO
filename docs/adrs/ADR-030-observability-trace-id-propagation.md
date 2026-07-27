# ADR-030: 全链路 trace_id 传播契约（contextvars + DTO 字段 + Kafka header）

**Status:** Accepted
**Date:** 2026-07-26
**关联:** 固化可观测层 tracer bullet 系列 #6784（API 入口）/ #6786（Backtest 跨进程）/ #6787（Paper/Live worker）/ #6785（error_stats 端点）；建立在 [ADR-009](ADR-009-global-service-hub.md)（GLOG 全局实例）之上。关联 memory `arch_api_src_dual_logging_trace_id`、`arch_base_engine_start_generate_task_id_overwrites_trace_id`、`arch_global_error_handler_trace_id`、`arch_get_error_stats_two_semantics`。

## Context

Ginkgo 的可观测层此前只有"错误响应信封带 trace_id"这一个孤岛接缝：`api/middleware/error_handler.py` 生成 trace_id 并写进错误信封，但**该 trace_id 与日志层完全断开**——`/tmp/ginkgo-api.log` 里同一请求的日志行无法按 trace_id 聚合，跨进程（Backtest/Paper/Live worker 经 Kafka）更是断链。

可观测层接入 tracer bullet（#6784-#6787，4 片）把 trace_id 接到了全链路，但契约散落在多个文件、且存在两个不看背景会觉得是 bug 的反直觉点：

1. **进程内 trace_id 的真相源是 `contextvars.ContextVar`**（`_trace_id_ctx`），不是 thread-local，也不是请求对象属性——FastAPI async 下 thread-local 在 task 切换时丢失。
2. **`BaseEngine.start` 用 `task_id` 覆盖 trace_id**（`src/ginkgo/trading/engines/base_engine.py:132` `GLOG.set_trace_id(self._task_id)`）——engine 跑起来后日志里不再是请求的 trace_id，而是 task_id。这是有意设计，但跨 engine 接力时若调用方未先 `set_task_id` 保留上游 trace_id，会被静默覆盖（`arch_base_engine_start_generate_task_id_overwrites_trace_id`）。
3. **trace_id 既是 DTO 字段又是 Kafka header，两层正交不互斥**：`PriceUpdateDTO`/`ControlCommandDTO` 带 `trace_id` 字段是**数据模型层的全局设计**（数据对 trace_id 透明，DTO 流到哪 trace_id 到哪，与进程边界无关）；任务派发/部署等**非 DTO 消息流**过 Kafka 边界时，trace_id 走 **Kafka message header** 作传输载体。两者不是"跨进程机制二选一"，而是数据模型层与传输层各管各的——看背景会觉得"既在 DTO 又在 header 是冗余"，实则是两层分工。

没有 ADR 锚定，后续 agent 极易把"contextvars 覆盖""engine 用 task_id 当 trace_id""DTO 带 trace_id 字段"当 bug 修掉。判定三条全中（难逆转 / 反直觉 / 真实取舍），立本 ADR。

> **实现时序注记**：本 ADR 起草时（相对 master 的 merge-base `debda14b`）api 层 `TraceIdFilter` 与 `error_handler._trace_id` 三级优先级尚未落地，早期版本按"待办/缺口"描述；[#6797](https://github.com/Kaoruha/GinkGO/pull/6797)（`9a89cfeb`，*API 请求 trace_id 全量注入贯穿 GLOG 日志*）随后在 master 实现了这两处接线。本 ADR 现按 master 现状（#6797 已合）描述，不再留"待办"措辞——否则后续 agent 会去"补齐"已存在的东西（#4652 类归因陷阱）。

## Decision

### 1. 进程内单一真相源：`_trace_id_ctx` contextvars

`src/ginkgo/libs/core/logger.py:22` 的 `_trace_id_ctx: ContextVar[Optional[str]]` 是进程内 trace_id 的**唯一真相源**。`GLOG` 暴露三件套管理它：

- `set_trace_id(trace_id) -> Token`：设置，返回令牌（T030）
- `clear_trace_id(token)`：经 token 恢复（T032），**禁止裸 `set(None)` 覆盖**（会丢嵌套上下文）
- `with_trace_id(trace_id)`：contextmanager，`set` + `finally reset`（T033）——请求级注入的首选

**src 层已实现**：`ecs_processor` / `ginkgo_processor`（structlog，`logger.py:152/208`）读 `_trace_id_ctx` 输出 `trace.id`，故 src 层 service/crud/engine 日志可按 trace_id 聚合。

**api 层标准 logging 已同源接线（#6797）**：`api/core/logging.py` 走独立 `logging` logger，但经 `TraceIdFilter`（`logging.Filter` 子类，`filter()` 内读 `GLOG.get_trace_id()` → `_trace_id_ctx` 注入 `record.trace_id`）桥接——`setup_logging` 中 `logger.addFilter(TraceIdFilter())` 挂载，`RichHandler` 格式串 `[trace_id=%(trace_id)s] %(message)s`、`JsonFormatter` 格式串含 `%(trace_id)s`。故 api 层 router/middleware（`from core.logging import logger`）日志亦带 trace_id，与 src 层共享同一 `_trace_id_ctx`——一个 trace_id 即可 grep 出一个请求的跨层（api + src）全链路日志。关联 memory `arch_api_src_dual_logging_trace_id`。

### 2. API 入口契约（#6784）

`TraceIdMiddleware`（`api/middleware/trace_id.py`）是 trace_id 的进程入口，对**每个请求**（不采样）执行：

1. `trace_id = request.headers.get("X-Trace-Id") or _new_trace_id()`——**透传客户端 trace_id 优先**，否则生成（uuid4 hex 前 16 位，与 error_handler 格式一致）。
2. `request.state.trace_id = trace_id`——跨中间件 unwind 的兜底载体，**error_handler 已读（#6797）**。`with_trace_id` 的 with 块退出会 reset contextvar；内层中间件（如 JWTAuthMiddleware 401）抛 `HTTPException` 时 `call_next` re-raise，异常逃逸到 `ServerErrorMiddleware`，此时 contextvar 已 reset。`error_handler._trace_id(request)` 三级优先级 `request.state.trace_id`（优先级 1）→ `GLOG.get_trace_id()`（contextvar）→ `uuid.uuid4().hex[:16]`（兜底）；`global_error_handler` 还在 `with_trace_id(trace_id)` 块内复位 contextvar——错误日志、`X-Trace-Id` 响应头、body trace_id 三者与请求同源。
3. `with GLOG.with_trace_id(trace_id): await call_next(request)`——sync contextmanager 包 await，保证 contextvars 在同 task 贯穿该请求所有后续 await（service/crud 同 task 读到），请求结束 finally 自动 reset 不泄漏。
4. `response.headers["X-Trace-Id"] = trace_id`——所有响应（正常 + 错误）回写，便于客户端关联。

### 3. 跨进程传播：数据模型层（DTO 字段）与传输层（Kafka header）正交

trace_id 跨进程传播由**两层正交设计**共同覆盖，不是"DTO 字段 vs headers"二选一：

**3a. 数据模型层（全局）：DTO 携带 `trace_id` 字段**——`PriceUpdateDTO`（`src/ginkgo/interfaces/dtos/price_update_dto.py:40`）、`ControlCommandDTO`（`src/ginkgo/interfaces/dtos/control_command_dto.py:53`）各带 `trace_id: Optional[str]`。这是**全局数据模型约定**：数据对 trace_id 透明，DTO 流到哪里 trace_id 跟到哪里，**与是否跨进程无关**。注入点 `src/ginkgo/livecore/data_manager.py:550` 从 `GLOG.get_trace_id()` 取 ctx 写字段（DTO 字段写入同函数 :564）；消费点 `src/ginkgo/workers/execution_node/node.py:860`（PriceUpdateDTO payload）与 `src/ginkgo/workers/execution_node/portfolio_processor.py:502`（ControlCommandDTO）读字段后 `GLOG.set_trace_id` 恢复。DTO 流过 Kafka 时 trace_id 随 payload 自然过界——全局字段的副作用，**非为跨进程单独选的机制**。

**3b. 传输层（跨进程载体）：Kafka message header**——任务派发/部署等**消息体非 DTO 的流**过 Kafka 边界时，trace_id 经 header 传播。写入 `src/ginkgo/data/services/backtest_task_service.py:845`（#6786 回测任务派发）、`src/ginkgo/trading/services/deployment_service.py:319`（#6787 paper/live 部署）；读取 `src/ginkgo/workers/backtest_worker/node.py:225`（#6786）、`src/ginkgo/workers/paper_trading_worker.py:1166`（#6787，注释明示"复用 #6786 header 传播模式"）。

### 4. Engine 接力：`task_id` 作为 trace_id（有意覆盖）

`BaseEngine.start`（`src/ginkgo/trading/engines/base_engine.py:132`）执行 `self._trace_id_token = GLOG.set_trace_id(self._task_id)`，`stop` 时 `clear_trace_id` 回收。**engine 生命周期内，trace_id == task_id**，让一次回测/实盘的全部引擎日志按 task_id 聚合——这是比"请求 trace_id"更稳定的聚合维度（engine 跨多个请求/消息）。

**隐式依赖（接力坑）**：跨 engine 接力时，上游须在调 `start` **之前**先 `set_task_id` 把上游 trace_id 传给下游 engine，否则 `start` 用下游自己的 task_id 覆盖，断链。动 engine 启动顺序 / LIVE 链路 trace_id 前，必读此约束（`arch_base_engine_start_generate_task_id_overwrites_trace_id`）。

### 5. 错误观测端点（#6785）

`GET /error-stats` 端点暴露 **GLOG 进程内错误热点统计**（`_error_patterns` 模式频次字典，`logger.py:519`），经 `SystemService.get_error_stats()`（`system_service.py:102` 透传 `GLOG.get_error_stats()`，分层 API→Service→GLOG）暴露，`_require_admin` 守卫；返回进程累计错误模式 top-N，某次错误的 trace_id/task_id 须回查（已带 trace_id 的）日志。注意 `get_error_stats` **同名异义**：GLOG 进程内版本（零外部依赖，**本端点所指**）vs `log_service` 版本（查 `MBacktestLog` 库、按 portfolio/时间窗口，**仅 CLI** `logging_cli.py:305` 调用，无 HTTP 端点）——本 ADR 指前者（`arch_get_error_stats_two_semantics`）。

## Rationale

- **为何 contextvars 而非 thread-local**：FastAPI 全 async，一个请求的 handler → service → crud 跨多个 await，同 task 但可能切线程（anyio threadpool）。thread-local 在 `to_thread` 跨越时丢失；`contextvars` 由 asyncio task 自动传播，且 `with_trace_id` 的 token/reset 保证嵌套作用域不互相污染。备选 thread-local 的取舍：简单但 async 下静默断链，不可接受。
- **为何 DTO 字段与 Kafka header 是两层正交而非二选一**：DTO `trace_id` 字段属**数据模型层**——让数据本身携带追踪上下文，DTO 无论进程内传递还是跨 Kafka 序列化都自带 trace_id，是与进程边界无关的全局约定。Kafka header 属**传输层**——为任务派发/部署这类**消息体非 DTO** 的流提供过界载体。两层正交：DTO 流无需额外 header（payload 自带），非 DTO 流靠 header。若误把"DTO 字段 vs headers"当跨进程二选一的取舍，会要么给 DTO 流多此一举加 header、要么给非 DTO 流漏掉 trace_id。
- **为何 engine 用 task_id 覆盖请求 trace_id**：engine 是秒~小时级长生命周期（一次回测、一轮实盘），期间消费成百上千条消息，每条带不同上游 trace_id。若 engine 内日志跟随每条消息的 trace_id 切换，同一 engine 的日志会被打散到无数 trace_id，无法按"这次回测"聚合。用 task_id 作稳定锚，engine 内全部日志可一次 `grep task_id` 取全。代价是 engine 入口处的请求 trace_id 被覆盖——由 Decision 4 的 `set_task_id` 先调约束兜底。
- **为何 `request.state.trace_id` 兜底而非依赖 contextvar 贯穿 error_handler**（**#6797 已落地**）：`ServerErrorMiddleware` 与 `TraceIdMiddleware` 的 `with_trace_id` 作用域是**错开的**——error_handler 在 with 块退出后才触发，此时 contextvar 已 reset。若强求 contextvar 贯穿，得把 error_handler 也塞进 with 块，破坏中间件分层。`request.state` 随 scope 存活、跨中间件 unwind 不丢，是最低成本的 trace_id 取回载体。`error_handler._trace_id(request)` 以 `request.state.trace_id` 为优先级 1，配合 `global_error_handler` 内 `with_trace_id` 复位 contextvar，使错误信封 / 响应头 / 日志三者同 trace_id。

## Consequences

- **所有日志层已同源读 `_trace_id_ctx`，禁止裸 `logging.getLogger`**：src 层经 `GLOG`（`ecs_processor` / `ginkgo_processor` 输出 `trace.id`），api 层经 `core.logging` 的 `TraceIdFilter`（#6797）。新增日志点 src 侧用 `GLOG`、api 侧 `from core.logging import logger`，均自动带 trace_id；裸 `logging.getLogger` 拿不到 trace_id，成为断点。
- **api 层 `TraceIdFilter` 已落地（#6797）**：`api/core/logging.py` 的 `TraceIdFilter`（`logging.Filter` 子类）读 `GLOG.get_trace_id()` 注入 record，`setup_logging` 经 `logger.addFilter(TraceIdFilter())` 挂载，`RichHandler` 格式 `[trace_id=%(trace_id)s]`、`JsonFormatter` 含 `%(trace_id)s`。改 api 日志格式须保留 `%(trace_id)s` 占位，否则 filter 注入被吞。
- **`error_handler` 已读请求 trace_id（#6797）**：`api/middleware/error_handler.py` 的 `_trace_id(request)` 三级优先级 `request.state.trace_id`（TraceIdMiddleware 注入，优先级 1）→ `GLOG.get_trace_id()`（contextvar）→ `uuid.uuid4().hex[:16]`（兜底）；`global_error_handler` 在 `with_trace_id(trace_id)` 块内复位 contextvar，错误日志 / `X-Trace-Id` 响应头 / body trace_id 三者同源。`request.state.trace_id` 随 scope 存活、跨中间件 unwind 不丢，是 error_handler 取回 trace_id 的主载体。
- **新增 DTO 按全局约定携带 `trace_id` 字段**（数据模型层，与跨进程无关）：生产侧注入、消费侧 `GLOG.set_trace_id` 恢复，否则 DTO 流下游断链。新增**非 DTO 跨进程消息流**则走 Kafka header 作传输载体——按消息性质选对层，勿混淆。
- **改 `BaseEngine.start` 启动顺序前必读 Decision 4**：`set_task_id` 须先于 `start` 调用以保留上游 trace_id；动 LIVE 链路 trace_id 尤甚。
- **`clear_trace_id` 须用 token，禁止裸覆盖**：嵌套 `with_trace_id` 场景下裸 `set(None)` 会破坏外层作用域的 trace_id。
- **trace_id 格式固定为 uuid4 hex 前 16 位**（`_new_trace_id`），与 error_handler 信封格式一致——改格式须同步两处 + 客户端解析。
- **`get_error_stats` 双语义不改名**（`arch_get_error_stats_two_semantics`）：`/error-stats` 端点指 **GLOG 进程内版本**（`system_service.py:102` 透传 `GLOG.get_error_stats()`）；`log_service` 查 `MBacktestLog` 库版本**仅 CLI** `logging_cli.py:305` 用、无 HTTP 端点。两者并存，判端点数据源前必 grep 区分进程内（GLOG/内存）vs 持久层（service/查库）。

## 判定标准自检

- ① **难逆转**：trace_id 已贯穿 API→Kafka→worker→engine 全链路 + error_stats 端点，全系统可观测依赖此契约——高。
- ② **反直觉**：① engine 用 task_id 覆盖 trace_id；② async 下用 contextvars 而非 thread-local；③ **trace_id 既在 DTO 字段又在 Kafka header，看似冗余实为数据模型层与传输层正交、各管各的流**；④ 进程内 trace_id 单一真相源为 contextvars、api/src 双层经各自的 filter/processor 同源读它——满足。
- ③ **真实权衡**：contextvars vs thread-local、DTO 字段（数据模型层）与 Kafka header（传输层）的正交分工、engine task_id 覆盖 vs 保留请求 trace_id——每条都有备选且做了取舍——满足。
