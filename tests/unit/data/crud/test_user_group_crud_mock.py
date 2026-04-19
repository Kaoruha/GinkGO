"""
性能: 220MB RSS, 1.88s, 8 tests [PASS]
UserGroupCRUD 单元测试（Mock 数据库连接）

覆盖范围：
- _get_field_config: 字段配置（name, description）
- _get_enum_mappings: 枚举映射（SOURCE_TYPES）
- _create_from_params: 参数转 MUserGroup 模型
- Business Helper: find_by_name_pattern
- 构造与类型检查
"""

import pytest
from unittest.mock import MagicMock, patch

from ginkgo.enums import SOURCE_TYPES


# ============================================================
# 辅助：构造 UserGroupCRUD 实例（mock DB 连接）
# ============================================================


@pytest.fixture
def crud_instance():
    """构造 UserGroupCRUD 实例，mock 掉 get_db_connection 避免真实数据库连接"""
    mock_logger = MagicMock()
    with patch("ginkgo.data.crud.base_crud.get_db_connection"), \
         patch("ginkgo.data.crud.base_crud.GLOG", mock_logger), \
         patch("ginkgo.data.crud.user_group_crud.GLOG", mock_logger), \
         patch("ginkgo.data.access_control.service_only", lambda f: f):
        from ginkgo.data.crud.user_group_crud import UserGroupCRUD
        crud = UserGroupCRUD()
        crud._logger = mock_logger
        return crud


# ============================================================
# _get_field_config 测试
# ============================================================


class TestUserGroupCRUDFieldConfig:
    """_get_field_config 字段配置测试"""

    @pytest.mark.unit
    def test_field_config_has_required_keys(self, crud_instance):
        """配置包含 name, description"""
        config = crud_instance._get_field_config()

        required_keys = {"name", "description"}
        assert required_keys.issubset(set(config.keys())), \
            f"缺少字段: {required_keys - set(config.keys())}"

    @pytest.mark.unit
    def test_field_config_name_validation(self, crud_instance):
        """name 字段为 string 类型，min=1, max=128"""
        config = crud_instance._get_field_config()

        assert config["name"]["type"] == "string"
        assert config["name"]["min"] == 1
        assert config["name"]["max"] == 128

    @pytest.mark.unit
    def test_field_config_description_validation(self, crud_instance):
        """description 字段为 string 类型，max=512"""
        config = crud_instance._get_field_config()

        assert config["description"]["type"] == "string"
        assert config["description"]["max"] == 512


# ============================================================
# _get_enum_mappings 测试
# ============================================================


class TestUserGroupCRUDEnumMappings:
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


class TestUserGroupCRUDCreateFromParams:
    """_create_from_params 参数转模型测试"""

    @pytest.mark.unit
    def test_create_from_params_basic(self, crud_instance):
        """传入完整参数，返回 MUserGroup 模型且属性正确"""
        from ginkgo.data.models import MUserGroup

        params = {"name": "traders"}

        model = crud_instance._create_from_params(**params)

        assert isinstance(model, MUserGroup)
        assert model.name == "traders"

    @pytest.mark.unit
    def test_create_from_params_missing_name_raises(self, crud_instance):
        """缺少 name 时抛出 ValueError"""
        with pytest.raises(ValueError, match="name"):
            crud_instance._create_from_params()


# ============================================================
# Business Helper 测试
# ============================================================


class TestUserGroupCRUDBusinessHelpers:
    """Business Helper 方法测试"""

    @pytest.mark.unit
    def test_find_by_name_pattern(self, crud_instance):
        """find_by_name_pattern 构造正确的 filters 并调用 self.find"""
        crud_instance.find = MagicMock(return_value=[])

        crud_instance.find_by_name_pattern(name_pattern="%trader%")

        crud_instance.find.assert_called_once()
        call_kwargs = crud_instance.find.call_args[1]
        assert call_kwargs["filters"]["name__like"] == "%trader%"


# ============================================================
# 构造与类型检查测试
# ============================================================


class TestUserGroupCRUDConstruction:
    """UserGroupCRUD 构造和类型检查测试"""

    @pytest.mark.unit
    def test_construction(self, crud_instance):
        """验证 model_class 为 MUserGroup，_is_mysql 为 True"""
        from ginkgo.data.models import MUserGroup

        assert crud_instance.model_class is MUserGroup
        assert crud_instance._is_mysql is True
        assert crud_instance._is_clickhouse is False
