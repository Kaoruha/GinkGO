# A 股日级纸上交易设计

> 日期：2026-03-30
> 分支：016-a-stock-paper-trading
> 状态：设计阶段
> 最后更新：2026-03-30（架构重设计 v3）

---

## 1. 目标

打通"回测 → 纸上交易"飞轮，让策略用真实 A 股行情进行日级验证。

核心思路：纸上交易 = "每天推进一格"的回测引擎，数据源从历史数据切换为当日真实数据。

## 2. 架构

### 2.1 整体流程

```
[Deploy 阶段]
ginkgo portfolio deploy --source <backtest_id> --mode paper
  └─ 复制源 Portfolio 配置到 DB（mode=PAPER）+ Kafka 通知 Worker

[启动阶段]
ginkgo serve worker-paper
  └─ PaperTradingWorker 长驻进程启动
       ├─ 从 DB 读取所有 PAPER 模式 Portfolio 配置
       ├─ 组装引擎（复用回测引擎），加载所有 PAPER Portfolio
       ├─ selector.pick() 初始化 interested codes
       ├─ 引擎常驻内存，状态自然保持
       └─ 订阅 Kafka ginkgo.live.control.commands

[每日循环]
TaskTimer (21:10) → Kafka → PaperTradingWorker
  └─ 对引擎执行 run_daily_cycle()
       ├─ 检查交易日
       ├─ sync_range_batch() 拉取当日数据
       └─ engine.advance_time_to(next_day)
            ├── Feeder → EventPriceUpdate → Strategy.cal() → Signal
            ├── Portfolio → T+1 信号 → Order → SimBroker → Fill
            └── T+1 结算 + Analyzer 记录
```

### 2.2 现有组件复用

| 组件 | 文件 | 纸上交易中的角色 |
|------|------|-----------------|
| TimeControlledEventEngine | trading/engines/ | PAPER 模式，复用回测引擎 |
| PortfolioT1Backtest | trading/portfolios/ | T+1 Signal 延迟 + 结算 |
| SimBroker | trading/brokers/ | 模拟成交 |
| BacktestFeeder | trading/feeders/ | 数据注入 |
| ComponentLoader | trading/services/_assembly/ | 从 Mapping 加载组件 |
| EngineAssemblyService | trading/services/ | 引擎装配 |
| TaskTimer | livecore/ | 定时触发（cron 21:10） |

### 2.3 新增/重写组件

| 组件 | 职责 |
|------|------|
| PaperTradingWorker（重写） | 长驻进程，持有引擎，消费 Kafka，执行每日循环 |
| deploy/unload CLI 命令（重写） | 纯 DB 操作，复制/卸载 Portfolio 配置 |

## 3. 核心设计决策

### 3.1 复用引擎

纸上交易的核心价值是验证策略在真实行情下表现是否和回测一致。引擎保证策略、风控、T+1、Broker 的代码路径完全一致。不复用引擎就无法保证验证的可信度。

### 3.2 有状态长驻进程

PaperTradingWorker 是长驻进程，持有引擎实例在内存中。

**为什么不是无状态批处理：**
- 引擎状态复杂（事件队列、时间提供者、持仓、信号队列），序列化/反序列化成本高
- 有状态方案更简单，状态自然保持
- 重启恢复逻辑只需做一次，Paper/Live 通用

**重启恢复：** Worker 重启后，从 DB 读取 PAPER Portfolio 配置重建引擎，加载所有 PAPER Portfolio。持仓和信号已在 DB 中持久化（每次成交自动写入），重建时从 DB 恢复状态即可。T+1 信号队列从 DB 加载未执行的信号。

### 3.3 Paper/Live 架构统一

日级 Paper Trading 和 Tick 级 Paper/Live Trading 共享同一套 Worker 架构：

| | Paper (日级) | Paper/Live (Tick 级) |
|--|---|---|
| Worker | PaperTradingWorker | 同一个 Worker（未来扩展） |
| Broker | SimBroker | SimBroker / 真实 Broker |
| 数据 | 日线 OHLCV | 逐笔 Tick |
| 触发 | 定时推进 | 实时推送 |
| 引擎 | TimeControlledEventEngine (PAPER) | TimeControlledEventEngine (LIVE) |

差异仅在 Broker 和数据源，Worker 生命周期管理完全一致。

### 3.4 deploy 是纯 DB 操作

deploy 只复制源 Portfolio 的配置到新 Portfolio（mode=PAPER），不创建引擎：

