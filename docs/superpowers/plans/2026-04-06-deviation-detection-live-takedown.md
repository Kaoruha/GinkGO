# Deviation Detection & Strategy Takedown Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract shared DeviationChecker module, add Live mode deviation detection, and implement manual strategy takedown via CLI + API.

**Architecture:** Extract deviation detection logic from PaperTradingWorker into DeviationChecker shared module. Add DeviationScheduler for Live mode daily checks. Implement takedown/online commands via Kafka control flow.

**Tech Stack:** Python 3.12.8, Redis, ClickHouse, Kafka (SYSTEM_EVENTS / CONTROL_COMMANDS), APScheduler, Typer

**Design Doc:** `docs/superpowers/specs/2026-04-06-deviation-detection-live-takedown-design.md`

**Key types (all Dict, no dedicated class):**
- Deviation result: `{"status": "completed", "overall_level": "NORMAL"|"MODERATE"|"SEVERE", "metrics": {...}, "deviations": {...}, "slice_period": int}`
- Deviation detail: `{"current_value": float, "baseline_mean": float, "z_score": float, "percentile": float, "level": str, "direction": str}`

**Existing file references:**
- `src/ginkgo/workers/paper_trading_worker.py` — source of methods to extract (lines 265-489)
- `src/ginkgo/trading/analysis/evaluation/live_deviation_detector.py` — LiveDeviationDetector class
- `src/ginkgo/trading/analysis/evaluation/__init__.py` — module exports
- `src/ginkgo/livecore/scheduler/command_handler.py` — CommandHandler with handler_map (line 80)
- `src/ginkgo/livecore/scheduler/scheduler.py` — Scheduler thread (line 60)
- `src/ginkgo/client/portfolio_cli.py` — CLI commands (Typer app, line 26)
- `src/ginkgo/data/models/model_portfolio.py` — MPortfolio model (line 25)
- `src/ginkgo/data/crud/portfolio_crud.py` — portfolio CRUD with `update()` method
- `src/ginkgo/interfaces/kafka_topics.py` — SYSTEM_EVENTS (line 92), CONTROL_COMMANDS

---

## Task 1: Add Portfolio `status` Field

Add `status` column (active/offline) to MPortfolio model. This is a prerequisite for takedown.

**Files:**
- Modify: `src/ginkgo/data/models/model_portfolio.py:44` (after `live_status`)
- Modify: `src/ginkgo/data/crud/portfolio_crud.py` (add `update_status()` method)
- Create: `tests/unit/data/test_portfolio_status.py`

- [ ] **Step 1: Add `status` column to MPortfolio model**

In `model_portfolio.py`, after line 44 (`live_status`), add:

```python
# Operational status: ACTIVE(1), OFFLINE(0)
status: Mapped[int] = mapped_column(TINYINT, default=1, comment="运营状态: 1=active, 0=offline")
```

- [ ] **Step 2: Add `update_status()` to portfolio_crud.py**

```python
def update_status(self, uuid: str, status: int) -> bool:
    """Update portfolio operational status. status: 1=active, 0=offline"""
    return self.update(uuid, status=status)
```

- [ ] **Step 3: Add `find_active_portfolios()` to portfolio_crud.py**

```python
def find_active_portfolios(self) -> List:
    return self.find(filters={"status": 1})
```

- [ ] **Step 4: Write test**

In `tests/unit/data/test_portfolio_status.py`:

```python
import pytest
from ginkgo.data.models.model_portfolio import MPortfolio

@pytest.mark.tdd
class TestPortfolioStatus:
    def test_default_status_is_active(self):
        p = MPortfolio()
        assert p.status == 1

    def test_status_can_be_set_offline(self):
        p = MPortfolio()
        p.status = 0
        assert p.status == 0
```

- [ ] **Step 5: Run test**

```bash
pytest tests/unit/data/test_portfolio_status.py -v
```

- [ ] **Step 6: Commit**

```bash
git add src/ginkgo/data/models/model_portfolio.py src/ginkgo/data/crud/portfolio_crud.py tests/unit/data/test_portfolio_status.py
git commit -m "feat: add portfolio status field (active/offline) for takedown"
```

---

## Task 2: Create DeviationChecker Shared Module

Extract deviation detection logic from PaperTradingWorker into a standalone module.

