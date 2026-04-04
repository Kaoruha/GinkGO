# Interface Naming Unification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename 13 I-prefixed ABC classes to Base prefix, enhance 9 pure I* interfaces with type annotations and docstrings.

**Architecture:** Mechanical rename with import updates. Each batch is independently committable. Classes with concrete implementations get `Base*` prefix; pure abstract classes keep `I*` prefix and get enhanced documentation.

**Tech Stack:** Python 3.12.8, pytest, grep/sed for mechanical rename

---

## Naming Conflict Policy

Two classes will end up with the same `Base*` name in different modules:

| Name | Module A | Module B |
|------|----------|----------|
| `BaseStrategy` | `core/interfaces/strategy_interface.py` (was `IStrategy`) | `trading/strategies/strategy_base.py` (was `StrategyBase`) |
| `BaseEngine` | `core/interfaces/engine_interface.py` (was `IEngine`) | `trading/engines/base_engine.py` (existing) |

**Resolution**: Both keep the name `Base*` in their respective modules. They serve different purposes and live in different Python namespaces. The few files importing both use module-qualified imports or aliases.

---

## Batch 1: `core/interfaces/` — IModel and sub-interfaces

### Task 1: Rename IModel → BaseModel

**Files to modify:**
- `src/ginkgo/core/interfaces/model_interface.py` — rename class + update self-references (`List[IModel]` → `List[BaseModel]`)
- `src/ginkgo/core/interfaces/__init__.py` — update import and `__all__`
- `src/ginkgo/core/adapters/model_adapter.py` — update imports, isinstance checks, return types, subclass definitions
- `src/ginkgo/quant_ml/models/xgboost.py:29` — update import
- `src/ginkgo/quant_ml/models/sklearn.py:33` — update import
- `src/ginkgo/quant_ml/models/lightgbm.py:29` — update import
- `src/ginkgo/quant_ml/strategies/ml_strategy_base.py:26` — update import
- `src/ginkgo/trading/strategies/ml_strategy_base.py:33` — update import
- `src/ginkgo/client/ml_cli.py:270,499` — update imports
- `tests/unit/core/interfaces/test_model_interface.py` — update imports, subclass definitions, assertions
- `tests/unit/backtest/test_ml_strategy.py` — update mock patch paths (12 occurrences: `ginkgo.backtest.strategy.strategies.ml_strategy_base.IModel`)

**Steps:**

- [ ] **Step 1: Rename class in definition file**

In `src/ginkgo/core/interfaces/model_interface.py`, replace all occurrences of `IModel` with `BaseModel` (class definition, self-references like `List[IModel]`, `IModel` in type annotations).

- [ ] **Step 2: Update `core/interfaces/__init__.py`**

Change:
```python
from ginkgo.core.interfaces.model_interface import IModel
```
to:
```python
from ginkgo.core.interfaces.model_interface import BaseModel
```
And update `__all__` from `'IModel'` to `'BaseModel'`.

- [ ] **Step 3: Update all production imports**

For each file listed above, replace `IModel` with `BaseModel` in imports and type annotations. Use grep to verify completeness:
```bash
grep -rn "IModel" src/ginkgo/core/interfaces/model_interface.py src/ginkgo/core/adapters/model_adapter.py src/ginkgo/quant_ml/ src/ginkgo/trading/strategies/ml_strategy_base.py src/ginkgo/client/ml_cli.py
```

- [ ] **Step 4: Update test imports**

```bash
grep -rn "IModel" tests/unit/core/interfaces/test_model_interface.py tests/unit/backtest/test_ml_strategy.py
```
For `test_ml_strategy.py`, the mock patches use path `ginkgo.backtest.strategy.strategies.ml_strategy_base.IModel`. The actual module is `ginkgo.trading.strategies.ml_strategy_base`. Update these to `ginkgo.trading.strategies.ml_strategy_base.BaseModel`.

- [ ] **Step 5: Run tests**

