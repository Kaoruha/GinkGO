"""
ParamService数据服务测试

测试参数管理服务的核心功能和业务逻辑
遵循pytest最佳实践，使用fixtures和参数化测试
"""
import pytest
import sys
from pathlib import Path
from datetime import datetime
import random
import string

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.data.services.param_service import ParamService
from ginkgo.data.services.base_service import BaseService, ServiceResult
from ginkgo.data.containers import container
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
def param_service():
    """获取ParamService实例"""
    return container.param_service()


@pytest.fixture
def unique_mapping_id():
    """生成唯一的测试映射ID"""
    timestamp = datetime.now().strftime('%H%M%S')
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
    return f"test_{timestamp}_{suffix}"


@pytest.fixture
def sample_param(param_service, unique_mapping_id):
    """创建示例参数"""
    result = param_service.add(
        mapping_id=unique_mapping_id,
        index=0,
        value="test_value"
    )
    yield result
    # 清理
    try:
        param_service.delete(mapping_id=unique_mapping_id, index=0)
    except Exception:
        pass


# ============================================================================
# 参数化测试数据
# ============================================================================

# 有效的参数值
VALID_VALUES = [
    (0, "数值0"),
    (1, "数值1"),
    (100, "数值100"),
    ("string_value", "字符串值"),
    (True, "布尔值True"),
    (False, "布尔值False"),
]

# 无效的索引
INVALID_INDICES = [
    (-1, "负数索引"),
    (-100, "大负数索引"),
]

# 无效的映射ID
INVALID_MAPPING_IDS = [
    ("", "空字符串"),
    ("   ", "纯空格"),
]


# ============================================================================
# 测试类 - 服务初始化和构造
# ============================================================================

@pytest.mark.unit
class TestParamServiceConstruction:
    """测试ParamService初始化和构造"""

    def test_service_initialization(self, param_service):
        """测试服务初始化"""
        assert param_service is not None
        assert isinstance(param_service, ParamService)

    def test_service_inherits_base_service(self, param_service):
        """测试继承BaseService"""
        assert isinstance(param_service, BaseService)

    def test_crud_repo_exists(self, param_service):
        """测试CRUD仓库存在"""
        assert hasattr(param_service, '_crud_repo')
        assert param_service._crud_repo is not None


# ============================================================================
# 测试类 - CRUD操作
# ============================================================================

@pytest.mark.database
@pytest.mark.db_cleanup
class TestParamServiceCRUD:
    """测试ParamService CRUD操作"""

    CLEANUP_CONFIG = {
        'param': {'param_info__param_key__like': 'test_%'}
    }

    def test_add_param_success(self, param_service, unique_mapping_id):
        """测试成功添加参数"""
        test_value = "test_value"
        result = param_service.add(
            mapping_id=unique_mapping_id,
            index=0,
            value=test_value
        )

        assert result.is_success()
        assert result.data is not None
        assert "param_info" in result.data
        assert result.data["param_info"]["value"] == test_value

    @pytest.mark.parametrize("index,description", INVALID_INDICES)
    def test_add_param_invalid_index(self, param_service, unique_mapping_id, index, description):
        """测试添加参数 - 无效索引"""
        result = param_service.add(
            mapping_id=unique_mapping_id,
            index=index,
            value="test_value"
        )

        assert not result.success
        assert "索引必须是非负整数" in result.error or "参数索引必须是非负整数" in result.error

    def test_add_param_duplicate(self, param_service, unique_mapping_id):
        """测试添加重复参数"""
        # 第一次添加
        param_service.add(
            mapping_id=unique_mapping_id,
            index=0,
            value="first_value"
        )

        # 第二次添加相同参数
        result = param_service.add(
            mapping_id=unique_mapping_id,
            index=0,
            value="second_value"
        )

        assert not result.success
        assert "已存在参数" in result.error or "重复" in result.error

    def test_get_param_by_id(self, param_service, unique_mapping_id):
        """测试通过ID获取参数"""
        # 先创建参数
        create_result = param_service.add(
            mapping_id=unique_mapping_id,
            index=0,
            value="test_value"
        )
        assert create_result.success
        param_uuid = create_result.data["param_info"]["uuid"]

        # 获取参数
        result = param_service.get(param_id=param_uuid)

        assert result.success
        assert len(result.data) > 0
        assert result.data[0].uuid == param_uuid

    def test_get_param_by_mapping(self, param_service, unique_mapping_id):
        """测试通过映射获取参数"""
        # 创建多个参数
        for i in range(3):
            param_service.add(
                mapping_id=unique_mapping_id,
                index=i,
                value=f"value_{i}"
            )

        # 获取参数
        result = param_service.get(mapping_id=unique_mapping_id)

        assert result.success
        assert len(result.data) == 3

    def test_update_param_by_id(self, param_service, unique_mapping_id):
        """测试通过ID更新参数"""
        # 先创建参数
        create_result = param_service.add(
            mapping_id=unique_mapping_id,
            index=0,
            value="original_value"
        )
        param_uuid = create_result.data["param_info"]["uuid"]

        # 更新参数
        result = param_service.update(
            param_id=param_uuid,
            value="updated_value"
        )

        assert result.success

        # 验证更新
        get_result = param_service.get(param_id=param_uuid)
        assert get_result.success
        if len(get_result.data) > 0:
            assert get_result.data[0].value == "updated_value"

    def test_delete_param_by_id(self, param_service, unique_mapping_id):
        """测试通过ID删除参数"""
        # 先创建参数
        create_result = param_service.add(
            mapping_id=unique_mapping_id,
            index=0,
            value="to_delete"
        )
        param_uuid = create_result.data["param_info"]["uuid"]

        # 删除参数
        result = param_service.delete(param_id=param_uuid)

        assert result.success
        assert result.data["deleted_count"] >= 1

        # 验证已删除
        get_result = param_service.get(param_id=param_uuid)
        assert len(get_result.data) == 0

    def test_count_params(self, param_service, unique_mapping_id):
        """测试统计参数数量"""
        # 创建几个参数
        for i in range(3):
            param_service.add(
                mapping_id=unique_mapping_id,
                index=i,
                value=f"value_{i}"
            )

        # 统计参数
        result = param_service.count(mapping_id=unique_mapping_id)

        assert result.success
        assert "count" in result.data
        assert result.data["count"] == 3