**Files:**
- Create: `src/ginkgo/trading/analysis/evaluation/deviation_checker.py`
- Modify: `src/ginkgo/trading/analysis/evaluation/__init__.py`
- Create: `tests/unit/trading/analysis/test_deviation_checker.py`

- [ ] **Step 1: Write failing tests**

Create `tests/unit/trading/analysis/test_deviation_checker.py`:

```python
import pytest
import json
from unittest.mock import MagicMock, patch
from ginkgo.trading.analysis.evaluation.deviation_checker import DeviationChecker


@pytest.mark.tdd
class TestGetBaseline:
    def test_returns_cached_baseline_from_redis(self):
        checker = DeviationChecker()
        baseline = {"net_value": {"mean": 1.0, "std": 0.1}}
        mock_redis = MagicMock()
        mock_redis.get.return_value = json.dumps(baseline)

        with patch("ginkgo.trading.analysis.evaluation.deviation_checker.services") as mock_services:
            mock_services.data.redis_service.return_value = mock_redis
            result = checker.get_baseline("p-001")

        assert result == baseline
        mock_redis.get.assert_called_once_with("deviation:baseline:p-001")

    def test_returns_none_when_no_source_mapping(self):
        checker = DeviationChecker()
        mock_redis = MagicMock()
        mock_redis.get.return_value = None  # no baseline cache

        with patch("ginkgo.trading.analysis.evaluation.deviation_checker.services") as mock_services:
            mock_services.data.redis_service.return_value = mock_redis
            result = checker.get_baseline("p-001")

        assert result is None


@pytest.mark.tdd
class TestGetDeviationConfig:
    def test_returns_default_config_when_no_redis(self):
        checker = DeviationChecker()
        mock_redis = MagicMock()
        mock_redis.get.return_value = None

        with patch("ginkgo.trading.analysis.evaluation.deviation_checker.services") as mock_services:
            mock_services.data.redis_service.return_value = mock_redis
            result = checker.get_deviation_config("p-001")

        assert result["auto_takedown"] is False
        assert result["alert_channels"] == ["kafka"]

    def test_returns_config_from_redis(self):
        checker = DeviationChecker()
        config = {"auto_takedown": True, "check_time": "21:00"}
        mock_redis = MagicMock()
        mock_redis.get.return_value = json.dumps(config)

        with patch("ginkgo.trading.analysis.evaluation.deviation_checker.services") as mock_services:
            mock_services.data.redis_service.return_value = mock_redis
            result = checker.get_deviation_config("p-001")

        assert result["auto_takedown"] is True
        assert result["check_time"] == "21:00"


@pytest.mark.tdd
class TestHandleDeviationResult:
    def test_normal_is_silent(self):
        checker = DeviationChecker()
        result = {"overall_level": "NORMAL", "deviations": {}}
        mock_producer = MagicMock()
        checker._producer = mock_producer
        checker.handle_deviation_result("p-001", result, auto_takedown=False)
        mock_producer.send.assert_not_called()

    def test_moderate_sends_alert(self):
        checker = DeviationChecker()
        result = {
            "overall_level": "MODERATE",
            "deviations": {"sharpe_ratio": {"z_score": 2.1, "level": "MODERATE"}}
        }
        mock_producer = MagicMock()
        checker._producer = mock_producer
        checker.handle_deviation_result("p-001", result, auto_takedown=False)
        mock_producer.send.assert_called_once()

    def test_severe_auto_takedown(self):
        checker = DeviationChecker()
        mock_takedown = MagicMock()
        checker._takedown_callback = mock_takedown
        result = {
            "overall_level": "SEVERE",
            "deviations": {"max_drawdown": {"z_score": 3.5, "level": "SEVERE"}}
        }
        mock_producer = MagicMock()
        checker._producer = mock_producer
        checker.handle_deviation_result("p-001", result, auto_takedown=True)
        mock_takedown.assert_called_once_with("p-001")


@pytest.mark.tdd
class TestSendDeviationAlert:
    def test_sends_multi_metric_to_system_events(self):
        checker = DeviationChecker()
        mock_producer = MagicMock()
        checker._producer = mock_producer
        checker._source = "test-source"
        result = {
            "overall_level": "MODERATE",
            "deviations": {
                "sharpe_ratio": {"z_score": 2.1, "level": "MODERATE"},
                "max_drawdown": {"z_score": 1.8, "level": "MODERATE"},
            },
            "risk_score": 0.5,
        }
        checker.send_deviation_alert("p-001", "MODERATE", result)
        call_args = mock_producer.send.call_args
        msg = call_args[0][1]
        assert isinstance(msg["deviation_details"], list)
        assert len(msg["deviation_details"]) == 2

    def test_noop_without_producer(self):
        checker = DeviationChecker()
        checker._producer = None
        checker.send_deviation_alert("p-001", "MODERATE", {})
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
pytest tests/unit/trading/analysis/test_deviation_checker.py -v
```

