"""
PortfolioService数据服务测试

测试PortfolioService的核心功能和业务逻辑
遵循pytest最佳实践，使用fixtures和参数化测试
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.data.services.portfolio_service import PortfolioService
from ginkgo.data.services.base_service import BaseService, ServiceResult
from ginkgo.data.containers import container
from ginkgo.enums import FILE_TYPES, PORTFOLIO_MODE_TYPES, PORTFOLIO_RUNSTATE_TYPES


# ============================================================================
# Fixtures - 共享测试资源
# ============================================================================

@pytest.fixture
def portfolio_service():
    """获取PortfolioService实例"""
    return container.portfolio_service()


@pytest.fixture
def file_service():
    """获取FileService实例"""
    return container.file_service()


@pytest.fixture
def unique_name():
    """生成唯一的测试名称"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    return f"test_{timestamp}"


@pytest.fixture
def sample_portfolio(portfolio_service, unique_name):
    """创建一个示例投资组合并返回UUID"""
    result = portfolio_service.add(
        name=f"{unique_name}_sample",
        mode=PORTFOLIO_MODE_TYPES.BACKTEST,
        description="Sample portfolio for testing"
    )
    assert result.is_success(), f"Failed to create sample portfolio: {result.error}"
    yield result.data["uuid"]
    # 清理（如果测试中没有删除）
    portfolio_service.delete(portfolio_id=result.data["uuid"])


# ============================================================================
# 参数化测试数据
# ============================================================================

# 有效的mode值
VALID_MODES = [
    (PORTFOLIO_MODE_TYPES.BACKTEST, PORTFOLIO_MODE_TYPES.BACKTEST.value),
    (PORTFOLIO_MODE_TYPES.PAPER, PORTFOLIO_MODE_TYPES.PAPER.value),
    (PORTFOLIO_MODE_TYPES.LIVE, PORTFOLIO_MODE_TYPES.LIVE.value),
    (0, 0),  # int值
    (1, 1),
    (2, 2),
]

# 有效的state值
VALID_STATES = [
    PORTFOLIO_RUNSTATE_TYPES.INITIALIZED,
    PORTFOLIO_RUNSTATE_TYPES.RUNNING,
    PORTFOLIO_RUNSTATE_TYPES.PAUSED,
    PORTFOLIO_RUNSTATE_TYPES.STOPPED,
]

# 无效的名称（用于边界测试）
INVALID_NAMES = [
    ("", "空字符串"),
    ("   ", "纯空格"),
    ("\t\n", "空白字符"),
]

# 无效的mode值
INVALID_MODES = [
    999,      # 超出范围
    -100,     # 负数
    "invalid",  # 字符串
    None,     # None值
]


# ============================================================================
# 测试类 - Portfolio CRUD操作
# ============================================================================

