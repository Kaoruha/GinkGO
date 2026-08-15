# ADR-046: 回测任务生命周期状态机形式化（迁移表 + 所有权 + 崩溃窗口 + 幂等）

**Status:** Accepted（设计定案，分阶段实现）
**Date:** 2026-08-15
**关联:** ADR-018（回测派发契约）· ADR-016（回测标识符边界）· #5562（MySQL 清理单事务）· #6846（cleanup_orphan_tasks reaper）· #6483（completed 硬编码）· #6543（StopAssignment no-op 委托 CancelAssignment）

## Context

回测任务生命周期（`MBacktestTask.status`）经多轮补丁演化出 6 状态：`created / pending / running / completed / failed / stopped`。锚点 2026-08-15 实测，现状有四个结构性缺陷：

1. **状态机约束散落**：`update_status`（backtest_task_service.py:312）只校验目标状态字符串合法（6 选 1），不校验来源状态。真正的迁移约束以局部变量形式散落在各调用点——`startable_states`(:742)、`stoppable_states`(:1007)、`cancelable_states`(:1066)、node.py 认领去重(:350-386)。新增调用点必须自己记得抄守卫，漏抄即非法迁移静默成功。
2. **双写方无仲裁**：API 与 Worker 都可写 `stopped/failed`，last-write-wins。stop_task 对 running 任务**乐观**置 stopped（不等 worker 确认，:1036），worker 随后的 completed/failed 写入会覆盖 stopped（或反之），终态取决于写库时序。
3. **所有权模型只覆盖 running**：Redis 心跳持有集只在 running 期登记 owner。pending 期（API 已过守卫+已清理+已置状态，但 Kafka 消息可能未发出/未被认领）无任何 owner 记录。
4. **已知卡死缺口（用户叫停补丁的直接诱因）**：API 崩溃在「置 pending 后、发 Kafka 前」→ 任务永久卡 pending：start_task 拒绝 pending 重入（重入=双清理+双派发，守卫是对的）、reaper 只扫 `get_running_tasks()`（#6846）救不了 pending、node.py 的认领逻辑依赖消息存在所以也救不了。每个补丁堵一个洞、暴露下一个洞。

补丁史印证：pending 拒绝（堵双派发）→ 暴露 W2 卡死；reaper（堵 worker 死）→ 只扫 running。逐洞打补丁不可收敛，需整体形式化。

## Decision

### D1 · 状态机形式化：单一迁移表 + 条件更新（CAS）

状态机以**声明式迁移表**为唯一真值，收敛进 `BacktestTaskService`：

| # | 从 | 到 | 触发者 | 动作（与迁移同边界或明确标注非原子） |
|---|---|---|---|---|
| T1 | ∅ | created | API | create（初始态） |
| T2 | created/completed/stopped/failed | pending | API start_task | 前置守卫→CH/MySQL 清理→摘要归零→**CAS 置 pending**→绩效归零→发 Kafka |
| T3 | pending | running | Worker 认领 | 原子：CAS 置 running + 注册心跳 |
| T4 | running | completed | Worker | 引擎正常结束 |
| T5 | running | failed | Worker | 执行异常 |
| T6 | running | stopped | Worker | 响应 StopAssignment（graceful-stop） |
| T7 | created/pending | stopped | API cancel_task | 发 CancelAssignment + CAS 置 stopped |
| T8 | running | failed | API reaper | 心跳持有集判 owner 失联（#6846 既有） |
| T9 | pending | failed | API reaper（**新增**） | 派发记录超 TTL 且无认领（D2，堵 W2） |

**迁移表之外一律非法**。`update_status` 升级为条件更新：`UPDATE ... SET status=:new WHERE uuid=:u AND status IN (:expected_from)`，影响行数=0 即迁移被拒（响亮报错，返回 ServiceResult.error 携带当前实际状态）。散落的 `startable/stoppable/cancelable_states` 局部变量全部退役，由迁移表派生。

