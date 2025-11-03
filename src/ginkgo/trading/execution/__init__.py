"""
Legacy compatibility layer for ginkgo.trading.execution.*

This package preserves backward-compatible import paths used by older tests
and extensions, mapping them to the reorganized modules in ginkgo.trading.*.

Examples:
- ginkgo.trading.execution.engines   -> ginkgo.trading.engines
- ginkgo.trading.execution.events    -> ginkgo.trading.events
- ginkgo.trading.execution.feeders   -> ginkgo.trading.feeders
- ginkgo.trading.execution.portfolios-> ginkgo.trading.portfolios
- ginkgo.trading.execution.routing   -> ginkgo.trading.routing

The layer raises a deprecation warning the first time any legacy path is used.
"""

from __future__ import annotations

import sys
import warnings
from types import ModuleType


def _warn_once(old_path: str, new_path: str) -> None:
    key = (old_path, new_path)
    warned = getattr(_warn_once, "_warned", set())
    if key not in warned:
        warnings.warn(
            f"Importing '{old_path}' is deprecated. Use '{new_path}' instead.",
            DeprecationWarning,
            stacklevel=3,
        )
        warned.add(key)
        _warn_once._warned = warned  # type: ignore[attr-defined]


class _CompatModule(ModuleType):
    def __init__(self, name: str, target: ModuleType):
        super().__init__(name)
        self._target = target
        self._old_path = name
        self._new_path = target.__name__
        self.__dict__.update(target.__dict__)

    def __getattr__(self, item):
        _warn_once(self._old_path, self._new_path)
        return getattr(self._target, item)


# Map legacy subpackages to new ones
try:
    from ginkgo.trading import engines as _engines
    from ginkgo.trading import events as _events
    from ginkgo.trading import feeders as _feeders
    from ginkgo.trading import portfolios as _portfolios
    from ginkgo.trading import routing as _routing
except Exception:  # pragma: no cover - best-effort mapping
    _engines = _events = _feeders = _portfolios = _routing = None  # type: ignore


_MAPPINGS = {
    "ginkgo.trading.execution.engines": _engines,
    "ginkgo.trading.execution.events": _events,
    "ginkgo.trading.execution.feeders": _feeders,
    "ginkgo.trading.execution.portfolios": _portfolios,
    "ginkgo.trading.execution.routing": _routing,
}


for legacy_name, target in list(_MAPPINGS.items()):
    if target is not None:
        # Register module alias for direct imports
        sys.modules.setdefault(legacy_name, _CompatModule(legacy_name, target))


__all__ = [
    "_CompatModule",
]

