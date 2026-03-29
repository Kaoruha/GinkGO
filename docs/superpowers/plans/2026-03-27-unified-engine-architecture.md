# 统一引擎架构实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 让 TimeControlledEventEngine 统一支持 BACKTEST/PAPER/LIVE 三种模式，废弃独立的 LiveEngine 和 PaperTradingEngine。

**Architecture:** 在现有 TimeControlledEventEngine 上做最小改造。PAPER 在所有 13 处分支中与 LIVE 行为一致，因此核心改动是验证 PAPER 走通 LIVE 路径 + 支持多 DataFeeder。TradeGateway 已有多 Broker 路由能力，只需改进 symbol pattern 匹配。

**Tech Stack:** Python 3.12.8, pytest, SQLAlchemy

---

## 文件结构映射

| 文件 | 职责 | 改动类型 |
|------|------|---------|
| `src/ginkgo/trading/engines/time_controlled_engine.py` | 核心引擎，三态分支 | 修改 |
| `src/ginkgo/trading/gateway/trade_gateway.py` | 多 Broker 路由，symbol pattern | 修改 |
| `src/ginkgo/trading/services/engine_assembly_service.py` | 引擎装配，新增 PAPER 模式 | 修改 |
| `src/ginkgo/trading/brokers/sim_broker.py` | 涨跌停实现 | 修改 |
| `src/ginkgo/livecore/live_engine.py` | 标记废弃 | 修改 |
| `src/ginkgo/trading/paper/paper_engine.py` | 标记废弃 | 修改 |
| `tests/unit/trading/engines/test_paper_mode.py` | PAPER 模式单元测试 | 新建 |
| `tests/unit/trading/engines/test_multi_feeder.py` | 多 DataFeeder 单元测试 | 新建 |
| `tests/unit/trading/gateway/test_symbol_pattern.py` | TradeGateway symbol pattern 测试 | 新建 |

---

## Task 1: PAPER 模式初始化验证

**Files:**
- Create: `tests/unit/trading/engines/test_paper_mode.py`
- Modify: `src/ginkgo/trading/engines/time_controlled_engine.py` (无需改动，仅验证)

验证 PAPER 模式在初始化时走通 LIVE 路径（现有代码已支持，只需测试覆盖）。

- [ ] **Step 1: 写失败测试 — PAPER 模式使用 SystemTimeProvider**

```python
import pytest
from ginkgo.trading.engines.time_controlled_engine import TimeControlledEventEngine
from ginkgo.enums import EXECUTION_MODE
from ginkgo.trading.time.providers import SystemTimeProvider

class TestPaperModeInitialization:
    """验证 PAPER 模式初始化行为"""

    def test_paper_mode_uses_system_time_provider(self):
        """PAPER 模式应使用 SystemTimeProvider"""
        engine = TimeControlledEventEngine(
            name="TestPaper",
            mode=EXECUTION_MODE.PAPER,
        )
        assert isinstance(engine._time_provider, SystemTimeProvider)

    def test_paper_mode_creates_thread_pool(self):
        """PAPER 模式应创建 ThreadPoolExecutor"""
        from concurrent.futures import ThreadPoolExecutor
        engine = TimeControlledEventEngine(
            name="TestPaper",
            mode=EXECUTION_MODE.PAPER,
        )
        assert engine._executor is not None
        assert isinstance(engine._executor, ThreadPoolExecutor)
        engine.stop()

    def test_paper_mode_uses_system_time_mode(self):
        """PAPER 模式的 TimeInfo 应为 TIME_MODE.SYSTEM"""
        from ginkgo.enums import TIME_MODE
        engine = TimeControlledEventEngine(
            name="TestPaper",
            mode=EXECUTION_MODE.PAPER,
        )
        time_info = engine.get_time_info()
        assert time_info.time_mode == TIME_MODE.SYSTEM
        assert not time_info.is_logical_time
```

- [ ] **Step 2: 运行测试验证通过**

Run: `cd /home/kaoru/Ginkgo && python -m pytest tests/unit/trading/engines/test_paper_mode.py -v`
Expected: PASS（现有代码已支持，PAPER 走 else 分支）

- [ ] **Step 3: 写失败测试 — PAPER 模式运行时行为**

