# ADR-001: 组件边界与单向流动

**Status:** Accepted
**Date:** 2026-06-13

## Context

回测/实盘的交易流水线由多个组件串联。早期各组件职责交叉（策略里算仓位、风控里加单），导致信号语义混乱、组件难以独立替换、测试相互纠缠。

## Decision

交易链路采用**单向数据流**，每个组件职责单一、输出类型固定，并有明确的"禁止"边界。

**事件链路：**

```
PriceUpdate → Strategy → Signal → Portfolio → Order → Fill
```

**组件职责矩阵：**

| 组件 | 职责 | 输出 | 禁止 |
|---|---|---|---|
| Selector | 选股 | `List[str]` | 生成信号、计算仓位、做风控 |
| Strategy | 交易信号 | `List[Signal]` | 选股、止损止盈、计算仓位 |
| Sizer | 开仓手数 | volume | 风控校验 |
| Risk | 风控拦截 | 调整后 order/signal | 增加订单量 |

## Rationale

- **可替换性**：组件只依赖上游的输出类型，可独立替换（如把 fixed Sizer 换成 atr Sizer 不动 Strategy）。
- **风险隔离**：Risk 只做"拦截/缩减"，明确禁止"增加订单量"，防止风控层反向放大风险。
- **信号纯净**：Strategy 不碰仓位与止损止盈，使 `Strategy.cal() -> List[Signal]` 契约稳定，向量化（`cal_vectorized`）与逐事件两条路径输出一致。

## Consequences

- 止损止盈属于 Portfolio/Risk 层职责，Strategy 内不应实现。
- 新增组件类型时，必须先定义其"输出类型"和"禁止行为"，再写实现。
