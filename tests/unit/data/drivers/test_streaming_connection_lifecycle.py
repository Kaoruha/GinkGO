# Issue: #5514
# Upstream: ginkgo.data.drivers.base_driver.DatabaseDriverBase
# Downstream: pytest
# Role: 流式查询连接生命周期管理（return 方法 + context manager + 计数器对称）

"""
DatabaseDriverBase 流式连接生命周期测试

根因：get_streaming_connection (base_driver.py:226-244) 返回裸连接无归还机制，
active_streaming_connections 计数器 +1（line 240）无配对 -1 路径，调用方无法
归还连接 → 连接泄漏 + 计数虚高/负数。对比 streaming_session（line 201-224）有
完整 try/finally，get_streaming_connection 没有。

修复：新增 return_streaming_connection()（显式归还）+ streaming_connection()
context manager（自动归还，try/finally），计数器 increment/decrement 对称，
return 带 active>0 guard 防负数。
"""

import pytest
from unittest.mock import MagicMock

from ginkgo.data.drivers.base_driver import DatabaseDriverBase


class _ConcreteDriver(DatabaseDriverBase):
    """最小具体子类（测试抽象基类，mock 掉抽象方法）"""
    def __init__(self):
        super().__init__("TestDriver")
    def _create_engine(self): return MagicMock()
    def _create_streaming_engine(self): return MagicMock()
    def _health_check_query(self): return "SELECT 1"
    def _get_uri(self): return "test://localhost"
    def _get_streaming_uri(self): return "test://localhost/streaming"


def _make_driver():
    """构造已启用 streaming 的 driver（mock _streaming_engine，跳过真实初始化）"""
    driver = _ConcreteDriver()
    driver._streaming_enabled = True
    driver._streaming_engine = MagicMock()
    return driver


@pytest.mark.unit
class TestStreamingConnectionLifecycle:
    """#5514: 流式连接必须可归还，计数器对称（get +1 / return -1）"""

    def test_context_manager_releases_on_exit(self):
        """context manager 退出时 close 连接 + 计数器归零（验收：连接生命周期）"""
        driver = _make_driver()
        mock_conn = MagicMock()
        driver._streaming_engine.raw_connection.return_value = mock_conn

        with driver.streaming_connection() as conn:
            assert conn is mock_conn
            # 进入时计数 +1（与 get_streaming_connection 的 increment 对称）
            assert driver._connection_stats["active_streaming_connections"] == 1

        # 退出后计数归零 + 连接被 close
        assert driver._connection_stats["active_streaming_connections"] == 0
        mock_conn.close.assert_called_once()

    def test_context_manager_releases_on_exception(self):
        """context manager 内抛异常时，finally 仍 close + 计数归零（验收：try/finally 对称）"""
        driver = _make_driver()
        mock_conn = MagicMock()
        driver._streaming_engine.raw_connection.return_value = mock_conn

        with pytest.raises(ValueError, match="boom"):
            with driver.streaming_connection() as conn:
                assert driver._connection_stats["active_streaming_connections"] == 1
                raise ValueError("boom")

        # 异常路径也归还，否则一次失败永久泄漏一个连接 + 计数虚高
        assert driver._connection_stats["active_streaming_connections"] == 0
        mock_conn.close.assert_called_once()

    def test_return_streaming_connection_decrements_counter(self):
        """显式 return_streaming_connection：close 连接 + 计数 -1（验收：return 方法存在）"""
        driver = _make_driver()
        mock_conn = MagicMock()
        driver._streaming_engine.raw_connection.return_value = mock_conn

        conn = driver.get_streaming_connection()
        assert driver._connection_stats["active_streaming_connections"] == 1

        driver.return_streaming_connection(conn)

        assert driver._connection_stats["active_streaming_connections"] == 0
        assert driver._connection_stats["streaming_connections_closed"] == 1
        mock_conn.close.assert_called_once()

    def test_return_guard_prevents_negative_counter(self):
        """多余 return 不致 active 计数下穿 0 变负（验收：counter 不负）"""
        driver = _make_driver()
        mock_conn = MagicMock()
        driver._streaming_engine.raw_connection.return_value = mock_conn

        conn = driver.get_streaming_connection()   # active 0 → 1
        driver.return_streaming_connection(conn)    # active 1 → 0
        driver.return_streaming_connection(conn)    # guard：active 已 0，不减；close 仍调用

        assert driver._connection_stats["active_streaming_connections"] == 0
        assert mock_conn.close.call_count == 2