```
ginkgo portfolio deploy --source <backtest_portfolio_id> --mode paper
  │
  ├─ 读取源 Portfolio 的所有配置
  │     ├─ strategy/risk/analyzer/selector/sizer 绑定关系
  │     └─ 参数（初始资金等）
  │
  ├─ 在 DB 中创建新 Portfolio（mode=PAPER）
  │     └─ 复制所有组件绑定关系
  │
  ├─ 设置初始资金
  │
  └─ 发 Kafka 通知 Worker 动态加载新 Portfolio
```

**粒度说明：** 1 次 deploy = 1 个 Portfolio 配置。1 个 Worker = 1 个 Engine = 加载所有 PAPER Portfolio。

### 3.5 unload 操作

deploy 的反向操作，从运行中的 Worker 卸载指定 Portfolio：

```
ginkgo portfolio unload <portfolio_id>
  │
  ├─ 发 Kafka 通知 Worker
  │
  ├─ Worker 收到通知
  │     ├─ engine.remove_portfolio(portfolio)
  │     └─ DB 标记 Portfolio 为非活跃
  │
  └─ 历史交易数据保留在 DB 中
```

### 3.6 interested codes 初始化

Worker 启动时，对每个 Portfolio 调用 `selector.pick()` 初始化 interested codes。`pick()` 通过 `bar_service` 直接查 ClickHouse，不依赖 feeder 事件机制。

**一天延迟：** selector.pick() 在 advance_time 中被调用，新选中的股票要到第二天才能拉到数据。日级策略可接受（T+1 本身就延迟一天）。

## 4. PaperTradingWorker 设计

### 4.1 职责

- 长驻进程，启动时从 DB 加载所有 PAPER Portfolio 并组装引擎
- 订阅 Kafka `ginkgo.live.control.commands`，消费命令
- Redis 心跳（同 BacktestWorker 模式）
- 优雅关闭

### 4.2 命令处理

| 命令 | 来源 | 处理 |
|------|------|------|
| `paper_trading` | TaskTimer (cron 21:10) | 对引擎执行每日循环 |
| `deploy` | CLI deploy 命令 | 动态加载新 Portfolio 到引擎 |
| `unload` | CLI unload 命令 | 从引擎卸载指定 Portfolio |

### 4.3 每日循环逻辑

```python
def run_daily_cycle(self) -> DailyCycleResult:
    # 1. 检查交易日
    if not is_trading_day(today):
        return skip

    # 2. 获取 interested codes（从所有 Portfolio 的 selector._interested）
    codes = get_interested_codes()

    # 3. 同步拉取当日数据
    sync_result = bar_service.sync_range_batch(codes, today, today)

    # 4. 推进引擎到下一个交易日
    next_day = trade_day_crud.get_next_trading_day(today)
    engine.advance_time_to(next_day)
```

### 4.4 启动入口

```bash
ginkgo serve worker-paper --id <worker_id>
```

参照 `ginkgo serve worker-backtest` 的模式：
- 信号处理（SIGINT/SIGTERM）
- Redis 心跳（10s 间隔，TTL 30s）
- Kafka 消费循环
- 优雅关闭

## 5. 组件生命周期

### 5.1 Worker 进程级

```
ginkgo serve worker-paper
  │
  ├─ 启动：连接 Kafka + Redis 心跳 + 从 DB 加载所有活跃 PAPER Portfolio
  │     └─ 组装引擎 → 加载所有 Portfolio → selector.pick() → engine.start()
  │
  ├─ 运行：消费 Kafka，处理三种命令
  │     ├─ paper_trading → 每日循环
  │     ├─ deploy → 动态加载新 Portfolio
  │     └─ unload → 卸载指定 Portfolio
  │
  └─ 停止：SIGINT/SIGTERM → engine.stop() → 清理退出
```

### 5.2 子组件绑定顺序

```
Engine
  ├─ add_portfolio(Portfolio)  ← 可重复，加载多个 Portfolio
  │     └─ Portfolio 已绑定 engine → bind_selector/add_strategy 等自动传播
  ├─ set_data_feeder(Feeder)
  │     └─ Feeder 绑定 engine + 传播给已有 Portfolio 的子组件
  ├─ bind_router(Gateway + SimBroker)
  │     └─ Gateway 绑定 engine + 注册所有 Portfolio
  └─ engine.start()
```

### 5.3 状态持久化时机

| 组件 | 写入时机 | 说明 |
|------|---------|------|
| 持仓 | Broker 成交后自动 | `_save_position()` 写 DB |
| 信号 | Strategy 产生后自动 | signal 写 DB |
| T+1 信号队列 | 仅内存 | Worker 重启后从 DB 加载未执行信号恢复 |
| 现金 | Portfolio 管理 | 跟随持仓变化 |

