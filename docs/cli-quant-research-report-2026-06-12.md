# CLI 量化研究进展报告

**日期**: 2026-06-12  
**目标**: 尝试仅使用 `ginkgo` CLI 完成量化研究，直到找到可实盘盈利策略，或确认当前 CLI 工具链无法支撑该目标。  
**本轮结论**: 暂未找到可实盘盈利策略；当前 CLI 主链路存在多处高影响阻断，现阶段不能证明“仅靠 CLI 可稳定完成从数据探索到可交易策略验证”的目标。

## 本轮实际执行

### 1. CLI 与前置条件

执行:

```bash
ginkgo --help
ginkgo debug on
ginkgo status
```

结果:

- 文档/记忆中常见的 `ginkgo system config ...` 已失效，当前实际命令是 `ginkgo debug on`
- `ginkgo status` 显示 `Workers: 0`
- CLI 仍有大量噪音输出:
  - `GCONF Config cache updated`
  - `FUNCTION ... executed in ... seconds`

结论:

- CLI 文档与真实入口存在漂移
- 非 debug 研究场景下，日志噪音仍然很重

### 2. 数据探索

执行:

```bash
ginkgo data get stockinfo --code 000001.SZ
ginkgo data get day --code 000001.SZ --start 2020-01-01 --end 2020-01-10 --page-size 5
```

结果:

- `stockinfo --code 000001.SZ` 没有精确过滤，返回前 50 条股票
- `data get day` 对 `000001.SZ` 在显式历史区间内仍返回:

```text
No bar data found for 000001.SZ (2020-01-01-2020-01-10)
```

结论:

- CLI 数据探索层已经不可靠
- 用户无法仅靠 CLI 确认“某只股票在哪段时间有可用 K 线”

## 最小回测实验 A: fixed_selector

### 操作

```bash
ginkgo portfolio create --name cli_goal_probe_20260612 --capital 100000
ginkgo portfolio bind-component cli_goal_probe_20260612 fixed_selector --type selector
ginkgo portfolio bind-component cli_goal_probe_20260612 moving_average_crossover --type strategy
ginkgo portfolio bind-component cli_goal_probe_20260612 fixed_sizer --type sizer
ginkgo portfolio bind-component cli_goal_probe_20260612 no_risk --type riskmanager
ginkgo backtest create --portfolio ef9dd88272844accaa2b7aef228b1f95 --start 2024-01-01 --end 2024-03-31 --name cli_goal_probe_bt --cash 100000
ginkgo backtest run f140c5c1ac414e56a50278ca1a46d37e
```

### 观察

回测引擎日志显示:

```text
No params found for FixedSelector, attempting instantiation with defaults
Selector has no interested codes or _interested attribute
Published interest update for 0 symbols: []
BacktestFeeder: No interested symbols at 2024-01-22
```

同时:

- `backtest cat` 在运行时仍显示 `Progress: 0%`
- 任务状态显示存在滞后/不一致

### 结论

- 这条“最小工作流”表面成功，实际是**静默零股票池**
- 用户如果按最直觉方式绑定默认 selector，会得到一个不会交易的回测，但 CLI 不会在前台直接阻止

## 最小回测实验 B: cn_all_selector

### 操作

```bash
ginkgo portfolio create --name cli_goal_probe_cnall_20260612 --capital 100000
ginkgo portfolio bind-component cli_goal_probe_cnall_20260612 cn_all_selector --type selector
ginkgo portfolio bind-component cli_goal_probe_cnall_20260612 moving_average_crossover --type strategy
ginkgo portfolio bind-component cli_goal_probe_cnall_20260612 fixed_sizer --type sizer
ginkgo portfolio bind-component cli_goal_probe_cnall_20260612 no_risk --type riskmanager
ginkgo backtest create --portfolio 2c4a5d7dd012438483cebe3aabeacbcb --start 2024-01-01 --end 2024-01-15 --name cli_goal_probe_cnall_bt --cash 100000
ginkgo backtest run f37a94cdd9b842e2b95bfcfd7aeb6fd4
```

