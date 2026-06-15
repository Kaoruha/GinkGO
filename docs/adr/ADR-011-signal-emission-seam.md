# ADR-011: 信号发射统一 Seam（Strategy + Risk）

**Status:** Accepted
**Date:** 2026-06-15（初稿 2026-06-14，落地前范围由 Strategy 扩至含 Risk）

## Context

`create_signal` 在代码库有**两份独立定义**，二者各自静默漂移：

- `BaseStrategy.create_signal`（strategy_base.py:33）—— 15 策略
- `RiskBase.create_signal`（risk_base.py:105）—— 8 Risk 类；RiskBase **不继承** BaseStrategy，是平行同名方法

两份都只填 portfolio/engine/task_id 后构造 Signal，三个跨切关注点漂移：

| 关注点 | Strategy 侧 | Risk 侧 |
|---|---|---|
| ClickHouse 日志 | 4/15 策略调 `blog.signal` | **0/8 记日志** |
| `source` | 1/15 设 STRATEGY，14 掉 OTHER（signal.py:36） | **8/8 全掉 OTHER** |
| `business_timestamp` | 8 用 `portfolio_info["now"]`、1（Random）用 `provider.now()`；同源（portfolio_base.py:919）冗余 | 各类各异 |

后果：同样"产生一个信号"，日志完整度与 `source` 字段因来源不同而不可靠——**静默数据质量漂移**。此外 `finalize()`/`on_data_updated()` 经 grep 无策略侧调用方（死方法），`validate_parameters()` 基类恒 `True`（仅 RandomSignalStrategy 覆写，#24 绑定时校验）。

## Decision

把两份 `create_signal` 统一深化为**信号发射 seam**——单一入口，背后藏 4 件事，调用方只见业务参数：

1. **构造** Signal（现状）—— 自动填 portfolio/engine/task_id
2. **`business_timestamp`** —— 缺省 `self.get_time_provider().now()`；provider 为 None 时**留 None**（全链路契约支持，见 Rationale）；调用方可覆盖
3. **`source`** —— 按角色缺省：Strategy→`SOURCE_TYPES.STRATEGY`，Risk→**新增 `SOURCE_TYPES.RISK`**；调用方可覆盖
4. **ClickHouse 日志** —— 无条件调 `self.blog.signal(...)`；Strategy 传 `strategy_id=self.uuid`，Risk 传 `risk_id=self.uuid`

配套：删除死方法 `finalize()`/`on_data_updated()`；收敛 4 个手写 blog 的策略（6 处）与 RandomSignalStrategy 的后置 `set_source`；`validate_parameters()` 留 hook + 默认 `True`（待类型化参数注入收编）。

**两份 seam 同结构、不同参数**：Strategy 与 Risk 共享"构造 / 时间 / source / 日志"四件事，仅 source 缺省值与日志 id 字段按角色分叉。**不抽共享 mixin**——BaseStrategy/RiskBase 继承链已分，禁改 Base 类 norm（CLAUDE.md）下强行抽 mixin 牵动面更大，且收益（省一份 ~10 行样板）抵不过耦合成本。

## Rationale

- **"值归谁"决定可不可覆盖**：`source`/`timestamp` 是组件**拥有的值**（缺省 + 可覆盖）；日志是框架**拥有的基础设施**（11 策略 + 8 Risk 不记是 bug，无条件）。这条线挡住"日志也加开关"的滑坡。
- **provider=None 留 None 有三层契约支撑**：entity 默认 `business_timestamp=None`（signal.py:42）、ORM `nullable=True`（model_signal.py:40）、下游 `signal.business_timestamp or signal.timestamp` 兜底（signal_tracking_service.py:63）。"可缺时间戳"是系统既有设计，非新引入风险。seam 拿不到 event（签名只有 code/direction/reason），无法照搬 Random 的 event 兜底。
- **加 `SOURCE_TYPES.RISK` 免 ALTER**：source 列是 `Int8`（model_clickbase.py:53），非 ClickHouse Enum16——枚举值只活在 Python 语义层，DB 层即 int，加值零成本，不触碰 ADR-007 禁手动 ALTER。
- **不退回显式两段（create + emit）**：那正是当前 RandomSignalStrategy 只 create 不 log 的漂移根源。
- **timestamp 取 `get_time_provider()`**：portfolio_base.py:919 证明 `portfolio_info["now"]` 与之同源，且两份 create_signal 所在类经 TimeMixin 已持 provider → seam 无需 `portfolio_info`，接口保持业务参数，深度最大。

## Consequences

- **行为变更（难逆转）**：23 个子类（15 Strategy + 8 Risk）将统一记 ClickHouse 信号日志；`source` 默认由 OTHER 变 STRATEGY（Strategy）/ RISK（Risk），均可覆盖。
- **新增枚举值**：`SOURCE_TYPES.RISK`（建议 =22），Int8 列免 ALTER。
- **验证方式**：一次回测前后对比 ClickHouse 信号行——修复前仅 4 策略有日志、source 混乱、Risk 完全无日志；修复后齐日志、source 按角色分明。比单测更能证明 drift 修好。
- **交叉引用**：ADR-001（组件单向流，`cal()`/`generate_signals()` 契约不变）、ADR-008（框架能力边界机制层细化）、ADR-010（Signal 是 Entity，发射 seam 耦合构造与观测）、ADR-007（Int8 列使加 source 值不破"Model 驱动建表"）。
- **未决（与本 ADR 正交，单独处理）**：4 处 `isinstance(event, EventPriceUpdate)` guard 多半死防御（需先确认 portfolio handler 注册的事件类型再删）；`initialize()` 签名错配（strategy_adapter.py:156 传 `**kwargs`、基类收 `context: Dict`）。

## 判定标准自检

- ① **难逆转**：23 子类依赖，但被其简化（回退需重加样板）——中等。
- ② **反直觉**：`create_signal` 顺带写 ClickHouse、且两份同名方法不同 source 缺省——未来必被质疑——满足。
- ③ **真实权衡**：A Strategy-only / B 两份统一（**本 ADR**）/ C 抽共享 mixin——选 B——满足。
