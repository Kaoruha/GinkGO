"""
PositionRecordCRUD 单元测试（Mock 数据库连接）

覆盖范围：
- _get_field_config: 字段配置结构与验证规则
- _get_enum_mappings: 枚举映射
- _create_from_params: 参数转 MPositionRecord 模型
- Business Helper: find_by_portfolio, count_by_portfolio
- 构造与类型检查
"""

import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

from ginkgo.enums import SOURCE_TYPES


# ============================================================
# 辅助：构造 PositionRecordCRUD 实例（mock DB 连接）
# ============================================================


@pytest.fixture
def position_record_crud():
    """构造 PositionRecordCRUD 实例，mock 掉 get_db_connection 避免真实数据库连接"""
    mock_logger = MagicMock()
    with patch("ginkgo.data.crud.base_crud.get_db_connection"), \
         patch("ginkgo.data.crud.base_crud.GLOG", mock_logger), \
         patch("ginkgo.data.crud.position_record_crud.GLOG", mock_logger), \
         patch("ginkgo.data.access_control.service_only", lambda f: f):
        from ginkgo.data.crud.position_record_crud import PositionRecordCRUD
        crud = PositionRecordCRUD()
        crud._logger = mock_logger
        return crud


# ============================================================
# _get_field_config 测试
# ============================================================


class TestPositionRecordCRUDFieldConfig:
    """_get_field_config 字段配置测试"""

    @pytest.mark.unit
    def test_field_config_has_required_keys(self, position_record_crud):
        """配置包含 portfolio_id/engine_id/code/cost/volume/frozen_volume/frozen_money/price/fee/timestamp/business_timestamp"""
        config = position_record_crud._get_field_config()

        required_keys = {
            "portfolio_id", "engine_id", "code", "cost", "volume",
            "frozen_volume", "frozen_money", "price", "fee",
            "timestamp", "business_timestamp",
        }
        assert required_keys.issubset(set(config.keys())), \
            f"缺少字段: {required_keys - set(config.keys())}"

    @pytest.mark.unit
    def test_field_config_portfolio_id_is_string(self, position_record_crud):
        """portfolio_id 字段类型为 string，max=32"""
        config = position_record_crud._get_field_config()

        assert config["portfolio_id"]["type"] == "string"
        assert config["portfolio_id"]["max"] == 32

    @pytest.mark.unit
    def test_field_config_cost_min_zero(self, position_record_crud):
        """cost 字段 min=0"""
        config = position_record_crud._get_field_config()

        assert config["cost"]["min"] == 0

    @pytest.mark.unit
    def test_field_config_volume_min_zero(self, position_record_crud):
        """volume 字段 min=0"""
        config = position_record_crud._get_field_config()

        assert config["volume"]["min"] == 0


# ============================================================
# _get_enum_mappings 测试
# ============================================================


class TestPositionRecordCRUDEnumMappings:
    """_get_enum_mappings 枚举映射测试"""

    @pytest.mark.unit
    def test_enum_mappings_has_source(self, position_record_crud):
        """映射包含 source 枚举"""
        mappings = position_record_crud._get_enum_mappings()

        assert "source" in mappings
        assert mappings["source"] is SOURCE_TYPES


# ============================================================
# _create_from_params 测试
# ============================================================


class TestPositionRecordCRUDCreateFromParams:
    """_create_from_params 参数转模型测试"""

    @pytest.mark.unit
    def test_create_from_params_basic(self, position_record_crud):
        """传入完整参数，返回 MPositionRecord 模型且属性正确"""
        params = {
            "portfolio_id": "portfolio-001",
            "engine_id": "engine-001",
            "code": "000001.SZ",
            "cost": Decimal("10.50"),
            "volume": 1000,
            "frozen_volume": 100,
            "frozen_money": Decimal("1050.00"),
            "price": Decimal("11.00"),
            "fee": Decimal("5.25"),
            "timestamp": datetime(2024, 1, 15),
        }

        model = position_record_crud._create_from_params(**params)

        assert model.portfolio_id == "portfolio-001"
        assert model.code == "000001.SZ"
        assert model.volume == 1000
        assert model.frozen_volume == 100

    @pytest.mark.unit
    def test_create_from_params_defaults(self, position_record_crud):
        """缺失字段使用默认值 0"""
        model = position_record_crud._create_from_params(
            portfolio_id="portfolio-001",
        )

        assert model.volume == 0
        assert model.frozen_volume == 0
        assert model.frozen_money == Decimal("0")
        assert model.price == Decimal("0")
        assert model.fee == Decimal("0")

    @pytest.mark.unit
    def test_create_from_params_timestamp_normalized(self, position_record_crud):
        """timestamp 经过 datetime_normalize 处理"""
        with patch("ginkgo.data.crud.position_record_crud.datetime_normalize") as mock_normalize:
            mock_normalize.return_value = datetime(2024, 6, 1)

            model = position_record_crud._create_from_params(
                portfolio_id="p1",
                timestamp="2024-06-01",
            )

            mock_normalize.assert_called()
            assert model.timestamp == datetime(2024, 6, 1)


# ============================================================
# Business Helper 测试
# ============================================================


class TestPositionRecordCRUDBusinessHelpers:
    """Business Helper 方法测试"""

    @pytest.mark.unit
    def test_find_by_portfolio(self, position_record_crud):
        """find_by_portfolio 构造正确的 filters 并调用 self.find"""
        position_record_crud.find = MagicMock(return_value=[])

        with patch("ginkgo.data.crud.position_record_crud.datetime_normalize") as mock_dt:
            mock_dt.side_effect = lambda x: x
            position_record_crud.find_by_portfolio(
                portfolio_id="portfolio-001",
                code="000001.SZ",
                start_date="2024-01-01",
            )

        position_record_crud.find.assert_called_once()
        call_kwargs = position_record_crud.find.call_args[1]
        assert call_kwargs["filters"]["portfolio_id"] == "portfolio-001"
        assert call_kwargs["filters"]["code"] == "000001.SZ"
        assert call_kwargs["order_by"] == "timestamp"

    @pytest.mark.unit
    def test_count_by_portfolio(self, position_record_crud):
        """count_by_portfolio 调用 self.count 并传入正确 filters"""
        position_record_crud.count = MagicMock(return_value=10)

        result = position_record_crud.count_by_portfolio("portfolio-001")

        assert result == 10
        position_record_crud.count.assert_called_once_with({"portfolio_id": "portfolio-001"})


# ============================================================
# 构造与类型检查测试
# ============================================================


class TestPositionRecordCRUDConstruction:
    """PositionRecordCRUD 构造和类型检查测试"""

    @pytest.mark.unit
    def test_position_record_crud_construction(self, position_record_crud):
        """验证 model_class 为 MPositionRecord，_is_clickhouse 为 True"""
        from ginkgo.data.models import MPositionRecord

        assert position_record_crud.model_class is MPositionRecord
        assert position_record_crud._is_clickhouse is True
        assert position_record_crud._is_mysql is False

    @pytest.mark.unit
    def test_position_record_crud_has_required_methods(self, position_record_crud):
        """验证 BaseCRUD 的关键 hook 方法都存在且可调用"""
        required_methods = [
            "_do_add", "_do_find", "_do_modify", "_do_remove", "_do_count",
            "_get_field_config", "_get_enum_mappings",
            "_create_from_params", "_convert_input_item",
        ]

        for method_name in required_methods:
            assert hasattr(position_record_crud, method_name), f"缺少方法: {method_name}"
            assert callable(getattr(position_record_crud, method_name)), f"不可调用: {method_name}"
