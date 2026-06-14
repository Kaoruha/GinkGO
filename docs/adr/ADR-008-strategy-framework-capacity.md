# ADR-008: 策略框架能力边界

**Status:** Accepted
**Date:** 2026-06-03

## Context

曾误判框架存在 6 项设计约束，据此高估了约 144 个策略"无法实现"，把数据源/指标/模型等实现工作误归因为"架构缺陷"，导致优先级错配。

## Decision

**框架设计层面能覆盖所有策略类型。** 经逐一验证，下列 6 项"约束"均**不成立**：

1. **Signal/Order 单标的单方向** —— 不成立。`Strategy.cal()` 返回 `List[Signal]`，可同时产 LONG A + SHORT B。
2. **Position 以 code 为 key，无独立空头** —— 不成立（刻意设计）。匹配 A 股单方向持仓规则；多资产用不同 Portfolio 隔离。
3. **事件链单标的线性流** —— 不成立。Strategy 持 `data_feeder`，收到 A 事件时可主动 `get_bars("B")` 拉任意标的。
4. **cal() 无状态，不支持 RL** —— 不成立。Strategy 是 Python 对象，可在 `__init__` 初始化、`cal()` 中累积；RL 训练在外部 pipeline，`cal()` 只做推理。
5. **Portfolio 单 Sizer** —— 不成立。不同资产用不同 Portfolio 隔离，各自绑 Sizer；Sizer 内部亦可按 code 分支。
6. **Risk 不能生成复杂对冲信号** —— 不成立。`generate_signals()` 可返回任意方向的 Signal，含反向对冲。

## Rationale

- 阻塞策略实现的是**数据源/指标/模型等具体工作**，不是架构约束。
- 把"未实现"误判为"框架不支持"，会错误地优先重构框架而非补数据/补实现。

## Consequences

- 评估 strategy-recommendation 类需求时，**框架设计不作为阻碍因素**，直接看数据源与实现工作量。
- 唯一的真实限制：两腿信号无原子性（一腿被 Risk 拦截后剩单腿敞口）——这是上层编排问题，非框架缺陷。
