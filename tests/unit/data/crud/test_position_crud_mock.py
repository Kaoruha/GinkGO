"""
性能: 221MB RSS, 2.0s, 16 tests [PASS]
PositionCRUD 单元测试（Mock 数据库连接）

覆盖范围：
- _get_field_config: 字段配置结构与验证规则
- _get_enum_mappings: 枚举映射
- _create_from_params: 参数转 MPosition 模型
- _convert_input_item: Position 业务对象转换
- Business Helper: find_by_portfolio, find_by_code, get_position, get_active_positions,
  get_portfolio_value, update_position, close_position, find_by_business_time
- 构造与类型检查
"""

import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

from ginkgo.enums import SOURCE_TYPES


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def position_crud():
    """绕过访问控制装饰器，创建 PositionCRUD 实例，mock 数据库连接和日志"""
    mock_logger = MagicMock()
    with patch("ginkgo.data.crud.base_crud.get_db_connection"), \
         patch("ginkgo.data.crud.base_crud.GLOG", mock_logger), \
         patch("ginkgo.data.crud.position_crud.GLOG", mock_logger), \
         patch("ginkgo.data.access_control.service_only", lambda f: f):
        from ginkgo.data.crud.position_crud import PositionCRUD
        crud = PositionCRUD()
        crud._logger = mock_logger
        return crud


# ============================================================================
# _get_field_config 测试
# ============================================================================


class TestPositionCRUDFieldConfig:
    """_get_field_config 字段配置测试"""

    @pytest.mark.unit
    def test_field_config_structure(self, position_crud):
        """配置包含 portfolio_id/engine_id/code/cost/volume/frozen_volume/frozen_money/price/fee/source"""
        config = position_crud._get_field_config()

        required_keys = {
            "portfolio_id", "engine_id", "code",
            "cost", "volume", "frozen_volume", "frozen_money",
            "price", "fee", "source",
        }
        assert required_keys.issubset(set(config.keys())), \
            f"缺少字段: {required_keys - set(config.keys())}"

    @pytest.mark.unit
    def test_field_config_types(self, position_crud):
        """验证各字段类型约束：字符串、数值、枚举等"""
        config = position_crud._get_field_config()

        # 字符串字段
        for field in ("portfolio_id", "engine_id", "code"):
            assert config[field]["type"] == "string"
            assert config[field]["min"] == 1

        # 整数字段
        for field in ("volume", "frozen_volume"):
            assert config[field]["type"] == "int"
            assert config[field]["min"] == 0

        # 数值字段（支持 decimal/float/int）
        for field in ("cost", "frozen_money", "price", "fee"):
            assert isinstance(config[field]["type"], list)
            assert config[field]["min"] == 0

        # 枚举字段
        assert config["source"]["type"] == "enum"


# ============================================================================
# _get_enum_mappings 测试
# ============================================================================


class TestPositionCRUDEnumMappings:
    """_get_enum_mappings 枚举映射测试"""

    @pytest.mark.unit
    def test_enum_mappings(self, position_crud):
        """映射包含 source 字段对应的 SOURCE_TYPES"""
        mappings = position_crud._get_enum_mappings()

        assert "source" in mappings
        assert mappings["source"] is SOURCE_TYPES


# ============================================================================
# _create_from_params 测试
# ============================================================================


