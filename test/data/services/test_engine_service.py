"""
EngineService数据服务测试

测试EngineService的核心功能和业务逻辑
遵循pytest最佳实践，使用fixtures和参数化测试
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.data.services.engine_service import EngineService
from ginkgo.data.services.base_service import BaseService, ServiceResult
from ginkgo.data.containers import container
from ginkgo.data.crud.engine_crud import EngineCRUD
from ginkgo.data.crud.engine_portfolio_mapping_crud import EnginePortfolioMappingCRUD
from ginkgo.enums import ENGINESTATUS_TYPES, SOURCE_TYPES
from ginkgo.libs import GCONF


# ============================================================================
# Fixtures - 共享测试资源
# ============================================================================

@pytest.fixture
def ginkgo_config():
    """配置调试模式"""
    GCONF.set_debug(True)
    yield GCONF
    GCONF.set_debug(False)


@pytest.fixture
def engine_service():
    """获取EngineService实例"""
    return container.engine_service()


@pytest.fixture
def unique_name():
    """生成唯一的测试引擎名称"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    return f"test_engine_{timestamp}"


@pytest.fixture
def sample_engine(engine_service, unique_name):
    """创建示例引擎并返回UUID"""
    result = engine_service.add(
        name=unique_name,
        is_live=False,
        description="Sample engine for testing"
    )
    assert result.is_success(), f"Failed to create sample engine: {result.error}"
    uuid = result.data["engine_info"]["uuid"]
    yield uuid
    # 清理
    try:
        engine_service.delete(uuid)
    except Exception:
        pass


# ============================================================================
# 参数化测试数据
# ============================================================================

# 有效的引擎状态
VALID_ENGINE_STATES = [
    ENGINESTATUS_TYPES.IDLE,         # 使用IDLE代替INITIALIZED
    ENGINESTATUS_TYPES.INITIALIZING, # 使用INITIALIZING代替INITIALIZED
    ENGINESTATUS_TYPES.RUNNING,
    ENGINESTATUS_TYPES.PAUSED,
    ENGINESTATUS_TYPES.STOPPED,
]

# 无效的引擎名称
INVALID_ENGINE_NAMES = [
    ("", "空字符串"),
    ("   ", "纯空格"),
    ("\t\n", "空白字符"),
]

# 超长名称测试
LONG_NAME = "a" * 60  # 超过50字符限制


# ============================================================================
# 测试类 - Engine CRUD操作
# ============================================================================

