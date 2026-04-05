"""
TransferCRUD 单元测试（Mock 数据库连接）

覆盖范围：
- _get_field_config: 字段配置结构与验证规则
- _get_enum_mappings: 枚举映射
- _create_from_params: 参数转 MTransfer 模型
- Business Helper: find_by_portfolio, find_by_status
- 构造与类型检查
"""

import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

from ginkgo.enums import (
    TRANSFERDIRECTION_TYPES,
    MARKET_TYPES,
    TRANSFERSTATUS_TYPES,
    SOURCE_TYPES,
)


# ============================================================
# 辅助：构造 TransferCRUD 实例（mock DB 连接）
# ============================================================


@pytest.fixture
def transfer_crud():
    """构造 TransferCRUD 实例，mock 掉 get_db_connection 避免真实数据库连接"""
    mock_logger = MagicMock()
    with patch("ginkgo.data.crud.base_crud.get_db_connection"), \
         patch("ginkgo.data.crud.base_crud.GLOG", mock_logger), \
         patch("ginkgo.data.crud.transfer_crud.GLOG", mock_logger), \
         patch("ginkgo.data.access_control.service_only", lambda f: f):
        from ginkgo.data.crud.transfer_crud import TransferCRUD
        crud = TransferCRUD()
        crud._logger = mock_logger
        return crud


# ============================================================
# _get_field_config 测试
# ============================================================


class TestTransferCRUDFieldConfig:
    """_get_field_config 字段配置测试"""

    @pytest.mark.unit
    def test_field_config_has_required_keys(self, transfer_crud):
        """配置包含 portfolio_id/engine_id/direction/market/money/status/timestamp/source"""
        config = transfer_crud._get_field_config()

        required_keys = {
            "portfolio_id", "engine_id", "direction", "market",
            "money", "status", "timestamp", "source",
        }
        assert required_keys.issubset(set(config.keys())), \
            f"缺少字段: {required_keys - set(config.keys())}"

    @pytest.mark.unit
    def test_field_config_money_validation(self, transfer_crud):
        """money 字段为数值类型，min=0.01"""
        config = transfer_crud._get_field_config()

        assert "decimal" in config["money"]["type"]
        assert config["money"]["min"] == 0.01

    @pytest.mark.unit
    def test_field_config_direction_is_enum(self, transfer_crud):
        """direction 字段为枚举类型"""
        config = transfer_crud._get_field_config()

        assert config["direction"]["type"] == "enum"
        assert "choices" in config["direction"]

    @pytest.mark.unit
    def test_field_config_status_is_enum(self, transfer_crud):
        """status 字段为枚举类型"""
        config = transfer_crud._get_field_config()

        assert config["status"]["type"] == "enum"
        assert "choices" in config["status"]


# ============================================================
# _get_enum_mappings 测试
# ============================================================


class TestTransferCRUDEnumMappings:
    """_get_enum_mappings 枚举映射测试"""

    @pytest.mark.unit
    def test_enum_mappings_has_four_enums(self, transfer_crud):
        """映射包含 direction/status/market/source 四个枚举"""
        mappings = transfer_crud._get_enum_mappings()

        assert "direction" in mappings
        assert "status" in mappings
        assert "market" in mappings
        assert "source" in mappings
        assert mappings["direction"] is TRANSFERDIRECTION_TYPES
        assert mappings["status"] is TRANSFERSTATUS_TYPES
        assert mappings["market"] is MARKET_TYPES
        assert mappings["source"] is SOURCE_TYPES


# ============================================================
# _create_from_params 测试
# ============================================================


