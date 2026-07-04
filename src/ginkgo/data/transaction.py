from __future__ import annotations

import contextvars
from contextlib import contextmanager
from typing import Callable, ContextManager, Dict, Iterator, Optional

from sqlalchemy.orm import Session


_session_registry_ctx: contextvars.ContextVar[Dict[str, Session]] = contextvars.ContextVar(
    "data_transaction_sessions",
    default={},
)


def get_transaction_session(key: str) -> Optional[Session]:
    """Return the active transaction session for the given key, if any."""
    return _session_registry_ctx.get().get(key)


@contextmanager
def transaction_scope(key: str, session_factory: Callable[[], ContextManager[Session]]) -> Iterator[Session]:
    """
    Provide a single transaction entry point per storage key.

    Nested calls with the same key reuse the active session; the outermost
    scope remains responsible for automatic commit / rollback via the driver's
    context-managed session factory.
    """
    current = get_transaction_session(key)
    if current is not None:
        yield current
        return

    with session_factory() as session:
        registry = dict(_session_registry_ctx.get())
        registry[key] = session
        token = _session_registry_ctx.set(registry)
        try:
            yield session
        finally:
            _session_registry_ctx.reset(token)
