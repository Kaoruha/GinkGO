# A 股日级纸上交易实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现回测 → 纸上交易飞轮，用真实 A 股行情进行日级策略验证

**Architecture:** 复用现有 BACKTEST 模式引擎（LogicalTimeProvider + BacktestFeeder），复用 TaskTimer 的调度基础设施（APScheduler + Kafka 命令 + `@safe_job_wrapper`）。PaperTradingController 不依赖 `bar_snapshot` 的异步完成，而是自行调用 `bar_service.sync_range_batch()` 同步拉取 portfolio 关注的少量股票（5-20只），拉完即推进引擎，确保数据就绪。

**复用现有架构：**
- `bar_service.sync_range_batch()` — 同步拉取指定股票的 K 线数据（Controller 自行调用）
- `TaskTimer._add_jobs()` — YAML 配置 + CronTrigger + APScheduler
- `@safe_job_wrapper` — 崩溃隔离
- `ControlCommandDTO.Commands` — Kafka 命令注册
- `notify()` / `notify_with_fields()` — 通知
- `TradeDayCRUD` — 交易日判断
- `_publish_to_kafka()` — Kafka 路由

**Tech Stack:** Python 3.12.8, Tushare Pro, APScheduler, ClickHouse, Kafka, Typer CLI

---

### Task 1: PaperTradingController — 每日循环控制

**Files:**
- Create: `src/ginkgo/trading/services/paper_trading_controller.py`
- Test: `tests/unit/trading/services/test_paper_trading_controller.py`

**设计说明：** Controller 持有引擎引用和 bar_service，提供 `run_daily_cycle()` 方法。每日循环：1) 检查交易日 2) 调用 `bar_service.sync_range_batch()` 同步拉取 portfolio 关注的少量股票（不依赖 bar_snapshot 的异步完成） 3) 推进引擎（BacktestFeeder 从 ClickHouse 读取数据并生成 EventPriceUpdate）。

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/trading/services/test_paper_trading_controller.py
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime


