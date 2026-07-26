# ADR-029: 全链路 trace_id 传播契约（contextvars + DTO 字段注入）

**Status:** Accepted
**Date:** 2026-07-26
**关联:** 固化可观测层 tracer bullet 系列 #6784（API 入口）/ #6786（Backtest 跨进程）/ #6787（Paper/Live worker）/ #6785（error_stats 端点）；建立在 [ADR-009](ADR-009-global-service-hub.md)（GLOG 全局实例）之上。关联 memory `arch_api_src_dual_logging_trace_id`、`arch_base_engine_start_generate_task_id_overwrites_trace_id`、`arch_global_error_handler_trace_id`、`arch_get_error_stats_two_semantics`。

## Context

Ginkgo 的可观测层此前只有"错误响应信封带 trace_id"这一个孤岛接缝：`api/middleware/error_handler.py` 生成 trace_id 并写进错误信封，但**该 trace_id 与日志层完全断开**——`/tmp/ginkgo-api.log` 里同一请求的日志行无法按 trace_id 聚合，跨进程（Backtest/Paper/Live worker 经 Kafka）更是断链。

可观测层接入 tracer bullet（#6784-#6787，4 片）把 trace_id 接到了全链路，但契约散落在多个文件、且存在两个不看背景会觉得是 bug 的反直觉点：

1. **进程内 trace_id 的真相源是 `contextvars.ContextVar`**（`_trace_id_ctx`），不是 thread-local，也不是请求对象属性——FastAPI async 下 thread-local 在 task 切换时丢失。
2. **`BaseEngine.start` 用 `task_id` 覆盖 trace_id**（`base_engine.py:132` `GLOG.set_trace_id(self._task_id)`）——engine 跑起来后日志里不再是请求的 trace_id，而是 task_id。这是有意设计，但跨 engine 接力时若调用方未先 `set_task_id` 保留上游 trace_id，会被静默覆盖（`arch_base_engine_start_generate_task_id_overwrites_trace_id`）。
3. **跨进程 trace_id 走 DTO 的 pydantic 字段**（`PriceUpdateDTO.trace_id` / `ControlCommandDTO.trace_id`），而非 Kafka headers——显式契约可校验，但新消息类型漏带该字段就断链。

没有 ADR 锚定，后续 agent 极易把"contextvars 覆盖""engine 用 task_id 当 trace_id""DTO 带 trace_id 字段"当 bug 修掉。判定三条全中（难逆转 / 反直觉 / 真实取舍），立本 ADR。

## Decision

### 1. 进程内单一真相源：`_trace_id_ctx` contextvars

`src/ginkgo/libs/core/logger.py:22` 的 `_trace_id_ctx: ContextVar[Optional[str]]` 是进程内 trace_id 的**唯一真相源**。`GLOG` 暴露三件套管理它：

- `set_trace_id(trace_id) -> Token`：设置，返回令牌（T030）
- `clear_trace_id(token)`：经 token 恢复（T032），**禁止裸 `set(None)` 覆盖**（会丢嵌套上下文）
- `with_trace_id(trace_id)`：contextmanager，`set` + `finally reset`（T033）——请求级注入的首选

**src 层已实现**：`ecs_processor` / `ginkgo_processor`（structlog，`logger.py:152/208`）读 `_trace_id_ctx` 输出 `trace.id`，故 src 层 service/crud/engine 日志可按 trace_id 聚合。

**api 层标准 logging 尚未接线（已知缺口）**：`api/core/logging.py` 走独立 `logging` logger（`RichHandler` / `JsonFormatter`），格式串 `'%(asctime)s %(name)s %(levelname)s %(message)s'` **不含 trace_id 字段**、无 filter 读 `_trace_id_ctx`，且显式"避免 GLOG 的 API 不兼容问题"；api 层 router/middleware（20+ 文件 `from core.logging import logger`）的日志记录**不带 trace_id**。故"一个 trace_id grep 出跨层全链路"当前**仅对 src 层成立**；补齐 api 层需新增 `TraceIdFilter`（读 `_trace_id_ctx` 注入 record）并接入 `setup_logging`（见 Consequences 待办）。关联 memory `arch_api_src_dual_logging_trace_id`（"#6784 后经 `_trace_id_ctx` 桥接"）据此校正：桥接仅落 src 侧，api 侧未建。

### 2. API 入口契约（#6784）