# ============================================================================
# 测试类 - 业务方法
# ============================================================================

@pytest.mark.database
@pytest.mark.db_cleanup
class TestParamServiceBusinessMethods:
    """测试ParamService业务方法"""

    CLEANUP_CONFIG = {
        'param': {'param_info__param_key__like': 'test_%'}
    }

    def test_exists_param_true(self, param_service, unique_mapping_id):
        """测试检查参数存在性 - 存在"""
        param_service.add(
            mapping_id=unique_mapping_id,
            index=0,
            value="test_value"
        )

        result = param_service.exists(
            mapping_id=unique_mapping_id,
            index=0
        )

        assert result.success
        assert result.data["exists"] is True

    def test_exists_param_false(self, param_service):
        """测试检查参数存在性 - 不存在"""
        result = param_service.exists(
            mapping_id="nonexistent_mapping",
            index=999
        )

        assert result.success
        assert result.data["exists"] is False

    def test_get_by_mapping(self, param_service, unique_mapping_id):
        """测试根据映射ID获取参数"""
        # 创建多个参数
        for i in range(3):
            param_service.add(
                mapping_id=unique_mapping_id,
                index=i,
                value=f"value_{i}"
            )

        result = param_service.get_by_mapping(unique_mapping_id)

        assert result.success
        assert len(result.data) == 3

    def test_update_batch(self, param_service, unique_mapping_id):
        """测试批量更新参数"""
        # 先创建参数
        for i in range(3):
            param_service.add(
                mapping_id=unique_mapping_id,
                index=i,
                value=f"original_{i}"
            )

        # 批量更新
        params_dict = {0: "value0", 1: "value1", 2: "value2"}
        result = param_service.update_batch(unique_mapping_id, params_dict)

        assert result.success
        assert result.data["success_count"] == 3
        assert result.data["failed_count"] == 0

    def test_copy_params(self, param_service):
        """测试复制参数"""
        source_mapping = unique_mapping_id()
        target_mapping = unique_mapping_id()

        # 创建源参数
        for i in range(2):
            param_service.add(
                mapping_id=source_mapping,
                index=i,
                value=f"source_value_{i}"
            )

        # 复制参数
        result = param_service.copy(
            source_mapping=source_mapping,
            target_mapping=target_mapping
        )

        assert result.success
        assert result.data["copied_count"] == 2

        # 清理目标参数
        try:
            param_service.delete_batch_by_mapping(target_mapping)
        except Exception:
            pass

    def test_delete_batch_by_mapping(self, param_service, unique_mapping_id):
        """测试删除映射参数"""
        # 创建多个参数
        for i in range(3):
            param_service.add(
                mapping_id=unique_mapping_id,
                index=i,
                value=f"value_{i}"
            )

        # 删除映射参数
        result = param_service.delete_batch_by_mapping(unique_mapping_id)

        assert result.success
        assert result.data["deleted_count"] >= 1

    def test_get_summary(self, param_service, unique_mapping_id):
        """测试获取参数汇总"""
        # 创建参数
        for i in range(3):
            param_service.add(
                mapping_id=unique_mapping_id,
                index=i,
                value=f"value_{i}"
            )

        result = param_service.get_summary(unique_mapping_id)

        assert result.success
        summary_data = result.data
        assert "total_params" in summary_data
        assert "param_count" in summary_data
        assert summary_data["total_params"] == 3

    def test_validate_params(self, param_service, unique_mapping_id):
        """测试参数验证"""
        # 创建有效参数
        for i in range(2):
            param_service.add(
                mapping_id=unique_mapping_id,
                index=i,
                value=f"value_{i}"
            )

        result = param_service.validate(unique_mapping_id)

        assert result.success
        assert result.data["is_valid"] is True


