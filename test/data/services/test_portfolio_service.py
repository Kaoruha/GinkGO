"""
PortfolioService数据服务测试

测试PortfolioService的核心功能和业务逻辑
遵循其他服务的测试模式，使用真实实例而非Mock
"""
import pytest
import sys
import os
from pathlib import Path
from datetime import datetime

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.data.services.portfolio_service import PortfolioService
from ginkgo.data.services.base_service import BaseService, ServiceResult
from ginkgo.data.containers import container
from ginkgo.enums import FILE_TYPES


@pytest.mark.unit
@pytest.mark.db_cleanup
class TestPortfolioServiceOperations:
    """
    PortfolioService 功能测试
    测试投资组合管理的核心操作和业务逻辑
    """

    # 自动清理配置：清理所有测试创建的投资组合
    CLEANUP_CONFIG = {
        'portfolio': {'name__like': 'test_%'}
    }

    def test_add_portfolio_success(self):
        """
        测试成功添加投资组合 - 验证实际数据库操作

        评审问题：
        - 直接数据库操作：第58行使用_crud_repo.find()破坏封装，第69行使用_crud_repo.remove()破坏封装
        - 清理逻辑问题：第68-71行使用try-except可能隐藏清理失败
        - 硬编码日期：回测日期硬编码在测试中，缺少日期工厂模式
        """
        portfolio_service = container.portfolio_service()

        # 执行添加投资组合操作
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        result = portfolio_service.add(
            name=f"test_portfolio_add_success_{timestamp}",
            backtest_start_date="2023-01-01",
            backtest_end_date="2023-12-31",
            is_live=False,
            description="Test portfolio for add operation"
        )

        # 验证操作结果
        assert result.is_success(), f"Portfolio creation failed: {result.message}"
        portfolio_info = result.data
        expected_name = f"test_portfolio_add_success_{timestamp}"
        assert portfolio_info["name"] == expected_name
        assert portfolio_info["is_live"] == False
        assert portfolio_info["desc"] == "Test portfolio for add operation"

        # 验证投资组合记录已创建
        portfolio_uuid = portfolio_info["uuid"]
        assert portfolio_uuid is not None
        assert len(portfolio_uuid) > 0

        # 验证投资组合确实被创建 - 通过服务接口查询
        get_result = portfolio_service.get(portfolio_id=portfolio_uuid)
        assert get_result.is_success(), f"Failed to retrieve created portfolio: {get_result.error}"
        retrieved_portfolios = get_result.data
        assert len(retrieved_portfolios) == 1, "Should find exactly one portfolio"

        retrieved_portfolio = retrieved_portfolios[0]
        assert retrieved_portfolio.uuid == portfolio_uuid, "UUID mismatch between ServiceResult and retrieved data"
        assert retrieved_portfolio.name == expected_name, "Name mismatch between ServiceResult and retrieved data"
        assert retrieved_portfolio.is_live == False, "Live status mismatch between ServiceResult and retrieved data"

    def test_add_portfolio_validation_errors(self):
        """
        测试投资组合添加的验证逻辑

        评审问题：
        - 缺少边界测试：没有测试开始日期晚于结束日期、过长名称、None值、特殊字符等边界情况
        - 测试不完整：第110行无效日期格式测试只验证失败状态，没有验证具体错误消息
        - 硬编码名称：测试中使用重复的"test_portfolio"名称，可能有潜在冲突风险
        """
        portfolio_service = container.portfolio_service()

        # 测试空投资组合名称
        result = portfolio_service.add(
            name="",
            backtest_start_date="2023-01-01",
            backtest_end_date="2023-12-31"
        )
        assert not result.is_success()
        assert "投资组合名称不能为空" in result.error

        # 测试空开始日期
        result = portfolio_service.add(
            name="test_portfolio",
            backtest_start_date="",
            backtest_end_date="2023-12-31"
        )
        assert not result.is_success()
        assert "回测开始和结束日期是必需的" in result.error

        # 测试空结束日期
        result = portfolio_service.add(
            name="test_portfolio",
            backtest_start_date="2023-01-01",
            backtest_end_date=""
        )
        assert not result.is_success()
        assert "回测开始和结束日期是必需的" in result.error

        # 测试无效日期格式
        result = portfolio_service.add(
            name="test_portfolio",
            backtest_start_date="invalid-date",
            backtest_end_date="2023-12-31"
        )
        assert not result.is_success()

    def test_add_portfolio_duplicate_name(self):
        """测试重名投资组合的处理"""
        portfolio_service = container.portfolio_service()

        # 首先创建一个投资组合
        first_result = portfolio_service.add(
            name="duplicate_test_portfolio",
            backtest_start_date="2023-01-01",
            backtest_end_date="2023-12-31"
        )

        assert first_result.is_success(), "First portfolio creation failed"
        portfolio_uuid = first_result.data["uuid"]

        # 尝试创建同名的投资组合
        second_result = portfolio_service.add(
            name="duplicate_test_portfolio",
            backtest_start_date="2023-01-01",
            backtest_end_date="2023-12-31"
        )

        # 应该失败
        assert not second_result.is_success()
        assert "已存在" in second_result.error

    def test_get_portfolio_success(self):
        """
        测试成功获取投资组合

        评审问题：
        - 缺少错误处理：没有try-finally保护，如果获取失败可能导致测试数据残留
        - 直接数据库操作：第170行直接使用_crud_repo.remove()破坏封装
        - 清理逻辑问题：第169-172行使用try-except可能隐藏清理失败
        - 验证深度有限：只验证UUID和名称，没有验证日期范围、状态等重要属性
        """
        portfolio_service = container.portfolio_service()

        # 先创建一个投资组合
        create_result = portfolio_service.add(
            name="test_portfolio_get",
            backtest_start_date="2023-01-01",
            backtest_end_date="2023-12-31"
        )

        assert create_result.is_success()
        portfolio_uuid = create_result.data["uuid"]

        # 获取投资组合
        get_result = portfolio_service.get(portfolio_id=portfolio_uuid)

        # 验证操作结果
        assert get_result.is_success(), f"Portfolio retrieval failed: {get_result.message}"
        portfolios = get_result.data
        assert len(portfolios) == 1
        retrieved_portfolio = portfolios[0]
        assert retrieved_portfolio.uuid == portfolio_uuid
        assert retrieved_portfolio.name == "test_portfolio_get"

    def test_get_portfolio_not_found(self):
        """测试获取不存在的投资组合"""
        portfolio_service = container.portfolio_service()

        # 使用不存在的UUID
        result = portfolio_service.get(portfolio_id="nonexistent-portfolio-uuid")

        # 应该失败
        assert not result.is_success()
        assert "投资组合不存在" in result.error

    def test_update_portfolio_success(self):
        """测试成功更新投资组合"""
        portfolio_service = container.portfolio_service()

        # 先创建一个投资组合
        create_result = portfolio_service.add(
            name="test_portfolio_update_original",
            backtest_start_date="2023-01-01",
            backtest_end_date="2023-12-31"
        )

        assert create_result.is_success()
        portfolio_uuid = create_result.data["uuid"]

        # 更新投资组合
        update_result = portfolio_service.update(
            portfolio_id=portfolio_uuid,
            name="test_portfolio_updated",
            description="Updated description"
        )

        # 验证更新结果
        assert update_result.is_success(), f"Portfolio update failed: {update_result.error}"

        # 验证更新后的数据
        get_result = portfolio_service.get(portfolio_id=portfolio_uuid)
        assert get_result.is_success()
        updated_portfolio = get_result.data[0]
        assert updated_portfolio.name == "test_portfolio_updated"
        assert updated_portfolio.desc == "Updated description"

    def test_delete_portfolio_success(self):
        """测试成功删除投资组合"""
        portfolio_service = container.portfolio_service()

        # 先创建一个投资组合
        create_result = portfolio_service.add(
            name="test_portfolio_delete",
            backtest_start_date="2023-01-01",
            backtest_end_date="2023-12-31"
        )

        assert create_result.is_success()
        portfolio_uuid = create_result.data["uuid"]

        # 删除投资组合
        delete_result = portfolio_service.delete(portfolio_id=portfolio_uuid)

        # 验证删除结果
        assert delete_result.is_success(), f"Portfolio deletion failed: {delete_result.error}"

        # 验证投资组合已被软删除
        get_result = portfolio_service.get(portfolio_id=portfolio_uuid)
        assert not get_result.is_success()  # 应该找不到被删除的投资组合

    def test_count_portfolios(self):
        """测试统计投资组合数量"""
        portfolio_service = container.portfolio_service()

        # 获取当前统计
        result = portfolio_service.count()

        # 验证统计结果
        assert result.is_success(), f"Portfolio count failed: {result.message}"
        assert "count" in result.data
        assert isinstance(result.data["count"], int)
        assert result.data["count"] >= 0

    def test_exists_portfolio(self):
        """测试检查投资组合存在性"""
        portfolio_service = container.portfolio_service()

        # 测试不存在的投资组合
        result = portfolio_service.exists(name="definitely_nonexistent_portfolio_name_12345")
        assert result.is_success()
        assert result.data["exists"] == False

        # 创建一个投资组合
        create_result = portfolio_service.add(
            name="test_exists_portfolio",
            backtest_start_date="2023-01-01",
            backtest_end_date="2023-12-31"
        )

        if create_result.is_success():
            # 测试存在的投资组合
            result = portfolio_service.exists(name="test_exists_portfolio")
            assert result.is_success()
            assert result.data["exists"] == True

    def test_mount_component_success(self):
        """
        测试成功挂载组件

        评审改进：
        - 移除pytest.skip()机制，使用真实错误处理
        - 移除直接数据库操作，使用服务接口
        - 简化测试逻辑，专注核心功能验证
        """
        portfolio_service = container.portfolio_service()
        file_service = container.file_service()

        # 创建投资组合
        portfolio_result = portfolio_service.add(
            name="test_mount_portfolio",
            backtest_start_date="2023-01-01",
            backtest_end_date="2023-12-31"
        )

        assert portfolio_result.is_success(), f"Failed to create test portfolio: {portfolio_result.error}"
        portfolio_uuid = portfolio_result.data["uuid"]

        # 创建策略文件
        strategy_content = b'''
class TestMountStrategy:
    def __init__(self):
        pass

    def generate_signal(self, data):
        return "BUY"
'''

        file_result = file_service.add(
            name="test_mount_strategy",
            file_type=FILE_TYPES.STRATEGY,
            data=strategy_content
        )

        assert file_result.is_success(), f"Failed to create test strategy file: {file_result.error}"
        file_uuid = file_result.data["file_info"]["uuid"]

        # 挂载组件
        mount_result = portfolio_service.mount_component(
            portfolio_id=portfolio_uuid,
            component_id=file_uuid,
            component_name="Test Mount Strategy",
            component_type=FILE_TYPES.STRATEGY
        )

        # 验证挂载结果
        assert mount_result.is_success(), f"Component mount failed: {mount_result.error}"
        mount_info = mount_result.data
        assert mount_info["portfolio_id"] == portfolio_uuid
        assert mount_info["component_id"] == file_uuid
        assert mount_info["component_name"] == "Test Mount Strategy"
        assert mount_info["component_type"] == "STRATEGY"

        # 验证组件已挂载
        components_result = portfolio_service.get_components(portfolio_id=portfolio_uuid)
        assert components_result.is_success()
        components = components_result.data
        assert len(components) >= 1

        # 找到挂载的组件
        mounted_component = None
        for component in components:
            if component["component_id"] == file_uuid:
                mounted_component = component
                break

        assert mounted_component is not None
        assert mounted_component["component_name"] == "Test Mount Strategy"

        # 卸载组件
        unmount_result = portfolio_service.unmount_component(mount_id=mount_info["mount_id"])
        assert unmount_result.is_success(), f"Component unmount failed: {unmount_result.error}"

        # 验证组件已卸载
        components_after_unmount = portfolio_service.get_components(portfolio_id=portfolio_uuid)
        assert components_after_unmount.is_success()
        unmounted_component = None
        for component in components_after_unmount.data:
            if component["component_id"] == file_uuid:
                unmounted_component = component
                break

        assert unmounted_component is None

    def test_mount_component_validation_errors(self):
        """测试组件挂载的验证逻辑"""
        portfolio_service = container.portfolio_service()

        # 测试空投资组合ID
        result = portfolio_service.mount_component(
            portfolio_id="",
            component_id="file-uuid",
            component_name="Test Component",
            component_type=FILE_TYPES.STRATEGY
        )
        assert not result.is_success()
        assert "投资组合ID不能为空" in result.error

        # 测试空组件ID
        result = portfolio_service.mount_component(
            portfolio_id="portfolio-uuid",
            component_id="",
            component_name="Test Component",
            component_type=FILE_TYPES.STRATEGY
        )
        assert not result.is_success()
        assert "组件ID不能为空" in result.error

        # 测试空组件名称
        result = portfolio_service.mount_component(
            portfolio_id="portfolio-uuid",
            component_id="file-uuid",
            component_name="",
            component_type=FILE_TYPES.STRATEGY
        )
        assert not result.is_success()
        assert "组件名称不能为空" in result.error

    def test_get_components_empty(self):
        """测试获取空投资组合的组件列表"""
        portfolio_service = container.portfolio_service()

        # 使用不存在的投资组合ID
        result = portfolio_service.get_components(portfolio_id="nonexistent-portfolio-uuid")

        # 验证结果
        assert result.is_success()
        assert len(result.data) == 0

    def test_health_check(self):
        """测试健康检查"""
        portfolio_service = container.portfolio_service()

        result = portfolio_service.health_check()

        # 验证健康检查结果
        assert result.is_success(), f"Health check failed: {result.message}"
        health_data = result.data
        assert "service_name" in health_data
        assert "status" in health_data
        assert health_data["service_name"] == "PortfolioService"
        assert health_data["status"] == "healthy"

    def test_validate_portfolio_data(self):
        """测试投资组合数据验证"""
        portfolio_service = container.portfolio_service()

        # 测试有效数据
        valid_data = {
            'name': 'Test Portfolio',
            'backtest_start_date': '2023-01-01',
            'backtest_end_date': '2023-12-31',
            'is_live': False
        }
        result = portfolio_service.validate(valid_data)
        assert result.is_success()
        assert result.data["valid"] == True

        # 测试无效数据（缺少必填字段）
        invalid_data = {
            'name': 'Test Portfolio',
            'backtest_start_date': '2023-01-01'
            # 缺少 backtest_end_date
        }
        result = portfolio_service.validate(invalid_data)
        assert not result.is_success()
        assert "缺少必填字段" in result.error

        # 测试无效日期格式
        invalid_date_data = {
            'name': 'Test Portfolio',
            'backtest_start_date': 'invalid-date',
            'backtest_end_date': '2023-12-31',
            'is_live': False
        }
        result = portfolio_service.validate(invalid_date_data)
        assert not result.is_success()