**pending→created 认领重置退役**：node.py:374「pending/running 但本机没在跑 → reset to created」是 W2/W5 缺口的临时自愈，与 T9 reaper 职责重叠且绕过迁移表（pending→created 不在表内）。Phase 3 移除，由 D2/D3 机制接管。

**权限矩阵**（谁能写哪个迁移）：API 限 T1/T2/T7/T8/T9；Worker 限 T3/T4/T5/T6。实现上按调用方传 `actor`（"api"/"worker"）查表校验，防御双写方越权。

### D2 · 所有权模型：心跳持有集推广到全生命周期

所有权分两段，登记载体统一 Redis：

- **pending 段（owner = dispatcher）**：start_task 在 CAS 置 pending 的同时写派发记录 `backtest:dispatch:{task_id} = {dispatched_at, api_instance, trace_id}`，TTL = 派发超时（建议 120s，> Kafka 消费端最大启动延迟）。
- **running 段（owner = worker）**：既有心跳持有集不变（TTL 30s / 10s 续约）。T3 认领成功即接管：写心跳 + 删派发记录。

**reaper 扩为两类扫描**：
- running 孤儿（既有 T8）：心跳集判失联 → failed。
- pending 陈旧（新增 T9）：派发记录存在且 `now - dispatched_at > TTL` 仍无认领 → CAS failed，error_message="dispatch lost: no worker claimed within TTL"。

**T9 判 failed 而非自动重派**：无法区分「Kafka 从未发出」与「发出后消费端全灭」，自动重派在后者会造成双跑。failed 诚实可见，用户重新 start 即可（此时清理幂等性保证重跑安全，见 D4）。Redis 不可达时 reaper skip（既有防误杀纪律不变）。

### D3 · 崩溃窗口枚举表（每步间隙的恢复路径）

start_task 时序：守卫 → CH 清理 → MySQL 清理(事务) → CAS 置 pending+派发记录 → 绩效归零 → 发 Kafka → worker 认领。

| 窗口 | 崩溃点 | 残留状态 | 恢复路径 |
|---|---|---|---|
| W1 | 清理后、置 pending 前 | 旧数据已删，状态仍为旧终态 | 无害：状态仍 startable，重跑再清理（清理幂等，D4） |
| W2 | 置 pending 后、发 Kafka 前 | 永久 pending（**现状卡死缺口**） | T9 reaper → failed → 可重新 start |
| W3 | 发 Kafka 后、worker 认领前 | pending + 消息在途 | 正常：worker 认领走 T3；若消费端全灭，TTL 后 T9 兜底 |
| W4 | Kafka at-least-once 重投 | 两 worker 先后收到同一 assignment | T3 CAS 只有一个成功，败者跳过（替代现状「终态跳过」去重） |
| W5 | worker 认领后、首 stage 写库前 | 心跳已注册但状态仍 pending | 无害：心跳存在 → reaper 不误杀；worker 继续，T3 迟早执行 |
| W6 | worker 运行中崩溃 | running + 心跳过期 | T8 reaper → failed（既有） |
| W7 | worker 终态写库前崩溃（计算已完成） | running + 心跳过期 | T8 → failed（结果丢失，诚实） |
| W8 | stop_task 置 stopped 后、worker 仍在跑 | stopped + worker 欲写 completed/failed | **终态冻结**：T4/T5/T6 的 CAS `expected_from=[running]` 失败 → worker 丢弃结果仅记日志。stopped 不被覆盖 |

W8 是双写方仲裁的裁决规则：先到者赢，后到者丢弃并留痕。现状 last-write-wins 下终态取决于时序运气，裁决后语义确定。

### D4 · 幂等性约定

