# 统一引擎架构设计规格

**日期**: 2026-03-27
**状态**: Draft
**分支**: `015-unified-engine-architecture`

---

## 1. 背景与目标

### 1.1 现状问题

当前 Ginkgo 的回测、模拟盘、实盘是三条独立链路：

- **回测**: `EngineHistoric` + `BacktestFeeder` + `SimBroker`（内部撮合）
- **模拟盘**: 无完整实现，代码中仅有 `EXECUTION_MODE.PAPER` 枚举值
- **实盘**: `LiveEngine` + `OKXDataFeeder` + `OKXBroker`（独立架构）

问题：
1. Strategy/Portfolio 代码无法在三种模式间复用
2. Engine 内部有 16 处 `== BACKTEST` / `!= BACKTEST` 二元分支，无法支持 PAPER
3. DataFeeder 和 Broker 是单绑定的（1:1），不支持多市场

### 1.2 设计目标

**核心公式**: `一个策略，三种运行模式，零代码修改`

```
PAPER    = LiveDataFeeder + SimBroker     (真实数据 + 虚拟成交)
LIVE     = LiveDataFeeder + RealBroker    (真实数据 + 真实成交)
BACKTEST = HistoricalFeeder + SimBroker   (历史数据 + 虚拟成交)
```

**设计原则**: 在现有框架上尽可能少改造，不引入新架构层。

---

## 2. 架构

### 2.1 Engine 类统一（现状问题）

当前存在三套独立 Engine 实现，接口不统一：

```
BaseEngine → EventEngine → TimeControlledEventEngine  ← 核心，有 BACKTEST/LIVE 分支
LiveEngine                  (独立，不继承 BaseEngine)   ← 实盘，管理 Broker/心跳/恢复
PaperTradingEngine          (独立，不继承 BaseEngine)   ← 模拟盘，独立实现
```

**问题**：
- `LiveEngine` 和 `PaperTradingEngine` 不走 `BaseEngine` 体系
- `TimeControlledEventEngine` 的 LIVE 分支实际没被使用（实盘走 `LiveEngine`）
- 三套 Engine 做类似的事情，Strategy/Portfolio 无法复用

### 2.2 Engine 类统一（目标）

统一为一条继承链，废弃独立的 `LiveEngine` 和 `PaperTradingEngine`：

```
BaseEngine → EventEngine → TimeControlledEventEngine
                               ├── mode=BACKTEST: HistoricalFeeder + SimBroker
                               ├── mode=PAPER:    LiveDataFeeder  + SimBroker
                               └── mode=LIVE:     LiveDataFeeder  + RealBroker
```

`LiveEngine` 中的 Broker 管理、心跳监控等功能降级为 `TimeControlledEventEngine` 的可选组件。
`PaperTradingEngine` 完全废弃，功能由 PAPER 模式覆盖。

### 2.3 改造范围

在 `TimeControlledEventEngine` 上扩展，**不引入新架构层**：

```
TimeControlledEventEngine (现有，扩展)
  ├── DataFeeders: [feeder_1, feeder_2, ...]   ← 从 1→N
  ├── TradeGateway: 多 Broker 路由               ← 复用现有
  ├── Portfolio (不变)
  ├── Strategies (不变)
  └── RiskManagers (不变)
  └── 可选组件（仅 PAPER/LIVE）:
        ├── HeartbeatMonitor                     ← 从 LiveEngine 迁移
        └── BrokerRecoveryService               ← 从 LiveEngine 迁移
```

### 2.4 正交维度

| | HistoricalFeeder | LiveDataFeeder |
|---|---|---|
| **SimBroker** | BACKTEST | **PAPER** |
| **RealBroker** | N/A | LIVE |

### 2.5 多市场支持

多个 DataFeeder 往同一个事件队列 push 事件，事件循环照常串行处理。订单提交时通过 BrokerRouter 路由到对应 Broker。

---

## 3. 核心设计决策

### 3.1 三态切换

当前 `time_controlled_engine.py` 有 16 处二元判断，需改为三态：

```python
# 当前（二元）
if self.execution_mode == EXECUTION_MODE.BACKTEST:
    # 回测逻辑
else:
    # 实盘逻辑

# 目标（三态）
if self.execution_mode == EXECUTION_MODE.BACKTEST:
    # 逻辑时间、非阻塞队列、历史数据
elif self.execution_mode == EXECUTION_MODE.PAPER:
    # 系统时间、阻塞队列、实时数据、虚拟成交
else:  # LIVE
    # 系统时间、阻塞队列、实时数据、真实成交
```

### 3.2 资金管理

```
BACKTEST: Portfolio 内部虚拟资金（不变）
PAPER:    Portfolio 内部虚拟资金（与 BACKTEST 相同）
LIVE:     Portfolio 从 Broker 查询真实余额（需要同步机制）
```

