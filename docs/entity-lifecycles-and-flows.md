# Ginkgo 实体生命周期、状态机与运行流程

## 一、实体生命周期

### 1. Signal — 无状态值对象

```
Strategy.cal() / Risk.generate_signals()
        │
        ▼
   Signal(code, direction, ...)
        │
        ▼  (T+1: 当日信号延迟到次日)
   EventSignalGeneration → 引擎队列 → Portfolio.on_signal()
        │
        ▼
   Sizer.cal(signal) → Order   (Signal 被"消费", 生命周期结束)
```

**关键属性**: `code`, `direction`(LONG/SHORT), `volume`, `weight`, `strength`, `confidence`, `reason`, `source`(STRATEGY/SELECTOR)

**生命周期**: 创建 → 包装为事件 → 引擎调度 → T+1延迟(可选) → Sizer消费 → 持久化到DB

> 源码: `src/ginkgo/trading/bases/signal_base.py`, `src/ginkgo/entities/signal.py`

---

### 2. Order 状态机 (`ORDERSTATUS_TYPES`)

```
                    ┌──────────────────┐
         submit()   │                  │  partial_fill()
   NEW ──────────► SUBMITTED ─────────┼───► PARTIAL_FILLED ──┐
    │               │    │            │        │              │
    │          cancel()  │   fill()   │        │  fill()      │
    │               │    └────────────┼───► FILLED (终态)     │
    ▼               ▼                 │                        │
 CANCELED (终态)  CANCELED ◄──────────┼────────────────────────┘
                  (终态)     cancel() │
```

**合法转换**:
- `NEW` → `SUBMITTED`, `CANCELED`
- `SUBMITTED` → `PARTIAL_FILLED`, `FILLED`, `CANCELED`
- `PARTIAL_FILLED` → `PARTIAL_FILLED`, `FILLED`, `CANCELED`
- `FILLED` / `CANCELED` — 终态

**关键方法**: `submit()`, `partial_fill(volume, price, fee)`, `fill(price, fee)`, `cancel()`, `get_fill_ratio()`

> 源码: `src/ginkgo/trading/bases/order_base.py`, `src/ginkgo/entities/order.py`

---

### 3. Position — 体积分区模型（无显式状态枚举）

```
total_position = volume(可用) + frozen_volume(挂卖冻结) + settlement_frozen_volume(T+N冻结)
```

```
 买入(T+0):  volume += vol
 买入(T+N):  settlement_frozen += vol → N日后 → volume
 卖出冻结:   volume → frozen
 卖出成交:   frozen -= vol, 计算realized_pnl
 每日推进:   process_settlement_queue() 将到期批次解冻
```

**关键方法**: `deal(direction, price, volume)`, `freeze(vol)`, `unfreeze(vol)`, `on_price_update(price)`, `process_settlement_queue(time)`

**PnL计算**: `total_pnl = total_position * (price - cost) - fee`, `realized_pnl` 累计已实现盈亏

> 源码: `src/ginkgo/trading/bases/position_base.py`, `src/ginkgo/entities/position.py`

---

### 4. Portfolio 状态机 (`PORTFOLIO_RUNSTATE_TYPES`)

```
INITIALIZED ──► RUNNING ◄──► PAUSED
                   │              │
                   ▼              ▼
              STOPPING ──────► STOPPED
                   │
              RELOADING ──► RUNNING (热更新组件)
              MIGRATING ──► RUNNING (节点迁移)
                   │
               OFFLINE (持久化后下线)
```

**模式枚举** (`PORTFOLIO_MODE_TYPES`): `BACKTEST(0)`, `PAPER(1)`, `LIVE(2)`

**管理的子组件**:
- `_strategies: List[BaseStrategy]` — 策略列表
- `_risk_managers: List[RiskBase]` — 风控管理器列表
- `_sizer: SizerBase` — 仓位计算器
- `_selectors: List[SelectorBase]` — 选股器列表
- `_positions: Dict[str, Position]` — 持仓字典
- `_analyzers: Dict[str, BaseAnalyzer]` — 分析器字典

**关键方法**: `on_price_received()`, `on_signal()`, `on_order_partially_filled()`, `advance_time()`, `snapshot_state()`, `restore_state()`

> 源码: `src/ginkgo/trading/bases/portfolio_base.py`, `src/ginkgo/trading/portfolios/t1backtest.py`

---

### 5. Broker 状态机 (`BrokerStateType`)

```
uninitialized → initializing → running ◄──► paused → stopped
                                    │
                                  error
```

**BrokerManager 生命周期方法**:
- `create_broker()` — 创建DB记录和Broker实例
- `start_broker()` — `broker.connect()` → running
- `stop_broker()` — `broker.disconnect()` → stopped
- `pause_broker()` / `resume_broker()` — running ↔ paused
- `emergency_stop_all()` — 紧急停止所有活跃Broker

