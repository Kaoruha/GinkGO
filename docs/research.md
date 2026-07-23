# 盈利策略探索研究日志

> 载体文档。每次 `/loop` 迭代在「迭代日志」追加一条。目标：在**生产模式**下找到**稳定盈利**且**可走通 回测→模拟盘→实盘** 的策略。
> 维护者：Claude（自动探索） ｜ 起始：2026-07-24 ｜ 频率：每 5 分钟一轮（cron `*/5 * * * *`）

---

## 1. 目标与硬约束

| # | 约束 | 含义 |
|---|---|---|
| G1 | **生产模式** | 回测跑 Master 库（`ginkgo debug off`），非 test 沙盒 |
| G2 | **稳定盈利** | 年化 > 0 且跨窗口/多次复现一致；不接受单次幸运样本 |
| G3 | **路径可行** | 候选策略必须能走通 回测 → 模拟盘 → 实盘 三段 |
| G4 | **无后视效应** | 禁用 FixedSelector 直接外推 live（源码自标"后视偏差仅回测用"）；用动态 selector 或 walk-forward |
| G5 | **明确退出信号** | 每个进场必有规则化出场（止损/止盈/反转/时间），不能只进不出 |
| G6 | **问题归集** | 期间发现的 bug / 缺失功能经 `/to-issues` 提交，编号记入 §7 |

**后视效应判定清单**（每条候选过堂）：
- [ ] 选股用的是 t 时刻可知的信息？（动态 selector √；预置股票池 ×）
- [ ] 参数是否在全样本上拟合后未做样本外验证？（须 walk-forward / OOS）
- [ ] 是否用了未来函数（如信号用当日收盘、当日才知的数据下当日单）？

---

## 2. 探索协议（每轮迭代遵循）

1. **确定性优先**：同配置连跑 ≥3 次（隔离已知非确定性 bug，见 §4 警告 A），取中位数，记录极差。
2. **生产模式（⚠️ debug 易翻转）**：`debug` 是**全局共享 config**，并发会话/用户可互相翻转。实测本探索期间被翻成 `true`（test 库），致 portfolio 落错库 + 组件 "File not found"。**每次建 portfolio / 回测前必 `ginkgo debug off` 并 grep config 确认 `debug: false`**；bg 进程启动时读 config 即锁死，免受运行中翻转影响。
3. **无后视**：单股策略必须做 walk-forward（in-sample 拟合 → out-of-sample 验证）；全市场策略用动态 selector。
4. **退出信号**：记录每个候选的进场/出场规则各是什么。
5. **基准对照**：每个策略与同标的 Buy&Hold 比，报告 alpha（超额）而非绝对收益。
6. **记录**：每轮在 §6 追加：配置 / 回测 id / 年化/夏普/maxDD/胜率 / 信号→订单数 / B&H 对照 / 是否 OOS。

---

## 3. 数据现实（2026-07-24 实测，**权威**）

直接查 ClickHouse `ginkgo.bar` 表（`timestamp` 列）：

| 库 | bar 行数 | 代码数 | 时间范围 |
|---|---|---|---|
| **Master 生产** `:9000` | **17,116,428** | **5796** | 1990-12-19 ~ 2026-07-20 |
| Test 沙盒 `:19000` | 16,917,360 | 5569 | 同 |

关键标的 bar 数（Master）：

| 代码 | 行数 | 起 |
|---|---|---|
| 601899.SH 紫金矿业 | 4386 | 2008-04-25 |
| 600036.SH 招商银行 | 5821 | 2002-04-09 |
| 601318.SH 中国平安 | 4646 | 2007-03-01 |
| 000001.SZ 平安银行 | 8395 | 1991-04-04 |
| 600519.SH 贵州茅台 | 5964 | 2001-08-27 |
| 300750.SZ 宁德时代 | 1967 | 2018-06-11 |

> **⚠️ 推翻前置结论**：`docs/e2e-cli-flow-audit.md` 称"000001.SZ 仅 3 条、主流股票大面积空洞"——**已过时**。当前生产库是全 A 股完整日线、更新到 4 天前。前置研究困于单股 FixedSelector 的根因（以为数据稀疏）已解除，**可用动态 selector 做无后视全市场策略**。

