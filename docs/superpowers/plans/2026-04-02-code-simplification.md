# Code Simplification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove ~4,450 lines of dead code and over-engineering from the Ginkgo project in 4 phases.

**Architecture:** Delete unused custom DI framework, duplicate interfaces, and dead container files (Phase 1). Refactor ServiceHub from copy-paste properties to a registry-driven approach (Phase 2). Remove mechanically-applied decorators from pure CRUD wrapper service methods (Phase 3). Each phase is independently committable.

**Tech Stack:** Python 3.12.8, dependency_injector, pytest

---

## Phase 1: Dead Code Removal

### Task 1: Delete custom DI framework (`libs/containers/`)

**Files:**
- Delete: `src/ginkgo/libs/containers/__init__.py`
- Delete: `src/ginkgo/libs/containers/base_container.py`
- Delete: `src/ginkgo/libs/containers/container_registry.py`
- Delete: `src/ginkgo/libs/containers/dependency_manager.py`
- Delete: `src/ginkgo/libs/containers/config_driven_di.py`
- Delete: `src/ginkgo/libs/containers/application_container.py`
- Delete: `src/ginkgo/libs/containers/cross_container_proxy.py`
- Delete: `src/ginkgo/libs/containers/exceptions.py`
- Delete: `tests/unit/libs/containers/test_container_registry.py`
- Delete: `tests/unit/libs/containers/test_dependency_manager.py`
- Delete: `tests/unit/libs/containers/test_exceptions.py`

- [ ] **Step 1: Delete the directory**

Run:
```bash
rm -rf src/ginkgo/libs/containers/
rm -rf tests/unit/libs/containers/
```

- [ ] **Step 2: Verify no broken production imports**

Run:
```bash
grep -r "from ginkgo.libs.containers" src/ --include="*.py"
grep -r "from ginkgo.libs import.*containers" src/ --include="*.py"
```
Expected: zero results (only `module_container.py` imported it, which we delete in Task 3).

- [ ] **Step 3: Run test suite to confirm nothing breaks**

Run:
```bash
cd /home/kaoru/Ginkgo && python -m pytest tests/ -x -q --timeout=60 2>&1 | tail -30
```
Expected: Tests pass. If any test references deleted modules, fix in this step.

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "refactor: remove unused custom DI framework (libs/containers/)

~2,458 lines of dead code. Project runs on dependency_injector via ServiceHub.
Zero production consumers. Only test files referenced this code."
```

---

### Task 2: Delete duplicate IBroker interface

**Files:**
- Delete: `src/ginkgo/trading/brokers/interfaces.py`
- Modify: `src/ginkgo/trading/brokers/okx_broker.py:1095-1149`

- [ ] **Step 1: Check current BrokerPosition usage in okx_broker.py**

Read `src/ginkgo/trading/brokers/okx_broker.py` lines 1095-1149. The `BrokerPosition` import is inside a `try/except ImportError` block that wraps a legacy compat class `OKXBrokerLegacy`. Since this entire block imports `BaseBroker` which itself may not exist, and the whole block is wrapped in `try/except ImportError`, the `BrokerPosition` import will simply cause an `ImportError` which is caught and silently ignored.

- [ ] **Step 2: Delete the dead interface file**

Run:
```bash
rm src/ginkgo/trading/brokers/interfaces.py
```

- [ ] **Step 3: Remove BrokerPosition import from okx_broker.py**

In `src/ginkgo/trading/brokers/okx_broker.py`, line 1098, remove:
```python
from ginkgo.trading.brokers.interfaces import BrokerPosition
```
And change line 1143:
```python
async def get_positions(self) -> list[BrokerPosition]:
```
to:
```python
async def get_positions(self) -> list:
```
Since this is inside a `try/except ImportError` legacy compat block, this is safe.

- [ ] **Step 4: Check for any other imports of the deleted file**

Run:
```bash
grep -r "from ginkgo.trading.brokers.interfaces" src/ --include="*.py"
grep -r "from ginkgo.trading.brokers import.*interfaces" src/ --include="*.py"
```
Expected: zero results.

- [ ] **Step 5: Run tests**

Run:
```bash
cd /home/kaoru/Ginkgo && python -m pytest tests/ -x -q --timeout=60 2>&1 | tail -30
```

- [ ] **Step 6: Commit**

```bash
git add src/ginkgo/trading/brokers/interfaces.py src/ginkgo/trading/brokers/okx_broker.py
git commit -m "refactor: remove duplicate IBroker interface (dead code)

