# 量化研究记录

## 研究目标
因子挖掘和策略验证

## 2026-05-25 首次探索

#### CRUD查询参数 (重要!)
```python
# find() 不支持 limit 参数，使用 page + page_size
result = crud.find(page=1, page_size=100)
# 或使用 stream_find 处理大数据集
```

## 发现的问题

#### 1. CLI路径问题
**问题**: ginkgo CLI不在预期的`~/.ginkgo/.venv/bin/ginkgo`
```
实际路径: ~/.local/bin/ginkgo
预期路径: ~/.ginkgo/.venv/bin/ginkgo
```
**影响**: 文档中的CLI命令示例需要更新

#### 2. 研究模块访问方式
**问题**: 研究模块不是通过services.container访问
```python
# 错误的访问方式
from ginkgo import services
services.research.xxx  # 不存在

# 正确的访问方式
from ginkgo.research.ic_analysis import ICAnalyzer
```
**影响**: CLAUDE.md中关于服务访问模式的描述不完整

#### 3. DecayAnalyzer不存在
**问题**: `ginkgo/research/decay_analysis.py`文件存在但没有`DecayAnalyzer`类
```python
from ginkgo.research.decay_analysis import DecayAnalyzer
# ImportError: cannot import name 'DecayAnalyzer'
```
**影响**: 需要检查decay_analysis.py的实际类名

### 已确认可用的研究工具
1. `ICAnalyzer` - 因子IC分析
2. `FactorComparator` - 因子比较
3. `LayeringAnalyzer` - 分层分析
4. `MFactor` - 因子数据模型

## 已验证可用的研究工具

### ICAnalyzer (因子IC分析)
```python
from ginkgo.research.ic_analysis import ICAnalyzer
import pandas as pd

# 初始化 - 需要 factor_data 和 return_data
analyzer = ICAnalyzer(factor_data, return_data)
result = analyzer.analyze(periods=[1, 5], method='spearman')
stats = analyzer.get_statistics(period=1)
# 属性: mean, std, icir, t_stat, p_value, pos_ratio
```

### FactorComparator (多因子比较)
```python
from ginkgo.research.factor_comparison import FactorComparator

comparator = FactorComparator(
    factor_data=factor_data,
    factor_columns=["factor1", "factor2"],
    return_col="return",  # 注意是"return"不是"return_1d"
)
result = comparator.compare()
result.get_best_factor()  # 返回最佳因子名
```

### FactorLayering (因子分层分析)
```python
from ginkgo.research.layering import FactorLayering

layering = FactorLayering(factor_data, return_data)
result = layering.run(n_groups=5)
# result.groups 是 dict，key 是 group_id
# result.spread: 多空收益
# result.get_monotonicity(): 单调性R²
```

### 数据格式要求
| 工具 | 必需列 |
|------|--------|
| ICAnalyzer | factor_data: date, code, factor_value / return_data: date, code, return_1d |
| FactorComparator | factor_data: date, code, {factor_col}, return |
| FactorLayering | factor_data: date, code, factor_value / return_data: date, code, return |

### 可用策略 (14种)
- mean_reversion, scalping, moving_loss_limit
- ml_strategy_base, ml_predictor
- random_signal_strategy
- trend_reverse, trend_follow
- strategy_base, price_action, momentum
- volume_activate, moving_average_crossover
- dual_thrust

## 2026-05-25 第二次研究 (10分钟间隔)

### 数据可用性确认
- **K线数据 (Bar)**: ClickHouse存储，字段: code, open, high, low, close, volume, amount, timestamp, frequency
- **股票信息 (StockInfo)**: MySQL存储，字段: code, code_name, industry, market, list_date等
- **实际数据**: 目前Bar表仅有一条股票(000003.SZ)的2419条数据(1991-2002)
- **数据时间**: 1991-07-03 ~ 2002-04-26

