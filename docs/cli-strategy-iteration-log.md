# CLI 策略迭代日志

> 目标：通过 ginkgo CLI 构建期望为正的稳定盈利策略，记录每次尝试和遇到的问题。

---

## 基线：ttt 配置复制验证

**Portfolio**: cli_verify_test (`b4fac5773a634db18fb233744fe47461`)
**时间**: 2026-05-07

### 配置（复制自 ttt）

| 类型 | 组件 | 参数 |
|---|---|---|
| strategy | random_signal_strategy | buy_prob=0.3, sell_prob=0.3 |
| selector | fixed_selector | codes=000001.sz |
| sizer | fixed_sizer | volume=150 |
| riskmanager | no_risk | - |

### 回测结果 (v1: verify_v1)

- **周期**: 2025-05-07 ~ 2026-05-07
- **PnL**: -1563.49
- **Sharpe**: -7.75
- **Win Rate**: 30.3%
- **Max Drawdown**: 1.74%
- **Signals**: 145, **Orders**: 111

**结论**: 随机信号策略，亏损，符合预期。

---

## 问题与不便记录

### 问题 1: `component create` 生成的 basic template 无参数定义

**现象**: 用 `ginkgo component create --type strategy --name xxx` 创建的组件，绑定后 WebUI 不显示 params。

**根因**: `basic` template 的源码没有 `__init__` 参数定义。API 层通过 `component_parameter_extractor` 解析源码提取参数名 → 空 dict → `config` 为空。

**影响**: CLI 创建的新组件在 WebUI 完全看不到参数，必须使用已有组件或手动编辑源码添加参数定义。

**建议**:
1. `component create` 应支持指定已有组件作为 template（clone 功能）
2. 或 `component create` 生成的 template 应包含示例参数定义
3. 或 API 层 fallback：当 `param_names` 为空时，用 `param_0`, `param_1`... 作为显示名

### 问题 2: Portfolio 列表 UUID 截断

**现象**: `ginkgo portfolio list` 显示的 UUID 被截断，无法直接复制使用。

**建议**: 添加 `--full-uuid` 选项，或在表格下方列出完整 UUID。

### 问题 3: mapping list 未实现

**现象**: `ginkgo mapping list` 提示 "Mapping listing not yet implemented"。

**影响**: 无法通过 CLI 查看组件绑定关系，只能通过 DB 查询。

### 问题 4: 回测缺少 selector 直接报错，错误信息不友好

**现象**: 绑定只有 strategy 没有 selector 时，回测失败报 `No selector found for portfolio`。

**建议**: 在 `backtest create` 阶段校验必要组件是否齐全，提前报错而非运行时失败。

### 问题 5: bind-component 参数传递不够直观

**现象**: `--param '0:"RandomSignalStrategy"' --param '1:0.3'` 格式需要知道参数的 index 位置。

**影响**: 用户需要查阅组件源码才能知道 index 对应什么参数。

**建议**: 支持命名参数如 `--param buy_probability=0.3`。

### 问题 6: backtest delete 需要交互确认

**现象**: `ginkgo backtest delete <uuid>` 需要手动输入 y/N，无法在脚本中自动执行。

**建议**: 添加 `--force` 或 `-y` 选项跳过确认。

### 问题 7: portfolio unbind-component 需要 --confirm

**现象**: 同上，需要 `--confirm` 但没有在 `--help` 中醒目提示。

---

## 迭代计划

### 方向 1: 调整随机策略参数
- 降低交易频率（降低概率）减少手续费损耗
- 调整仓位大小

### 方向 2: 使用技术指标策略
- moving_average_crossover 等趋势策略
- 需要确认是否有现成的均线策略组件可用

### 方向 3: 多股票分散
- selector 选多只股票分散风险

---

## 迭代 2: MA Crossover (name-only params)

**Portfolio**: ma_cross_v2 (`6480a050e8b6468182ef872c06893640`)
**时间**: 2026-05-07

### 发现: 策略动态加载 bug

**问题**: 传 numeric params 时实例化失败。
```
实例化组件失败: '<' not supported between instances of 'str' and 'int'
```
**根因**: `_instantiate_component` 从数据库读取 param values 均为 string，直接传给构造函数不做类型转换。
如 `MovingAverageCrossover("name", "20", "60", "1d")` → `short_period="20"` → 内部比较 `if self.short_period > 0` 时 str vs int 报错。

**Workaround**: 只传字符串参数（name），让数值参数使用默认值。
```bash
--param '0:"MovingAverageCrossover"'  # 只传 name，不传 short_period/long_period
```

