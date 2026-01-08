"""
ExecutionNode.load_portfolio() 集成测试

测试 ExecutionNode 的 Portfolio 加载功能：
1. 从数据库加载预置的present_portfolio_live（is_live=True）
2. 验证is_live=True检查
3. 创建PortfolioProcessor和双队列
4. 启动output_queue监听器
5. 处理Portfolio不存在的情况
6. 处理非实盘Portfolio的情况
7. 处理重复加载的情况
8. unload_portfolio() 卸载Portfolio

注意：这些测试使用ginkgo init创建的预置Portfolio进行测试，
不需要mock，直接使用真实的数据库连接。
"""

import pytest
from queue import Queue

from ginkgo.workers.execution_node.node import ExecutionNode
from ginkgo.data.containers import container

# 从依赖注入容器获取服务实例
portfolio_service = container.portfolio_service()


@pytest.mark.integration
@pytest.mark.live
class TestExecutionNodeLoadPortfolio:
    """测试 ExecutionNode.load_portfolio() 方法 - 使用真实Portfolio"""

    @pytest.fixture(autouse=True)
    def setup_portfolio(self):
        """确保预置Portfolio存在"""
        # 尝试获取present_portfolio_live
        result = portfolio_service.get(filters={"name": "present_portfolio_live"})

        if not result.success or len(result.data) == 0:
            pytest.skip("预置Portfolio 'present_portfolio_live' 不存在，请先运行 'ginkgo init'")

    def test_load_present_portfolio_live_success(self):
        """测试成功加载预置的实盘Portfolio"""
        node = ExecutionNode(node_id="test_node_load")

        # 获取present_portfolio_live的UUID
        result = portfolio_service.get(filters={"name": "present_portfolio_live"})
        assert result.success, f"获取present_portfolio_live失败: {result.error}"
        assert len(result.data) > 0, "present_portfolio_live不存在"

        portfolio_uuid = result.data[0].uuid
        print(f"📋 找到预置Portfolio: {portfolio_uuid}")

        # 加载Portfolio
        load_result = node.load_portfolio(portfolio_uuid)

        # 验证加载成功
        assert load_result == True, f"加载Portfolio失败"
        assert len(node.portfolios) == 1, f"应该有1个Portfolio"
        assert portfolio_uuid in node.portfolios, f"Portfolio应该在portfolios字典中"
        assert portfolio_uuid in node._portfolio_instances, f"Portfolio应该在_portfolio_instances中"

        # 验证PortfolioProcessor已启动
        processor = node.portfolios[portfolio_uuid]
        assert processor.is_running == True, "PortfolioProcessor应该正在运行"

        print(f"✅ 成功加载预置实盘Portfolio: {portfolio_uuid[:8]}")

        # 清理
        node.unload_portfolio(portfolio_uuid)

    def test_load_portfolio_checks_is_live_flag(self):
        """测试load_portfolio检查is_live标志"""
        node = ExecutionNode(node_id="test_node_is_live")

        # 获取present_portfolio（回测Portfolio，is_live=False）
        result = portfolio_service.get(filters={"name": "present_portfolio"})
        if not result.success or len(result.data) == 0:
            pytest.skip("预置Portfolio 'present_portfolio' 不存在")

        portfolio_uuid = result.data[0].uuid

        # 尝试加载回测Portfolio（应该失败，因为is_live=False）
        load_result = node.load_portfolio(portfolio_uuid)

        # 验证加载失败（因为is_live=False）
        assert load_result == False, "加载非实盘Portfolio应该失败"
        assert len(node.portfolios) == 0, "不应该有Portfolio被加载"

        print(f"✅ 正确拒绝非实盘Portfolio")

    def test_load_portfolio_duplicate_fails(self):
        """测试重复加载同一个Portfolio失败"""
        node = ExecutionNode(node_id="test_node_duplicate")

        # 获取present_portfolio_live的UUID
        result = portfolio_service.get(filters={"name": "present_portfolio_live"})
        if not result.success or len(result.data) == 0:
            pytest.skip("预置Portfolio 'present_portfolio_live' 不存在")

        portfolio_uuid = result.data[0].uuid

        # 第一次加载
        load_result_1 = node.load_portfolio(portfolio_uuid)
        assert load_result_1 == True, "第一次加载应该成功"

        # 第二次加载（应该失败）
        load_result_2 = node.load_portfolio(portfolio_uuid)
        assert load_result_2 == False, "重复加载应该失败"

        print(f"✅ 重复加载被正确拒绝")

        # 清理
        node.unload_portfolio(portfolio_uuid)

    def test_load_non_existent_portfolio_fails(self):
        """测试加载不存在的Portfolio失败"""
        node = ExecutionNode(node_id="test_node_not_found")

        # 使用不存在的UUID
        fake_uuid = "00000000-0000-0000-0000-000000000000"

        # 尝试加载
        load_result = node.load_portfolio(fake_uuid)

        # 验证加载失败
        assert load_result == False, "加载不存在的Portfolio应该失败"
        assert len(node.portfolios) == 0, "不应该有Portfolio被加载"

        print(f"✅ 正确拒绝不存在的Portfolio")


