# ADR-016: 回测标识符边界（task_id / engine_id / uuid）

**Status:** Accepted
**Date:** 2026-06-19

## Context

回测数据模型里**三个标识符**在记录与任务表上共存，语义长期漂移，最终在 baseline 管线静默断裂（#6174）：

| 标识符 | 来源 | 注释意图（docstring） |
|---|---|---|
| `uuid` | 实体主键 | 永久唯一 |
| `task_id` | `MBacktestRecordBase:42` / `MBacktestTask:52`（unique） | "执行会话ID"（动态，每次 run） |
| `engine_id` | `MBacktestRecordBase:41` / `MBacktestTask:54` | "引擎装配ID"（稳定，配置驱动） |

**实证（源组合 `bcc34af4` / 回测 `8b7b8cd8`）**：

1. **记录侧两列同值**：analyzer/signal 记录 `engine_id = task_id = 8b7b8cd8`（= 回测 uuid）。非偶然——回测写入端普遍 `engine_id=task_id`：
   - `backtest_orchestrator.py:123,169` `engine_id=task_id`
   - `workers/backtest_worker/task_processor.py:200,387` `engine_id=self.task.task_uuid`
2. **任务表 `engine_id` 系统性空**：47/50 completed 任务 `engine_id=''`；3 个非空值为旧格式 `engine_0`/`engine_f`（非 uuid）。`MBacktestTask` 创建默认 `""`（`backtest_task_crud.py:85`），`update_status(uuid, status, error_message, **result_fields)` 签名未暴露 engine_id 写入，完成路径从不回写。
3. **管线混用**：`slice_data_manager.py:61` `get_by_task_id(task_id=engine_id)` 显式把 `engine_id` 当 `task_id` 喂查询。它"能查到"**纯靠回测不变量 `engine_id==task_id` 的偶然**；signal/order 的 `find(filters={"engine_id":...})`（`:70,:77`）同理。
4. **断裂链**：`_generate_baseline_if_possible:871` 从 task 读空 `engine_id` → `evaluate_backtest_stability(engine_id='')` → `get_by_task_id(task_id='')` → analyzer 空 → `_validate_backtest_data:196` 判 `invalid_data` → `monitoring_baseline` 不产出 → worker `disabled`。

**设计意图与现实的关系**：`base_engine.py:26-27` 注释把 `engine_id`（稳定装配）/`task_id`（动态会话）定为**二维**。live/paper 路径接近此意图（`trade_gateway_adapter.py:192-193` 默认 `'live_engine'`/`'live_run'` 占位串，二者独立）。但**回测路径一次回测 = 一次装配 = 一次执行**，二维天然坍缩成一维——这不是实现 bug，是回测的固有形态。强行让回测维护"独立的稳定 engine_id"会引入不存在的装配生命周期。

## Decision

### 边界定义

| 标识符 | 语义 | 回测取值 | live/paper 取值 |
|---|---|---|---|
| **`task_id`** | 执行会话ID；**回测记录的主查询键** | `≡ MBacktestTask.uuid` | 每 session 新生成 |
| **`engine_id`** | 引擎装配ID；标识"哪套装配跑的" | `≡ task_id`（坍缩，非偶然） | 稳定装配 id（跨 session） |
| `uuid` | 实体主键 | task 表：`≡ task_id` | — |

### 三条铁律

1. **读回测记录一律按 `task_id`**（主键）。`engine_id` 仅用于"按装配聚合 / 跨 session 查询"，**禁止当 `task_id` 喂 `get_by_task_id`** 或作为单次回测数据的查询条件。
2. **回测完成必须写 `task.engine_id = task.uuid`**，维持 `engine_id ≡ task_id` 不变量。`MBacktestTask.engine_id` 是真实查询维度（`get_tasks_by_engine`、service `get`/list filter），不得留空。
3. **live/paper 路径 `engine_id` 与 `task_id` 独立**——本 ADR 不改变 live 语义，仅约束回测。当前 live 占位串 `'live_engine'`/`'live_run'` 的规整属后续独立工作。

### 查询实体分界（决定用哪个 id）

- 查 **`MEngine` / `MEnginePortfolioMapping`**（引擎装配实体）→ 用 `engine_id`（这些表的主键就是装配 id）。**正确用法，不在本 ADR 改动范围**。
- 查 **回测记录**（analyzer/signal/order/position/signal_tracker/transfer）→ 用 `task_id`。

## Rationale

- **"主查询键"必须唯一确定一次执行的数据**：一次回测产出的全部记录共享一个 `task_id`，用 `engine_id` 查在 live 下会跨 session 串数据。`task_id` 天然是 per-run 边界，故为记录主键。
- **回测坍缩是事实，强行展开二维是过度设计**：回测没有"同一装配多次运行"的生命周期（每次回测都重新 assemble），故 `engine_id` 在回测里没有独立于 `task_id` 的信息量。承认坍缩、维持不变量，比虚构装配 id 更诚实。
- **混用是 bug 不是兼容层**：`get_by_task_id(task_id=engine_id)` 依赖不变量才工作，是脆弱耦合。边界明确后应消除，而非保留"碰巧能跑"。
- **不抽共享 mixin / 不改 Base 类**（CLAUDE.md）：记录模型各自 `@update.register(str)` 重载补 `task_id` 形参即可，不触碰 `MBacktestRecordBase` 字段定义（字段本就两列都在）。

## Consequences

**正向**：baseline 管线（#6174）闭合；`get_tasks_by_engine` 等任务表 engine_id 消费者可用；记录查询语义一致。

**本次落地范围**（PR #6174）：
- W1 task 完成回写 `engine_id = task.uuid`（`progress_tracker._write_status_to_db` completed 分支，经 `update_status(**result_fields)` → CRUD `update_task_status` → `modify` 三层透传落库）
- R1 `slice_data_manager` 形参 `engine_id→task_id`、内部查询全走 `task_id`
- R2 `backtest_evaluator.evaluate_backtest_stability` 形参 `engine_id→task_id`
- R3 `portfolio_cli._generate_baseline_if_possible` 传 `task_id`（已读取 `task.task_id`，却误传可能为空的 `engine_id`，即 #6174 直接病灶）
- R4 `deviation_checker.get_baseline` 传 `task_id`（同 R3 模式）
- 附带：`evaluation_cli` 两处 `evaluate_backtest_stability` 调用（死代码块内，防 `return` 移除后 `TypeError`）

**W2 经实证撤销**：原计划"记录模型 `.update()` singledispatch 重载补 `task_id`"。实证发现：
1. 记录真实写入路径是 CRUD `_create_from_params`（`base_crud:340` 调用），已设 `task_id=kwargs.get("task_id","")`；
2. MAnalyzerRecord 等 `.update()` singledispatch（str 重载）全仓无调用方，为 vestigial 代码；
3. `_convert_input_item` 亦未被 base 调用。
故记录端一直正确，无需改动。改死代码会制造虚假完整性，违反 verify-before-implement。

**不在本次范围**（独立 follow-up）：
- live/paper 占位串 `'live_engine'`/`'live_run'` 规整
- live 路径 engine_id 稳定装配 id 的真实落地（需引擎装配注册表，属 ADR-003 引擎双模式后续）

**向后兼容**：历史数据 `MBacktestTask.engine_id` 多为空——W1 仅影响新完成回测；读点改 `task_id` 后，历史回测仍可查（`task_id` 一直正确填充）。无需数据迁移、无 schema 变更（字段已存在）。