### 回测结果 (ma_cross_v2, 2024-01-01~2026-05-07)

- **PnL**: 0（0笔交易）
- **原因**: 数据馈送器固定只返回 ~48 条 K 线，策略需要 60 条预热
- **557 个交易日全部 "数据不足"**

### 发现: 数据馈送器预热数据不足

**问题**: 数据库有 8335 条 000001.SZ 日K（1991~2026），但 data_feeder.get_bars() 只返回 48 条。
**影响**: 所有需要 >48 条历史数据的策略（MA、Bollinger 等）完全无法运行。
**可能根因**: data_feeder 的 lookback window 硬编码或配置限制。

---

## 迭代 3: MeanReversion (RSI 14)

**Portfolio**: mean_rev_v1 (`cb358f111e284c779d754bb26c4c58f7`)
**时间**: 2026-05-07

### 配置

| 类型 | 组件 | 参数 |
|---|---|---|
| strategy | mean_reversion | name="MeanReversion" (其余默认: rsi=14, oversold=30, overbought=70) |
| selector | fixed_selector | codes=000001.sz |
| sizer | fixed_sizer | volume=100 |
| riskmanager | no_risk | - |

### 回测结果 (mean_rev_v1, 2024-01-01~2026-05-07)

- **PnL**: 0（0笔交易）
- **原因**: RSI 计算失败 `unsupported operand type(s) for +: 'float' and 'str'`

### 发现: 数据层类型转换 bug

**问题**: bar data 的 close 等价格字段返回为 string 而非 float，导致 RSI 计算的算术运算失败。

---

## 迭代 4: TrendFollow / DualThrust / VolumeActivate

**Portfolio**: trend_v1, dual_thrust_v1, volume_v1
**时间**: 2026-05-07

### 回测结果

| 策略 | 加载 | 运行 | 交易 | 错误 |
|---|---|---|---|---|
| TrendFollow | ✅ | ❌ STRATEGY_FAILED | 0 | NoneType - timedelta |
| DualThrust | ✅ | ❌ STRATEGY_FAILED | 0 | NoneType - timedelta |
| VolumeActivate | ✅ | ❌ STRATEGY_FAILED | 0 | NoneType + timedelta |

### 发现: 时间戳字段为 None

**问题**: 数据馈送器返回的 bar 数据 timestamp 字段为 None，策略执行 `timestamp - timedelta()` 时报错。
**影响**: 所有需要时间计算的策略（突破、趋势）完全无法运行。

---

## 迭代 5: Scalping / PriceAction / Momentum

**Portfolio**: scalping_v1, price_action_v1, momentum_v1
**时间**: 2026-05-07

### 回测结果

| 策略 | 加载 | 运行 | 交易 | 错误 |
|---|---|---|---|---|
| Scalping | ❌ fallback RandomSignal | - | - | `BaseStrategy.__init__() takes 1-2 positional args but 3 were given` |
| PriceAction | ❌ fallback RandomSignal | - | - | 同上 |
| Momentum | ✅ | ✅ (无报错) | 0 | 多股排名策略，单股无信号 |

### 发现: 策略构造函数签名不兼容

**问题**: 部分 strategy 组件的 `__init__` 参数数量超过 `BaseStrategy.__init__` 的签名限制，导致 `*component_params` 传参失败。

---

## 总结: CLI 策略完整链路不可用

### 已测试 8 个策略，全部失败

| # | 策略 | 失败阶段 | 根因分类 |
|---|---|---|---|
| 1 | random_signal_strategy | 运行(亏损) | 随机策略，负期望 |
| 2 | moving_average_crossover | 运行(无交易) | 数据预热不足 |
| 3 | mean_reversion | 运行(计算失败) | 数据类型: float+str |
| 4 | trend_follow | 运行(计算失败) | timestamp=None |
| 5 | dual_thrust | 运行(计算失败) | timestamp=None |
| 6 | volume_activate | 运行(计算失败) | timestamp=None |
| 7 | scalping | 加载(实例化失败) | 构造函数签名不兼容 |
| 8 | price_action | 加载(实例化失败) | 构造函数签名不兼容 |
| 9 | momentum | 运行(无信号) | 设计用于多股排名 |

### 根因分析: 5 个系统性 bug

#### Bug 1: 参数类型不转换（严重）
- **位置**: `portfolio_service._instantiate_component` (line 1343)
- **现象**: `component_class(*component_params)` 传入的 params 全为 string
- **影响**: 所有含数值参数的策略实例化失败，fallback 到 RandomSignalStrategy
- **修复**: `component_params` 应根据目标构造函数的类型注解做 `int()`/`float()` 转换