```python
    def test_paper_mode_blocking_queue_wait(self):
        """PAPER 模式应使用阻塞队列等待（与 LIVE 一致）"""
        engine = TimeControlledEventEngine(
            name="TestPaper",
            mode=EXECUTION_MODE.PAPER,
        )
        # 验证 mode 不是 BACKTEST（走 else 分支）
        assert engine.mode == EXECUTION_MODE.PAPER
        assert engine.mode != EXECUTION_MODE.BACKTEST

    def test_paper_mode_no_auto_time_advance(self):
        """PAPER 模式不应自动推进时间"""
        engine = TimeControlledEventEngine(
            name="TestPaper",
            mode=EXECUTION_MODE.PAPER,
        )
        # advance_time_to 在非 BACKTEST 模式应返回 False
        result = engine.advance_time_to(engine.now())
        assert result is False

    def test_paper_mode_no_backtest_task_on_run(self):
        """PAPER 模式 run() 不应创建 BacktestTask"""
        engine = TimeControlledEventEngine(
            name="TestPaper",
            mode=EXECUTION_MODE.PAPER,
        )
        # run() 中只有 BACKTEST 模式才调用 _create_backtest_task()
        # PAPER 模式应跳过，不会报错
        # 这里只验证 run() 能正常启动（不实际启动事件循环）
        engine.stop()
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd /home/kaoru/Ginkgo && python -m pytest tests/unit/trading/engines/test_paper_mode.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add tests/unit/trading/engines/test_paper_mode.py
git commit -m "test: Add PAPER mode initialization and runtime tests"
```

---

## Task 2: 多 DataFeeder 支持

**Files:**
- Create: `tests/unit/trading/engines/test_multi_feeder.py`
- Modify: `src/ginkgo/trading/engines/time_controlled_engine.py:814-855`

当前 `set_data_feeder()` 只支持单个 feeder（`self._datafeeder`）。需要扩展为支持多个 feeder，所有 feeder 的事件都入同一队列。

- [ ] **Step 1: 写失败测试 — 多 feeder 注册和事件分发**

```python
import pytest
from unittest.mock import MagicMock, patch
from ginkgo.trading.engines.time_controlled_engine import TimeControlledEventEngine
from ginkgo.enums import EXECUTION_MODE

class TestMultiDataFeeder:
    """验证多 DataFeeder 支持"""

    def test_add_data_feeder_stores_multiple(self):
        """add_data_feeder 应能添加多个 feeder"""
        engine = TimeControlledEventEngine(
            name="TestMultiFeeder",
            mode=EXECUTION_MODE.PAPER,
        )
        feeder1 = MagicMock(name="Feeder1")
        feeder1.name = "Feeder1"
        feeder2 = MagicMock(name="Feeder2")
        feeder2.name = "Feeder2"

        engine.add_data_feeder(feeder1)
        engine.add_data_feeder(feeder2)

        assert len(engine._data_feeders) == 2
        engine.stop()

    def test_set_data_feeder_still_works(self):
        """set_data_feeder 向后兼容，仍支持单个 feeder"""
        engine = TimeControlledEventEngine(
            name="TestSingle",
            mode=EXECUTION_MODE.PAPER,
        )
        feeder = MagicMock(name="SingleFeeder")
        feeder.name = "SingleFeeder"

        engine.set_data_feeder(feeder)

        assert len(engine._data_feeders) == 1
        engine.stop()

    def test_add_data_feeder_binds_engine_and_publisher(self):
        """add_data_feeder 应绑定引擎和事件发布器"""
        engine = TimeControlledEventEngine(
            name="TestBinding",
            mode=EXECUTION_MODE.PAPER,
        )
        feeder = MagicMock(name="BoundFeeder")
        feeder.name = "BoundFeeder"

        engine.add_data_feeder(feeder)

        feeder.bind_engine.assert_called_once_with(engine)
        feeder.set_event_publisher.assert_called_once()
        engine.stop()

    def test_add_data_feeder_propagates_to_portfolios(self):
        """add_data_feeder 应将 feeder 传播到所有 portfolio"""
        engine = TimeControlledEventEngine(
            name="TestPropagation",
            mode=EXECUTION_MODE.PAPER,
        )
        feeder = MagicMock(name="PropFeeder")
        feeder.name = "PropFeeder"
        portfolio = MagicMock(name="TestPortfolio")
        portfolio.bind_data_feeder = MagicMock()

        engine.add_portfolio(portfolio)
        engine.add_data_feeder(feeder)

        portfolio.bind_data_feeder.assert_called_with(feeder)
        engine.stop()
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd /home/kaoru/Ginkgo && python -m pytest tests/unit/trading/engines/test_multi_feeder.py -v`
Expected: FAIL — `AttributeError: 'TimeControlledEventEngine' object has no attribute 'add_data_feeder'`

