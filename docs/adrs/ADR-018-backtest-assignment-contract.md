# ADR-018: 回测派发契约（判别联合 + DTO 层 wire spec）

**Status:** Accepted
**Date:** 2026-06-28
**Related:** ADR-010（Entity/ORM/DTO 三层 + DTO=状态信使）、ADR-017（声明式类型契约 > 字符串分派）、#5646（派发前校验，部分缓解）；细化 ADR-009（不触 Base）；候选源自 `/improve-codebase-architecture` 评审 + `/grill-with-docs` 拷问

## Context

回测任务命令（assignment）跨 Kafka 边界（`BACKTEST_ASSIGNMENTS` topic），契约无 owner，真相散落 5 处，drift 静默发生且无法测。经 grep/Read 核实（搜索须覆盖 `src/`+`api/` 全仓——曾因只搜 `src/` 误判 `stop_task` 为死方法）：

- **生产端 3 处手搓 dict literal**，三命令同 topic、不同 shape：
  - `start_task`（`backtest_task_service.py:716-722`）：`{task_uuid, portfolio_uuid, name, command:"start", config:{...14 keys}}`
  - `stop_task`（`:768-771`）/ `cancel_task`（`:821-824`）：`{task_uuid, command}` 仅 2 键
  - 三处共用 `producer=GinkgoProducer(); .send(); .flush(2.0); .close()` 样板
- **消费端字符串分派**：`command = assignment.get("command","start")`（`node.py:224`）按字符串 if/elif，无类型守护"stop 不能带 config"。
- **stop 消费无 handler**（拷问发现）：`stop_task` 经 API `POST /{uuid}/stop`（`api/backtest.py:527`）真在调用、真发 Kafka `{command:"stop"}`，但 `node.py:227-230` 的 if/elif 只有 start/cancel——**stop 消息静默掉 void 后照常提交 offset**。这是活契约（端点+service+Kafka 全通）的消费侧缺口，非死代码。端点 docstring 还区分 stop="停 running 任务"、cancel="取消 created/pending 任务"，设计上是有意两回事，只是 stop 的 worker 动作没实现。
- **默认值双源**：生产端从 `config_snapshot` 恢复（`:698-703`），消费端全硬编码（`node.py:346-353`：`initial_cash=100000.0`/`commission_rate=0.0003`/`slippage_rate=0.0001`/`benchmark_return=0.0`/`max_position_ratio=0.3`/`stop_loss_ratio=0.05`/`take_profit_ratio=0.15`/`frequency="DAY"`/`analyzers=[]`）。两边对得上纯属巧合，非契约。
- **死字段**：生产端发 `broker_type/broker_attitude/commission_min`（`:699`），消费端 worker `BacktestConfig`（`models.py:48`）根本不读。
- **校验重复且错位**：service 层只 `portfolio_uuid or task.portfolio_id` coalesce（`:718`）不显式拒；消费端字面拒 `"portfolio_uuid is required"`（`:310`）、`"Missing dates"`（`:324`）。错误信息跨 Kafka 降级，根因在 service、暴露在 worker（#5646 部分缓解：API 层加 BusinessError 预校验，但重复仍在）。
- **孤儿 DTO**：`interfaces/dtos/backtest_assignment_dto.py` 定义 `BacktestAssignmentDTO`(dataclass)/`BacktestProgressDTO`，grep 零引用——边界处无人用，是第三份自漂移 shape（带 `priority/timeout` 真消息没有；`to_json()->str` 形态错，producer 收 dict）。且用 dataclass 偏离 DTO 层 pydantic 惯例（10:1）。

判定三条全中（难逆转 / 反直觉 / 真实取舍 A vs B vs C），立本 ADR。

## Decision

把回测派发契约深化为**判别联合（discriminated union）+ DTO 层 wire spec**，单一 owner 藏构造/校验/默认/序列化，两端只绑类型。

### DTO 层（`interfaces/dtos/backtest_assignment_dto.py`，复活孤儿，pydantic BaseModel）

- `BacktestAssignmentConfig`——wire spec，11 字段：
  - **required**：`start_date:str`、`end_date:str`
  - **optional**（带默认，唯一默认表）：`initial_cash:float=100000.0`、`commission_rate:float=0.0003`、`slippage_rate:float=0.0001`、`benchmark_return:float=0.0`、`max_position_ratio:float=0.3`、`stop_loss_ratio:float=0.05`、`take_profit_ratio:float=0.15`、`frequency:str="DAY"`、`analyzers:list[dict]=[]`
  - `analyzers` 透传 `list[dict]`（内部结构是 worker `AnalyzerConfig` 的事，DTO 不解析——ADR-010 信使/主体分离）；dates 为 `str`（worker `BacktestConfig.start_date/end_date` 同型，`to_payload` 无需日期序列化）