@pytest.mark.integration
@pytest.mark.db_cleanup
class TestPortfolioServiceIntegration:
    """
    PortfolioService 集成测试
    测试投资组合服务的完整工作流程
    """

    # 自动清理配置：清理所有测试创建的投资组合
    CLEANUP_CONFIG = {
        'portfolio': {'name__like': 'lifecycle_%'}
    }

    def test_portfolio_lifecycle_basic(self):
        """
        测试投资组合的基本生命周期：创建 -> 更新 -> 删除
        重构后简化测试逻辑，移除复杂组件挂载操作
        """
        portfolio_service = container.portfolio_service()

        # 1. 创建投资组合
        create_result = portfolio_service.add(
            name="lifecycle_test_portfolio",
            backtest_start_date="2023-01-01",
            backtest_end_date="2023-12-31",
            is_live=False,
            description="Portfolio for lifecycle testing"
        )
        assert create_result.is_success(), f"Portfolio creation failed: {create_result.error}"
        portfolio_uuid = create_result.data["uuid"]

        # 2. 更新投资组合
        update_result = portfolio_service.update(
            portfolio_id=portfolio_uuid,
            description="Updated lifecycle portfolio description"
        )
        assert update_result.is_success(), f"Portfolio update failed: {update_result.error}"

        # 3. 获取投资组合信息验证更新
        get_result = portfolio_service.get(portfolio_id=portfolio_uuid)
        assert get_result.is_success(), f"Portfolio retrieval failed: {get_result.error}"
        portfolio = get_result.data[0]
        assert portfolio.desc == "Updated lifecycle portfolio description"

        # 4. 删除投资组合
        delete_result = portfolio_service.delete(portfolio_id=portfolio_uuid)
        assert delete_result.is_success(), f"Portfolio deletion failed: {delete_result.error}"

        # 5. 验证投资组合已不存在
        get_after_delete = portfolio_service.get(portfolio_id=portfolio_uuid)
        assert not get_after_delete.is_success(), "Deleted portfolio should not be retrievable"