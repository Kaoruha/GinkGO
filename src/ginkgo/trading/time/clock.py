"""
Global Clock Adapter

提供一个轻量全局时钟适配层，便于在尚未彻底注入 ITimeProvider 的代码中，
统一通过 clock.now() 获取当前时间：
- 若已设置全局 provider，则返回 provider.now()
- 否则回退为系统 UTC 时间
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from .interfaces import ITimeProvider

_GLOBAL_TIME_PROVIDER: Optional[ITimeProvider] = None


def set_global_time_provider(provider: ITimeProvider) -> None:
    global _GLOBAL_TIME_PROVIDER
    _GLOBAL_TIME_PROVIDER = provider


def get_global_time_provider() -> Optional[ITimeProvider]:
    return _GLOBAL_TIME_PROVIDER


def now() -> datetime:
    """获取当前时间（优先使用全局 provider）"""
    if _GLOBAL_TIME_PROVIDER is not None:
        try:
            return _GLOBAL_TIME_PROVIDER.now()
        except Exception:
            pass
    # 回退到系统 UTC 时间
    return datetime.now(timezone.utc)