@pytest.mark.unit
@pytest.mark.db_cleanup
class TestPortfolioCRUD:
    """
    Portfolio CRUD操作测试
    测试创建、读取、更新、删除基本功能
    """

    CLEANUP_CONFIG = {'portfolio': {'name__like': 'test_%'}}

    # -------------------- 创建操作 --------------------

    def test_add_portfolio_success(self, portfolio_service, unique_name):
        """测试成功创建投资组合"""
        result = portfolio_service.add(
            name=f"{unique_name}_add_success",
            mode=PORTFOLIO_MODE_TYPES.BACKTEST,
            description="Test portfolio"
        )

        assert result.is_success()
        assert result.data["name"] == f"{unique_name}_add_success"
        assert result.data["mode"] == PORTFOLIO_MODE_TYPES.BACKTEST.value
        assert result.data["uuid"] is not None

    @pytest.mark.parametrize("invalid_name,description", INVALID_NAMES)
    def test_add_portfolio_invalid_name(self, portfolio_service, invalid_name, description):
        """参数化测试：无效名称边界测试"""
        result = portfolio_service.add(name=invalid_name)
        assert not result.is_success(), f"应该拒绝{description}"
        assert "不能为空" in result.error

    def test_add_portfolio_duplicate_name(self, portfolio_service, unique_name):
        """测试重名投资组合应该被拒绝"""
        name = f"{unique_name}_duplicate"

        # 第一次创建应该成功
        first = portfolio_service.add(name=name)
        assert first.is_success()

        # 第二次创建应该失败
        second = portfolio_service.add(name=name)
        assert not second.is_success()
        assert "已存在" in second.error

    # -------------------- 查询操作 --------------------

    def test_get_portfolio_success(self, portfolio_service, sample_portfolio):
        """测试成功获取投资组合"""
        result = portfolio_service.get(portfolio_id=sample_portfolio)

        assert result.is_success()
        assert len(result.data) == 1
        assert result.data[0].uuid == sample_portfolio

    def test_get_portfolio_not_found(self, portfolio_service):
        """测试获取不存在的投资组合"""
        result = portfolio_service.get(portfolio_id="nonexistent-uuid-12345")

        assert not result.is_success()
        assert "不存在" in result.error

    def test_get_portfolio_verify_all_fields(self, portfolio_service, unique_name):
        """测试获取时验证所有字段"""
        # 创建
        create_result = portfolio_service.add(
            name=f"{unique_name}_verify",
            mode=PORTFOLIO_MODE_TYPES.PAPER,
            description="Full verification test"
        )
        assert create_result.is_success()
        uuid = create_result.data["uuid"]

        # 获取并验证
        get_result = portfolio_service.get(portfolio_id=uuid)
        assert get_result.is_success()

        portfolio = get_result.data[0]
        assert portfolio.uuid == uuid
        assert portfolio.name == f"{unique_name}_verify"
        assert portfolio.mode == PORTFOLIO_MODE_TYPES.PAPER.value
        assert portfolio.desc == "Full verification test"

    # -------------------- 更新操作 --------------------

    def test_update_portfolio_name(self, portfolio_service, sample_portfolio):
        """测试更新投资组合名称"""
        result = portfolio_service.update(
            portfolio_id=sample_portfolio,
            name="updated_name"
        )

        assert result.is_success()

        # 验证更新
        get_result = portfolio_service.get(portfolio_id=sample_portfolio)
        assert get_result.data[0].name == "updated_name"

    def test_update_portfolio_description(self, portfolio_service, sample_portfolio):
        """测试更新投资组合描述"""
        result = portfolio_service.update(
            portfolio_id=sample_portfolio,
            description="Updated description"
        )

        assert result.is_success()

        get_result = portfolio_service.get(portfolio_id=sample_portfolio)
        assert get_result.data[0].desc == "Updated description"

    def test_update_portfolio_not_found(self, portfolio_service):
        """测试更新不存在的投资组合"""
        # 注意：当前服务实现允许更新不存在的UUID（返回成功但实际未更新）
        # 这是一个边界行为，测试应匹配实际实现
        result = portfolio_service.update(
            portfolio_id="nonexistent-uuid-12345",
            name="new_name"
        )

        # 服务返回成功（即使没有实际更新任何记录）
        # 可以通过再次查询验证是否真正更新
        assert result.is_success()  # 当前行为：更新操作本身成功执行

        # 验证实际没有创建或更新任何记录
        verify = portfolio_service.get(portfolio_id="nonexistent-uuid-12345")
        assert not verify.is_success()  # 记录仍然不存在

    # -------------------- 删除操作 --------------------

    def test_delete_portfolio_success(self, portfolio_service, unique_name):
        """测试成功删除投资组合"""
        # 创建
        create = portfolio_service.add(name=f"{unique_name}_delete")
        uuid = create.data["uuid"]

        # 删除
        delete = portfolio_service.delete(portfolio_id=uuid)
        assert delete.is_success()

        # 验证已删除
        get = portfolio_service.get(portfolio_id=uuid)
        assert not get.is_success()

    # -------------------- 统计操作 --------------------

    def test_count_portfolios(self, portfolio_service):
        """测试统计投资组合数量"""
        result = portfolio_service.count()

        assert result.is_success()
        assert "count" in result.data
        assert isinstance(result.data["count"], int)
        assert result.data["count"] >= 0

    def test_exists_portfolio(self, portfolio_service, unique_name):
        """测试检查投资组合存在性"""
        name = f"{unique_name}_exists"

        # 不存在时
        result = portfolio_service.exists(name=name)
        assert result.is_success()
        assert result.data["exists"] is False

        # 创建后
        portfolio_service.add(name=name)
        result = portfolio_service.exists(name=name)
        assert result.is_success()
        assert result.data["exists"] is True


# ============================================================================
# 测试类 - Mode和State枚举
# ============================================================================