## 6. 数据流详解

### 6.1 单日循环

```
[21:10] TaskTimer → Kafka (paper_trading)
  │
  └─ PaperTradingWorker 消费
       └─ 对引擎：
            ├─ bar_service.sync_range_batch(codes, today)
            ├─ engine.advance_time_to(next_day 15:00)
            │     ├── Feeder 推进 → EventPriceUpdate
            │     │     └── Strategy.cal() → Signal → _signals 队列
            │     ├── Portfolio 推进 → 取出昨日信号 → 下单
            │     │     └── SimBroker.execute() → Fill → 写回 DB
            │     ├── selector.pick() → 更新 interested codes（次日生效）
            │     └── T+1 结算（解冻持仓）
            └── Analyzer 记录净值
```

### 6.2 T+1 时序

```
Day 0: 数据到达 → Strategy.cal() → Signal → 存入 _signals（不执行）
Day 1: 数据到达 → advance_time() → 取出昨日 Signal → Broker 成交
       → T+1 冻结
Day 2: advance_time() → settlement 解冻 → 可卖出
```

## 7. Tushare 数据对接

使用 Tushare `daily` 接口拉取日线数据，先落盘再读取，和回测使用相同的数据路径。

```
Tushare API → bar_crud.add_bars() → ClickHouse → bar_service.get_bars_page_filtered() → List[Bar]
```

## 8. 配置

### 8.1 纸上交易配置

```python
PAPER_TRADING = {
    "trigger_time": "21:10",         # 每日触发时间（bar_snapshot 21:00 之后）
    "data_source": "tushare",        # 数据源
    "broker_type": "sim",            # Broker 类型
    "skip_holiday": True,            # 跳过非交易日
}
```

### 8.2 CLI 命令

```bash
# 部署（复制配置到 DB + 通知 Worker）
ginkgo portfolio deploy --source <backtest_portfolio_id> --mode paper --capital 100000

# 卸载（通知 Worker 移除 + DB 标记非活跃）
ginkgo portfolio unload <portfolio_id>

# 启动 Worker
ginkgo serve worker-paper --id <worker_id>

# 查看状态
ginkgo portfolio list --mode paper
```

## 9. 实现范围

### 包含

- PaperTradingWorker：长驻进程，Kafka 消费，引擎持有，1 Engine : N Portfolio
- deploy CLI：纯 DB 配置复制 + Kafka 通知
- unload CLI：Kafka 通知 Worker 卸载 + DB 标记非活跃
- `ginkgo serve worker-paper` 启动入口
- TaskTimer 集成：`paper_trading` 命令（已有）
- 查看状态命令
- 引擎重启状态恢复：从 DB 加载持仓/信号，恢复 T+1 队列

### 不包含

- Tick 级实时交易（后续扩展，复用同一 Worker 架构）
- 实盘 Broker 对接（后续扩展）
- Web UI 集成（CLI 先行）
- 独立 stop 命令（停 Worker 即停所有）

## 10. 审计修复记录

### 2026-03-30 逻辑审计

| 问题 | 严重度 | 修复 |
|------|--------|------|
| `engine.portfolios.values()` 崩溃（List 不是 Dict） | 严重 | ✅ 直接迭代 `engine.portfolios` |
| `getattr(portfolio, "selector")` 取不到（存在 `_selectors` 列表） | 严重 | ✅ 遍历 `portfolio._selectors` |
| `bind_selector/add_strategy/bind_sizer` 不传播 data_feeder | 中等 | ✅ portfolio_base 加 `_data_feeder` 字段，绑定方法中自动传播 |
| 首次推进死锁（selector 未 pick → 无 codes → 不推进） | 中等 | 📋 Worker 启动时调用 selector.pick() 初始化 interested |
| 调试 print 残留 | 低 | ✅ 替换为 GLOG |

### 2026-03-30 架构演进

| 版本 | 方案 | 弃用原因 |
|------|------|---------|
| v1 | CLI 创建引擎 + PaperTradingController + 有状态 Worker | Worker 没有实际运行（Kafka TODO），引擎生命周期管理混乱 |
| v2 | 无状态批处理，每天从 DB 重建引擎 | 状态序列化复杂，过度设计 |
| **v3（当前）** | **有状态长驻 Worker，1 Engine : N Portfolio，Paper/Live 架构统一** | **简洁，与 Live Trading 共享架构** |
