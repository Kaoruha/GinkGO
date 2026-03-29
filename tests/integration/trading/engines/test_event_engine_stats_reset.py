"""
EventEngine 统计重置测试 - 覆盖 reset_event_stats 修复

测试范围:
1. reset_event_stats 重置 _processed_events_count
2. reset_event_stats 重置 _processing_start_time
3. 重置后 get_engine_status 返回 0
4. 重置后 get_event_stats 返回 0
5. 重置后 processing_rate 为 0
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../../..'))

import time
import threading
from unittest.mock import MagicMock
import pytest

from ginkgo.trading.engines.event_engine import EventEngine
from ginkgo.enums import EVENT_TYPES


class TestEventEngineStatsReset:
    """reset_event_stats 重置计数器测试"""

    def _make_engine(self):
        engine = EventEngine(name="test_engine")
        engine.start()
        return engine

    def _process_events(self, engine, count=5):
        """向引擎中处理 count 个事件"""
        for i in range(count):
            event = MagicMock()
            event.event_type = EVENT_TYPES.PRICEUPDATE
            event.uuid = f"event-{i}"
            engine.put(event)
            time.sleep(0.01)
        # 等待处理完成
        time.sleep(0.1)

    def test_reset_clears_processed_events_count(self):
        """reset_event_stats 应重置 _processed_events_count"""
        engine = self._make_engine()
        try:
            self._process_events(engine, count=3)
            assert engine._processed_events_count == 3

            engine.reset_event_stats()
            assert engine._processed_events_count == 0
        finally:
            engine.stop()

    def test_reset_clears_processing_start_time(self):
        """reset_event_stats 应重置 _processing_start_time"""
        engine = self._make_engine()
        try:
            self._process_events(engine, count=1)
            assert engine._processing_start_time is not None

            engine.reset_event_stats()
            assert engine._processing_start_time is None
        finally:
            engine.stop()

    def test_reset_clears_event_stats_dict(self):
        """reset_event_stats 应重置 _event_stats 字典"""
        engine = self._make_engine()
        try:
            self._process_events(engine, count=2)
            assert engine._event_stats['completed_events'] == 2

            engine.reset_event_stats()
            assert engine._event_stats['completed_events'] == 0
            assert engine._event_stats['total_events'] == 0
            assert engine._event_stats['failed_events'] == 0
        finally:
            engine.stop()

    def test_get_engine_status_after_reset(self):
        """重置后 get_engine_status.processed_events 应为 0"""
        engine = self._make_engine()
        try:
            self._process_events(engine, count=5)
            engine.reset_event_stats()

            status = engine.get_engine_status()
            assert status.processed_events == 0
        finally:
            engine.stop()

    def test_get_event_stats_after_reset(self):
        """重置后 get_event_stats.processed_events 应为 0"""
        engine = self._make_engine()
        try:
            self._process_events(engine, count=5)
            engine.reset_event_stats()

            stats = engine.get_event_stats()
            assert stats.processed_events == 0
            # processing_rate 应为 0（start_time 已重置）
            assert stats.processing_rate == 0.0
        finally:
            engine.stop()

    def test_events_after_reset_count_correctly(self):
        """重置后新事件应从 0 开始计数"""
        engine = self._make_engine()
        try:
            self._process_events(engine, count=3)
            engine.reset_event_stats()

            self._process_events(engine, count=2)
            assert engine._processed_events_count == 2
        finally:
            engine.stop()

    def test_reset_on_fresh_engine(self):
        """未处理事件时重置不应报错"""
        engine = self._make_engine()
        try:
            engine.reset_event_stats()
            assert engine._processed_events_count == 0
            assert engine._processing_start_time is None
        finally:
            engine.stop()
