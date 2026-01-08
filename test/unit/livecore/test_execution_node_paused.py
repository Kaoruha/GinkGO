"""
ExecutionNode 单元测试：PAUSED 状态功能

测试 ExecutionNode 在 PAUSED 状态下的行为：
1. pause/resume 命令
2. get_status 返回正确信息
3. 心跳上报包含 paused 状态
4. 调度更新命令处理

运行方式：
    PYTHONPATH=/home/kaoru/Ginkgo/src python -m pytest test/unit/livecore/test_execution_node_paused.py -v
"""

import unittest
from unittest.mock import patch, MagicMock
import time

from ginkgo.workers.execution_node.node import ExecutionNode


class TestExecutionNodePausedState(unittest.TestCase):
    """
    ExecutionNode PAUSED 状态单元测试
    """

    def setUp(self):
        """测试前的准备工作"""
        # 创建 ExecutionNode 实例
        self.node = ExecutionNode(node_id="test_node")

    def tearDown(self):
        """测试后的清理工作"""
        if self.node.is_running:
            self.node.should_stop = True
            self.node.is_running = False

    # ========================================================================
    # 测试 1: 初始状态
    # ========================================================================

    def test_initial_state(self):
        """测试初始状态"""
        self.assertFalse(self.node.is_running)
        self.assertFalse(self.node.is_paused)
        self.assertFalse(self.node.should_stop)
        self.assertEqual(self.node.node_id, "test_node")

    # ========================================================================
    # 测试 2: pause 命令
    # ========================================================================

    def test_pause_command(self):
        """测试 pause 命令"""
        # 初始状态：未暂停
        self.assertFalse(self.node.is_paused)

        # 执行 pause
        self.node.pause()

        # 验证状态
        self.assertTrue(self.node.is_paused)

    def test_pause_when_already_paused(self):
        """测试已暂停状态下再次 pause"""
        # 设置为暂停
        self.node.is_paused = True

        # 再次 pause
        self.node.pause()

        # 验证状态保持暂停
        self.assertTrue(self.node.is_paused)

    # ========================================================================
    # 测试 3: resume 命令
    # ========================================================================

    def test_resume_command(self):
        """测试 resume 命令"""
        # 设置为暂停
        self.node.is_paused = True

        # 执行 resume
        self.node.resume()

        # 验证状态恢复
        self.assertFalse(self.node.is_paused)

    def test_resume_when_not_paused(self):
        """测试未暂停状态下 resume"""
        # 初始状态：未暂停
        self.assertFalse(self.node.is_paused)

        # 执行 resume
        self.node.resume()

        # 验证状态保持未暂停
        self.assertFalse(self.node.is_paused)

    # ========================================================================
    # 测试 4: get_status 方法
    # ========================================================================

    def test_get_status_when_running(self):
        """测试 RUNNING 状态的 get_status"""
        self.node.is_running = True
        self.node.is_paused = False
        self.node.should_stop = False

        status = self.node.get_status()

        self.assertEqual(status['node_id'], "test_node")
        self.assertEqual(status['status'], "RUNNING")
        self.assertTrue(status['is_running'])
        self.assertFalse(status['is_paused'])
        self.assertFalse(status['should_stop'])

    def test_get_status_when_paused(self):
        """测试 PAUSED 状态的 get_status"""
        self.node.is_running = True
        self.node.is_paused = True
        self.node.should_stop = False

        status = self.node.get_status()

        self.assertEqual(status['status'], "PAUSED")
        self.assertTrue(status['is_running'])
        self.assertTrue(status['is_paused'])

    def test_get_status_when_stopped(self):
        """测试 STOPPED 状态的 get_status"""
        self.node.is_running = False
        self.node.is_paused = False
        self.node.should_stop = True

        status = self.node.get_status()

        self.assertEqual(status['status'], "STOPPED")
        self.assertFalse(status['is_running'])

    # ========================================================================
    # 测试 5: 心跳上报包含 paused 状态
    # ========================================================================

    @patch('ginkgo.data.crud.RedisCRUD')
    def test_heartbeat_metrics_includes_paused_status(self, mock_redis_crud):
        """测试心跳指标包含 paused 状态"""
        # Mock Redis 客户端
        mock_redis = MagicMock()
        mock_redis_crud.return_value.redis = mock_redis

        # 设置为暂停
        self.node.is_running = True
        self.node.is_paused = True

        # 执行心跳指标更新
        self.node._update_node_metrics()

        # 验证 Redis hset 被调用
        self.assertTrue(mock_redis.hset.called)

        # 获取调用参数（使用 kwargs 中的 mapping）
        call_kwargs = mock_redis.hset.call_args.kwargs
        if 'mapping' in call_kwargs:
            metrics = call_kwargs['mapping']

            # 验证 metrics 包含 status 字段
            self.assertIn('status', metrics)
            self.assertEqual(metrics['status'], "PAUSED")
        else:
            self.fail("Redis hset was not called with mapping parameter")

    @patch('ginkgo.data.crud.RedisCRUD')
    def test_heartbeat_metrics_running_status(self, mock_redis_crud):
        """测试心跳指标的 RUNNING 状态"""
        # Mock Redis 客户端
        mock_redis = MagicMock()
        mock_redis_crud.return_value.redis = mock_redis

        # 设置为运行
        self.node.is_running = True
        self.node.is_paused = False

        # 执行心跳指标更新
        self.node._update_node_metrics()

        # 获取调用参数（使用 kwargs 中的 mapping）
        call_kwargs = mock_redis.hset.call_args.kwargs
        if 'mapping' in call_kwargs:
            metrics = call_kwargs['mapping']

            # 验证 status 为 RUNNING
            self.assertEqual(metrics['status'], "RUNNING")
        else:
            self.fail("Redis hset was not called with mapping parameter")

    # ========================================================================
    # 测试 6: 调度更新命令处理
    # ========================================================================

    def test_handle_node_pause_command(self):
        """测试 node.pause 命令处理"""
        # 初始状态：未暂停
        self.node.is_paused = False

        # 模拟命令数据
        command_data = {
            "command": "node.pause",
            "node_id": "test_node",
            "timestamp": "2026-01-06T10:00:00"
        }

        # 处理命令
        self.node._handle_node_pause(command_data)

        # 验证状态
        self.assertTrue(self.node.is_paused)

    def test_handle_node_resume_command(self):
        """测试 node.resume 命令处理"""
        # 设置为暂停
        self.node.is_paused = True

        # 模拟命令数据
        command_data = {
            "command": "node.resume",
            "node_id": "test_node",
            "timestamp": "2026-01-06T10:00:00"
        }

        # 处理命令
        self.node._handle_node_resume(command_data)

        # 验证状态
        self.assertFalse(self.node.is_paused)

    # ========================================================================
    # 测试 7: 事件处理暂停逻辑
    # ========================================================================

    def test_route_event_skips_when_paused(self):
        """测试 PAUSED 时事件路由被跳过"""
        from ginkgo.trading.events.price_update import EventPriceUpdate
        from datetime import datetime

        # 设置为暂停
        self.node.is_paused = True

        # 创建模拟事件
        event = EventPriceUpdate(
            code="000001.SZ",
            timestamp=datetime.now(),
            price=10.0,
            volume=1000
        )

        # 路由事件（应该被跳过）
        self.node._route_event_to_portfolios(event)

        # 验证事件计数未增加
        self.assertEqual(self.node.total_event_count, 0)

    def test_route_event_processes_when_not_paused(self):
        """测试未暂停时事件正常处理"""
        from ginkgo.trading.events.price_update import EventPriceUpdate
        from datetime import datetime

        # 确保未暂停
        self.node.is_paused = False

        # 创建模拟事件
        event = EventPriceUpdate(
            code="000001.SZ",
            timestamp=datetime.now(),
            price=10.0,
            volume=1000
        )

        # 路由事件（应该处理，即使没有portfolio也会增加计数）
        self.node._route_event_to_portfolios(event)

        # 验证事件计数增加
        self.assertEqual(self.node.total_event_count, 1)

    # ========================================================================
    # 测试 8: stop 方法
    # ========================================================================

    def test_stop_sets_flags(self):
        """测试 stop 方法设置标志"""
        # 设置为运行
        self.node.is_running = True

        # 执行 stop
        self.node.stop()

        # 验证标志
        self.assertTrue(self.node.should_stop)
        self.assertFalse(self.node.is_running)


if __name__ == '__main__':
    unittest.main()