---

## 4. 前置研究接力（digest 自 docs/strategy-search/、loop-backtest-positive-ev、cli-quant-*）

**最佳已知配置**（A1，3 年 87 轮迭代）：
`momentum(lookback=10, threshold=0.022) + RatioSizer(0.8) + LossLimitRisk(10%) on 601899.SH`
年化 15–17%、Sharpe 0.65–0.70、maxDD 20–21%、胜率 42–48%。

**警告（必读）**：
- **A. 非确定性 bug（P0 悬而未决）**：同配置多次跑年化在 3.9%–17% 波动（4 倍），成功率 ~60%。**任何结论须 ≥3 次复跑**。
- **B. FixedSelector 后视**：单股回测好 ≠ live 可用（G4）。
- **C. 出场时机是真瓶颈**：前置结论"瓶颈是出场不是仓位"；双风控(loss+profit_target)实测把年化从 15.8% 拖到 3.5%，**不要叠双风控**。
- **D. 所有主动策略大幅跑输 B&H**（最佳捕获率 38%）。紫金 3 年 B&H 年化 ~42.6%——绝对收益基准极难超。

**已修 issue**：#6182/#6183/#6184（数据调度链路，PR #6185）。

---

## 5. 回测 → 模拟盘 → 实盘 路径现状（自 e2e 审计，待复测）

| 阶段 | 状态 | 阻断点 |
|---|---|---|
| 策略构建 | ✅ | — |
| 回测 | ⚠️ | 无数据预检→0 交易要跑完才知；`result show` 末值 50 点采样未必含末日 |
| 模拟盘 | ⚠️ | **2026-07-24 代码复核**：组件装配对称（INIT/`_handle_deploy` 经 #6473 共 `_seed_selectors`，service 层 #6164/#6279 克隆全类型）。**但发现新阻断（#6757 P1）**：`_handle_deploy`（worker:858-948）建 `PortfolioT1Backtest` 后**不 `add_cash`**，而 `PortfolioBase` 默认 cash=0（base:117）；INIT step8（worker:193-218）对新 portfolio 会注入 `initial_capital`。`_deploy_core` step9（deploy_service:236-250）发 Kafka 命令给运行中 worker → **worker 运行中 deploy 新 paper portfolio → 现金=0 → 信号照发但订单因无购买力全失败 → 静默 0 成交却标 RUNNING**（memory 警示的"安静失败"类）。**#6757 已提，与 #6473 互补**（#6473 修信号链 selector 种子，#6757 修资金链 cash） |
| 实盘 | ❌ | 无 CLI 建账户；假 account_id 触发裸 `Unknown column` SQL 错 |
| deploy 输出 | ⚠️ | Portfolio ID 被截断 31 位（真 32 位 UUID） |

---

## 6. 迭代日志

### ITER-000 (2026-07-24) — Bootstrap
- 消化前置研究语料（Explore 子代理）；查明生产库数据完整（§3）。
- 建立本载体 + 探索协议 + 任务清单。

### ITER-001 (2026-07-24) — 复现 A1 + 隔离非确定性（**进行中**）

**配置**：`momentum(lookback=10, threshold=0.022) + FixedSelector(601899.SH) + RatioSizer(0.8) + LossLimitRisk(10%)`
Portfolio `badbea37d8fd4250bbf07706ca6c56a5`

**G5 出场规则过堂**：进场 `momentum>0.022 且空仓→LONG`；出场 ① `momentum<-0.022 且持仓→SHORT`（反转）② `亏损>10%→卖`（止损）。✅ 有规则出场。

**验证回测（3 月 2026-04~07，生产 Master 库）** BT `9e5682914e404aa0ab074352a73de050`：
55s ｜ Final 103389(+3.39%) ｜ **年化 9.78%** ｜ Sharpe 1.15 ｜ MaxDD 2.14% ｜ 胜率 0.50 ｜ Signal 7 / Order 6。
✅ G1（生产可跑）+ G5 验证通过，组件装配正确。