- [ ] **Step 3: 实现 `add_data_feeder()` 方法**

在 `src/ginkgo/trading/engines/time_controlled_engine.py` 的 `_initialize_components()` 中初始化列表，在 `set_data_feeder()` 旁边添加 `add_data_feeder()`：

```python
# 在 _initialize_components() 中添加：
self._data_feeders: list = []

# 在 set_data_feeder() 旁边添加：
def add_data_feeder(self, feeder) -> None:
    """添加数据馈送器（支持多个 feeder）"""
    self._data_feeders.append(feeder)
    self._datafeeder = feeder  # 向后兼容，最后一个 feeder 作为默认

    # 绑定引擎到feeder
    feeder.bind_engine(self)

    # 绑定事件发布器
    if hasattr(feeder, "set_event_publisher"):
        feeder.set_event_publisher(self.put)

    # 设置时间提供者
    if hasattr(feeder, "set_time_provider") and self._time_provider is not None:
        feeder.set_time_provider(self._time_provider)

    # 注册事件处理器
    self._auto_register_component_events(feeder)

    # 传播给所有 portfolio
    for portfolio in self.portfolios:
        if hasattr(portfolio, 'bind_data_feeder'):
            portfolio.bind_data_feeder(feeder)

    GLOG.INFO(f"Data feeder {feeder.name} added (total: {len(self._data_feeders)})")
```

同时修改现有 `set_data_feeder()` 使其也维护 `_data_feeders` 列表：

```python
def set_data_feeder(self, feeder) -> None:
    """设置数据馈送器（向后兼容，等同于清空后添加）"""
    self._data_feeders = []
    self.add_data_feeder(feeder)
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd /home/kaoru/Ginkgo && python -m pytest tests/unit/trading/engines/test_multi_feeder.py -v`
Expected: PASS

- [ ] **Step 5: 运行现有测试确保无回归**

Run: `cd /home/kaoru/Ginkgo && python -m pytest tests/e2e/python_backtest_e2e.py -v`
Expected: PASS（现有 E2E 测试使用 set_data_feeder，向后兼容）

- [ ] **Step 6: 提交**

```bash
git add tests/unit/trading/engines/test_multi_feeder.py src/ginkgo/trading/engines/time_controlled_engine.py
git commit -m "feat: Add multi-DataFeeder support with backward compatibility"
```

---

## Task 3: TradeGateway 动态 Symbol Pattern

**Files:**
- Create: `tests/unit/trading/gateway/test_symbol_pattern.py`
- Modify: `src/ginkgo/trading/gateway/trade_gateway.py:87-154`

当前 `_code_market_mapping` 写死了示例 symbol，需要改为动态 pattern 匹配。

- [ ] **Step 1: 写失败测试 — 动态 pattern 匹配**

```python
import pytest
from ginkgo.trading.gateway.trade_gateway import TradeGateway
from ginkgo.trading.brokers.sim_broker import SimBroker

class TestSymbolPatternMatching:
    """验证动态 symbol pattern 匹配"""

    def _make_brokers(self):
        sim = SimBroker()
        sim.market = "SIM"
        sim.name = "SimBroker"
        return [sim]

    def test_a_share_pattern_sz(self):
        """000001.SZ 应识别为 A股"""
        gw = TradeGateway(brokers=self._make_brokers())
        assert gw._get_market_by_code("000001.SZ") == "A股"

    def test_a_share_pattern_sh(self):
        """600000.SH 应识别为 A股"""
        gw = TradeGateway(brokers=self._make_brokers())
        assert gw._get_market_by_code("600000.SH") == "A股"

    def test_crypto_pattern(self):
        """BTC/USDT 应识别为 Crypto"""
        gw = TradeGateway(brokers=self._make_brokers())
        assert gw._get_market_by_code("BTC/USDT") == "Crypto"

    def test_hk_stock_pattern(self):
        """00700.HK 应识别为 港股"""
        gw = TradeGateway(brokers=self._make_brokers())
        assert gw._get_market_by_code("00700.HK") == "港股"

    def test_unknown_symbol_defaults(self):
        """未识别的 symbol 不应崩溃"""
        gw = TradeGateway(brokers=self._make_brokers())
        result = gw._get_market_by_code("UNKNOWN123")
        assert result is not None  # 不崩溃，返回默认值
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd /home/kaoru/Ginkgo && python -m pytest tests/unit/trading/gateway/test_symbol_pattern.py -v`
Expected: FAIL — `_get_market_by_code("BTC/USDT")` 返回 `'A股'`（默认值），不是 `'Crypto'`

