# A 股日级纸上交易设计

> 日期：2026-03-30
> 分支：016-a-stock-paper-trading
> 状态：设计阶段

---

## 1. 目标

打通"回测 → 纸上交易"飞轮，让策略用真实 A 股行情进行日级验证。

核心思路：纸上交易 = "每天推进一格"的回测引擎，数据源从历史数据切换为当日真实数据。

## 2. 架构

### 2.1 整体流程

```
15:30 收盘
  │
  ▼
DailyDataFetcher (从 Tushare 拉取当日 OHLCV)
  │
  ▼
TimeControlledEventEngine (mode=PAPER, timer_interval=1day)
  │
  ├── PriceUpdate → Strategy.cal() → Signal
  │                                    │
  │                              _signals 队列 (T+1 延迟)
  │                                    │
  │                              (次日 advance_time 发送)
  │                                    │
  ├── SimBroker.execute() → Fill (市价/限价)
  │
  ├── T+1 结算 (Position.process_settlement_queue)
  │
  └── Analyzer 记录 (NetValue 等)
```

### 2.2 现有组件复用

| 组件 | 文件 | 纸上交易中的角色 |
|------|------|-----------------|
| TimeControlledEventEngine | trading/engines/ | PAPER 模式，系统时间驱动 |
| PortfolioT1Backtest | trading/portfolios/ | T+1 Signal 延迟 + 结算 |
| SimBroker | trading/brokers/ | 市价随机撮合 + 限价成交 |
| BacktestFeeder | trading/feeders/ | 数据注入接口（需适配为外部数据源） |
| ComponentLoader | trading/services/_assembly/ | 从 Mapping 加载策略/风控 |
| EngineAssemblyService | trading/services/ | 引擎装配 |

### 2.3 新增组件

| 组件 | 职责 |
|------|------|
| DailyDataFetcher | 收盘后从 Tushare 拉取当日 A 股 OHLCV，转为 Bar 对象 |
| PaperTradingScheduler | 每日定时触发引擎推进一天 |
| deploy CLI 命令 | 从回测 Portfolio 创建纸上交易实例并启动 |

## 3. 组件设计

### 3.1 DailyDataFetcher

职责：收盘后拉取当日行情数据，转为引擎可消费的 Bar 对象。

```python
class DailyDataFetcher:
    """每日数据拉取器 - 从 Tushare 获取当日 A 股 OHLCV"""

    def __init__(self):
        self._bar_service = services.data.bar_service()

    def fetch_today_bars(self, codes: List[str]) -> List[Bar]:
        """
        拉取指定股票的当日 OHLCV 数据

        Args:
            codes: 股票代码列表，如 ["000001.SZ", "600036.SH"]

        Returns:
            Bar 对象列表
        """
        today = datetime.date.today()
        bars = self._bar_service.get_bars_page_filtered(
            codes=codes, start=str(today), end=str(today)
        )
        return bars

    def is_market_open_today(self) -> bool:
        """判断今天是否是交易日"""
        pass
```

数据流：
```
Tushare API → bar_crud.add_bars() → ClickHouse → bar_service.get_bars_page_filtered() → List[Bar]
```

先落盘再读取，和回测使用相同的数据路径，确保一致性。

### 3.2 PaperTradingScheduler

职责：每日收盘后自动触发引擎推进。

```python
class PaperTradingScheduler:
    """纸上交易调度器"""

    def __init__(self, engine, data_fetcher, trigger_time="15:35"):
        self._engine = engine
        self._fetcher = data_fetcher
        self._trigger_time = trigger_time

    def start(self):
        """启动调度循环"""
        # 使用 APScheduler 或简单的 while + sleep
        # 每天 15:35 触发
        pass

    def _run_daily_cycle(self):
        """
        每日执行一次：
        1. 检查是否交易日
        2. 拉取当日数据
        3. 喂入引擎
        4. 推进时间
        """
        if not self._fetcher.is_market_open_today():
            return

        bars = self._fetcher.fetch_today_bars(self._engine.interested_codes)
        for bar in bars:
            self._engine.on_price_update(bar)

        # 推进到下一个交易日
        next_trading_day = self._get_next_trading_day()
        self._engine.advance_time(next_trading_day)
```

### 3.3 deploy CLI 命令

```bash
# 从已有回测 Portfolio 创建纸上交易
ginkgo portfolio deploy --source <backtest_portfolio_id> --mode paper

# 查看纸上交易状态
ginkgo portfolio list --mode paper

# 停止纸上交易
ginkgo portfolio stop <portfolio_id>
```

deploy 流程：
```
1. 读取源 Portfolio 的 Mapping 配置（strategy/risk/analyzer/selector）
2. 创建新 Portfolio（复用 ComponentLoader 加载组件）
3. 设置 mode=PAPER
4. 绑定 SimBroker
5. 启动 PaperTradingScheduler
```

## 4. 数据流详解

### 4.1 单日循环

```
[15:35] scheduler 触发
  │
  ├─ [1] fetch_today_bars(["000001.SZ", ...])
  │     └── Tushare → ClickHouse → List[Bar]
  │
  ├─ [2] engine.on_price_update(bar)  ← 对每只股票
  │     └── EventPriceUpdate
  │           └── Strategy.cal()
  │                 └── Signal → _signals 队列 (不立即发 Broker)
  │
  ├─ [3] engine.advance_time(next_day)
  │     └── PortfolioT1Backtest.advance_time()
  │           ├── process_settlement_queue()  ← T+1 解冻
  │           ├── 取出 _signals → put(EventSignalGeneration)
  │           └── Signal → Order → SimBroker.execute() → Fill
  │
  └─ [4] Analyzer 记录净值等指标
```

### 4.2 T+1 时序

```
Day 0: 收盘数据到达 → 策略产生买入 Signal → 存入 _signals
Day 1: 收盘数据到达 → advance_time() → Signal 发送到 Broker → 买入成交
       → settlement_frozen (T+1 冻结)
Day 2: advance_time() → settlement 解冻 → 可卖出
```

## 5. Tushare 数据对接

### 5.1 拉取接口

使用 Tushare `daily` 接口拉取日线数据：
```python
pro.daily(ts_code='000001.SZ', start_date='20260330', end_date='20260330')
```

### 5.2 落盘路径

```
Tushare API → bar_crud.add_bars() → ClickHouse (MBar)
                                    ↓
                          bar_service.get_bars_page_filtered()
                                    ↓
                               List[Bar] → 引擎消费
```

复用现有数据落盘流程，不新建数据路径。

## 6. 配置

### 6.1 纸上交易配置

```python
# 新增配置项，存入 GCONF 或 portfolio config
PAPER_TRADING = {
    "trigger_time": "15:35",        # 每日触发时间
    "data_source": "tushare",        # 数据源
    "broker_type": "sim",            # Broker 类型
    "auto_restart": True,            # 异常后自动重启
    "skip_holiday": True,            # 跳过非交易日
}
```

### 6.2 CLI 参数

```bash
ginkgo portfolio deploy \
    --source <backtest_portfolio_id> \
    --mode paper \
    --trigger-time 15:35 \
    --capital 100000
```

## 7. 实现范围

### 包含

- DailyDataFetcher：Tushare → Bar 落盘
- PaperTradingScheduler：每日调度
- deploy CLI：创建 + 启动纸上交易
- 基本状态查看和停止命令

### 不包含

- Tick 级实时交易（另一个引擎）
- 限价单 OHLC 触及检查（当前 SimBroker 直接以限价成交，够用）
- 实盘 Broker 对接（OKX paper mode 等，后续扩展）
- Web UI 集成（CLI 先行）
