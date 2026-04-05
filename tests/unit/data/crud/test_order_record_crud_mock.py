"""
OrderRecordCRUD 单元测试（Mock 数据库连接）

覆盖范围：
- _get_field_config: 字段配置结构与验证规则
- _get_enum_mappings: 枚举映射（DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES, SOURCE_TYPES）
- _create_from_params: 参数转 MOrderRecord 模型
- Business Helper: find_by_portfolio, count_by_portfolio
- 构造与类型检查
"""

import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES, SOURCE_TYPES


# ============================================================
# 辅助：构造 OrderRecordCRUD 实例（mock DB 连接）
# ============================================================


@pytest.fixture
def order_record_crud():
    """构造 OrderRecordCRUD 实例，mock 掉 get_db_connection 避免真实数据库连接"""
    mock_logger = MagicMock()
    with patch("ginkgo.data.crud.base_crud.get_db_connection"), \
         patch("ginkgo.data.crud.base_crud.GLOG", mock_logger), \
         patch("ginkgo.data.crud.order_record_crud.GLOG", mock_logger), \
         patch("ginkgo.data.access_control.service_only", lambda f: f):
        from ginkgo.data.crud.order_record_crud import OrderRecordCRUD
        crud = OrderRecordCRUD()
        crud._logger = mock_logger
        return crud


# ============================================================
# _get_field_config 测试
# ============================================================


class TestOrderRecordCRUDFieldConfig:
    """_get_field_config 字段配置测试"""

    @pytest.mark.unit
    def test_field_config_has_required_keys(self, order_record_crud):
        """配置包含 order_id/portfolio_id/engine_id/code/direction/order_type/status/volume/limit_price/timestamp/business_timestamp"""
        config = order_record_crud._get_field_config()

        required_keys = {
            "order_id", "portfolio_id", "engine_id", "code",
            "direction", "order_type", "status", "volume",
            "limit_price", "timestamp", "business_timestamp",
        }
        assert required_keys.issubset(set(config.keys())), \
            f"缺少字段: {required_keys - set(config.keys())}"

    @pytest.mark.unit
    def test_field_config_order_id_is_string(self, order_record_crud):
        """order_id 字段类型为 string，max=32"""
        config = order_record_crud._get_field_config()

        assert config["order_id"]["type"] == "string"
        assert config["order_id"]["max"] == 32

    @pytest.mark.unit
    def test_field_config_volume_min(self, order_record_crud):
        """volume 字段 min=1"""
        config = order_record_crud._get_field_config()

        assert config["volume"]["min"] == 1

    @pytest.mark.unit
    def test_field_config_direction_is_enum(self, order_record_crud):
        """direction 字段类型为枚举"""
        config = order_record_crud._get_field_config()

        assert config["direction"]["type"] == "enum"


# ============================================================
# _get_enum_mappings 测试
# ============================================================


class TestOrderRecordCRUDEnumMappings:
    """_get_enum_mappings 枚举映射测试"""

    @pytest.mark.unit
    def test_enum_mappings_has_all_enums(self, order_record_crud):
        """映射包含 direction/order/orderstatus/source 四个枚举"""
        mappings = order_record_crud._get_enum_mappings()

        assert "direction" in mappings
        assert "order" in mappings
        assert "orderstatus" in mappings
        assert "source" in mappings
        assert mappings["direction"] is DIRECTION_TYPES
        assert mappings["order"] is ORDER_TYPES
        assert mappings["orderstatus"] is ORDERSTATUS_TYPES
        assert mappings["source"] is SOURCE_TYPES


# ============================================================
# _create_from_params 测试
# ============================================================