- [ ] **Step 3: 实现 pattern 匹配**

修改 `_get_market_by_code()` 和 `_setup_market_mapping()`：

```python
import re

def _setup_market_mapping(self):
    """建立市场到Broker的映射"""
    for broker in self.brokers:
        if hasattr(broker, 'market'):
            self._market_mapping[broker.market] = broker

    # 动态 pattern 匹配规则（按优先级排序）
    self._symbol_patterns = [
        # Crypto: BTC/USDT, ETH/USDT, SOL/USDT 等
        (re.compile(r'^[A-Z]+/USDT$'), 'Crypto'),
        # 港股: 00700.HK
        (re.compile(r'^\d{5}\.HK$'), '港股'),
        # A股: 000001.SZ, 600000.SH, 300001.SZ
        (re.compile(r'^\d{6}\.(SZ|SH)$'), 'A股'),
        # 期货: IF2312, IC2312, IH2312
        (re.compile(r'^(IF|IC|IH|IM|MO)\d{4}$'), '期货'),
        # 美股: AAPL, TSLA, MSFT (纯大写字母)
        (re.compile(r'^[A-Z]{1,5}$'), '美股'),
    ]

    # SIM broker 作为所有市场的默认
    if "SIM" in self._market_mapping:
        sim_broker = self._market_mapping["SIM"]
        for market in ['A股', '港股', '美股', '期货', 'Crypto']:
            if market not in self._market_mapping:
                self._market_mapping[market] = sim_broker

def _get_market_by_code(self, code: str) -> Optional[str]:
    """根据股票代码动态判断市场"""
    if not code:
        return 'A股'

    # 遍历 pattern 规则
    for pattern, market in self._symbol_patterns:
        if pattern.match(code):
            return market

    return 'A股'  # 默认为A股
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd /home/kaoru/Ginkgo && python -m pytest tests/unit/trading/gateway/test_symbol_pattern.py -v`
Expected: PASS

- [ ] **Step 5: 运行现有 TradeGateway 测试**

Run: `cd /home/kaoru/Ginkgo && python -m pytest tests/unit/live/test_trade_gateway_adapter.py -v`
Expected: PASS

- [ ] **Step 6: 提交**

```bash
git add tests/unit/trading/gateway/test_symbol_pattern.py src/ginkgo/trading/gateway/trade_gateway.py
git commit -m "feat: Replace hardcoded symbol mapping with dynamic pattern matching"
```

---

## Task 4: EngineAssemblyService PAPER 模式

**Files:**
- Create: `tests/unit/trading/services/test_engine_assembly_paper.py`
- Modify: `src/ginkgo/trading/services/engine_assembly_service.py`

让 `assemble_backtest_engine()` 支持 PAPER 模式组装（LiveDataFeeder + SimBroker）。

- [ ] **Step 1: 写失败测试**

```python
import pytest
from unittest.mock import MagicMock, patch
from ginkgo.enums import EXECUTION_MODE

class TestEngineAssemblyPaper:
    """验证 PAPER 模式引擎装配"""

    @patch('ginkgo.trading.services.engine_assembly_service.TimeControlledEventEngine')
    @patch('ginkgo.trading.services.engine_assembly_service.OKXDataFeeder')
    @patch('ginkgo.trading.services.engine_assembly_service.SimBroker')
    def test_assemble_paper_engine_creates_correct_components(self, MockSimBroker, MockOKXFeeder, MockEngine):
        """PAPER 模式应创建 LiveDataFeeder + SimBroker"""
        from ginkgo.trading.services.engine_assembly_service import EngineAssemblyService

        service = EngineAssemblyService()
        service.initialize()

        result = service.assemble_backtest_engine(
            engine_id="test-paper-001",
            execution_mode=EXECUTION_MODE.PAPER,
        )

        assert result.is_success()
        # 验证创建的引擎 mode 为 PAPER
        # （具体断言取决于 assemble_backtest_engine 内部实现）
```