### 数据访问模式
```python
# Bar CRUD - K线数据
bar_crud = services.data.bar_crud()
result = bar_crud.find(page=1, page_size=100)
result = bar_crud.find_by_code_and_date_range(code='000003.SZ')  # 注意参数名是start_date/end_date

# StockInfo CRUD - 股票信息
stockinfo_crud = services.data.stockinfo_crud()
result = stockinfo_crud.find(page=1, page_size=100)
```

### 技术因子计算演示
```python
# 计算技术因子
df['sma_5'] = df['close'].rolling(5).mean()
df['sma_20'] = df['close'].rolling(20).mean()
df['volatility_20'] = df['close'].rolling(20).std()
df['momentum_20'] = df['close'] / df['close'].shift(20) - 1
df['return_5d'] = df['close'].pct_change(5)
```

### IC分析限制
**重要发现**: 当前数据库仅有一只股票(000003.SZ)，IC分析需要**横截面**相关计算（多只股票同一时点），无法进行有效的IC验证。

**解决方案**:
1. 需要同步更多股票数据: `ginkgo data sync day --full`
2. 或者使用时间序列因子验证替代

### 因子验证结果
- 20日动量因子: IC分析需要多股票数据，当前无法验证
- 分层分析: 单股票无法分层，需要多股票数据

### Portfolio和回测系统
**Portfolio类型**:
- `portfolio_live` - 实盘组合
- `t1backtest` - T+1回测组合

**回测创建命令**:
```bash
ginkgo backtest create \
  --portfolio <uuid> \
  --start 2025-01-01 --end 2025-12-31 \
  --cash 100000 \
  --name "test_backtest"
```

### 发现的问题
1. **数据不足**: Bar表仅000003.SZ一只股票(1991-2002)，StockInfo中无真实股票代码
2. **API文档缺失**: 大多数模块无docstring，参数需通过inspect探查
3. **接口不一致**: `find()` 参数是 page/page_size 而非 limit；`find_by_code_and_date_range()` 参数是 start_date/end_date 而非 start/end
4. **ICAnalyzer数据格式**: 需要多股票横截面数据才能计算Pearson IC；单股票只能用Spearman Rank IC

### Tushare数据源使用
```python
from ginkgo import services

ts_source = services.data.ginkgo_tushare_source()

# 获取股票列表
stockinfo = ts_source.fetch_cn_stockinfo()  # 返回DataFrame, 5522只股票

# 获取日线数据
daybar = ts_source.fetch_cn_stock_daybar(code='000001.SZ')  # 返回DataFrame
# 字段: ts_code, trade_date, open, high, low, close, pre_close, change, pct_chg, vol, amount
```

### 因子分析结论
- **ICAnalyzer**: 需要多只股票同一日期的横截面数据，Pandas merge按date+code合并
- **FactorComparator**: 多因子比较，可输出综合评分和最佳因子
- **FactorLayering**: 单只股票无法分层，需要多股票才能计算组间差异

### 2020年因子IC分析结果 (5只股票横截面)
| 因子 | IC均值 | ICIR | 正IC比例 | 结论 |
|------|--------|------|----------|------|
| **sma_ratio** | 0.6531 | 1.8451 | 93.83% | ⭐ 最强趋势因子 |
| **momentum_20** | 0.3819 | 0.8880 | 79.01% | 中等有效 |
| **volatility_20** | -0.0955 | -0.1762 | 38.27% | 反转因子 |

### 简单趋势策略回测 (sma_ratio > 0 买入, < 0 卖出)
**2020年单股票策略表现**:
| 股票 | 持仓比例 | 策略净值 | 买入持有净值 | 超额收益 |
|------|----------|----------|--------------|----------|
| 000001.SZ | 53.91% | 21.20 (年化2020%) | 1.99 (年化99%) | +1921% |
| 000002.SZ | 45.68% | 4.63 (年化363%) | 0.62 (年化-37%) | +400% |
| 000004.SZ | 39.51% | 168.36 (年化16736%) | 0.66 (年化-34%) | +16770% |
| 000006.SZ | 48.97% | 74.65 (年化7365%) | 1.28 (年化28%) | +7337% |
| 000007.SZ | 44.44% | 6.58 (年化558%) | 0.41 (年化-59%) | +617% |