class TestOrderRecordCRUDCreateFromParams:
    """_create_from_params 参数转模型测试"""

    @pytest.mark.unit
    def test_create_from_params_basic(self, order_record_crud):
        """传入完整参数，返回 MOrderRecord 模型且属性正确"""
        params = {
            "order_id": "order-001",
            "portfolio_id": "portfolio-001",
            "engine_id": "engine-001",
            "code": "000001.SZ",
            "direction": DIRECTION_TYPES.LONG,
            "order_type": ORDER_TYPES.LIMITORDER,
            "status": ORDERSTATUS_TYPES.SUBMITTED,
            "volume": 1000,
            "limit_price": Decimal("10.50"),
            "timestamp": datetime(2024, 1, 15),
        }

        model = order_record_crud._create_from_params(**params)

        assert model.order_id == "order-001"
        assert model.code == "000001.SZ"
        assert model.volume == 1000

    @pytest.mark.unit
    def test_create_from_params_defaults(self, order_record_crud):
        """缺失字段使用默认值"""
        model = order_record_crud._create_from_params(
            order_id="order-002",
            portfolio_id="p1",
        )

        assert model.order_id == "order-002"
        assert model.limit_price == Decimal("0")
        assert model.fee == Decimal("0")

    @pytest.mark.unit
    def test_create_from_params_timestamp_normalized(self, order_record_crud):
        """timestamp 经过 datetime_normalize 处理"""
        with patch("ginkgo.data.crud.order_record_crud.datetime_normalize") as mock_normalize:
            mock_normalize.return_value = datetime(2024, 6, 1)

            model = order_record_crud._create_from_params(
                order_id="o1",
                timestamp="2024-06-01",
            )

            mock_normalize.assert_called()
            assert model.timestamp == datetime(2024, 6, 1)


# ============================================================
# Business Helper 测试
# ============================================================


class TestOrderRecordCRUDBusinessHelpers:
    """Business Helper 方法测试"""

    @pytest.mark.unit
    def test_find_by_portfolio(self, order_record_crud):
        """find_by_portfolio 构造正确的 filters 并调用 self.find"""
        order_record_crud.find = MagicMock(return_value=[])

        with patch("ginkgo.data.crud.order_record_crud.datetime_normalize") as mock_dt:
            mock_dt.side_effect = lambda x: x
            order_record_crud.find_by_portfolio(
                portfolio_id="portfolio-001",
                start_date="2024-01-01",
                end_date="2024-12-31",
            )

        order_record_crud.find.assert_called_once()
        call_kwargs = order_record_crud.find.call_args[1]
        assert call_kwargs["filters"]["portfolio_id"] == "portfolio-001"
        assert call_kwargs["order_by"] == "timestamp"
        assert call_kwargs["desc_order"] is True

    @pytest.mark.unit
    def test_count_by_portfolio(self, order_record_crud):
        """count_by_portfolio 调用 self.count 并传入正确 filters"""
        order_record_crud.count = MagicMock(return_value=42)

        result = order_record_crud.count_by_portfolio("portfolio-001")

        assert result == 42
        order_record_crud.count.assert_called_once_with({"portfolio_id": "portfolio-001"})


# ============================================================
# 构造与类型检查测试
# ============================================================


class TestOrderRecordCRUDConstruction:
    """OrderRecordCRUD 构造和类型检查测试"""

    @pytest.mark.unit
    def test_order_record_crud_construction(self, order_record_crud):
        """验证 model_class 为 MOrderRecord，_is_clickhouse 为 True"""
        from ginkgo.data.models import MOrderRecord

        assert order_record_crud.model_class is MOrderRecord
        assert order_record_crud._is_clickhouse is True
        assert order_record_crud._is_mysql is False

    @pytest.mark.unit
    def test_order_record_crud_has_required_methods(self, order_record_crud):
        """验证 BaseCRUD 的关键 hook 方法都存在且可调用"""
        required_methods = [
            "_do_add", "_do_find", "_do_modify", "_do_remove", "_do_count",
            "_get_field_config", "_get_enum_mappings",
            "_create_from_params", "_convert_input_item",
        ]

        for method_name in required_methods:
            assert hasattr(order_record_crud, method_name), f"缺少方法: {method_name}"
            assert callable(getattr(order_record_crud, method_name)), f"不可调用: {method_name}"