### 观察

日志先显示:

```text
No params found for CNAllSelector, attempting instantiation with defaults
Selector has no interested codes or _interested attribute
```

随后 feeder 开始对大量股票报:

```text
BacktestFeeder: No bar data for 301063.SZ at 2024-01-03
BacktestFeeder: No bar data for 301065.SZ at 2024-01-03
...
```

特点:

- 不是少量告警，而是成千上万条
- 说明“全市场 selector + 当前数据层”会把研究过程变成日志洪水
- 即使缩短到 15 天窗口，CLI 仍然很难作为高效研究工具使用

### 结论

- `cn_all_selector` 也没有提供开箱即用的稳定研究体验
- 数据覆盖、selector 默认行为、日志治理三者同时失控

## 本轮新增确认的问题

1. **CLI 入口/文档漂移**
   - `ginkgo system config ...` 不再可用
   - 现有项目文档仍在引用旧命令

2. **数据查询不可信**
   - `stockinfo --code` 过滤失效
   - `data get day` 对常见股票历史区间返回无数据

3. **最小回测工作流会静默失败**
   - `fixed_selector` 默认无股票池
   - `cn_all_selector` 默认行为也不可靠

4. **回测任务状态展示错误**
   - 运行中/已完成任务长期显示 `Progress: 0%`

5. **日志噪音和告警洪水严重影响研究效率**
   - 性能日志、缓存日志默认外露
   - 全市场回测时“无 bar 数据”逐股票刷屏

6. **结果发现能力不足**
   - `ginkgo compare top` 不提供“全局 top”，必须先手工提供回测 ID
   - 不利于从海量历史任务中发现候选盈利策略

## 候选历史组合复跑验证

本轮没有继续盲目新建策略，而是优先复跑已有命名组合，验证 CLI 是否至少能稳定复现“历史上看起来不错”的已有配置。

### 1. `r118_ma_cross`

- 组合详情显示策略参数明确存在:
  - selector: `fixed_selector("600000.SH")`
  - strategy: `moving_average_crossover(5, 20)`
- 验证任务:
  - `12789d36a9634c2ea39cc487abe0bba6` (`2024-01-01 ~ 2024-03-31`)

结果:

- `backtest cat` 仍显示:
  - `Status: running`
  - `Progress: 0%`
- 但 `result show` 已经能读到 analyzer 记录，说明**状态层与结果层不一致**
- `annualized_return` 末值约:
  - `2024-03-31 -> 0.00079301`
- `order_count` 末值:
  - `1`
- `profit` 末几日仅有零星个位数波动:
  - `2024-03-29 -> -6`
  - `2024-03-27 -> 3`

结论:

- 该组合至少不是零交易
- 但收益极小、交易极少，完全不足以支持“可实盘盈利策略”的结论

### 2. `growth_trend`

- 验证任务:
  - `a328729ea52444e9a6caa2dbc0936b71` (`2024-01-01 ~ 2024-03-31`)

结果:

- `annualized_return` 持续为 `0`
- `order_count` 持续为 `0`
- `profit` 持续为 `0`

结论:

- 该组合在当前 CLI 链路下等价于**无交易回测**
- 即使结果表中不断积累 analyzer 记录，也没有产生实际交易行为

### 3. `bluechip_mac`

- 验证任务:
  - `47557676140e462eb462216cfac5fa0a` (`2024-01-01 ~ 2024-03-31`)
- 追加短窗任务:
  - `9a45fd036ad742e4b9f59f2c8055f03f` (`2024-01-01 ~ 2024-01-31`)

阶段性结果:

- `result show` 已出现记录，说明引擎在推进
- `annualized_return` 早期记录为正:
  - `2024-01-24 -> 0.03680025`
