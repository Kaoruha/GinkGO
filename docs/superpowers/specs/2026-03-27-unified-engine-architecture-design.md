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
3. Portfolio 与 LiveAccount 无关联，无法同步实盘资金
4. DataFeeder 和 Broker 是硬编码的，不支持动态切换

### 1.2 设计目标

**核心公式**: `一个策略，三种运行模式，零代码修改`

```
PAPER = LiveDataFeeder + SimBroker    (真实数据 + 虚拟成交)
LIVE  = LiveDataFeeder + RealBroker   (真实数据 + 真实成交)
BACKTEST = HistoricalFeeder + SimBroker (历史数据 + 虚拟成交)
```

---

## 2. 架构总览

### 2.1 分层架构

```
┌─────────────────────────────────────────────┐
│              Orchestrator                    │  ← 跨市场协调层
│  (多市场组合策略、套利、资金分配)              │
├─────────────────────────────────────────────┤
│    Engine(A股)  │  Engine(Crypto)  │  ...    │  ← 每市场一个引擎
│  ┌───────────┐  │  ┌───────────┐  │         │
│  │ DataFeeder│  │  │ DataFeeder│  │         │
│  │(LiveData) │  │  │(LiveData) │  │         │
│  ├───────────┤  │  ├───────────┤  │         │
│  │  Broker   │  │  │  Broker   │  │         │
│  │(Sim/Real) │  │  │(Sim/Real) │  │         │
│  └───────────┘  │  └───────────┘  │         │
│  ┌───────────┐  │  ┌───────────┐  │         │
│  │ Strategy  │  │  │ Strategy  │  │         │
│  │ Portfolio │  │  │ Portfolio │  │         │
│  │ RiskMgr   │  │  │ RiskMgr   │  │         │
│  └───────────┘  │  └───────────┘  │         │
└─────────────────────────────────────────────┘
```

### 2.2 两个正交维度

| | HistoricalFeeder | LiveDataFeeder |
|---|---|---|
| **SimBroker** | BACKTEST | **PAPER** |
| **RealBroker** | N/A | LIVE |

---

## 3. 核心设计决策

### 3.1 引擎分层：Engine-per-Market + Orchestrator

**决策**: 底层每个市场一个独立 Engine，上层 Orchestrator 协调跨市场策略。

**理由**:
- 单市场策略是主要场景，保持简单
- 跨市场套利策略通过 Orchestrator 层组合多个 Engine
- Orchestrator 是未来扩展，本次不实现

**市场识别**: 通过 symbol pattern 动态路由，不依赖配置文件写死：
- `BTC/USDT` → Crypto Engine → OKXDataFeeder + OKXBroker
- `000001.SZ` → A-Share Engine → EastMoneyFeeder + SimBroker
- `AAPL` → US Stock Engine → AlpacaFeeder + AlpacaBroker

### 3.2 时间模式：三态切换

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

### 3.3 资金管理模式

```
BACKTEST: Portfolio 内部虚拟资金（现有逻辑不变）
PAPER:    Portfolio 内部虚拟资金（与 BACKTEST 相同逻辑）
LIVE:     Portfolio 从 Broker 查询真实余额（需要同步机制）
```

**PAPER vs LIVE 的关键差异只在 Broker 层**，Portfolio 层面 PAPER 与 BACKTEST 行为一致。

### 3.4 DataFeeder 路由

DataFeeder 不做聚合，每个 Engine 绑定一个 DataFeeder。路由规则：

```python
class DataFeederRouter:
    """根据 symbol pattern 选择 DataFeeder"""

    ROUTES = [
        (r'^BTC/.*|ETH/.*|SOL/.*', OKXDataFeeder),
        (r'\.SZ$|\.SH$', EastMoneyFeeder),
        (r'^[A-Z]+$', AlpacaFeeder),  # 纯字母 → 美股
    ]

    def resolve(self, symbol: str) -> type:
        for pattern, feeder_class in self.ROUTES:
            if re.match(pattern, symbol):
                return feeder_class
        raise ValueError(f"No feeder for symbol: {symbol}")
```

### 3.5 Broker 路由

类似 DataFeeder，根据 symbol 的市场选择 Broker：

```python
class BrokerRouter:
    """根据 execution_mode + symbol 选择 Broker"""

    def resolve(self, symbol: str, mode: EXECUTION_MODE):
        market = self._detect_market(symbol)
        if mode in (EXECUTION_MODE.BACKTEST, EXECUTION_MODE.PAPER):
            return SimBroker  # 所有市场共用模拟撮合
        else:
            return REAL_BROKERS[market]  # OKXBroker / AlpacaBroker / ...
```

