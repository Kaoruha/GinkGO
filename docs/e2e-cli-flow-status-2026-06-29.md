# Ginkgo CLI 量化研究全链路状态（2026-06-29 复验）

## 背景
量化研究员目标：通过 ginkgo CLI 完成「策略开发 → 回测 → 评估 → 找稳定盈利策略 → 部署模拟盘」全链路，定位缺失功能。
本文为 2026-06-29 **实测复验**（对照 6-22 e2e 审计头条 issue #6279-#6285）。

环境：DEBUG 模式；测试库 CH 行情数据上限 2025-02-18；少量数据。

---

## 一、链路体检（实测）

| 环节 | 可用性 | 实测证据 | 当前卡点 |
|---|---|---|---|
| 策略开发 | ✅ | 14 策略可 bind | #6480 name 错绑（绕过=strategy 不传 --param）|
| 回测 | ⚠️ | `backtest create/run/cat` 通 | #6483 600行截断(P1)、数据上限 2025-02-18 |
| 评估 | ✅ | 21 analyzer 正常（profit/sharpe/PF/drawdown/win_rate…）| result_service 缺 sum 聚合（小增强）|
| deploy paper | ✅ | #6473(pick种子)/#6489(service路径) 已合并 master | #6481 装配崩溃（strategy 传 params 时）|
| 模拟盘运行 | ⚠️ **已通** | worker 跑 8 组合、advance 到 2026-06-30、record signal_count/order_count、有组合 profit=659万 | #6488 trade_day 正式同步 |
| 实盘 | ❌→待验 | #6284 已补 account CLI（CLOSED）| 需端到端复验 deploy live |

---

## 二、重大进展（vs 6-22 审计）

6-22 头条 7 个 P0/P1 bug（#6279-#6285）**全部 CLOSED**：
- #6279 deploy 克隆丢绑定、#6280 UUID 截断、#6281 live 裸 SQL、#6282 数据预检、#6283 worker --id、#6284 account CLI、#6285 deploy info 打磨
- paper 侧 #6473（运行时 deploy 补 selector.pick() 种子）、#6489（worker service 路径）已修
- ADR-017（commit `d6054a0e`）重构 feeder 事件订阅：`on_interest_update` 替代了记忆里的死方法 `update_interested_codes`（grep 零命中确认已删/改名）

**结论：链路实质已通。** 6-29 worker 日志实测：advance 到 2026-06-30、record signal_count/order_count、`Portfolio.on_signal` 多次触发、某组合 profit=659万。

> 注：6-29 周日被 daily_cycle 判定「非交易日 skip」是**正确行为**，worker 随后 advance 到 6-30 周一交易日。

---

## 三、缺失功能清单（按优先级）

### P0 — 阻塞「稳定盈利验证」
| # | 缺失 | 状态 | 影响 |
|---|---|---|---|
| #6483 | 回测 ~600 行 net_value 静默截断却标 completed | OPEN | ~20 月天花板，跨策略系统性；判跑满须查 analyzer 末日 vs cfg end，**非信 task.status**；无法验证 3 年+策略稳定性 |
| — | DEBUG 测试库数据上限 2025-02-18 | 基建 | 历史样本不足，momentum/MR 同止于此；需切非 DEBUG 库或补数据 |

### P1 — 阻塞「模拟盘真实信号生产」
| # | 缺失 | 状态 | 影响 / 绕过 |
|---|---|---|---|
| #6488 | trade_day 日历正式同步 | OPEN | `fetch_cn_stock_trade_day` 4 源定义但 sync 链路零调用，靠手动补表；数据更新第 4 断点 |
| #6491 | feeder 注入第二层 | OPEN **(待 triage)** | ADR-017 已用 `on_interest_update` 重构注入，issue 前提可能过时，需复核是否仍成立 |
| #6481 | deploy→paper worker 装配 strategy 崩溃 | OPEN | strategy bind 传 params 触发 #6480；回测同组合成功（装配路径 + 数据源双不对称）|
| #6480 | bind-component name 传 index0 错绑首个业务参数 | OPEN | 绕过=strategy 不传 --param 全默认实例化（带类型校验组件如 MeanReversion 才崩，无校验如 Momentum 静默用错值更危险）|

### P2 — 实盘链路
| # | 缺失 | 状态 |
|---|---|---|
| #6284 | 实盘 account CLI | CLOSED（已补），需端到端复验 deploy live 全链路 |

### 其他 OPEN（不阻塞跑通，影响健壮性/可维护性）
#6484 get_total_adjustment NameError、#6485 saga 补偿链丢单步、#6478 MPortfolio.update_at 列名永不刷新、#6486 bare print/except-pass 守门失败；架构深化簇 #6293-#6300 / #6469-#6479 / #6448-#6456。

---

## 四、对研究员的实操建议

1. **当前可用链路**：`portfolio create` → `bind-component`(selector+codes / **strategy 不传 --param 绕 #6480** / sizer / risk) → `backtest create/run/cat` → `deploy deploy --mode paper`
2. **迄今最 promising 策略**：`mean_reversion` MR14（RSI14，阈值 30/70 默认）— 回测净值 +14.1% / Sharpe +0.254 / PF 2.17 / 胜率 68.7%，whipsaw 镜像抗跌（动量 -21% 时 MR 仅 -4.8%）。momentum 已被充分样本证伪（无 alpha）。
3. **模拟盘验证**：装配层已通；signal 生产待 #6488 正式修复 + bar 数据补今日。
4. **「稳定盈利」结论受限**：#6483 截断 + DEBUG 数据上限双重限制，**扩数据后须复验**，勿据当前小样本下定论。
5. **profit=659 万组合可疑**：疑 stale replay engine 异常值（记忆 `project_paper_analyzer_inconsistency_unverified` 记载），需 DB 核对净值曲线。

---

## 五、阻塞关系

```
数据基建(#6488 trade_day) ─┐
                          ├─→ 模拟盘真实 signal ─→ 实盘(#6284 复验)
装配(#6480/#6481) ─────────┘
回测截断(#6483) + 数据上限 ─→ 稳定盈利验证（需扩数据）
```

关联 issue：#6473 #6480 #6481 #6483 #6488 #6489 #6491 #6279-#6285
对照：6-22 e2e 审计、paper-trading 状态记忆、ADR-017 feeder 事件订阅契约
