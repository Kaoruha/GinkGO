"""
FactorCRUD 单元测试（Mock 数据库连接）

覆盖范围：
- _get_field_config: 字段配置结构与验证规则
- _get_enum_mappings: 枚举映射（ENTITY_TYPES, SOURCE_TYPES）
- _create_from_params: 参数转 MFactor 模型
- Business Helper: get_factors_by_entity, get_available_entities
- 构造与类型检查
"""

import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

from ginkgo.enums import ENTITY_TYPES, SOURCE_TYPES


# ============================================================
# 辅助：构造 FactorCRUD 实例（mock DB 连接）
# ============================================================


@pytest.fixture
def factor_crud():
    """构造 FactorCRUD 实例，mock 掉 get_db_connection 避免真实数据库连接"""
    mock_logger = MagicMock()
    with patch("ginkgo.data.crud.base_crud.get_db_connection"), \
         patch("ginkgo.data.crud.base_crud.GLOG", mock_logger), \
         patch("ginkgo.data.crud.factor_crud.GLOG", mock_logger), \
         patch("ginkgo.data.access_control.service_only", lambda f: f):
        from ginkgo.data.crud.factor_crud import FactorCRUD
        crud = FactorCRUD()
        crud._logger = mock_logger
        return crud


# ============================================================
# _get_field_config 测试
# ============================================================


class TestFactorCRUDFieldConfig:
    """_get_field_config 字段配置测试"""

    @pytest.mark.unit
    def test_field_config_has_required_keys(self, factor_crud):
        """配置包含 entity_type/entity_id/factor_name/factor_value/factor_category"""
        config = factor_crud._get_field_config()

        required_keys = {
            "entity_type", "entity_id", "factor_name",
            "factor_value", "factor_category",
        }
        assert required_keys.issubset(set(config.keys())), \
            f"缺少字段: {required_keys - set(config.keys())}"

    @pytest.mark.unit
    def test_field_config_entity_id_is_string(self, factor_crud):
        """entity_id 字段类型为 string，min=1"""
        config = factor_crud._get_field_config()

        assert config["entity_id"]["type"] == "string"
        assert config["entity_id"]["min"] == 1

    @pytest.mark.unit
    def test_field_config_factor_value_is_numeric(self, factor_crud):
        """factor_value 字段支持 decimal/float/int"""
        config = factor_crud._get_field_config()

        assert isinstance(config["factor_value"]["type"], list)

    @pytest.mark.unit
    def test_field_config_entity_type_is_enum(self, factor_crud):
        """entity_type 字段类型为 enum"""
        config = factor_crud._get_field_config()

        assert config["entity_type"]["type"] == "enum"
        assert ENTITY_TYPES.VOID not in config["entity_type"]["choices"]


# ============================================================
# _get_enum_mappings 测试
# ============================================================


class TestFactorCRUDEnumMappings:
    """_get_enum_mappings 枚举映射测试"""

    @pytest.mark.unit
    def test_enum_mappings_has_entity_type_and_source(self, factor_crud):
        """映射包含 entity_type 和 source 两个枚举"""
        mappings = factor_crud._get_enum_mappings()

        assert "entity_type" in mappings
        assert "source" in mappings
        assert mappings["entity_type"] is ENTITY_TYPES
        assert mappings["source"] is SOURCE_TYPES


# ============================================================
# _create_from_params 测试
# ============================================================


class TestFactorCRUDCreateFromParams:
    """_create_from_params 参数转模型测试"""

    @pytest.mark.unit
    def test_create_from_params_basic(self, factor_crud):
        """传入完整参数，返回 MFactor 模型且属性正确"""
        params = {
            "entity_type": ENTITY_TYPES.STOCK,
            "entity_id": "000001.SZ",
            "factor_name": "RSI",
            "factor_value": Decimal("65.5"),
            "factor_category": "technical",
            "timestamp": datetime(2024, 1, 15),
        }

        model = factor_crud._create_from_params(**params)

        assert model.entity_type == ENTITY_TYPES.STOCK.value
        assert model.entity_id == "000001.SZ"
        assert model.factor_name == "RSI"
        assert model.factor_value == Decimal("65.5")

    @pytest.mark.unit
    def test_create_from_params_defaults(self, factor_crud):
        """缺失字段使用默认值"""
        model = factor_crud._create_from_params()

        assert model.entity_id == ""
        assert model.factor_name == ""
        assert model.factor_category == ""

    @pytest.mark.unit
    def test_create_from_params_timestamp_normalized(self, factor_crud):
        """timestamp 经过 datetime_normalize 处理"""
        with patch("ginkgo.data.crud.factor_crud.datetime_normalize") as mock_normalize:
            mock_normalize.return_value = datetime(2024, 6, 1)

            model = factor_crud._create_from_params(timestamp="2024-06-01")

            mock_normalize.assert_called_once_with("2024-06-01")
            assert model.timestamp == datetime(2024, 6, 1)


# ============================================================
# Business Helper 测试
# ============================================================


class TestFactorCRUDBusinessHelpers:
    """Business Helper 方法测试"""

    @pytest.mark.unit
    def test_get_factors_by_entity_with_enum(self, factor_crud):
        """get_factors_by_entity 传入枚举类型构造正确 filters"""
        factor_crud.find = MagicMock(return_value=[])

        factor_crud.get_factors_by_entity(
            entity_type=ENTITY_TYPES.STOCK,
            entity_id="000001.SZ",
            factor_names=["RSI", "PE"],
        )

        factor_crud.find.assert_called_once()
        call_kwargs = factor_crud.find.call_args[1]
        assert call_kwargs["filters"]["entity_type"] == ENTITY_TYPES.STOCK.value
        assert call_kwargs["filters"]["entity_id"] == "000001.SZ"
        assert call_kwargs["filters"]["factor_name__in"] == ["RSI", "PE"]

    @pytest.mark.unit
    def test_get_available_entities_with_filter(self, factor_crud):
        """get_available_entities 传入 entity_type 过滤"""
        factor_crud.find = MagicMock(return_value=["000001.SZ", "600000.SH"])

        result = factor_crud.get_available_entities(entity_type=ENTITY_TYPES.STOCK)

        assert result == ["000001.SZ", "600000.SH"]
        call_kwargs = factor_crud.find.call_args[1]
        assert call_kwargs["filters"]["entity_type"] == ENTITY_TYPES.STOCK.value
        assert call_kwargs["distinct_field"] == "entity_id"


# ============================================================
# 构造与类型检查测试
# ============================================================


class TestFactorCRUDConstruction:
    """FactorCRUD 构造和类型检查测试"""

    @pytest.mark.unit
    def test_factor_crud_construction(self, factor_crud):
        """验证 model_class 为 MFactor，_is_clickhouse 为 True"""
        from ginkgo.data.models import MFactor

        assert factor_crud.model_class is MFactor
        assert factor_crud._is_clickhouse is True
        assert factor_crud._is_mysql is False

    @pytest.mark.unit
    def test_factor_crud_has_required_methods(self, factor_crud):
        """验证 BaseCRUD 的关键 hook 方法都存在且可调用"""
        required_methods = [
            "_do_add", "_do_find", "_do_modify", "_do_remove", "_do_count",
            "_get_field_config", "_get_enum_mappings",
            "_create_from_params", "_convert_input_item",
        ]

        for method_name in required_methods:
            assert hasattr(factor_crud, method_name), f"缺少方法: {method_name}"
            assert callable(getattr(factor_crud, method_name)), f"不可调用: {method_name}"