class TestTransferCRUDCreateFromParams:
    """_create_from_params 参数转模型测试"""

    @pytest.mark.unit
    def test_create_from_params_basic(self, transfer_crud):
        """传入完整参数，返回 MTransfer 模型且属性正确"""
        from ginkgo.data.models import MTransfer

        with patch("ginkgo.data.crud.transfer_crud.datetime_normalize") as mock_dt, \
             patch("ginkgo.data.crud.transfer_crud.to_decimal") as mock_decimal:
            mock_dt.return_value = datetime(2024, 1, 15, 10, 30, 0)
            mock_decimal.return_value = Decimal("10000.00")

            params = {
                "portfolio_id": "portfolio-001",
                "engine_id": "engine-001",
                "direction": TRANSFERDIRECTION_TYPES.IN,
                "market": MARKET_TYPES.CHINA,
                "money": Decimal("10000.00"),
                "status": TRANSFERSTATUS_TYPES.PENDING,
            }

            mtransfer = transfer_crud._create_from_params(**params)

            assert isinstance(mtransfer, MTransfer)
            assert mtransfer.portfolio_id == "portfolio-001"
            assert mtransfer.engine_id == "engine-001"
            assert mtransfer.direction == TRANSFERDIRECTION_TYPES.IN.value
            assert mtransfer.market == MARKET_TYPES.CHINA.value
            assert mtransfer.status == TRANSFERSTATUS_TYPES.PENDING.value

    @pytest.mark.unit
    def test_create_from_params_defaults(self, transfer_crud):
        """缺失字段使用默认值"""
        with patch("ginkgo.data.crud.transfer_crud.datetime_normalize") as mock_dt, \
             patch("ginkgo.data.crud.transfer_crud.to_decimal") as mock_decimal:
            mock_dt.return_value = datetime(2024, 1, 15)
            mock_decimal.return_value = Decimal("0")

            mtransfer = transfer_crud._create_from_params()

            assert mtransfer.portfolio_id == ""
            assert mtransfer.engine_id == ""
            assert mtransfer.direction == TRANSFERDIRECTION_TYPES.IN.value
            assert mtransfer.status == TRANSFERSTATUS_TYPES.PENDING.value
            assert mtransfer.source == SOURCE_TYPES.SIM.value


# ============================================================
# Business Helper 测试
# ============================================================


class TestTransferCRUDBusinessHelpers:
    """Business Helper 方法测试"""

    @pytest.mark.unit
    def test_find_by_portfolio(self, transfer_crud):
        """find_by_portfolio 构造正确的 filters 并调用 self.find"""
        transfer_crud.find = MagicMock(return_value=[])

        transfer_crud.find_by_portfolio(portfolio_id="portfolio-001")

        transfer_crud.find.assert_called_once()
        call_kwargs = transfer_crud.find.call_args[1]
        assert call_kwargs["filters"]["portfolio_id"] == "portfolio-001"
        assert call_kwargs["desc_order"] is True
        assert call_kwargs["order_by"] == "timestamp"

    @pytest.mark.unit
    def test_find_by_status(self, transfer_crud):
        """find_by_status 调用 self.find 且 desc_order=True"""
        transfer_crud.find = MagicMock(return_value=[])

        transfer_crud.find_by_status(status=TRANSFERSTATUS_TYPES.FILLED)

        transfer_crud.find.assert_called_once()
        call_kwargs = transfer_crud.find.call_args[1]
        assert call_kwargs["filters"]["status"] == TRANSFERSTATUS_TYPES.FILLED
        assert call_kwargs["desc_order"] is True
        assert call_kwargs["order_by"] == "timestamp"


# ============================================================
# 构造与类型检查测试
# ============================================================


class TestTransferCRUDConstruction:
    """TransferCRUD 构造和类型检查测试"""

    @pytest.mark.unit
    def test_transfer_crud_construction(self, transfer_crud):
        """验证 model_class 为 MTransfer，_is_mysql 为 True"""
        from ginkgo.data.models import MTransfer

        assert transfer_crud.model_class is MTransfer
        assert transfer_crud._is_mysql is True
        assert transfer_crud._is_clickhouse is False

    @pytest.mark.unit
    def test_transfer_crud_has_required_methods(self, transfer_crud):
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
            assert hasattr(transfer_crud, method_name), f"缺少方法: {method_name}"
            assert callable(getattr(transfer_crud, method_name)), f"不可调用: {method_name}"