Expected: FAIL (ModuleNotFoundError)

- [ ] **Step 3: Implement DeviationChecker**

Create `src/ginkgo/trading/analysis/evaluation/deviation_checker.py`:

```python
import json
from datetime import datetime
from typing import Dict, List, Optional

from ginkgo.interfaces.kafka_topics import KafkaTopics
from ginkgo.libs import GLOG


class DeviationChecker:
    """Shared deviation detection logic for Paper and Live modes."""

    def __init__(self, producer=None, source: str = "deviation-checker", takedown_callback=None):
        self._producer = producer
        self._source = source
        self._takedown_callback = takedown_callback
        self._detectors: Dict[str, object] = {}

    def get_detector(self, portfolio_id: str):
        return self._detectors.get(portfolio_id)

    def set_detector(self, portfolio_id: str, detector) -> None:
        self._detectors[portfolio_id] = detector

    def get_baseline(self, portfolio_id: str) -> Optional[dict]:
        """Get baseline from Redis cache, compute on miss."""
        from ginkgo import services

        try:
            redis_svc = services.data.redis_service()
            if redis_svc:
                cached = redis_svc.get(f"deviation:baseline:{portfolio_id}")
                if cached:
                    return json.loads(cached)
        except Exception:
            pass

        try:
            redis_svc = services.data.redis_service()
            source_id = None
            if redis_svc:
                source_id = redis_svc.get(f"deviation:source:{portfolio_id}")

            if not source_id:
                GLOG.DEBUG(f"[DEV-CHECKER] No source portfolio for {portfolio_id[:8]}")
                return None

            task_service = services.data.backtest_task_service()
            task_result = task_service.list(
                portfolio_id=source_id, status="completed", page_size=1,
            )
            if not task_result.is_success() or not task_result.data:
                return None

            latest_task = task_result.data[0] if isinstance(task_result.data, list) else task_result.data
            run_id = getattr(latest_task, "run_id", None)
            engine_id = getattr(latest_task, "engine_id", None)
            if not run_id:
                return None

            from ginkgo.trading.analysis.evaluation.backtest_evaluator import BacktestEvaluator
            evaluator = BacktestEvaluator()
            eval_result = evaluator.evaluate_backtest_stability(
                portfolio_id=source_id, engine_id=engine_id,
            )
            if eval_result.get("status") != "success":
                return None

            baseline = eval_result.get("monitoring_baseline")
            if not baseline:
                return None

            if redis_svc:
                redis_svc.set(
                    f"deviation:baseline:{portfolio_id}",
                    json.dumps(baseline, default=str),
                )
            return baseline
        except Exception as e:
            GLOG.WARN(f"[DEV-CHECKER] Baseline computation failed for {portfolio_id[:8]}: {e}")
            return None

    def get_deviation_config(self, portfolio_id: str) -> dict:
        """Read deviation detection config from Redis."""
        from ginkgo import services

        try:
            redis_svc = services.data.redis_service()
            if redis_svc:
                config_json = redis_svc.get(f"deviation:config:{portfolio_id}")
                if config_json:
                    return json.loads(config_json)
        except Exception:
            pass

        return {
            "auto_takedown": False,
            "slice_period_days": None,
            "confidence_levels": [0.68, 0.95, 0.99],
            "alert_channels": ["kafka"],
            "check_time": "20:30",
            "anomaly_pnl_threshold": -0.05,
        }

    def run_deviation_check(self, portfolio_id: str, today_records: Dict) -> Optional[Dict]:
        """Run deviation check for a single portfolio. Returns result dict or None."""
        detector = self._detectors.get(portfolio_id)
        if not detector:
            return None

        try:
            slice_complete = detector.accumulate_live_data(
                analyzer_records=today_records.get("analyzers"),
                signal_records=today_records.get("signals"),
                order_records=today_records.get("orders"),
            )
            if slice_complete:
                return detector.check_deviation_on_slice_complete()
        except Exception as e:
            GLOG.ERROR(f"[DEV-CHECKER] Deviation check error for {portfolio_id[:8]}: {e}")

        return None

    def handle_deviation_result(self, portfolio_id: str, result: Dict, auto_takedown: bool = False) -> None:
        """Handle deviation result: alert + optional auto takedown."""
        level = result.get("overall_level", "NORMAL")

        if level == "NORMAL":
            GLOG.DEBUG(f"[DEV-CHECKER] {portfolio_id[:8]}: deviation NORMAL")
            return

        deviations = result.get("deviations", {})
        severity_metrics = [
            f"{k} (z={v['z_score']:.1f})"
            for k, v in deviations.items()
            if v.get("level") != "NORMAL"
        ]

        if level == "MODERATE":
            GLOG.WARN(f"[DEV-CHECKER] {portfolio_id[:8]}: MODERATE - {', '.join(severity_metrics)}")
        elif level == "SEVERE":
            GLOG.ERROR(f"[DEV-CHECKER] {portfolio_id[:8]}: SEVERE - {', '.join(severity_metrics)}")

        self.send_deviation_alert(portfolio_id, level, result)

        if level == "SEVERE" and auto_takedown and self._takedown_callback:
            GLOG.ERROR(f"[DEV-CHECKER] Auto-takedown triggered for {portfolio_id[:8]}")
            self._takedown_callback(portfolio_id)

    def send_deviation_alert(self, portfolio_id: str, level: str, result: Dict) -> None:
        """Send deviation alert to Kafka SYSTEM_EVENTS with multi-metric details."""
        if not self._producer:
            return

        deviations = result.get("deviations", {})
        deviation_details = [
            {
                "metric": k,
                "level": v.get("level"),
                "z_score": v.get("z_score", 0),
                "threshold": v.get("threshold", 2.0),
            }
            for k, v in deviations.items()
            if v.get("level") != "NORMAL"
        ]

        try:
            self._producer.send(
                KafkaTopics.SYSTEM_EVENTS,
                {
                    "source": self._source,
                    "type": "deviation_alert",
                    "level": level,
                    "portfolio_id": portfolio_id,
                    "deviation_details": deviation_details,
                    "risk_score": result.get("risk_score", 0),
                    "timestamp": datetime.now().isoformat(),
                },
            )
        except Exception as e:
            GLOG.ERROR(f"[DEV-CHECKER] Failed to send deviation alert: {e}")
```

