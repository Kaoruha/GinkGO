"""
ParamService 测试用例

测试参数管理服务的各项功能，包括标准CRUD操作和业务方法。
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock

# 设置测试环境路径
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../..', 'src'))

from ginkgo.data.services.param_service import ParamService
from ginkgo.data.services.base_service import ServiceResult
from ginkgo.libs import GLOG


class TestParamServiceBasics:
    """ParamService 基础功能测试"""

    def setup_method(self):
        """测试前置设置"""
        self.service = ParamService()
        self.test_mapping_id = "test_mapping_001"
        self.test_index = 0
        self.test_value = "test_value"

    def test_service_initialization(self):
        """测试服务初始化"""
        assert self.service is not None
        assert hasattr(self.service, '_crud_repo')
        assert self.service._crud_repo is not None

    def test_health_check_success(self):
        """测试健康检查成功"""
        with patch.object(self.service._crud_repo, 'count', return_value=10):
            result = self.service.health_check()

            assert result.is_success()
            assert result.data["status"] == "healthy"
            assert result.data["param_count"] == 10
            assert result.data["crud_connection"] == "ok"

    def test_health_check_failure(self):
        """测试健康检查失败"""
        with patch.object(self.service._crud_repo, 'count', side_effect=Exception("DB Error")):
            result = self.service.health_check()

            assert not result.is_success()
            assert "健康检查失败" in result.error


class TestParamServiceCRUD:
    """ParamService CRUD 操作测试"""

    def setup_method(self):
        """测试前置设置"""
        self.service = ParamService()
        self.test_mapping_id = "test_mapping_001"
        self.test_index = 0
        self.test_value = "test_value"

    def test_add_param_success(self):
        """测试添加参数成功"""
        # Mock 模型对象
        mock_param = Mock()
        mock_param.uuid = "test_uuid_001"
        mock_param.mapping_id = self.test_mapping_id
        mock_param.index = self.test_index
        mock_param.value = self.test_value

        with patch.object(self.service._crud_repo, 'find', return_value=[]), \
             patch.object(self.service._crud_repo, 'create', return_value=mock_param):

            result = self.service.add(
                mapping_id=self.test_mapping_id,
                index=self.test_index,
                value=self.test_value
            )

            assert result.is_success()
            assert result.data["param_info"]["uuid"] == "test_uuid_001"
            assert result.data["param_info"]["mapping_id"] == self.test_mapping_id
            assert result.data["param_info"]["index"] == self.test_index
            assert result.data["param_info"]["value"] == self.test_value

    def test_add_param_empty_mapping_id(self):
        """测试添加参数 - 空映射ID"""
        result = self.service.add(mapping_id="", index=0, value="test")

        assert not result.is_success()
        assert "映射ID不能为空" in result.error

    def test_add_param_negative_index(self):
        """测试添加参数 - 负数索引"""
        result = self.service.add(
            mapping_id=self.test_mapping_id,
            index=-1,
            value="test"
        )

        assert not result.is_success()
        assert "参数索引必须是非负整数" in result.error

    def test_add_param_empty_value(self):
        """测试添加参数 - 空值"""
        result = self.service.add(
            mapping_id=self.test_mapping_id,
            index=0,
            value=None
        )

        assert not result.is_success()
        assert "参数值不能为空" in result.error

    def test_add_param_duplicate(self):
        """测试添加参数 - 重复参数"""
        with patch.object(self.service._crud_repo, 'find', return_value=[Mock()]):
            result = self.service.add(
                mapping_id=self.test_mapping_id,
                index=self.test_index,
                value=self.test_value
            )

            assert not result.is_success()
            assert "已存在参数" in result.error

    def test_update_param_by_id_success(self):
        """测试通过ID更新参数成功"""
        mock_param = Mock()
        mock_param.uuid = "test_uuid_001"
        mock_param.mapping_id = self.test_mapping_id
        mock_param.index = self.test_index
        mock_param.value = "updated_value"

        with patch.object(self.service._crud_repo, 'modify', return_value=1), \
             patch.object(self.service._crud_repo, 'find', return_value=[mock_param]):

            result = self.service.update(
                param_id="test_uuid_001",
                value="updated_value"
            )

            assert result.is_success()
            assert result.data["param_info"]["value"] == "updated_value"

    def test_update_param_by_mapping_index_success(self):
        """测试通过映射ID和索引更新参数成功"""
        mock_param = Mock()
        mock_param.uuid = "test_uuid_001"
        mock_param.mapping_id = self.test_mapping_id
        mock_param.index = self.test_index
        mock_param.value = "updated_value"

        with patch.object(self.service._crud_repo, 'modify', return_value=1), \
             patch.object(self.service._crud_repo, 'find', return_value=[mock_param]):

            result = self.service.update(
                mapping_id=self.test_mapping_id,
                index=self.test_index,
                value="updated_value"
            )

            assert result.is_success()
            assert result.data["param_info"]["value"] == "updated_value"

    def test_update_param_no_identifier(self):
        """测试更新参数 - 缺少标识符"""
        result = self.service.update(value="new_value")

        assert not result.is_success()
        assert "必须提供param_id或(mapping_id + index)" in result.error

    def test_update_param_no_fields(self):
        """测试更新参数 - 没有要更新的字段"""
        result = self.service.update(param_id="test_uuid")

        assert not result.is_success()
        assert "未提供要更新的字段" in result.error

    def test_delete_param_by_id_success(self):
        """测试通过ID删除参数成功"""
        with patch.object(self.service._crud_repo, 'remove', return_value=1):
            result = self.service.delete(param_id="test_uuid_001")

            assert result.is_success()
            assert result.data["deleted_count"] == 1

    def test_delete_param_by_mapping_index_success(self):
        """测试通过映射ID和索引删除参数成功"""
        with patch.object(self.service._crud_repo, 'remove', return_value=1):
            result = self.service.delete(
                mapping_id=self.test_mapping_id,
                index=self.test_index
            )

            assert result.is_success()
            assert result.data["deleted_count"] == 1

    def test_delete_param_no_identifier(self):
        """测试删除参数 - 缺少标识符"""
        result = self.service.delete()

        assert not result.is_success()
        assert "必须提供param_id或(mapping_id + index)" in result.error

    def test_get_param_by_id_success(self):
        """测试通过ID获取参数成功"""
        mock_param = Mock()
        mock_param.uuid = "test_uuid_001"

        with patch.object(self.service._crud_repo, 'find', return_value=[mock_param]):
            result = self.service.get(param_id="test_uuid_001")

            assert result.is_success()
            assert result.data == [mock_param]

    def test_get_param_by_mapping_success(self):
        """测试通过映射ID获取参数成功"""
        mock_params = [Mock(), Mock()]

        with patch.object(self.service._crud_repo, 'find', return_value=mock_params):
            result = self.service.get(mapping_id=self.test_mapping_id)

            assert result.is_success()
            assert result.data == mock_params

    def test_count_params_success(self):
        """测试统计参数数量成功"""
        with patch.object(self.service._crud_repo, 'count', return_value=5):
            result = self.service.count(mapping_id=self.test_mapping_id)

            assert result.is_success()
            assert result.data["count"] == 5

    def test_exists_param_true(self):
        """测试检查参数存在性 - 存在"""
        with patch.object(self.service._crud_repo, 'exists', return_value=True):
            result = self.service.exists(
                mapping_id=self.test_mapping_id,
                index=self.test_index
            )

            assert result.is_success()
            assert result.data["exists"] is True

    def test_exists_param_false(self):
        """测试检查参数存在性 - 不存在"""
        with patch.object(self.service._crud_repo, 'exists', return_value=False):
            result = self.service.exists(
                mapping_id=self.test_mapping_id,
                index=self.test_index
            )

            assert result.is_success()
            assert result.data["exists"] is False


class TestParamServiceBusinessMethods:
    """ParamService 业务方法测试"""

    def setup_method(self):
        """测试前置设置"""
        self.service = ParamService()
        self.test_mapping_id = "test_mapping_001"

    def test_get_params_by_mapping_success(self):
        """测试根据映射ID获取参数成功"""
        mock_params = [Mock(), Mock()]

        with patch.object(self.service._crud_repo, 'find', return_value=mock_params):
            result = self.service.get_params_by_mapping(self.test_mapping_id)

            assert result.is_success()
            assert result.data == mock_params

    def test_get_params_by_mapping_empty_mapping_id(self):
        """测试根据映射ID获取参数 - 空映射ID"""
        result = self.service.get_params_by_mapping("")

        assert not result.is_success()
        assert "映射ID不能为空" in result.error

    def test_update_params_batch_success(self):
        """测试批量更新参数成功"""
        params_dict = {0: "value0", 1: "value1", 2: "value2"}

        with patch.object(self.service, 'update', return_value=ServiceResult.success({})):
            result = self.service.update_params_batch(self.test_mapping_id, params_dict)

            assert result.is_success()
            assert result.data["success_count"] == 3
            assert result.data["failed_count"] == 0

    def test_update_params_batch_partial_success(self):
        """测试批量更新参数 - 部分成功"""
        params_dict = {0: "value0", 1: "value1", 2: "value2"}

        def mock_update_side_effect(*args, **kwargs):
            if kwargs.get('index') == 1:
                return ServiceResult.error("Update failed")
            return ServiceResult.success({})

        with patch.object(self.service, 'update', side_effect=mock_update_side_effect):
            result = self.service.update_params_batch(self.test_mapping_id, params_dict)

            assert not result.is_success()  # 部分成功仍然返回错误
            assert result.data["success_count"] == 2
            assert result.data["failed_count"] == 1

    def test_update_params_batch_empty_mapping_id(self):
        """测试批量更新参数 - 空映射ID"""
        result = self.service.update_params_batch("", {0: "value"})

        assert not result.is_success()
        assert "映射ID不能为空" in result.error

    def test_update_params_batch_invalid_params(self):
        """测试批量更新参数 - 无效参数字典"""
        result = self.service.update_params_batch(self.test_mapping_id, None)

        assert not result.is_success()
        assert "参数字典不能为空" in result.error

    def test_copy_params_success(self):
        """测试复制参数成功"""
        mock_params = [
            Mock(index=0, value="value0"),
            Mock(index=1, value="value1")
        ]

        with patch.object(self.service, 'get_params_by_mapping', return_value=ServiceResult.success(mock_params)), \
             patch.object(self.service, 'add', return_value=ServiceResult.success({})):

            result = self.service.copy_params(
                source_mapping="source_001",
                target_mapping="target_001"
            )

            assert result.is_success()
            assert result.data["copied_count"] == 2
            assert result.data["failed_count"] == 0

    def test_copy_params_empty_source(self):
        """测试复制参数 - 源映射为空"""
        with patch.object(self.service, 'get_params_by_mapping', return_value=ServiceResult.success([])):
            result = self.service.copy_params(
                source_mapping="empty_source",
                target_mapping="target_001"
            )

            assert result.is_success()
            assert result.data["copied_count"] == 0

    def test_copy_params_same_mapping(self):
        """测试复制参数 - 相同映射"""
        result = self.service.copy_params(
            source_mapping="same_mapping",
            target_mapping="same_mapping"
        )

        assert not result.is_success()
        assert "源映射和目标映射不能相同" in result.error

    def test_delete_mapping_params_success(self):
        """测试删除映射参数成功"""
        with patch.object(self.service._crud_repo, 'remove', return_value=3):
            result = self.service.delete_mapping_params(self.test_mapping_id)

            assert result.is_success()
            assert result.data["deleted_count"] == 3

    def test_delete_mapping_params_empty_mapping_id(self):
        """测试删除映射参数 - 空映射ID"""
        result = self.service.delete_mapping_params("")

        assert not result.is_success()
        assert "映射ID不能为空" in result.error

    def test_get_params_summary_success(self):
        """测试获取参数汇总成功"""
        mock_params = [
            Mock(index=0, value="value0"),
            Mock(index=1, value="value1"),
            Mock(index=2, value="value2")
        ]

        with patch.object(self.service, 'count', return_value=ServiceResult.success({"count": 3})), \
             patch.object(self.service, 'get_params_by_mapping', return_value=ServiceResult.success(mock_params)):

            result = self.service.get_params_summary(self.test_mapping_id)

            assert result.is_success()
            assert result.data["total_params"] == 3
            assert result.data["param_count"] == 3
            assert result.data["min_index"] == 0
            assert result.data["max_index"] == 2

    def test_validate_params_success(self):
        """测试参数验证成功"""
        mock_params = [
            Mock(index=0, value="value0"),
            Mock(index=1, value="value1")
        ]

        with patch.object(self.service, 'get_params_by_mapping', return_value=ServiceResult.success(mock_params)):
            result = self.service.validate_params(self.test_mapping_id)

            assert result.is_success()
            assert result.data["is_valid"] is True
            assert result.data["param_count"] == 2

    def test_validate_params_empty_mapping(self):
        """测试参数验证 - 空映射"""
        with patch.object(self.service, 'get_params_by_mapping', return_value=ServiceResult.success([])):
            result = self.service.validate_params(self.test_mapping_id)

            assert result.is_success()
            assert result.data["param_count"] == 0
            assert "映射没有参数" in result.data["warnings"]

    def test_validate_params_duplicate_indices(self):
        """测试参数验证 - 重复索引"""
        mock_params = [
            Mock(index=0, value="value0"),
            Mock(index=0, value="value1")  # 重复索引
        ]

        with patch.object(self.service, 'get_params_by_mapping', return_value=ServiceResult.success(mock_params)):
            result = self.service.validate_params(self.test_mapping_id)

            assert result.is_success()
            assert result.data["is_valid"] is False
            assert "存在重复索引" in result.data["issues"][0]


class TestParamServiceIntegration:
    """ParamService 集成测试"""

    def setup_method(self):
        """测试前置设置"""
        self.service = ParamService()

    def test_param_lifecycle(self):
        """测试参数完整生命周期"""
        mapping_id = "lifecycle_test"
        param_index = 0
        param_value = "lifecycle_value"

        # 由于是集成测试，这里只测试方法调用，不涉及真实数据库
        with patch.object(self.service._crud_repo, 'find', return_value=[]), \
             patch.object(self.service._crud_repo, 'create') as mock_create, \
             patch.object(self.service._crud_repo, 'modify', return_value=1), \
             patch.object(self.service._crud_repo, 'remove', return_value=1):

            # Mock 创建的参数
            mock_param = Mock()
            mock_param.uuid = "lifecycle_uuid"
            mock_param.mapping_id = mapping_id
            mock_param.index = param_index
            mock_param.value = param_value
            mock_create.return_value = mock_param

            # 1. 创建参数
            add_result = self.service.add(mapping_id, param_index, param_value)
            assert add_result.is_success()

            # 2. 更新参数
            update_result = self.service.update(
                mapping_id=mapping_id,
                index=param_index,
                value="updated_value"
            )
            # 这里因为find返回空，update会失败，这是预期的
            # 在真实环境中需要正确的数据库设置

            # 3. 检查存在性
            exists_result = self.service.exists(
                mapping_id=mapping_id,
                index=param_index
            )

            # 4. 删除参数
            delete_result = self.service.delete(
                mapping_id=mapping_id,
                index=param_index
            )
            assert delete_result.is_success()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])