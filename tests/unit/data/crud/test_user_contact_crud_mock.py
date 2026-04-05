"""
UserContactCRUD 单元测试（Mock 数据库连接）

覆盖范围：
- _get_field_config: 字段配置（contact_type, user_id, address, is_primary, is_active）
- _get_enum_mappings: 枚举映射（CONTACT_TYPES, SOURCE_TYPES）
- _create_from_params: 参数转 MUserContact 模型
- Business Helper: get_by_user, find_by_contact_type
- 构造与类型检查
"""

import pytest
from unittest.mock import MagicMock, patch

from ginkgo.enums import SOURCE_TYPES, CONTACT_TYPES


# ============================================================
# 辅助：构造 UserContactCRUD 实例（mock DB 连接）
# ============================================================


@pytest.fixture
def crud_instance():
    """构造 UserContactCRUD 实例，mock 掉 get_db_connection 避免真实数据库连接"""
    mock_logger = MagicMock()
    with patch("ginkgo.data.crud.base_crud.get_db_connection"), \
         patch("ginkgo.data.crud.base_crud.GLOG", mock_logger), \
         patch("ginkgo.data.crud.user_contact_crud.GLOG", mock_logger), \
         patch("ginkgo.data.access_control.service_only", lambda f: f):
        from ginkgo.data.crud.user_contact_crud import UserContactCRUD
        crud = UserContactCRUD()
        crud._logger = mock_logger
        return crud


# ============================================================
# _get_field_config 测试
# ============================================================


class TestUserContactCRUDFieldConfig:
    """_get_field_config 字段配置测试"""

    @pytest.mark.unit
    def test_field_config_has_required_keys(self, crud_instance):
        """配置包含 contact_type, user_id, address, is_primary, is_active"""
        config = crud_instance._get_field_config()

        required_keys = {"contact_type", "user_id", "address", "is_primary", "is_active"}
        assert required_keys.issubset(set(config.keys())), \
            f"缺少字段: {required_keys - set(config.keys())}"

    @pytest.mark.unit
    def test_field_config_contact_type_is_enum(self, crud_instance):
        """contact_type 字段为枚举类型"""
        config = crud_instance._get_field_config()

        assert config["contact_type"]["type"] == "enum"

    @pytest.mark.unit
    def test_field_config_user_id_validation(self, crud_instance):
        """user_id 字段为 string 类型，min=1, max=32"""
        config = crud_instance._get_field_config()

        assert config["user_id"]["type"] == "string"
        assert config["user_id"]["min"] == 1
        assert config["user_id"]["max"] == 32


# ============================================================
# _get_enum_mappings 测试
# ============================================================


class TestUserContactCRUDEnumMappings:
    """_get_enum_mappings 枚举映射测试"""

    @pytest.mark.unit
    def test_enum_mappings_has_two_enums(self, crud_instance):
        """映射包含 contact_type 和 source 两个枚举"""
        mappings = crud_instance._get_enum_mappings()

        assert "contact_type" in mappings
        assert "source" in mappings
        assert mappings["contact_type"] is CONTACT_TYPES
        assert mappings["source"] is SOURCE_TYPES


# ============================================================
# _create_from_params 测试
# ============================================================


class TestUserContactCRUDCreateFromParams:
    """_create_from_params 参数转模型测试"""

    @pytest.mark.unit
    def test_create_from_params_basic(self, crud_instance):
        """传入完整参数，返回 MUserContact 模型且属性正确"""
        from ginkgo.data.models import MUserContact

        params = {
            "user_id": "user-001",
            "contact_type": CONTACT_TYPES.EMAIL,
            "address": "test@example.com",
        }

        model = crud_instance._create_from_params(**params)

        assert isinstance(model, MUserContact)
        assert model.user_id == "user-001"
        assert model.address == "test@example.com"

    @pytest.mark.unit
    def test_create_from_params_missing_user_id_raises(self, crud_instance):
        """缺少 user_id 时抛出 ValueError"""
        with pytest.raises(ValueError, match="user_id"):
            crud_instance._create_from_params(contact_type=CONTACT_TYPES.EMAIL)


# ============================================================
# Business Helper 测试
# ============================================================


class TestUserContactCRUDBusinessHelpers:
    """Business Helper 方法测试"""

    @pytest.mark.unit
    def test_get_by_user(self, crud_instance):
        """get_by_user 构造正确的 filters 并调用 self.find"""
        crud_instance.find = MagicMock(return_value=[])

        crud_instance.get_by_user(user_id="user-001")

        crud_instance.find.assert_called_once()
        call_kwargs = crud_instance.find.call_args[1]
        assert call_kwargs["filters"]["user_id"] == "user-001"
        assert call_kwargs["as_dataframe"] is False

    @pytest.mark.unit
    def test_get_by_user_with_active_filter(self, crud_instance):
        """get_by_user 传入 is_active 过滤"""
        crud_instance.find = MagicMock(return_value=[])

        crud_instance.get_by_user(user_id="user-001", is_active=True)

        call_kwargs = crud_instance.find.call_args[1]
        assert call_kwargs["filters"]["is_active"] is True

    @pytest.mark.unit
    def test_find_by_contact_type(self, crud_instance):
        """find_by_contact_type 构造正确的 filters 并调用 self.find"""
        crud_instance.find = MagicMock(return_value=[])

        crud_instance.find_by_contact_type(contact_type=CONTACT_TYPES.EMAIL)

        crud_instance.find.assert_called_once()
        call_kwargs = crud_instance.find.call_args[1]
        assert "contact_type" in call_kwargs["filters"]


# ============================================================
# 构造与类型检查测试
# ============================================================


class TestUserContactCRUDConstruction:
    """UserContactCRUD 构造和类型检查测试"""

    @pytest.mark.unit
    def test_construction(self, crud_instance):
        """验证 model_class 为 MUserContact，_is_mysql 为 True"""
        from ginkgo.data.models import MUserContact

        assert crud_instance.model_class is MUserContact
        assert crud_instance._is_mysql is True
        assert crud_instance._is_clickhouse is False