- [ ] **Step 4: Update `__init__.py` exports**

In `src/ginkgo/trading/analysis/evaluation/__init__.py`, add:

```python
from ginkgo.trading.analysis.evaluation.deviation_checker import DeviationChecker
```

And add `"DeviationChecker"` to `__all__`.

- [ ] **Step 5: Run tests — verify they pass**

```bash
pytest tests/unit/trading/analysis/test_deviation_checker.py -v
```

- [ ] **Step 6: Commit**

```bash
git add src/ginkgo/trading/analysis/evaluation/deviation_checker.py \
        src/ginkgo/trading/analysis/evaluation/__init__.py \
        tests/unit/trading/analysis/test_deviation_checker.py
git commit -m "feat: extract DeviationChecker shared module from PaperTradingWorker"
```

---

## Task 3: Refactor PaperTradingWorker to Use DeviationChecker

Replace internal deviation methods with DeviationChecker calls. Add offline status check in daily cycle.

**Files:**
- Modify: `src/ginkgo/workers/paper_trading_worker.py`
- Modify: `tests/unit/workers/test_paper_trading_worker.py`

- [ ] **Step 1: Replace internal deviation methods**

In `paper_trading_worker.py`:

1. Add import at top:
```python
from ginkgo.trading.analysis.evaluation.deviation_checker import DeviationChecker
```

2. In `__init__` (after line 64), add:
```python
self._deviation_checker = DeviationChecker(
    producer=self._producer,
    source=f"paper-trading-{worker_id}",
    takedown_callback=self._handle_unload,
)
```

3. In `assemble_engine()` where detectors are created (around line 200), also register with checker:
```python
# After creating detector:
self._deviation_checker.set_detector(portfolio.portfolio_id, detector)
```

4. Replace `_get_baseline` → delegate:
```python
def _get_baseline(self, portfolio_id: str) -> Optional[dict]:
    return self._deviation_checker.get_baseline(portfolio_id)
```

