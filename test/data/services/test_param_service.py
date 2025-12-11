"""
ParamService 测试用例 - 重构版本

测试参数管理服务的各项功能，使用真实数据库操作而非Mock
遵循ServiceResult统一格式和container最佳实践
"""

import pytest
import time
from datetime import datetime

# 设置测试环境路径
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../..', 'src'))

from ginkgo.data.services.param_service import ParamService
from ginkgo.data.services.base_service import ServiceResult
from ginkgo.data.containers import container
from ginkgo.libs import GLOG


def generate_test_id(prefix="test"):
    """生成短的测试ID（限制在32字符内）"""
    import random
    import string
    suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    # 确保总长度不超过32字符
    max_prefix_len = 32 - len("_") - len(suffix)
    if len(prefix) > max_prefix_len:
        prefix = prefix[:max_prefix_len]
    return f"{prefix}_{suffix}"


@pytest.mark.db_cleanup
class TestParamServiceBasics:
    """ParamService 基础功能测试"""

    CLEANUP_CONFIG = {
        'param': {'param_info__param_key__like': 'test_%'}
    }

    def test_service_initialization(self):
        """测试服务初始化"""
        service = container.param_service()
        assert service is not None
        assert hasattr(service, '_crud_repo')
        assert service._crud_repo is not None
        assert isinstance(service, ParamService)

    def test_health_check_success(self):
        """测试健康检查成功"""
        service = container.param_service()
        result = service.health_check()

        # 验证ServiceResult格式统一
        assert result.is_success(), f"健康检查失败: {result.error}"
        assert result.data is not None

        # 验证健康检查数据结构
        health_data = result.data
        assert "service_name" in health_data
        assert "status" in health_data
        assert health_data["service_name"] == "ParamService"
        assert health_data["status"] in ["healthy", "unhealthy", "degraded"]


