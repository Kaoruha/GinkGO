"""
conftest.py - Shared fixtures and helpers for trading engine tests.
"""
import pytest


def safe_get_event(engine, timeout=0.1):
    """安全获取事件，从内部队列直接读取（仅用于测试验证）"""
    try:
        return engine._event_queue.get(timeout=timeout)
    except Exception:
        return None