`TraceIdMiddleware`（`api/middleware/trace_id.py`）是 trace_id 的进程入口，对**每个请求**（不采样）执行：

1. `trace_id = request.headers.get("X-Trace-Id") or _new_trace_id()`——**透传客户端 trace_id 优先**，否则生成（uuid4 hex 前 16 位，与 error_handler 格式一致）。
2. `request.state.trace_id = trace_id`——**设计上**作跨中间件 unwind 的兜底载体（**当前为待接线的死载体**）。`with_trace_id` 的 with 块退出会 reset contextvar；内层中间件（如 JWTAuthMiddleware 401）抛 `HTTPException` 时 `call_next` re-raise、响应头写入行被跳过。**注意**：`error_handler`（`api/middleware/error_handler.py`）当前**未读 `request.state.trace_id`**——错误信封的 `trace_id` 由 `_trace_id()`（`uuid.uuid4().hex[:16]`）重新生成（L35/L47），与请求 trace_id **断链**。故 `request.state.trace_id` 目前写了从不读，待 error_handler 改读它（或 `GLOG.get_trace_id()`）才名副其实（见 Consequences 待办）。
3. `with GLOG.with_trace_id(trace_id): await call_next(request)`——sync contextmanager 包 await，保证 contextvars 在同 task 贯穿该请求所有后续 await（service/crud 同 task 读到），请求结束 finally 自动 reset 不泄漏。
4. `response.headers["X-Trace-Id"] = trace_id`——所有响应（正常 + 错误）回写，便于客户端关联。

### 3. 跨进程契约：DTO 字段注入（#6786 / #6787）

跨进程 trace_id 经 **DTO 的 pydantic 字段**传播，不走 Kafka headers：

- **生产侧**：`PriceUpdateDTO` / `ControlCommandDTO` 各携带 `trace_id: Optional[str]` 字段。`livecore/data_manager.py:549` 等发布点从 `GLOG.get_trace_id()` 取当前 ctx 注入 DTO。
- **消费侧**：`workers/execution_node/node.py:857` 从反序列化的 event_data 取 `trace_id`，`GLOG.set_trace_id(trace_id)` 恢复到当前 worker task 的 contextvar。

覆盖 Backtest（Kafka 派发→worker 消费，#6786）与 Paper/Live worker（#6787）两条跨进程路径。

### 4. Engine 接力：`task_id` 作为 trace_id（有意覆盖）

`BaseEngine.start`（`base_engine.py:132`）执行 `self._trace_id_token = GLOG.set_trace_id(self._task_id)`，`stop` 时 `clear_trace_id` 回收。**engine 生命周期内，trace_id == task_id**，让一次回测/实盘的全部引擎日志按 task_id 聚合——这是比"请求 trace_id"更稳定的聚合维度（engine 跨多个请求/消息）。

**隐式依赖（接力坑）**：跨 engine 接力时，上游须在调 `start` **之前**先 `set_task_id` 把上游 trace_id 传给下游 engine，否则 `start` 用下游自己的 task_id 覆盖，断链。动 engine 启动顺序 / LIVE 链路 trace_id 前，必读此约束（`arch_base_engine_start_generate_task_id_overwrites_trace_id`）。

### 5. 错误观测端点（#6785）

`log_service` 聚合 `MBacktestLog`（MySQL）提供 `error_stats` 端点，按 trace_id / task_id 关联错误热点。注意 `get_error_stats` **同名异义**：GLOG 进程内版本（零外部依赖）vs `log_service` 版本（查 MBacktestLog 库，CLI 已用）——本 ADR 指后者（`arch_get_error_stats_two_semantics`）。

## Rationale