- **清理幂等**：按 task_id 的 CH DELETE 与 MySQL 事务清理重复执行结果一致（删 0 行也是成功）。这是 T9 判 failed 后允许重新 start 的前提。
- **派发 at-least-once 可接受**：因 T3 认领是 CAS，重复消息天然去重，不需要 exactly-once。
- **reaper 幂等**：T8/T9 的 CAS `expected_from` 保证重复扫描不双重迁移。
- **绩效归零/摘要重置幂等**：写定值（0/None），重复写无副作用。

### D5 · 实现边界

- CAS 落在 `update_status` 单点（MySQL 单条 UPDATE 自带原子性；不改 BaseCRUD——在 service 层经既有 `modify` 通道传条件或加专用方法，遵守 ADR-040 后的 interface 纪律）。
- 迁移表为 service 层模块级常量 `TASK_TRANSITIONS`，reaper/stop/cancel/start/worker 各调用点共享。
- 派发记录 key 纳入既有 Redis 命名空间，不引入新存储。

## Rationale

- **为何收敛成迁移表而非继续局部守卫**：守卫知识放错层——状态机的合法迁移是领域规则，却由 5+ 个调用点各自记忆。每新增一个写状态的地方（如未来 CLI stop、reaper 扩展）都要重新发明守卫，漏发明即非法迁移。表驱动后单源派生，非法迁移在 CAS 处统一响亮失败。
- **为何 T9 选 failed 而非自动重派/回滚 created**：自动重派在「消息已发出但消费端慢」场景会双跑（两 worker 各拿到一份）；回滚 created 掩盖了「清理已执行」的事实且 created 语义是「从未派发」。failed + error_message 是唯一既诚实又保留重跑自由的终态。
- **为何终态冻结而非 worker 优先**：stop 是用户显式意图，且 stop_task 的乐观置位已是既有行为（#6543 review 后的委托链）。让用户意图输给迟到的结果写库，比反过来更反直觉。
- **为何不引入 outbox/事务消息**：W2 窗口的教科书解法是 transactional outbox（pending 与 Kafka 消息同库同事务）。但 Kafka 发送在 service 层、MySQL 事务边界在清理段，引入 outbox 表 + relay 是新基建；T9 reaper 以一条 Redis TTL 记录 + 一次扫描达到同等恢复能力（代价：卡死窗口延长至 TTL 而非即时），与既有 #6846 reaper 机制同构，维护面小。自用系统（见 memory：自用优先功能）不值得为此上 outbox。
- **为何 actor 校验做在查表层而非网络层**：Worker 调用的是同一个 service 方法（progress_tracker → task_service.update_status），没有可信的网络身份可验；`actor` 参数是约定级防线，防的是**误用**（新调用点抄错迁移），非恶意。

## Consequences

正面：
- W2 永久卡 pending 缺口关闭（T9）；W4/W8 双写方竞争有确定裁决（CAS + 终态冻结）。
- 状态机可审计：一条 SQL 能验证线上无表外迁移（扫描 status 变更日志比对 TASK_TRANSITIONS）。
- node.py 的 pending-reset 特例退役，worker 认领逻辑简化为「CAS + 心跳注册」。

负面/代价：
- 卡死窗口从「即时」变为「最多 TTL（120s）」——用户在 TTL 内看到的是 pending 而非 failed，可接受。
- `update_status` 签名变更（加 expected_from/actor），全调用点需适配，是一次破坏性收口。
- Worker 丢弃 W8 迟到结果意味着计算白跑——诚实但浪费；graceful-stop（StopAssignment A1）真正实现后此窗口收窄。

分阶段落地：
- **Phase 1**：TASK_TRANSITIONS 表 + CAS update_status，吸收散落守卫（startable/stoppable/cancelable 派生化）。
- **Phase 2**：派发记录 + T9 reaper（关 W2）。
- **Phase 3**：T3 认领 CAS + 终态冻结 + node.py reset 退役（关 W4/W5/W8）。

各 Phase 独立可交付、独立可回滚；Phase 1 不依赖 Phase 2/3 即消除非法迁移类 bug。
