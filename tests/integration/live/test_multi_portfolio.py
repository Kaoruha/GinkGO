"""
多Portfolio集成测试

测试 ExecutionNode 多Portfolio并行运行的核心功能：
1. 加载多个Portfolio
2. InterestMap路由优化
3. 背压监控集成
4. 并发事件处理
5. Portfolio隔离验证
"""

import pytest
from unittest.mock import MagicMock, Mock
from decimal import Decimal
from datetime import datetime

from ginkgo.workers.execution_node.node import ExecutionNode
from ginkgo.workers.execution_node.interest_map import InterestMap
from ginkgo.workers.execution_node.backpressure import BackpressureChecker


@pytest.mark.integration
class TestMultiPortfolioLoading:
    """测试多Portfolio加载"""

    def test_load_single_portfolio(self):
        """测试加载单个Portfolio"""
        # 注意：完整实现需要数据库支持，这里测试基本逻辑
        interest_map = InterestMap()

        # 模拟添加订阅
        interest_map.add_portfolio("portfolio_1", ["000001.SZ", "000002.SZ"])

        # 验证InterestMap状态
        assert "000001.SZ" in interest_map
        assert "000002.SZ" in interest_map
        assert interest_map.get_portfolios("000001.SZ") == ["portfolio_1"]

        print(f"✅ 单个Portfolio加载测试通过")

    def test_load_multiple_portfolios(self):
        """测试加载多个Portfolio"""
        interest_map = InterestMap()

        # 加载多个Portfolio，每个订阅不同股票
        interest_map.add_portfolio("portfolio_1", ["000001.SZ", "000002.SZ", "600000.SH"])
        interest_map.add_portfolio("portfolio_2", ["000002.SZ", "600036.SH", "600519.SH"])
        interest_map.add_portfolio("portfolio_3", ["000001.SZ", "600000.SH"])

        # 验证InterestMap状态
        assert interest_map.size() == 5  # 5个唯一股票代码

        # 验证000001.SZ有2个订阅者
        subscribers_000001 = interest_map.get_portfolios("000001.SZ")
        assert len(subscribers_000001) == 2
        assert "portfolio_1" in subscribers_000001
        assert "portfolio_3" in subscribers_000001

        # 验证000002.SZ有2个订阅者
        subscribers_000002 = interest_map.get_portfolios("000002.SZ")
        assert set(subscribers_000002) == {"portfolio_1", "portfolio_2"}

        print(f"✅ 多个Portfolio加载测试通过")


@pytest.mark.integration
class TestInterestMapRoutingOptimization:
    """测试InterestMap路由优化"""

    def test_o1_lookup_performance(self):
        """测试O(1)查找性能"""
        interest_map = InterestMap()

        # 添加大量Portfolio和订阅
        for i in range(100):
            portfolio_id = f"portfolio_{i}"
            codes = [f"00000{j % 10}.SZ" for j in range(i, i + 5)]
            interest_map.add_portfolio(portfolio_id, codes)

        # 测试查找速度（应该非常快，O(1)复杂度）
        import time

        start = time.time()
        for _ in range(1000):
            result = interest_map.get_portfolios("000005.SZ")
        end = time.time()

        # 1000次查找应该在很短时间内完成（< 0.1秒）
        assert end - start < 0.1
        assert len(result) > 0  # 应该有订阅者

        print(f"✅ O(1)查找性能测试通过（1000次查找耗时: {end - start:.4f}秒）")

    def test_routing_accuracy(self):
        """测试路由准确性"""
        interest_map = InterestMap()

        # 创建复杂的订阅关系
        interest_map.add_portfolio("portfolio_a", ["000001.SZ", "000002.SZ"])
        interest_map.add_portfolio("portfolio_b", ["000002.SZ", "000003.SZ"])
        interest_map.add_portfolio("portfolio_c", ["000001.SZ", "000003.SZ"])

        # 验证路由准确性
        # 000001.SZ应该路由到portfolio_a和portfolio_c
        subscribers_1 = interest_map.get_portfolios("000001.SZ")
        assert set(subscribers_1) == {"portfolio_a", "portfolio_c"}

        # 000002.SZ应该路由到portfolio_a和portfolio_b
        subscribers_2 = interest_map.get_portfolios("000002.SZ")
        assert set(subscribers_2) == {"portfolio_a", "portfolio_b"}

        # 000003.SZ应该路由到portfolio_b和portfolio_c
        subscribers_3 = interest_map.get_portfolios("000003.SZ")
        assert set(subscribers_3) == {"portfolio_b", "portfolio_c"}

        print(f"✅ 路由准确性测试通过")


