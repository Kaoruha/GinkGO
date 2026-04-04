# Interface and Base Class Naming Unification

**Date**: 2026-04-05
**Status**: Approved
**Scope**: Unify naming conventions for interfaces and base classes across the codebase

## Background

Ginkgo has ~195K lines of Python code with inconsistent naming: some classes use `I` prefix (Java-style), others use `Base` prefix, and some concepts have both ABC and Protocol versions. This creates confusion about whether a class is a pure contract or a base with shared implementation.

## Naming Convention

**Rule**: The name reflects the class's role, not its implementation mechanism.

| Prefix | Meaning | When to use |
|--------|---------|-------------|
| `I*` | Pure contract (no implementation) | All methods are `@abstractmethod` with `pass`. No `__init__`, no stored state. Includes `Protocol` classes. |
| `Base*` | Base class with shared implementation | Has concrete methods (`__init__`, properties, helpers). May also have `@abstractmethod` methods that subclasses must implement. |

## Classification

### Rename to Base* (13 classes)

These have `__init__`, stored state, and concrete helper methods. They are base classes, not interfaces.

| # | Current | Target | File | Abstract | Concrete |
|---|---------|--------|------|----------|----------|
| 1 | `IStrategy` | `BaseStrategy` | `core/interfaces/strategy_interface.py` | 3 | 12 |
| 2 | `IMLStrategy` | `BaseMLStrategy` | same | 2 | 4 |
| 3 | `IModel` | `BaseModel` | `core/interfaces/model_interface.py` | 3 | 17 |
| 4 | `ITimeSeriesModel` | `BaseTimeSeriesModel` | same | 1 | 4 |
| 5 | `IEnsembleModel` | `BaseEnsembleModel` | same | 0 | 7 |
| 6 | `IEngine` | `BaseEngine` | `core/interfaces/engine_interface.py` | 2 | 20 |
| 7 | `IEventDrivenEngine` | `BaseEventDrivenEngine` | same | 2 | 4 |
| 8 | `IMatrixEngine` | `BaseMatrixEngine` | same | 2 | 4 |
| 9 | `IHybridEngine` | `BaseHybridEngine` | same | 2 | 2 |
| 10 | `IPortfolio` | `BasePortfolio` | `core/interfaces/portfolio_interface.py` | 4 | 19 |
| 11 | `IMultiStrategyPortfolio` | `BaseMultiStrategyPortfolio` | same | 2 | 6 |
| 12 | `IBroker` | Merge into `BaseBroker` | `trading/brokers/interfaces.py` | 11 | 8 |
| 13 | `INotificationChannel` | `BaseNotificationChannel` | `notifier/channels/base_channel.py` | 4 | 1 |

### Keep as I* (9 classes)

These are pure contracts — all methods are `@abstractmethod` with `pass`, no state, no implementation.

| # | Class | File |
|---|-------|------|
| 1 | `INotificationService` | `interfaces/notification_interface.py` |
| 2 | `IDataFeeder` | `trading/feeders/interfaces.py` |
| 3 | `IBacktestDataFeeder` | `trading/feeders/interfaces.py` |
| 4 | `ILiveDataFeeder` | `trading/feeders/interfaces.py` |
| 5 | `ITimeProvider` | `trading/time/interfaces.py` |
| 6 | `ITimeAwareComponent` | `trading/time/interfaces.py` |
| 7 | `IEventRoutingCenter` | `trading/gateway/interfaces.py` |
| 8 | `ILoadBalancer` | `trading/gateway/interfaces.py` |
| 9 | `ICircuitBreaker` | `trading/gateway/interfaces.py` |

### Enhance I* interfaces (9 classes)

All retained `I*` interfaces must have complete type annotations and docstrings for each method. Currently they only have `@abstractmethod` + `pass`.

**Before:**
```python
@abstractmethod
def initialize(self, config) -> None:
    pass
```

