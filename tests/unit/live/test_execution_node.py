"""
ExecutionNode 单元测试

测试 ExecutionNode 主类的基础功能：
1. 实例化 ExecutionNode（不需要数据库）
2. start() 和 stop() 方法（不需要数据库）
3. get_status() 获取状态（不需要数据库）
4. InterestMap功能（不需要数据库）
5. portfolios字典功能（不需要数据库）

注意：这些测试只测试ExecutionNode的基础功能，不测试需要数据库的load_portfolio功能。
load_portfolio测试在test_execution_node_load_portfolio.py中使用真实Portfolio。
"""

import pytest
from ginkgo.workers.execution_node.node import ExecutionNode


@pytest.mark.unit
class TestExecutionNodeBasics:
    """测试 ExecutionNode 基础功能"""

    def test_execution_node_initialization(self):
        """测试 ExecutionNode 实例化"""
        node = ExecutionNode(node_id="test_node")

        assert node.node_id == "test_node"
        assert node.is_running == False
        assert len(node.portfolios) == 0
        assert len(node._portfolio_instances) == 0
        assert len(node.interest_map) == 0
        print(f"✅ ExecutionNode 初始化成功: node_id={node.node_id}")

    @pytest.mark.skip(reason="Phase 4: run_id参数尚未实现")
    def test_execution_node_initialization_with_run_id(self):
        """测试使用run_id初始化（Phase 4功能）"""
        node = ExecutionNode(node_id="test_node_with_run", run_id="test_run_001")

        assert node.node_id == "test_node_with_run"
        assert node.run_id == "test_run_001"
        assert node.is_running == False
        print(f"✅ ExecutionNode 使用run_id初始化成功")

    def test_execution_node_id_can_be_updated(self):
        """测试node_id可以被更新"""
        node = ExecutionNode(node_id="original_id")

        # 直接设置node_id（测试属性可变性）
        original_id = node.node_id
        node.node_id = "updated_id"

        assert node.node_id == "updated_id"
        assert node.node_id != original_id
        print(f"✅ node_id可以更新")


@pytest.mark.unit
class TestExecutionNodeStatus:
    """测试 ExecutionNode 状态管理"""

    def test_status_empty(self):
        """测试空ExecutionNode的状态"""
        node = ExecutionNode(node_id="test_node")
        status = node.get_status()

        assert status["portfolio_count"] == 0
        assert status["is_running"] == False
        assert len(status["portfolios"]) == 0
        print(f"✅ 空ExecutionNode状态正确")

    def test_status_after_start(self):
        """测试启动后的状态"""
        node = ExecutionNode(node_id="test_node")
        node.start()
        status = node.get_status()

        assert status["is_running"] == True
        print(f"✅ 启动后状态正确")

        # 清理
        node.stop()

    def test_status_after_stop(self):
        """测试停止后的状态"""
        node = ExecutionNode(node_id="test_node")
        node.start()
        node.stop()
        status = node.get_status()

        assert status["is_running"] == False
        print(f"✅ 停止后状态正确")

    def test_status_contains_node_info(self):
        """测试状态包含节点信息"""
        node = ExecutionNode(node_id="test_node_info")
        status = node.get_status()

        assert "node_id" in status
        assert status["node_id"] == "test_node_info"
        assert "portfolio_count" in status
        print(f"✅ 状态包含节点信息")


@pytest.mark.unit
class TestExecutionNodeLifecycle:
    """测试 ExecutionNode 生命周期"""

    def test_start_sets_is_running_flag(self):
        """测试 start() 设置运行标志"""
        node = ExecutionNode(node_id="test_node")
        node.start()

        assert node.is_running == True
        print(f"✅ start() 正确设置 is_running=True")

        # 清理
        node.stop()

    def test_stop_sets_is_running_false(self):
        """测试 stop() 清除运行标志"""
        node = ExecutionNode(node_id="test_node")
        node.start()
        node.stop()

        assert node.is_running == False
        print(f"✅ stop() 正确设置 is_running=False")

    def test_start_stop_cycle(self):
        """测试启动-停止循环"""
        node = ExecutionNode(node_id="test_node")

        # 第一次启动
        node.start()
        assert node.is_running == True

        # 停止
        node.stop()
        assert node.is_running == False

        # 第二次启动
        node.start()
        assert node.is_running == True

        # 再次停止
        node.stop()
        assert node.is_running == False

        print(f"✅ 可以多次启动-停止")


@pytest.mark.unit
class TestExecutionNodeInterestMap:
    """测试 ExecutionNode InterestMap 功能"""

    def test_interest_map_initialization(self):
        """测试InterestMap初始化"""
        node = ExecutionNode(node_id="test_node")

        assert hasattr(node, 'interest_map')
        assert len(node.interest_map) == 0
        print(f"✅ InterestMap初始化正确")

    def test_interest_map_can_add_subscription(self):
        """测试可以向InterestMap添加订阅"""
        node = ExecutionNode(node_id="test_node")

        # InterestMap是公开属性，可以直接操作
        from ginkgo.workers.execution_node.interest_map import InterestMap
        node.interest_map = InterestMap()

        # 使用正确的API添加订阅
        node.interest_map.add_portfolio("portfolio_1", ["000001.SZ"])

        assert "000001.SZ" in node.interest_map.get_all_subscriptions("portfolio_1")
        print(f"✅ 可以向InterestMap添加订阅")


@pytest.mark.unit
class TestExecutionNodePortfoliosDict:
    """测试 ExecutionNode portfolios 字典"""

    def test_portfolios_dict_initially_empty(self):
        """测试portfolios字典初始为空"""
        node = ExecutionNode(node_id="test_node")

        assert hasattr(node, 'portfolios')
        assert len(node.portfolios) == 0
        print(f"✅ portfolios字典初始为空")

    def test_portfolio_instances_dict_initially_empty(self):
        """测试_portfolio_instances字典初始为空"""
        node = ExecutionNode(node_id="test_node")

        assert hasattr(node, '_portfolio_instances')
        assert len(node._portfolio_instances) == 0
        print(f"✅ _portfolio_instances字典初始为空")


@pytest.mark.unit
class TestExecutionNodeGetStatus:
    """测试 ExecutionNode.get_status() 方法"""

    def test_get_status_returns_dict(self):
        """测试 get_status() 返回字典"""
        node = ExecutionNode(node_id="test_node")

        status = node.get_status()

        assert isinstance(status, dict)
        print(f"✅ get_status() 返回字典")

    def test_get_status_includes_all_fields(self):
        """测试 get_status() 包含所有必要字段"""
        node = ExecutionNode(node_id="test_node")

        status = node.get_status()

        # 验证必要字段存在
        required_fields = ["node_id", "is_running", "portfolio_count", "portfolios"]
        for field in required_fields:
            assert field in status, f"Missing field: {field}"

        print(f"✅ get_status() 包含所有必要字段")

    def test_get_status_updates_after_lifecycle_changes(self):
        """测试 get_status() 在生命周期变化后更新"""
        node = ExecutionNode(node_id="test_node")

        # 初始状态
        status_initial = node.get_status()
        assert status_initial["is_running"] == False

        # 启动后
        node.start()
        status_running = node.get_status()
        assert status_running["is_running"] == True

        # 停止后
        node.stop()
        status_stopped = node.get_status()
        assert status_stopped["is_running"] == False

        print(f"✅ get_status() 在生命周期变化后正确更新")