- `order_count` 早期记录为:
  - `1`
- `profit` 在相邻几日剧烈来回:
  - `2024-01-24 -> 121.5`
  - `2024-01-25 -> -126`

结论:

- 该组合目前只能证明“有交易、会波动”
- 还不能证明最终为正收益，更不能证明可实盘

## 本轮新增高影响阻断

### 1. 投资组合参数在回测装配时丢失

这是本轮最严重的新证据。

先看组合定义:

- `ginkgo portfolio get r118_ma_cross --details` 清楚显示:
  - `moving_average_crossover`
  - `[1]: 5`
  - `[2]: 20`

但短窗复跑 `b864941ba27e4ed38c08bd66a8e73213` 的引擎装配日志却显示:

```text
MovingAverageCrossover: 初始化金叉死叉策略 (短期=20, 长期=60, 频率=1d)
```

这意味着:

- 组合里存着 `5/20`
- 回测运行时却实例化成默认 `20/60`

结论:

- CLI 现阶段**不能可靠复现已保存的策略参数**
- 因此即便某个历史组合名义上“表现不错”，当前 CLI 复跑结果也不可信，因为跑的可能根本不是原策略

### 2. `result show --mode terminal` 依赖未自动处理

执行 analyzer 展示时，CLI 会报:

```text
Terminal chart failed: Missing required dependency
plotext package not found.
解决方案: pip install plotext
```

问题在于:

- `--help` 默认示例直接展示 `--mode terminal`
- 但默认环境下该模式并不可用

结论:

- 结果展示链路存在隐藏运行时依赖
- 用户在“按帮助正常使用”时会直接踩坑

## 本轮已完成修复与回归验证

在继续“只用 CLI 做量化研究”之前，本轮对两条最核心的阻断做了代码修复，并用真实 CLI 再验证了一次。

### 1. 修复：旧 Portfolio 参数被错位解释

根因最终确认不是单一问题，而是两个缺陷叠加：

1. `ComponentParameterExtractor` 对 `moving_average_crossover -> MovingAverageCrossover` 这类 `snake_case -> CamelCase` 名称匹配失败，导致参数名提取返回空字典
2. 在拿不到参数名时，`ComponentLoader` 只能走 positional 调用；旧索引 `[1]=5, [2]=20` 会被当成:
   - `name=5`
   - `short_period=20`
   - `long_period` 保持默认 `60`

这也是为什么之前日志出现的是：

```text
5: 初始化金叉死叉策略 (短期=20, 长期=60, 频率=1d)
```

本轮修复后，再次验证 `moving_average_crossover` 的参数提取结果：

```text
{0: 'short_period', 1: 'long_period', 2: 'frequency'}
```

随后重新运行短窗任务:

- `21fea4e68bb5450283454a373a1ba6c5`

运行日志已变为:

```text
MovingAverageCrossover: 初始化金叉死叉策略 (短期=5, 长期=20, 频率=1d)
```

结论:

- `r118_ma_cross` 现在终于在 CLI 回测链路里使用了正确的 `5/20` 参数
- “保存的策略参数被静默替换成默认值”的关键阻断已得到代码层修复和 CLI 级验证

### 2. 修复：CLI 本地回测进度始终显示 `0%`

根因确认：

- `TimeControlledEventEngine` 只有拿到 `progress_callback` 才会写回进度
- 但 `backtest_cli -> BacktestOrchestrator -> EngineAssemblyService` 这条 CLI 执行链，原先没有把回调往下传

本轮修复后：

- CLI 运行时会通过 `BacktestTaskService.update_progress()` 持续写回:
  - `progress`
  - `current_stage`
  - `current_date`
- 任务完成时显式写回 `100%`

验证任务同样使用:

- `21fea4e68bb5450283454a373a1ba6c5`

`ginkgo backtest cat` 结果已显示:

```text
Status:   completed
Progress: 100%
Completed: 2026-06-12 03:32:07
```