@pytest.mark.db_cleanup
class TestParamServiceCRUD:
    """ParamService CRUD 操作测试"""

    CLEANUP_CONFIG = {
        'param': {'param_info__param_key__like': 'test_%'}
    }

    def test_add_param_success(self):
        """测试添加参数成功"""
        service = container.param_service()
        # 生成唯一测试数据
        timestamp = datetime.now().strftime('%H%M%S')
        test_mapping_id = f"test_{timestamp}"
        test_index = 0
        test_value = "test_value"

        # 执行添加操作
        result = service.add(
            mapping_id=test_mapping_id,
            index=test_index,
            value=test_value
        )

        # 验证ServiceResult格式
        assert result.is_success(), f"添加参数失败: {result.error}"
        assert result.data is not None

        # 验证返回的参数信息
        param_info = result.data
        assert "param_info" in param_info
        assert param_info["param_info"]["mapping_id"] == test_mapping_id
        assert param_info["param_info"]["index"] == test_index
        assert param_info["param_info"]["value"] == test_value

        # 验证数据库中的实际数据
        get_result = service.get(mapping_id=test_mapping_id, index=test_index)
        assert get_result.success, "验证数据库中的数据失败"
        assert len(get_result.data) > 0

    def test_add_param_empty_mapping_id(self):
        """测试添加参数 - 空映射ID"""
        service = container.param_service()
        result = service.add(mapping_id="", index=0, value="test")

        assert not result.success, "空映射ID应该返回失败"
        assert "映射ID不能为空" in result.error

    def test_add_param_negative_index(self):
        """测试添加参数 - 负数索引"""
        service = container.param_service()
        test_mapping_id = generate_test_id("test_negative")

        result = service.add(
            mapping_id=test_mapping_id,
            index=-1,
            value="test"
        )

        assert not result.success, "负数索引应该返回失败"
        assert "参数索引必须是非负整数" in result.error

    def test_add_param_empty_value(self):
        """测试添加参数 - 空值"""
        service = container.param_service()
        test_mapping_id = generate_test_id("test_empty_value")

        result = service.add(
            mapping_id=test_mapping_id,
            index=0,
            value=None
        )

        assert not result.success, "空值应该返回失败"
        assert "参数值不能为空" in result.error

    def test_add_param_duplicate(self):
        """测试添加参数 - 重复参数"""
        service = container.param_service()
        test_mapping_id = generate_test_id("test_duplicate")
        test_index = 0
        test_value = "test_value"

        # 先添加一个参数
        first_result = service.add(
            mapping_id=test_mapping_id,
            index=test_index,
            value=test_value
        )

        # 尝试添加重复参数
        second_result = service.add(
            mapping_id=test_mapping_id,
            index=test_index,
            value="another_value"
        )

        assert not second_result.success, "重复参数应该返回失败"
        assert "已存在参数" in second_result.error

    def test_update_param_by_id_success(self):
        """测试通过ID更新参数成功"""
        service = container.param_service()
        # 先创建一个参数
        test_mapping_id = generate_test_id('test')
        create_result = service.add(
            mapping_id=test_mapping_id,
            index=0,
            value="original_value"
        )

        assert create_result.success, "创建测试参数失败"
        param_uuid = create_result.data["param_info"]["uuid"]

        # 更新参数
        update_result = service.update(
            param_id=param_uuid,
            value="updated_value"
        )

        assert update_result.success, f"更新参数失败: {update_result.error}"

        # 验证更新后的数据
        get_result = service.get(mapping_id=test_mapping_id, index=0)
        assert get_result.success
        if len(get_result.data) > 0:
            updated_param = get_result.data[0]
            assert updated_param.value == "updated_value"

    def test_update_param_by_mapping_index_success(self):
        """测试通过映射ID和索引更新参数成功"""
        service = container.param_service()
        test_mapping_id = generate_test_id('test')

        # 先创建参数
        create_result = service.add(
            mapping_id=test_mapping_id,
            index=0,
            value="original_value"
        )

        assert create_result.success, "创建测试参数失败"

        # 通过映射ID和索引更新
        update_result = service.update(
            mapping_id=test_mapping_id,
            index=0,
            value="updated_value"
        )

        assert update_result.success, f"更新参数失败: {update_result.error}"

        # 验证更新结果
        get_result = service.get(mapping_id=test_mapping_id, index=0)
        assert get_result.success
        if len(get_result.data) > 0:
            updated_param = get_result.data[0]
            assert updated_param.value == "updated_value"

    def test_update_param_no_identifier(self):
        """测试更新参数 - 缺少标识符"""
        service = container.param_service()
        result = service.update(value="new_value")

        assert not result.success, "缺少标识符应该返回失败"
        assert "必须提供param_id或(mapping_id + index)" in result.error

    def test_update_param_no_fields(self):
        """测试更新参数 - 没有要更新的字段"""
        service = container.param_service()
        result = service.update(param_id="test_uuid")

        assert not result.success, "没有更新字段应该返回失败"
        assert "未提供要更新的字段" in result.error

    def test_delete_param_by_id_success(self):
        """测试通过ID删除参数成功"""
        service = container.param_service()
        # 先创建参数
        test_mapping_id = generate_test_id('test')
        create_result = service.add(
            mapping_id=test_mapping_id,
            index=0,
            value="to_delete"
        )

        assert create_result.success, "创建测试参数失败"
        param_uuid = create_result.data["param_info"]["uuid"]

        # 删除参数
        delete_result = service.delete(param_id=param_uuid)

        assert delete_result.success, f"删除参数失败: {delete_result.error}"
        assert delete_result.data["deleted_count"] >= 1

        # 验证参数已被删除
        get_result = service.get(param_id=param_uuid)
        assert get_result.success
        assert len(get_result.data) == 0

    def test_delete_param_by_mapping_index_success(self):
        """测试通过映射ID和索引删除参数成功"""
        service = container.param_service()
        test_mapping_id = generate_test_id('test')

        # 先创建参数
        create_result = service.add(
            mapping_id=test_mapping_id,
            index=0,
            value="to_delete"
        )

        assert create_result.success, "创建测试参数失败"

        # 删除参数
        delete_result = service.delete(
            mapping_id=test_mapping_id,
            index=0
        )

        assert delete_result.success, f"删除参数失败: {delete_result.error}"
        assert delete_result.data["deleted_count"] >= 1

    def test_delete_param_no_identifier(self):
        """测试删除参数 - 缺少标识符"""
        service = container.param_service()
        result = service.delete()

        assert not result.success, "缺少标识符应该返回失败"
        assert "必须提供param_id或(mapping_id + index)" in result.error

    def test_get_param_by_id_success(self):
        """测试通过ID获取参数成功"""
        service = container.param_service()
        # 先创建参数
        test_mapping_id = generate_test_id('test')
        create_result = service.add(
            mapping_id=test_mapping_id,
            index=0,
            value="test_value"
        )

        assert create_result.success, "创建测试参数失败"
        param_uuid = create_result.data["param_info"]["uuid"]

        # 获取参数
        get_result = service.get(param_id=param_uuid)

        assert get_result.success, f"获取参数失败: {get_result.error}"
        assert isinstance(get_result.data, list)
        assert len(get_result.data) > 0
        assert get_result.data[0].uuid == param_uuid

    def test_get_param_by_mapping_success(self):
        """测试通过映射ID获取参数成功"""
        service = container.param_service()
        test_mapping_id = generate_test_id('test')

        # 创建多个参数
        for i in range(3):
            create_result = service.add(
                mapping_id=test_mapping_id,
                index=i,
                value=f"value_{i}"
            )

        # 获取参数
        get_result = service.get(mapping_id=test_mapping_id)

        assert get_result.success, f"获取参数失败: {get_result.error}"
        assert isinstance(get_result.data, list)
        assert len(get_result.data) == 3

    def test_count_params_success(self):
        """测试统计参数数量成功"""
        service = container.param_service()
        test_mapping_id = generate_test_id('test')

        # 创建几个参数
        for i in range(3):
            create_result = service.add(
                mapping_id=test_mapping_id,
                index=i,
                value=f"value_{i}"
            )

        # 统计参数
        count_result = service.count(mapping_id=test_mapping_id)

        assert count_result.success, f"统计参数失败: {count_result.error}"
        assert "count" in count_result.data
        assert isinstance(count_result.data["count"], int)
        assert count_result.data["count"] == 3

    def test_exists_param_true(self):
        """测试检查参数存在性 - 存在"""
        service = container.param_service()
        test_mapping_id = generate_test_id('test')

        # 创建参数
        create_result = service.add(
            mapping_id=test_mapping_id,
            index=0,
            value="test_value"
        )

        assert create_result.success, "创建测试参数失败"

        # 检查存在性
        exists_result = service.exists(
            mapping_id=test_mapping_id,
            index=0
        )

        assert exists_result.success, f"检查存在性失败: {exists_result.error}"
        assert exists_result.data["exists"] is True

    def test_exists_param_false(self):
        """测试检查参数存在性 - 不存在"""
        service = container.param_service()
        result = service.exists(
            mapping_id="nonexistent_mapping",
            index=999
        )

        assert result.success, f"检查存在性失败: {result.error}"
        assert result.data["exists"] is False