```bash
cd /home/kaoru/Ginkgo && python -m pytest tests/unit/core/interfaces/test_model_interface.py tests/unit/backtest/test_ml_strategy.py src/ginkgo/quant_ml/ -x -q --timeout=60 2>&1 | tail -30
```

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "refactor: rename IModel to BaseModel (interface naming unification)"
```

### Task 2: Rename ITimeSeriesModel → BaseTimeSeriesModel, IEnsembleModel → BaseEnsembleModel

**Files to modify:**
- `src/ginkgo/core/interfaces/model_interface.py` — rename both classes
- `tests/unit/core/interfaces/test_model_interface.py` — update imports, subclasses, assertions

**Steps:**

- [ ] **Step 1: Rename in definition file**

In `src/ginkgo/core/interfaces/model_interface.py`:
- `class ITimeSeriesModel(IModel)` → `class BaseTimeSeriesModel(BaseModel)`
- `class IEnsembleModel(IModel)` → `class BaseEnsembleModel(BaseModel)`
- Update internal references (`List[IModel]` → `List[BaseModel]`)

- [ ] **Step 2: Update test file**

In `tests/unit/core/interfaces/test_model_interface.py`:
- Update imports: `ITimeSeriesModel` → `BaseTimeSeriesModel`, `IEnsembleModel` → `BaseEnsembleModel`
- Update subclass definitions and issubclass assertions

- [ ] **Step 3: Run tests**

```bash
cd /home/kaoru/Ginkgo && python -m pytest tests/unit/core/interfaces/test_model_interface.py -x -q --timeout=60 2>&1 | tail -20
```

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "refactor: rename ITimeSeriesModel/IEnsembleModel to Base* prefix"
```

---

## Batch 2: `core/interfaces/` — IStrategy and IPortfolio

### Task 3: Rename IStrategy → BaseStrategy, IMLStrategy → BaseMLStrategy

**Files to modify:**
- `src/ginkgo/core/interfaces/strategy_interface.py` — rename both classes
- `src/ginkgo/core/interfaces/__init__.py` — update import and `__all__`
- `src/ginkgo/core/interfaces/portfolio_interface.py` — update type annotations (`List[IStrategy]` → `List[BaseStrategy]`)
- `src/ginkgo/core/adapters/strategy_adapter.py` — update imports, isinstance, return types, subclass definitions
- `src/ginkgo/core/adapters/mode_adapter.py` — update imports and type annotations
- `tests/unit/core/interfaces/test_strategy_interface.py` — update imports, subclasses, assertions
- `tests/unit/core/adapters/test_mode_adapter.py` — update imports
- `tests/conftest.py:727,761` — update `@protocol_test(IStrategy)` and `@protocol_compatibility_test(IStrategy, ...)`

**Steps:**

- [ ] **Step 1: Rename in definition file**

In `src/ginkgo/core/interfaces/strategy_interface.py`:
- `class IStrategy(ABC)` → `class BaseStrategy(ABC)`
- `class IMLStrategy(IStrategy)` → `class BaseMLStrategy(BaseStrategy)`
- Update all internal references

- [ ] **Step 2: Update `core/interfaces/__init__.py`**

`IStrategy` → `BaseStrategy` in import and `__all__`.

- [ ] **Step 3: Update portfolio_interface.py**

`from ginkgo.core.interfaces.strategy_interface import IStrategy` → `from ginkgo.core.interfaces.strategy_interface import BaseStrategy`
All `IStrategy` type annotations → `BaseStrategy`.

- [ ] **Step 4: Update adapters**

For `strategy_adapter.py` and `mode_adapter.py`: replace all `IStrategy` → `BaseStrategy`, `IMLStrategy` → `BaseMLStrategy`.

Note: `strategy_adapter.py` also imports `StrategyBase` from `trading.strategies`. After this rename, both `BaseStrategy` (core) and `StrategyBase` (trading) may be imported. If both are needed, use alias:
```python
from ginkgo.core.interfaces.strategy_interface import BaseStrategy as StrategyInterface
from ginkgo.trading.strategies.strategy_base import StrategyBase
```

- [ ] **Step 5: Update tests and conftest**

- [ ] **Step 6: Run tests**

```bash
cd /home/kaoru/Ginkgo && python -m pytest tests/unit/core/interfaces/test_strategy_interface.py tests/unit/core/adapters/test_mode_adapter.py -x -q --timeout=60 2>&1 | tail -20
```

- [ ] **Step 7: Commit**

```bash
git add -A && git commit -m "refactor: rename IStrategy/IMLStrategy to BaseStrategy/BaseMLStrategy"
```

### Task 4: Rename IPortfolio → BasePortfolio, IMultiStrategyPortfolio → BaseMultiStrategyPortfolio

**Files to modify:**
- `src/ginkgo/core/interfaces/portfolio_interface.py` — rename both classes
- `src/ginkgo/core/interfaces/__init__.py` — update import and `__all__`
- `tests/unit/core/interfaces/test_portfolio_interface.py` — update imports, subclasses, assertions

**Steps:**

- [ ] **Step 1: Rename in definition file**

`IPortfolio` → `BasePortfolio`, `IMultiStrategyPortfolio` → `BaseMultiStrategyPortfolio`.
Update all `IStrategy` references to `BaseStrategy` (from Task 3).

- [ ] **Step 2: Update `__init__.py`**

- [ ] **Step 3: Update test file**

- [ ] **Step 4: Run tests**