结论:

- “CLI 本地回测永远是 running/0%” 这条主路径阻断已在当前环境中被修通

### 3. 自动化回归

使用项目虚拟环境执行:

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 /home/kaoru/.ginkgo/.venv/bin/python -m pytest \
  -o required_plugins='' -o addopts='' \
  tests/unit/data/services/test_parameter_extractor_skip_name.py \
  tests/unit/trading/services/test_component_loader_param_compat.py \
  tests/unit/trading/services/test_backtest_orchestrator.py \
  tests/unit/services/smoke/test_component_parameter_extractor_smoke.py -q
```

结果:

```text
24 passed, 1 warning in 0.78s
```

说明:

- warning 来自 `pyproject.toml` 中 `timeout` 配置依赖未加载，并非本轮修复失败
- 至少本轮新增回归都已稳定通过

## 修复后策略复跑（进行中）

在参数链与进度链修复后，本轮重新发起了 3 个 `2024Q1` 验证任务：

- `ee141756dcf14f93bcc52b9c6367ccb7` -> `r118_ma_cross`
- `73f75d5eeb054a9b9286462e8d433632` -> `bluechip_mac`
- `9d2865b9a8fe4d76829d8503df2fe67c` -> `growth_trend`

### 当前阶段性观察

1. `r118_ma_cross`

- 运行日志已确认使用正确参数:

```text
MovingAverageCrossover: 初始化金叉死叉策略 (短期=5, 长期=20, 频率=1d)
```

- `backtest cat` 进度已推进到:
  - `26%`
- `order_count` 已出现非零:
  - `2024-02-13 -> 1`
- 但当前截面 `profit` 仍接近 0:
  - `2024-02-14 ~ 2024-02-10 -> 0`

阶段结论:

- 这条组合至少已经证明“正确参数 + 真实交易”成立
- 但截至当前截面，尚未证明存在有意义收益

2. `bluechip_mac`

- 组合详情中策略绑定本来就没有自定义参数展示，因此当前应视为**默认参数版本的均线组合**
- 运行日志显示仍按默认参数实例化:

```text
MovingAverageCrossover: 初始化金叉死叉策略 (短期=20, 长期=60, 频率=1d)
```

- `backtest cat` 进度已推进到:
  - `15%`
- `order_count` 已出现非零:
  - `2024-01-27 -> 1`
- `profit` 有明显波动:
  - `2024-01-26 -> 174`
  - `2024-01-25 -> -126`
  - `2024-01-24 -> 121.5`
  - `2024-01-23 -> 156`

阶段结论:

- `bluechip_mac` 不是零交易假回测
- 但它当前只是“默认参数的蓝筹篮子 MA 组合”，不能再误当成精确定义的历史优化策略
- 是否最终为正收益，仍需等待完整窗口跑完

3. `growth_trend`

- 组合详情同样没有展示策略参数
- 运行日志按默认方式实例化 `trend_follow`
- `backtest cat` 已推进到:
  - `68%`
- 但到 `2024-03-03` 这一截面仍然:
  - `order_count = 0`
  - `profit = 0`
  - `annualized_return = 0`

阶段结论:

- `growth_trend` 在修复后的 CLI 链路下依旧基本等价于**无交易回测**

### 当前更新后的判断

修复后，问题已经从“CLI 会不会把策略跑错 / 会不会永远卡 0%”收敛为更明确的策略分层：

- `r118_ma_cross`: 正确参数、存在真实交易，但暂未证明有意义收益
- `bluechip_mac`: 默认参数下存在真实交易和盈亏波动，但尚未完成窗口验证
- `growth_trend`: 仍然无交易，当前可基本排除

这说明：

- CLI 主链路可信度比修复前明显提升
- 但“找到可实盘盈利策略”仍未达成
- 接下来应优先等待 `r118_ma_cross` 与 `bluechip_mac` 完整窗口结果，而不是再继续扩大量级

## 修复后策略复跑（已完成的 Q1 结论）

截至目前，3 个 `2024Q1` 验证任务已有 2 个完成、1 个明确排除：

### 1. `r118_ma_cross` (`ee141756dcf14f93bcc52b9c6367ccb7`)

这是修复后最可信的“正确参数复跑”样本，因为运行日志已确认使用:

```text
MovingAverageCrossover: 初始化金叉死叉策略 (短期=5, 长期=20, 频率=1d)
```

最终结果:

- `Status: completed`
- `Final Value: 99990.5000`
- `Total PnL: -9.5000`
- `Annual Return: -0.0003`
- `Max Drawdown: 0.0001`
- `Sharpe Ratio: -189.3520`
- `Signals: 4`
- `Orders: 2`

同时 analyzer 末值也一致:

- `annualized_return(2024-03-31) = -0.00026896`
- `order_count(2024-03-31) = 2`
- `profit(2024-03-29) = -9.5`

结论:

- 这条策略已经可以排除
- 它证明了“修复后的 CLI 可以正确复跑参数”
- 但不能证明该策略盈利

### 2. `growth_trend` (`9d2865b9a8fe4d76829d8503df2fe67c`)

最终结果:

- `Status: completed`
- `Final Value: 100000.0000`
- `annualized_return(2024-03-31) = 0`
- `order_count(2024-03-31) = 0`
- `profit(2024-03-31) = 0`

CLI 直接给出:

```text
⚠️ No trades generated — selector may have returned empty symbols.
```

结论:

- 这条组合在当前 CLI 链路下是完整窗口零交易
- 可以明确排除

### 3. `bluechip_mac` (`73f75d5eeb054a9b9286462e8d433632`)

这条组合的一个重要前提是：

- 组合详情中**没有**展示策略参数
- 因此当前应视为**默认参数**的蓝筹篮子均线策略
- 运行日志也确认使用默认:

```text
MovingAverageCrossover: 初始化金叉死叉策略 (短期=20, 长期=60, 频率=1d)
```

但它是本轮第一个完整跑出正收益的真实样本。

最终结果:

- `Status: completed`
- `Final Value: 102931.0000`
- `Total PnL: 2930.5900`
- `Annual Return: 0.0852`
- `Max Drawdown: 0.0090`
- `Sharpe Ratio: 1.5517`
- `Signals: 5`
- `Orders: 4`

末值 analyzer 也匹配:

- `annualized_return(2024-03-31) = 0.08522326`
- `order_count(2024-03-31) = 4`
- `profit(2024-03-29) = 28.5`

结论:

- `bluechip_mac` 是当前第一条**真实交易 + Q1 正收益**的候选组合
- 但它还不能直接升级为“可实盘盈利策略”
- 因为它目前只在单一窗口、且基于默认参数版本得到正结果

## 紧接着的相邻窗口复验

为了避免只凭单季度就下结论，已立即发起:

- `38e9e195c4934b6e94eeb4c4a657dc7c`
- 任务名: `verify_bluechip_q2_after_fix_20260612`
- 区间: `2024-04-01 ~ 2024-06-30`

当前已确认:

- 任务已成功启动
- 仍按默认 `20/60` 参数运行
- CLI 进度更新链正常

## 当前最保守且最可靠的结论

截至本报告这一刻：

- 还**不能**宣称已经找到“可实盘盈利策略”
- 但也**不能**再说“CLI 完全跑不出可信候选”

更准确的说法是：

- `r118_ma_cross`: 可正确复跑，但为负收益
- `growth_trend`: 完整零交易，排除
- `bluechip_mac`: 默认参数版本在 `2024Q1` 为正收益，是当前唯一值得继续验证的候选

因此下一步的重点不再是继续广撒网，而是：

1. 完成 `bluechip_mac` 的 Q2 复验
2. 如果 Q2 仍为正，再继续做更长窗口或更早窗口验证
3. 只有连续多个窗口都维持正收益，才有资格讨论“可实盘盈利”

## 对目标的当前判断

截至本轮，**还不能确认仅靠 CLI 工具链可以稳定达成“找到可实盘盈利策略”**。  
原因不是“暂时没跑出盈利策略”这么简单，而是：

- 数据探索命令本身已不可靠
- 默认组件组合会静默产出零交易
- 全市场实验被数据缺失和日志洪水淹没
- 结果发现能力仍不足，难以高效筛选候选策略

在这个前提下，当前最接近“正收益候选”的 `r118_ma_cross` 和 `bluechip_mac` 也只能说明:

- CLI 偶尔能产出少量非零结果
- 但这些结果还不足以证明策略有效
- 虽然 `r118_ma_cross` 的参数复跑可信度已恢复，但样本仍过短、交易仍过少

换言之，当前更像是“研究工具链本身还在修”，而不是“可以进入稳定找 alpha 的阶段”。

## 下一步建议

优先级从高到低:

1. 修复 `stockinfo --code` 与 `data get day` 的可信度
2. 给 selector/sizer/risk 的默认参数缺失提供前台硬错误，而不是静默 fallback
3. 修复 `stockinfo --code` 与 `data get day` 的可信度
4. 抑制非 debug 噪音日志
5. 补齐 `result show --mode terminal` 依赖处理或回退机制
6. 为 `compare top` / `result list` 增加可发现性，支持直接从全量历史中筛选最佳回测
7. 在修复后的 CLI 上重新验证 `r118_ma_cross`、`bluechip_mac`、以及更多历史组合的完整窗口表现
8. 只有在上述问题继续缓解后，才值得继续大规模 CLI 策略搜索

## Q2 复验最终结果更新

更新时间: `2026-06-12 03:42:04 CST`

`bluechip_mac` 相邻窗口复验任务 `38e9e195c4934b6e94eeb4c4a657dc7c` 已完成:

- 区间: `2024-04-01 ~ 2024-06-30`
- `Status: completed`
- `Final Value: 99398.0000`
- `Total PnL: -602.0000`
- `Annual Return: -0.0170`
- `Max Drawdown: 0.0061`
- `Sharpe Ratio: -10.4877`
- `Signals: 8`
- `Orders: 2`

补充 analyzer 末端观察:

- `annualized_return(2024-06-15) = -0.01778258`
- `order_count(2024-06-15) = 2`
- `profit(2024-06-16) = 0`

结论更新:

- `bluechip_mac` 虽然在 `2024Q1` 为正收益，但在紧邻的 `2024Q2` 已转为负收益
- 因此它不能升级为“跨窗口稳定盈利候选”
- 到目前为止，CLI 侧仍然**没有**发现一个足够可信、可继续朝实盘盈利推进的策略

## 动态选股新一轮验证

为了避免继续被历史脏组合误导，额外新建了两条**参数显式落库**的动态研究组合：

1. `qr_dyn_momsel_mom_20260612`
   - portfolio: `1dac88015f9f470a8af4bcd2666dbcf9`
   - selector: `momentum_selector(5, 5, 20)`
   - strategy: `momentum(20, 0.02, 1d)`
   - sizer: `fixed_sizer(100)`
   - risk: `no_risk`
2. `qr_dyn_pop_ma_20260612`
   - portfolio: `595130b6a4d24574bebc021e46662759`
   - selector: `popularity_selector(10, 30)`
   - strategy: `moving_average_crossover(20, 60, 1d)`
   - sizer: `fixed_sizer(100)`
   - risk: `no_risk`

对应 `2025H1` 回测任务:

- `0b7814cbde3c4d0da247991277ac0811` -> `qr_dyn_momsel_mom_h1_2025`
- `e1e4db0b703844d680ac92c979d51f07` -> `qr_dyn_pop_ma_h1_2025`

当前观察结果（`2026-06-12 03:48 CST`）:

- `0b7814cb...` 仍在运行，`Progress: 1%`
- `e1e4db0b...` 仍在运行，`Progress: 11%`
- 两者都已能持续产出 analyzer 记录，说明链路不是“假启动”
- 但截至当前截面，两者 `order_count` 仍为 `0`

这轮验证新增了三个非常实际的问题：

1. `backtest create` 只会**创建任务**，不会自动执行  
   - 还必须额外手动跑 `ginkgo backtest run <task_id>`
   - 对批量研究非常不友好，也容易误判成“命令已开始回测”

2. `result list` 依然不可用于全局筛选  
   - `ginkgo result list --help` 已存在，但实际执行仍返回:
   - `Result listing not yet implemented`
   - 同时仍伴随 `-p` 参数重复告警

3. 动态 selector 的研究吞吐明显不足  
   - `momentum_selector` 半年窗口在本地跑了数十秒后仍只到 `1%`
   - `popularity_selector` 同期只推进到 `11%`
   - 即使功能正确，也很难支撑高频迭代式的 CLI 策略研究

截至这一步，CLI 的情况更接近：

- 可以跑通“显式参数 + 动态选股”的真实研究链路
- 但执行成本仍然过高
- 而且尚未证明这些更接近实盘的组合能产生稳定交易，更谈不上稳定盈利

## 动态选股进一步观察

在继续轮询后，动态组合出现了更明确的中间证据：

### 1. `momentum_selector + momentum`

运行中任务:

- `0b7814cbde3c4d0da247991277ac0811`
- 名称: `qr_dyn_momsel_mom_h1_2025`
- 区间: `2025-01-01 ~ 2025-06-30`

截至 `2026-06-12 03:49 CST` 已确认:

- `Progress: 3%`
- `order_count(2025-01-05 ~ 2025-01-07) = 3`
- `annualized_return(2025-01-05) = -0.00836523`
- `annualized_return(2025-01-06) = -0.03710542`
- `annualized_return(2025-01-07) = -0.04195278`

这说明：

- 它已经不是“零交易假研究”
- CLI 的动态 selector + 动量策略链路能真实出单
- 但当前看到的第一个有交易截面就是负收益

### 2. `popularity_selector + moving_average_crossover`

运行中任务:

- `e1e4db0b703844d680ac92c979d51f07`
- 名称: `qr_dyn_pop_ma_h1_2025`
- 区间: `2025-01-01 ~ 2025-06-30`

截至 `2026-06-12 03:49 CST` 已确认:

- `Progress: 17%`
- `order_count(2025-01-29 ~ 2025-01-31) = 1`
- `annualized_return(2025-01-29) = -0.00046656`
- `annualized_return(2025-01-30) = -0.00044991`
- `annualized_return(2025-01-31) = -0.00043439`

这说明：

- 这条链路也已经产生真实订单
- 但到首个有成交的截面仍是轻微负收益

## 月窗口吞吐验证

为了确认“慢”到底是不是因为半年窗口太长，又补建并启动了两条 `2025-01` 月窗口任务：

- `f5a6bf4ead4143d383d45b93e22de1d7` -> `qr_dyn_momsel_mom_jan_2025`
- `e6a497183dc04d5d9d8133c439d42584` -> `qr_dyn_pop_ma_jan_2025`

截至 `2026-06-12 03:51 CST`:

- `f5a6bf4e...` 仍在运行，`Progress: 10%`
- `e6a49718...` 仍在运行，`Progress: 30%`

同时已确认：

- `f5a6bf4e...` 截至 `2025-01-04` 仍无成交
- `e6a49718...` 截至 `2025-01-10` 仍无成交

这轮验证给出的结论更清晰：

- 把窗口从半年缩到 1 个月，确实会更快
- 但即便是月窗口，动态 selector 回测仍然明显偏慢
- 因此当前 CLI 的主要限制之一，不只是策略是否赚钱，而是**动态选股研究吞吐过低**

## 当前阶段判断再收敛

截至本轮：

- `bluechip_mac` 已被 Q2 复验淘汰
- 两条新建动态组合都已证明“能真实出单”
- 但当前观察到的首批真实交易截面，收益都为负
- 更短月窗口也没有把研究效率提升到可高频迭代的程度

所以当前最保守的判断是：

- CLI 已不再是“完全跑不通量化研究”
- 但它仍然**没有**提供足够高效、足够稳定的研究环境来支撑“持续寻找可实盘盈利策略”

## 最新轮询补充

截至 `2026-06-12 03:53 CST`，四个动态任务进一步推进为：

- `0b7814cbde3c4d0da247991277ac0811` (`qr_dyn_momsel_mom_h1_2025`)
  - `Status: running`
  - `Progress: 7%`
- `e1e4db0b703844d680ac92c979d51f07` (`qr_dyn_pop_ma_h1_2025`)
  - `Status: running`
  - `Progress: 27%`
- `f5a6bf4ead4143d383d45b93e22de1d7` (`qr_dyn_momsel_mom_jan_2025`)
  - `Status: running`
  - `Progress: 10%`
- `e6a497183dc04d5d9d8133c439d42584` (`qr_dyn_pop_ma_jan_2025`)
  - `Status: running`
  - `Progress: 70%`

其中最值得注意的是月窗口任务 `e6a49718...`：

- 到 `2025-01-22` 为止，`order_count = 0`
- 到 `2025-01-22` 为止，`annualized_return = 0`
- 到 `2025-01-23` 为止，`profit = 0`

这进一步强化了两个判断：

1. 月窗口确实比半年窗口快  
   - `popularity_selector + MA` 的月窗口已到 `70%`
   - 同组合的半年窗口仍只有 `27%`

2. 但“更快”仍不足以支撑高频研究  
   - 即便是 1 个月窗口，动态 selector 回测依然需要较长等待
   - 而且跑到窗口后段之前，往往拿不到任何交易或收益反馈

因此当前 CLI 的真实状态更接近：

- 可以做“低频、长等待”的实验
- 但不适合靠快速迭代去搜索实盘级盈利策略

## 首个动态月窗口完整结果

截至 `2026-06-12 03:54 CST`，`popularity_selector + moving_average_crossover` 的月窗口任务已经完整结束：

- 任务: `e6a497183dc04d5d9d8133c439d42584`
- 名称: `qr_dyn_pop_ma_jan_2025`
- 区间: `2025-01-01 ~ 2025-01-31`
- `Status: completed`
- `Final Value: 99995.0000`
- `Total PnL: -5.0000`
- `Annual Return: -0.0004`
- `Max Drawdown: 0.0001`
- `Sharpe Ratio: -206.4880`
- `Signals: 6`
- `Orders: 1`

对应末端 analyzer 也一致：

- `order_count(2025-01-31) = 1`
- `annualized_return(2025-01-31) = -0.00043439`
- `profit(2025-01-29) = -5`
- `max_drawdown(2025-01-31) = -0.00005`

这条结果非常关键，因为它同时说明了三件事：

1. 这不是“零交易假回测”  
   - 任务确实出过单
   - 不是因为 selector 为空或任务没真正执行

2. 它也不是盈利候选  
   - 完整月窗口最终为负收益
   - 而且只有 `1` 笔订单，样本极薄

3. CLI 研究吞吐问题依旧存在  
   - 即使只是 `1` 个月窗口，也仍然跑了几分钟才收敛
   - 对真实量化研究而言，试错成本依然偏高

因此可以把 `qr_dyn_pop_ma_jan_2025` 明确归类为：

- **真实运行成功**
- **真实有交易**
- **但不可作为盈利策略候选**