@pytest.mark.db_cleanup
class TestParamServiceBusinessMethods:
    """ParamService 业务方法测试"""

    CLEANUP_CONFIG = {
        'param': {'param_info__param_key__like': 'test_%'}
    }

    def test_get_by_mapping_success(self):
        """测试根据映射ID获取参数成功"""
        service = container.param_service()
        test_mapping_id = generate_test_id('test')

        # 创建测试参数
        for i in range(3):
            create_result = service.add(
                mapping_id=test_mapping_id,
                index=i,
                value=f"value_{i}"
            )

        # 获取参数
        result = service.get_by_mapping(test_mapping_id)

        assert result.success, f"获取映射参数失败: {result.error}"
        assert isinstance(result.data, list)
        assert len(result.data) == 3

    def test_get_by_mapping_empty_mapping_id(self):
        """测试根据映射ID获取参数 - 空映射ID"""
        service = container.param_service()
        result = service.get_by_mapping("")

        assert not result.success, "空映射ID应该返回失败"
        assert "映射ID不能为空" in result.error

    def test_update_batch_success(self):
        """测试批量更新参数成功"""
        service = container.param_service()
        test_mapping_id = generate_test_id('test')
        params_dict = {0: "value0", 1: "value1", 2: "value2"}

        # 先创建参数
        for index in params_dict.keys():
            create_result = service.add(
                mapping_id=test_mapping_id,
                index=index,
                value=f"original_{index}"
            )

        # 批量更新
        result = service.update_batch(test_mapping_id, params_dict)

        assert result.success, f"批量更新失败: {result.error}"
        assert result.data["success_count"] == 3
        assert result.data["failed_count"] == 0

        # 验证更新结果
        for index, expected_value in params_dict.items():
            get_result = service.get(mapping_id=test_mapping_id, index=index)
            if get_result.success and len(get_result.data) > 0:
                assert get_result.data[0].value == expected_value

    def test_copy_success(self):
        """测试复制参数成功"""
        service = container.param_service()
        source_mapping = generate_test_id('test')
        target_mapping = generate_test_id('test')

        # 创建源参数
        source_params = []
        for i in range(2):
            create_result = service.add(
                mapping_id=source_mapping,
                index=i,
                value=f"source_value_{i}"
            )
            if create_result.success:
                source_params.append(create_result.data["param_info"])

        # 复制参数
        result = service.copy(
            source_mapping=source_mapping,
            target_mapping=target_mapping
        )

        assert result.success, f"复制参数失败: {result.error}"
        assert result.data["copied_count"] == 2
        assert result.data["failed_count"] == 0

        # 清理目标参数
        try:
            service.delete_batch_by_mapping(target_mapping)
        except:
            pass

    def test_copy_same_mapping(self):
        """测试复制参数 - 相同映射"""
        service = container.param_service()
        test_mapping = generate_test_id('test')

        result = service.copy(
            source_mapping=test_mapping,
            target_mapping=test_mapping
        )

        assert not result.success, "相同映射应该返回失败"
        assert "源映射和目标映射不能相同" in result.error

    def test_delete_batch_by_mapping_success(self):
        """测试删除映射参数成功"""
        service = container.param_service()
        test_mapping_id = generate_test_id('test')

        # 创建多个参数
        for i in range(3):
            create_result = service.add(
                mapping_id=test_mapping_id,
                index=i,
                value=f"value_{i}"
            )

        # 删除映射参数
        result = service.delete_batch_by_mapping(test_mapping_id)

        assert result.success, f"删除映射参数失败: {result.error}"
        assert result.data["deleted_count"] >= 1

        # 验证参数已被删除
        get_result = service.get(mapping_id=test_mapping_id)
        assert get_result.success
        assert len(get_result.data) == 0

    def test_get_summary_success(self):
        """测试获取参数汇总成功"""
        service = container.param_service()
        test_mapping_id = generate_test_id('test')

        # 创建参数
        for i in range(3):
            create_result = service.add(
                mapping_id=test_mapping_id,
                index=i,
                value=f"value_{i}"
            )

        # 获取汇总
        result = service.get_summary(test_mapping_id)

        assert result.success, f"获取参数汇总失败: {result.error}"
        summary_data = result.data
        assert "total_params" in summary_data
        assert "param_count" in summary_data
        assert "min_index" in summary_data
        assert "max_index" in summary_data
        assert summary_data["total_params"] == 3
        assert summary_data["param_count"] == 3
        assert summary_data["min_index"] == 0
        assert summary_data["max_index"] == 2

    def test_validate_success(self):
        """测试参数验证成功"""
        service = container.param_service()
        test_mapping_id = generate_test_id('test')

        # 创建有效参数
        for i in range(2):
            create_result = service.add(
                mapping_id=test_mapping_id,
                index=i,
                value=f"value_{i}"
            )

        # 验证参数
        result = service.validate(test_mapping_id)

        assert result.success, f"参数验证失败: {result.error}"
        assert result.data["is_valid"] is True
        assert result.data["param_count"] == 2