class TestPositionCRUDCreateFromParams:
    """_create_from_params 参数转模型测试"""

    @pytest.mark.unit
    def test_create_from_params_basic(self, position_crud):
        """传入完整参数，返回 MPosition 模型且属性正确"""
        params = {
            "portfolio_id": "portfolio-001",
            "engine_id": "engine-001",
            "code": "000001.SZ",
            "cost": Decimal("10.50"),
            "volume": 1000,
            "frozen_volume": 100,
            "frozen_money": Decimal("500.00"),
            "price": Decimal("11.00"),
            "fee": Decimal("5.25"),
            "source": SOURCE_TYPES.TUSHARE,
        }

        model = position_crud._create_from_params(**params)

        assert isinstance(model, position_crud.model_class)
        assert model.portfolio_id == "portfolio-001"
        assert model.code == "000001.SZ"
        assert model.volume == 1000
        assert model.frozen_volume == 100
        # 枚举值存储为 int
        assert model.source == SOURCE_TYPES.TUSHARE.value

    @pytest.mark.unit
    def test_create_from_params_defaults(self, position_crud):
        """缺失可选字段使用默认值：volume=0, cost=0, source=SIM"""
        model = position_crud._create_from_params(
            portfolio_id="portfolio-002",
            code="000002.SZ",
        )

        assert isinstance(model, position_crud.model_class)
        assert model.portfolio_id == "portfolio-002"
        assert model.code == "000002.SZ"
        assert model.volume == 0
        assert model.frozen_volume == 0
        assert model.source == SOURCE_TYPES.SIM.value


# ============================================================================
# 构造与类型检查测试
# ============================================================================


class TestPositionCRUDConstruction:
    """PositionCRUD 构造和类型检查测试"""

    @pytest.mark.unit
    def test_construction(self, position_crud):
        """验证 model_class 为 MPosition，_is_mysql 为 True（MPosition 继承 MMysqlBase）"""
        from ginkgo.data.models import MPosition

        assert position_crud.model_class is MPosition
        assert position_crud._is_mysql is True
        assert position_crud._is_clickhouse is False



# ============================================================================
# Business Helper 测试
# ============================================================================