**Broker 层次**:
```
IBroker (接口)
  ├─ BaseBroker (基础实现: 订单生命周期、持仓管理)
  │    ├─ LiveBrokerBase (实盘基类: API交易、异步执行)
  │    │    ├─ OKXBroker (OKX交易所适配器)
  │    │    └─ AlpacaBroker...
  │    └─ SimBroker (回测模拟: 即时撮合、滑点模型、A股佣金)
  └─ (其他交易所适配器)
```

> 源码: `src/ginkgo/trading/bases/base_broker.py`, `src/ginkgo/trading/brokers/broker_manager.py`

---

### 6. Strategy — 无状态处理器

```
创建/配置 → add_strategy(portfolio) → bind_engine(engine)
                                          │
            每次PriceUpdate ◄─────────────┘
                │
                ▼
           cal(portfolio_info, event) → List[Signal]
                │
                ▼
           create_signal(code, direction, ...) → Signal (自动填充上下文)
```

**无状态枚举** — 策略是纯函数式处理器，接收事件产生信号。

> 源码: `src/ginkgo/trading/strategies/strategy_base.py`

---

### 7. Risk Management — 双重机制

```
┌─────────────────────────────────────────────────────────────┐
│  被动拦截: cal(portfolio_info, order) → Order | None        │
│    在 Portfolio.on_signal() 中，Sizer 之后逐个调用          │
│    可调整订单量、或返回 None 完全拦截                        │
│    例: PositionRatioRisk 调整仓位, CapitalRisk 检查资金     │
├─────────────────────────────────────────────────────────────┤
│  主动信号: generate_signals(portfolio_info, event) → List   │
│    在 Portfolio.generate_risk_signals() 中调用              │
│    监控市场事件，主动生成平仓信号                             │
│    例: LossLimitRisk 止损, ProfitTargetRisk 止盈            │
└─────────────────────────────────────────────────────────────┘
```

> 源码: `src/ginkgo/trading/bases/risk_base.py`, `src/ginkgo/trading/risk_management/`

---

### 8. Sizer — 信号→订单转换器

```
cal(portfolio_info, signal) → Order | None

FixedSizer:  固定手数，按可用资金调整
RatioSizer:  按资金比例计算
ATRSizer:    基于ATR波动率计算
```

> 源码: `src/ginkgo/trading/bases/sizer_base.py`, `src/ginkgo/trading/sizers/`

---

## 二、单时间步事件流（代码驱动回测核心循环）

**引擎**: `TimeControlledEventEngine` (`src/ginkgo/trading/engines/time_controlled_engine.py`)

```
┌─────────────────────────────────────────────────────────────────────┐
│  TimeControlledEventEngine.main_loop() — 队列空时自动推进时间      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ① EventTimeAdvance(T+1)                                           │
│     └─ LogicalTimeProvider.set(T+1)                                │
│                                                                     │
│  ② EventComponentTimeAdvance("feeder")                             │
│     └─ BacktestFeeder.advance_time()                               │
│         └─ bar_service.get(code, T+1) → EventPriceUpdate × N       │
│                                                                     │
│  ③ EventComponentTimeAdvance("portfolio")                          │
│     └─ Portfolio.advance_time(T+1)                                 │
│         ├─ T+1结算: position.process_settlement_queue()            │
│         ├─ Selector.pick() → EventInterestUpdate (更新订阅)        │
│         └─ 昨日延迟信号 → EventSignalGeneration × M                │
│                                                                     │
│  ④ EventPriceUpdate × N 被处理                                     │
│     ├─→ Portfolio.on_price_received()                              │
│     │     └─ strategy.cal(info, event) → List[Signal]              │
│     │           └─ EventSignalGeneration → 队列                    │
│     └─→ TradeGateway.on_price_received()                           │
│           └─ 更新 Broker 市场数据缓存                              │
│                                                                     │
│  ⑤ EventSignalGeneration 被处理                                    │
│     └─→ Portfolio.on_signal()                                      │
│          ├─ 当日信号? → 延迟到次日                                 │
│          └─ 非当日:                                                 │
│               sizer.cal(info, signal) → Order(NEW)                 │
│               risk.cal(info, order) × R (可能调整/拦截)            │
│               freeze(资金/持仓)                                    │
│               EventOrderAck → 队列                                 │
│                                                                     │
│  ⑥ EventOrderAck 被处理                                            │
│     └─→ TradeGateway → SimBroker.submit_order_event()              │
│           └─ 即时撮合 → EventOrderPartiallyFilled → 队列           │
│                                                                     │
│  ⑦ EventOrderPartiallyFilled 被处理                                │
│     └─→ Portfolio.on_order_partially_filled()                      │
│          ├─ LONG: deduct_frozen → position.deal(LONG)              │
│          ├─ SHORT: add_cash → position.deal(SHORT)                 │
│          └─ update_worth() → Analyzer hooks                        │
│                                                                     │
│  ⑧ 队列清空 → _is_backtest_finished()?                            │
│              ├─ 否 → 回到① 推进T+2                                 │
│              └─ 是 → _aggregate_backtest_results() → 保存结果      │
└─────────────────────────────────────────────────────────────────────┘
```

