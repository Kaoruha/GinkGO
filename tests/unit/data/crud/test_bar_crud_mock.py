"""
BarCRUD 单元测试（Mock 数据库连接）

覆盖范围：
- _get_field_config: 字段配置结构与验证规则
- _get_enum_mappings: 枚举映射
- _create_from_params: 参数转 MBar 模型
- _convert_input_item: Bar 业务对象转换
- Business Helper: find_by_code_and_date_range, get_latest_bars, count_by_code 等
- 构造与类型检查
"""

import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch, PropertyMock

from ginkgo.enums import FREQUENCY_TYPES, SOURCE_TYPES


# ============================================================
# 辅助：构造 BarCRUD 实例（mock DB 连接）
# ============================================================


@pytest.fixture
def bar_crud():
    """构造 BarCRUD 实例，mock 掉 get_db_connection 避免真实数据库连接"""
    mock_logger = MagicMock()
    with patch("ginkgo.data.crud.base_crud.get_db_connection"), \
         patch("ginkgo.data.crud.base_crud.GLOG", mock_logger), \
         patch("ginkgo.data.crud.bar_crud.GLOG", mock_logger), \
         patch("ginkgo.data.access_control.service_only", lambda f: f):
        from ginkgo.data.crud.bar_crud import BarCRUD
        crud = BarCRUD()
        # _convert_input_item 内部使用 self._logger
        crud._logger = mock_logger
        return crud


# ============================================================
# _get_field_config 测试
# ============================================================


class TestBarCRUDFieldConfig:
    """_get_field_config 字段配置测试"""

    @pytest.mark.unit
    def test_field_config_has_required_keys(self, bar_crud):
        """配置包含 code/open/high/low/close/volume/amount/timestamp/frequency"""
        config = bar_crud._get_field_config()

        required_keys = {"code", "open", "high", "low", "close", "volume", "amount", "timestamp", "frequency"}
        assert required_keys.issubset(set(config.keys())), \
            f"缺少字段: {required_keys - set(config.keys())}"

    @pytest.mark.unit
    def test_field_config_price_validation(self, bar_crud):
        """OHLC 价格字段 min=0.001"""
        config = bar_crud._get_field_config()

        for field in ("open", "high", "low", "close"):
            assert field in config, f"缺少价格字段: {field}"
            assert config[field]["min"] == 0.001, f"{field} 的 min 应为 0.001"
            # 类型支持 decimal/float/int
            assert isinstance(config[field]["type"], list), f"{field} type 应为列表"

    @pytest.mark.unit
    def test_field_config_volume_validation(self, bar_crud):
        """volume 字段 min=0"""
        config = bar_crud._get_field_config()

        assert config["volume"]["min"] == 0

    @pytest.mark.unit
    def test_field_config_code_is_string(self, bar_crud):
        """code 字段类型为 string"""
        config = bar_crud._get_field_config()

        assert config["code"]["type"] == "string"
        assert config["code"]["min"] == 1


# ============================================================
# _get_enum_mappings 测试
# ============================================================


class TestBarCRUDEnumMappings:
    """_get_enum_mappings 枚举映射测试"""

    @pytest.mark.unit
    def test_enum_mappings_has_frequency_and_source(self, bar_crud):
        """映射包含 frequency 和 source 两个枚举"""
        mappings = bar_crud._get_enum_mappings()

        assert "frequency" in mappings
        assert "source" in mappings
        assert mappings["frequency"] is FREQUENCY_TYPES
        assert mappings["source"] is SOURCE_TYPES


# ============================================================
# _create_from_params 测试
# ============================================================


class TestBarCRUDCreateFromParams:
    """_create_from_params 参数转模型测试"""

    @pytest.mark.unit
    def test_create_from_params_basic(self, bar_crud):
        """传入完整参数，返回 MBar 模型且属性正确"""
        params = {
            "code": "000001.SZ",
            "open": Decimal("10.50"),
            "high": Decimal("11.00"),
            "low": Decimal("10.20"),
            "close": Decimal("10.80"),
            "volume": 1000000,
            "amount": Decimal("10800000.00"),
            "timestamp": datetime(2024, 1, 15, 9, 30, 0),
            "frequency": FREQUENCY_TYPES.DAY,
        }

        mbar = bar_crud._create_from_params(**params)

        assert mbar.code == "000001.SZ"
        assert mbar.volume == 1000000
        # MBar 模型将枚举存储为 int 值
        assert mbar.frequency == FREQUENCY_TYPES.DAY.value

    @pytest.mark.unit
    def test_create_from_params_defaults(self, bar_crud):
        """缺失字段使用默认值：volume=0, frequency=DAY, source=TUSHARE"""
        mbar = bar_crud._create_from_params(code="000002.SZ")

        assert mbar.code == "000002.SZ"
        assert mbar.volume == 0
        # MBar 模型将枚举存储为 int 值
        assert mbar.frequency == FREQUENCY_TYPES.DAY.value
        assert mbar.source == SOURCE_TYPES.TUSHARE.value

    @pytest.mark.unit
    def test_create_from_params_timestamp_normalized(self, bar_crud):
        """timestamp 经过 datetime_normalize 处理"""
        with patch("ginkgo.data.crud.bar_crud.datetime_normalize") as mock_normalize:
            mock_normalize.return_value = datetime(2024, 6, 1)

            mbar = bar_crud._create_from_params(code="000001.SZ", timestamp="2024-06-01")

            mock_normalize.assert_called_once_with("2024-06-01")
            assert mbar.timestamp == datetime(2024, 6, 1)