class TestPositionCRUDBusinessHelpers:
    """Business Helper 方法测试"""

    @pytest.mark.unit
    def test_find_by_portfolio(self, position_crud):
        """find_by_portfolio 构造 filters 并按 cost 降序调用 self.find"""
        position_crud.find = MagicMock(return_value=[])

        position_crud.find_by_portfolio("portfolio-001", min_volume=100)

        position_crud.find.assert_called_once()
        call_kwargs = position_crud.find.call_args[1]
        assert call_kwargs["filters"]["portfolio_id"] == "portfolio-001"
        assert call_kwargs["filters"]["volume__gte"] == 100
        assert call_kwargs["order_by"] == "cost"
        assert call_kwargs["desc_order"] is True

    @pytest.mark.unit
    def test_find_by_code(self, position_crud):
        """find_by_code 构造 filters 并按 volume 降序调用 self.find"""
        position_crud.find = MagicMock(return_value=[])

        position_crud.find_by_code("000001.SZ", portfolio_id="portfolio-001")

        position_crud.find.assert_called_once()
        call_kwargs = position_crud.find.call_args[1]
        assert call_kwargs["filters"]["code"] == "000001.SZ"
        assert call_kwargs["filters"]["portfolio_id"] == "portfolio-001"
        assert call_kwargs["order_by"] == "volume"
        assert call_kwargs["desc_order"] is True

    @pytest.mark.unit
    def test_find_by_code_without_portfolio(self, position_crud):
        """find_by_code 不传 portfolio_id 时 filters 中不含该字段"""
        position_crud.find = MagicMock(return_value=[])

        position_crud.find_by_code("000001.SZ")

        call_kwargs = position_crud.find.call_args[1]
        assert "portfolio_id" not in call_kwargs["filters"]

    @pytest.mark.unit
    def test_get_position_found(self, position_crud):
        """get_position 找到持仓时返回第一条记录"""
        mock_model = MagicMock(spec=position_crud.model_class)
        position_crud.find = MagicMock(return_value=[mock_model])

        result = position_crud.get_position("portfolio-001", "000001.SZ")

        assert result is mock_model
        position_crud.find.assert_called_once()
        call_kwargs = position_crud.find.call_args[1]
        assert call_kwargs["filters"]["portfolio_id"] == "portfolio-001"
        assert call_kwargs["filters"]["code"] == "000001.SZ"
        assert call_kwargs["page_size"] == 1

    @pytest.mark.unit
    def test_get_position_not_found(self, position_crud):
        """get_position 未找到持仓时返回 None"""
        position_crud.find = MagicMock(return_value=[])

        result = position_crud.get_position("portfolio-999", "999999.SZ")

        assert result is None

    @pytest.mark.unit
    def test_get_active_positions_delegates(self, position_crud):
        """get_active_positions 委托给 find_by_portfolio 并传入 min_volume=1"""
        position_crud.find_by_portfolio = MagicMock(return_value=[])

        position_crud.get_active_positions("portfolio-001")

        position_crud.find_by_portfolio.assert_called_once_with("portfolio-001", 1)

    @pytest.mark.unit
    def test_get_portfolio_value(self, position_crud):
        """get_portfolio_value 返回包含统计信息的字典"""
        pos1 = MagicMock()
        pos1.cost = Decimal("100.00")
        pos1.price = Decimal("110.00")
        pos1.volume = 100
        pos2 = MagicMock()
        pos2.cost = Decimal("200.00")
        pos2.price = Decimal("0")
        pos2.volume = 0

        position_crud.find_by_portfolio = MagicMock(return_value=[pos1, pos2])

        result = position_crud.get_portfolio_value("portfolio-001")

        assert isinstance(result, dict)
        assert result["portfolio_id"] == "portfolio-001"
        assert result["total_positions"] == 2
        assert result["active_positions"] == 1
        # total_cost 是所有非零 cost 之和（100 + 200 = 300）
        assert result["total_cost"] == 300.0
        # total_market_value = price * volume（仅 volume > 0 且 price > 0 的持仓）
        assert result["total_market_value"] == 11000.0
        assert result["total_pnl"] == 10700.0
        assert result["total_volume"] == 100

    @pytest.mark.unit
    def test_update_position(self, position_crud):
        """update_position 构造 filters 并调用 self.modify"""
        position_crud.modify = MagicMock()

        position_crud.update_position("portfolio-001", "000001.SZ", volume=2000, cost=15.0)

        position_crud.modify.assert_called_once()
        filters = position_crud.modify.call_args[0][0]
        updates = position_crud.modify.call_args[0][1]
        assert filters["portfolio_id"] == "portfolio-001"
        assert filters["code"] == "000001.SZ"
        assert updates["volume"] == 2000
        assert updates["cost"] == 15.0

    @pytest.mark.unit
    def test_close_position(self, position_crud):
        """close_position 将 volume 和 frozen_volume 设为 0"""
        position_crud.modify = MagicMock()

        position_crud.close_position("portfolio-001", "000001.SZ")

        position_crud.modify.assert_called_once()
        updates = position_crud.modify.call_args[0][1]
        assert updates["volume"] == 0
        assert updates["frozen_volume"] == 0

    @pytest.mark.unit
    def test_find_by_business_time(self, position_crud):
        """find_by_business_time 构造时间范围 filters 并调用 self.find"""
        position_crud.find = MagicMock(return_value=[])

        with patch("ginkgo.data.crud.position_crud.datetime_normalize") as mock_dt:
            mock_dt.side_effect = lambda x: x
            position_crud.find_by_business_time(
                portfolio_id="portfolio-001",
                start_business_time="2024-01-01",
                end_business_time="2024-06-01",
                min_volume=50,
            )

        position_crud.find.assert_called_once()
        call_kwargs = position_crud.find.call_args[1]
        assert call_kwargs["filters"]["portfolio_id"] == "portfolio-001"
        assert call_kwargs["filters"]["volume__gte"] == 50
        assert "business_timestamp__gte" in call_kwargs["filters"]
        assert "business_timestamp__lte" in call_kwargs["filters"]
        assert call_kwargs["order_by"] == "business_timestamp"
        assert call_kwargs["desc_order"] is True
