"""
ClickHouse 流式引擎连接生命周期测试 (#5505)

验证流式游标清理时归还借出的池连接，而非销毁底层 dbapi 连接。
缺陷表象：池连接被 _cleanup_cursor 通过 cursor.connection.close() 物理销毁，
         每次流式查询消耗一个池连接，pool_size 次后系统挂起。
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

project_root = Path(__file__).resolve().parents[5]
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.data.streaming.engines.clickhouse_streaming_engine import ClickHouseStreamingEngine

# NOTE: config 用 MagicMock 而非真实 StreamingConfig，隔离 engine/config 字段不同步问题
# （engine 引用的 enable_column_optimization 等字段在 PerformanceConfig 中不存在），
# 让测试聚焦 #5505 的连接生命周期行为本身。


@pytest.mark.unit
@pytest.mark.database
class TestClickHouseStreamingConnectionLifecycle:
    """ClickHouse 流式引擎连接生命周期 (#5505)"""

    def _make_engine(self):
        """构造带分身 mock 的引擎：池代理与底层 dbapi 连接分离"""
        fake_underlying = MagicMock(name="underlying_dbapi_conn")
        fake_cursor = MagicMock(name="streaming_cursor")
        fake_cursor.connection = fake_underlying  # cursor.connection 穿透到底层
        fake_raw = MagicMock(name="pooled_raw_connection")  # 池代理（close=归还）
        fake_raw.cursor.return_value = fake_cursor
        fake_engine = MagicMock(name="sqlalchemy_engine")
        fake_engine.raw_connection.return_value = fake_raw
        engine = ClickHouseStreamingEngine(fake_engine, MagicMock(name="streaming_config"))
        return engine, fake_raw, fake_cursor, fake_underlying

    def test_cleanup_returns_borrowed_connection_instead_of_destroying_underlying(self):
        """清理游标时应归还借出的池连接，而非销毁底层 dbapi 连接"""
        engine, fake_raw, fake_cursor, fake_underlying = self._make_engine()

        cursor = engine._create_streaming_cursor("SELECT 1")
        engine._cleanup_cursor(cursor)

        # 归还：借出的池代理连接被关闭（SQLAlchemy 池语义下 close = 归还）
        fake_raw.close.assert_called_once()
        # 不销毁：底层 dbapi 连接（cursor.connection）未被物理关闭
        fake_underlying.close.assert_not_called()

    def test_repeated_queries_return_every_borrowed_connection(self):
        """多次流式查询：每次借出的池连接都被归还，池不会耗尽 (#5505)"""
        borrowed = []

        def lend_raw():
            raw = MagicMock(name="pooled_raw")
            cursor = MagicMock(name="streaming_cursor")
            cursor.connection = MagicMock(name="underlying")
            raw.cursor.return_value = cursor
            borrowed.append(raw)
            return raw

        fake_engine = MagicMock(name="sqlalchemy_engine")
        fake_engine.raw_connection.side_effect = lend_raw

        engine = ClickHouseStreamingEngine(fake_engine, MagicMock(name="streaming_config"))

        # 连续 5 次流式查询（超过典型 pool_size 的压力）
        for _ in range(5):
            cursor = engine._create_streaming_cursor("SELECT 1")
            engine._cleanup_cursor(cursor)

        # 5 次借出，5 次归还，无一泄漏（否则第 pool_size+1 次查询会因池耗尽而挂起）
        assert len(borrowed) == 5
        for raw in borrowed:
            raw.close.assert_called_once()