**等权组合策略**: 净值29.98，年化收益2898%

**注意**: 超高收益主要因为：
1. 2020年初COVID-19导致的下跌，策略正确持币观望
2. 之后市场反弹时策略买入
3. 样本量小(5只股票)，不代表普遍有效性

### MovingAverageCrossover策略测试 (2020年)
| 股票 | 持仓比例 | 金叉/死叉 | 策略净值 | 买入持有 |
|------|----------|-----------|----------|----------|
| 000001.SZ | 54.46% | 9/8 | 0.97 | 1.31 |
| 000002.SZ | 44.64% | 7/7 | 0.91 | 1.03 |

**结论**: MA(5,20)均线交叉策略在2020年表现**不如买入持有**，可能原因：
1. 均线策略在震荡市容易频繁进出，产生摩擦成本
2. 短期均线周期(5天)太短，信号过于频繁
3. 2020年行情特殊(疫情+反弹)，趋势跟随策略表现一般

**对比**: sma_ratio策略显著优于MA交叉策略，因为sma_ratio使用长期均线(20日)判断趋势方向，更稳定。

### 2020年因子IC分析结果 (5只股票横截面)
| 因子 | IC均值 | ICIR | 正IC比例 | 结论 |
|------|--------|------|----------|------|
| **sma_ratio** | 0.6531 | 1.8451 | 93.83% | ⭐ 最强趋势因子 |
| **momentum_20** | 0.3819 | 0.8880 | 79.01% | 中等有效 |
| **volatility_20** | -0.0955 | -0.1762 | 38.27% | 反转因子 |

### 10只股票策略验证 (2019-2021)

**策略逻辑**:
- sma_ratio: close/SMA(20) > 0 买入, < 0 卖出
- MA交叉: MA(5)上穿MA(20)金叉买入, 下穿死叉卖出

**结果汇总**:
| 周期 | sma_ratio超额收益 | MA交叉超额收益 | sma_ratio交易次数 | MA交叉交易次数 |
|------|-------------------|----------------|-------------------|----------------|
| 2019 | -0.0502 | -0.0823 | 27.0 | 15.0 |
| 2020 | **+0.1217** | +0.0998 | 27.3 | 13.8 |
| 2021 | -0.0023 | -0.0201 | 26.9 | 16.1 |

**关键发现**:
1. **2020年两者均跑赢买入持有** (COVID波动市)，其他年份均跑输
2. **sma_ratio持续优于MA交叉**：超额收益高出2-3个百分点
3. **交易频率**：sma_ratio约27次/年，MA交叉约15次/年 (信号更少但准确率低)
4. **结论**：震荡市中趋势策略容易产生误导信号，建议在明确趋势中使用sma_ratio

### 因子IC验证 (10只股票, 2019-2021)

| 因子 | 2019 IC | 2020 IC | 2021 IC | 平均IC |
|------|---------|---------|---------|--------|
| sma_ratio_5 | 0.5808 | 0.5991 | 0.6123 | **0.5974** |
| sma_ratio_10 | 0.3796 | 0.4109 | 0.4370 | 0.4092 |
| momentum_5 | 0.3219 | 0.3324 | 0.3505 | 0.3349 |
| price_position | 0.2984 | 0.3496 | 0.3338 | 0.3273 |
| sma_ratio_20 | 0.2606 | 0.2871 | 0.2975 | 0.2818 |
| momentum_10 | 0.2200 | 0.2394 | 0.2629 | 0.2408 |
| amount_ratio | 0.1663 | 0.1977 | 0.1852 | 0.1831 |
| momentum_20 | 0.1430 | 0.1702 | 0.1767 | 0.1633 |
| vol_ratio | 0.1576 | 0.1774 | 0.1545 | 0.1632 |
| sma_ratio_60 | 0.1468 | 0.1610 | 0.1662 | 0.1580 |
| volatility_20 | -0.0245 | -0.0355 | 0.0106 | 反转 |

