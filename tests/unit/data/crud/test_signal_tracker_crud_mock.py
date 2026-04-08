"""
性能: 221MB RSS, 1.93s, 11 tests [PASS]
SignalTrackerCRUD 单元测试（Mock 数据库连接）

覆盖范围：
- _get_field_config: 字段配置结构与验证规则
- _get_enum_mappings: 枚举映射（DIRECTION_TYPES, SOURCE_TYPES）
- _create_from_params: 参数转 MSignalTracker 模型
- Business Helper: find_by_portfolio, find_by_signal_id
- 构造与类型检查
"""

import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES


# ============================================================
# 辅助：构造 SignalTrackerCRUD 实例（mock DB 连接）
# ============================================================


@pytest.fixture
def signal_tracker_crud():
    """构造 SignalTrackerCRUD 实例，mock 掉 get_db_connection 避免真实数据库连接"""
    mock_logger = MagicMock()
    with patch("ginkgo.data.crud.base_crud.get_db_connection"), \
         patch("ginkgo.data.crud.base_crud.GLOG", mock_logger), \
         patch("ginkgo.data.crud.signal_tracker_crud.GLOG", mock_logger), \
         patch("ginkgo.data.access_control.service_only", lambda f: f):
        from ginkgo.data.crud.signal_tracker_crud import SignalTrackerCRUD
        crud = SignalTrackerCRUD()
        crud._logger = mock_logger
        return crud


# ============================================================
# _get_field_config 测试
# ============================================================


class TestSignalTrackerCRUDFieldConfig:
    """_get_field_config 字段配置测试"""

    @pytest.mark.unit
    def test_field_config_has_required_keys(self, signal_tracker_crud):
        """配置包含 signal_id/strategy_id/portfolio_id/expected_code/expected_direction/expected_price/expected_volume/expected_timestamp/business_timestamp/engine_id/run_id/account_type/execution_mode"""
        config = signal_tracker_crud._get_field_config()

        required_keys = {
            "signal_id", "strategy_id", "portfolio_id",
            "expected_code", "expected_direction", "expected_price",
            "expected_volume", "expected_timestamp", "business_timestamp",
            "engine_id", "run_id", "account_type", "execution_mode",
        }
        assert required_keys.issubset(set(config.keys())), \
            f"缺少字段: {required_keys - set(config.keys())}"

    @pytest.mark.unit
    def test_field_config_signal_id_is_string(self, signal_tracker_crud):
        """signal_id 字段类型为 string"""
        config = signal_tracker_crud._get_field_config()

        assert config["signal_id"]["type"] == str

    @pytest.mark.unit
    def test_field_config_expected_direction_is_enum(self, signal_tracker_crud):
        """expected_direction 字段类型为 enum"""
        config = signal_tracker_crud._get_field_config()

        assert config["expected_direction"]["type"] == "enum"

    @pytest.mark.unit
    def test_field_config_execution_mode_is_enum(self, signal_tracker_crud):
        """execution_mode 字段类型为 enum"""
        config = signal_tracker_crud._get_field_config()

        assert config["execution_mode"]["type"] == "enum"


# ============================================================
# _get_enum_mappings 测试
# ============================================================


class TestSignalTrackerCRUDEnumMappings:
    """_get_enum_mappings 枚举映射测试"""

    @pytest.mark.unit
    def test_enum_mappings_has_direction_and_source(self, signal_tracker_crud):
        """映射包含 expected_direction 和 source 枚举"""
        mappings = signal_tracker_crud._get_enum_mappings()

        assert "expected_direction" in mappings
        assert "source" in mappings
        assert mappings["expected_direction"] is DIRECTION_TYPES
        assert mappings["source"] is SOURCE_TYPES


# ============================================================
# _create_from_params 测试
# ============================================================


class TestSignalTrackerCRUDCreateFromParams:
    """_create_from_params 参数转模型测试"""

    @pytest.mark.unit
    def test_create_from_params_basic(self, signal_tracker_crud):
        """传入完整参数，返回 MSignalTracker 模型且属性正确"""
        params = {
            "signal_id": "signal-001",
            "strategy_id": "strategy-001",
            "portfolio_id": "portfolio-001",
            "expected_code": "000001.SZ",
            "expected_direction": DIRECTION_TYPES.LONG,
            "expected_price": Decimal("10.50"),
            "expected_volume": 1000,
            "expected_timestamp": datetime(2024, 1, 15),
            "business_timestamp": datetime(2024, 1, 15),
            "engine_id": "engine-001",
            "run_id": "run-001",
        }

        model = signal_tracker_crud._create_from_params(**params)

        assert model.signal_id == "signal-001"
        assert model.expected_code == "000001.SZ"
        assert model.expected_volume == 1000

    @pytest.mark.unit
    def test_create_from_params_defaults(self, signal_tracker_crud):
        """缺失字段使用默认值"""
        model = signal_tracker_crud._create_from_params(
            signal_id="signal-002",
            expected_price=0,
            expected_volume=0,
        )

        assert model.signal_id == "signal-002"
        assert model.strategy_id == ""

    @pytest.mark.unit
    def test_create_from_params_timestamp_normalized(self, signal_tracker_crud):
        """expected_timestamp 经过 datetime_normalize 处理"""
        with patch("ginkgo.data.crud.signal_tracker_crud.datetime_normalize") as mock_normalize:
            mock_normalize.return_value = datetime(2024, 6, 1)

            model = signal_tracker_crud._create_from_params(
                signal_id="s1",
                expected_price=0,
                expected_volume=0,
                expected_timestamp="2024-06-01",
            )

            mock_normalize.assert_called()
            assert model.expected_timestamp == datetime(2024, 6, 1)


# ============================================================
# Business Helper 测试
# ============================================================


class TestSignalTrackerCRUDBusinessHelpers:
    """Business Helper 方法测试"""

    @pytest.mark.unit
    def test_find_by_portfolio(self, signal_tracker_crud):
        """find_by_portfolio 构造正确的 filters 并调用 self.find"""
        signal_tracker_crud.find = MagicMock(return_value=[])

        signal_tracker_crud.find_by_portfolio(
            portfolio_id="portfolio-001",
        )

        signal_tracker_crud.find.assert_called_once()
        call_kwargs = signal_tracker_crud.find.call_args[1]
        assert call_kwargs["filters"]["portfolio_id"] == "portfolio-001"

    @pytest.mark.unit
    def test_find_by_signal_id(self, signal_tracker_crud):
        """find_by_signal_id 调用 self.get_items_filtered 并传入正确参数"""
        signal_tracker_crud.get_items_filtered = MagicMock(return_value=[])

        result = signal_tracker_crud.find_by_signal_id("signal-001")

        assert result is None  # 空列表返回 None
        signal_tracker_crud.get_items_filtered.assert_called_once_with(
            signal_id="signal-001", limit=1,
        )


# ============================================================
# 构造与类型检查测试
# ============================================================


class TestSignalTrackerCRUDConstruction:
    """SignalTrackerCRUD 构造和类型检查测试"""

    @pytest.mark.unit
    def test_signal_tracker_crud_construction(self, signal_tracker_crud):
        """验证 model_class 为 MSignalTracker"""
        from ginkgo.data.models.model_signal_tracker import MSignalTracker

        assert signal_tracker_crud.model_class is MSignalTracker