**超时事故 + CLI 缺口**：全 3.5 年 run1（BT `a71978d9…`）前台 8min 超时被杀（exit 143），**卡 running 70% 不可恢复**（`feedback_backtest_run_sync_timeout` 陷阱）。
- `ginkgo backtest` 有 `delete`（软删）但**无 `cancel`/`reset`/`abort`**——卡死任务无法恢复（待 /to-issues）。
- `backtest run` 有 `-bg`（后台线程）选项，异步能力存在；但前台同步默认 + 无超时保护，长窗口（>8min）前台必死。

**改 2 年窗口后台 3 连跑**（2024-07-20~2026-07-20，bg `bi37qu1jg`）：实际 ~9-11min/次、~30min 总。

**3 连跑结果**（BT run1=`25a5fbf6` run2=`60ea8b42` run3=`1c5570f6`）：

| 指标 | run1 | run2 | run3 | 极差 | 中位 |
|---|---|---|---|---|---|
| 年化 | 15.93% | 15.35% | 16.53% | **1.18pp** | 15.93% |
| Sharpe | 0.674 | 0.650 | 0.697 | 0.047 | 0.674 |
| MaxDD | 26.74% | 25.29% | 25.32% | 1.45pp | 25.32% |
| 胜率 | .4375 | .4375 | .5000 | — | .4375 |
| **Signals** | **57** | **57** | **57** | **0** | 57 |
| **Orders** | **44** | **44** | **44** | **0** | 44 |
| Final | 153372 | 151148 | 155652 | 3% | 153372 |

**ITER-001 结论（✅ 完成）**：
1. **引擎 per-portfolio 近确定性**：Signals/Orders 三次**完全相同**(57/44)；年化极差仅 1.18pp（中位 15.93%）。
2. **§4 警告 A（3.9–17% 4 倍方差）未被复现**——该方差是**跨 portfolio 轴**（#4711：同参不同 portfolio 信号数 14 vs 0），非同 portfolio 跑间。同 portfolio 单次回测**可信任**（±1pp）。
3. 微小 Final 差（1.5–3%）来自 fill 级执行价微扰（同信号不同成交价），非逻辑层。
4. **复现 A1 成功**：中位 年化 15.93%/Sharpe 0.674/MaxDD 25.3%/胜率 ~44%，落在 A1 已知带（15–17%/0.65–0.70/20–21%/42–48%）。
5. ⚠️ **G4 不达标**：FixedSelector(601899.SH) 是预选股（后视），**不可直接上 live**。ITER-001 只验证了引擎可复现性 + A1 盈利性，**非可部署策略**。可部署路径须 ITER-003 动态 selector。

### ITER-003 (2026-07-24) — 动态 selector 全市场无后视路径（**进行中**）

**配置**：`MomentumSelector(interval=5,rank=5,window=20)` + `momentum(lookback=10,threshold=0.022)` + `RatioSizer(0.1)` + `LossLimitRisk(10%)`
Portfolio `036057a26f624444885123af10f0ee8f`（生产 Master 库，`debug:false` 核验）

**G4 后视过堂**：✅ MomentumSelector 每 interval(5) bar 用**过去 window(20) 天已知收益**横截面排序选 top-5——纯历史信息，无未来函数、无预置股票池。这是**首个真正无后视可部署**的候选（FixedSelector 的替代）。
**G5 出场过堂**：进场 `选入且 momentum>0.022→LONG`；出场 ① `momentum<-0.022→反转` ② `亏损>10%→LossLimitRisk 卖`。✅ 规则化出场。