---

## 4. 模块重构清单

### 4.1 Phase 1: Engine 三态支持

**文件**: `src/ginkgo/trading/engines/time_controlled_engine.py`

将 16 处二元分支改为三态，按影响分组：

| 位置 | 功能 | BACKTEST | PAPER | LIVE |
|------|------|----------|-------|------|
| `main_loop()` L248 | 队列等待 | timeout=0.01 | blocking wait | blocking wait |
| `_initialize_components()` L182 | 时间提供者 | LogicalTime | SystemTime | SystemTime |
| `_initialize_components()` L202 | 线程池 | 无 | ThreadPoolExecutor | ThreadPoolExecutor |
| `main_loop()` L304 | 空队列处理 | 推进时间 | 继续等待 | 继续等待 |
| `_setup_data_feeder()` L735 | DataFeeder | BacktestFeeder | LiveDataFeeder | LiveDataFeeder |

### 4.2 Phase 2: EngineAssemblyService PAPER 模式

**文件**: `src/ginkgo/trading/services/engine_assembly_service.py`

新增 `assemble_paper_engine()` 方法：

```python
def assemble_paper_engine(self, config: EngineConfig) -> EngineHistoric:
    """组装模拟盘引擎: LiveDataFeeder + SimBroker"""
    engine = EngineHistoric(execution_mode=EXECUTION_MODE.PAPER)
    engine.set_data_feeder(OKXDataFeeder(...))  # 或其他 LiveDataFeeder
    engine.set_broker(SimBroker(...))
    return engine
```

修改 `_setup_data_feeder_for_engine()` 支持根据 execution_mode 选择 feeder。

### 4.3 Phase 3: SimBroker 增强

**文件**: `src/ginkgo/trading/brokers/sim_broker.py`

- 实现 `_is_limit_blocked()` — 当前是 stub，返回 False
- 新增 `match_on_tick` 模式 — Tick 级别订单匹配（PAPER 精确撮合）

### 4.4 Phase 4: Orchestrator 层（未来）

**新增文件**: `src/ginkgo/trading/orchestrator/`

跨市场策略协调，暂不实现。本次设计预留接口：

```python
class IOrchestrator(ABC):
    """跨市场引擎协调器接口"""

    @abstractmethod
    def register_engine(self, market: str, engine: EngineBase) -> None: ...

    @abstractmethod
    def start_all(self) -> None: ...

    @abstractmethod
    def stop_all(self) -> None: ...
```

---

## 5. 不变的部分

以下模块在本次重构中**不需要修改**：

- **Strategy**: 已有 `BaseStrategy.cal()` 接口，与数据源无关
- **RiskManagement**: 已有 `BaseRiskManagement` 双重机制，与执行模式无关
- **PortfolioBase**: 内部资金管理，BACKTEST/PAPER 共用
- **Analyzer**: 分析器与运行模式无关
- **MLiveAccount**: 仅存储 API 凭证，不涉及资金/持仓同步
- **Event 系统**: 事件链路 `PriceUpdate → Strategy → Signal → Portfolio → Order → Fill` 不变

---

## 6. 执行顺序

```
Phase 1 (Engine 三态)  ─→  Phase 2 (Assembly PAPER)  ─→  Phase 3 (SimBroker 增强)
     ↓                                                              ↓
  单元测试覆盖                                                    E2E 验证
                                                               (PAPER 模式完整流程)

Phase 4 (Orchestrator) — 未来迭代，本次不实现
```

**估计改动量**:
- Phase 1: ~16 处分支修改 + 测试
- Phase 2: ~50 行新增 + 测试
- Phase 3: ~100 行（涨跌停实现 + Tick 撮合）
- 总计: ~3 个文件核心修改，预计新增 ~300 行代码

---

## 7. 风险与约束

1. **向后兼容**: 所有改动不破坏现有 BACKTEST 模式的行为
2. **SimBroker 涨跌停**: `_is_limit_blocked()` 需要接入实时行情数据判断涨跌停
3. **LiveDataFeeder 超时**: PAPER 模式下 DataFeeder 断连时的容错处理
4. **Broker 路由精度**: symbol pattern 匹配需要覆盖所有支持的 symbol 格式
