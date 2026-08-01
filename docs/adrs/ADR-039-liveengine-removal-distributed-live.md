# ADR-039: 实盘走 ExecutionNode 分布式,移除 LiveEngine 迁移孤儿

**Status:** Accepted
**Date:** 2026-07-29
**Related:** ADR-003（引擎二态统一,其"mode=LIVE 接管"目标在此降级）、[Epic #6875 移除 LiveEngine 迁移孤儿](https://github.com/Kaoruha/GinkGO/issues/6875)（由 issue 跟踪实现）

## Context

2026-07-29 spike 考古结论：LiveEngine 是**引擎统一迁移（ADR-003）+ 实盘分布式转向**两条线夹缝中的孤儿。

历史脉络：
- LiveEngine 原与按 mode 分态的旧引擎族同级（`ENGINE_TYPES.LIVE=4` 是独立引擎类型；ADR-003:8「引擎层曾遍布 `if mode==` 三态分支」）。
- ADR-003（2026-03-28）二态统一，声称「旧 LiveEngine 废弃，统一为 `TimeControlledEventEngine(mode=LIVE)`」。

但两条后续迁移线都没真正接管实盘：
1. **统一引擎线没落地**：`TimeControlledEventEngine(mode=LIVE)` 从未实例化。grep 确认 `time_controlled_engine.py` 全是 `if mode==BACKTEST / else`，实际只服务 BACKTEST/PAPER。
2. **分布式新线绕开引擎**：实盘改走 ExecutionNode 双平面（Control/Data），`PortfolioProcessor` 裸线程消费 Kafka 事件裸驱动 `PortfolioLive`，`node.py` 零 `EventEngine`/`engine.start`。

→ LiveEngine 被两条线同时抛弃，成夹缝孤儿：既没被统一引擎取代，也没被分布式架构容纳。叠加下单链路断（`TradeGateway` 全仓仅 3 处构造且实盘路径零实例化、`OKXBroker` 无 Kafka 订单入口只有入站 WS、`PortfolioLive` 不持 broker），它「活」的只剩连接 / WS 数据同步（入站），策略→下单→交易所闭环从未闭合。

相邻死代码 / 画饼枚举：
- `broker_manager.startup_create_all_brokers`（扫 `mode=LIVE` 建 broker，src/ 零调用方）——与 `LiveEngine.initialize` 重复的死方法。
- `TradeGatewayAdapter` 占位符（`main.py:396 _trade_gateway_placeholder`，「Phase 4 集成代码」在注释里未挂载）。
- `ENGINE_ARCHITECTURE.MATRIX`（矩阵/向量化架构）枚举值——即历史「向量计算引擎」设想，src/ 零分支实现、`engines/` 全事件驱动系，从未有对应引擎类。

## Decision

1. **正式承认实盘 = ExecutionNode 分布式路径**（Control/Data 双平面 + PortfolioProcessor 裸线程 + Kafka/Redis 总线）。这是现状，ADR 予以追认。不再追求「实盘收敛回 `TimeControlledEventEngine(mode=LIVE)`」——那是 ADR-003 的未完成目标，正式放弃。
2. **移除 LiveEngine 迁移孤儿**，连同其独有但无人使用的编排重复。具体清理项与顺序由关联 Epic 跟踪。
3. **下单闭环补焊另立 Epic**（不在本 ADR 决策范围）：移除 LiveEngine 既不修、也不恶化「实盘不能下单」——它本来就断。补焊是独立的实盘落地工作，涉资金安全需单独 gate。

## Rationale

- **Deletion test**：LiveEngine 是浅模块 + 重复——核心编排与 `startup_create_all_brokers` 重复（且后者已死），独有增量仅「进程胶水」（心跳 / 数据同步 / 恢复 / 信号处理），独立层无 leverage 只增 indirection。删它复杂度不重新散落到 N 个调用方。
- **架构叙事失真**：实盘现状就是 ExecutionNode 分布式。保留一个从不接管实盘的旧引擎类，会让 CLAUDE.md「实盘端到端待验证」被误读为「快好了」，而实则是闭环从未焊。移除孤儿让叙事归真。
- **scope 分离**：清理孤儿（可逆、低风险、纯删除）与补焊实盘下单（不可逆、高资金风险）是两种性质的工作。混 scope 会把删除的安全可逆性嫁接给下单接线的风险。

## Consequences

- `serve livecore --live-engine` / `live start` 等启用 LiveEngine 的入口需一并清理或重定向（ExecutionNode 已是正路）。
- `ENGINE_ARCHITECTURE.MATRIX` 等未实现枚举值的处置：移除或显式标注 `planned, not built`——防 grep 误判「已实现」（参因子子系统休眠 75% 教训）。
- 实盘下单闭环仍断（维持现状），由后续「实盘下单接线」Epic 解决——本 ADR 明确不覆盖。
- **与 ADR-003 的关系**：ADR-003 的「mode=LIVE 接管」目标降级为「仅引擎层行为语义（LIVE 与 PAPER 在引擎层等价）」，不再承诺实盘跑在事件引擎上。ADR-003 文本需补一条「见 ADR-039」的指针。