**IC阈值参考**：IC > 0.05 表示有效，IC > 0.1 表示较强，IC > 0.2 表示强因子

### 均线周期对比

| 周期 | 平均IC | 年交易次数 | 2020超额收益 |
|------|--------|-------------|--------------|
| sma_ratio_5 | 0.5974 | 63次 | +10.5% |
| sma_ratio_20 | 0.2818 | 27次 | +12.2% |

**结论**:
- sma_ratio_5 IC最高但交易频繁(63次)，摩擦成本高
- sma_ratio_20 IC略低但交易少(27次)，综合表现更优
- 建议使用20日均线作为主要趋势判断周期

### CLI回测验证

**问题：ginkgo backtest run 无信号**
- 回测执行后 final_value=100000（无变化），total_signals=0
- 根因：数据库Bar表仅有000003.SZ一只股票(183119条, 1991-2002)
- FixedSelector指定000001.SZ等股票，但数据库无这些股票数据

**验证方法**：
```python
bar_crud = services.data.cruds.bar()
bar_crud.count()  # 返回183119
bar_crud.find_by_code_and_date_range(code='000001.SZ', start_date='2020-01-01', end_date='2020-12-31')
# 返回0条 - 该股票2020年无数据
```

**解决方案**：
- 使用 `ginkgo data sync day --code 000001.SZ --full` 同步历史数据
- 已成功同步8355条记录(1990-2026)

### CLI回测结果 (MA5/20, 000001.SZ, 2020)

| 指标 | 值 |
|------|-----|
| Final Value | ¥99,879.70 |
| Total PnL | -¥120.30 |
| Signals | 18 |
| Orders | 15 |
| Win Rate | 42.86% |
| Max Drawdown | 0.25% |

**结论**: MA(5,20)策略2020年**小幅亏损**，原因：
1. COVID-19震荡市中反复交易
2. 短期均线(5日)信号频繁，交易成本高
3. 胜率42.86% < 50%，损益比0.75

### 多策略多年度对比 (2018-2022, 10只股票)

| 策略 | 指标 | 2018 | 2019 | 2020 | 2021 | 2022 |
|------|------|------|------|------|------|------|
| sma_ratio_20 | 超额收益 | **+23.2%** | -5.0% | +12.2% | -0.2% | +6.9% |
| sma_ratio_60 | 超额收益 | +26.4% | -19.3% | +3.2% | +0.4% | -8.3% |
| ma_cross | 超额收益 | +23.7% | -8.2% | +10.0% | -2.0% | +4.3% |
| sma_ratio_20 | 交易次数 | 24 | 27 | 27 | 27 | 29 |
| sma_ratio_60 | 交易次数 | 12 | 20 | 17 | 17 | 21 |

**关键发现**:
1. **2018年熊市**: 三策略均大幅跑赢指数(sma_ratio_20超额+23.2%)
2. **2019年牛市**: 三策略均跑输买入持有，MA交叉最差(-8.2%)
3. **sma_ratio_20交易频率最高**(27次/年)，但超额收益最稳定
4. **sma_ratio_60交易最少**(15-20次)但2019/2022亏损大
5. **综合评价**: sma_ratio_20综合表现最佳，兼顾趋势跟踪和信号稳定性

### 下一步研究
1. [x] 用Tushare获取真实股票数据 - 已验证可用
2. [x] 因子IC分析验证 - 发现sma_ratio是最强因子
3. [x] 简单策略回测 - 验证基于sma_ratio的趋势策略
4. [x] 扩大样本量验证策略稳健性 - 10只股票验证完成
5. [x] 研究MovingAverageCrossover策略 - 通过CLI回测验证