brokers/interfaces.py (438 lines) had zero inheritors. The canonical
interface is trading/interfaces/broker_interface.py used by all brokers."
```

---

### Task 3: Delete dead container files

**Files:**
- Delete: `src/ginkgo/data/module_container.py`
- Delete: `src/ginkgo/core/containers/core_container.py`
- Modify: `src/ginkgo/core/containers/__init__.py` (remove if only entry after deletion)

- [ ] **Step 1: Verify zero production imports**

Run:
```bash
grep -r "module_container" src/ --include="*.py" | grep -v __pycache__
grep -r "core_container" src/ --include="*.py" | grep -v __pycache__ | grep -v core_containers.py
```
Expected: `core/containers/__init__.py` imports from `core_containers.py` (NOT `core_container.py`), and `module_container.py` has no external importers.

- [ ] **Step 2: Delete the files**

Run:
```bash
rm src/ginkgo/data/module_container.py
rm src/ginkgo/core/containers/core_container.py
```

- [ ] **Step 3: Check if core/containers/ directory is now empty (besides __init__.py)**

Run:
```bash
ls -la src/ginkgo/core/containers/
```
If only `__init__.py` remains, that's fine — it re-exports from `core_containers.py`.

- [ ] **Step 4: Run tests**

Run:
```bash
cd /home/kaoru/Ginkgo && python -m pytest tests/ -x -q --timeout=60 2>&1 | tail -30
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor: remove dead BaseContainer module containers

data/module_container.py and core/containers/core_container.py were
built on the unused custom DI framework. Zero production code imported
them. Active containers use dependency_injector."
```

---

## Phase 2: ServiceHub Simplification

### Task 4: Refactor ServiceHub to registry-driven approach

**Files:**
- Modify: `src/ginkgo/service_hub.py` (full rewrite)

- [ ] **Step 1: Read current service_hub.py**

Read `src/ginkgo/service_hub.py` to understand all 12 module properties and their import paths. The key mapping is:

| Property | Import Path | Variable |
|----------|-------------|----------|
| data | `ginkgo.data.containers` | `container as data_container` |
| trading | `ginkgo.trading.core.containers` | `backtest_container` |
| core | `ginkgo.core.core_containers` | `container as core_container` |
| ml | `ginkgo.quant_ml.containers` | `container as ml_container` |
| features | `ginkgo.features.containers` | `feature_container` (+ `configure_features_container(self.data)`) |
| notifier | `ginkgo.notifier.containers` | `container as notifier_container` |
| research | `ginkgo.research.containers` | `research_container` |
| validation | `ginkgo.validation.containers` | `validation_container` |
| paper | `ginkgo.trading.paper.containers` | `paper_container` |
| comparison | `ginkgo.trading.comparison.containers` | `comparison_container` |
| optimization | `ginkgo.optimization.containers` | `optimization_container` |
| logging | `ginkgo.services.logging.containers` | `container as logging_container` |

**Important:** `features` has a special post-load hook (`configure_features_container(self.data)`) that must be preserved.

- [ ] **Step 2: Rewrite service_hub.py**

Replace the entire file with:

```python
# Upstream: 外部应用和CLI命令(统一服务访问入口from ginkgo import service_hub)
# Downstream: DataContainer/Data/Trading/Core/ML/Features容器(懒加载各模块容器提供依赖注入)
# Role: ServiceHub服务访问协调器提供懒加载/错误处理支持交易系统功能和组件集成提供完整业务支持


"""
Ginkgo ServiceHub - 统一服务访问协调器

通过注册表驱动的懒加载提供到各模块 dependency_injector 容器的统一访问。

Usage:
    from ginkgo import services
    bar_crud = services.data.cruds.bar()
    engine = services.trading.engines.time_controlled()
"""

from typing import Dict, Any, Optional, List
import time

from ginkgo.libs import GLOG