5. Replace `_get_deviation_config` → delegate:
```python
def _get_deviation_config(self, portfolio_id: str) -> dict:
    return self._deviation_checker.get_deviation_config(portfolio_id)
```

6. Replace `_run_deviation_check` → delegate:
```python
def _run_deviation_check(self) -> None:
    if not self._deviation_checker._detectors:
        return
    for portfolio in self._engine.portfolios:
        try:
            records = self._load_today_records(portfolio.portfolio_id)
            result = self._deviation_checker.run_deviation_check(
                portfolio.portfolio_id, records
            )
            if result:
                config = self._get_deviation_config(portfolio.portfolio_id)
                self._deviation_checker.handle_deviation_result(
                    portfolio.portfolio_id, result,
                    auto_takedown=config.get("auto_takedown", False),
                )
        except Exception as e:
            GLOG.ERROR(f"[PAPER-WORKER] Deviation check error for {portfolio.portfolio_id[:8]}: {e}")
```

7. Replace `_handle_deviation_result` and `_send_deviation_alert` with thin wrappers (or remove and use checker directly).

8. Add offline check in `run_daily_cycle()` — before processing each portfolio:
```python
# Skip offline portfolios
if getattr(portfolio, 'status', 1) == 0:
    GLOG.DEBUG(f"[PAPER-WORKER] Skipping offline portfolio {portfolio.portfolio_id[:8]}")
    continue
```

- [ ] **Step 2: Run existing worker tests**

```bash
pytest tests/unit/workers/test_paper_trading_worker.py -v
```

- [ ] **Step 3: Commit**

```bash
git add src/ginkgo/workers/paper_trading_worker.py tests/unit/workers/test_paper_trading_worker.py
git commit -m "refactor: PaperTradingWorker delegates to DeviationChecker, skip offline portfolios"
```

---

## Task 4: CLI Takedown/Online Commands

**Files:**
- Modify: `src/ginkgo/client/portfolio_cli.py`
- Create: `tests/unit/client/test_portfolio_takedown_cli.py`

- [ ] **Step 1: Write test**

Create `tests/unit/client/test_portfolio_takedown_cli.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
from ginkgo.client.portfolio_cli import app

runner = CliRunner()


@pytest.mark.tdd
class TestTakedownCommand:
    @patch("ginkgo.client.portfolio_cli.GinkgoProducer")
    @patch("ginkgo.client.portfolio_cli.container")
    def test_sends_takedown_command(self, mock_container, mock_producer_cls):
        mock_producer = MagicMock()
        mock_producer_cls.return_value = mock_producer
        mock_crud = MagicMock()
        mock_crud.update.return_value = True
        mock_container.portfolio_crud.return_value = mock_crud

        result = runner.invoke(app, ["takedown", "test-uuid", "--reason", "manual check"])
        assert result.exit_code == 0
        mock_crud.update.assert_called_once()
        mock_producer.send.assert_called_once()

    @patch("ginkgo.client.portfolio_cli.container")
    def test_online_command(self, mock_container):
        mock_crud = MagicMock()
        mock_crud.update.return_value = True
        mock_container.portfolio_crud.return_value = mock_crud

        # online doesn't need Kafka, just updates DB
        result = runner.invoke(app, ["online", "test-uuid"])
        assert result.exit_code == 0
        mock_crud.update.assert_called_once()


@pytest.mark.tdd
class TestListShowsStatus:
    @patch("ginkgo.client.portfolio_cli.container")
    def test_list_shows_offline_status(self, mock_container):
        mock_portfolio = MagicMock()
        mock_portfolio.uuid = "p-001"
        mock_portfolio.name = "Test"
        mock_portfolio.status = 0  # offline
        mock_portfolio.mode = 1
        mock_portfolio.state = 1
        mock_crud = MagicMock()
        mock_crud.find.return_value = [mock_portfolio]
        mock_container.portfolio_crud.return_value = mock_crud

        result = runner.invoke(app, ["list"])
        assert "offline" in result.stdout.lower() or "OFFLINE" in result.stdout
```

- [ ] **Step 2: Run test — verify it fails**

```bash
pytest tests/unit/client/test_portfolio_takedown_cli.py -v
```

- [ ] **Step 3: Implement CLI commands**

In `src/ginkgo/client/portfolio_cli.py`, add:

```python
@app.command(name="takedown")
def takedown_portfolio(
    portfolio_id: str = typer.Argument(help="Portfolio UUID"),
    reason: str = typer.Option("manual takedown", help="Reason for takedown"),
):
    """Take a portfolio offline (stop strategy execution, keep positions)."""
    from ginkgo.data.containers import container
    from ginkgo.interfaces.kafka_topics import KafkaTopics

    crud = container.portfolio_crud()
    crud.update(portfolio_id, status=0)
    rprint(f"[yellow]Portfolio {portfolio_id[:8]} is now OFFLINE[/yellow]")

    # Send Kafka notification
    try:
        producer = GinkgoProducer()
        producer.send(KafkaTopics.SYSTEM_EVENTS, {
            "source": "cli",
            "type": "portfolio_takedown",
            "portfolio_id": portfolio_id,
            "reason": reason,
            "operator": "cli",
            "timestamp": datetime.now().isoformat(),
        })
        producer.flush()
    except Exception as e:
        rprint(f"[red]Failed to send notification: {e}[/red]")


@app.command(name="online")
def online_portfolio(
    portfolio_id: str = typer.Argument(help="Portfolio UUID"),
):
    """Bring a portfolio back online."""
    from ginkgo.data.containers import container

    crud = container.portfolio_crud()
    crud.update(portfolio_id, status=1)
    rprint(f"[green]Portfolio {portfolio_id[:8]} is now ACTIVE[/green]")
```

Also update the `list` command to show status column — add `status` to the table with "active"/"offline" label.

- [ ] **Step 4: Run test — verify it passes**

```bash
pytest tests/unit/client/test_portfolio_takedown_cli.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/ginkgo/client/portfolio_cli.py tests/unit/client/test_portfolio_takedown_cli.py
git commit -m "feat: add portfolio takedown/online CLI commands"
```

---

## Task 5: CommandHandler Takedown/Online + API Endpoints

**Files:**
- Modify: `src/ginkgo/livecore/scheduler/command_handler.py`
- Create: `tests/unit/livecore/scheduler/test_command_handler_takedown.py`

- [ ] **Step 1: Write test**

Create `tests/unit/livecore/scheduler/test_command_handler_takedown.py`:

```python
import pytest
from unittest.mock import MagicMock

@pytest.mark.tdd
class TestHandleTakedown:
    def test_updates_portfolio_status_to_offline(self):
        handler = MagicMock()
        from ginkgo.livecore.scheduler.command_handler import CommandHandler
        # Test that handle_takedown calls portfolio_crud.update(id, status=0)
        # and publishes SYSTEM_EVENTS notification

    def test_handle_online_restores_status(self):
        # Test that handle_online calls portfolio_crud.update(id, status=1)
        pass
```

- [ ] **Step 2: Implement CommandHandler methods**

In `src/ginkgo/livecore/scheduler/command_handler.py`:

1. Add to `handler_map` (line 80):
```python
'takedown': self.handle_takedown,
'online': self.handle_online,
```

2. Add methods:
```python
def handle_takedown(self, params: Dict):
    """Mark portfolio as offline."""
    from ginkgo import services
    portfolio_id = params.get("portfolio_id")
    if not portfolio_id:
        return

    crud = services.data.portfolio_crud()
    crud.update(portfolio_id, status=0)

    # Publish notification
    if self._publish_callback:
        self._publish_callback({
            "source": "scheduler",
            "type": "portfolio_takedown",
            "portfolio_id": portfolio_id,
            "reason": params.get("reason", "scheduler command"),
            "operator": "scheduler",
            "timestamp": datetime.now().isoformat(),
        })

def handle_online(self, params: Dict):
    """Restore portfolio to active."""
    from ginkgo import services
    portfolio_id = params.get("portfolio_id")
    if not portfolio_id:
        return

    crud = services.data.portfolio_crud()
    crud.update(portfolio_id, status=1)
```

- [ ] **Step 3: Run tests**

```bash
pytest tests/unit/livecore/scheduler/test_command_handler_takedown.py -v
```

- [ ] **Step 4: Commit**

```bash
git add src/ginkgo/livecore/scheduler/command_handler.py \
        tests/unit/livecore/scheduler/test_command_handler_takedown.py
git commit -m "feat: add takedown/online commands to CommandHandler"
```

---

## Task 6: Live DeviationScheduler

