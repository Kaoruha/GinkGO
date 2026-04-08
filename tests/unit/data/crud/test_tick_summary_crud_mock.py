"""
性能: 221MB RSS, 1.87s, 11 tests [PASS]
TickSummaryCRUD 单元测试（Mock 数据库连接）

覆盖范围：
- _get_field_config: 字段配置结构与验证规则
- _get_enum_mappings: 枚举映射
- _create_from_params: 参数转 MTickSummary 模型
- Business Helper: find_by_code, find_by_date
- 构造与类型检查
"""

import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

from ginkgo.enums import SOURCE_TYPES


# ============================================================
# 辅助：构造 TickSummaryCRUD 实例（mock DB 连接）
# ============================================================


@pytest.fixture
def tick_summary_crud():
    """构造 TickSummaryCRUD 实例，mock 掉 get_db_connection 避免真实数据库连接"""
    mock_logger = MagicMock()
    with patch("ginkgo.data.crud.base_crud.get_db_connection"), \
         patch("ginkgo.data.crud.base_crud.GLOG", mock_logger), \
         patch("ginkgo.data.crud.tick_summary_crud.GLOG", mock_logger), \
         patch("ginkgo.data.access_control.service_only", lambda f: f):
        from ginkgo.data.crud.tick_summary_crud import TickSummaryCRUD
        crud = TickSummaryCRUD()
        crud._logger = mock_logger
        return crud


# ============================================================
# _get_field_config 测试
# ============================================================


class TestTickSummaryCRUDFieldConfig:
    """_get_field_config 字段配置测试"""

    @pytest.mark.unit
    def test_field_config_has_required_keys(self, tick_summary_crud):
        """配置包含 code/price/volume/timestamp/source"""
        config = tick_summary_crud._get_field_config()

        required_keys = {"code", "price", "volume", "timestamp", "source"}
        assert required_keys.issubset(set(config.keys())), \
            f"缺少字段: {required_keys - set(config.keys())}"

    @pytest.mark.unit
    def test_field_config_code_is_string(self, tick_summary_crud):
        """code 字段类型为 string，max=32"""
        config = tick_summary_crud._get_field_config()

        assert config["code"]["type"] == "string"
        assert config["code"]["max"] == 32

    @pytest.mark.unit
    def test_field_config_price_min_zero(self, tick_summary_crud):
        """price 字段 min=0"""
        config = tick_summary_crud._get_field_config()

        assert config["price"]["min"] == 0

    @pytest.mark.unit
    def test_field_config_volume_min_zero(self, tick_summary_crud):
        """volume 字段 min=0"""
        config = tick_summary_crud._get_field_config()

        assert config["volume"]["min"] == 0


# ============================================================
# _get_enum_mappings 测试
# ============================================================


class TestTickSummaryCRUDEnumMappings:
    """_get_enum_mappings 枚举映射测试"""

    @pytest.mark.unit
    def test_enum_mappings_has_source(self, tick_summary_crud):
        """映射包含 source 枚举"""
        mappings = tick_summary_crud._get_enum_mappings()

        assert "source" in mappings
        assert mappings["source"] is SOURCE_TYPES


# ============================================================
# _create_from_params 测试
# ============================================================


class TestTickSummaryCRUDCreateFromParams:
    """_create_from_params 参数转模型测试"""

    @pytest.mark.unit
    def test_create_from_params_basic(self, tick_summary_crud):
        """传入完整参数，返回 MTickSummary 模型且属性正确"""
        params = {
            "code": "000001.SZ",
            "price": Decimal("10.50"),
            "volume": 50000,
            "timestamp": datetime(2024, 1, 15, 9, 30, 0),
            "source": SOURCE_TYPES.TUSHARE,
        }

        model = tick_summary_crud._create_from_params(**params)

        assert model.code == "000001.SZ"
        assert model.price == Decimal("10.50")
        assert model.volume == 50000

    @pytest.mark.unit
    def test_create_from_params_defaults(self, tick_summary_crud):
        """缺失字段使用默认值"""
        model = tick_summary_crud._create_from_params()

        assert model.code == ""
        assert model.price == Decimal("0")
        assert model.volume == 0
        assert model.source == SOURCE_TYPES.OTHER.value

    @pytest.mark.unit
    def test_create_from_params_timestamp_normalized(self, tick_summary_crud):
        """timestamp 经过 datetime_normalize 处理"""
        with patch("ginkgo.data.crud.tick_summary_crud.datetime_normalize") as mock_normalize:
            mock_normalize.return_value = datetime(2024, 6, 1)

            model = tick_summary_crud._create_from_params(
                code="000001.SZ",
                timestamp="2024-06-01",
            )

            mock_normalize.assert_called_once_with("2024-06-01")
            assert model.timestamp == datetime(2024, 6, 1)


# ============================================================
# Business Helper 测试
# ============================================================


class TestTickSummaryCRUDBusinessHelpers:
    """Business Helper 方法测试"""

    @pytest.mark.unit
    def test_find_by_code(self, tick_summary_crud):
        """find_by_code 构造正确的 filters 并调用 self.find"""
        tick_summary_crud.find = MagicMock(return_value=[])

        with patch("ginkgo.data.crud.tick_summary_crud.datetime_normalize") as mock_dt:
            mock_dt.side_effect = lambda x: x
            tick_summary_crud.find_by_code(
                code="000001.SZ",
                start_date="2024-01-01",
                end_date="2024-12-31",
            )

        tick_summary_crud.find.assert_called_once()
        call_kwargs = tick_summary_crud.find.call_args[1]
        assert call_kwargs["filters"]["code"] == "000001.SZ"
        assert call_kwargs["order_by"] == "timestamp"

    @pytest.mark.unit
    def test_find_by_date(self, tick_summary_crud):
        """find_by_date 构造正确的 filters 并调用 self.find"""
        tick_summary_crud.find = MagicMock(return_value=[])

        with patch("ginkgo.data.crud.tick_summary_crud.datetime_normalize") as mock_dt:
            mock_dt.return_value = datetime(2024, 1, 15)
            tick_summary_crud.find_by_date(
                date="2024-01-15",
                codes=["000001.SZ", "600000.SH"],
            )

        tick_summary_crud.find.assert_called_once()
        call_kwargs = tick_summary_crud.find.call_args[1]
        assert call_kwargs["filters"]["timestamp"] == datetime(2024, 1, 15)
        assert call_kwargs["filters"]["code__in"] == ["000001.SZ", "600000.SH"]
        assert call_kwargs["order_by"] == "code"


# ============================================================
# 构造与类型检查测试
# ============================================================


class TestTickSummaryCRUDConstruction:
    """TickSummaryCRUD 构造和类型检查测试"""

    @pytest.mark.unit
    def test_tick_summary_crud_construction(self, tick_summary_crud):
        """验证 model_class 为 MTickSummary，_is_clickhouse 为 True"""
        from ginkgo.data.models import MTickSummary

        assert tick_summary_crud.model_class is MTickSummary
        assert tick_summary_crud._is_clickhouse is True
        assert tick_summary_crud._is_mysql is False