# ============================================================
# _convert_input_item 测试
# ============================================================


class TestBarCRUDConvertInputItem:
    """_convert_input_item 业务对象转换测试"""

    @pytest.mark.unit
    def test_convert_input_item_bar_object(self, bar_crud):
        """传入 Bar 业务对象，返回 MBar 模型"""
        from ginkgo.trading import Bar

        bar_obj = Bar(
            code="000001.SZ",
            open=Decimal("10.50"),
            high=Decimal("11.00"),
            low=Decimal("10.20"),
            close=Decimal("10.80"),
            volume=500000,
            amount=Decimal("5400000.00"),
            frequency=FREQUENCY_TYPES.DAY,
            timestamp=datetime(2024, 1, 15),
        )

        mbar = bar_crud._convert_input_item(bar_obj)

        assert mbar is not None
        assert mbar.code == "000001.SZ"
        assert mbar.volume == 500000
        # MBar 模型将枚举存储为 int 值
        assert mbar.frequency == FREQUENCY_TYPES.DAY.value

    @pytest.mark.unit
    def test_convert_input_item_unsupported_type(self, bar_crud):
        """传入非 Bar 类型（如 dict），返回 None"""
        result = bar_crud._convert_input_item({"code": "000001.SZ"})

        assert result is None


# ============================================================
# Business Helper 测试
# ============================================================


class TestBarCRUDBusinessHelpers:
    """Business Helper 方法测试"""

    @pytest.mark.unit
    def test_find_by_code_with_date_range(self, bar_crud):
        """find_by_code_and_date_range 构造正确的 filters 并调用 self.find"""
        # mock self.find 避免真实数据库操作
        bar_crud.find = MagicMock(return_value=[])

        with patch("ginkgo.data.crud.bar_crud.datetime_normalize") as mock_dt:
            mock_dt.side_effect = lambda x: x  # 直接返回输入
            bar_crud.find_by_code_and_date_range(
                code="000001.SZ",
                start_date="2024-01-01",
                end_date="2024-12-31",
                page=0,
                page_size=100,
            )

        bar_crud.find.assert_called_once()
        call_kwargs = bar_crud.find.call_args[1]
        assert call_kwargs["filters"]["code"] == "000001.SZ"
        assert "timestamp__gte" in call_kwargs["filters"]
        assert "timestamp__lte" in call_kwargs["filters"]
        assert call_kwargs["order_by"] == "timestamp"

    @pytest.mark.unit
    def test_get_latest_bars(self, bar_crud):
        """get_latest_bars 调用 self.find 且 desc_order=True"""
        bar_crud.find = MagicMock(return_value=[])

        bar_crud.get_latest_bars(code="000001.SZ", limit=10, page=0)

        bar_crud.find.assert_called_once()
        call_kwargs = bar_crud.find.call_args[1]
        assert call_kwargs["filters"]["code"] == "000001.SZ"
        assert call_kwargs["page_size"] == 10
        assert call_kwargs["desc_order"] is True
        assert call_kwargs["order_by"] == "timestamp"

    @pytest.mark.unit
    def test_count_by_code(self, bar_crud):
        """count_by_code 调用 self.count 并传入正确 filters"""
        bar_crud.count = MagicMock(return_value=42)

        result = bar_crud.count_by_code("000001.SZ")

        assert result == 42
        bar_crud.count.assert_called_once_with({"code": "000001.SZ"})

    @pytest.mark.unit
    def test_remove_by_code_and_date_range(self, bar_crud):
        """remove_by_code_and_date_range 构造 filters 并调用 self.remove"""
        bar_crud.remove = MagicMock()

        with patch("ginkgo.data.crud.bar_crud.datetime_normalize") as mock_dt:
            mock_dt.side_effect = lambda x: x
            bar_crud.remove_by_code_and_date_range(
                code="000001.SZ",
                start_date="2024-01-01",
                end_date="2024-06-01",
            )

        bar_crud.remove.assert_called_once()
        filters = bar_crud.remove.call_args[0][0]
        assert filters["code"] == "000001.SZ"
        assert "timestamp__gte" in filters
        assert "timestamp__lte" in filters


# ============================================================
# 构造与类型检查测试
# ============================================================


class TestBarCRUDConstruction:
    """BarCRUD 构造和类型检查测试"""

    @pytest.mark.unit
    def test_bar_crud_construction(self, bar_crud):
        """验证 model_class 为 MBar，_is_clickhouse 为 True"""
        from ginkgo.data.models import MBar

        assert bar_crud.model_class is MBar
        assert bar_crud._is_clickhouse is True
        assert bar_crud._is_mysql is False

    @pytest.mark.unit
    def test_bar_crud_has_required_methods(self, bar_crud):
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
            assert hasattr(bar_crud, method_name), f"缺少方法: {method_name}"
            assert callable(getattr(bar_crud, method_name)), f"不可调用: {method_name}"