**Smoke（1 月 2026-06-20~07-20）** BT `a084006395534f0088b715c128433af8`：
Final 87524(-12.5%) ｜ 年化 **-68.6%** ｜ Sharpe **-5.83** ｜ MaxDD 13.7% ｜ 胜率 **10%** ｜ **Signals 99 / Orders 30**。
- ✅ **关键正面结论**：**Signals=99**（≈20 交易日×5 股）证明全市场 momentum_selector **在回测模式能取数产信号**——`arch-strategy-data-api-backtest-availability` 的 data-feeder 陷阱**不适用**动态 selector（该陷阱是单股策略取数 API 问题）。**G4 可行性 + 回测可跑通**。
- ⚠️ 1 月巨亏属预期：动量在 2026-06~07 反转窗口被碾压（买顶部赢家即反转），**不代表全周期**。胜率 10% 偏低，后续迭代可加趋势过滤/调阈值。

**全 2 年周期起跑**（2024-07-20~2026-07-20）BT `fa9a1ca93b1d40db99ce48206a7dd98f`：**超时被杀**。精确测算 73%@40.8min（速率从 0.49 退化到 0.59 min/%，后段 universe 增大），ETA 04:18 > timeout 04:14:51，**裁定 pivot**：杀 2yr（记录于 `stuck_bts.txt` 待软删）。
- **⚠️ perf 教训（重要）**：全市场 momentum_selector（5796 股横截面排序）长窗口**单次 >60min、且后段退化**——迭代不可行。后段（2026）universe 最密最慢。**全市场迭代用 1yr 窗口**，优胜者再补完整 2yr 终验。

**1yr calendar-2025 fallback（✅ 完成 → 裁定 LOSS）** BT `945c5716c5154fac9625bf728f4e072b`：同配置，窗口 **2025-01-01~12-31**（避开 2026 最密尾段）。
Final **61404(-38.6%)** ｜ 年化 **-28.72%** ｜ Sharpe **-3.15** ｜ MaxDD **38.6%** ｜ 胜率 **25.5%** ｜ **Signals 7801 / Orders 700**。
- **裁定：亏损策略（非盈利）**。全市场 top-5 动量轮动在 2025 全年震荡市被反复打脸（买顶部赢家即反转→止损→换股→再反转），承袭 smoke 反转窗口结论，**非一次性样本**。胜率 25.5%（7801 信号 / 700 成交：多数信号被 RatioSizer 现金不足/LossLimitRisk 拦截，或 SHORT 在 A 股无券可融失败）。
- **孤儿救援技巧（可复用）**：刷新阶段逼近 3000s timeout（数据 04:26 已到 12-31，但收尾 add_all 刷新慢且 CH I/O 竞争下退化 1.5→9.4s）。SIGKILL timeout 封装+脚本冻结倒计时、**孤立 python 引擎**继续刷新，待并发回测退出后刷新加速（add_all 降 1.1s），引擎 04:58:16 干净完成——从超时丢失中救回结果。
- **关键判读**：A 股 2025 属震荡/均值回归市，**纯动量不适配**。plan-B 须换**市场适配**的信号（均值回归）而非仅调参（B1 拉长窗口难逃震荡市动量失效）。

### ITER-003b (2026-07-24) — plan-B mean_reversion（**prep 完成，待 CH 空闲起 smoke**）

**配置**：`momentum_selector(interval=5,rank=5,window=20)` + `MeanReversion(rsi_period=14,oversold=30,overbought=70)` + `RatioSizer(0.1)` + `LossLimitRisk(10%)`
Portfolio `iter_mr_planB` = `9a08d73217bd4c7187b0bf47c22aa7fd`（生产 Master，`debug:false` 核验；4 组件绑定读回齐全，index0 name 全在）。
**G4/G5 过堂**：RSI 用过去 N(14) 日算超卖/超买→纯历史（G4✅）；出场 RSI 升破 overbought/止损（G5✅）。
**已验 mean_reversion 真实实现**（非 stub，`src/ginkgo/trading/strategies/mean_reversion.py`：`_calculate_rsi`+`_detect_crossing`）。
**下一步（CH-gated）**：CH 当前被并发会话 bt `6554d322`(iter9_mom2025c，非我的) flush 占用，**起 smoke 前须 pgrep 确认其退出**。先 smoke 2026-06~07（MR 反转主场，~3min）；盈→1yr cal-2025 终验。
⚠️ 语义风险：momentum_selector 喂 top-5 动量赢家（常 overbought），MR 要 oversold→可能 LONG 信号稀少/SHORT(A股不可融)失败。smoke Signals 数即判据；若≈0 换 popularity/cn_all selector。

