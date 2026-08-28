# ADR-047: 交易日阶段状态机（日结构从涌现到声明）

**Status:** Proposed（方向已定，未实施；第 0 步 ENDDAY 上提引擎已于 2026-08 落地，见 §5）
**Date:** 2026-08-26
**Related:** ADR-036（回测 fill 时序两阶段推进——EOD pipeline 的直接前身）、ADR-023（业务时间/基础设施时间 Seam）

## Context

引擎的"一天"不存在于任何单点代码中。以"D 日终"为例，理解它何时发生需要在脑内拼出横跨 3 文件 5 方法的执行链：

```
① mainloop get 抛 Empty          → 隐含"D 日事件消化完"（推理，非声明）
② _is_backtest_finished / _get_next_time → now + interval
③ put EventTimeAdvance           → 隐含"日终信号"（队列空后才产生，推理）
④ handler: [end_day] → set_current_time(D+1) → matchmaking → put feeder 事件
⑤ feeder.advance_time → put D+1 价格事件 → put portfolio 事件（FIFO 涌现两段式）
⑥ 价格事件 → 持仓重标记
⑦ portfolio.advance_time → T+1 结算 → 信号重发 → NEWDAY
```

三个结构性病灶：

1. **语义靠推理**："队列空"≡"日终"、"FIFO 顺序"≡"两段式编排"这类等价关系只存在于注释与读者脑内。G1 修复中它们只能写成注释——当代码正确性需要注释才能理解，就是该概念该被结构化的信号。
2. **控制流分布式**：日生命周期无单点呈现，时序正确性是执行的结果，不是可检查的规格。
3. **隐式契约脆弱**：挪一行钩子位置、改一个 put 顺序，时序即静默漂移。G1（ENDDAY 记录戳晚一天）正是如此长出：钩子被"移到 T+1 信号处理之后"（注释还写着动机），无人意识到时钟与价格已翻页，数月无人发现。

代码中已有此方向的化石：`EventTimeAdvance` 注释自称"扩展 EventNextPhase 概念"并携带 `phase_id` 字段；`EVENT_TYPES.ENDOFDAY=5` 枚举、`EventEndOfDay` 类、`_is_end_of_day()`（跨 15:00 收盘或跨日期判定）、`_trigger_end_of_day_sequence()`、`_check_and_emit_bar_close()` 全部存在但零调用方/零 handler——原作者有此意图，走了一半未完成。

## Decision

**交易日阶段成为一等公民：引擎持有一个显式的 Session 状态机，阶段转换是唯一的时间语义事件源；组件声明式订阅阶段事件，"在 advance_time 里的位置"这一隐式约定逐步退役。**

### 1. 阶段模型

```python
SESSION_PHASES: PRE_OPEN → OPEN → INTRADAY → (LUNCH_BREAK) → CLOSE → EOD → 次日 PRE_OPEN
```

- 转换由**交易日历 + 时钟**驱动：回测走逻辑钟（LogicalTimeProvider 推进跨阈值即转换），实盘走墙钟（SystemTimeProvider 心跳跨阈值即转换），**同一张状态表**——这是回测/实盘 parity 的结构基础。
- `EOD` 语义 = A 股 15:00 收盘后的日终清算，而非午夜跨日（现状 `_is_end_of_day` 已含此判定）。
- 午休（11:30–13:00）在分钟级场景下是一等阶段；日级回测退化为 OPEN→EOD 一步。

### 2. EOD pipeline 显式编排

EOD 转换触发的动作序列是一条**显式有序 pipeline**，取代当前靠 FIFO 涌现的两段式：

```
EOD(D): ① portfolio.end_day()     — D 日终采样（时钟/价格仍=D，分析器纯净）
        ② clock → D+1             — 共享时钟翻页
        ③ feeder.advance_time     — 发布 D+1 价格
        ④ portfolio.advance_time  — T+1 结算/延迟信号重发/清仓/NEWDAY
```

### 3. 阶段事件目录

激活既有骨架：`EventEndOfDay`/`ENDOFDAY` 之外补 `EventSessionOpen` 等；ENDDAY/NEWDAY 分析器钩子迁移为订阅阶段事件；LIVE 日结复用同一入口（`PortfolioBase.end_day()`）。

### 4. 诚实边界：本 ADR 不解决什么

**组件间的数据依赖不会被消灭，只会被命名。** 两段式（③ 先于 ④）不是风格选择，是刚性依赖——T+1 重发信号的撮合需要 D+1 价已入 broker。阶段状态机结构化了"**什么时候**"，"**谁先谁后**"仍需在 pipeline 中显式编排（如上）。

## Rationale

- **可推理性**：日终从推理产物变成一个可断言的状态转换；时序 bug 的观测点从"追事件流"变成"断言状态机"（与 ADR-046 把回测任务生命周期形式化是同一洞察的两个应用维度）。
- **守卫消亡**：`date() !=` 比较、15:00 判定、`_last_end_day_date` 去重等"从连续时间重新推断离散阶段"的补丁全部消失——阶段本身一等后无需再推断。
- **parity**：回测/实盘共享同一张阶段表，LIVE 日结（15:00 收盘事件化）从"将来另做"变成"复用"。
- **备选与否决**：
  - *维持现状（涌现时序）*：零改动，但 G1 类 bug 的温床仍在，每加一个时间语义都要重新拼图。
  - *全面推翻重写引擎循环*：一步到位但迁移面失控，否决；取渐进路径（§5）。

## Consequences

**正向**：时序成为可检查规格；分析器/组件注册语义清晰；分钟级与午休天然支持；LIVE 日结路径就位。

**负向/代价**：所有 `advance_time` 调用点与依赖 FIFO 顺序的隐式契约需重新对齐（迁移期风险最高）；阶段表引入新的全局常量需与交易日历模块协同（节假日、半日市）；旧调试习惯（追事件流）需过渡。

## 5. 渐进迁移路径（不推翻）

| 步骤 | 内容 | 状态 |
|---|---|---|
| 0 | ENDDAY 上提引擎层：`_handle_time_advance_event` 推时钟前守卫触发 `PortfolioBase.end_day()`；`_is_end_of_day` 复用；`_last_end_day_date` 每交易日去重；模式守卫 = 与 `advance_time_to` 同款（BACKTEST+PAPER 族） | ✅ 2026-08 已落地（本 ADR 的第一步，引擎已持有日终判定权 = 状态机雏形） |
| 1 | 定义 `SESSION_PHASES` + 引擎内 Session 状态对象；推进判定输出"阶段转换"而非裸 datetime | 未实施 |
| 2 | 激活 `EventEndOfDay` 骨架，阶段转换发事件；ENDDAY/NEWDAY 钩子迁移为阶段订阅 | 未实施 |
| 3 | EOD pipeline 显式化（替换 FIFO 涌现的两段式）；组件按阶段重排 | 未实施 |
| 4 | LIVE 接同一张阶段表（墙钟跨 15:00 → EOD 事件 → `end_day()`） | 未实施 |

**实施前置**：本 ADR 仅为方向记录，不触发实施。当前优先级是让现有系统整体可跑（回测→模拟→实盘链路可用性），阶段状态机在系统稳定后按上表分步推进，每步独立可回退。