#### Bug 2: 数据预热窗口不足（严重）
- **位置**: 数据馈送器的 lookback window
- **现象**: data_feeder.get_bars() 最多只返回 ~48 条，MA(60) 等长周期指标无法预热
- **影响**: 所有需要长历史数据的策略无法生成信号
- **修复**: 数据馈送器应支持可配置的 lookback 或预加载足够历史数据

#### Bug 3: Bar 数据 timestamp 为 None（严重）
- **位置**: 数据馈送器返回的 bar 对象
- **现象**: bar.timestamp 为 None，策略做时间运算时崩溃
- **影响**: 所有涉及时间计算的策略（突破、趋势）无法运行
- **修复**: 确保数据馈送器正确填充 timestamp 字段

#### Bug 4: Bar 数据价格字段为 string（严重）
- **位置**: 数据馈送器返回的 bar 对象
- **现象**: close/high/low/open 为 string 类型，算术运算失败
- **影响**: 所有需要价格计算的策略（RSI、均线等）无法运行
- **修复**: 确保数据馈送器将价格字段转为 float

#### Bug 5: 策略构造函数签名不兼容（中等）
- **位置**: 部分 strategy 组件的 `__init__` 参数
- **现象**: `BaseStrategy.__init__() takes 1-2 positional args but N were given`
- **影响**: 部分 strategy 组件无法实例化
- **修复**: 策略组件应使用 `**kwargs` 或对齐 BaseStrategy 签名

### 结论（迭代 2 更新）

通过利用 RandomSignalStrategy 的 `buy_prob=0.99, sell_prob=0.0, max_signals=20` 配置实现确定性早期建仓，配合 600000.SH（浦发银行）在 2024-2026 期间的上涨趋势，达到了年化 ~20% 的收益。

---

## 迭代 6: 收益最大化探索

**时间**: 2026-05-07

### 策略: 确定性早期建仓持有

利用 RandomSignalStrategy 的参数特性实现近似"买入持有"：
- `buy_prob=0.99`: 几乎每天生成买入信号
- `sell_prob=0.0`: 从不卖出
- `max_signals=20`: 20次信号后停止，等于在前20个交易日建仓
- `sizer=500`: 每次买入500股

**本质**: 确定性策略（非随机），等于期初一次性买入 10,000 股后持有。

### 回测结果

| 股票 | 周期 | Sizer | Max Signals | Final Value | 收益率 | 年化 |
|---|---|---|---|---|---|---|
| 000001.SZ | 2024-2026 | 300 | 20 | 109,631 | +9.6% | ~3.8% |
| 600000.SH | 2024-2026 | 200 | 30 | 127,831 | +27.8% | ~11.1% |
| 600000.SH | 2024-2026 | 500 | 20 | **146,975** | **+47.0%** | **~20.0%** |
| 000061.SZ | 2024-2026 | 200 | 20 | 111,657 | +11.7% | ~4.7% |

### 稳定性验证（spdb_max, 3次运行）

- Run 1: +46.0% (年化 ~19.5%)
- Run 2: +47.0% (年化 ~20.0%)
- Run 3: +46.0% (年化 ~19.5%)

**稳定性 100%**（确定性策略），**年化收益 ~20%**。

### 重要局限性

1. **非策略alpha**: 收益100%来自选股，策略本身无择时能力
2. **后视偏差**: 选择600000.SH是因为我们已知道它涨了56.8%
3. **非稳定盈利**: 如果选错股票（如000002.SZ -63.1%），会大幅亏损
4. **单一资产集中风险**: 全仓单只股票
5. **无法实时复制**: 未来哪只股票会涨是未知的

### 发现: 数据时区不一致 bug（Bug 6）

**问题**: 部分股票的 bar 数据 timestamp 带有 16:00 时区偏移。
- 000001-000005.SZ, 000032/000061.SZ, 600xxx.SH: `00:00:00` ✓
- 000006-000012.SZ: `16:00:00` ✗（UTC+8 时区偏移）

**影响**: BacktestFeeder 无法为时区偏移的股票生成价格事件，导致这些股票无法参与回测。
- 000007.SZ（+142%涨幅）因 此 bug 无法用于回测

### 发现: PositionRatioRisk 阻止所有交易（Bug 7）

**现象**: 使用 PositionRatioRisk 时，所有买入信号被阻止，0笔成交。
**建议**: 检查默认参数是否过于保守。

---

## 迭代 7: 策略泛化性验证

**时间**: 2026-05-07

### 跨周期跨股票验证