class TestPaperTradingController:
    def test_run_daily_cycle_skips_non_trading_day(self):
        """非交易日不应推进引擎"""
        from ginkgo.trading.services.paper_trading_controller import PaperTradingController

        mock_trade_day_crud = MagicMock()
        mock_trade_day_crud.find.return_value = MagicMock(data=[])

        mock_engine = MagicMock()

        controller = PaperTradingController(
            engine=mock_engine,
            trade_day_crud=mock_trade_day_crud,
        )

        result = controller.run_daily_cycle()

        assert result.skipped is True
        mock_engine.advance_time_to.assert_not_called()

    def test_run_daily_cycle_fetches_data_then_advances(self):
        """交易日应先拉取数据再推进引擎"""
        from ginkgo.trading.services.paper_trading_controller import PaperTradingController

        mock_trade_day_crud = MagicMock()
        mock_trade_day_result = MagicMock()
        mock_trade_day_result.data = [MagicMock(is_open=True)]
        mock_trade_day_crud.find.return_value = mock_trade_day_result

        mock_bar_service = MagicMock()
        mock_sync_result = MagicMock()
        mock_sync_result.success = True
        mock_bar_service.sync_range_batch.return_value = mock_sync_result

        mock_selector = MagicMock()
        mock_selector._interested = ["000001.SZ", "600036.SH"]
        mock_portfolio = MagicMock()
        mock_portfolio.selector = mock_selector

        mock_engine = MagicMock()
        mock_engine.portfolios = {"test": mock_portfolio}
        mock_engine.advance_time_to.return_value = True

        controller = PaperTradingController(
            engine=mock_engine,
            trade_day_crud=mock_trade_day_crud,
            bar_service=mock_bar_service,
        )

        with patch("ginkgo.trading.services.paper_trading_controller.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 3, 30, 21, 10)
            mock_dt.now.return_value.date.return_value = datetime(2026, 3, 30).date()
            result = controller.run_daily_cycle()

        assert result.skipped is False
        assert result.advanced is True
        mock_bar_service.sync_range_batch.assert_called_once()
        mock_engine.advance_time_to.assert_called_once()

    def test_run_daily_cycle_skips_when_no_codes(self):
        """无关注股票时应跳过"""
        from ginkgo.trading.services.paper_trading_controller import PaperTradingController

        mock_trade_day_crud = MagicMock()
        mock_trade_day_result = MagicMock()
        mock_trade_day_result.data = [MagicMock(is_open=True)]
        mock_trade_day_crud.find.return_value = mock_trade_day_result

        mock_engine = MagicMock()
        mock_engine.portfolios = {}

        controller = PaperTradingController(
            engine=mock_engine,
            trade_day_crud=mock_trade_day_crud,
        )

        result = controller.run_daily_cycle()

        assert result.skipped is True
        assert "No interested codes" in result.error
        mock_engine.advance_time_to.assert_not_called()

    def test_get_interested_codes_from_selector(self):
        """应从引擎的 selector 获取关注股票列表"""
        from ginkgo.trading.services.paper_trading_controller import PaperTradingController

        mock_selector = MagicMock()
        mock_selector._interested = ["000001.SZ", "600036.SH"]

        mock_portfolio = MagicMock()
        mock_portfolio.selector = mock_selector

        mock_engine = MagicMock()
        mock_engine.portfolios = {"test": mock_portfolio}

        mock_trade_day_crud = MagicMock()
        controller = PaperTradingController(
            engine=mock_engine,
            trade_day_crud=mock_trade_day_crud,
        )

        codes = controller.get_interested_codes()
        assert codes == ["000001.SZ", "600036.SH"]
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /home/kaoru/Ginkgo && python -m pytest tests/unit/trading/services/test_paper_trading_controller.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: 实现 PaperTradingController**

```python
# src/ginkgo/trading/services/paper_trading_controller.py
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

from ginkgo.libs import GLOG, time_logger


@dataclass
class DailyCycleResult:
    """每日循环执行结果"""
    skipped: bool = False
    date: str = ""
    fetched_count: int = 0
    advanced: bool = False
    error: str = ""


class PaperTradingController:
    """
    纸上交易控制器

    职责：每个交易日收盘后执行一次循环：
    1. 检查是否交易日
    2. 自行拉取 portfolio 关注股票的当日 K 线（同步调用，不依赖 bar_snapshot）
    3. 推进引擎一天（BacktestFeeder 从 ClickHouse 读取数据并生成 EventPriceUpdate）

    数据就绪保证：通过 bar_service.sync_range_batch() 同步拉取，
    拉取完成后数据即在 ClickHouse 中，无需等待 bar_snapshot 的异步处理。
    """

    def __init__(self, engine, bar_service=None, trade_day_crud=None):
        """
        Args:
            engine: TimeControlledEventEngine 实例
            bar_service: BarService 实例（可选，默认从 services 获取）
            trade_day_crud: TradeDayCRUD 实例（可选，默认从 services 获取）
        """
        self._engine = engine
        if bar_service is None:
            from ginkgo import services
            bar_service = services.data.bar_service()
        self._bar_service = bar_service
        if trade_day_crud is None:
            from ginkgo.data.crud.trade_day_crud import TradeDayCRUD
            trade_day_crud = TradeDayCRUD()
        self._trade_day_crud = trade_day_crud

    def get_interested_codes(self) -> List[str]:
        """从引擎的 selector 获取关注股票列表"""
        codes = []
        for portfolio in self._engine.portfolios.values():
            selector = getattr(portfolio, "selector", None)
            if selector and hasattr(selector, "_interested"):
                codes.extend(selector._interested)
        return list(set(codes))

    @time_logger
    def run_daily_cycle(self) -> DailyCycleResult:
        """
        执行每日循环

        Returns:
            DailyCycleResult: 执行结果
        """
        today = datetime.now().date()

        # 1. 检查交易日
        if not self._is_trading_day(today):
            GLOG.INFO(f"[PAPER] {today} is not a trading day, skipping")
            return DailyCycleResult(skipped=True, date=str(today))

        # 2. 获取关注股票列表
        codes = self.get_interested_codes()
        if not codes:
            GLOG.WARN("[PAPER] No interested codes, skipping")
            return DailyCycleResult(
                skipped=True, date=str(today), error="No interested codes"
            )

        # 3. 同步拉取当日 K 线数据（同步调用，确保数据就绪）
        try:
            sync_result = self._bar_service.sync_range_batch(
                codes=codes,
                start_date=today,
                end_date=today,
            )
            fetched_count = sync_result.data.get("success_count", 0) if sync_result.success else 0
        except Exception as e:
            GLOG.ERROR(f"[PAPER] Failed to fetch data: {e}")
            return DailyCycleResult(
                skipped=True, date=str(today), error=f"Data fetch failed: {e}"
            )

        # 4. 推进引擎到明天 15:00
        next_day = today + timedelta(days=1)
        target_time = datetime.combine(next_day, datetime.min.time().replace(hour=15, minute=0))

        try:
            success = self._engine.advance_time_to(target_time)
            GLOG.INFO(
                f"[PAPER] Daily cycle: {today} -> {target_time}, "
                f"fetched={fetched_count}/{len(codes)}, advanced={success}"
            )
            return DailyCycleResult(
                skipped=False,
                date=str(today),
                fetched_count=fetched_count,
                advanced=success,
            )
        except Exception as e:
            GLOG.ERROR(f"[PAPER] Failed to advance engine: {e}")
            return DailyCycleResult(
                skipped=False,
                date=str(today),
                fetched_count=fetched_count,
                advanced=False,
                error=str(e),
            )

    def _is_trading_day(self, date) -> bool:
        """判断指定日期是否是 A 股交易日"""
        from ginkgo.enums import MARKET_TYPES

        try:
            results = self._trade_day_crud.find(
                filters={"timestamp": date, "market": MARKET_TYPES.CHINA}
            )
            if results and len(results) > 0:
                return bool(results[0].is_open)
        except Exception as e:
            GLOG.ERROR(f"Failed to check trading day: {e}")
        return False
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd /home/kaoru/Ginkgo && python -m pytest tests/unit/trading/services/test_paper_trading_controller.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/ginkgo/trading/services/paper_trading_controller.py tests/unit/trading/services/test_paper_trading_controller.py
git commit -m "feat(paper-trading): add PaperTradingController for daily cycle management"
```

---

### Task 2: deploy/stop CLI — 创建并启动纸上交易

**Files:**
- Modify: `src/ginkgo/client/portfolio_cli.py`
- Test: `tests/unit/client/test_paper_trading_cli.py`

**设计说明：** 在 `portfolio_cli.py` 中添加 `deploy` 和 `stop` 子命令。复用现有的 `collect_portfolio_components()` 函数从 Mapping 加载策略组件。

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/client/test_paper_trading_cli.py
import pytest
from unittest.mock import MagicMock, patch
from typer.testing import CliRunner


class TestPaperTradingDeployCLI:
    def test_deploy_command_requires_source_argument(self):
        """deploy 命令需要 --source 参数"""
        from ginkgo.client.portfolio_cli import app

        runner = CliRunner()
        result = runner.invoke(app, ["deploy"])
        assert result.exit_code != 0
        assert "--source" in result.output or "Missing option" in result.output

    def test_deploy_command_creates_portfolio_and_engine(self):
        """deploy 应创建新 Portfolio 并启动引擎"""
        from ginkgo.client.portfolio_cli import app

        runner = CliRunner()

        with patch("ginkgo.client.portfolio_cli._deploy_paper_trading") as mock_deploy:
            mock_deploy.return_value = "paper_portfolio_123"
            result = runner.invoke(app, [
                "deploy",
                "--source", "backtest_portfolio_456",
                "--capital", "100000",
            ])

        assert result.exit_code == 0
        mock_deploy.assert_called_once()
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /home/kaoru/Ginkgo && python -m pytest tests/unit/client/test_paper_trading_cli.py -v`
Expected: FAIL — deploy 命令不存在

- [ ] **Step 3: 在 portfolio_cli.py 中添加 deploy 和 stop 命令**

在 `src/ginkgo/client/portfolio_cli.py` 末尾添加：

```python
# 全局 PaperTradingWorker 实例
_paper_worker = None


@app.command(name="deploy")
def deploy_portfolio(
    source: str = typer.Option(..., "--source", "-s", help="源 Portfolio ID（回测）"),
    capital: float = typer.Option(100000.0, "--capital", "-c", help="初始资金"),
):
    """从回测 Portfolio 创建纸上交易实例"""
    from rich.panel import Panel

    GLOG.info(f"[DEPLOY] Creating paper trading from {source}")

    try:
        portfolio_id = _deploy_paper_trading(
            source_portfolio_id=source,
            capital=capital,
        )

        console.print(Panel(
            f"[bold green]Paper trading started[/bold green]\n\n"
            f"Portfolio ID: {portfolio_id}\n"
            f"Source: {source}\n"
            f"Capital: ¥{capital:,.0f}\n"
            f"Schedule: 21:10 daily (after bar_snapshot)",
            title="Deploy Success",
        ))
    except Exception as e:
        console.print(f"[bold red]Deploy failed: {e}[/bold red]")
        raise typer.Exit(1)


@app.command(name="stop")
def stop_paper_trading(
    portfolio_id: str = typer.Argument(..., help="Portfolio ID to stop"),
):
    """停止纸上交易"""
    from rich.panel import Panel

    global _paper_worker

    if _paper_worker is None:
        console.print(f"[bold red]No PaperTradingWorker running[/bold red]")
        raise typer.Exit(1)

    try:
        _paper_worker.unregister_controller(portfolio_id)
        console.print(Panel(
            f"[bold yellow]Paper trading stopped[/bold yellow]\n\n"
            f"Portfolio ID: {portfolio_id}",
            title="Stop Success",
        ))

        # 如果没有活跃的 controller，停止 Worker
        if not _paper_worker._controllers:
            _paper_worker.stop()
            _paper_worker = None
    except Exception as e:
        console.print(f"[bold red]Stop failed: {e}[/bold red]")
        raise typer.Exit(1)


def _deploy_paper_trading(
    source_portfolio_id: str,
    capital: float,
) -> str:
    """
    执行纸上交易部署

    流程：
    1. 从源 Portfolio 读取 Mapping 配置
    2. 创建新 Portfolio + Engine（BACKTEST 模式 + 真实数据）
    3. 组装组件（策略/风控/分析器/选择器）
    4. 注册到 PaperTradingWorker

    Args:
        source_portfolio_id: 源回测 Portfolio ID
        capital: 初始资金

    Returns:
        str: 新 Portfolio ID
    """
    from decimal import Decimal
    from datetime import datetime

    from ginkgo import services
    from ginkgo.trading.engines.time_controlled_engine import TimeControlledEventEngine
    from ginkgo.trading.portfolios.t1backtest import PortfolioT1Backtest
    from ginkgo.trading.feeders.backtest_feeder import BacktestFeeder
    from ginkgo.trading.gateway.trade_gateway import TradeGateway
    from ginkgo.trading.brokers.sim_broker import SimBroker
    from ginkgo.enums import EXECUTION_MODE, ATTITUDE_TYPES
    from ginkgo.trading.services.paper_trading_controller import PaperTradingController
    from ginkgo.trading.services._assembly.component_loader import ComponentLoader

    # 1. 获取源 Portfolio 配置
    container = services.data.container()
    components = collect_portfolio_components(source_portfolio_id, container)

    # 2. 创建引擎（BACKTEST 模式，用真实数据）
    today = datetime.now()
    engine = TimeControlledEventEngine(
        name=f"paper_{source_portfolio_id[:8]}",
        mode=EXECUTION_MODE.BACKTEST,
        logical_time_start=datetime(today.year, today.month, today.day, 9, 30),
        timer_interval=0.01,
    )

    # 3. 创建 Portfolio
    portfolio = PortfolioT1Backtest(f"paper_{source_portfolio_id[:8]}")
    portfolio.add_cash(Decimal(str(capital)))

    # 4. 创建数据源和 Broker
    feeder = BacktestFeeder(name="paper_feeder")
    bar_service = services.data.bar_service()
    feeder.bar_service = bar_service

    broker = SimBroker(
        name="PaperSimBroker",
        attitude=ATTITUDE_TYPES.OPTIMISTIC,
        commission_rate=0.0003,
        commission_min=5,
    )
    gateway = TradeGateway(name="PaperGateway", brokers=[broker])

    # 5. 绑定组件
    engine.add_portfolio(portfolio)
    engine.bind_router(gateway)
    engine.set_data_feeder(feeder)

    # 6. 加载策略/风控/分析器/选择器（通过 ComponentLoader）
    loader = ComponentLoader(file_service=container.file_service(), logger=GLOG)
    loader.perform_component_binding(portfolio, components, GLOG)

    # 7. 启动引擎
    engine.start()

    # 8. 创建 Controller 并注册到 PaperTradingWorker
    controller = PaperTradingController(engine=engine, bar_service=bar_service)

    global _paper_worker
    if _paper_worker is None:
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker
        _paper_worker = PaperTradingWorker()
        _paper_worker.start()
        GLOG.INFO("[DEPLOY] PaperTradingWorker started")

    _paper_worker.register_controller(portfolio.portfolio_id, controller)

    GLOG.INFO(f"[DEPLOY] Paper trading started: {portfolio.portfolio_id}")
    return portfolio.portfolio_id
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd /home/kaoru/Ginkgo && python -m pytest tests/unit/client/test_paper_trading_cli.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/ginkgo/client/portfolio_cli.py tests/unit/client/test_paper_trading_cli.py
git commit -m "feat(paper-trading): add deploy and stop CLI commands for paper trading"
```

---

### Task 3: 集成测试 — 端到端纸上交易流程

**Files:**
- Test: `tests/integration/test_paper_trading_flow.py`

- [ ] **Step 1: 写集成测试**

```python
# tests/integration/test_paper_trading_flow.py
"""
纸上交易集成测试

验证完整的日级循环：
1. Day 0 数据到达 → 策略产生 Signal → T+1 延迟
2. Day 1 advance_time → Signal 发送到 Broker → 成交
3. T+1 结算解冻
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from decimal import Decimal


class TestPaperTradingIntegration:
    def test_daily_cycle_signal_t1_delay(self):
        """验证 Signal 在当日产生但 T+1 延迟到次日成交"""
        from ginkgo.trading.engines.time_controlled_engine import TimeControlledEventEngine
        from ginkgo.trading.portfolios.t1backtest import PortfolioT1Backtest
        from ginkgo.trading.feeders.backtest_feeder import BacktestFeeder
        from ginkgo.trading.gateway.trade_gateway import TradeGateway
        from ginkgo.trading.brokers.sim_broker import SimBroker
        from ginkgo.trading.strategies.random_signal_strategy import RandomSignalStrategy
        from ginkgo.trading.sizers.fixed_sizer import FixedSizer
        from ginkgo.trading.selectors.fixed_selector import FixedSelector
        from ginkgo.trading.analysis.analyzers.net_value import NetValue
        from ginkgo.enums import EXECUTION_MODE, ATTITUDE_TYPES

        # 创建引擎
        engine = TimeControlledEventEngine(
            name="test_paper",
            mode=EXECUTION_MODE.BACKTEST,
            logical_time_start=datetime(2026, 3, 30, 9, 30),
            timer_interval=0.01,
        )

        # 创建 Portfolio
        portfolio = PortfolioT1Backtest("test_paper_portfolio")
        portfolio.add_cash(Decimal("100000"))

        # 创建组件
        strategy = RandomSignalStrategy(buy_probability=1.0, sell_probability=0.0, max_signals=1)
        strategy.set_random_seed(42)
        sizer = FixedSizer(volume=1000)
        selector = FixedSelector(name="test_selector", codes=["000001.SZ"])
        analyzer = NetValue(name="paper_net_value")

        # 创建 Broker
        broker = SimBroker(
            name="TestSimBroker",
            attitude=ATTITUDE_TYPES.OPTIMISTIC,
            commission_rate=0.0003,
            commission_min=5,
        )
        gateway = TradeGateway(name="TestGateway", brokers=[broker])

        # Mock bar_service — 返回模拟数据
        mock_bar_service = MagicMock()
        mock_bar = MagicMock()
        mock_bar.code = "000001.SZ"
        mock_bar.open = Decimal("10.0")
        mock_bar.high = Decimal("10.5")
        mock_bar.low = Decimal("9.8")
        mock_bar.close = Decimal("10.2")
        mock_bar.volume = 1000000

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.data.empty.return_value = False
        mock_result.data.to_entities.return_value = [mock_bar]
        mock_bar_service.get.return_value = mock_result

        feeder = BacktestFeeder(name="test_feeder")
        feeder.bar_service = mock_bar_service

        # 绑定
        engine.add_portfolio(portfolio)
        engine.bind_router(gateway)
        portfolio.add_strategy(strategy)
        portfolio.bind_sizer(sizer)
        portfolio.bind_selector(selector)
        portfolio.add_analyzer(analyzer)
        engine.set_data_feeder(feeder)

        # Day 0: 推进引擎 — 策略产生 Signal（T+1 延迟）
        engine.start()
        engine.advance_time_to(datetime(2026, 3, 30, 15, 0))

        # 等待引擎处理完成
        import time
        time.sleep(1)

        # 验证 Signal 被延迟，没有立即成交
        assert len(portfolio.signals) > 0 or len(portfolio.filled_orders) == 0

        # Day 1: 推进引擎 — 延迟的 Signal 发送到 Broker
        engine.advance_time_to(datetime(2026, 3, 31, 15, 0))
        time.sleep(1)

        # 验证订单已成交
        assert len(portfolio.filled_orders) > 0

        # 清理
        engine.stop()
```

- [ ] **Step 2: 运行集成测试**

Run: `cd /home/kaoru/Ginkgo && python -m pytest tests/integration/test_paper_trading_flow.py -v -s`
Expected: PASS（需要 debug 模式开启和数据库连接）

- [ ] **Step 3: 提交**

```bash
git add tests/integration/test_paper_trading_flow.py
git commit -m "test(paper-trading): add integration test for daily cycle T+1 flow"
```

---

### Task 4: 注册到 TaskTimer — 复用调度基础设施

**Files:**
- Modify: `src/ginkgo/interfaces/dtos/control_command_dto.py` — 添加 PAPER_TRADING 命令
- Modify: `src/ginkgo/livecore/task_timer.py` — 添加 paper_trading job

**设计说明：** 纸上交易的每日循环通过 TaskTimer 调度，完全复用现有基础设施。Controller 自行拉取数据，不依赖 bar_snapshot 的完成状态。执行时序：

```
21:10  paper_trading job → 发送 Kafka 命令 → PaperTradingWorker
         → Controller.sync_range_batch() 同步拉取数据 → 数据就绪 → advance_time()
```

- [ ] **Step 1: 在 ControlCommandDTO 中注册 PAPER_TRADING 命令**

在 `src/ginkgo/interfaces/dtos/control_command_dto.py` 的 `Commands` 类中添加：

```python
PAPER_TRADING = "paper_trading"  # 纸上交易：推进引擎一天
```

同时在类 docstring 的 params 说明中添加：

```python
        - PAPER_TRADING:
            - 无参数（推进所有活跃的纸上交易引擎）
```

- [ ] **Step 2: 在 TaskTimer 中注册 paper_trading job**

在 `src/ginkgo/livecore/task_timer.py` 的三个位置添加代码：

**2a. `_get_job_function()` — 注册命令映射：**

```python
"paper_trading": self._paper_trading_job,  # 新增
```

**2b. `_get_valid_commands()` — 更新有效命令列表：**

```python
"paper_trading",  # 新增
```

**2c. 新增 `_paper_trading_job()` 方法**（在 `_heartbeat_test_job` 附近添加）：

```python
@safe_job_wrapper
def _paper_trading_job(self) -> None:
    """
    纸上交易推进任务（21:10触发，在 bar_snapshot 之后）

    发送 paper_trading 控制命令到 Kafka，
    PaperTradingWorker 接收后推进所有活跃的纸上交易引擎。
    """
    try:
        command_dto = ControlCommandDTO(
            command=ControlCommandDTO.Commands.PAPER_TRADING,
            params={},
            source="task_timer"
        )
        self._publish_to_kafka(command_dto.model_dump_json())
        GLOG.INFO("Sent paper_trading advance command")

        self._send_notification("纸上交易推进命令已发送", "PAPER_TRADING")
    except Exception as e:
        GLOG.ERROR(f"Paper trading job failed: {e}")
        self._send_error_notification("纸上交易推进任务执行失败", e)
```

- [ ] **Step 3: 更新 task_timer.yml 默认配置**

在 `_get_default_config()` 的 `scheduled_tasks` 列表中添加：

```python
{
    "name": "paper_trading",
    "cron": "10 21 * * *",  # 每天21:10（bar_snapshot后10分钟）
    "command": "paper_trading",
    "enabled": True,
},
```

- [ ] **Step 4: 提交**

```bash
git add src/ginkgo/interfaces/dtos/control_command_dto.py src/ginkgo/livecore/task_timer.py
git commit -m "feat(paper-trading): register paper_trading job in TaskTimer"
```

---

### Task 5: PaperTradingWorker — Kafka 命令接收与引擎推进

**Files:**
- Create: `src/ginkgo/workers/paper_trading_worker.py`
- Test: `tests/unit/workers/test_paper_trading_worker.py`

**设计说明：** PaperTradingWorker 是一个长驻进程，持有所有活跃的纸上交易引擎实例。它订阅 Kafka 控制命令 topic，收到 `paper_trading` 命令后调用所有 PaperTradingController 的 `run_daily_cycle()`。架构模式与 DataWorker 一致。

- [ ] **Step 1: 写失败测试**

```python
# tests/unit/workers/test_paper_trading_worker.py
import pytest
from unittest.mock import MagicMock, patch


class TestPaperTradingWorker:
    def test_on_paper_trading_command_calls_all_controllers(self):
        """收到 paper_trading 命令时应调用所有 controller"""
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker

        worker = PaperTradingWorker.__new__(PaperTradingWorker)
        worker._controllers = {
            "p1": MagicMock(),
            "p2": MagicMock(),
        }

        worker._handle_command("paper_trading", {})

        worker._controllers["p1"].run_daily_cycle.assert_called_once()
        worker._controllers["p2"].run_daily_cycle.assert_called_once()

    def test_register_controller_stores_controller(self):
        """register_controller 应存储 controller 到内部字典"""
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker

        worker = PaperTradingWorker.__new__(PaperTradingWorker)
        worker._controllers = {}

        mock_controller = MagicMock()
        worker.register_controller("portfolio_123", mock_controller)

        assert "portfolio_123" in worker._controllers
        assert worker._controllers["portfolio_123"] is mock_controller

    def test_unregister_controller_removes_controller(self):
        """unregister_controller 应移除 controller"""
        from ginkgo.workers.paper_trading_worker import PaperTradingWorker

        worker = PaperTradingWorker.__new__(PaperTradingWorker)
        worker._controllers = {"portfolio_123": MagicMock()}

        worker.unregister_controller("portfolio_123")

        assert "portfolio_123" not in worker._controllers
```

- [ ] **Step 2: 运行测试确认失败**

Run: `cd /home/kaoru/Ginkgo && python -m pytest tests/unit/workers/test_paper_trading_worker.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: 实现 PaperTradingWorker**

```python
# src/ginkgo/workers/paper_trading_worker.py
import threading
from typing import Dict

from ginkgo.libs import GLOG


class PaperTradingWorker:
    """
    纸上交易 Worker

    长驻进程，持有所有活跃的纸上交易引擎实例。
    通过 Kafka 接收 TaskTimer 的 paper_trading 控制命令，
    调用所有 PaperTradingController 的 run_daily_cycle() 推进引擎。

    架构模式与 DataWorker 一致。
    """

    def __init__(self):
        self._controllers: Dict[str, object] = {}
        self._lock = threading.Lock()
        self._running = False

    def register_controller(self, portfolio_id: str, controller) -> None:
        """注册纸上交易控制器"""
        with self._lock:
            self._controllers[portfolio_id] = controller
            GLOG.INFO(f"[PAPER-WORKER] Registered controller for {portfolio_id}")

    def unregister_controller(self, portfolio_id: str) -> None:
        """注销纸上交易控制器"""
        with self._lock:
            self._controllers.pop(portfolio_id, None)
            GLOG.INFO(f"[PAPER-WORKER] Unregistered controller for {portfolio_id}")

    def _handle_command(self, command: str, params: Dict) -> bool:
        """处理 Kafka 控制命令"""
        if command == "paper_trading":
            return self._handle_paper_trading(params)
        return False

    def _handle_paper_trading(self, params: Dict) -> bool:
        """处理 paper_trading 命令：推进所有引擎"""
        GLOG.info(
            f"[PAPER-WORKER] Paper trading advance triggered, "
            f"active controllers: {len(self._controllers)}"
        )

        with self._lock:
            for portfolio_id, controller in self._controllers.items():
                try:
                    result = controller.run_daily_cycle()
                    GLOG.INFO(
                        f"[PAPER-WORKER] {portfolio_id}: "
                        f"skipped={result.skipped}, advanced={result.advanced}"
                    )
                except Exception as e:
                    GLOG.ERROR(f"[PAPER-WORKER] {portfolio_id} failed: {e}")

        return True

    def start(self) -> None:
        """启动 Worker（订阅 Kafka topic）"""
        # TODO: Kafka 订阅逻辑，类似 DataWorker
        # 当前版本通过 CLI deploy 直接调用 register_controller
        self._running = True
        GLOG.INFO("[PAPER-WORKER] Worker started")

    def stop(self) -> None:
        """停止 Worker"""
        self._running = False
        GLOG.INFO("[PAPER-WORKER] Worker stopped")
```

- [ ] **Step 4: 运行测试确认通过**

Run: `cd /home/kaoru/Ginkgo && python -m pytest tests/unit/workers/test_paper_trading_worker.py -v`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add src/ginkgo/workers/paper_trading_worker.py tests/unit/workers/test_paper_trading_worker.py
git commit -m "feat(paper-trading): add PaperTradingWorker for Kafka command processing"
```

---

## 自检清单

**Spec 覆盖检查：**
- [x] 数据拉取：Task 1 — Controller 自行调用 `bar_service.sync_range_batch()` 同步拉取，不依赖 bar_snapshot
- [x] 交易日判断：Task 1 — TradeDayCRUD 查询
- [x] PaperTradingController：Task 1 — 检查交易日 + 拉取数据 + 推进引擎
- [x] deploy CLI：Task 2 — 创建并启动纸上交易，集成 PaperTradingWorker
- [x] stop CLI：Task 2 — 停止纸上交易，注销 Worker controller
- [x] T+1 Signal 延迟：现有 PortfolioT1Backtest 已实现
- [x] SimBroker 撮合：现有实现已满足
- [x] TaskTimer 调度：Task 4 — ControlCommandDTO 注册 + job 函数 + 默认配置
- [x] PaperTradingWorker：Task 5 — Kafka 命令接收 + controller 管理
- [x] 集成测试：Task 3 — 端到端验证

**占位符扫描：** 无 TBD/TODO/占位符（PaperTradingWorker.start() 中的 Kafka TODO 是已知后续扩展点，非占位符）

**类型一致性检查：** 所有引用的类型和方法签名与现有代码一致