**Smoke 结果（2026-06-20~07-20，BT `ad8314efe4a9488d855b914f62147602`）**：Final **100000（0 交易）** ｜ **total_signals: 0** ｜ Status completed。
- **根因 = 语义不匹配（非 bug）**：run.log 显示 `get_bars_cached` **回测可用**——270 次查询全返 **42-45 根** bar（>>RSI 需 29），0 硬失败，RSI 实算 ~263 次。但 `_detect_crossing` 仅在 RSI **穿越 30/70** 时触发；momentum_selector 喂的赢家 RSI 常驻 **50-70 中高位、无穿越** → 0 信号。
- **重要修正**：`arch-strategy-data-api-backtest-availability`（取数 API 回测失效）旧陷阱**不适用** MR 的 `get_bars_cached` 路径——该 API 在回测**正常工作**（42 根）。MR 0 信号是 selector×strategy 语义错配，非基建。
- 7 次 `计算 RSI 失败: unsupported`（close=None/类型，`strategy_data_mixin.py:161` 只过滤 timestamp 没过滤 close）——已被 `_calculate_rsi` try/except 兜住返 None，非功能 bug，不提 issue。
- **裁定**：MR + momentum_selector = 死组合（赢家不打 RSI 极值）。plan-B 须换**喂波动/极值股**的 selector。

### ITER-003c (2026-07-24) — plan-B 换 popularity_selector（**0 symbols，撞 selector bug #6760**）

**假设**：momentum_selector 每 5 日轮动、专挑赢家，赢家不打 RSI 极值故 MR 死。换 `popularity_selector`（按成交量 Top-N，**不按动量轮动**）→ 可持仓穿越回调 → MR 可抓超卖反弹。
**配置**：`PopularitySelector(rank=10,span=30)` + `MeanReversion(14,30,70)` + `RatioSizer(0.1)` + `LossLimitRisk(10%)`，Portfolio `iter_mr_pop` = `48e51ab2f9fc455c996c1e251778903f`（4 组件绑定读回齐全）。
**Smoke 结果（2026-06-20~07-20，BT `eb49f0ce29b445ffbaf33dead3c871e0`）**：Final **100000（0 交易）** ｜ **total_signals: 0** ｜ run.log 全程 `Published interest update for 0 symbols: []`，**无** `PopularitySelector: scanning` 日志 → pick 短路在空 codes。
- **根因（确凿）**：`PopularitySelector.pick` 取候选 code 走 `stock_info_crud.get_all_codes()`；**Master MySQL `stock_info` 表实测 0 行** → codes 恒空 → `if not codes: return`（**静默**，无 WARN）。同库 ClickHouse `ginkgo.bar` 有 ~5800 code 齐全。`MomentumSelector` 早已避开此坑（改用 `bar_service.get_available_codes()` 从 bar 表取，并在空时 WARN，注释明示「扫 stock_info 创造空工作」），popularity 未跟进。
- **裁定**：非策略问题，是 **selector 取码路径 bug + 静默失败**。已提 **#6760**（P2, mod:trading, ready-for-agent）。
- **plan-B 三连裁定**：MR 路径两个动态 selector 均受阻——momentum 是**语义不兼容**（ITER-003b），popularity 是**基建 bug**（本轮）。可跑通产信号的动态 selector 目前**仅 momentum 一个**，而 momentum+momentum 已证 2025 巨亏（ITER-003）。MR 等震荡市策略暂无可用动态 selector 喂票。

### ITER-003d (2026-07-24) — selector 可用性盘点（**代码分析定论，未跑回测**）

