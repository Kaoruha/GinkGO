# ADR-041: 三链路 Portfolio 契约统一（回测/模拟/实盘同源成本模型）

**Status:** Accepted（分层：D1 大方向 Accepted；D2/D3 端口契约与 CostBreakdown 结构为 draft 附挂，待 S1 审计后定稿）

**Date:** 2026-07-29

**Related:** ADR-003（引擎二态统一 BACKTEST/LIVE）、ADR-032（CH 时序审计 vs MySQL 活状态）、ADR-036（回测 fill T+1 无后视）、ADR-037（slippage/FillPriceModel，#6851 已落地）、ADR-039（实盘 ExecutionNode 分布式，已落地）、Epic #6868

## Context

### 动机

Ginkgo 的 Portfolio 层有三条装配链路（详见 memory `arch_three_path_assembly`）：

- **回测**：`PortfolioT1Backtest` + SimBroker（T+1 延迟队列，ADR-036）
- **模拟盘**：`PortfolioT1Backtest` 变种 + SimBroker（手写装配，ADR-033）
- **实盘**：`PortfolioLive` + 真 Broker + Kafka（ExecutionNode 分布式，ADR-039）

三链路理论上共享 `PortfolioBase` 契约，但实测发现：**价格回调命名、fill 事件字段消费、成本入账语义三处不一致**。同一个策略在回测/模拟/实盘的成交成本计算口径不同——回测净值的"成本"与实盘真实成本不可比，削弱了回测对实盘的预测力。

`#6851`（epic-6851 / ADR-037）已落地 SimBroker 侧的 `FillPriceModel` 统一（**成交价生成阶段**接入 slippage）。本 ADR 聚焦**下游 Portfolio 入账阶段**的契约统一——fill 价已生成后，Portfolio 如何记账。

### 现状审计（2026-07-29 grep 实测）

#### 1. 价格回调命名裂痕

| 链路 | 回调名 | 位置 |
|---|---|---|
| PortfolioBase | `on_price_received` | `bases/portfolio_base.py:737` |
| 回测 (t1backtest) | `on_price_received`（继承） | `portfolios/t1backtest.py:405` |
| 模拟盘 | `on_price_received`（继承 t1backtest） | — |
| 实盘 (portfolio_live) | **`on_price_update`** | `portfolios/portfolio_live.py:194` |
| TradeGateway | `on_price_received` | `gateway/trade_gateway.py:231` |

`PortfolioLive` **没有覆写** `on_price_received`，而是另起 `on_price_update`——base 契约的 `on_price_received` 在 live 链路不被触发（或由别处桥接）。端口契约名实不符。

#### 2. fill 事件字段消费裂痕

`EventOrderPartiallyFilled`（`events/order_lifecycle_events.py:105`）定义字段：`filled_quantity` / `fill_price` / `trade_id` / `commission` / `order_status` / `fill_amount`。

但 `PortfolioT1Backtest.deal_long_filled`（`t1backtest.py:873`）类型注解为 `event: EventOrderPartiallyFilled`，却消费：

- `event.fee` → 实读 `EventOrderRelated.payload.fee`（= `order.fee`，`order_related.py:109-110`）——**订单级累计费用**，非本次成交
- `event.frozen_money` / `event.remain` / `event.transaction_price` —— **均不在 `EventOrderPartiallyFilled` 定义中**（类型注解漂移：实际 event 或为另一事件类型，或属性经 payload/order 间接提供）

而 `PortfolioLive.on_order_partially_filled`（`portfolio_live.py:258`）消费 `event.commission`（本次成交手续费）+ `fill_price`。

**语义错位**：

- 回测入账 fee = `order.fee`（订单级累计）
- 实盘入账 fee = `event.commission`（本次成交）
- 两者不是同一口径，跨链路不可比。

#### 3. slippage 可获得性裂痕（决策性发现）

- `EventOrderPartiallyFilled`（回测/实盘 fill 主事件）：**无 slippage 字段**。回测的 slippage 已在 SimBroker 生成 `fill_price` 时吸收（ADR-037 / #6851），portfolio 入账不单独记。
- `EventExecutionConfirmed`（`events/execution_confirmation.py:24`）：**有 slippage 字段**（`expected_price` vs `actual_price` 推算）——但 **全仓零使用**（grep `ExecutionConfirmation` 使用点为空，休眠事件）。
- 实盘交易所**不报告 slippage**（只报成交价/量/手续费）。

结论：**CostBreakdown 的 Slippage 元素在实盘侧天然不可获得**。任何"三链路同源成本模型"必须分层处理：回测/模拟可分解 `Fill + Slippage + Fee`，实盘只能 `Fill（含隐含 slippage） + Fee`。

### 数据流对比

```
回测/模拟 (PortfolioT1Backtest):
  SimBroker --[EventOrderPartiallyFilled]--> deal_long_filled
    fill_price(含 slippage, ADR-037) + order.fee + frozen_money/remain/transaction_price
    --> add_fee(order.fee) + deduct_from_frozen(transaction_cost)

实盘 (PortfolioLive):
  Broker --[EventOrderPartiallyFilled]--> on_order_partially_filled
    fill_price(交易所报, 隐含 slippage 不可拆) + event.commission
    --> fill_cost = price*qty + commission --> add_fee(commission)
```

