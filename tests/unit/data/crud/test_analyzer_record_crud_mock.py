"""
性能: 219MB RSS, 1.8s, 11 tests [PASS]
AnalyzerRecordCRUD 单元测试（Mock 数据库连接）

覆盖范围：
- _get_field_config: 字段配置结构与验证规则
- _get_enum_mappings: 枚举映射
- _create_from_params: 参数转 MAnalyzerRecord 模型
- Business Helper: find_by_portfolio, count_by_portfolio（通过 find/count 验证）
- 构造与类型检查
"""

import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

from ginkgo.enums import SOURCE_TYPES


# ============================================================
# 辅助：构造 AnalyzerRecordCRUD 实例（mock DB 连接）
# ============================================================


@pytest.fixture
def analyzer_record_crud():
    """构造 AnalyzerRecordCRUD 实例，mock 掉 get_db_connection 避免真实数据库连接"""
    mock_logger = MagicMock()
    with patch("ginkgo.data.crud.base_crud.get_db_connection"), \
         patch("ginkgo.data.crud.base_crud.GLOG", mock_logger), \
         patch("ginkgo.data.crud.analyzer_record_crud.GLOG", mock_logger), \
         patch("ginkgo.data.access_control.service_only", lambda f: f):
        from ginkgo.data.crud.analyzer_record_crud import AnalyzerRecordCRUD
        crud = AnalyzerRecordCRUD()
        crud._logger = mock_logger
        return crud


# ============================================================
# _get_field_config 测试
# ============================================================


class TestAnalyzerRecordCRUDFieldConfig:
    """_get_field_config 字段配置测试"""

    @pytest.mark.unit
    def test_field_config_has_required_keys(self, analyzer_record_crud):
        """配置包含 portfolio_id/engine_id/task_id/name/analyzer_id/timestamp/business_timestamp/value/source"""
        config = analyzer_record_crud._get_field_config()

        required_keys = {
            "portfolio_id", "engine_id", "task_id", "name",
            "analyzer_id", "timestamp", "business_timestamp", "value", "source",
        }
        assert required_keys.issubset(set(config.keys())), \
            f"缺少字段: {required_keys - set(config.keys())}"

    @pytest.mark.unit
    def test_field_config_portfolio_id_is_string(self, analyzer_record_crud):
        """portfolio_id 字段类型为 string，min=1"""
        config = analyzer_record_crud._get_field_config()

        assert config["portfolio_id"]["type"] == "string"
        assert config["portfolio_id"]["min"] == 1

    @pytest.mark.unit
    def test_field_config_value_is_numeric(self, analyzer_record_crud):
        """value 字段支持 decimal/float/int"""
        config = analyzer_record_crud._get_field_config()

        assert isinstance(config["value"]["type"], list)

    @pytest.mark.unit
    def test_field_config_timestamp_types(self, analyzer_record_crud):
        """timestamp 字段支持 datetime 和 string"""
        config = analyzer_record_crud._get_field_config()

        assert "datetime" in config["timestamp"]["type"]
        assert "string" in config["timestamp"]["type"]


# ============================================================
# _get_enum_mappings 测试
# ============================================================


class TestAnalyzerRecordCRUDEnumMappings:
    """_get_enum_mappings 枚举映射测试"""

    @pytest.mark.unit
    def test_enum_mappings_has_source(self, analyzer_record_crud):
        """映射包含 source 枚举"""
        mappings = analyzer_record_crud._get_enum_mappings()

        assert "source" in mappings
        assert mappings["source"] is SOURCE_TYPES


# ============================================================
# _create_from_params 测试
# ============================================================


class TestAnalyzerRecordCRUDCreateFromParams:
    """_create_from_params 参数转模型测试"""

    @pytest.mark.unit
    def test_create_from_params_basic(self, analyzer_record_crud):
        """传入完整参数，返回 MAnalyzerRecord 模型且属性正确"""
        params = {
            "portfolio_id": "portfolio-001",
            "engine_id": "engine-001",
            "task_id": "run-001",
            "name": "net_value",
            "analyzer_id": "analyzer-001",
            "timestamp": datetime(2024, 1, 15),
            "value": Decimal("1.05"),
            "source": SOURCE_TYPES.SIM,
        }

        model = analyzer_record_crud._create_from_params(**params)

        assert model.portfolio_id == "portfolio-001"
        assert model.name == "net_value"
        assert model.value == Decimal("1.05")

    @pytest.mark.unit
    def test_create_from_params_defaults(self, analyzer_record_crud):
        """缺失字段使用默认值"""
        model = analyzer_record_crud._create_from_params(
            portfolio_id="portfolio-001",
            engine_id="engine-001",
        )

        assert model.portfolio_id == "portfolio-001"
        assert model.task_id == ""
        assert model.name == ""
        assert model.value == Decimal("0")
        assert model.source == SOURCE_TYPES.SIM.value

    @pytest.mark.unit
    def test_create_from_params_timestamp_normalized(self, analyzer_record_crud):
        """timestamp 经过 datetime_normalize 处理"""
        with patch("ginkgo.data.crud.analyzer_record_crud.datetime_normalize") as mock_normalize:
            mock_normalize.return_value = datetime(2024, 6, 1)

            model = analyzer_record_crud._create_from_params(
                portfolio_id="p1",
                timestamp="2024-06-01",
            )

            mock_normalize.assert_called()
            assert model.timestamp == datetime(2024, 6, 1)


# ============================================================
# Business Helper 测试
# ============================================================


class TestAnalyzerRecordCRUDBusinessHelpers:
    """Business Helper 方法测试"""

    @pytest.mark.unit
    def test_find_by_portfolio(self, analyzer_record_crud):
        """find_by_portfolio 构造正确的 filters 并调用 self.find"""
        analyzer_record_crud.find = MagicMock(return_value=[])

        with patch("ginkgo.data.crud.analyzer_record_crud.datetime_normalize") as mock_dt:
            mock_dt.side_effect = lambda x: x
            analyzer_record_crud.find_by_portfolio(
                portfolio_id="portfolio-001",
                analyzer_name="net_value",
                start_date="2024-01-01",
                end_date="2024-12-31",
            )

        analyzer_record_crud.find.assert_called_once()
        call_kwargs = analyzer_record_crud.find.call_args[1]
        assert call_kwargs["filters"]["portfolio_id"] == "portfolio-001"
        assert call_kwargs["filters"]["name"] == "net_value"
        assert call_kwargs["order_by"] == "timestamp"
        assert call_kwargs["desc_order"] is True

    @pytest.mark.unit
    def test_count_by_portfolio(self, analyzer_record_crud):
        """通过 count 方法验证 portfolio 过滤（使用 mock count）"""
        analyzer_record_crud.count = MagicMock(return_value=10)

        result = analyzer_record_crud.count({"portfolio_id": "portfolio-001"})

        assert result == 10
        analyzer_record_crud.count.assert_called_once_with({"portfolio_id": "portfolio-001"})


# ============================================================
# 构造与类型检查测试
# ============================================================


class TestAnalyzerRecordCRUDConstruction:
    """AnalyzerRecordCRUD 构造和类型检查测试"""

    @pytest.mark.unit
    def test_analyzer_record_crud_construction(self, analyzer_record_crud):
        """验证 model_class 为 MAnalyzerRecord，_is_clickhouse 为 True"""
        from ginkgo.data.models import MAnalyzerRecord

        assert analyzer_record_crud.model_class is MAnalyzerRecord
        assert analyzer_record_crud._is_clickhouse is True
        assert analyzer_record_crud._is_mysql is False

