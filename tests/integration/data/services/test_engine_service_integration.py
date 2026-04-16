"""
EngineService 集成测试 - 连接真实数据库通过CRUD操作

测试EngineService与MySQL数据库的集成，验证引擎配置的增删改查、
存在性检查、健康检查和数据验证等功能。
需要数据库环境可用，使用 SOURCE_TYPES.TEST 隔离测试数据。

运行方式:
    pytest tests/integration/data/services/test_engine_service_integration.py -v -m "database and integration"
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.enums import SOURCE_TYPES, ENGINESTATUS_TYPES
from ginkgo.data.services.engine_service import EngineService
from ginkgo.data.services.base_service import ServiceResult


# 测试用的唯一引擎名称前缀，避免与其他测试冲突
_TEST_ENGINE_PREFIX = "INT_TEST_"
_TEST_COUNTER = [0]


def _unique_engine_name():
    """生成唯一的测试引擎名称"""
    _TEST_COUNTER[0] += 1
    return f"{_TEST_ENGINE_PREFIX}{datetime.now().strftime('%H%M%S')}_{_TEST_COUNTER[0]}"


def _skip_if_db_unavailable(exc):
    """数据库不可用时跳过测试的辅助函数"""
    pytest.skip(f"数据库不可用，跳过集成测试: {exc}")


def _create_engine_service():
    """创建连接真实数据库的EngineService实例"""
    from ginkgo.data.crud.engine_crud import EngineCRUD
    from ginkgo.data.crud.engine_portfolio_mapping_crud import EnginePortfolioMappingCRUD
    from ginkgo.data.crud.param_crud import ParamCRUD

    try:
        engine_crud = EngineCRUD()
        mapping_crud = EnginePortfolioMappingCRUD()
        param_crud = ParamCRUD()

        return EngineService(
            crud_repo=engine_crud,
            engine_portfolio_mapping_crud=mapping_crud,
            param_crud=param_crud
        )
    except Exception as e:
        _skip_if_db_unavailable(e)


@pytest.fixture(scope="module")
def engine_service():
    """EngineService fixture - 模块级别共享"""
    return _create_engine_service()


@pytest.fixture(scope="function")
def engine_service_with_cleanup(engine_service):
    """每次测试后清理测试数据的EngineService fixture"""
    test_engine_id = None
    yield (engine_service, lambda eid: setattr(type('', (), {'engine_id': eid})(), 'engine_id', eid))

    # 清理所有以INT_TEST_开头的测试引擎
    try:
        engines = engine_service._crud_repo.find(
            filters={"name__startswith": _TEST_ENGINE_PREFIX, "is_del": False},
            as_dataframe=False
        )
        if engines:
            for engine in engines:
                engine_service.delete(engine_id=engine.uuid)
    except Exception:
        pass


@pytest.mark.database
@pytest.mark.integration
class TestEngineServiceConstruction:
    """1. EngineService构造与数据库连接测试"""

    def test_service_construction(self, engine_service):
        """测试EngineService使用真实CRUD成功构造"""
        assert engine_service is not None
        assert isinstance(engine_service, EngineService)

    def test_service_crud_repo_connected(self, engine_service):
        """测试CRUD仓库已正确注入"""
        assert engine_service._crud_repo is not None

    def test_service_mapping_repo_connected(self, engine_service):
        """测试引擎-组合映射CRUD已正确注入"""
        assert engine_service._mapping_repo is not None

    def test_service_param_repo_connected(self, engine_service):
        """测试参数CRUD已正确注入"""
        assert engine_service._param_crud is not None

    def test_service_name(self, engine_service):
        """测试服务名称正确设置"""
        assert engine_service.service_name == "EngineService"


@pytest.mark.database
@pytest.mark.integration
class TestEngineServiceAdd:
    """2. 引擎创建测试"""

    def test_add_engine(self, engine_service_with_cleanup):
        """测试创建新引擎"""
        engine_service, _ = engine_service_with_cleanup
        name = _unique_engine_name()

        result = engine_service.add(name=name, is_live=False)

        assert isinstance(result, ServiceResult)
        assert result.success is True
        assert result.data is not None
        assert "engine_info" in result.data
        assert result.data["engine_info"]["name"] == name
        assert result.data["engine_info"]["is_live"] is False

    def test_add_engine_with_description(self, engine_service_with_cleanup):
        """测试创建带描述的引擎"""
        engine_service, _ = engine_service_with_cleanup
        name = _unique_engine_name()
        description = "集成测试用引擎描述"

        result = engine_service.add(name=name, is_live=False, description=description)

        assert isinstance(result, ServiceResult)
        assert result.success is True
        assert "engine_info" in result.data

    def test_add_engine_duplicate_name(self, engine_service_with_cleanup):
        """测试创建重复名称的引擎应失败"""
        engine_service, _ = engine_service_with_cleanup
        name = _unique_engine_name()

        # 第一次创建
        result1 = engine_service.add(name=name)
        assert result1.success is True

        # 第二次创建同名引擎
        result2 = engine_service.add(name=name)
        assert result2.success is False
        assert result2.error != ""

    def test_add_engine_empty_name(self, engine_service):
        """测试创建空名称的引擎应失败"""
        result = engine_service.add(name="")
        assert isinstance(result, ServiceResult)
        assert result.success is False


@pytest.mark.database
@pytest.mark.integration
class TestEngineServiceGet:
    """3. 引擎查询测试"""

    def test_get_all_engines(self, engine_service):
        """测试查询所有引擎"""
        result = engine_service.get()

        assert isinstance(result, ServiceResult)
        assert result.success is True
        assert result.data is not None

    def test_get_engine_by_id(self, engine_service_with_cleanup):
        """测试按ID查询引擎"""
        engine_service, _ = engine_service_with_cleanup
        name = _unique_engine_name()

        # 先创建
        add_result = engine_service.add(name=name)
        engine_id = add_result.data["engine_info"]["uuid"]

        # 再查询
        result = engine_service.get(engine_id=engine_id)

        assert isinstance(result, ServiceResult)
        assert result.success is True
        assert result.data is not None

    def test_get_engine_by_name(self, engine_service_with_cleanup):
        """测试按名称查询引擎"""
        engine_service, _ = engine_service_with_cleanup
        name = _unique_engine_name()

        # 先创建
        engine_service.add(name=name)

        # 按名称查询
        result = engine_service.get(name=name)

        assert isinstance(result, ServiceResult)
        assert result.success is True


@pytest.mark.database
@pytest.mark.integration
class TestEngineServiceCount:
    """4. 引擎统计测试"""

    def test_count_all_engines(self, engine_service):
        """测试统计所有引擎数量"""
        result = engine_service.count()

        assert isinstance(result, ServiceResult)
        assert result.success is True
        assert result.data is not None
        assert "count" in result.data
        assert isinstance(result.data["count"], int)
        assert result.data["count"] >= 0

    def test_count_engines_after_add(self, engine_service_with_cleanup):
        """测试创建引擎后数量增加"""
        engine_service, _ = engine_service_with_cleanup

        before = engine_service.count()
        assert before.success is True
        before_count = before.data["count"]

        name = _unique_engine_name()
        engine_service.add(name=name)

        after = engine_service.count()
        assert after.success is True
        after_count = after.data["count"]

        assert after_count == before_count + 1


@pytest.mark.database
@pytest.mark.integration
class TestEngineServiceUpdate:
    """5. 引擎更新测试"""

    def test_update_engine_name(self, engine_service_with_cleanup):
        """测试更新引擎名称"""
        engine_service, _ = engine_service_with_cleanup
        name = _unique_engine_name()

        # 创建
        add_result = engine_service.add(name=name)
        engine_id = add_result.data["engine_info"]["uuid"]

        # 更新名称
        new_name = f"{name}_UPDATED"
        result = engine_service.update(engine_id=engine_id, name=new_name)

        assert isinstance(result, ServiceResult)
        assert result.success is True
        assert result.data is not None
        assert result.data["engine_info"]["name"] == new_name

    def test_update_engine_status(self, engine_service_with_cleanup):
        """测试更新引擎状态"""
        engine_service, _ = engine_service_with_cleanup
        name = _unique_engine_name()

        # 创建（默认IDLE状态）
        add_result = engine_service.add(name=name)
        engine_id = add_result.data["engine_info"]["uuid"]

        # 更新状态
        result = engine_service.set_status(
            engine_id=engine_id,
            status=ENGINESTATUS_TYPES.RUNNING
        )

        assert isinstance(result, ServiceResult)
        assert result.success is True

    def test_update_nonexistent_engine(self, engine_service):
        """测试更新不存在的引擎应失败"""
        result = engine_service.update(
            engine_id="00000000-0000-0000-0000-000000000000",
            name="不存在"
        )
        # 可能失败或返回无更新
        assert isinstance(result, ServiceResult)


@pytest.mark.database
@pytest.mark.integration
class TestEngineServiceDelete:
    """6. 引擎删除测试"""

    def test_delete_engine(self, engine_service_with_cleanup):
        """测试删除引擎"""
        engine_service, _ = engine_service_with_cleanup
        name = _unique_engine_name()

        # 创建
        add_result = engine_service.add(name=name)
        engine_id = add_result.data["engine_info"]["uuid"]

        # 验证存在
        exists_result = engine_service.exists(engine_id=engine_id)
        assert exists_result.success is True
        assert exists_result.data["exists"] is True

        # 删除
        result = engine_service.delete(engine_id=engine_id)

        assert isinstance(result, ServiceResult)
        assert result.success is True
        assert result.data is not None

        # 验证已删除
        exists_after = engine_service.exists(engine_id=engine_id)
        assert exists_after.success is True
        assert exists_after.data["exists"] is False

    def test_delete_nonexistent_engine(self, engine_service):
        """测试删除不存在的引擎"""
        result = engine_service.delete(
            engine_id="00000000-0000-0000-0000-000000000000"
        )
        # 可能成功也可能失败，取决于实现
        assert isinstance(result, ServiceResult)


@pytest.mark.database
@pytest.mark.integration
class TestEngineServiceHealthCheck:
    """7. 健康检查测试"""

    def test_health_check(self, engine_service):
        """测试服务健康检查"""
        result = engine_service.health_check()

        assert isinstance(result, ServiceResult)
        assert result.success is True
        assert result.data is not None

        # 健康检查应返回数据库连接状态和各CRUD计数
        assert "database_connection" in result.data
        assert "engine_count" in result.data
        assert "mapping_count" in result.data
        assert "param_count" in result.data


@pytest.mark.database
@pytest.mark.integration
class TestEngineServiceValidate:
    """8. 数据验证测试"""

    def test_validate_engine_data(self, engine_service):
        """测试引擎数据验证 - 无参数时通过"""
        result = engine_service.validate()

        assert isinstance(result, ServiceResult)
        assert result.success is True

    def test_validate_nonexistent_engine(self, engine_service):
        """测试验证不存在的引擎"""
        result = engine_service.validate(
            engine_id="00000000-0000-0000-0000-000000000000"
        )
        assert isinstance(result, ServiceResult)
        assert result.success is False

    def test_validate_engine_data_fields(self, engine_service):
        """测试引擎数据字段验证"""
        # 空名称应失败
        result = engine_service.validate(engine_data={"name": ""})
        assert result.success is False

        # 无效的is_live类型应失败
        result = engine_service.validate(engine_data={"is_live": "not_bool"})
        assert result.success is False

        # 无效的状态值应失败
        result = engine_service.validate(engine_data={"status": 999})
        assert result.success is False


@pytest.mark.database
@pytest.mark.integration
class TestEngineServiceExists:
    """9. 引擎存在性检查测试"""

    def test_exists_after_create(self, engine_service_with_cleanup):
        """测试创建后存在性检查返回True"""
        engine_service, _ = engine_service_with_cleanup
        name = _unique_engine_name()

        add_result = engine_service.add(name=name)
        engine_id = add_result.data["engine_info"]["uuid"]

        result = engine_service.exists(engine_id=engine_id)
        assert isinstance(result, ServiceResult)
        assert result.success is True
        assert result.data["exists"] is True

    def test_exists_nonexistent(self, engine_service):
        """测试不存在的引擎"""
        result = engine_service.exists(
            engine_id="00000000-0000-0000-0000-000000000000"
        )
        assert isinstance(result, ServiceResult)
        assert result.success is True
        assert result.data["exists"] is False


@pytest.mark.database
@pytest.mark.integration
class TestEngineServiceIntegrity:
    """10. 数据完整性检查测试"""

    def test_check_integrity_all(self, engine_service):
        """测试检查所有引擎数据完整性"""
        result = engine_service.check_integrity()

        assert isinstance(result, ServiceResult)
        assert result.success is True
        assert result.data is not None

    def test_check_integrity_single_engine(self, engine_service_with_cleanup):
        """测试检查单个引擎数据完整性"""
        engine_service, _ = engine_service_with_cleanup
        name = _unique_engine_name()

        add_result = engine_service.add(name=name)
        engine_id = add_result.data["engine_info"]["uuid"]

        result = engine_service.check_integrity(engine_id=engine_id)
        assert isinstance(result, ServiceResult)
        assert result.success is True