```bash
cd /home/kaoru/Ginkgo && python -m pytest tests/unit/core/interfaces/test_portfolio_interface.py -x -q --timeout=60 2>&1 | tail -20
```

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "refactor: rename IPortfolio/IMultiStrategyPortfolio to Base* prefix"
```

---

## Batch 3: `core/interfaces/` — IEngine and sub-interfaces

### Task 5: Rename IEngine → BaseEngine, sub-interfaces → Base* prefix

**Files to modify:**
- `src/ginkgo/core/interfaces/engine_interface.py` — rename `IEngine`, `IEventDrivenEngine`, `IMatrixEngine`, `IHybridEngine`
- `src/ginkgo/core/interfaces/__init__.py` — update import and `__all__`
- `tests/integration/interfaces/test_engine_interface.py` — update imports, subclasses, assertions
- `tests/unit/backtest/test_enhanced_backtest_integration.py:22` — imports `EngineMode` (not being renamed, verify it still works)

**Conflict**: `trading/engines/base_engine.py` already has a `BaseEngine` class. After this rename, there will be two `BaseEngine` classes in different modules. This is OK — they serve different purposes and are in different namespaces.

**Steps:**

- [ ] **Step 1: Rename in definition file**

`IEngine` → `BaseEngine`, `IEventDrivenEngine` → `BaseEventDrivenEngine`, `IMatrixEngine` → `BaseMatrixEngine`, `IHybridEngine` → `BaseHybridEngine`.

- [ ] **Step 2: Update `__init__.py`**

- [ ] **Step 3: Update test file**

- [ ] **Step 4: Run tests**

```bash
cd /home/kaoru/Ginkgo && python -m pytest tests/integration/interfaces/test_engine_interface.py -x -q --timeout=60 2>&1 | tail -20
```

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "refactor: rename IEngine/sub-interfaces to Base* prefix"
```

---

## Batch 4: Trading layer — IBroker and StrategyBase

### Task 6: Rename StrategyBase → BaseStrategy

**Files to modify:**
- `src/ginkgo/trading/strategies/strategy_base.py` — rename class
- `src/ginkgo/trading/strategies/__init__.py` — update import and `__all__`
- 7 strategy implementation files (dual_thrust, moving_average_crossover, volume_activate, trend_follow, random_signal_strategy, ml_strategy_base, scalping)
- `src/ginkgo/quant_ml/strategies/ml_strategy_base.py` — update import
- `src/ginkgo/core/adapters/strategy_adapter.py` — update import
- `src/ginkgo/trading/evaluation/evaluators/base_evaluator.py:128` — lazy import
- `src/ginkgo/trading/evaluation/rules/structural_rules.py:57` — lazy import
- `src/ginkgo/client/validation_cli.py:540` — lazy import
- `tests/unit/backtest/test_strategy_integration.py` — imports and subclasses

**Steps:**

- [ ] **Step 1: Rename class in definition file**

`class StrategyBase(ContextMixin, TimeMixin, NamedMixin, Base)` → `class BaseStrategy(ContextMixin, TimeMixin, NamedMixin, Base)`

- [ ] **Step 2: Update `strategies/__init__.py`**

`from ginkgo.trading.strategies.strategy_base import StrategyBase` → `from ginkgo.trading.strategies.strategy_base import BaseStrategy`

- [ ] **Step 3: Update all production imports**

Use grep to find all remaining `StrategyBase` references:
```bash
grep -rn "StrategyBase" src/ginkgo/trading/strategies/ src/ginkgo/quant_ml/strategies/ src/ginkgo/core/adapters/ src/ginkgo/trading/evaluation/ src/ginkgo/client/ --include="*.py"
```

- [ ] **Step 4: Update test imports**

- [ ] **Step 5: Run tests**

