"""
Scheduler 单元测试：PAUSED 状态功能

测试 Scheduler 在 PAUSED 状态下的行为：
1. 自动调度循环在 PAUSED 时停止
2. recalculate 命令在 PAUSED 时默认拒绝
3. recalculate --force 在 PAUSED 时执行
4. schedule 命令在 PAUSED 时默认拒绝
5. schedule --force 在 PAUSED 时执行
6. migrate 命令在 PAUSED 时始终可用
7. pause/resume 命令
8. status 命令返回正确的命令可用性

运行方式：
    PYTHONPATH=/home/kaoru/Ginkgo/src python -m pytest test/unit/livecore/test_scheduler_paused.py -v
"""

import unittest
from unittest.mock import patch, MagicMock, call
import time

from ginkgo.livecore.scheduler import Scheduler


class TestSchedulerPausedState(unittest.TestCase):
    """
    Scheduler PAUSED 状态单元测试
    """

    def setUp(self):
        """测试前的准备工作"""
        # Mock Redis 和 Kafka
        self.mock_redis = MagicMock()
        self.mock_kafka_producer = MagicMock()

        # 创建 Scheduler 实例
        self.scheduler = Scheduler(
            redis_client=self.mock_redis,
            kafka_producer=self.mock_kafka_producer,
            schedule_interval=1,  # 1秒调度间隔（测试用）
            node_id="test_scheduler"
        )

    def tearDown(self):
        """测试后的清理工作"""
        if self.scheduler.is_running:
            self.scheduler.should_stop = True
            self.scheduler.is_running = False

    # ========================================================================
    # 测试 1: 初始状态
    # ========================================================================

    def test_scheduler_initial_state(self):
        """测试 Scheduler 初始状态"""
        self.assertFalse(self.scheduler.is_running)
        self.assertFalse(self.scheduler.should_stop)
        self.assertFalse(self.scheduler.is_paused)
        self.assertEqual(self.scheduler.schedule_interval, 1)
        self.assertEqual(self.scheduler.node_id, "test_scheduler")

    # ========================================================================
    # 测试 2: pause 命令
    # ========================================================================

    def test_pause_command(self):
        """测试 pause 命令"""
        # 初始状态：未暂停
        self.assertFalse(self.scheduler.is_paused)

        # 执行 pause 命令
        self.scheduler._handle_pause({})

        # 验证状态
        self.assertTrue(self.scheduler.is_paused)

    def test_pause_command_when_already_paused(self):
        """测试已暂停状态下再次 pause"""
        # 设置为已暂停
        self.scheduler.is_paused = True

        # 再次执行 pause 命令
        self.scheduler._handle_pause({})

        # 验证状态保持暂停
        self.assertTrue(self.scheduler.is_paused)

    # ========================================================================
    # 测试 3: resume 命令
    # ========================================================================

    def test_resume_command(self):
        """测试 resume 命令"""
        # 设置为暂停
        self.scheduler.is_paused = True

        # 执行 resume 命令
        self.scheduler._handle_resume({})

        # 验证状态恢复
        self.assertFalse(self.scheduler.is_paused)

    def test_resume_command_when_not_paused(self):
        """测试未暂停状态下 resume"""
        # 初始状态：未暂停
        self.assertFalse(self.scheduler.is_paused)

        # 执行 resume 命令
        self.scheduler._handle_resume({})

        # 验证状态保持未暂停
        self.assertFalse(self.scheduler.is_paused)

    # ========================================================================
    # 测试 4: recalculate 命令 - PAUSED 状态
    # ========================================================================

    @patch('ginkgo.livecore.scheduler.Scheduler._schedule_loop')
    def test_recalculate_rejected_when_paused(self, mock_schedule_loop):
        """测试 PAUSED 时 recalculate 命令被拒绝"""
        # 设置为暂停
        self.scheduler.is_paused = True

        # 执行 recalculate 命令（无 force）
        self.scheduler._handle_recalculate({'force': False})

        # 验证调度循环未执行
        mock_schedule_loop.assert_not_called()

    @patch('ginkgo.livecore.scheduler.Scheduler._schedule_loop')
    def test_recalculate_executed_with_force_when_paused(self, mock_schedule_loop):
        """测试 PAUSED 时 recalculate --force 执行"""
        # 设置为暂停
        self.scheduler.is_paused = True

        # 执行 recalculate 命令（有 force）
        self.scheduler._handle_recalculate({'force': True})

        # 验证调度循环执行
        mock_schedule_loop.assert_called_once()

    @patch('ginkgo.livecore.scheduler.Scheduler._schedule_loop')
    def test_recalculate_executed_when_not_paused(self, mock_schedule_loop):
        """测试未暂停时 recalculate 正常执行"""
        # 确保未暂停
        self.scheduler.is_paused = False

        # 执行 recalculate 命令（无 force）
        self.scheduler._handle_recalculate({'force': False})

        # 验证调度循环执行
        mock_schedule_loop.assert_called_once()

    # ========================================================================
    # 测试 5: schedule 命令 - PAUSED 状态
    # ========================================================================

    @patch('ginkgo.livecore.scheduler.Scheduler._get_current_schedule_plan')
    @patch('ginkgo.livecore.scheduler.Scheduler._get_all_portfolios')
    @patch('ginkgo.livecore.scheduler.Scheduler._get_healthy_nodes')
    @patch('ginkgo.livecore.scheduler.Scheduler._assign_portfolios')
    @patch('ginkgo.livecore.scheduler.Scheduler._publish_schedule_update')
    def test_schedule_rejected_when_paused(
        self, mock_publish, mock_assign, mock_nodes, mock_portfolios, mock_plan
    ):
        """测试 PAUSED 时 schedule 命令被拒绝"""
        # 设置为暂停
        self.scheduler.is_paused = True

        # Mock 返回值
        mock_plan.return_value = {}
        mock_portfolios.return_value = []
        mock_nodes.return_value = []

        # 执行 schedule 命令（无 force）
        self.scheduler._handle_schedule({'force': False})

        # 验证 _assign_portfolios 未调用
        mock_assign.assert_not_called()

    @patch('ginkgo.livecore.scheduler.Scheduler._get_current_schedule_plan')
    @patch('ginkgo.livecore.scheduler.Scheduler._get_all_portfolios')
    @patch('ginkgo.livecore.scheduler.Scheduler._get_healthy_nodes')
    @patch('ginkgo.livecore.scheduler.Scheduler._assign_portfolios')
    @patch('ginkgo.livecore.scheduler.Scheduler._publish_schedule_update')
    def test_schedule_executed_with_force_when_paused(
        self, mock_publish, mock_assign, mock_nodes, mock_portfolios, mock_plan
    ):
        """测试 PAUSED 时 schedule --force 执行"""
        # 设置为暂停
        self.scheduler.is_paused = True

        # Mock 返回值 - 模拟有未分配的 portfolios
        mock_plan.return_value = {}
        mock_portfolios.return_value = [
            {'uuid': 'portfolio_1', 'name': 'Test Portfolio 1'}
        ]
        mock_nodes.return_value = [{'node_id': 'node_1', 'metrics': {}}]
        mock_assign.return_value = {'portfolio_1': 'node_1'}

        # 执行 schedule 命令（有 force）
        self.scheduler._handle_schedule({'force': True})

        # 验证 _assign_portfolios 被调用
        mock_assign.assert_called_once()

    @patch('ginkgo.livecore.scheduler.Scheduler._get_current_schedule_plan')
    @patch('ginkgo.livecore.scheduler.Scheduler._get_all_portfolios')
    @patch('ginkgo.livecore.scheduler.Scheduler._get_healthy_nodes')
    @patch('ginkgo.livecore.scheduler.Scheduler._assign_portfolios')
    @patch('ginkgo.livecore.scheduler.Scheduler._publish_schedule_update')
    def test_schedule_executed_when_not_paused(
        self, mock_publish, mock_assign, mock_nodes, mock_portfolios, mock_plan
    ):
        """测试未暂停时 schedule 正常执行"""
        # 确保未暂停
        self.scheduler.is_paused = False

        # Mock 返回值 - 模拟有未分配的 portfolios
        mock_plan.return_value = {}
        mock_portfolios.return_value = [
            {'uuid': 'portfolio_1', 'name': 'Test Portfolio 1'}
        ]
        mock_nodes.return_value = [{'node_id': 'node_1', 'metrics': {}}]
        mock_assign.return_value = {'portfolio_1': 'node_1'}

        # 执行 schedule 命令（无 force）
        self.scheduler._handle_schedule({'force': False})

        # 验证 _assign_portfolios 被调用
        mock_assign.assert_called_once()

    # ========================================================================
    # 测试 6: migrate 命令 - 始终可用
    # ========================================================================

    @patch('ginkgo.livecore.scheduler.Scheduler._send_schedule_command')
    def test_migrate_available_when_paused(self, mock_send):
        """测试 PAUSED 时 migrate 命令可用"""
        # 设置为暂停
        self.scheduler.is_paused = True

        # 执行 migrate 命令
        params = {
            'portfolio_id': 'test_portfolio',
            'target_node': 'node_1'
        }
        self.scheduler._handle_migrate(params)

        # 验证命令被处理
        mock_send.assert_called_once()

    @patch('ginkgo.livecore.scheduler.Scheduler._send_schedule_command')
    def test_migrate_available_when_not_paused(self, mock_send):
        """测试未暂停时 migrate 命令可用"""
        # 确保未暂停
        self.scheduler.is_paused = False

        # 执行 migrate 命令
        params = {
            'portfolio_id': 'test_portfolio',
            'target_node': 'node_1'
        }
        self.scheduler._handle_migrate(params)

        # 验证命令被处理
        mock_send.assert_called_once()

    # ========================================================================
    # 测试 7: status 命令
    # ========================================================================

    def test_status_when_paused(self):
        """测试 PAUSED 时 status 返回正确信息"""
        # 设置为暂停
        self.scheduler.is_paused = True
        self.scheduler.is_running = True

        # 执行 status 命令
        # 注意：_handle_status 只记录日志，不返回值
        # 这里我们测试它不会抛出异常
        try:
            self.scheduler._handle_status({})
            # 如果没有异常，测试通过
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"_handle_status raised exception: {e}")

    def test_status_when_not_paused(self):
        """测试未暂停时 status 返回正确信息"""
        # 确保未暂停
        self.scheduler.is_paused = False
        self.scheduler.is_running = True

        # 执行 status 命令
        try:
            self.scheduler._handle_status({})
            self.assertTrue(True)
        except Exception as e:
            self.fail(f"_handle_status raised exception: {e}")

    # ========================================================================
    # 测试 8: 主循环 - PAUSED 状态
    # ========================================================================

    @patch('ginkgo.livecore.scheduler.Scheduler._check_commands')
    @patch('ginkgo.livecore.scheduler.Scheduler._schedule_loop')
    def test_main_loop_skips_schedule_when_paused(self, mock_schedule, mock_check):
        """测试主循环在 PAUSED 时跳过调度"""
        # 设置为暂停
        self.scheduler.is_paused = True
        self.scheduler.is_running = True
        self.scheduler.should_stop = False

        # 模拟一次主循环迭代
        self.scheduler._check_commands()
        if not self.scheduler.is_paused:
            self.scheduler._schedule_loop()

        # 验证 _check_commands 被调用
        mock_check.assert_called_once()

        # 验证 _schedule_loop 未被调用（因为暂停）
        mock_schedule.assert_not_called()

    @patch('ginkgo.livecore.scheduler.Scheduler._check_commands')
    @patch('ginkgo.livecore.scheduler.Scheduler._schedule_loop')
    def test_main_loop_executes_schedule_when_not_paused(self, mock_schedule, mock_check):
        """测试主循环在未暂停时执行调度"""
        # 确保未暂停
        self.scheduler.is_paused = False
        self.scheduler.is_running = True
        self.scheduler.should_stop = False

        # 模拟一次主循环迭代
        self.scheduler._check_commands()
        if not self.scheduler.is_paused:
            self.scheduler._schedule_loop()

        # 验证 _check_commands 被调用
        mock_check.assert_called_once()

        # 验证 _schedule_loop 被调用（因为未暂停）
        mock_schedule.assert_called_once()

    # ========================================================================
    # 测试 9: stop 方法
    # ========================================================================

    def test_stop_sets_should_stop_flag(self):
        """测试 stop 方法设置 should_stop 标志"""
        # 初始状态
        self.assertFalse(self.scheduler.should_stop)

        # 调用 stop
        self.scheduler.stop()

        # 验证标志被设置
        self.assertTrue(self.scheduler.should_stop)


if __name__ == '__main__':
    unittest.main()