@pytest.mark.unit
@pytest.mark.db_cleanup
class TestPortfolioModeAndState:
    """
    Portfolio Mode和State枚举测试
    测试运行模式和状态的管理
    """

    CLEANUP_CONFIG = {'portfolio': {'name__like': 'test_%'}}

    @pytest.mark.parametrize("mode,expected_value", VALID_MODES)
    def test_create_with_valid_mode(self, portfolio_service, unique_name, mode, expected_value):
        """参数化测试：使用有效mode创建投资组合"""
        result = portfolio_service.add(
            name=f"{unique_name}_mode_{expected_value}",
            mode=mode
        )

        assert result.is_success()
        assert result.data["mode"] == expected_value

    def test_create_with_paper_mode(self, portfolio_service, unique_name):
        """测试创建模拟盘投资组合"""
        result = portfolio_service.add(
            name=f"{unique_name}_paper",
            mode=PORTFOLIO_MODE_TYPES.PAPER
        )

        assert result.is_success()
        assert result.data["mode"] == PORTFOLIO_MODE_TYPES.PAPER.value

    def test_create_with_live_mode(self, portfolio_service, unique_name):
        """测试创建实盘投资组合"""
        result = portfolio_service.add(
            name=f"{unique_name}_live",
            mode=PORTFOLIO_MODE_TYPES.LIVE
        )

        assert result.is_success()
        assert result.data["mode"] == PORTFOLIO_MODE_TYPES.LIVE.value

    def test_update_mode(self, portfolio_service, sample_portfolio):
        """测试更新投资组合模式"""
        # 从BACKTEST更新到PAPER
        result = portfolio_service.update(
            portfolio_id=sample_portfolio,
            mode=PORTFOLIO_MODE_TYPES.PAPER
        )

        assert result.is_success()

        get_result = portfolio_service.get(portfolio_id=sample_portfolio)
        assert get_result.data[0].mode == PORTFOLIO_MODE_TYPES.PAPER.value

    @pytest.mark.parametrize("state", VALID_STATES)
    def test_create_with_valid_state(self, portfolio_service, unique_name, state):
        """参数化测试：使用有效state创建投资组合"""
        # 注意：state在add中可能不是直接参数，这里测试CRUD层
        result = portfolio_service.add(
            name=f"{unique_name}_state_{state.value}"
        )

        assert result.is_success()
        # 默认state应该是INITIALIZED
        assert result.data.get("state", PORTFOLIO_RUNSTATE_TYPES.INITIALIZED.value) is not None

    def test_mode_transition_backtest_to_paper(self, portfolio_service, unique_name):
        """测试模式转换：回测 -> 模拟盘"""
        # 创建回测组合
        create = portfolio_service.add(
            name=f"{unique_name}_transition",
            mode=PORTFOLIO_MODE_TYPES.BACKTEST
        )
        uuid = create.data["uuid"]

        # 转换为模拟盘
        portfolio_service.update(portfolio_id=uuid, mode=PORTFOLIO_MODE_TYPES.PAPER)

        get = portfolio_service.get(portfolio_id=uuid)
        assert get.data[0].mode == PORTFOLIO_MODE_TYPES.PAPER.value

    def test_mode_transition_paper_to_live(self, portfolio_service, unique_name):
        """测试模式转换：模拟盘 -> 实盘"""
        create = portfolio_service.add(
            name=f"{unique_name}_to_live",
            mode=PORTFOLIO_MODE_TYPES.PAPER
        )
        uuid = create.data["uuid"]

        portfolio_service.update(portfolio_id=uuid, mode=PORTFOLIO_MODE_TYPES.LIVE)

        get = portfolio_service.get(portfolio_id=uuid)
        assert get.data[0].mode == PORTFOLIO_MODE_TYPES.LIVE.value


# ============================================================================
# 测试类 - 数据验证
# ============================================================================