| 测试 | 股票 | 周期 | Final Value | 收益率 | 年化 |
|---|---|---|---|---|---|
| spdb_max | 600000.SH | 2024-2026 牛市 | 146,975 | +47.0% | ~20.0% |
| spdb_bear | 600000.SH | 2020-2022 熊市 | 63,014 | **-37.0%** | ~-17% |
| pab_bull | 000001.SZ | 2024-2026 牛市 | 116,180 | +16.2% | ~6.5% |
| pab_bear | 000001.SZ | 2021-2023 熊市 | 56,915 | **-43.1%** | ~-21% |

### 结论: 买入持有策略不"稳定"

- 熊市期间亏损 37-43%，牛市收益无法抵消熊市亏损
- 600000.SH 在 2020-2023 连续4年下跌（-22%, -12%, -15%, -8%），2024年才涨56%
- 任何固定的买入持有策略都无法实现跨周期"稳定盈利"
- 本质上：**无择时能力的策略无法实现稳定盈利**

---

## 最终总结

### 技术分析策略: 完全不可用
7个系统性 bug 阻断了所有技术分析策略的运行。无法通过 CLI 构建任何基于技术指标的策略。

### 买入持有策略: 不满足"稳定盈利"条件
- 牛市可盈利（+16%~+47%），但熊市大幅亏损（-37%~-43%）
- 完全依赖选股和市场周期，不具备策略稳定性
- 无法满足"稳定性80%以上"的条件（跨周期胜率远低于80%）

### 根本原因
CLI 策略链路存在两个不可逾越的障碍：
1. **技术分析策略链路完全断裂** — 7个 bug 导致所有技术指标策略无法运行
2. **唯一可用的随机策略无 alpha** — RandomSignalStrategy 不产生超额收益

要构建真正的"稳定盈利策略"，需要：
- 修复参数类型转换（Bug 1）→ 恢复策略动态加载
- 修复数据预热/类型/timestamp（Bug 2-4）→ 恢复策略运行
- 在此基础上才能开发和测试有择时能力的策略

### 系统性 bug 清单

| # | Bug | 严重性 | 影响范围 |
|---|---|---|---|
| 1 | 参数类型不转换 | 严重 | 所有非随机策略 |
| 2 | 数据预热窗口不足 | 严重 | 长周期指标策略 |
| 3 | Bar timestamp=None | 严重 | 时间相关策略 |
| 4 | Bar 价格为 string | 严重 | 价格计算策略 |
| 5 | 策略构造函数签名不兼容 | 中等 | 部分策略 |
| 6 | 数据时区不一致 | 严重 | 部分股票无法回测 |
| 7 | PositionRatioRisk 过度限制 | 中等 | 风控组件 |

### CLI 改进建议清单

| # | 建议 | 优先级 |
|---|---|---|
| 1 | backtest cat 展示关键指标（Sharpe、Win Rate 等） | 高 |
| 2 | 回测日志持久化到文件 | 高 |
| 3 | 错误信息不截断 | 高 |
| 4 | portfolio list 显示完整 UUID | 中 |
| 5 | mapping list 命令实现 | 中 |
| 6 | backtest/portfolio 批量清理 | 中 |
| 7 | bind-component 支持命名参数 | 中 |
| 8 | backtest create 校验必要组件 | 高 |

### 新发现的问题与不便

#### 问题 8: backtest cat 结果信息过于简略

**现象**: `ginkgo backtest cat` 只显示 `Final Value`，不显示 PnL、Sharpe、Win Rate 等关键指标。
**影响**: 无法直接评估策略表现。
**建议**: 增加关键指标展示（年化收益率、Sharpe、最大回撤、胜率、信号数、订单数）。

#### 问题 9: 回测日志不持久化到文件

**现象**: `ginkgo backtest run` 的日志输出到 stdout，需手动 `tee` 保存。
**影响**: 错误信息量大但容易丢失，排查问题困难。
**建议**: 回测日志自动保存到 `~/.ginkgo/logs/` 或任务关联目录。

#### 问题 10: 策略错误信息被截断

**现象**: Rich/structlog 的 ERROR 日志行被截断，如 `unsupported operand type(s) for +: 'float' and` 后面被截断。
**影响**: 难以确定具体错误原因。
**建议**: ERROR 级别日志不截断，或完整错误信息写入日志文件。

#### 问题 11: Portfolio/Backtest 清理不便

**现象**: 创建了大量测试 Portfolio 和 Backtest 后，没有批量清理命令。
**建议**: 添加 `ginkgo portfolio list --filter name=xxx` 和 `ginkgo backtest delete --filter` 批量操作。