### CostBreakdown 结构（draft）

```python
@dataclass
class CostBreakdown:
    fill: Decimal                  # 名义成交额 = fill_price × filled_quantity（所有链路可得）
    fee: Decimal                   # 手续费/佣金（所有链路可得，口径需统一为"本次成交 commission"）
    slippage: Optional[Decimal]    # 滑点成本（回测/模拟可从 FillPriceModel 拆出；实盘 None）
    # total_cost = fill + fee + (slippage or 0)
```

**关键约束**：`slippage` 在实盘恒为 `None`——不是缺失，是**语义上不可获得**。统一模型必须接受这一不对称。

### 四个待 S1 定稿的问题

1. **端口契约统一到什么粒度**：仅统一回调名（`on_price_update` → `on_price_received`）？还是连 fill 事件字段消费也收敛（回测改读 `event.commission` 而非 `order.fee`）？
2. **CostBreakdown 的 slippage 不对称如何呈现**：实盘 `slippage=None` 是接受现状，还是回测侧也放弃拆分（统一为 `fill+fee`，slippage 隐含）以保可比？
3. **类型注解漂移**：`deal_long_filled` 注解 `EventOrderPartiallyFilled` 却消费 `frozen_money/transaction_price`——是修注解还是修事件定义？关系到是否需扩 `EventOrderPartiallyFilled` 字段（触碰事件契约）。
4. **与 #6851(ADR-037) 的边界**：slippage 在 fill_price 生成阶段（#6851）vs 入账阶段（本 ADR）——#6851 完成后，回测 slippage 是否已可通过 `FillPriceModel` 反查，使 `CostBreakdown.slippage` 在回测侧可得？

## Decision

**分层决策**（S1 阶段）：

### D1 [Accepted，大方向]：端口层统一契约，不合并三个 Portfolio 子类

三链路 Portfolio 子类（`PortfolioT1Backtest` / `PortfolioLive`）保持独立——它们的事件源、装配链路、T+1 语义确有差异，合并违反 ADR-003 引擎二态。统一收敛在**端口契约层**：`PortfolioBase` 定义统一的回调名与 fill 事件消费契约，子类覆写实现但**不另起名、不消费注解外的字段**。

不采用"合并为单一 Portfolio"方案——三链路差异（SimBroker T+1 vs 真 Broker 实时 vs ExecutionNode 分布式）是本质的，合并会把 ADR-003/036/039 的语义揉成一团。

### D2 [draft 附挂]：端口契约草案（待 S1 审计定稿）

```python
# PortfolioBase 统一契约（草案）
def on_price_received(self, event: EventPriceUpdate) -> None: ...   # 实盘 on_price_update 改名归一
def on_order_partially_filled(self, event: EventOrderPartiallyFilled) -> None: ...
    # 统一只消费 event 定义内字段：fill_price / filled_quantity / commission
    # 禁止读 order.fee / frozen_money / transaction_price 等注解外字段
```

具体迁移（回测 `deal_long_filled` 改读 `event.commission`、`frozen_money` 如何归一等）待 S1 审计后定，可能需扩 `EventOrderPartiallyFilled` 字段（触碰事件契约，单列 S3）。

### D3 [draft 附挂]：CostBreakdown 结构（待 S1 审计定稿）

采用上文 `CostBreakdown` dataclass 草案。`slippage: Optional[Decimal]` 接受实盘 `None` 的不对称——这是对"交易所不报 slippage"这一物理事实的诚实建模，而非缺陷。

是否在回测侧也放弃拆分（问题 2）待定。

## Rationale

- **不合并子类**：三链路差异是 ADR-003/036/039 的刻意设计，合并逆转性高、风险大，违反"难以逆转才立 ADR"的反面——这是"难以逆转就不要做"。
- **统一在端口层**：契约统一（回调名 + 字段消费）是低成本高收益——让同一策略跨链路成本可比，提升回测预测力。
- **slippage 不对称诚实建模**：实盘 slippage 不可获得是物理事实（交易所不报），强行对称会引入虚假数据。`Optional` 是正确语义。
- **分层 Accepted + draft 附挂**：大方向（端口层统一）已明确无异议，立 Accepted；具体契约/结构因依赖 #6851 进度与 S1 审计，作 draft 附挂避免过早承诺。

## Consequences

- **正向**：三链路成本口径收敛后，回测净值与实盘成本可比，策略评估可信度提升。
- **代价**：D2 迁移需触碰 `deal_long_filled` 的字段消费（可能扩事件字段 = S3），是中量级重构。
- **依赖**：S3（事件字段扩展）依赖 `#6851`(ADR-037) 合并后才能定 `fill_price`/`slippage` 的拆分边界。
- **S1 产物**：本 ADR + 审计。S2-S4 是否值得做，由本审计的四个问题回答后决定——若问题 2/3 答案倾向"放弃拆分/仅修注解"，则 epic #6868 可瘦身甚至不解（呼应"可能不需要 epic issue"的质疑）。
