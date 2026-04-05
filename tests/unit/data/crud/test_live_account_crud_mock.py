"""
LiveAccountCRUD 单元测试（Mock 数据库连接）

覆盖范围：
- _get_field_config: 字段配置（exchange, environment, name, api_key, api_secret, passphrase, status）
- _get_enum_mappings: 枚举映射（SOURCE_TYPES）
- _create_from_params: 参数转 MLiveAccount 模型
- Business Helper: get_live_account_by_uuid, update_status
- 构造与类型检查
"""

import pytest
from unittest.mock import MagicMock, patch

from ginkgo.enums import SOURCE_TYPES


# ============================================================
# 辅助：构造 LiveAccountCRUD 实例（mock DB 连接）
# ============================================================


@pytest.fixture
def crud_instance():
    """构造 LiveAccountCRUD 实例，mock 掉 get_db_connection 避免真实数据库连接"""
    mock_logger = MagicMock()
    with patch("ginkgo.data.crud.base_crud.get_db_connection"), \
         patch("ginkgo.data.crud.base_crud.GLOG", mock_logger), \
         patch("ginkgo.data.crud.live_account_crud.GLOG", mock_logger), \
         patch("ginkgo.data.access_control.service_only", lambda f: f):
        from ginkgo.data.crud.live_account_crud import LiveAccountCRUD
        crud = LiveAccountCRUD()
        crud._logger = mock_logger
        return crud


# ============================================================
# _get_field_config 测试
# ============================================================


class TestLiveAccountCRUDFieldConfig:
    """_get_field_config 字段配置测试"""

    @pytest.mark.unit
    def test_field_config_has_required_keys(self, crud_instance):
        """配置包含 exchange, environment, name, api_key, api_secret, passphrase, status"""
        config = crud_instance._get_field_config()

        required_keys = {"exchange", "environment", "name", "api_key", "api_secret", "passphrase", "status"}
        assert required_keys.issubset(set(config.keys())), \
            f"缺少字段: {required_keys - set(config.keys())}"

    @pytest.mark.unit
    def test_field_config_name_validation(self, crud_instance):
        """name 字段为 string 类型，min=1, max=100"""
        config = crud_instance._get_field_config()

        assert config["name"]["type"] == "string"
        assert config["name"]["min"] == 1
        assert config["name"]["max"] == 100

    @pytest.mark.unit
    def test_field_config_passphrase_optional(self, crud_instance):
        """passphrase 字段为可选"""
        config = crud_instance._get_field_config()

        assert config["passphrase"]["type"] == "string"
        assert config["passphrase"]["required"] is False


# ============================================================
# _get_enum_mappings 测试
# ============================================================


class TestLiveAccountCRUDEnumMappings:
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


class TestLiveAccountCRUDCreateFromParams:
    """_create_from_params 参数转模型测试"""

    @pytest.mark.unit
    def test_create_from_params_basic(self, crud_instance):
        """传入完整参数，返回 MLiveAccount 模型"""
        from ginkgo.data.models.model_live_account import MLiveAccount

        params = {
            "user_id": "user-001",
            "exchange": "okx",
            "name": "测试账号",
            "api_key": "key-xxx",
            "api_secret": "secret-xxx",
        }

        model = crud_instance._create_from_params(**params)

        assert isinstance(model, MLiveAccount)
        assert model.user_id == "user-001"
        assert model.exchange == "okx"
        assert model.name == "测试账号"


# ============================================================
# Business Helper 测试
# ============================================================


class TestLiveAccountCRUDBusinessHelpers:
    """Business Helper 方法测试"""

    @pytest.mark.unit
    def test_get_live_account_by_uuid(self, crud_instance):
        """get_live_account_by_uuid 构造正确的 filters 并调用 self.find"""
        crud_instance.find = MagicMock(return_value=[])

        result = crud_instance.get_live_account_by_uuid(uuid="account-uuid-001")

        crud_instance.find.assert_called_once()
        call_kwargs = crud_instance.find.call_args[1]
        assert call_kwargs["filters"]["uuid"] == "account-uuid-001"
        assert call_kwargs["filters"]["is_del"] is False
        assert result is None

    @pytest.mark.unit
    def test_update_status(self, crud_instance):
        """update_status 调用 self.modify 更新状态"""
        # 先 mock find 返回一个模拟账号
        mock_account = MagicMock()
        mock_account.status = "disabled"
        crud_instance.find = MagicMock(return_value=[mock_account])
        crud_instance.modify = MagicMock(return_value=1)

        result = crud_instance.update_status(uuid="account-uuid-001", status="enabled")

        crud_instance.find.assert_called()
        crud_instance.modify.assert_called_once()
        call_kwargs = crud_instance.modify.call_args[1]
        assert call_kwargs["filters"]["uuid"] == "account-uuid-001"
        assert call_kwargs["updates"]["status"] == "enabled"


# ============================================================
# 构造与类型检查测试
# ============================================================


class TestLiveAccountCRUDConstruction:
    """LiveAccountCRUD 构造和类型检查测试"""

    @pytest.mark.unit
    def test_construction(self, crud_instance):
        """验证 model_class 为 MLiveAccount，_is_mysql 为 True"""
        from ginkgo.data.models.model_live_account import MLiveAccount

        assert crud_instance.model_class is MLiveAccount
        assert crud_instance._is_mysql is True
        assert crud_instance._is_clickhouse is False

    @pytest.mark.unit
    def test_has_required_methods(self, crud_instance):
        """验证 BaseCRUD 的关键 hook 方法都存在且可调用"""
        required_methods = [
            "_do_add", "_do_find", "_do_modify", "_do_remove", "_do_count",
            "_get_field_config", "_get_enum_mappings", "_create_from_params",
            "_convert_input_item",
        ]

        for method_name in required_methods:
            assert hasattr(crud_instance, method_name), f"缺少方法: {method_name}"
            assert callable(getattr(crud_instance, method_name)), f"不可调用: {method_name}"