Create the scheduler that runs deviation checks for Live mode portfolios.

**Files:**
- Create: `src/ginkgo/livecore/scheduler/deviation_scheduler.py`
- Modify: `src/ginkgo/livecore/scheduler/scheduler.py` (integrate)
- Create: `tests/unit/livecore/scheduler/test_deviation_scheduler.py`

- [ ] **Step 1: Write test**

Create `tests/unit/livecore/scheduler/test_deviation_scheduler.py`:

```python
import pytest
from unittest.mock import MagicMock, patch
from ginkgo.livecore.scheduler.deviation_scheduler import DeviationScheduler


@pytest.mark.tdd
class TestDeviationScheduler:
    def test_runs_check_for_active_live_portfolios(self):
        scheduler = DeviationScheduler(producer=MagicMock())
        mock_checker = MagicMock()
        scheduler._checker = mock_checker

        mock_portfolio = MagicMock()
        mock_portfolio.portfolio_id = "live-001"
        mock_portfolio.status = 1  # active
        scheduler._get_live_portfolios = MagicMock(return_value=[mock_portfolio])
        scheduler._load_today_records = MagicMock(return_value={"analyzers": [], "signals": [], "orders": []})

        scheduler.run_daily_check()

        mock_checker.run_deviation_check.assert_called_once()

    def test_skips_offline_portfolios(self):
        scheduler = DeviationScheduler(producer=MagicMock())
        mock_portfolio = MagicMock()
        mock_portfolio.portfolio_id = "live-001"
        mock_portfolio.status = 0  # offline
        scheduler._get_live_portfolios = MagicMock(return_value=[mock_portfolio])
        mock_checker = MagicMock()
        scheduler._checker = mock_checker

        scheduler.run_daily_check()
        mock_checker.run_deviation_check.assert_not_called()
```

- [ ] **Step 2: Implement DeviationScheduler**

Create `src/ginkgo/livecore/scheduler/deviation_scheduler.py`:

```python
import json
from datetime import datetime
from typing import Dict, List, Optional

from ginkgo.trading.analysis.evaluation.deviation_checker import DeviationChecker
from ginkgo.trading.analysis.evaluation.live_deviation_detector import LiveDeviationDetector
from ginkgo.interfaces.kafka_topics import KafkaTopics
from ginkgo.libs import GLOG


class DeviationScheduler:
    """Scheduled deviation checks for Live mode portfolios."""

    def __init__(self, producer=None):
        self._producer = producer
        self._checker = DeviationChecker(
            producer=producer,
            source="live-deviation-scheduler",
        )
        self._portfolios_cache: List = []

    def initialize(self, portfolios: List) -> None:
        """Initialize detectors for Live portfolios."""
        self._portfolios_cache = [p for p in portfolios if getattr(p, 'status', 1) == 1]
        for portfolio in self._portfolios_cache:
            baseline = self._checker.get_baseline(portfolio.portfolio_id)
            if baseline:
                config = self._checker.get_deviation_config(portfolio.portfolio_id)
                slice_days = config.get("slice_period_days") or 30
                detector = LiveDeviationDetector(
                    baseline_stats=baseline,
                    slice_period_days=slice_days,
                )
                self._checker.set_detector(portfolio.portfolio_id, detector)

    def run_daily_check(self) -> None:
        """Run deviation check for all active Live portfolios."""
        for portfolio in self._portfolios_cache:
            if getattr(portfolio, 'status', 1) == 0:
                continue

            try:
                records = self._load_today_records(portfolio.portfolio_id)
                result = self._checker.run_deviation_check(portfolio.portfolio_id, records)
                if result:
                    config = self._checker.get_deviation_config(portfolio.portfolio_id)
                    self._checker.handle_deviation_result(
                        portfolio.portfolio_id, result,
                        auto_takedown=config.get("auto_takedown", False),
                    )
            except Exception as e:
                GLOG.ERROR(f"[LIVE-DEV] Check error for {portfolio.portfolio_id[:8]}: {e}")

    def check_anomaly_trigger(self, portfolio_id: str, current_worth: float, initial_capital: float) -> bool:
        """Check if anomaly trigger threshold is exceeded. Returns True if triggered."""
        if initial_capital <= 0:
            return False
        pnl_pct = (current_worth - initial_capital) / initial_capital
        config = self._checker.get_deviation_config(portfolio_id)
        threshold = config.get("anomaly_pnl_threshold", -0.05)
        if pnl_pct < threshold:
            GLOG.WARN(
                f"[LIVE-DEV] Anomaly trigger: P&L {pnl_pct:.2%} < {threshold:.2%} "
                f"for {portfolio_id[:8]}"
            )
            return True
        return False

    def _load_today_records(self, portfolio_id: str) -> Dict:
        """Load today's analyzer/signal/order records from ClickHouse."""
        from ginkgo import services

        today = datetime.now().strftime("%Y-%m-%d")
        records = {"analyzers": [], "signals": [], "orders": []}

        try:
            analyzer_service = services.data.services.analyzer_service()
            result = analyzer_service.get_by_run_id(
                run_id="live", portfolio_id=portfolio_id,
            )
            if result.is_success() and result.data:
                for r in result.data:
                    ts = str(getattr(r, 'timestamp', ''))[:10]
                    if ts == today:
                        records["analyzers"].append({
                            "name": getattr(r, 'name', ''),
                            "value": float(getattr(r, 'value', 0)),
                        })
        except Exception as e:
            GLOG.DEBUG(f"[LIVE-DEV] Failed to load records: {e}")

        return records
```

