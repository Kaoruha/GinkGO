"""
UserGroupMappingCRUD 单元测试（Mock 数据库连接）

覆盖范围：
- _get_field_config: 字段配置（user_uuid, group_uuid）
- _get_enum_mappings: 枚举映射（SOURCE_TYPES）
- _create_from_params: 参数转 MUserGroupMapping 模型
- Business Helper: find_by_user, check_mapping_exists
- 构造与类型检查
"""

import pytest
from unittest.mock import MagicMock, patch

from ginkgo.enums import SOURCE_TYPES


# ============================================================
# 辅助：构造 UserGroupMappingCRUD 实例（mock DB 连接）
# ============================================================


@pytest.fixture
def crud_instance():
    """构造 UserGroupMappingCRUD 实例，mock 掉 get_db_connection 避免真实数据库连接"""
    mock_logger = MagicMock()
    with patch("ginkgo.data.crud.base_crud.get_db_connection"), \
         patch("ginkgo.data.crud.base_crud.GLOG", mock_logger), \
         patch("ginkgo.data.crud.user_group_mapping_crud.GLOG", mock_logger), \
         patch("ginkgo.data.access_control.service_only", lambda f: f):
        from ginkgo.data.crud.user_group_mapping_crud import UserGroupMappingCRUD
        crud = UserGroupMappingCRUD()
        crud._logger = mock_logger
        return crud


# ============================================================
# _get_field_config 测试
# ============================================================


class TestUserGroupMappingCRUDFieldConfig:
    """_get_field_config 字段配置测试"""

    @pytest.mark.unit
    def test_field_config_has_required_keys(self, crud_instance):
        """配置包含 user_uuid, group_uuid"""
        config = crud_instance._get_field_config()

        required_keys = {"user_uuid", "group_uuid"}
        assert required_keys.issubset(set(config.keys())), \
            f"缺少字段: {required_keys - set(config.keys())}"

    @pytest.mark.unit
    def test_field_config_user_uuid_validation(self, crud_instance):
        """user_uuid 字段为 string 类型，min=1, max=32"""
        config = crud_instance._get_field_config()

        assert config["user_uuid"]["type"] == "string"
        assert config["user_uuid"]["min"] == 1
        assert config["user_uuid"]["max"] == 32

    @pytest.mark.unit
    def test_field_config_group_uuid_validation(self, crud_instance):
        """group_uuid 字段为 string 类型，min=1, max=32"""
        config = crud_instance._get_field_config()

        assert config["group_uuid"]["type"] == "string"
        assert config["group_uuid"]["min"] == 1
        assert config["group_uuid"]["max"] == 32


# ============================================================
# _get_enum_mappings 测试
# ============================================================


class TestUserGroupMappingCRUDEnumMappings:
    """_get_enum_mappings 枚举映射测试"""

    @pytest.mark.unit
    def test_enum_mappings_has_source(self, crud_instance):
        """映射包含 source 枚举"""
        mappings = crud_instance._get_enum_mappings()

        assert "source" in mappings
        assert mappings["source"] is SOURCE_TYPES


# ============================================================
# _create_from_params 测试
# ============================================================


class TestUserGroupMappingCRUDCreateFromParams:
    """_create_from_params 参数转模型测试"""

    @pytest.mark.unit
    def test_create_from_params_basic(self, crud_instance):
        """传入完整参数，返回 MUserGroupMapping 模型且属性正确"""
        from ginkgo.data.models import MUserGroupMapping

        params = {"user_uuid": "user-001", "group_uuid": "group-001"}

        model = crud_instance._create_from_params(**params)

        assert isinstance(model, MUserGroupMapping)
        assert model.user_uuid == "user-001"
        assert model.group_uuid == "group-001"

    @pytest.mark.unit
    def test_create_from_params_missing_user_uuid_raises(self, crud_instance):
        """缺少 user_uuid 时抛出 ValueError"""
        with pytest.raises(ValueError, match="user_uuid"):
            crud_instance._create_from_params(group_uuid="group-001")

    @pytest.mark.unit
    def test_create_from_params_missing_group_uuid_raises(self, crud_instance):
        """缺少 group_uuid 时抛出 ValueError"""
        with pytest.raises(ValueError, match="group_uuid"):
            crud_instance._create_from_params(user_uuid="user-001")


# ============================================================
# Business Helper 测试
# ============================================================


class TestUserGroupMappingCRUDBusinessHelpers:
    """Business Helper 方法测试"""

    @pytest.mark.unit
    def test_find_by_user(self, crud_instance):
        """find_by_user 构造正确的 filters 并调用 self.find"""
        crud_instance.find = MagicMock(return_value=[])

        crud_instance.find_by_user(user_uuid="user-001")

        crud_instance.find.assert_called_once()
        call_kwargs = crud_instance.find.call_args[1]
        assert call_kwargs["filters"]["user_uuid"] == "user-001"
        assert call_kwargs["as_dataframe"] is False

    @pytest.mark.unit
    def test_check_mapping_exists_true(self, crud_instance):
        """check_mapping_exists 存在映射时返回 True"""
        mock_mapping = MagicMock()
        crud_instance.find = MagicMock(return_value=[mock_mapping])

        result = crud_instance.check_mapping_exists(user_uuid="user-001", group_uuid="group-001")

        assert result is True
        call_kwargs = crud_instance.find.call_args[1]
        assert call_kwargs["filters"]["user_uuid"] == "user-001"
        assert call_kwargs["filters"]["group_uuid"] == "group-001"
        assert call_kwargs["page_size"] == 1

    @pytest.mark.unit
    def test_check_mapping_exists_false(self, crud_instance):
        """check_mapping_exists 不存在映射时返回 False"""
        crud_instance.find = MagicMock(return_value=[])

        result = crud_instance.check_mapping_exists(user_uuid="user-001", group_uuid="group-001")

        assert result is False


# ============================================================
# 构造与类型检查测试
# ============================================================


class TestUserGroupMappingCRUDConstruction:
    """UserGroupMappingCRUD 构造和类型检查测试"""

    @pytest.mark.unit
    def test_construction(self, crud_instance):
        """验证 model_class 为 MUserGroupMapping，_is_mysql 为 True"""
        from ginkgo.data.models import MUserGroupMapping

        assert crud_instance.model_class is MUserGroupMapping
        assert crud_instance._is_mysql is True
        assert crud_instance._is_clickhouse is False