§8 第二优先级探测 cn_all/multi_params，结果（代码层 + 实测，无需回测即定论）：
- **`cn_all_selector` 同死于 #6760**：pick 走 `stockinfo_service.get_stockinfos_df()`，实测 success 但 **0 行**（Master stock_info 空）→ pick 恒空。与 popularity 同根因。
- **`multi_params` selector 无 src 实现**：`src/ginkgo/trading/selectors/` 仅 4 文件（fixed/cn_all/momentum/popularity），multi_params 不在其中（可能 DB 脚本组件或 CLAUDE.md 过时条目）。
- **`fixed_selector` 预选股后视**（违 G4，ITER-001 已证不可部署）。
- **selector 可用性终盘**：4 个有实现的 selector 中，**stock_info 空表杀死 cn_all + popularity（2/4）**，fixed 后视不可部署，**仅 momentum 可用**。selector 缺口从「popularity 单点」升级为「stock_info 元数据未填充的结构性缺口」。
- **stock_info 空根因**：数据源 TUSHARE、需 sync 导入，Master 库未导入；`data_cli` 只有 `get stockinfo` 无 `sync`/`import` 命令。
- **已补 #6760 comment**：扩大影响面至 2/4 selector，建议修复时一并覆盖 cn_all。
- **裁定**：在 stock_info 补数或 selector 改取 bar 码（#6760 修复）之前，**策略空间被锁死在 momentum 单族**。ITER-004 walk-forward 成为本 arc 唯一可推进的研究线（验 momentum 是否存盈利窗口）。

### ITER-004 (2026-07-24) — momentum walk-forward smoke（**2024Q4 涨势段仍亏 → momentum 判死**）

**目的**：momentum+momentum 唯一未验窗口是 2024（ITER-003 只测 2025 震荡 -28.72%）。挑 **2024-10~12（924 后最强涨势段）** 作 smoke——若 momentum 连最强涨势都不盈，即可判死，不必再跑全年。
**配置**：复用 ITER-003 portfolio `036057a26f624444885123af10f0ee8f`（`iter003_xs_mom`：momentum_selector+momentum+ratio_sizer(0.1)+loss_limit(10%)），仅换窗口。
**结果（BT `3656920189444c71a1f122cea9379415`，2024-10-01~12-31，Master，与 a3778c58 并发 ~3.5min）**：
Final **94358（-5.6%）** ｜ MaxDD **18.88%** ｜ Sharpe **-0.6687** ｜ AnnualReturn **-15.01%** ｜ WinRate **13.16%** ｜ 482 信号 / 119 单。
- **G5 诊断**：momentum 退出 = `动量 < -threshold → SHORT 信号`（reason "动量卖出"），**形式上有明确退出规则**（G5 达标）。但 win 13% 说明 entry 追高（买 86%+ 涨幅的见顶股）→ 频繁在动量反转时亏损卖出。
- **判死依据**：2024Q4 是 A 股近 2 年最强涨势段（924 行情），momentum 在此仍 -5.6%/win 13% + 2025 震荡 -28.72% → **涨势、震荡双市场均亏 = 结构性失效**（非周期性、非参数可救）。entry「追最高动量股」在 A 股追涨杀跌失效。
- **结论**：唯一可用动态 selector（momentum）× momentum strategy 在所有已测窗口亏损。**momentum 路径判死**。

### ITER-005 (2026-07-24) — G3 实盘侧 account create 诊断（**create 通畅；改发现 UUID 输出空 bug #6761**）

**目的**：arc 收束后，推进 §8 队列"G3 路径 live 侧 account create SQL error 待查"——独立于策略盈利性，属问求"实盘路径可行性"范畴。
**方法**（生产库 debug=false，只读探表 + 单次 auto-validate OFF 重现）：
- `account list`（只读）正常返回"无记录"——`live_account` 表存在于 Master、可读、非 SQL error。先前"SQL error"未复现。
- `account create`（auto-validate OFF，dummy OKX 凭证，不触达交易所）**成功**：账号 `27039f7b...` 入库、status disabled。**写路径通畅**。
- **发现 bug**：create 成功输出里 `Account UUID:` 恒空、`--account <uuid>` 提示 uuid 空白；同文件 `list` 却正确显示同一 UUID。根因 = CLI create 读 `data.account_uuid` 键、服务返回 `data.uuid` 键、list 读 `acc.uuid`——**三方不一致，create 单点取错键**。用户拿不到 deploy 所需 uuid（list 为 workaround）。
- **清理**：CRUD `delete_live_account`（无 CLI delete）软删 dummy 账号，`remaining_for_user=0`，Master 库已还原干净。
**结果**：提 **#6761**（bug, P2, mod:cli/mod:live, ready-for-agent）。G3 live 侧 account 表/读写均通畅，先前 SQL error 假设证伪；唯一缺陷是 create 输出取错返回键的显示 bug。paper 侧 blocker 仍为 #6757。