**核心类继承链**:
```
BaseEngine → EventEngine → TimeControlledEventEngine
                           ├─ mode=BACKTEST (回测)
                           ├─ mode=PAPER   (模拟盘)
                           └─ mode=LIVE    (实盘)
```

**事件类型** (`EVENT_TYPES`):
| 事件 | ID | 触发时机 |
|------|-----|---------|
| PRICEUPDATE | 1 | Feeder推送行情 |
| SIGNALGENERATION | 100 | 策略/风控产生信号 |
| ORDERACK | 21 | 订单提交到Broker |
| ORDERPARTIALLYFILLED | 22 | 订单部分/全部成交 |
| ORDERCANCELACK | 25 | 订单取消确认 |
| TIME_ADVANCE | - | 时间推进 |

---

## 三、Worker 回测流程

**组件**: `BacktestWorker` + `BacktestProcessor`

```
API/CLI                          Kafka                          Worker
───────                          ─────                          ──────

BacktestTaskService              backtest.assignments           BacktestWorker
  .start_task()                        │
  ├─ 清理旧数据 ──────────────────► 消费 ◄──────── _start_task_consumer_thread()
  ├─ DB status→pending                │                  │
  └─ Produce assignment ─────────►    │           _start_task()
                                       │             ├─ 等待空闲slot(最多5并发)
                                       │             ├─ Build BacktestConfig
                                       │             └─ BacktestProcessor.start()
                                                       │
                                              ┌────────┴────────┐
                                              │ Thread.run()     │
                                              │                  │
                                              │ _assemble_engine()
                                              │  ├─ load_portfolio_with_components(DB)
                                              │  ├─ 加载策略/风控/Sizer/选择器文件
                                              │  └─ EngineAssemblyService.assemble()
                                              │       → TimeControlledEventEngine
                                              │
                                              │ engine.run() ← 同"二"的事件循环
                                              │
                                              │ _calculate_result()
                                              │ _aggregate_and_save_results()
                                              │ ProgressTracker.report_completed()
                                              │  ├─ Kafka → backtest.progress
                                              │  ├─ DB → status="completed"
                                              │  └─ HTTP → WebSocket 通知前端
                                              └──────────────────┘
```

**任务状态机**:
```
created → pending → DATA_PREPARING → ENGINE_BUILDING → RUNNING → COMPLETED
                                                          ├─→ FAILED
                                                          └─→ CANCELLED
```

**Kafka Topics**:
| Topic | 方向 | 用途 |
|-------|------|------|
| `backtest.assignments` | API → Worker | 任务分发(start/cancel) |
| `backtest.progress` | Worker → API | 进度上报 |
| `backtest.results` | Worker → API | 最终结果 |

**并发模型**: 最多 5 个并发回测，每个在独立 daemon 线程中运行，通过 `threading.Event` 管理槽位。

> 源码: `src/ginkgo/workers/backtest_worker/node.py`, `src/ginkgo/workers/backtest_worker/task_processor.py`

---

## 四、Worker 实盘流程

### 4.1 PaperTradingWorker（模拟盘）

```
启动: assemble_engine()
  ├─ 加载所有 PAPER 模式 Portfolio
  ├─ 创建 TimeControlledEventEngine(mode=PAPER)
  ├─ 恢复持久化状态 / 初始化资金
  └─ 检测模式:
       persisted_time < now? → REPLAY(LogicalTime) + SOURCE=PAPER_REPLAY
       persisted_time ≥ now? → LIVE_PAPER(SystemTime) + SOURCE=PAPER_LIVE

每日 21:10 Kafka "paper_trading" 命令:
  ├─ REPLAY 模式:
  │    while engine_date < today:
  │        engine.advance_time_to(next_trading_day)  ← 批量快进历史
  │    _transition_to_live()
  │       └─ LogicalTimeProvider → SystemTimeProvider
  │          SOURCE → PAPER_LIVE
  │
  └─ LIVE_PAPER 模式:
       sync bar data → advance_time_to(next_day)
       偏差检测 → 持久化状态
```

**REPLAY → LIVE 转换**: Worker 启动时如果落后于当前时间，先用 `LogicalTimeProvider` 批量快进历史数据（复用回测引擎），追上后切换为 `SystemTimeProvider` 进入实时模式。