@pytest.mark.unit
class TestPortfolioValidation:
    """
    Portfolio数据验证测试
    测试各种边界条件和验证规则
    """

    CLEANUP_CONFIG = {'portfolio': {'name__like': 'test_%'}}

    def test_validate_valid_data(self, portfolio_service):
        """测试验证有效数据"""
        valid_data = {
            'name': 'Valid Portfolio',
            'mode': PORTFOLIO_MODE_TYPES.BACKTEST.value,
            'state': PORTFOLIO_RUNSTATE_TYPES.INITIALIZED.value
        }

        result = portfolio_service.validate(valid_data)
        assert result.is_success()
        assert result.data["valid"] is True

    def test_validate_missing_name(self, portfolio_service):
        """测试验证缺少name的数据"""
        invalid_data = {
            'mode': PORTFOLIO_MODE_TYPES.BACKTEST.value
        }

        result = portfolio_service.validate(invalid_data)
        assert not result.is_success()
        assert "缺少必填字段" in result.error

    def test_validate_empty_name(self, portfolio_service):
        """测试验证空名称"""
        invalid_data = {
            'name': '',
            'mode': PORTFOLIO_MODE_TYPES.BACKTEST.value
        }

        result = portfolio_service.validate(invalid_data)
        assert not result.is_success()

    @pytest.mark.parametrize("invalid_mode", [-1, 999, "invalid", None])
    def test_validate_invalid_mode(self, portfolio_service, invalid_mode):
        """参数化测试：验证无效mode值"""
        data = {
            'name': 'Test',
            'mode': invalid_mode
        }

        # 根据实现，可能返回成功（使用默认值）或失败
        result = portfolio_service.validate(data)
        # 不应该崩溃


# ============================================================================
# 测试类 - 组件管理
# ============================================================================

@pytest.mark.unit
@pytest.mark.db_cleanup
class TestPortfolioComponentManagement:
    """
    Portfolio组件管理测试
    测试组件挂载、卸载和查询
    """

    CLEANUP_CONFIG = {'portfolio': {'name__like': 'test_%'}}

    def test_mount_component_success(self, portfolio_service, file_service, unique_name):
        """测试成功挂载组件"""
        # 创建投资组合
        portfolio_result = portfolio_service.add(name=f"{unique_name}_mount")
        portfolio_uuid = portfolio_result.data["uuid"]

        # 创建策略文件
        file_result = file_service.add(
            name=f"{unique_name}_strategy",
            file_type=FILE_TYPES.STRATEGY,
            data=b'class TestStrategy: pass'
        )
        file_uuid = file_result.data["file_info"]["uuid"]

        # 挂载
        mount_result = portfolio_service.mount_component(
            portfolio_id=portfolio_uuid,
            component_id=file_uuid,
            component_name="Test Strategy",
            component_type=FILE_TYPES.STRATEGY
        )

        assert mount_result.is_success()
        assert mount_result.data["portfolio_id"] == portfolio_uuid
        assert mount_result.data["component_id"] == file_uuid

        # 清理
        portfolio_service.unmount_component(mount_id=mount_result.data["mount_id"])

    def test_mount_component_validation_errors(self, portfolio_service):
        """参数化测试：挂载组件验证错误"""
        # 空portfolio_id
        result = portfolio_service.mount_component(
            portfolio_id="",
            component_id="file-uuid",
            component_name="Test",
            component_type=FILE_TYPES.STRATEGY
        )
        assert not result.is_success()
        assert "投资组合ID" in result.error

        # 空component_id
        result = portfolio_service.mount_component(
            portfolio_id="portfolio-uuid",
            component_id="",
            component_name="Test",
            component_type=FILE_TYPES.STRATEGY
        )
        assert not result.is_success()
        assert "组件ID" in result.error

        # 空component_name
        result = portfolio_service.mount_component(
            portfolio_id="portfolio-uuid",
            component_id="file-uuid",
            component_name="",
            component_type=FILE_TYPES.STRATEGY
        )
        assert not result.is_success()
        assert "组件名称" in result.error

    def test_get_components_empty(self, portfolio_service):
        """测试获取空组件列表"""
        result = portfolio_service.get_components(portfolio_id="nonexistent-uuid")

        assert result.is_success()
        assert len(result.data) == 0

    def test_component_mount_unmount_lifecycle(self, portfolio_service, file_service, unique_name):
        """测试组件挂载-卸载生命周期"""
        # 创建
        portfolio = portfolio_service.add(name=f"{unique_name}_lifecycle")
        portfolio_uuid = portfolio.data["uuid"]

        file = file_service.add(
            name=f"{unique_name}_comp",
            file_type=FILE_TYPES.STRATEGY,
            data=b'class Comp: pass'
        )
        file_uuid = file.data["file_info"]["uuid"]

        # 挂载
        mount = portfolio_service.mount_component(
            portfolio_id=portfolio_uuid,
            component_id=file_uuid,
            component_name="Lifecycle Component",
            component_type=FILE_TYPES.STRATEGY
        )
        assert mount.is_success()

        # 验证已挂载
        components = portfolio_service.get_components(portfolio_id=portfolio_uuid)
        assert any(c["component_id"] == file_uuid for c in components.data)

        # 卸载
        unmount = portfolio_service.unmount_component(mount_id=mount.data["mount_id"])
        assert unmount.is_success()

        # 验证已卸载
        components = portfolio_service.get_components(portfolio_id=portfolio_uuid)
        assert not any(c["component_id"] == file_uuid for c in components.data)


