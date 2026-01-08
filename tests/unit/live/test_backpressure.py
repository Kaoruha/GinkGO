"""
BackpressureChecker 单元测试

测试 BackpressureChecker 的核心功能：
1. 队列状态检查（OK/WARNING/CRITICAL）
2. 背压阈值验证
3. 多Portfolio检查
4. 统计信息收集
5. 历史记录管理
6. 边界情况处理
"""

import pytest
from unittest.mock import MagicMock
from ginkgo.workers.execution_node.backpressure import BackpressureChecker


@pytest.mark.unit
class TestBackpressureCheckerInitialization:
    """测试 BackpressureChecker 初始化"""

    def test_init_default_thresholds(self):
        """测试默认阈值初始化"""
        checker = BackpressureChecker()

        assert checker.warning_threshold == 0.7
        assert checker.critical_threshold == 0.95
        assert checker.warning_count == 0
        assert checker.critical_count == 0
        assert checker.total_checks == 0
        assert len(checker.backpressure_history) == 0

        print(f"✅ BackpressureChecker 默认初始化成功")

    def test_init_custom_thresholds(self):
        """测试自定义阈值初始化"""
        checker = BackpressureChecker(warning_threshold=0.5, critical_threshold=0.8)

        assert checker.warning_threshold == 0.5
        assert checker.critical_threshold == 0.8

        print(f"✅ BackpressureChecker 自定义阈值初始化成功")


@pytest.mark.unit
class TestBackpressureCheckerQueueStatus:
    """测试队列状态检查"""

    def test_check_queue_status_ok(self):
        """测试正常队列状态"""
        checker = BackpressureChecker()

        result = checker.check_queue_status("portfolio_1", current_size=30, max_size=100)

        assert result["portfolio_id"] == "portfolio_1"
        assert result["usage"] == 0.3
        assert result["level"] == "OK"
        assert result["action"] == "accept"
        assert "30.0% capacity" in result["message"]
        assert checker.total_checks == 1
        assert checker.warning_count == 0
        assert checker.critical_count == 0

        print(f"✅ 队列状态检查（OK）成功")

    def test_check_queue_status_warning(self):
        """测试警告队列状态"""
        checker = BackpressureChecker(warning_threshold=0.7, critical_threshold=0.95)

        result = checker.check_queue_status("portfolio_1", current_size=75, max_size=100)

        assert result["portfolio_id"] == "portfolio_1"
        assert result["usage"] == 0.75
        assert result["level"] == "WARNING"
        assert result["action"] == "warn"
        assert "75.0% capacity (WARNING)" in result["message"]
        assert checker.total_checks == 1
        assert checker.warning_count == 1
        assert checker.critical_count == 0

        print(f"✅ 队列状态检查（WARNING）成功")

    def test_check_queue_status_critical(self):
        """测试严重队列状态"""
        checker = BackpressureChecker(warning_threshold=0.7, critical_threshold=0.95)

        result = checker.check_queue_status("portfolio_1", current_size=98, max_size=100)

        assert result["portfolio_id"] == "portfolio_1"
        assert result["usage"] == 0.98
        assert result["level"] == "CRITICAL"
        assert result["action"] == "reject"
        assert "98.0% capacity (CRITICAL)" in result["message"]
        assert checker.total_checks == 1
        assert checker.warning_count == 0
        assert checker.critical_count == 1

        print(f"✅ 队列状态检查（CRITICAL）成功")

    def test_check_queue_status_zero_max_size(self):
        """测试max_size为0的边界情况"""
        checker = BackpressureChecker()

        result = checker.check_queue_status("portfolio_1", current_size=50, max_size=0)

        assert result["usage"] == 0.0
        assert result["level"] == "OK"

        print(f"✅ 队列状态检查（零max_size）成功")

    def test_check_queue_status_full_queue(self):
        """测试满队列情况"""
        checker = BackpressureChecker()

        result = checker.check_queue_status("portfolio_1", current_size=100, max_size=100)

        assert result["usage"] == 1.0
        assert result["level"] == "CRITICAL"
        assert result["action"] == "reject"

        print(f"✅ 队列状态检查（满队列）成功")


@pytest.mark.unit
class TestBackpressureCheckerMultiplePortfolios:
    """测试多Portfolio检查"""

    def test_check_all_portfolios_empty(self):
        """测试检查空Portfolio列表"""
        checker = BackpressureChecker()

        results = checker.check_all_portfolios({})

        assert results == []
        assert checker.total_checks == 0

        print(f"✅ 检查空Portfolio列表成功")

    def test_check_all_portfolios_multiple(self):
        """测试检查多个Portfolio"""
        checker = BackpressureChecker()

        # 创建mock PortfolioProcessor
        processor_1 = MagicMock()
        processor_1.input_queue.qsize.return_value = 50
        processor_1.max_queue_size = 100

        processor_2 = MagicMock()
        processor_2.input_queue.qsize.return_value = 90
        processor_2.max_queue_size = 100

        portfolios = {
            "portfolio_1": processor_1,
            "portfolio_2": processor_2
        }

        results = checker.check_all_portfolios(portfolios)

        assert len(results) == 2
        assert results[0]["portfolio_id"] == "portfolio_1"
        assert results[0]["level"] == "OK"
        assert results[1]["portfolio_id"] == "portfolio_2"
        assert results[1]["level"] in ["WARNING", "CRITICAL"]  # 90%可能是WARNING或CRITICAL
        assert checker.total_checks == 2

        print(f"✅ 检查多个Portfolio成功")

    def test_check_all_portfolios_with_error(self):
        """测试Portfolio检查出错的情况"""
        checker = BackpressureChecker()

        # 创建一个会抛出异常的mock
        processor_broken = MagicMock()
        processor_broken.input_queue.qsize.side_effect = Exception("Queue error")

        portfolios = {
            "portfolio_broken": processor_broken
        }

        results = checker.check_all_portfolios(portfolios)

        assert len(results) == 1
        assert results[0]["portfolio_id"] == "portfolio_broken"
        assert results[0]["level"] == "ERROR"
        assert results[0]["usage"] == -1
        assert "Failed to check queue status" in results[0]["message"]

        print(f"✅ Portfolio检查错误处理成功")