@pytest.mark.integration
class TestBackpressureIntegration:
    """测试背压监控集成"""

    def test_backpressure_checker_integration(self):
        """测试BackpressureChecker集成"""
        checker = BackpressureChecker(warning_threshold=0.7, critical_threshold=0.95)

        # 创建mock processors
        processor_1 = MagicMock()
        processor_1.input_queue.qsize.return_value = 65
        processor_1.max_queue_size = 100

        processor_2 = MagicMock()
        processor_2.input_queue.qsize.return_value = 90
        processor_2.max_queue_size = 100

        processor_3 = MagicMock()
        processor_3.input_queue.qsize.return_value = 30
        processor_3.max_queue_size = 100

        portfolios = {
            "portfolio_1": processor_1,
            "portfolio_2": processor_2,
            "portfolio_3": processor_3
        }

        # 检查所有Portfolio
        results = checker.check_all_portfolios(portfolios)

        assert len(results) == 3

        # 验证检查结果
        result_1 = next(r for r in results if r["portfolio_id"] == "portfolio_1")
        assert result_1["level"] == "OK"  # 65% < 70%

        result_2 = next(r for r in results if r["portfolio_id"] == "portfolio_2")
        assert result_2["level"] in ["WARNING", "CRITICAL"]  # 90% >= 70%

        result_3 = next(r for r in results if r["portfolio_id"] == "portfolio_3")
        assert result_3["level"] == "OK"  # 30% < 70%

        # 验证统计信息
        stats = checker.get_statistics()
        assert stats["total_checks"] == 3

        print(f"✅ BackpressureChecker集成测试通过")

    def test_backpressure_critical_rejection(self):
        """测试严重背压时的消息拒绝"""
        checker = BackpressureChecker()

        # 创建一个严重背压的Portfolio
        processor = MagicMock()
        processor.input_queue.qsize.return_value = 98
        processor.max_queue_size = 100

        result = checker.check_queue_status("critical_portfolio", 98, 100)

        assert result["level"] == "CRITICAL"
        assert result["action"] == "reject"
        assert result["usage"] == 0.98

        print(f"✅ 严重背压拒绝测试通过")


@pytest.mark.integration
class TestConcurrentEventProcessing:
    """测试并发事件处理"""

    def test_simultaneous_price_updates(self):
        """测试同时处理多个价格更新"""
        interest_map = InterestMap()

        # 设置订阅关系
        interest_map.add_portfolio("portfolio_1", ["000001.SZ", "000002.SZ"])
        interest_map.add_portfolio("portfolio_2", ["000002.SZ", "000003.SZ"])
        interest_map.add_portfolio("portfolio_3", ["000001.SZ", "000003.SZ"])

        # 模拟并发事件路由（快速连续查询）
        codes = ["000001.SZ", "000002.SZ", "000003.SZ"]
        results = {}

        for code in codes:
            subscribers = interest_map.get_portfolios(code)
            results[code] = subscribers

        # 验证路由正确性
        assert set(results["000001.SZ"]) == {"portfolio_1", "portfolio_3"}
        assert set(results["000002.SZ"]) == {"portfolio_1", "portfolio_2"}
        assert set(results["000003.SZ"]) == {"portfolio_2", "portfolio_3"}

        print(f"✅ 并发价格更新处理测试通过")

    def test_subscription_update_during_processing(self):
        """测试处理过程中的订阅更新"""
        interest_map = InterestMap()

        # 初始订阅
        interest_map.add_portfolio("portfolio_1", ["000001.SZ", "000002.SZ"])

        # 验证初始状态
        assert set(interest_map.get_portfolios("000001.SZ")) == {"portfolio_1"}

        # 更新订阅（移除000001.SZ，添加000003.SZ）
        old_codes = ["000001.SZ", "000002.SZ"]
        new_codes = ["000002.SZ", "000003.SZ"]
        interest_map.update_portfolio("portfolio_1", old_codes, new_codes)

        # 验证更新后的状态
        assert interest_map.get_portfolios("000001.SZ") == []  # 已取消订阅
        assert set(interest_map.get_portfolios("000002.SZ")) == {"portfolio_1"}  # 保持订阅
        assert set(interest_map.get_portfolios("000003.SZ")) == {"portfolio_1"}  # 新增订阅

        print(f"✅ 处理过程中订阅更新测试通过")