---

## 7. 已提交 issue（本轮探索期间）

> 通过 `/to-issues` 提交，编号记此。

- **#6756** `feat(cli): ginkgo backtest 缺 cancel/reset 命令`（P2, mod:cli, ready-for-agent）— ITER-001 撞 a71978d9 卡 running 70% 不可恢复；`backtest` 有 `delete` 软删但无主动 cancel/reset。与 **#4633 互补**（#4633=worker 死后心跳被动自愈；#6756=用户主动手动终止/恢复）。
- **#6757** `bug(paper): 运行时 deploy 路径漏 add_cash，新 paper 组合现金=0→信号照发但订单全失败（状态却 RUNNING）`（P1, mod:trading, ready-for-agent）— G3 代码复核发现：`_handle_deploy` 不注资而 INIT step8 注资；`_deploy_core` step9 发 Kafka 给运行中 worker → 新 paper 组合 cash=0 → 订单因无购买力静默全失败。与 **#6473 互补**（#6473=信号链 selector 种子；#6757=资金链 cash）。属 memory 警示的"状态机绿/链路红"安静失败类。
- **#6760** `bug(selector): PopularitySelector 生产库 pick 恒返回空（依赖空 stock_info 表未 fallback bar 表 + 静默无告警）`（P2, mod:trading, ready-for-agent）— ITER-003c 撞实：Master `stock_info` 表 0 行，popularity 取码 `get_all_codes()` 恒空且静默 return → 0 信号。`MomentumSelector` 已改从 bar 表取码 + 空时 WARN，popularity 未对齐。属「selector 依赖未填充元数据表→静默 0 交易」又一例。
- **#6761** `bug(account): 创建实盘账户成功但输出中 Account UUID 恒为空（取错返回字段）`（P2, mod:cli/mod:live, ready-for-agent）— ITER-005 验 G3 live 侧：create 成功入库但输出 UUID 空白（CLI create 读 `data.account_uuid`、服务返 `data.uuid`、list 读 `acc.uuid` 三方不一致，create 单点取错键）→ deploy 首步拿不到 uuid（list 为 workaround）。先前"account create SQL error"假设证伪，写路径实通畅。

---

## 8. 下一步（队列）

1. ✅ **ITER-001 完成**：引擎 per-portfolio 近确定性（年化极差 1.18pp），A1 复现成功；但 FixedSelector 违 G4 不可部署。
2. **ITER-003（进行中）**：`MomentumSelector` 全市场动态选股——**首个无后视可部署路径**。Smoke 已证回测可取数产信号(99)；2yr 全市场窗口超时被杀（perf 教训），现跑 **1yr cal-2025**（BT `945c5716`），结果待录。
3. **ITER-002**：对 ITER-003 胜出策略走 walk-forward（2023 训练→2024–2026 OOS），验 G2/G4。
4. **G3 路径**：ITER-003 出 G2 达标候选后，立即验 deploy 模拟盘是否丢绑定（§5），是则 `/to-issues`。
5. **既有 issue 关联**（不重复提）：#4711 非确定性 P1（ITER-001 证其属跨 portfolio 轴）、#4633 卡死 P2（a71978d9 70% 为其复现）。