- `StartAssignment | StopAssignment | CancelAssignment`（pydantic BaseModel）：
  - 共享 `task_uuid:str`（三命令通用 required）
  - 各持 `command: ClassVar[str]`（`"start"`/`"stop"`/`"cancel"`）——类型标记**非实例字段**，不进 `model_dump()`
  - Start 独有 required：`portfolio_uuid:str`、`name:str`、`config:BacktestAssignmentConfig`
- `from_payload(dict) -> Start|Stop|Cancel`：按 `command` 分流返子类；pydantic 构造自动校验 required/类型；畸形（缺 task_uuid、未知 command、start 缺 portfolio_uuid/dates）raise `MalformedAssignmentError(ValueError)`。stop/cancel 的多余字段（如误带的 config）**忽略**——判别联合的守护在返回类型层面（`StopAssignment` 无 `config` 字段，消费端 match 拿到也无法误用），无需 `from_payload` 对 raw 多余字段逐项拒
- `to_payload() -> dict`：`model_dump()` + 显式注入 `"command": self.command`（对齐今天 wire 结构）；目标 **dict 非 json str**（`producer.send` 收 dict，订正孤儿 `to_json()->str` 双重编码风险）

### 生产端（data/services）

`start_task`/`stop_task`/`cancel_task` 三处手搓 dict literal → `StartAssignment(...).to_payload()` 等 → `producer.send`。死字段 `broker_type/broker_attitude/commission_min` 停发（不进 spec）。

### 消费端（workers）

- `node.py._handle_task_assignment`：`command` 字符串分派 → `cmd = from_payload(raw)` + `match cmd`：
  - `case StartAssignment():` `_start_task(cmd)`（传 cmd 非裸 dict）
  - `case StopAssignment():` `GLOG.WARN("stop handler 未实现")` + 不改任务状态 + 提交 offset（**A1**：stop 是活契约但消费侧 handler 缺失，显式记录而非静默掉 void；graceful-stop 单开 issue）
  - `case CancelAssignment():` `_cancel_task(cmd.task_uuid)`
- 畸形：`except MalformedAssignmentError as e:` `report_failed_by_uuid(error=str(e))` + `return`（保持今天"标记失败 + 提交 offset"语义，at-least-once）。**窄捕**：只接契约畸形，其他异常（真 bug）照常向上抛触发重投
- `_start_task` 删字面校验块（`:309-329`）+ 手搓 BacktestConfig（`:343-355`）+ 默认表（`:346-353`），改调 `assignment_to_backtest_config(cmd)`

### 映射层（`workers/backtest_worker/models.py`）

模块级 `assignment_to_backtest_config(cmd:StartAssignment) -> BacktestConfig`，含 analyzers `AnalyzerConfig(**d)` 转换（dict 字段不全 → try/except 转 `MalformedAssignmentError`，与消费端窄捕一致）。**DTO 不 import worker 类型**（信使不知主体，ADR-010）；worker import DTO（消费方向）。映射是第三者胶水，不挂信使也不挂状态主体。

## Considered Options

- **联合形态**：
  - A 扁平单类（`command:Literal[...]` 运行时字段）：否决——type 不阻 stop+config，config 须额外纪律保 typed 才不退化成裸 dict 套壳（默认漂移原样存活）。
  - **B 判别联合（本 ADR）**："哪个命令"是类型，构造期强制 stop 不能带 config。
  - C 信封 port（`BacktestCommand` port + Kafka adapter，藏传输）：否决——3 命令的 seam 嫌过重；今天 Kafka-only，传输不会变，port 是假设性 seam（删掉只回到 B，无增量集中）。

- **stop 处置**：A1 保留三元 + 消费端显式 WARN no-op（本 ADR）/ A2 stop 复用 cancel / C 现在实现 graceful handler。否决 A2（掩盖缺口）、C（新功能不塞 ADR）。

- **死字段**：A 不进 spec + 生产停发（本 ADR）/ B 进 spec 标 deprecated / C 进 spec 不标。否决 B/C（契约=双方真实交互最小集，死字段进 spec 是噪音）。

- **错误传播**：A raise `MalformedAssignmentError`（本 ADR）/ B return Optional / C 错误信封。否决 B（None 丢原因+吞 bug）、C（签名丑）。

- **映射位置**：A worker 侧独立函数 `assignment_to_backtest_config`（本 ADR）/ B DTO 方法 / C BacktestConfig classmethod。否决 B（DTO 反向依赖 worker，违 ADR-010）、C（主体职责膨胀）。

## Rationale