@pytest.mark.unit
class TestBackpressureCheckerStatistics:
    """测试统计信息"""

    def test_get_statistics(self):
        """测试获取统计信息"""
        checker = BackpressureChecker(warning_threshold=0.6, critical_threshold=0.9)

        # 执行一些检查
        checker.check_queue_status("p1", 30, 100)  # OK
        checker.check_queue_status("p2", 70, 100)  # WARNING
        checker.check_queue_status("p3", 95, 100)  # CRITICAL

        stats = checker.get_statistics()

        assert stats["warning_threshold"] == 0.6
        assert stats["critical_threshold"] == 0.9
        assert stats["warning_count"] == 1
        assert stats["critical_count"] == 1
        assert stats["total_checks"] == 3
        assert stats["warning_rate"] == 1/3
        assert stats["critical_rate"] == 1/3
        assert stats["history_size"] == 3

        print(f"✅ 获取统计信息成功")

    def test_reset_statistics(self):
        """测试重置统计计数器"""
        checker = BackpressureChecker()

        # 执行一些检查
        checker.check_queue_status("p1", 70, 100)  # WARNING
        checker.check_queue_status("p2", 95, 100)  # CRITICAL

        assert checker.warning_count == 1
        assert checker.critical_count == 1
        assert checker.total_checks == 2
        assert len(checker.backpressure_history) == 2

        # 重置
        checker.reset_statistics()

        assert checker.warning_count == 0
        assert checker.critical_count == 0
        assert checker.total_checks == 0
        assert len(checker.backpressure_history) == 0

        print(f"✅ 重置统计计数器成功")


@pytest.mark.unit
class TestBackpressureCheckerHistory:
    """测试历史记录管理"""

    def test_history_recording(self):
        """测试历史记录保存"""
        checker = BackpressureChecker()

        checker.check_queue_status("p1", 30, 100)
        checker.check_queue_status("p2", 80, 100)

        assert len(checker.backpressure_history) == 2

        # 验证历史记录内容
        assert checker.backpressure_history[0]["portfolio_id"] == "p1"
        assert checker.backpressure_history[1]["portfolio_id"] == "p2"
        assert "timestamp" in checker.backpressure_history[0]
        assert "level" in checker.backpressure_history[0]

        print(f"✅ 历史记录保存成功")

    def test_history_limit(self):
        """测试历史记录大小限制（默认100条）"""
        checker = BackpressureChecker()

        # 添加超过默认限制（100）的记录
        for i in range(105):
            checker.check_queue_status(f"p{i}", 50, 100)

        # 历史记录应该被限制在100
        assert len(checker.backpressure_history) == 100

        # 最早的记录应该被删除，保留最近100条
        assert checker.backpressure_history[0]["portfolio_id"] == "p5"
        assert checker.backpressure_history[-1]["portfolio_id"] == "p104"

        print(f"✅ 历史记录大小限制成功")

    def test_get_history_limit(self):
        """测试获取限制数量的历史记录"""
        checker = BackpressureChecker()

        # 添加10条记录
        for i in range(10):
            checker.check_queue_status(f"p{i}", 50, 100)

        # 获取最近5条
        history = checker.get_history(limit=5)

        assert len(history) == 5
        assert history[0]["portfolio_id"] == "p5"
        assert history[-1]["portfolio_id"] == "p9"

        print(f"✅ 获取限制数量历史记录成功")


@pytest.mark.unit
class TestBackpressureCheckerUtilityMethods:
    """测试工具方法"""

    def test_repr(self):
        """测试__repr__方法"""
        checker = BackpressureChecker(warning_threshold=0.6, critical_threshold=0.9)

        # 执行一些检查以增加计数器
        checker.check_queue_status("p1", 70, 100)  # WARNING
        checker.check_queue_status("p2", 95, 100)  # CRITICAL

        repr_str = repr(checker)

        assert "BackpressureChecker" in repr_str
        assert "warning=60%" in repr_str or "warning=0.6" in repr_str
        assert "critical=90%" in repr_str or "critical=0.9" in repr_str
        assert "warnings=1" in repr_str
        assert "criticals=1" in repr_str

        print(f"✅ __repr__方法正确: {repr_str}")


@pytest.mark.unit
class TestBackpressureCheckerEdgeCases:
    """测试边界情况"""

    def test_negative_usage(self):
        """测试负使用率（current_size > max_size）"""
        checker = BackpressureChecker()

        result = checker.check_queue_status("p1", 150, 100)

        # 使用率会超过1.0
        assert result["usage"] == 1.5
        assert result["level"] == "CRITICAL"
        assert result["action"] == "reject"

        print(f"✅ 负使用率处理成功")

    def test_exactly_at_threshold(self):
        """测试恰好等于阈值的情况"""
        checker = BackpressureChecker(warning_threshold=0.7, critical_threshold=0.95)

        # 恰好等于warning_threshold
        result1 = checker.check_queue_status("p1", 70, 100)
        assert result1["level"] == "WARNING"

        # 恰好等于critical_threshold
        result2 = checker.check_queue_status("p2", 95, 100)
        assert result2["level"] == "CRITICAL"

        print(f"✅ 阈值边界处理成功")