PAPER 与 BACKTEST 的差异只在 DataFeeder 数据来源，Portfolio 行为一致。

### 3.3 Broker 路由

复用现有 `TradeGateway`（`src/ginkgo/trading/gateway/trade_gateway.py`），不做新建：

- `TradeGateway` 已实现多 Broker 注册和按 symbol 路由
- `get_broker_for_order()` 根据订单 symbol 自动选择 Broker
- 需要改进：`_code_market_mapping` 当前写死示例 symbol，改为动态 pattern 匹配（见 3.4）

### 3.4 Symbol 市场识别

`TradeGateway._get_market_by_code()` 当前写死示例 symbol，需改为动态 pattern 匹配：

- `BTC/USDT` → Crypto → OKXBroker
- `000001.SZ` → A-Share → SimBroker（PAPER）或 实盘券商（LIVE）
- `AAPL` → US Stock → AlpacaBroker

---

## 4. 重构清单

### 4.1 Phase 1: Engine 三态支持

**文件**: `src/ginkgo/trading/engines/time_controlled_engine.py`

16 处二元分支改为三态：

| 位置 | 功能 | BACKTEST | PAPER | LIVE |
|------|------|----------|-------|------|
| `main_loop()` | 队列等待 | timeout=0.01 | blocking wait | blocking wait |
| `_initialize_components()` | 时间提供者 | LogicalTime | SystemTime | SystemTime |
| `_initialize_components()` | 线程池 | 无 | ThreadPoolExecutor | ThreadPoolExecutor |
| `main_loop()` | 空队列处理 | 推进时间 | 继续等待 | 继续等待 |
| `_setup_data_feeder()` | DataFeeder | BacktestFeeder | LiveDataFeeder | LiveDataFeeder |

### 4.2 Phase 2: 多 DataFeeder / TradeGateway 集成

**文件**: `src/ginkgo/trading/engines/time_controlled_engine.py`

- `self._data_feeder` → `self._data_feeders: List[IDataFeeder]`
- 接入现有 `TradeGateway`（多 Broker 路由），不新建 BrokerRouter
- 各 feeder 独立启动，事件统一入队
- 改进 `TradeGateway._get_market_by_code()` 为动态 pattern 匹配

### 4.3 Phase 3: EngineAssemblyService PAPER 模式

**文件**: `src/ginkgo/trading/services/engine_assembly_service.py`

- 修改 `assemble_backtest_engine()` 支持 PAPER 模式
- PAPER: 组装 LiveDataFeeder + SimBroker
- LIVE: 组装 LiveDataFeeder + RealBroker

### 4.4 Phase 4: 废弃独立 Engine，迁移功能

**废弃文件**:
- `src/ginkgo/livecore/live_engine.py` — 功能迁移到 `TimeControlledEventEngine` 可选组件
- `src/ginkgo/trading/paper/paper_engine.py` — 完全废弃，功能由 PAPER 模式覆盖

**迁移内容**:
- `HeartbeatMonitor` → `TimeControlledEventEngine` 可选组件（PAPER/LIVE 启用）
- `BrokerRecoveryService` → `TimeControlledEventEngine` 可选组件（仅 LIVE 启用）
- `DataSyncService`（余额/持仓同步）→ LIVE 模式下由 Portfolio 调用

### 4.5 Phase 5: SimBroker 增强

**文件**: `src/ginkgo/trading/brokers/sim_broker.py`

- 实现 `_is_limit_blocked()` — 当前是 stub，返回 False
- 新增 `match_on_tick` 模式 — Tick 级别订单匹配

---

## 5. 不变的部分

- **Strategy**: `BaseStrategy.cal()` 接口与数据源无关
- **PortfolioBase**: 内部资金管理，BACKTEST/PAPER 共用
- **RiskManagement**: `BaseRiskManagement` 双重机制与执行模式无关
- **Analyzer**: 与运行模式无关
- **Event 系统**: 事件链路不变

---

## 6. 执行顺序

```
Phase 1 (三态分支) → Phase 2 (多 feeder/broker) → Phase 3 (Assembly PAPER) → Phase 4 (废弃独立Engine) → Phase 5 (SimBroker增强)
       ↓                        ↓                          ↓                            ↓                          ↓
    单元测试                 单元测试                    集成测试                     集成测试                    E2E 验证
```

---

## 7. 风险与约束

1. **向后兼容**: 所有改动不破坏现有 BACKTEST 模式
2. **多 feeder 并发**: 多个 LiveDataFeeder 同时 push 事件，队列线程安全
3. **SimBroker 涨跌停**: `_is_limit_blocked()` 需要接入实时行情数据
4. **LiveDataFeeder 超时**: PAPER 模式下断连时的容错处理