- **类型强制是消除 drift 的真杠杆**：stop+config、缺字段、未知 command 都在**构造期**报错，而非靠人记得同步五处。与 ADR-017 选"声明式类型契约 > 字符串分派"同根。
- **defaults 归一处**：DTO `BacktestAssignmentConfig` 持唯一默认表 → worker BacktestConfig 默认删除。"双源靠巧合对齐"彻底消失。
- **serde 目标是 dict 非 json str**：`producer.send(topic, assignment)` 收 dict（`:724`），孤儿 DTO 现行 `to_json()->str` 形态错。订正为 `to_payload()->dict`/`from_payload(dict)`。
- **DTO ↔ 内部模型映射是 feature 非累赘**：wire 契约与 worker 内部表示解耦，生产端改 wire 字段不影响 worker，反之亦然——ADR-010"DTO 不持不变量、状态主体持"的落点。
- **不复活孤儿 DTO 的 priority/timeout**：真消息从未带，是历史臆测字段，丢弃。`BacktestProgressDTO` 同样零引用（反向 worker→API 进度链路从未走 DTO），一并删。
- **不抽共享 config mixin / 不动 Base**：worker BacktestConfig 是内部模型、与 wire spec 角色不同，强行合并牵动 worker 内部（ProgressTracker 耦合）面更大；遵守 ADR-009 不触 Base。

## Consequences

- **删**：生产端 3 dict literal + 样板、消费端 `.get()` 默认表（`node.py:346-353`）、字面校验块（`:309-329` 上移到 DTO 构造期）、孤儿 DTO 旧实现（`BacktestAssignmentDTO` dataclass + `priority/timeout`）、`BacktestProgressDTO`（死代码）、死字段 `broker_type/broker_attitude/commission_min`（生产端停发）。
- **worker BacktestConfig 默认**：删（DTO 构造期已由唯一默认表填齐 9 字段）。
- **stop 消费缺口**：A1 显式 WARN no-op 记录；graceful-stop handler 单开 issue（不塞本 ADR）。
- **#5646 收敛**（迁移门⑤）：API 预校验走 DTO 构造（`StartAssignment(...)`/`from_payload`），`MalformedAssignmentError` 被 service 层 `try/except`（`:731-733`）转 `ServiceResult.error`。#5646 那套手写 BusinessError 字面预校验被 DTO 构造取代，校验更严（缺字段在构造期而非 service 字面 if）。
- **魔法数标注**：service 哨兵（`:712` `if initial_cash != 100000.0 ...`）与 DTO `initial_cash` 默认共享 `100000.0` 这个数，**改一处须同步**。
- **测试面（replace 不 layer）**：`tests/unit/interfaces/test_backtest_assignment_dto.py`——round-trip `to_payload(from_payload(d))==d`、9 默认值应用、`from_payload` 拒畸形（缺 task_uuid / 未知 command / stop 带 start-config / 缺 portfolio_uuid·dates）。消费端硬编码默认断言、字面校验断言删除。
- **迁移顺序**（单分支 `6447-refactor/backtest-assignment-contract`，单 PR 5 commit，TDD 每步先测试）：
  ① DTO 层 3 类 + config spec + from/to_payload + seam 测试（含本 ADR；不动调用方，纯新增零风险）
  ② 生产端 3 dict → `Assignment(...).to_payload()`，门：新旧 payload 字节级相等（除死字段）
  ③ 消费端 `.get()`+默认表 → `from_payload`+match+`assignment_to_backtest_config`，门：同 payload 构出同 BacktestConfig
  ④ 删死代码 + 验证死字段停发，门：grep 零命中死字段+旧 API
  ⑤ #5646 API 预校验收敛进 DTO 构造，门：缺字段任务在 service 层即 `ServiceResult.error`，不进 Kafka
- **风险**：全量测试 OOM（~20GB，见测试原则）——主门用 backtest 派发/消费路径分模块测，全量终验；`BacktestConfig` 映射须逐字段确认语义。
- **交叉引用**：ADR-010（DTO=状态信使、状态主体分离）、ADR-017（类型契约 > 字符串分派）、ADR-009（不触 Base）、ADR-002（DTO 在边界层，service→CRUD 层化不涉及）。

## 判定标准自检

- ① **难逆转**：契约 shape 承诺跨生产+消费+测试，回退需重散 5 处——满足。
- ② **反直觉**：未来见 `StartAssignment|StopAssignment|CancelAssignment` 三类 + `from_payload` + Stop 的 WARN no-op 会问"为何不是一个 dict / stop 为何不执行"——满足。
- ③ **真实权衡**：联合形态 A/B/C + stop 处置 + 死字段 + 错误传播 + 映射位置五轴均有真实备选——满足。