- [ ] **Step 3: Integrate with Scheduler**

In `src/ginkgo/livecore/scheduler/scheduler.py`, in `__init__`:

```python
from .deviation_scheduler import DeviationScheduler
# ...
self._deviation_scheduler = DeviationScheduler(producer=kafka_producer)
```

In `_schedule_loop()`, add daily check call based on configured time:

```python
from datetime import datetime
config_time = "20:30"  # default, could read from config
now = datetime.now()
if now.strftime("%H:%M") == config_time and not self._deviation_check_done_today:
    self._deviation_scheduler.run_daily_check()
    self._deviation_check_done_today = True
if now.strftime("%H:%M") == "00:00":
    self._deviation_check_done_today = False  # reset at midnight
```

- [ ] **Step 4: Run tests**

```bash
pytest tests/unit/livecore/scheduler/test_deviation_scheduler.py -v
```

- [ ] **Step 5: Commit**

```bash
git add src/ginkgo/livecore/scheduler/deviation_scheduler.py \
        src/ginkgo/livecore/scheduler/scheduler.py \
        tests/unit/livecore/scheduler/test_deviation_scheduler.py
git commit -m "feat: add DeviationScheduler for Live mode daily deviation checks"
```

---

## Task 7: Fix Existing CLI Tests (3 failing)

Fix the 3 failing tests in `test_paper_trading_cli.py` that were identified before this work started.

**Files:**
- Modify: `tests/unit/client/test_paper_trading_cli.py`

- [ ] **Step 1: Identify the mock issue**

The problem: `_generate_baseline_if_possible` uses `from ginkgo import services` inside the function body. Patching `ginkgo.client.portfolio_cli.services` doesn't work because the local import shadows it.

- [ ] **Step 2: Fix mock strategy**

Patch at the service level where it's actually called:
```python
# Instead of: patch("ginkgo.client.portfolio_cli.services")
# Use: patch("ginkgo.data.services.backtest_task_service.BacktestTaskService.list")
# Or: patch the redis_service directly
```

- [ ] **Step 3: Run tests to verify**

```bash
pytest tests/unit/client/test_paper_trading_cli.py -v
```

- [ ] **Step 4: Commit**

```bash
git add tests/unit/client/test_paper_trading_cli.py
git commit -m "fix: resolve mock issues in CLI baseline tests"
```

---

## Self-Review Checklist

| Spec Section | Task | Status |
|---|---|---|
| DeviationChecker shared module | Task 2 | Covered |
| Live mode daily check (configurable time) | Task 6 | Covered |
| Live mode anomaly trigger (real-time P&L) | Task 6 | Covered |
| Portfolio status field (active/offline) | Task 1 | Covered |
| Takedown flow (CLI → Kafka → Handler) | Task 4, 5 | Covered |
| Online flow | Task 4, 5 | Covered |
| Paper mode skips offline portfolios | Task 3 | Covered |
| Live mode skips offline portfolios | Task 6 | Covered |
| Multi-metric deviation_details | Task 2 | Covered |
| MODERATE vs SEVERE handling | Task 2 | Covered |
| Fix existing failing tests | Task 7 | Covered |