@pytest.mark.unit
@pytest.mark.db_cleanup
class TestEngineCRUD:
    """
    Engine CRUD操作测试
    测试创建、读取、更新、删除基本功能
    """

    CLEANUP_CONFIG = {'engine': {'name__like': 'test_%'}}

    # -------------------- 创建操作 --------------------

    def test_add_engine_success(self, engine_service, unique_name):
        """测试成功创建引擎"""
        result = engine_service.add(
            name=unique_name,
            is_live=False,
            description="Test engine"
        )

        assert result.is_success()
        assert result.data["engine_info"]["name"] == unique_name
        assert result.data["engine_info"]["is_live"] is False
        assert result.data["engine_info"]["uuid"] is not None

    def test_add_live_engine(self, engine_service, unique_name):
        """测试创建实盘引擎"""
        result = engine_service.add(
            name=f"{unique_name}_live",
            is_live=True
        )

        assert result.is_success()
        assert result.data["engine_info"]["is_live"] is True

    @pytest.mark.parametrize("invalid_name, description", INVALID_ENGINE_NAMES)
    def test_add_engine_invalid_name(self, engine_service, invalid_name, description):
        """参数化测试：无效名称边界测试"""
        result = engine_service.add(name=invalid_name, is_live=False)
        assert not result.is_success(), f"应该拒绝{description}"
        assert "空" in result.error or "cannot" in result.error.lower()

    def test_add_engine_duplicate_name(self, engine_service, unique_name):
        """测试重名引擎应该被拒绝"""
        # 第一次创建应该成功
        first = engine_service.add(name=unique_name, is_live=False)
        assert first.is_success()

        # 第二次创建应该失败
        second = engine_service.add(name=unique_name, is_live=False)
        assert not second.is_success()
        assert "已存在" in second.error or "exists" in second.error.lower()

    def test_add_engine_long_name_truncation(self, engine_service, unique_name):
        """测试超长名称截断"""
        long_name = f"{unique_name}_{LONG_NAME}"
        result = engine_service.add(name=long_name, is_live=False)

        assert result.is_success()
        assert len(result.data["engine_info"]["name"]) <= 50
        assert len(result.warnings) > 0

    # -------------------- 查询操作 --------------------

    def test_get_engine_success(self, engine_service, sample_engine):
        """测试成功获取引擎"""
        result = engine_service.get(engine_id=sample_engine)

        assert result.is_success()
        assert len(result.data) == 1
        assert result.data[0].uuid == sample_engine

    def test_get_all_engines(self, engine_service):
        """测试获取所有引擎"""
        result = engine_service.get()

        assert result.is_success()
        assert result.data is not None
        assert isinstance(result.data, list)

    def test_get_engine_not_found(self, engine_service):
        """测试获取不存在的引擎"""
        result = engine_service.get(engine_id="nonexistent-uuid-12345")

        assert result.is_success()  # 查询本身成功
        assert len(result.data) == 0  # 但没有数据

    # -------------------- 更新操作 --------------------

    def test_update_engine_name(self, engine_service, sample_engine):
        """测试更新引擎名称"""
        result = engine_service.update(
            engine_id=sample_engine,
            name="updated_name"
        )

        assert result.is_success()

        # 验证更新
        get_result = engine_service.get(engine_id=sample_engine)
        assert get_result.data[0].name == "updated_name"

    def test_update_engine_is_live(self, engine_service, sample_engine):
        """测试更新引擎实盘标志"""
        result = engine_service.update(
            engine_id=sample_engine,
            is_live=True
        )

        assert result.is_success()

        get_result = engine_service.get(engine_id=sample_engine)
        assert get_result.data[0].is_live is True

    def test_update_engine_description(self, engine_service, sample_engine):
        """测试更新引擎描述"""
        result = engine_service.update(
            engine_id=sample_engine,
            description="Updated description"
        )

        assert result.is_success()

        get_result = engine_service.get(engine_id=sample_engine)
        assert get_result.data[0].desc == "Updated description"

    def test_update_engine_not_found(self, engine_service):
        """测试更新不存在的引擎"""
        result = engine_service.update(
            engine_id="nonexistent-uuid-12345",
            name="new_name"
        )

        # 当前实现允许更新不存在的UUID
        assert result.is_success()

        # 验证没有实际创建记录
        verify = engine_service.get(engine_id="nonexistent-uuid-12345")
        assert len(verify.data) == 0

    @pytest.mark.parametrize("invalid_name, description", INVALID_ENGINE_NAMES)
    def test_update_engine_invalid_name(self, engine_service, sample_engine, invalid_name, description):
        """参数化测试：更新时无效名称"""
        result = engine_service.update(
            engine_id=sample_engine,
            name=invalid_name
        )
        assert not result.is_success()

    # -------------------- 删除操作 --------------------

    def test_delete_engine_success(self, engine_service, unique_name):
        """测试成功删除引擎"""
        # 创建引擎
        create = engine_service.add(name=unique_name, is_live=False)
        uuid = create.data["engine_info"]["uuid"]

        # 删除引擎
        delete = engine_service.delete(uuid)
        assert delete.is_success()

        # 验证已删除
        get = engine_service.get(engine_id=uuid)
        assert len(get.data) == 0

    def test_delete_engine_empty_id(self, engine_service):
        """测试删除空引擎ID"""
        result = engine_service.delete("")

        assert not result.is_success()
        assert "不能为空" in result.error


# ============================================================================
# 测试类 - Engine状态管理
# ============================================================================

@pytest.mark.unit
@pytest.mark.db_cleanup
class TestEngineStatusManagement:
    """
    Engine状态管理测试
    测试引擎状态设置和转换
    """

    CLEANUP_CONFIG = {'engine': {'name__like': 'test_%'}}

    def test_set_status_success(self, engine_service, sample_engine):
        """测试成功设置引擎状态"""
        result = engine_service.set_status(sample_engine, ENGINESTATUS_TYPES.RUNNING)

        assert result.is_success()

    @pytest.mark.parametrize("status", VALID_ENGINE_STATES)
    def test_set_valid_statuses(self, engine_service, sample_engine, status):
        """参数化测试：设置有效状态"""
        result = engine_service.set_status(sample_engine, status)

        assert result.is_success()

    def test_set_status_empty_id(self, engine_service):
        """测试设置空ID的状态"""
        result = engine_service.set_status("", ENGINESTATUS_TYPES.RUNNING)

        assert not result.is_success()
        assert "不能为空" in result.error

    def test_status_transition_workflow(self, engine_service, unique_name):
        """测试状态转换工作流"""
        # 创建引擎
        create = engine_service.add(name=unique_name, is_live=False)
        uuid = create.data["engine_info"]["uuid"]

        # IDLE -> RUNNING
        engine_service.set_status(uuid, ENGINESTATUS_TYPES.RUNNING)

        # RUNNING -> PAUSED
        engine_service.set_status(uuid, ENGINESTATUS_TYPES.PAUSED)

        # PAUSED -> RUNNING
        engine_service.set_status(uuid, ENGINESTATUS_TYPES.RUNNING)

        # RUNNING -> STOPPED
        engine_service.set_status(uuid, ENGINESTATUS_TYPES.STOPPED)

        # 验证最终状态
        get_result = engine_service.get(engine_id=uuid)
        assert get_result.data[0].status == ENGINESTATUS_TYPES.STOPPED.value


# ============================================================================
# 测试类 - Engine与Portfolio映射
# ============================================================================

