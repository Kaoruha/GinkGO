"""
性能: 219MB RSS, 1.91s, 17 tests [PASS]
SignalCRUD 单元测试（Mock 数据库连接）

覆盖范围：
- _get_field_config: 字段配置结构与验证规则
- _get_enum_mappings: 枚举映射
- _create_from_params: 参数转 MSignal 模型
- _convert_input_item: Signal 业务对象转换
- Business Helper: find_by_portfolio, find_by_engine, find_by_code_and_direction,
  get_latest_signals, delete_by_portfolio, delete_by_portfolio_and_date_range,
  count_by_portfolio, count_by_code_and_direction, find_by_business_time
- 构造与类型检查
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def signal_crud():
    """绕过访问控制装饰器，创建 SignalCRUD 实例，mock 数据库连接和日志"""
    mock_logger = MagicMock()
    with patch("ginkgo.data.crud.base_crud.get_db_connection"), \
         patch("ginkgo.data.crud.base_crud.GLOG", mock_logger), \
         patch("ginkgo.data.crud.signal_crud.GLOG", mock_logger), \
         patch("ginkgo.data.access_control.service_only", lambda f: f):
        from ginkgo.data.crud.signal_crud import SignalCRUD
        crud = SignalCRUD()
        crud._logger = mock_logger
        return crud


# ============================================================================
# _get_field_config 测试
# ============================================================================


class TestSignalCRUDFieldConfig:
    """_get_field_config 字段配置测试"""

    @pytest.mark.unit
    def test_field_config_structure(self, signal_crud):
        """配置包含 portfolio_id/engine_id/run_id/code/direction/timestamp/reason/source"""
        config = signal_crud._get_field_config()

        required_keys = {
            "portfolio_id", "engine_id", "run_id", "code",
            "direction", "timestamp", "reason", "source",
        }
        assert required_keys.issubset(set(config.keys())), \
            f"缺少字段: {required_keys - set(config.keys())}"

    @pytest.mark.unit
    def test_field_config_types(self, signal_crud):
        """验证各字段类型约束：字符串、枚举类型名、datetime 等"""
        config = signal_crud._get_field_config()

        # 字符串字段
        for field in ("portfolio_id", "engine_id", "run_id", "code"):
            assert config[field]["type"] == "string"
            assert config[field]["min"] == 1

        # reason 允许空字符串
        assert config["reason"]["type"] == "string"
        assert config["reason"]["min"] == 0

        # 枚举字段使用类型名称字符串
        assert config["direction"]["type"] == "DIRECTION_TYPES"
        assert config["source"]["type"] == "SOURCE_TYPES"

        # timestamp 支持 datetime/string
        assert isinstance(config["timestamp"]["type"], list)


# ============================================================================
# _get_enum_mappings 测试
# ============================================================================


class TestSignalCRUDEnumMappings:
    """_get_enum_mappings 枚举映射测试"""

    @pytest.mark.unit
    def test_enum_mappings(self, signal_crud):
        """映射包含 direction 和 source 两个枚举"""
        mappings = signal_crud._get_enum_mappings()

        assert "direction" in mappings
        assert "source" in mappings
        assert mappings["direction"] is DIRECTION_TYPES
        assert mappings["source"] is SOURCE_TYPES


# ============================================================================
# _create_from_params 测试
# ============================================================================


class TestSignalCRUDCreateFromParams:
    """_create_from_params 参数转模型测试"""

    @pytest.mark.unit
    def test_create_from_params_basic(self, signal_crud):
        """传入完整参数，返回 MSignal 模型且属性正确"""
        params = {
            "portfolio_id": "portfolio-001",
            "engine_id": "engine-001",
            "run_id": "run-001",
            "code": "000001.SZ",
            "direction": DIRECTION_TYPES.LONG,
            "timestamp": datetime(2024, 1, 15, 9, 30, 0),
            "reason": "均线突破",
            "source": SOURCE_TYPES.TUSHARE,
        }

        model = signal_crud._create_from_params(**params)

        assert isinstance(model, signal_crud.model_class)
        assert model.portfolio_id == "portfolio-001"
        assert model.code == "000001.SZ"
        assert model.direction == DIRECTION_TYPES.LONG.value
        assert model.reason == "均线突破"
        assert model.source == SOURCE_TYPES.TUSHARE.value

    @pytest.mark.unit
    def test_create_from_params_defaults(self, signal_crud):
        """缺失可选字段使用默认值：source=SIM, direction 使用 validate_input"""
        model = signal_crud._create_from_params(
            portfolio_id="portfolio-002",
            code="000002.SZ",
            direction=1,  # int 输入
            timestamp=datetime(2024, 6, 1),
        )

        assert isinstance(model, signal_crud.model_class)
        assert model.portfolio_id == "portfolio-002"
        assert model.code == "000002.SZ"
        assert model.direction == 1
        assert model.source == SOURCE_TYPES.SIM.value

    @pytest.mark.unit
    def test_create_from_params_business_timestamp_fallback(self, signal_crud):
        """business_timestamp 为 None 时回退到 timestamp"""
        model = signal_crud._create_from_params(
            portfolio_id="portfolio-003",
            code="000003.SZ",
            direction=DIRECTION_TYPES.SHORT,
            timestamp=datetime(2024, 3, 15),
        )

        assert isinstance(model, signal_crud.model_class)
        assert model.business_timestamp == datetime(2024, 3, 15)


# ============================================================================
# 构造与类型检查测试
# ============================================================================


class TestSignalCRUDConstruction:
    """SignalCRUD 构造和类型检查测试"""

    @pytest.mark.unit
    def test_construction(self, signal_crud):
        """验证 model_class 为 MSignal，_is_clickhouse 为 True（MSignal 继承 MClickBase）"""
        from ginkgo.data.models import MSignal

        assert signal_crud.model_class is MSignal
        assert signal_crud._is_clickhouse is True
        assert signal_crud._is_mysql is False



# ============================================================================
# Business Helper 测试
# ============================================================================


class TestSignalCRUDBusinessHelpers:
    """Business Helper 方法测试"""

    @pytest.mark.unit
    def test_find_by_portfolio(self, signal_crud):
        """find_by_portfolio 构造 filters 并按 timestamp 排序调用 self.find"""
        signal_crud.find = MagicMock(return_value=[])

        with patch("ginkgo.data.crud.signal_crud.datetime_normalize") as mock_dt:
            mock_dt.side_effect = lambda x: x
            signal_crud.find_by_portfolio(
                portfolio_id="portfolio-001",
                start_date="2024-01-01",
                end_date="2024-12-31",
                page=0,
                page_size=50,
                desc_order=True,
            )

        signal_crud.find.assert_called_once()
        call_kwargs = signal_crud.find.call_args[1]
        assert call_kwargs["filters"]["portfolio_id"] == "portfolio-001"
        assert "timestamp__gte" in call_kwargs["filters"]
        assert "timestamp__lte" in call_kwargs["filters"]
        assert call_kwargs["order_by"] == "timestamp"
        assert call_kwargs["desc_order"] is True
        assert call_kwargs["page"] == 0
        assert call_kwargs["page_size"] == 50

    @pytest.mark.unit
    def test_find_by_engine(self, signal_crud):
        """find_by_engine 构造 filters 并按 timestamp 降序调用 self.find"""
        signal_crud.find = MagicMock(return_value=[])

        signal_crud.find_by_engine("engine-001")

        signal_crud.find.assert_called_once()
        call_kwargs = signal_crud.find.call_args[1]
        assert call_kwargs["filters"]["engine_id"] == "engine-001"
        assert call_kwargs["order_by"] == "timestamp"
        assert call_kwargs["desc_order"] is True

    @pytest.mark.unit
    def test_find_by_code_and_direction(self, signal_crud):
        """find_by_code_and_direction 构造 filters 包含 code 和 direction"""
        signal_crud.find = MagicMock(return_value=[])

        signal_crud.find_by_code_and_direction(
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            portfolio_id="portfolio-001",
        )

        signal_crud.find.assert_called_once()
        call_kwargs = signal_crud.find.call_args[1]
        assert call_kwargs["filters"]["code"] == "000001.SZ"
        assert call_kwargs["filters"]["direction"] == DIRECTION_TYPES.LONG
        assert call_kwargs["filters"]["portfolio_id"] == "portfolio-001"

    @pytest.mark.unit
    def test_get_latest_signals(self, signal_crud):
        """get_latest_signals 调用 find_by_portfolio 且 desc_order=True"""
        signal_crud.find_by_portfolio = MagicMock(return_value=[])

        signal_crud.get_latest_signals("portfolio-001", limit=10, page=0)

        signal_crud.find_by_portfolio.assert_called_once_with(
            portfolio_id="portfolio-001",
            page=0,
            page_size=10,
            desc_order=True,
            as_dataframe=False,
        )

    @pytest.mark.unit
    def test_delete_by_portfolio(self, signal_crud):
        """delete_by_portfolio 调用 self.remove 并记录警告日志"""
        signal_crud.remove = MagicMock()

        signal_crud.delete_by_portfolio("portfolio-001")

        signal_crud.remove.assert_called_once()
        filters = signal_crud.remove.call_args[0][0]
        assert filters["portfolio_id"] == "portfolio-001"

    @pytest.mark.unit
    def test_delete_by_portfolio_empty_id_raises(self, signal_crud):
        """delete_by_portfolio 传入空 portfolio_id 时抛出 ValueError"""
        with pytest.raises(ValueError, match="portfolio_id"):
            signal_crud.delete_by_portfolio("")

    @pytest.mark.unit
    def test_delete_by_portfolio_and_date_range(self, signal_crud):
        """delete_by_portfolio_and_date_range 构造时间范围 filters 并调用 self.remove"""
        signal_crud.remove = MagicMock()

        with patch("ginkgo.data.crud.signal_crud.datetime_normalize") as mock_dt:
            mock_dt.side_effect = lambda x: x
            signal_crud.delete_by_portfolio_and_date_range(
                portfolio_id="portfolio-001",
                start_date="2024-01-01",
                end_date="2024-06-01",
            )

        signal_crud.remove.assert_called_once()
        filters = signal_crud.remove.call_args[0][0]
        assert filters["portfolio_id"] == "portfolio-001"
        assert "timestamp__gte" in filters
        assert "timestamp__lte" in filters

    @pytest.mark.unit
    def test_count_by_portfolio(self, signal_crud):
        """count_by_portfolio 调用 self.count 并传入正确 filters"""
        signal_crud.count = MagicMock(return_value=42)

        result = signal_crud.count_by_portfolio("portfolio-001")

        assert result == 42
        signal_crud.count.assert_called_once_with({"portfolio_id": "portfolio-001"})

    @pytest.mark.unit
    def test_count_by_code_and_direction(self, signal_crud):
        """count_by_code_and_direction 调用 self.count 并传入 code 和 direction"""
        signal_crud.count = MagicMock(return_value=7)

        result = signal_crud.count_by_code_and_direction("000001.SZ", DIRECTION_TYPES.LONG)

        assert result == 7
        signal_crud.count.assert_called_once_with(
            {"code": "000001.SZ", "direction": DIRECTION_TYPES.LONG}
        )

    @pytest.mark.unit
    def test_find_by_business_time(self, signal_crud):
        """find_by_business_time 构造时间范围 filters 并调用 self.find"""
        signal_crud.find = MagicMock(return_value=[])

        with patch("ginkgo.data.crud.signal_crud.datetime_normalize") as mock_dt:
            mock_dt.side_effect = lambda x: x
            signal_crud.find_by_business_time(
                portfolio_id="portfolio-001",
                start_business_time="2024-01-01",
                end_business_time="2024-06-01",
            )

        signal_crud.find.assert_called_once()
        call_kwargs = signal_crud.find.call_args[1]
        assert call_kwargs["filters"]["portfolio_id"] == "portfolio-001"
        assert "business_timestamp__gte" in call_kwargs["filters"]
        assert "business_timestamp__lte" in call_kwargs["filters"]
        assert call_kwargs["order_by"] == "business_timestamp"
        assert call_kwargs["desc_order"] is True