@pytest.mark.integration
@pytest.mark.live
class TestExecutionNodeUnloadPortfolio:
    """测试 ExecutionNode.unload_portfolio() 方法"""

    @pytest.fixture(autouse=True)
    def setup_portfolio(self):
        """确保预置Portfolio存在"""
        result = portfolio_service.get(filters={"name": "present_portfolio_live"})

        if not result.success or len(result.data) == 0:
            pytest.skip("预置Portfolio 'present_portfolio_live' 不存在")

    def test_unload_portfolio_success(self):
        """测试成功卸载Portfolio"""
        node = ExecutionNode(node_id="test_node_unload")

        # 获取present_portfolio_live的UUID
        result = portfolio_service.get(filters={"name": "present_portfolio_live"})
        portfolio_uuid = result.data[0].uuid

        # 先加载Portfolio
        load_result = node.load_portfolio(portfolio_uuid)
        assert load_result == True

        # 卸载Portfolio
        unload_result = node.unload_portfolio(portfolio_uuid)

        assert unload_result == True
        assert len(node.portfolios) == 0, "portfolios应该为空"
        assert len(node._portfolio_instances) == 0, "_portfolio_instances应该为空"

        print(f"✅ Portfolio卸载成功")

    def test_unload_non_existent_portfolio_fails(self):
        """测试卸载不存在的Portfolio失败"""
        node = ExecutionNode(node_id="test_node_unload_not_found")

        # 尝试卸载不存在的Portfolio
        fake_uuid = "00000000-0000-0000-0000-000000000000"
        unload_result = node.unload_portfolio(fake_uuid)

        assert unload_result == False
        print(f"✅ 正确拒绝卸载不存在的Portfolio")


@pytest.mark.integration
@pytest.mark.live
class TestExecutionNodePortfolioStatusAfterLoad:
    """测试加载Portfolio后的ExecutionNode状态"""

    @pytest.fixture(autouse=True)
    def setup_portfolio(self):
        """确保预置Portfolio存在"""
        result = portfolio_service.get(filters={"name": "present_portfolio_live"})

        if not result.success or len(result.data) == 0:
            pytest.skip("预置Portfolio 'present_portfolio_live' 不存在")

    def test_status_includes_loaded_portfolio(self):
        """测试加载Portfolio后的状态包含Portfolio信息"""
        node = ExecutionNode(node_id="test_node_status")

        # 获取present_portfolio_live的UUID
        result = portfolio_service.get(filters={"name": "present_portfolio_live"})
        portfolio_uuid = result.data[0].uuid

        # 加载Portfolio
        node.load_portfolio(portfolio_uuid)

        # 获取状态
        status = node.get_status()

        assert status["portfolio_count"] == 1
        assert portfolio_uuid in status["portfolios"]

        # 验证Portfolio状态
        portfolio_status = status["portfolios"][portfolio_uuid]
        assert "state" in portfolio_status
        assert "is_running" in portfolio_status
        assert portfolio_status["is_running"] == True

        print(f"✅ 加载Portfolio后状态正确")

        # 清理
        node.unload_portfolio(portfolio_uuid)


@pytest.mark.integration
@pytest.mark.live
class TestExecutionNodePortfolioDualQueues:
    """测试加载Portfolio创建的双队列模式"""

    @pytest.fixture(autouse=True)
    def setup_portfolio(self):
        """确保预置Portfolio存在"""
        result = portfolio_service.get(filters={"name": "present_portfolio_live"})

        if not result.success or len(result.data) == 0:
            pytest.skip("预置Portfolio 'present_portfolio_live' 不存在")

    def test_load_portfolio_creates_dual_queues(self):
        """测试加载Portfolio创建双队列模式"""
        node = ExecutionNode(node_id="test_node_dual_queues")

        # 获取present_portfolio_live的UUID
        result = portfolio_service.get(filters={"name": "present_portfolio_live"})
        portfolio_uuid = result.data[0].uuid

        # 加载Portfolio
        node.load_portfolio(portfolio_uuid)

        # 验证PortfolioProcessor有input_queue和output_queue
        processor = node.portfolios[portfolio_uuid]
        assert hasattr(processor, 'input_queue'), "应该有input_queue"
        assert hasattr(processor, 'output_queue'), "应该有output_queue"
        assert isinstance(processor.input_queue, Queue), "input_queue应该是Queue"
        assert isinstance(processor.output_queue, Queue), "output_queue应该是Queue"

        print(f"✅ 双队列模式创建成功")

        # 清理
        node.unload_portfolio(portfolio_uuid)