# 模块注册表: name → (module_path, attribute_name, post_load_hook)
_MODULE_REGISTRY: Dict[str, tuple] = {
    'data': ('ginkgo.data.containers', 'container', None),
    'trading': ('ginkgo.trading.core.containers', 'backtest_container', None),
    'core': ('ginkgo.core.core_containers', 'container', None),
    'ml': ('ginkgo.quant_ml.containers', 'container', None),
    'features': ('ginkgo.features.containers', 'feature_container', '_configure_features'),
    'notifier': ('ginkgo.notifier.containers', 'container', None),
    'research': ('ginkgo.research.containers', 'research_container', None),
    'validation': ('ginkgo.validation.containers', 'validation_container', None),
    'paper': ('ginkgo.trading.paper.containers', 'paper_container', None),
    'comparison': ('ginkgo.trading.comparison.containers', 'comparison_container', None),
    'optimization': ('ginkgo.trading.optimization.containers', 'optimization_container', None),
    'logging': ('ginkgo.services.logging.containers', 'container', None),
}


class ServiceHubError(Exception):
    """ServiceHub相关异常"""
    pass


class ServiceHub:
    """
    统一服务访问协调器

    通过注册表驱动的方式提供到各模块容器的懒加载访问。
    """

    def __init__(self):
        self._module_cache: Dict[str, Any] = {}
        self._module_errors: Dict[str, str] = {}
        self._debug_mode: bool = False

    def enable_debug(self) -> None:
        """启用调试模式"""
        self._debug_mode = True

    def disable_debug(self) -> None:
        """禁用调试模式"""
        self._debug_mode = False

    def __getattr__(self, name: str) -> Any:
        if name.startswith('_'):
            raise AttributeError(name)
        if name not in _MODULE_REGISTRY:
            raise AttributeError(f"ServiceHub has no module '{name}'")

        if name in self._module_cache:
            return self._module_cache[name]

        return self._load_module(name)

    def _load_module(self, name: str) -> Any:
        """加载并缓存模块容器"""
        module_path, attr_name, post_hook = _MODULE_REGISTRY[name]

        try:
            module = __import__(module_path, fromlist=[attr_name])
            container = getattr(module, attr_name)

            if post_hook:
                getattr(self, post_hook)(container)

            self._module_cache[name] = container
            return container
        except Exception as e:
            self._module_errors[name] = str(e)
            if self._debug_mode:
                GLOG.ERROR(f"{name} module error: {e}")
            return None

    def _configure_features(self, container) -> None:
        """features 模块后置配置"""
        from ginkgo.features.containers import configure_features_container
        configure_features_container(self.data)

    def get_module_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有模块状态"""
        status = {}
        for name in _MODULE_REGISTRY:
            try:
                module = getattr(self, name)
                status[name] = {
                    'available': module is not None,
                    'error': self._module_errors.get(name)
                }
            except Exception as e:
                status[name] = {'available': False, 'error': str(e)}
        return status

    def diagnose_issues(self) -> List[str]:
        """诊断并报告服务问题"""
        issues = []
        for name, info in self.get_module_status().items():
            if not info['available']:
                issues.append(f"{name}: {info['error']}")
        if issues:
            GLOG.ERROR(f"ServiceHub issues: {issues}")
        return issues

    def list_available_modules(self) -> List[str]:
        """列出可用模块"""
        return [name for name in _MODULE_REGISTRY if getattr(self, name, None) is not None]

    def clear_cache(self, module_name: Optional[str] = None) -> None:
        """清理模块缓存"""
        if module_name and module_name in self._module_cache:
            del self._module_cache[module_name]
        elif module_name is None:
            self._module_cache.clear()


# 创建全局ServiceHub实例
service_hub = ServiceHub()

# 为了向后兼容，保留services别名
services = service_hub

__all__ = ['service_hub', 'services']
```

- [ ] **Step 3: Verify external interface is unchanged**

Run these quick checks:
```bash
cd /home/kaoru/Ginkgo && python -c "from ginkgo import services; print('services type:', type(services).__name__)"
cd /home/kaoru/Ginkgo && python -c "from ginkgo import services; print('modules:', services.list_available_modules())"
```
Expected: `ServiceHub` type, list of available module names.

- [ ] **Step 4: Run test suite**

Run:
```bash
cd /home/kaoru/Ginkgo && python -m pytest tests/ -x -q --timeout=60 2>&1 | tail -30
```

- [ ] **Step 5: Commit**

```bash
git add src/ginkgo/service_hub.py
git commit -m "refactor: simplify ServiceHub from 501 to ~120 lines

Replace 12 copy-paste @property methods with registry-driven __getattr__.
External interface (services.data, services.trading, etc.) unchanged.
Remove over-engineered diagnostics/performance-measurement wrapper."
```

---

## Phase 3: Service Layer Decorator Cleanup

### Task 5: Remove @time_logger and @retry from pure CRUD wrapper methods in service files

**Files to modify** (17 files in `src/ginkgo/data/services/`):

| File | Decorator occurrences | Action |
|------|----------------------|--------|
| `analyzer_service.py` | 6 | Remove all (pure CRUD wrappers) |
| `param_service.py` | 24 | Remove @time_logger only; keep @retry on write operations (add/update/delete/copy) |
| `tick_service.py` | 10 | Remove @time_logger only; keep @retry on write operations |
| `adjustfactor_service.py` | 4 | Remove all (pure CRUD wrappers) |
| `factor_service.py` | 7 | Remove @time_logger only; keep @retry on write operations |
| `bar_service.py` | 6 | Remove @time_logger only; keep @retry on write operations |
| `mapping_service.py` | 18 | Remove @time_logger only; keep @retry on write operations |
| `result_service.py` | 22 | Remove @time_logger only; keep @retry on write operations |
| `stockinfo_service.py` | 6 | Remove @time_logger only; keep @retry on write operations |
| `backtest_task_service.py` | 25 | Remove @time_logger only; keep @retry on write operations |
| `portfolio_service.py` | 25 | Remove @time_logger only; keep @retry on write operations |
| `engine_service.py` | 26 | Remove @time_logger only; keep @retry on write operations |
| `live_account_service.py` | 8 | Remove @time_logger only; keep @retry on write operations |
| `portfolio_mapping_service.py` | 11 | Remove @time_logger only; keep @retry on write operations |
| `signal_tracking_service.py` | 46 | Review individually — this has the most decorators |
| `file_service.py` | 7 | Keep both (file I/O benefits from retry) |
| `redis_service.py` | 2 | Keep both (network calls benefit from retry) |

**Rule:**
- Remove `@time_logger` from ALL service methods (253 occurrences)
- Remove `@retry` from READ-only methods (get/find/count/list/query)
- Keep `@retry` on WRITE methods (add/create/update/delete) and external-call methods
- Keep ALL decorators on `file_service.py` and `redis_service.py` (I/O and network)

- [ ] **Step 1: Process each file — remove @time_logger from all service methods**

For each file listed above (except `file_service.py` and `redis_service.py`):
1. Open the file
2. Remove all `@time_logger` decorator lines
3. Remove `@retry(max_try=3)` from read-only methods (methods that only call `_crud_repo.find`, `_crud_repo.get`, or query data)
4. Keep `@retry(max_try=3)` on write methods (add/update/delete/create/remove/modify)

For `signal_tracking_service.py` (46 decorator occurrences), read each method first to determine if it's a read or write operation before removing decorators.

- [ ] **Step 2: Clean up unused imports**

After removing decorators, check each file for:
- `from ginkgo.libs.decorators import time_logger` — remove `time_logger` if no longer used
- `from ginkgo.libs.decorators import retry` — keep if `@retry` is still used on write methods
- If both were imported on one line and one is removed, adjust the import

- [ ] **Step 3: Run test suite**

Run:
```bash
cd /home/kaoru/Ginkgo && python -m pytest tests/ -x -q --timeout=60 2>&1 | tail -30
```
Expected: All tests pass. If any fail, it indicates a decorator was providing necessary behavior — investigate and fix.

- [ ] **Step 4: Commit**

```bash
git add src/ginkgo/data/services/
git commit -m "refactor: remove @time_logger from service layer CRUD methods

Remove ~200+ @time_logger uses and ~100+ @retry uses from read-only
service methods. Keep @retry on write operations and external-call
methods (file_service, redis_service)."
```

---

## Summary

| Task | Description | Files | Est. Lines Removed |
|------|-------------|-------|-------------------|
| 1 | Delete custom DI framework | 11 files deleted | ~2,458 |
| 2 | Delete duplicate IBroker | 1 file deleted, 1 modified | ~438 |
| 3 | Delete dead containers | 2 files deleted | ~706 |
| 4 | Simplify ServiceHub | 1 file rewritten | ~380 |
| 5 | Service decorator cleanup | 15 files modified | ~200+ decorator lines |
| **Total** | | | **~4,180+** |