# ============================================================================
# 测试类 - 健康检查
# ============================================================================

@pytest.mark.unit
class TestParamServiceHealthCheck:
    """测试健康检查功能"""

    def test_health_check_success(self, param_service):
        """测试健康检查成功"""
        result = param_service.health_check()

        assert result.is_success()
        assert result.data is not None

        # 验证健康检查数据结构
        health_data = result.data
        assert "service_name" in health_data
        assert "status" in health_data
        assert health_data["service_name"] == "ParamService"


# ============================================================================
# 测试类 - 错误处理
# ============================================================================

@pytest.mark.unit
class TestParamServiceErrorHandling:
    """测试错误处理"""

    @pytest.mark.parametrize("mapping_id,description", INVALID_MAPPING_IDS)
    def test_add_with_invalid_mapping_id(self, param_service, mapping_id, description):
        """测试使用无效映射ID添加参数"""
        result = param_service.add(
            mapping_id=mapping_id,
            index=0,
            value="test_value"
        )

        assert not result.success

    def test_update_without_identifier(self, param_service):
        """测试更新缺少标识符"""
        result = param_service.update(value="new_value")

        assert not result.success

    def test_delete_without_identifier(self, param_service):
        """测试删除缺少标识符"""
        result = param_service.delete()

        assert not result.success


# ============================================================================
# 测试类 - 业务逻辑
# ============================================================================

@pytest.mark.database
@pytest.mark.db_cleanup
class TestParamServiceBusinessLogic:
    """测试业务逻辑"""

    CLEANUP_CONFIG = {
        'param': {'param_info__param_key__like': 'test_%'}
    }

    def test_param_lifecycle(self, param_service, unique_mapping_id):
        """测试参数完整生命周期"""
        # 1. 创建
        create_result = param_service.add(
            mapping_id=unique_mapping_id,
            index=0,
            value="lifecycle_value"
        )
        assert create_result.success
        param_uuid = create_result.data["param_info"]["uuid"]

        # 2. 读取
        get_result = param_service.get(param_id=param_uuid)
        assert get_result.success
        assert len(get_result.data) > 0

        # 3. 检查存在性
        exists_result = param_service.exists(
            mapping_id=unique_mapping_id,
            index=0
        )
        assert exists_result.success
        assert exists_result.data["exists"] is True

        # 4. 更新
        update_result = param_service.update(
            param_id=param_uuid,
            value="updated_value"
        )
        assert update_result.success

        # 5. 删除
        delete_result = param_service.delete(param_id=param_uuid)
        assert delete_result.success

        # 6. 验证已删除
        final_get = param_service.get(param_id=param_uuid)
        assert len(final_get.data) == 0


# ============================================================================
# 测试类 - 边界测试
# ============================================================================

@pytest.mark.database
@pytest.mark.db_cleanup
class TestParamServiceEdgeCases:
    """测试边界情况"""

    CLEANUP_CONFIG = {
        'param': {'param_info__param_key__like': 'test_%'}
    }

    @pytest.mark.parametrize("value,description", VALID_VALUES)
    def test_various_value_types(self, param_service, unique_mapping_id, value, description):
        """测试各种值类型"""
        result = param_service.add(
            mapping_id=unique_mapping_id,
            index=0,
            value=value
        )

        assert result.success
        assert result.data["param_info"]["value"] == value

    def test_same_mapping_different_indices(self, param_service, unique_mapping_id):
        """测试相同映射不同索引"""
        # 创建多个不同索引的参数
        for i in range(5):
            param_service.add(
                mapping_id=unique_mapping_id,
                index=i,
                value=f"value_{i}"
            )

        # 获取所有参数
        result = param_service.get(mapping_id=unique_mapping_id)

        assert result.success
        assert len(result.data) == 5

        # 验证索引唯一性
        indices = [p.index for p in result.data]
        assert len(indices) == len(set(indices))