@pytest.mark.integration
class TestPortfolioIsolationWithInterestMap:
    """测试使用InterestMap的Portfolio隔离"""

    def test_portfolio_unsubscription(self):
        """测试Portfolio取消订阅"""
        interest_map = InterestMap()

        # 三个Portfolio都订阅000001.SZ
        interest_map.add_portfolio("portfolio_1", ["000001.SZ"])
        interest_map.add_portfolio("portfolio_2", ["000001.SZ"])
        interest_map.add_portfolio("portfolio_3", ["000001.SZ"])

        assert len(interest_map.get_portfolios("000001.SZ")) == 3

        # portfolio_1取消订阅
        interest_map.remove_portfolio("portfolio_1", ["000001.SZ"])

        subscribers = interest_map.get_portfolios("000001.SZ")
        assert len(subscribers) == 2
        assert "portfolio_1" not in subscribers
        assert "portfolio_2" in subscribers
        assert "portfolio_3" in subscribers

        print(f"✅ Portfolio取消订阅测试通过")

    def test_portfolio_complex_isolation(self):
        """测试复杂的Portfolio隔离场景"""
        interest_map = InterestMap()

        # 复杂的订阅关系
        interest_map.add_portfolio("portfolio_a", ["000001.SZ", "000002.SZ", "000003.SZ"])
        interest_map.add_portfolio("portfolio_b", ["000002.SZ", "000003.SZ", "000004.SZ"])
        interest_map.add_portfolio("portfolio_c", ["000003.SZ", "000004.SZ", "000005.SZ"])

        # 验证每个股票的订阅者
        assert set(interest_map.get_portfolios("000001.SZ")) == {"portfolio_a"}
        assert set(interest_map.get_portfolios("000002.SZ")) == {"portfolio_a", "portfolio_b"}
        assert set(interest_map.get_portfolios("000003.SZ")) == {"portfolio_a", "portfolio_b", "portfolio_c"}
        assert set(interest_map.get_portfolios("000004.SZ")) == {"portfolio_b", "portfolio_c"}
        assert set(interest_map.get_portfolios("000005.SZ")) == {"portfolio_c"}

        # portfolio_a取消所有订阅
        interest_map.remove_portfolio("portfolio_a", ["000001.SZ", "000002.SZ", "000003.SZ"])

        # 验证取消后的状态
        assert interest_map.get_portfolios("000001.SZ") == []  # 无订阅者，代码被删除
        assert set(interest_map.get_portfolios("000002.SZ")) == {"portfolio_b"}
        assert set(interest_map.get_portfolios("000003.SZ")) == {"portfolio_b", "portfolio_c"}

        print(f"✅ 复杂Portfolio隔离测试通过")


@pytest.mark.integration
class TestInterestMapUtilityMethods:
    """测试InterestMap工具方法"""

    def test_size_and_len(self):
        """测试size和len方法"""
        interest_map = InterestMap()

        assert interest_map.size() == 0
        assert len(interest_map) == 0

        interest_map.add_portfolio("p1", ["000001.SZ", "000002.SZ"])
        interest_map.add_portfolio("p2", ["000002.SZ", "000003.SZ"])

        assert interest_map.size() == 3  # 3个唯一代码
        assert len(interest_map) == 3

        print(f"✅ size和len方法测试通过")

    def test_contains(self):
        """测试__contains__方法"""
        interest_map = InterestMap()

        assert "000001.SZ" not in interest_map

        interest_map.add_portfolio("p1", ["000001.SZ"])

        assert "000001.SZ" in interest_map
        assert "000002.SZ" not in interest_map

        print(f"✅ __contains__方法测试通过")

    def test_get_all_subscriptions(self):
        """测试获取Portfolio的所有订阅"""
        interest_map = InterestMap()

        interest_map.add_portfolio("p1", ["000001.SZ", "000002.SZ"])
        interest_map.add_portfolio("p2", ["000002.SZ", "000003.SZ"])
        interest_map.add_portfolio("p3", ["000001.SZ", "000004.SZ"])

        # 获取p1的所有订阅
        p1_subs = interest_map.get_all_subscriptions("p1")
        assert set(p1_subs) == {"000001.SZ", "000002.SZ"}

        # 获取p2的所有订阅
        p2_subs = interest_map.get_all_subscriptions("p2")
        assert set(p2_subs) == {"000002.SZ", "000003.SZ"}

        # 获取不存在的Portfolio的订阅
        p4_subs = interest_map.get_all_subscriptions("p4")
        assert p4_subs == []

        print(f"✅ 获取所有订阅测试通过")

    def test_clear(self):
        """测试清空InterestMap"""
        interest_map = InterestMap()

        interest_map.add_portfolio("p1", ["000001.SZ", "000002.SZ"])
        interest_map.add_portfolio("p2", ["000003.SZ"])

        assert interest_map.size() == 3

        interest_map.clear()

        assert interest_map.size() == 0
        assert len(interest_map) == 0

        print(f"✅ 清空InterestMap测试通过")


@pytest.mark.integration
class TestBackpressureEdgeCases:
    """测试背压监控边界情况"""

    def test_empty_queue_division(self):
        """测试空队列的除零保护"""
        checker = BackpressureChecker()

        # max_size为0的情况
        result = checker.check_queue_status("test", 0, 0)

        assert result["usage"] == 0.0
        assert result["level"] == "OK"

        print(f"✅ 空队列除零保护测试通过")

    def test_negative_queue_size(self):
        """测试负队列大小（异常情况）"""
        checker = BackpressureChecker()

        # current_size为负数（异常）
        result = checker.check_queue_status("test", -10, 100)

        assert result["usage"] == -0.1
        assert result["level"] == "OK"

        print(f"✅ 负队列大小处理测试通过")

    def test_statistics_with_no_checks(self):
        """测试无检查时的统计信息"""
        checker = BackpressureChecker()

        stats = checker.get_statistics()

        assert stats["total_checks"] == 0
        assert stats["warning_count"] == 0
        assert stats["critical_count"] == 0
        assert stats["warning_rate"] == 0.0
        assert stats["critical_rate"] == 0.0

        print(f"✅ 无检查统计信息测试通过")
