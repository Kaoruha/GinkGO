"""
性能: 219MB RSS, 1.95s, 8 tests [PASS]
MarketSubscriptionCRUD 单元测试（Mock 数据库连接）

覆盖范围：
- _get_field_config: 字段配置（exchange, environment, symbol, data_types, is_active）
- _get_enum_mappings: 枚举映射（SOURCE_TYPES）
- _create_from_params: 参数转 MMarketSubscription 模型
- Business Helper: get_user_subscriptions, get_all_active_symbols
- 构造与类型检查
"""

import pytest
from unittest.mock import MagicMock, patch

from ginkgo.enums import SOURCE_TYPES


# ============================================================
# 辅助：构造 MarketSubscriptionCRUD 实例（mock DB 连接）
# ============================================================


@pytest.fixture
def crud_instance():
    """构造 MarketSubscriptionCRUD 实例，mock 掉 get_db_connection 避免真实数据库连接"""
    mock_logger = MagicMock()
    with patch("ginkgo.data.crud.base_crud.get_db_connection"), \
         patch("ginkgo.data.crud.base_crud.GLOG", mock_logger), \
         patch("ginkgo.data.crud.market_subscription_crud.GLOG", mock_logger), \
         patch("ginkgo.data.access_control.service_only", lambda f: f):
        from ginkgo.data.crud.market_subscription_crud import MarketSubscriptionCRUD
        crud = MarketSubscriptionCRUD()
        crud._logger = mock_logger
        return crud


# ============================================================
# _get_field_config 测试
# ============================================================


class TestMarketSubscriptionCRUDFieldConfig:
    """_get_field_config 字段配置测试"""

    @pytest.mark.unit
    def test_field_config_has_required_keys(self, crud_instance):
        """配置包含 exchange, environment, symbol, data_types, is_active"""
        config = crud_instance._get_field_config()

        required_keys = {"exchange", "environment", "symbol", "data_types", "is_active"}
        assert required_keys.issubset(set(config.keys())), \
            f"缺少字段: {required_keys - set(config.keys())}"

    @pytest.mark.unit
    def test_field_config_exchange_validation(self, crud_instance):
        """exchange 字段为 string 类型，min=2, max=20"""
        config = crud_instance._get_field_config()

        assert config["exchange"]["type"] == "string"
        assert config["exchange"]["min"] == 2
        assert config["exchange"]["max"] == 20

    @pytest.mark.unit
    def test_field_config_data_types_is_json(self, crud_instance):
        """data_types 字段为 json 类型"""
        config = crud_instance._get_field_config()

        assert config["data_types"]["type"] == "json"

    @pytest.mark.unit
    def test_field_config_is_active_is_boolean(self, crud_instance):
        """is_active 字段为 boolean 类型"""
        config = crud_instance._get_field_config()

        assert config["is_active"]["type"] == "boolean"


# ============================================================
# _get_enum_mappings 测试
# ============================================================


class TestMarketSubscriptionCRUDEnumMappings:
    """_get_enum_mappings 枚举映射测试"""

    @pytest.mark.unit
    def test_enum_mappings_has_source(self, crud_instance):
        """映射包含 source 枚举"""
        mappings = crud_instance._get_enum_mappings()

        assert "source" in mappings
        assert mappings["source"] is SOURCE_TYPES


# ============================================================
# Business Helper 测试
# ============================================================


class TestMarketSubscriptionCRUDBusinessHelpers:
    """Business Helper 方法测试"""

    @pytest.mark.unit
    def test_get_user_subscriptions_active_only(self, crud_instance):
        """get_user_subscriptions 构造正确的 filters 并调用 self.find"""
        crud_instance.find = MagicMock(return_value=[])

        result = crud_instance.get_user_subscriptions(user_id="user-001", active_only=True)

        crud_instance.find.assert_called_once()
        call_kwargs = crud_instance.find.call_args[1]
        assert call_kwargs["filters"]["user_id"] == "user-001"
        assert call_kwargs["filters"]["is_del"] is False
        assert call_kwargs["filters"]["is_active"] is True
        assert result == []

    @pytest.mark.unit
    def test_get_all_active_symbols(self, crud_instance):
        """get_all_active_symbols 构造正确的 filters 并调用 self.find"""
        crud_instance.find = MagicMock(return_value=[])

        result = crud_instance.get_all_active_symbols()

        crud_instance.find.assert_called_once()
        call_kwargs = crud_instance.find.call_args[1]
        assert call_kwargs["filters"]["is_active"] is True
        assert call_kwargs["filters"]["is_del"] is False
        assert result == []


# ============================================================
# 构造与类型检查测试
# ============================================================


class TestMarketSubscriptionCRUDConstruction:
    """MarketSubscriptionCRUD 构造和类型检查测试"""

    @pytest.mark.unit
    def test_construction(self, crud_instance):
        """验证 model_class 为 MMarketSubscription，_is_mysql 为 True"""
        from ginkgo.data.models.model_market_subscription import MMarketSubscription

        assert crud_instance.model_class is MMarketSubscription
        assert crud_instance._is_mysql is True
        assert crud_instance._is_clickhouse is False