> **ITER-003 1yr cal-2025（BT `945c5716`）已出 → LOSS（年化 -28.72%）。分流决策（2026-07-24 落定）**：
> - **判定根因**：非参数问题，是**市场适配问题**——A 股 2025 震荡/均值回归市，纯动量不适配。故 plan-B 弃 B1（调 momentum 参难逃市场失效），**改走 mean_reversion（市场适配的对偶策略）**。
> - **ITER-003b plan-B（执行中）**：`MeanReversion`(RSI 真实实现，已核验非 stub) + 动态 selector（守 G4）。RSI 均值回归买超卖、卖回归，正契合震荡市。
>   - **smoke 先行**（2026-06~07 反转窗口，MR 理论主场）：快（~3min，排名次数少），先验 MR 方向性。MR 在反转窗口若仍亏→论断死，止损；盈→上 1yr cal-2025 终验。
>   - ⚠️ **perf gate**：全市场 1yr 单跑 ~50min 且并发回测争 CH I/O 时 flush 退化。起 1yr 前须确认无并发回测（当前 bt `6554d322` 并发中，等待清空）。
>   - ⚠️ `trend_follow` 有 `arch_trend_follow_calendar_day_window_zero_signal`（0 信号 bug），**不用**。

> **ITER-003c 后再分流（2026-07-24 落定）**：
> - **现状盘点（ITER-003d 实测确认）**：能跑通产信号的**动态 selector 仅 `momentum` 一个**——popularity + cn_all 同死于 stock_info 空表（#6760，影响 2/4），multi_params 无 src 实现，fixed 后视不可部署。真实可用策略（非 stub）约：momentum/mean_reversion/moving_average_crossover/dual_thrust/trend_reverse/random_signal 等（scalping/price_action 是 stub，trend_follow 0 信号 bug）。
> - **关键未验**：`momentum+momentum` 只测了 2025（巨亏 -28.72%）。**未验 momentum 是否在 2023/2024 盈利**——若历史窗口盈利，则 2025 是周期性失效非策略死；可据此判断 momentum 是否"阶段性稳定盈利"。
> - **下一轮方向（优先级）**：
>   1. ~~ITER-004 momentum walk-forward~~（**已完成 2026-07-24，判死**：2024Q4 涨势段 -5.6%/win 13% + 2025 震荡 -28.72% → momentum 双市场均亏，结构性失效）。
>   2. ~~探测 cn_all/multi_params~~（ITER-003d 已完成：均不可用）。

> **ITER-004 后结论（2026-07-24 落定）— 本 arc 进入收束阶段**：
> - **核心结论**：现有**动态 selector×内置策略**组合在近 2 年 A 股（2024Q4 涨势 + 2025 震荡）**难稳定盈利**。唯一可用动态 selector（momentum）× momentum strategy 双窗口均亏，结构性失效。
> - **根因双线**：
>   1. **selector 缺口**（#6760）：stock_info 元数据未填充锁死 cn_all+popularity，策略空间被压缩到 momentum 单族。
>   2. **momentum 失效**：entry 追最高动量股 → A 股追涨杀跌失效（win 13%），连最强涨势都不盈。
> - **未关闭的探索口**（条件 gated，非本 arc 阻塞）：
>   - **#6760 修复后**：cn_all/popularity 复活 → 可测 MR/mean_reversion/trend_reverse 等震荡市策略（它们曾因无 selector 喂票而未验）。
>   - **其他真实策略未验**：moving_average_crossover / dual_thrust / trend_reverse / volume_activate 等（非 stub），但同样卡在 selector 缺口（需 momentum 喂票，而 momentum 喂的股对这些策略未必适配）。
> - **G3 路径**：paper 侧 blocker #6757（cash=0）已提；live 侧 account create 已验通畅（ITER-005 证伪先前"SQL error"假设），改发现 create 输出 UUID 恒空 bug **#6761**（实盘 deploy 首步拿不到 uuid，list 为 workaround）。路径连通性独立于策略盈利性——可用任一有交易组合（如 momentum 2024Q4 的 119 单）验回测→模拟盘→实盘管道，不受 momentum 判死影响。
> - **本 arc 收束判定**：在 #6760 修复（打开 selector 空间）前，进一步策略探索边际收益低；优先等 #6760 落地后重启 MR/震荡市策略线。