**After:**
```python
@abstractmethod
def initialize(self, config: dict) -> None:
    """初始化数据源。

    Args:
        config: 配置字典，包含连接信息、数据范围等。

    Raises:
        ConnectionError: 连接失败时抛出
    """
```

### Protocol classes (unchanged)

The 4 `Protocol` classes in `trading/interfaces/protocols/` keep their `I*` prefix and are not modified:
- `IRiskManagement`
- `IPortfolio`
- `IEngine`
- `IStrategy`

## Naming Conflicts

### Conflict 1: `BaseEngine`

| Location | Class |
|----------|-------|
| `trading/engines/base_engine.py` | `BaseEngine` (existing, production) |
| `core/interfaces/engine_interface.py` | `IEngine` (to be renamed) |

**Resolution**: The `trading/engines/base_engine.py` version is the production base class used by `EventEngine`. The `core/interfaces/` version is an interface-layer definition. After renaming `IEngine` to `BaseEngine` in `core/interfaces/`, both files export `BaseEngine`. The `trading/` version should be considered the canonical one. The `core/interfaces/` version's `BaseEngine` should be merged or the import path should be updated.

**Investigation needed**: Check if `core/interfaces/engine_interface.py` is imported anywhere directly (not via `trading/engines/`).

### Conflict 2: `BaseBroker`

| Location | Class |
|----------|-------|
| `trading/brokers/base_broker.py` | `BaseBroker` (existing, inherits `IBroker`) |
| `trading/brokers/interfaces.py` | `IBroker` (to be merged) |

**Resolution**: `BaseBroker` already inherits from `IBroker`. Delete the `IBroker` class entirely and move its type annotations/docstrings into `BaseBroker`. Update `isinstance` checks from `IBroker` to `BaseBroker`.

### Conflict 3: `StrategyBase`

| Location | Class |
|----------|-------|
| `trading/strategies/strategy_base.py` | `StrategyBase` (existing, 7 inheritors) |
| `core/interfaces/strategy_interface.py` | `IStrategy` (to be renamed to `BaseStrategy`) |

**Resolution**: Rename `StrategyBase` to `BaseStrategy` to match convention. The `core/interfaces/` `IStrategy` becomes `BaseStrategy` (interface layer definition). Check inheritance relationship and merge if needed.

## Execution Plan

**Batch 1**: `core/interfaces/` — the 4 most central interface files
- `strategy_interface.py`: `IStrategy` → `BaseStrategy`, `IMLStrategy` → `BaseMLStrategy`
- `model_interface.py`: `IModel` → `BaseModel`, `ITimeSeriesModel` → `BaseTimeSeriesModel`, `IEnsembleModel` → `BaseEnsembleModel`
- `engine_interface.py`: `IEngine` → `BaseEngine` (+ sub-interfaces), resolve conflict with `trading/engines/base_engine.py`
- `portfolio_interface.py`: `IPortfolio` → `BasePortfolio`, `IMultiStrategyPortfolio` → `BaseMultiStrategyPortfolio`

**Batch 2**: `trading/brokers/` + `trading/strategies/`
- Merge `IBroker` into `BaseBroker`
- Rename `StrategyBase` → `BaseStrategy`

**Batch 3**: `notifier/` + enhance all 9 pure `I*` interfaces
- `INotificationChannel` → `BaseNotificationChannel`
- Add type annotations and docstrings to all 9 retained `I*` interfaces

## Non-Changes

- `Protocol` classes in `trading/interfaces/protocols/` — unchanged
- `Base*` classes that already follow convention — unchanged
- False positives (`ICAnalyzer`, `ICStatistics`, `IMAX`, etc.) — unchanged (not interfaces)
- Existing `BaseCRUD`, `BaseService`, `BaseAnalyzer` etc. — unchanged

## Testing Strategy

1. After each batch: run full test suite
2. `grep -r "from.*import IStrategy\|from.*import IEngine\|from.*import IPortfolio\|from.*import IModel"` to find broken imports
3. Verify all subclasses still inherit correctly
4. Verify `isinstance` checks still work
