"""
性能: 219MB RSS, 1.9s, 11 tests [PASS]
CapitalAdjustmentCRUD 单元测试（Mock 数据库连接）

覆盖范围：
- _get_field_config: 字段配置结构与验证规则
- _get_enum_mappings: 枚举映射
- _create_from_params: 参数转 MCapitalAdjustment 模型
- Business Helper: find_by_portfolio, get_total_adjustment
- 构造与类型检查
"""

import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

from ginkgo.enums import SOURCE_TYPES


# ============================================================
# 辅助：构造 CapitalAdjustmentCRUD 实例（mock DB 连接）
# ============================================================


@pytest.fixture
def capital_adjustment_crud():
    """构造 CapitalAdjustmentCRUD 实例，mock 掉 get_db_connection 避免真实数据库连接"""
    mock_logger = MagicMock()
    with patch("ginkgo.data.crud.base_crud.get_db_connection"), \
         patch("ginkgo.data.crud.base_crud.GLOG", mock_logger), \
         patch("ginkgo.data.crud.capital_adjustment_crud.GLOG", mock_logger), \
         patch("ginkgo.data.access_control.service_only", lambda f: f):
        from ginkgo.data.crud.capital_adjustment_crud import CapitalAdjustmentCRUD
        crud = CapitalAdjustmentCRUD()
        crud._logger = mock_logger
        return crud


# ============================================================
# _get_field_config 测试
# ============================================================


class TestCapitalAdjustmentCRUDFieldConfig:
    """_get_field_config 字段配置测试"""

    @pytest.mark.unit
    def test_field_config_has_required_keys(self, capital_adjustment_crud):
        """配置包含 portfolio_id/timestamp/amount/reason/source/business_timestamp"""
        config = capital_adjustment_crud._get_field_config()

        required_keys = {
            "portfolio_id", "timestamp", "amount", "reason",
            "source", "business_timestamp",
        }
        assert required_keys.issubset(set(config.keys())), \
            f"缺少字段: {required_keys - set(config.keys())}"

    @pytest.mark.unit
    def test_field_config_portfolio_id_is_string(self, capital_adjustment_crud):
        """portfolio_id 字段类型为 string，min=1"""
        config = capital_adjustment_crud._get_field_config()

        assert config["portfolio_id"]["type"] == "string"
        assert config["portfolio_id"]["min"] == 1

    @pytest.mark.unit
    def test_field_config_amount_is_numeric(self, capital_adjustment_crud):
        """amount 字段支持 decimal/float/int"""
        config = capital_adjustment_crud._get_field_config()

        assert isinstance(config["amount"]["type"], list)

    @pytest.mark.unit
    def test_field_config_reason_max_length(self, capital_adjustment_crud):
        """reason 字段 max=200"""
        config = capital_adjustment_crud._get_field_config()

        assert config["reason"]["max"] == 200


# ============================================================
# _get_enum_mappings 测试
# ============================================================


class TestCapitalAdjustmentCRUDEnumMappings:
    """_get_enum_mappings 枚举映射测试"""

    @pytest.mark.unit
    def test_enum_mappings_has_source(self, capital_adjustment_crud):
        """映射包含 source 枚举"""
        mappings = capital_adjustment_crud._get_enum_mappings()

        assert "source" in mappings
        assert mappings["source"] is SOURCE_TYPES


# ============================================================
# _create_from_params 测试
# ============================================================


class TestCapitalAdjustmentCRUDCreateFromParams:
    """_create_from_params 参数转模型测试"""

    @pytest.mark.unit
    def test_create_from_params_basic(self, capital_adjustment_crud):
        """传入完整参数，返回 MCapitalAdjustment 模型且属性正确"""
        params = {
            "portfolio_id": "portfolio-001",
            "timestamp": datetime(2024, 1, 15),
            "amount": Decimal("100000.00"),
            "reason": "初始资金",
            "source": SOURCE_TYPES.SIM,
        }

        model = capital_adjustment_crud._create_from_params(**params)

        assert model.portfolio_id == "portfolio-001"
        assert model.amount == Decimal("100000.00")
        assert model.reason == "初始资金"

    @pytest.mark.unit
    def test_create_from_params_defaults(self, capital_adjustment_crud):
        """缺失字段使用默认值"""
        model = capital_adjustment_crud._create_from_params(
            portfolio_id="portfolio-001",
        )

        assert model.portfolio_id == "portfolio-001"
        assert model.amount == Decimal("0")
        assert model.reason == ""
        assert model.source == SOURCE_TYPES.SIM.value

    @pytest.mark.unit
    def test_create_from_params_timestamp_normalized(self, capital_adjustment_crud):
        """timestamp 经过 datetime_normalize 处理"""
        with patch("ginkgo.data.crud.capital_adjustment_crud.datetime_normalize") as mock_normalize:
            mock_normalize.return_value = datetime(2024, 6, 1)

            model = capital_adjustment_crud._create_from_params(
                portfolio_id="p1",
                timestamp="2024-06-01",
            )

            mock_normalize.assert_called()
            assert model.timestamp == datetime(2024, 6, 1)


# ============================================================
# Business Helper 测试
# ============================================================


class TestCapitalAdjustmentCRUDBusinessHelpers:
    """Business Helper 方法测试"""

    @pytest.mark.unit
    def test_find_by_portfolio(self, capital_adjustment_crud):
        """find_by_portfolio 构造正确的 filters 并调用 self.find"""
        capital_adjustment_crud.find = MagicMock(return_value=[])

        with patch("ginkgo.data.crud.capital_adjustment_crud.datetime_normalize") as mock_dt:
            mock_dt.side_effect = lambda x: x
            capital_adjustment_crud.find_by_portfolio(
                portfolio_id="portfolio-001",
                start_date="2024-01-01",
                end_date="2024-12-31",
            )

        capital_adjustment_crud.find.assert_called_once()
        call_kwargs = capital_adjustment_crud.find.call_args[1]
        assert call_kwargs["filters"]["portfolio_id"] == "portfolio-001"
        assert call_kwargs["order_by"] == "timestamp"

    @pytest.mark.unit
    def test_get_total_adjustment(self, capital_adjustment_crud):
        """get_total_adjustment 返回所有调整金额之和"""
        mock_adj1 = MagicMock()
        mock_adj1.amount = Decimal("100000.00")
        mock_adj2 = MagicMock()
        mock_adj2.amount = Decimal("50000.00")

        capital_adjustment_crud.find = MagicMock(return_value=[mock_adj1, mock_adj2])

        result = capital_adjustment_crud.get_total_adjustment("portfolio-001")

        assert result == 150000.0


# ============================================================
# 构造与类型检查测试
# ============================================================


class TestCapitalAdjustmentCRUDConstruction:
    """CapitalAdjustmentCRUD 构造和类型检查测试"""

    @pytest.mark.unit
    def test_capital_adjustment_crud_construction(self, capital_adjustment_crud):
        """验证 model_class 为 MCapitalAdjustment，_is_clickhouse 为 True"""
        from ginkgo.data.models import MCapitalAdjustment

        assert capital_adjustment_crud.model_class is MCapitalAdjustment
        assert capital_adjustment_crud._is_clickhouse is True
        assert capital_adjustment_crud._is_mysql is False