```bash
cd /home/kaoru/Ginkgo && python -m pytest tests/unit/backtest/test_strategy_integration.py -x -q --timeout=60 2>&1 | tail -20
```

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "refactor: rename StrategyBase to BaseStrategy"
```

### Task 7: Merge IBroker into BaseBroker

**Files to modify:**
- `src/ginkgo/trading/brokers/base_broker.py` — inherits `IBroker` from `trading/interfaces/broker_interface.py`; update isinstance checks
- `src/ginkgo/trading/brokers/sim_broker.py` — remove redundant `IBroker` from inheritance
- `src/ginkgo/trading/brokers/live_broker_base.py` — remove redundant `IBroker` from inheritance
- `src/ginkgo/trading/brokers/__init__.py` — update re-exports
- `src/ginkgo/trading/gateway/trade_gateway.py` — update type annotations (`List[IBroker]` → `List[BaseBroker]`)
- `src/ginkgo/livecore/trade_gateway_adapter.py` — update type annotations
- `src/ginkgo/livecore/main.py` — update import

**Steps:**

- [ ] **Step 1: Update type annotations in consumers**

Replace `IBroker` type annotations with `BaseBroker` in:
- `trade_gateway.py`
- `trade_gateway_adapter.py`
- `livecore/main.py`

- [ ] **Step 2: Clean up redundant inheritance**

In `sim_broker.py`: `class SimBroker(BaseBroker, IBroker)` → `class SimBroker(BaseBroker)`
In `live_broker_base.py`: `class LiveBrokerBase(BaseBroker, IBroker, ABC)` → `class LiveBrokerBase(BaseBroker, ABC)`

- [ ] **Step 3: Update `brokers/__init__.py`**

The `__init__.py` currently imports `IBroker` from `.interfaces`. Update to also export `BaseBroker`.

- [ ] **Step 4: Run tests**

```bash
cd /home/kaoru/Ginkgo && python -m pytest tests/ -x -q --timeout=60 -k "broker" 2>&1 | tail -30
```

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "refactor: use BaseBroker type annotations instead of IBroker"
```

---

## Batch 5: INotificationChannel + enhance pure interfaces

### Task 8: Rename INotificationChannel → BaseNotificationChannel

**Files to modify:**
- `src/ginkgo/notifier/channels/base_channel.py` — rename class
- `src/ginkgo/notifier/channels/__init__.py` — update `__all__` and lazy import
- `src/ginkgo/notifier/__init__.py` — update `__all__` and lazy import
- `src/ginkgo/notifier/channels/email_channel.py` — update import and inheritance
- `src/ginkgo/notifier/channels/console_channel.py` — update import and inheritance
- `src/ginkgo/notifier/channels/webhook_channel.py` — update import and inheritance
- `src/ginkgo/notifier/core/notification_service.py` — update import and type annotations
- `src/ginkgo/notifier/core/webhook_dispatcher.py` — update type annotation

**Steps:**

- [ ] **Step 1: Rename in definition file**

`class INotificationChannel(ABC)` → `class BaseNotificationChannel(ABC)`

- [ ] **Step 2: Update all imports and references**

- [ ] **Step 3: Run tests**

```bash
cd /home/kaoru/Ginkgo && python -m pytest tests/ -x -q --timeout=60 -k "notification" 2>&1 | tail -30
```

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "refactor: rename INotificationChannel to BaseNotificationChannel"
```

### Task 9: Enhance 9 pure I* interfaces with type annotations and docstrings

**Files to modify:**
- `src/ginkgo/interfaces/notification_interface.py` — `INotificationService` (3 methods)
- `src/ginkgo/trading/feeders/interfaces.py` — `IDataFeeder`, `IBacktestDataFeeder`, `ILiveDataFeeder` (17 methods)
- `src/ginkgo/trading/time/interfaces.py` — `ITimeProvider`, `ITimeAwareComponent` (8 methods)
- `src/ginkgo/trading/gateway/interfaces.py` — `IEventRoutingCenter`, `ILoadBalancer`, `ICircuitBreaker` (25 methods)

**Steps:**

- [ ] **Step 1: Add type annotations and docstrings to INotificationService**

For each method, add parameter types, return type, and docstring. Example:
```python
@abstractmethod
def beep(self, times: int = 1) -> None:
    """发出提示音。

    Args:
        times: 提示音次数
    """
```

- [ ] **Step 2: Add type annotations and docstrings to IDataFeeder and sub-interfaces**

- [ ] **Step 3: Add type annotations and docstrings to ITimeProvider and ITimeAwareComponent**

- [ ] **Step 4: Add type annotations and docstrings to gateway interfaces**

- [ ] **Step 5: Run tests**

```bash
cd /home/kaoru/Ginkgo && python -m pytest tests/ -x -q --timeout=60 2>&1 | tail -30
```

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "docs: add type annotations and docstrings to pure I* interfaces"
```

---

## Summary

| Task | Description | Files | Batch |
|------|-------------|-------|-------|
| 1 | IModel → BaseModel | ~10 files | 1 |
| 2 | ITimeSeriesModel/IEnsembleModel → Base* | 2 files | 1 |
| 3 | IStrategy/IMLStrategy → Base* | ~8 files | 2 |
| 4 | IPortfolio/IMultiStrategyPortfolio → Base* | 3 files | 2 |
| 5 | IEngine/sub-interfaces → Base* | 3 files | 3 |
| 6 | StrategyBase → BaseStrategy | ~14 files | 4 |
| 7 | IBroker → BaseBroker type annotations | ~6 files | 4 |
| 8 | INotificationChannel → BaseNotificationChannel | ~8 files | 5 |
| 9 | Enhance 9 pure I* interfaces | 4 files | 5 |
