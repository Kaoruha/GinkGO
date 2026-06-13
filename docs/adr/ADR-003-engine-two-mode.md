# ADR-003: 引擎二态简化

**Status:** Implemented
**Date:** 2026-03-28

## Context

`EXECUTION_MODE` 枚举有 BACKTEST / LIVE / PAPER / PAPER_MANUAL 多个值。引擎层曾遍布 `if mode ==` 三态分支，但审查发现所有分支本质都是 **BACKTEST vs 非 BACKTEST**，PAPER 与 LIVE 在引擎层零差异（`elif PAPER: same as LIVE`），三态制造了不必要的复杂度。

## Decision

引擎层 `TimeControlledEventEngine` **只按二态行为**：仅判断 `if self.mode == EXECUTION_MODE.BACKTEST`，其余（LIVE / PAPER / PAPER_MANUAL）走同一非回测路径。

- PAPER 与 LIVE 的差异（模拟成交 vs 真实下单）属于 **Broker / Gateway 层**，不进引擎。
- `EXECUTION_MODE` 枚举**保持四态不变**——PAPER / PAPER_MANUAL 在 Broker/Gateway 层仍有意义。
- 旧 `LiveEngine` 已废弃，统一为 `TimeControlledEventEngine(mode=EXECUTION_MODE.LIVE)`。

## Rationale

- 引擎层无需区分 PAPER/LIVE：它们的差异是"订单往哪发"，由 Broker 决定，与事件调度无关。
- 消除冗余 `elif PAPER` 分支后，引擎控制流从三态收敛为二态，可读性与可测性显著提升。

## Consequences

- 引擎代码中新增逻辑时，用 `if BACKTEST / else`，不要引入 `elif PAPER` 分支。
- 若未来确需引擎层区分 PAPER/LIVE，**说明关注点放错了层级**，应下沉到 Broker/Gateway。
- 详见 `src/ginkgo/trading/engines/time_controlled_engine.py` 与废弃的 `src/ginkgo/livecore/live_engine.py`。