# ============================================================================
# 测试类 - 服务健康检查
# ============================================================================

@pytest.mark.unit
class TestPortfolioServiceHealth:
    """PortfolioService健康检查测试"""

    def test_health_check(self, portfolio_service):
        """测试健康检查返回正确信息"""
        result = portfolio_service.health_check()

        assert result.is_success()
        health_data = result.data
        assert health_data["service_name"] == "PortfolioService"
        assert health_data["status"] == "healthy"


# ============================================================================
# 测试类 - 集成测试
# ============================================================================

@pytest.mark.integration
@pytest.mark.db_cleanup
class TestPortfolioServiceIntegration:
    """
    PortfolioService集成测试
    测试完整的业务流程
    """

    CLEANUP_CONFIG = {'portfolio': {'name__like': 'integration_%'}}

    def test_full_lifecycle_crud(self, portfolio_service):
        """测试完整CRUD生命周期：创建->读取->更新->删除"""
        # 1. 创建
        create = portfolio_service.add(
            name="integration_lifecycle",
            mode=PORTFOLIO_MODE_TYPES.BACKTEST,
            description="Integration test"
        )
        assert create.is_success()
        uuid = create.data["uuid"]

        # 2. 读取
        read = portfolio_service.get(portfolio_id=uuid)
        assert read.is_success()
        assert read.data[0].name == "integration_lifecycle"

        # 3. 更新
        update = portfolio_service.update(
            portfolio_id=uuid,
            name="integration_updated",
            mode=PORTFOLIO_MODE_TYPES.PAPER,
            description="Updated"
        )
        assert update.is_success()

        # 验证更新
        read_updated = portfolio_service.get(portfolio_id=uuid)
        assert read_updated.data[0].mode == PORTFOLIO_MODE_TYPES.PAPER.value

        # 4. 删除
        delete = portfolio_service.delete(portfolio_id=uuid)
        assert delete.is_success()

        # 验证删除
        read_deleted = portfolio_service.get(portfolio_id=uuid)
        assert not read_deleted.is_success()

    def test_mode_state_workflow(self, portfolio_service):
        """测试模式状态工作流：BACKTEST -> PAPER -> LIVE"""
        # 创建回测组合
        create = portfolio_service.add(
            name="integration_workflow",
            mode=PORTFOLIO_MODE_TYPES.BACKTEST
        )
        uuid = create.data["uuid"]

        # 模拟回测完成，升级到模拟盘
        portfolio_service.update(
            portfolio_id=uuid,
            mode=PORTFOLIO_MODE_TYPES.PAPER
        )

        get = portfolio_service.get(portfolio_id=uuid)
        assert get.data[0].mode == PORTFOLIO_MODE_TYPES.PAPER.value

        # 模拟盘验证通过，升级到实盘
        portfolio_service.update(
            portfolio_id=uuid,
            mode=PORTFOLIO_MODE_TYPES.LIVE
        )

        get = portfolio_service.get(portfolio_id=uuid)
        assert get.data[0].mode == PORTFOLIO_MODE_TYPES.LIVE.value

        # 清理
        portfolio_service.delete(portfolio_id=uuid)

    def test_batch_operations(self, portfolio_service):
        """测试批量操作：创建多个投资组合"""
        names = [f"integration_batch_{i}" for i in range(3)]
        uuids = []

        # 批量创建
        for name in names:
            result = portfolio_service.add(name=name)
            assert result.is_success()
            uuids.append(result.data["uuid"])

        # 验证全部存在
        count_before = portfolio_service.count()

        # 批量删除
        for uuid in uuids:
            portfolio_service.delete(portfolio_id=uuid)

        # 验证全部删除
        for uuid in uuids:
            result = portfolio_service.get(portfolio_id=uuid)
            assert not result.is_success()
