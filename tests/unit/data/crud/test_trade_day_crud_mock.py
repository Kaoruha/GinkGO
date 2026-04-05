"""
TradeDayCRUD 单元测试（Mock 数据库连接）

覆盖范围：
- _get_field_config: 字段配置结构与验证规则
- _get_enum_mappings: 枚举映射
- _create_from_params: 参数转 MTradeDay 模型
- Business Helper: find_trading_days, is_open
- 构造与类型检查
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from ginkgo.enums import MARKET_TYPES, SOURCE_TYPES


# ============================================================
# 辅助：构造 TradeDayCRUD 实例（mock DB 连接）
# ============================================================


@pytest.fixture
def trade_day_crud():
    """构造 TradeDayCRUD 实例，mock 掉 get_db_connection 避免真实数据库连接"""
    mock_logger = MagicMock()
    with patch("ginkgo.data.crud.base_crud.get_db_connection"), \
         patch("ginkgo.data.crud.base_crud.GLOG", mock_logger), \
         patch("ginkgo.data.crud.trade_day_crud.GLOG", mock_logger), \
         patch("ginkgo.data.access_control.service_only", lambda f: f):
        from ginkgo.data.crud.trade_day_crud import TradeDayCRUD
        crud = TradeDayCRUD()
        crud._logger = mock_logger
        return crud


# ============================================================
# _get_field_config 测试
# ============================================================


class TestTradeDayCRUDFieldConfig:
    """_get_field_config 字段配置测试"""

    @pytest.mark.unit
    def test_field_config_has_required_keys(self, trade_day_crud):
        """配置包含 timestamp/market/is_open/source"""
        config = trade_day_crud._get_field_config()

        required_keys = {"timestamp", "market", "is_open", "source"}
        assert required_keys.issubset(set(config.keys())), \
            f"缺少字段: {required_keys - set(config.keys())}"

    @pytest.mark.unit
    def test_field_config_timestamp_type(self, trade_day_crud):
        """timestamp 字段支持 datetime 和 string"""
        config = trade_day_crud._get_field_config()

        assert "datetime" in config["timestamp"]["type"]
        assert "string" in config["timestamp"]["type"]

    @pytest.mark.unit
    def test_field_config_market_is_enum(self, trade_day_crud):
        """market 字段为枚举类型"""
        config = trade_day_crud._get_field_config()

        assert config["market"]["type"] == "enum"
        assert "choices" in config["market"]

    @pytest.mark.unit
    def test_field_config_is_open_is_bool(self, trade_day_crud):
        """is_open 字段类型为 bool"""
        config = trade_day_crud._get_field_config()

        assert config["is_open"]["type"] == "bool"


# ============================================================
# _get_enum_mappings 测试
# ============================================================


class TestTradeDayCRUDEnumMappings:
    """_get_enum_mappings 枚举映射测试"""

    @pytest.mark.unit
    def test_enum_mappings_has_market_and_source(self, trade_day_crud):
        """映射包含 market 和 source 两个枚举"""
        mappings = trade_day_crud._get_enum_mappings()

        assert "market" in mappings
        assert "source" in mappings
        assert mappings["market"] is MARKET_TYPES
        assert mappings["source"] is SOURCE_TYPES


# ============================================================
# _create_from_params 测试
# ============================================================


class TestTradeDayCRUDCreateFromParams:
    """_create_from_params 参数转模型测试"""

    @pytest.mark.unit
    def test_create_from_params_basic(self, trade_day_crud):
        """传入完整参数，返回 MTradeDay 模型且属性正确"""
        from ginkgo.data.models import MTradeDay

        with patch("ginkgo.data.crud.trade_day_crud.datetime_normalize") as mock_normalize:
            mock_normalize.return_value = datetime(2024, 1, 15)

            mday = trade_day_crud._create_from_params(
                timestamp="2024-01-15",
                market=MARKET_TYPES.CHINA,
                is_open=True,
            )

            assert isinstance(mday, MTradeDay)
            assert mday.timestamp == datetime(2024, 1, 15)
            assert mday.is_open is True
            # MTradeDay 模型将枚举存储为 int 值
            assert mday.market == MARKET_TYPES.CHINA.value
            assert mday.source == SOURCE_TYPES.TUSHARE.value

    @pytest.mark.unit
    def test_create_from_params_defaults(self, trade_day_crud):
        """缺失字段使用默认值"""
        with patch("ginkgo.data.crud.trade_day_crud.datetime_normalize") as mock_normalize:
            mock_normalize.return_value = datetime(2024, 6, 1)

            mday = trade_day_crud._create_from_params()

            assert mday.market == MARKET_TYPES.CHINA.value
            assert mday.is_open is True
            assert mday.source == SOURCE_TYPES.TUSHARE.value


# ============================================================
# Business Helper 测试
# ============================================================


class TestTradeDayCRUDBusinessHelpers:
    """Business Helper 方法测试"""

    @pytest.mark.unit
    def test_find_trading_days(self, trade_day_crud):
        """find_trading_days 构造正确的 filters 并调用 self.find"""
        trade_day_crud.find = MagicMock(return_value=[])

        with patch("ginkgo.data.crud.trade_day_crud.datetime_normalize") as mock_dt:
            mock_dt.side_effect = lambda x: x
            trade_day_crud.find_trading_days(start_date="2024-01-01", end_date="2024-12-31")

        trade_day_crud.find.assert_called_once()
        call_kwargs = trade_day_crud.find.call_args[1]
        assert "timestamp__gte" in call_kwargs["filters"]
        assert "timestamp__lte" in call_kwargs["filters"]
        assert call_kwargs["filters"]["is_open"] is True
        assert call_kwargs["order_by"] == "timestamp"

    @pytest.mark.unit
    def test_is_open_with_result(self, trade_day_crud):
        """is_open 有结果时返回 is_open 属性"""
        mock_day = MagicMock()
        mock_day.is_open = True
        trade_day_crud.find = MagicMock(return_value=[mock_day])

        with patch("ginkgo.data.crud.trade_day_crud.datetime_normalize") as mock_dt:
            mock_dt.return_value = datetime(2024, 1, 15)
            result = trade_day_crud.is_open(date="2024-01-15")

        assert result is True

    @pytest.mark.unit
    def test_is_open_no_result(self, trade_day_crud):
        """is_open 无结果时返回 False"""
        trade_day_crud.find = MagicMock(return_value=[])

        with patch("ginkgo.data.crud.trade_day_crud.datetime_normalize") as mock_dt:
            mock_dt.return_value = datetime(2024, 1, 15)
            result = trade_day_crud.is_open(date="2024-01-15")

        assert result is False


# ============================================================
# 构造与类型检查测试
# ============================================================


class TestTradeDayCRUDConstruction:
    """TradeDayCRUD 构造和类型检查测试"""

    @pytest.mark.unit
    def test_trade_day_crud_construction(self, trade_day_crud):
        """验证 model_class 为 MTradeDay，_is_mysql 为 True"""
        from ginkgo.data.models import MTradeDay

        assert trade_day_crud.model_class is MTradeDay
        assert trade_day_crud._is_mysql is True
        assert trade_day_crud._is_clickhouse is False

    @pytest.mark.unit
    def test_trade_day_crud_has_required_methods(self, trade_day_crud):
        """验证 BaseCRUD 的关键 hook 方法都存在且可调用"""
        required_methods = [
            "_do_add",
            "_do_find",
            "_do_modify",
            "_do_remove",
            "_do_count",
            "_get_field_config",
            "_get_enum_mappings",
            "_create_from_params",
            "_convert_input_item",
        ]

        for method_name in required_methods:
            assert hasattr(trade_day_crud, method_name), f"缺少方法: {method_name}"
            assert callable(getattr(trade_day_crud, method_name)), f"不可调用: {method_name}"