注意：这个测试的具体断言需要根据 `assemble_backtest_engine()` 当前实现调整。先写基本结构，实现时再完善。

- [ ] **Step 2: 运行测试确认当前状态**

Run: `cd /home/kaoru/Ginkgo && python -m pytest tests/unit/trading/services/test_engine_assembly_paper.py -v`
Expected: 可能 PASS 也可能 FAIL，取决于当前实现是否已支持 PAPER

- [ ] **Step 3: 修改 assemble_backtest_engine 支持 PAPER**

在 `_setup_data_feeder_for_engine()` 中根据 `execution_mode` 选择 feeder：

```python
# 在 _setup_data_feeder_for_engine() 中:
if execution_mode in (EXECUTION_MODE.PAPER, EXECUTION_MODE.LIVE):
    feeder = OKXDataFeeder(...)  # 或其他 LiveDataFeeder
else:
    feeder = BacktestFeeder(...)
```

在 Broker 选择中，PAPER 使用 SimBroker（现有逻辑不变）。

- [ ] **Step 4: 运行测试验证通过**

Run: `cd /home/kaoru/Ginkgo && python -m pytest tests/unit/trading/services/test_engine_assembly_paper.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add tests/unit/trading/services/test_engine_assembly_paper.py src/ginkgo/trading/services/engine_assembly_service.py
git commit -m "feat: Add PAPER mode support in EngineAssemblyService"
```

---

## Task 5: 标记废弃 LiveEngine 和 PaperTradingEngine

**Files:**
- Modify: `src/ginkgo/livecore/live_engine.py`
- Modify: `src/ginkgo/trading/paper/paper_engine.py`

添加 deprecation warning，不删除代码（保持向后兼容）。

- [ ] **Step 1: 在 LiveEngine 和 PaperTradingEngine 中添加 deprecation**

```python
import warnings

class LiveEngine:
    """
    实盘交易引擎

    .. deprecated::
        此类已废弃。请使用 TimeControlledEventEngine(execution_mode=EXECUTION_MODE.LIVE)。
        将在未来版本中移除。
    """

    def __init__(self):
        warnings.warn(
            "LiveEngine is deprecated. Use TimeControlledEventEngine(mode=EXECUTION_MODE.LIVE) instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        # ... 原有代码 ...
```

PaperTradingEngine 同理。

- [ ] **Step 2: 运行现有测试确认无回归**

Run: `cd /home/kaoru/Ginkgo && python -m pytest tests/unit/live/test_livecore_main.py tests/trading/paper/test_paper_engine.py -v`
Expected: PASS（测试应忽略 deprecation warning 或有 filter）

- [ ] **Step 3: 提交**

```bash
git add src/ginkgo/livecore/live_engine.py src/ginkgo/trading/paper/paper_engine.py
git commit -m "deprecate: Mark LiveEngine and PaperTradingEngine as deprecated"
```

---

## Task 6: SimBroker 涨跌停实现

**Files:**
- Create: `tests/unit/trading/brokers/test_sim_broker_limit.py`
- Modify: `src/ginkgo/trading/brokers/sim_broker.py` — `_is_limit_blocked()` 方法

当前 `_is_limit_blocked()` 是 stub，返回 False。

- [ ] **Step 1: 写失败测试**