- **为何 contextvars 而非 thread-local**：FastAPI 全 async，一个请求的 handler → service → crud 跨多个 await，同 task 但可能切线程（anyio threadpool）。thread-local 在 `to_thread` 跨越时丢失；`contextvars` 由 asyncio task 自动传播，且 `with_trace_id` 的 token/reset 保证嵌套作用域不互相污染。备选 thread-local 的取舍：简单但 async 下静默断链，不可接受。
- **为何跨进程走 DTO 字段而非 Kafka headers**：DTO 是 pydantic 契约，`trace_id` 字段在序列化/反序列化两端显式可见、可 schema 校验、可单测；Kafka headers 是隐式 dict，新增消费者易漏读。代价是新 DTO 类型须显式加该字段——但 Ginkgo 跨进程消息类型有限（PriceUpdate / ControlCommand 为主），成本可控，换来强契约。
- **为何 engine 用 task_id 覆盖请求 trace_id**：engine 是秒~小时级长生命周期（一次回测、一轮实盘），期间消费成百上千条消息，每条带不同上游 trace_id。若 engine 内日志跟随每条消息的 trace_id 切换，同一 engine 的日志会被打散到无数 trace_id，无法按"这次回测"聚合。用 task_id 作稳定锚，engine 内全部日志可一次 `grep task_id` 取全。代价是 engine 入口处的请求 trace_id 被覆盖——由 Decision 4 的 `set_task_id` 先调约束兜底。
- **为何 `request.state.trace_id` 兜底而非依赖 contextvar 贯穿 error_handler**（**设计意图；当前未落地**）：`ServerErrorMiddleware` 与 `TraceIdMiddleware` 的 `with_trace_id` 作用域是**错开的**——error_handler 在 with 块退出后才触发，此时 contextvar 已 reset。若强求 contextvar 贯穿，得把 error_handler 也塞进 with 块，破坏中间件分层。`request.state` 随 scope 存活、跨中间件 unwind 不丢，是最低成本的 trace_id 取回载体——**但 error_handler 当前未实现此读取**（见 Decision 2 / Consequences 待办），故该兜底目前是设计预留而非已生效。

## Consequences

- **新增日志点须经 `GLOG`（src 层，自动带 trace_id），禁止裸 `logging.getLogger`**——否则该日志行拿不到 trace_id，成为断点。注意 api 层 `core.logging` 标准 logger **当前不带 trace_id**（见 Decision 1 缺口），其 trace_id 覆盖待 `TraceIdFilter` 落地。
- **【待办】api 层 `TraceIdFilter` 未实现**：补齐 `api/core/logging.py` 的 trace_id 注入（新增 `TraceIdFilter` 读 `_trace_id_ctx` 写入 record + `JsonFormatter` 格式串加 `trace_id` 字段 + `setup_logging` 挂 filter），使"双层日志同源"名副其实。落地前勿宣称 api 层日志可按 trace_id 聚合。
- **【待办】`error_handler` 未读请求 trace_id**：`api/middleware/error_handler.py` 的错误信封 `trace_id` 由 `_trace_id()` 重生成（L35/L47），与请求 trace_id 断链；`request.state.trace_id`（Decision 2.2 写入）当前是死载体。补齐：error_handler 改读 `getattr(request.state, "trace_id", None) or GLOG.get_trace_id() or _trace_id()`，使错误信封与请求/日志同 trace_id。
- **新增跨进程 DTO 必须携带 `trace_id` 字段**，且生产侧注入、消费侧恢复，否则下游断链。新增 DTO review 项。
- **改 `BaseEngine.start` 启动顺序前必读 Decision 4**：`set_task_id` 须先于 `start` 调用以保留上游 trace_id；动 LIVE 链路 trace_id 尤甚。
- **`clear_trace_id` 须用 token，禁止裸覆盖**：嵌套 `with_trace_id` 场景下裸 `set(None)` 会破坏外层作用域的 trace_id。
- **trace_id 格式固定为 uuid4 hex 前 16 位**（`_new_trace_id`），与 error_handler 信封格式一致——改格式须同步两处 + 客户端解析。
- **`get_error_stats` 双语义不改名**（`arch_get_error_stats_two_semantics`）：error_stats 端点指 `log_service` 查库版本；GLOG 进程内版本服务其他场景。两者并存。

## 判定标准自检

- ① **难逆转**：trace_id 已贯穿 API→Kafka→worker→engine 全链路 + error_stats 端点，全系统可观测依赖此契约——高。
- ② **反直觉**：① engine 用 task_id 覆盖 trace_id；② async 下用 contextvars 而非 thread-local；③ 跨进程走 DTO 字段而非 Kafka headers；④ 进程内 trace_id 单一真相源为 contextvars、设计上供 api/src 双层共享（api 层 `TraceIdFilter` 待落地，见 Decision 1 / Consequences）——满足。
- ③ **真实权衡**：contextvars vs thread-local、DTO 字段 vs headers、engine task_id 覆盖 vs 保留请求 trace_id——每条都有备选且做了取舍——满足。