**Kafka 控制命令** (topic: `ginkgo.live.control.commands`):
| 命令 | 动作 |
|------|------|
| `paper_trading` | 触发每日循环 |
| `deploy` | 动态加载新 Portfolio |
| `unload` | 移除 Portfolio |

> 源码: `src/ginkgo/workers/paper_trading_worker.py`

---

### 4.2 ExecutionNode（实盘交易）

```
Scheduler ──Kafka SCHEDULE_UPDATES──► ExecutionNode.load_portfolio()
                                              │
                                   ┌──────────┴──────────┐
                                   │ PortfolioProcessor    │
                                   │ ├─ input_queue  ←──┐ │
                                   │ ├─ output_queue ───┼─┼─► Kafka ORDERS_SUBMISSION
                                   │ └─ Strategy线程    │ │
                                   └────────────────────┘ │
                                                          │
Kafka MARKET_DATA ──► _route_event_to_portfolios() ───────┘
                       └─ InterestMap 查找 → 放入 input_queue
                              │
                    PortfolioProcessor:
                      strategy.cal() → Order → output_queue
                              │
                    LiveEngine 消费 ORDERS_SUBMISSION:
                      OKXBroker.submit_order_event()
                        └─ python-okx SDK → 交易所
                           WebSocket → 订单状态回报
                              │
                    ORDERS_FEEDBACK → ExecutionNode → Portfolio
```

**架构特点**:
- 每个 Portfolio 独立线程 + 双队列(input/output)
- `InterestMap` 提供 O(1) 事件路由（按股票代码查找订阅的 Portfolio）
- 订单通过 Kafka `ORDERS_SUBMISSION` 送到 LiveEngine，再由 OKXBroker 提交到交易所
- 成交回报通过 `ORDERS_FEEDBACK` 回传

**Kafka Topics**:
| Topic | 方向 | 用途 |
|-------|------|------|
| `ginkgo.live.market.data` | DataSync → Node | 实时行情 |
| `ginkgo.live.orders.submission` | Node → LiveEngine | 订单提交 |
| `ginkgo.live.orders.feedback` | LiveEngine → Node | 成交回报 |
| `ginkgo.schedule.updates` | Scheduler → Node | Portfolio迁移/暂停/恢复 |

> 源码: `src/ginkgo/workers/execution_node/node.py`, `src/ginkgo/livecore/live_engine.py`

---

## 五、部署服务（回测 → 模拟/实盘）

```
BacktestTask(COMPLETED)
        │
        ▼  DeploymentService.deploy(task_id, mode, account_id)
        │
        ├─ 验证回测任务已完成
        ├─ 读取源 Portfolio 的组件映射
        ├─ 创建新 Portfolio (PAPER 或 LIVE 模式)
        ├─ 深拷贝组件: 策略/风控/Sizer/选择器文件 + 参数
        ├─ 复制 MongoDB 图结构
        ├─ [LIVE] 创建 MBrokerInstance 记录
        └─ 创建 MDeployment 记录
```

> 源码: `src/ginkgo/trading/services/deployment_service.py`

---

## 六、关键枚举速查

| 枚举 | 值 | 用途 |
|------|-----|------|
| `DIRECTION_TYPES` | LONG(1), SHORT(2) | 交易方向 |
| `ORDERSTATUS_TYPES` | NEW(1)→SUBMITTED(2)→PARTIAL_FILLED(3)→FILLED(4) / CANCELED(5) | 订单状态 |
| `ORDER_TYPES` | MARKETORDER(1), LIMITORDER(2) | 订单类型 |
| `PORTFOLIO_MODE_TYPES` | BACKTEST(0), PAPER(1), LIVE(2) | Portfolio运行模式 |
| `PORTFOLIO_RUNSTATE_TYPES` | INITIALIZED(0)→RUNNING(1)↔PAUSED(2)→STOPPED(4), RELOADING(5), MIGRATING(6), OFFLINE(7) | Portfolio运行状态 |
| `ENGINESTATUS_TYPES` | IDLE(0)→INITIALIZING(1)→RUNNING(2)↔PAUSED(3)→STOPPPED(4) | 引擎状态 |
| `SOURCE_TYPES` | BACKTEST(15), PAPER_REPLAY(18), PAPER_LIVE(19) | 数据来源标记 |
| `BrokerStateType` | uninitialized→initializing→running↔paused→stopped / error | Broker状态 |
| `RECORDSTAGE_TYPES` | NEWDAY(1), SIGNALGENERATION(2), ORDERSEND(3), ORDERPARTIALLYFILLED(8), ENDDAY(6) | Analyzer记录阶段 |
| `EVENT_TYPES` | PRICEUPDATE(1), SIGNALGENERATION(100), ORDERACK(21), ORDERPARTIALLYFILLED(22) | 事件类型 |