```python
import pytest
from decimal import Decimal
from unittest.mock import MagicMock
from ginkgo.trading.brokers.sim_broker import SimBroker

class TestSimBrokerLimitPrice:
    """验证 SimBroker 涨跌停检测"""

    def test_buy_at_limit_up_should_block(self):
        """涨停价买单应被拦截"""
        broker = SimBroker()
        # 设置当前价格 = 涨停价
        broker._current_market_data = {
            "000001.SZ": {
                "limit_up": Decimal("10.00"),
                "limit_down": Decimal("9.00"),
                "current_price": Decimal("10.00"),
            }
        }
        # 买入价格为涨停价应被拦截
        assert broker._is_limit_blocked("000001.S", Decimal("10.00"), "buy") is True

    def test_buy_below_limit_up_should_pass(self):
        """低于涨停价的买单应通过"""
        broker = SimBroker()
        broker._current_market_data = {
            "000001.SZ": {
                "limit_up": Decimal("10.00"),
                "limit_down": Decimal("9.00"),
                "current_price": Decimal("9.50"),
            }
        }
        assert broker._is_limit_blocked("000001.SZ", Decimal("9.80"), "buy") is False

    def test_sell_at_limit_down_should_block(self):
        """跌停价卖单应被拦截"""
        broker = SimBroker()
        broker._current_market_data = {
            "000001.SZ": {
                "limit_up": Decimal("10.00"),
                "limit_down": Decimal("9.00"),
                "current_price": Decimal("9.00"),
            }
        }
        assert broker._is_limit_blocked("000001.SZ", Decimal("9.00"), "sell") is True

    def test_sell_above_limit_down_should_pass(self):
        """高于跌停价的卖单应通过"""
        broker = SimBroker()
        broker._current_market_data = {
            "000001.SZ": {
                "limit_up": Decimal("10.00"),
                "limit_down": Decimal("9.00"),
                "current_price": Decimal("9.50"),
            }
        }
        assert broker._is_limit_blocked("000001.SZ", Decimal("9.20"), "sell") is False

    def test_no_market_data_should_pass(self):
        """无市场数据时应通过（不阻塞）"""
        broker = SimBroker()
        assert broker._is_limit_blocked("UNKNOWN.SZ", Decimal("10.00"), "buy") is False
```

- [ ] **Step 2: 运行测试验证失败**

Run: `cd /home/kaoru/Ginkgo && python -m pytest tests/unit/trading/brokers/test_sim_broker_limit.py -v`
Expected: FAIL — `_is_limit_blocked()` 总是返回 False

- [ ] **Step 3: 实现 `_is_limit_blocked()`**

```python
def _is_limit_blocked(self, code: str, price: Decimal, direction: str) -> bool:
    """检查是否触发涨跌停限制"""
    market_data = self._current_market_data.get(code)
    if not market_data:
        return False

    limit_up = market_data.get("limit_up")
    limit_down = market_data.get("limit_down")

    if direction == "buy" and limit_up is not None:
        return price >= limit_up
    elif direction == "sell" and limit_down is not None:
        return price <= limit_down

    return False
```

- [ ] **Step 4: 运行测试验证通过**

Run: `cd /home/kaoru/Ginkgo && python -m pytest tests/unit/trading/brokers/test_sim_broker_limit.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add tests/unit/trading/brokers/test_sim_broker_limit.py src/ginkgo/trading/brokers/sim_broker.py
git commit -m "feat: Implement _is_limit_blocked() for price limit detection in SimBroker"
```

---

## Task 7: 全量回归测试

**Files:** 无新改动

确保所有改动不破坏现有功能。

- [ ] **Step 1: 运行全部引擎相关测试**

Run: `cd /home/kaoru/Ginkgo && python -m pytest tests/unit/trading/engines/ tests/unit/trading/gateway/ tests/unit/trading/brokers/ tests/unit/live/ tests/e2e/python_backtest_e2e.py -v`

- [ ] **Step 2: 验证 BACKTEST 模式 E2E 通过**

Run: `cd /home/kaoru/Ginkgo && python -m pytest tests/e2e/python_backtest_e2e.py -v`

- [ ] **Step 3: 修复发现的问题（如有）**

- [ ] **Step 4: 提交修复**

```bash
git commit -m "fix: Fix regression issues found in integration tests"
```

---

## 依赖关系

```
Task 1 (PAPER 初始化测试)
  ↓ 无依赖
Task 2 (多 DataFeeder) ← 可并行
  ↓ 无依赖
Task 3 (TradeGateway pattern) ← 可并行
  ↓
Task 4 (Assembly PAPER)
  ↓
Task 5 (废弃标记)
  ↓
Task 6 (SimBroker 涨跌停) ← 可并行
  ↓
Task 7 (回归测试)
```

Task 1/2/3/6 之间无依赖，可并行。Task 4 依赖 Task 2/3。Task 7 在所有完成后执行。