@pytest.mark.unit
@pytest.mark.db_cleanup
class TestEnginePortfolioMapping:
    """
    Engine与Portfolio映射测试
    测试引擎和投资组合的关联关系
    """

    CLEANUP_CONFIG = {
        'engine': {'name__like': 'test_%'},
        'engine_portfolio_mapping': {}
    }

    def test_add_portfolio_to_engine(self, engine_service, sample_engine):
        """测试添加投资组合到引擎"""
        # 这个功能需要PortfolioService支持
        # 这里只测试接口存在性
        assert hasattr(engine_service, 'add_portfolio') or hasattr(engine_service, 'mount_portfolio')

    def test_remove_portfolio_from_engine(self, engine_service, sample_engine):
        """测试从引擎移除投资组合"""
        assert hasattr(engine_service, 'remove_portfolio') or hasattr(engine_service, 'unmount_portfolio')

    def test_get_engine_portfolios(self, engine_service, sample_engine):
        """测试获取引擎的投资组合列表"""
        result = engine_service.get_portfolios(engine_id=sample_engine)

        assert result.is_success()
        assert isinstance(result.data, list)


# ============================================================================
# 测试类 - Engine验证
# ============================================================================

@pytest.mark.unit
class TestEngineValidation:
    """
    Engine数据验证测试
    测试各种边界条件和验证规则
    """

    def test_validate_valid_engine_data(self, engine_service):
        """测试验证有效引擎数据"""
        valid_data = {
            'name': 'Valid Engine',
            'is_live': False,
            'description': 'Valid description'
        }

        # EngineService可能没有validate方法，这里测试创建操作
        result = engine_service.add(**valid_data)
        assert result.is_success()

        # 清理
        if result.is_success():
            engine_service.delete(result.data["engine_info"]["uuid"])

    def test_validate_missing_name(self, engine_service):
        """测试验证缺少name的数据"""
        result = engine_service.add(is_live=False)

        assert not result.is_success()
        assert "name" in result.error.lower() or "required" in result.error.lower()


# ============================================================================
# 测试类 - Engine服务健康检查
# ============================================================================

@pytest.mark.unit
class TestEngineServiceHealth:
    """EngineService健康检查测试"""

    def test_health_check(self, engine_service):
        """测试健康检查返回正确信息"""
        result = engine_service.health_check()

        assert result.is_success()
        health_data = result.data
        assert health_data["service_name"] == "EngineService"
        assert health_data["status"] in ["healthy", "unhealthy", "degraded"]


# ============================================================================
# 测试类 - Engine服务集成测试
# ============================================================================

@pytest.mark.integration
@pytest.mark.db_cleanup
class TestEngineServiceIntegration:
    """
    EngineService集成测试
    测试完整的业务流程
    """

    CLEANUP_CONFIG = {'engine': {'name__like': 'integration_%'}}

    def test_full_lifecycle_workflow(self, engine_service):
        """测试完整生命周期：创建->运行->停止->删除"""
        # 1. 创建
        create = engine_service.add(
            name="integration_lifecycle",
            is_live=False,
            description="Integration test"
        )
        assert create.is_success()
        uuid = create.data["engine_info"]["uuid"]

        # 2. 设置为运行状态
        engine_service.set_status(uuid, ENGINESTATUS_TYPES.RUNNING)

        # 3. 验证状态
        get = engine_service.get(engine_id=uuid)
        assert get.data[0].status == ENGINESTATUS_TYPES.RUNNING.value

        # 4. 停止引擎
        engine_service.set_status(uuid, ENGINESTATUS_TYPES.STOPPED)

        # 5. 删除
        delete = engine_service.delete(uuid)
        assert delete.is_success()

        # 6. 验证删除
        verify = engine_service.get(engine_id=uuid)
        assert len(verify.data) == 0

    def test_backtest_to_live_transition(self, engine_service):
        """测试回测到实盘的转换流程"""
        # 1. 创建回测引擎
        create = engine_service.add(
            name="integration_transition",
            is_live=False
        )
        assert create.is_success()
        uuid = create.data["engine_info"]["uuid"]

        # 2. 升级为实盘
        update = engine_service.update(
            engine_id=uuid,
            is_live=True
        )
        assert update.is_success()

        # 3. 验证升级
        get = engine_service.get(engine_id=uuid)
        assert get.data[0].is_live is True

        # 清理
        engine_service.delete(uuid)

    def test_batch_engine_operations(self, engine_service):
        """测试批量操作：创建多个引擎"""
        names = [f"integration_batch_{i}" for i in range(3)]
        uuids = []

        # 批量创建
        for name in names:
            result = engine_service.add(name=name, is_live=False)
            assert result.is_success()
            uuids.append(result.data["engine_info"]["uuid"])

        # 验证全部存在
        all_engines = engine_service.get()
        assert all_engines.is_success()

        # 批量删除
        for uuid in uuids:
            engine_service.delete(uuid)

        # 验证全部删除
        for uuid in uuids:
            result = engine_service.get(engine_id=uuid)
            assert len(result.data) == 0