@pytest.mark.db_cleanup
class TestParamServiceIntegration:
    """ParamService 集成测试"""

    CLEANUP_CONFIG = {
        'param': {'param_info__param_key__like': 'test_%'}
    }

    def test_param_lifecycle(self):
        """测试参数完整生命周期"""
        service = container.param_service()
        test_mapping_id = generate_test_id('test')

        # 1. 创建参数
        create_result = service.add(
            mapping_id=test_mapping_id,
            index=0,
            value="lifecycle_value"
        )

        assert create_result.success, "创建参数失败"
        param_uuid = create_result.data["param_info"]["uuid"]

        # 2. 更新参数
        update_result = service.update(
            param_id=param_uuid,
            value="updated_lifecycle_value"
        )
        assert update_result.success, "更新参数失败"

        # 3. 检查存在性
        exists_result = service.exists(
            mapping_id=test_mapping_id,
            index=0
        )
        assert exists_result.success
        assert exists_result.data["exists"] is True

        # 4. 获取参数
        get_result = service.get(param_id=param_uuid)
        assert get_result.success
        assert len(get_result.data) > 0
        assert get_result.data[0].value == "updated_lifecycle_value"

        # 5. 删除参数
        delete_result = service.delete(param_id=param_uuid)
        assert delete_result.success

        # 6. 验证已删除
        final_get_result = service.get(param_id=param_uuid)
        assert final_get_result.success
        assert len(final_get_result.data) == 0

        # 测试已删除，无需手动清理


if __name__ == "__main__":
    pytest.main([__file__, "-v"])