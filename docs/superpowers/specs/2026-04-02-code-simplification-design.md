# Code Simplification Design

**Date**: 2026-04-02
**Status**: Approved
**Scope**: Remove dead code, simplify ServiceHub, reduce decorator noise

## Background

Ginkgo project has ~195,000 lines of Python code. Analysis revealed ~4,450 lines of removable over-engineering across 5 categories: dead DI framework, duplicate interfaces, dead container files, ServiceHub repetition, and mechanical decorator application.

## Changes

### Phase 1: Dead Code Removal

#### 1.1 Delete custom DI framework (`libs/containers/`)

**Files to delete (7 files, ~2,458 lines):**
- `src/ginkgo/libs/containers/base_container.py` (400 lines)
- `src/ginkgo/libs/containers/container_registry.py` (424 lines)
- `src/ginkgo/libs/containers/dependency_manager.py` (472 lines)
- `src/ginkgo/libs/containers/config_driven_di.py` (421 lines)
- `src/ginkgo/libs/containers/application_container.py` (375 lines)
- `src/ginkgo/libs/containers/cross_container_proxy.py` (290 lines)
- `src/ginkgo/libs/containers/exceptions.py` (76 lines)

**Why**: Zero production consumers. Project runs on `dependency_injector` via `ServiceHub`.
**Test impact**: 3 test files reference the framework.

#### 1.2 Delete duplicate IBroker interface

**File to delete:**
- `src/ginkgo/trading/brokers/interfaces.py` (438 lines)

**Why**: `IBroker` in this file has zero inheritors. The canonical interface is `trading/interfaces/broker_interface.py` (250 lines), used by all 7 broker implementations.
**Migration**: Move `BrokerPosition` (used by `okx_broker.py` in TYPE_CHECKING) to local definition or import from broker_interface.

#### 1.3 Delete dead container files

**Files to delete (2 files, ~706 lines):**
- `src/ginkgo/data/module_container.py` (258 lines)
- `src/ginkgo/core/containers/core_container.py` (448 lines)

**Why**: Both import `BaseContainer` from the dead DI framework. Both create container instances that zero production code imports. The `dependency_injector` versions (`data/containers.py` and `core/core_containers.py`) are the active ones.
**Note**: Check if `core/containers/` directory has other files after deletion.

### Phase 2: ServiceHub Simplification

#### 2.1 Registry-driven ServiceHub

**File to modify:**
- `src/ginkgo/service_hub.py` (501 lines → ~150 lines)

**Change**: Replace 12 copy-paste `@property` methods (~300 lines) with a registry-driven `get_module()` + dynamic property generation. Keep external interface (`services.data`, `services.trading`, etc.) unchanged.

**Before (per module, ~25 lines each):**
```python
@property
def data(self):
    if 'data' in self._module_cache:
        return self._module_cache['data']
    @self._measure_performance('data')
    def _load_data():
        from ginkgo.data.containers import container
        return container
    try:
        container = _load_data()
        self._module_cache['data'] = container
        return container
    except Exception as e:
        self._module_errors['data'] = str(e)
        if self._debug_mode:
            GLOG.ERROR(f"Data module error: {e}")
            import traceback
            traceback.print_exc()
        return None
```

**After (single method + registry):**
```python
_MODULE_REGISTRY = {
    'data': 'ginkgo.data.containers:container',
    'trading': 'ginkgo.trading.core.containers:backtest_container',
    'core': 'ginkgo.core.core_containers:container',
    # ... etc
}

def __getattr__(self, name):
    if name not in self._MODULE_REGISTRY:
        raise AttributeError(f"No module '{name}'")
    return self._load_module(name)
```

### Phase 3: Service Layer Decorator Cleanup

#### 3.1 Remove @time_logger and @retry from pure CRUD wrapper methods

**Scope**: Service layer files where methods are pure CRUD delegation (call CRUD then wrap in ServiceResult).
**Keep**: Decorators on methods that perform external calls (data sources, broker APIs, network operations).

**Files to review** (service layer, not exhaustive):
- `data/services/param_service.py`
- `data/services/analyzer_service.py`
- `data/services/result_service.py`
- `data/services/bar_service.py`
- Other service files with thin CRUD wrappers

**Rule**: If a method only calls `self._crud_repo.find/create/modify/remove()` and wraps the result, remove both decorators.

## Non-Changes (Explicitly Kept)

- **Empty directories** (23): Kept for future architecture
- **OrderService stub** (61 lines): Kept as Phase 3 placeholder
- **BaseService** (272 lines): Kept as-is
- **BaseCRUD** (2,332 lines): Kept as-is
- **ABC base classes** (Strategy/Analyzer/RiskManagement): Kept — justified by multiple implementations
- **@cache_with_expiration** (16 uses): Kept — targeted and reasonable
- **Decorators on external-call methods**: Kept (data sources, broker, network)

## Estimated Impact

| Phase | Lines Removed | Risk |
|-------|--------------|------|
| 1.1 Custom DI framework | ~2,458 | Low |
| 1.2 Duplicate IBroker | ~438 | Low |
| 1.3 Dead containers | ~706 | Low |
| 2.1 ServiceHub simplification | ~350 | Low |
| 3.1 Decorator cleanup | ~500+ decorator uses | Medium |
| **Total** | **~4,450** | |

## Testing Strategy

1. Run full test suite after each phase
2. Phase 1: Fix any test imports referencing deleted modules
3. Phase 2: Verify `services.data.cruds.bar()` etc. still work
4. Phase 3: Verify service methods still return correct results
