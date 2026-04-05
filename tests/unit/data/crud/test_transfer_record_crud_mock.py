"""
TransferRecordCRUD 单元测试（Mock 数据库连接）

覆盖范围：
- _get_field_config: 字段配置结构与验证规则
- _get_enum_mappings: 枚举映射（TRANSFERDIRECTION_TYPES, MARKET_TYPES, TRANSFERSTATUS_TYPES, SOURCE_TYPES）
- _create_from_params: 参数转 MTransferRecord 模型
- Business Helper: find_by_portfolio, get_total_transfer_amount
- 构造与类型检查
"""

import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

from ginkgo.enums import TRANSFERDIRECTION_TYPES, MARKET_TYPES, TRANSFERSTATUS_TYPES, SOURCE_TYPES


# ============================================================
# 辅助：构造 TransferRecordCRUD 实例（mock DB 连接）
# ============================================================


@pytest.fixture
def transfer_record_crud():
    """构造 TransferRecordCRUD 实例，mock 掉 get_db_connection 避免真实数据库连接"""
    mock_logger = MagicMock()
    with patch("ginkgo.data.crud.base_crud.get_db_connection"), \
         patch("ginkgo.data.crud.base_crud.GLOG", mock_logger), \
         patch("ginkgo.data.crud.transfer_record_crud.GLOG", mock_logger), \
         patch("ginkgo.data.access_control.service_only", lambda f: f):
        from ginkgo.data.crud.transfer_record_crud import TransferRecordCRUD
        crud = TransferRecordCRUD()
        crud._logger = mock_logger
        return crud


# ============================================================
# _get_field_config 测试
# ============================================================


class TestTransferRecordCRUDFieldConfig:
    """_get_field_config 字段配置测试"""

    @pytest.mark.unit
    def test_field_config_has_required_keys(self, transfer_record_crud):
        """配置包含 portfolio_id/direction/market/money/status/timestamp/source"""
        config = transfer_record_crud._get_field_config()

        required_keys = {
            "portfolio_id", "direction", "market", "money",
            "status", "timestamp", "source",
        }
        assert required_keys.issubset(set(config.keys())), \
            f"缺少字段: {required_keys - set(config.keys())}"

    @pytest.mark.unit
    def test_field_config_portfolio_id_is_string(self, transfer_record_crud):
        """portfolio_id 字段类型为 string，min=1"""
        config = transfer_record_crud._get_field_config()

        assert config["portfolio_id"]["type"] == "string"
        assert config["portfolio_id"]["min"] == 1

    @pytest.mark.unit
    def test_field_config_money_min(self, transfer_record_crud):
        """money 字段 min=0.01"""
        config = transfer_record_crud._get_field_config()

        assert config["money"]["min"] == 0.01

    @pytest.mark.unit
    def test_field_config_direction_is_enum(self, transfer_record_crud):
        """direction 字段类型为 enum"""
        config = transfer_record_crud._get_field_config()

        assert config["direction"]["type"] == "enum"


# ============================================================
# _get_enum_mappings 测试
# ============================================================


class TestTransferRecordCRUDEnumMappings:
    """_get_enum_mappings 枚举映射测试"""

    @pytest.mark.unit
    def test_enum_mappings_has_all_enums(self, transfer_record_crud):
        """映射包含 transferdirection/market/source/transferstatus 四个枚举"""
        mappings = transfer_record_crud._get_enum_mappings()

        assert "transferdirection" in mappings
        assert "market" in mappings
        assert "source" in mappings
        assert "transferstatus" in mappings
        assert mappings["transferdirection"] is TRANSFERDIRECTION_TYPES
        assert mappings["market"] is MARKET_TYPES
        assert mappings["source"] is SOURCE_TYPES
        assert mappings["transferstatus"] is TRANSFERSTATUS_TYPES


# ============================================================
# _create_from_params 测试
# ============================================================


class TestTransferRecordCRUDCreateFromParams:
    """_create_from_params 参数转模型测试"""

    @pytest.mark.unit
    def test_create_from_params_basic(self, transfer_record_crud):
        """传入完整参数，返回 MTransferRecord 模型且属性正确"""
        params = {
            "portfolio_id": "portfolio-001",
            "direction": TRANSFERDIRECTION_TYPES.IN,
            "market": MARKET_TYPES.CHINA,
            "money": Decimal("100000.00"),
            "status": TRANSFERSTATUS_TYPES.SUBMITTED,
            "timestamp": datetime(2024, 1, 15),
            "source": SOURCE_TYPES.SIM,
        }

        model = transfer_record_crud._create_from_params(**params)

        assert model.portfolio_id == "portfolio-001"
        assert model.money == Decimal("100000.00")

    @pytest.mark.unit
    def test_create_from_params_defaults(self, transfer_record_crud):
        """缺失字段使用默认值"""
        model = transfer_record_crud._create_from_params(
            portfolio_id="portfolio-001",
        )

        assert model.portfolio_id == "portfolio-001"
        assert model.money == Decimal("0")
        assert model.source == SOURCE_TYPES.SIM.value

    @pytest.mark.unit
    def test_create_from_params_timestamp_normalized(self, transfer_record_crud):
        """timestamp 经过 datetime_normalize 处理"""
        with patch("ginkgo.data.crud.transfer_record_crud.datetime_normalize") as mock_normalize:
            mock_normalize.return_value = datetime(2024, 6, 1)

            model = transfer_record_crud._create_from_params(
                portfolio_id="p1",
                timestamp="2024-06-01",
            )

            mock_normalize.assert_called()
            assert model.timestamp == datetime(2024, 6, 1)


# ============================================================
# Business Helper 测试
# ============================================================


class TestTransferRecordCRUDBusinessHelpers:
    """Business Helper 方法测试"""

    @pytest.mark.unit
    def test_find_by_portfolio(self, transfer_record_crud):
        """find_by_portfolio 构造正确的 filters 并调用 self.find"""
        transfer_record_crud.find = MagicMock(return_value=[])

        with patch("ginkgo.data.crud.transfer_record_crud.datetime_normalize") as mock_dt:
            mock_dt.side_effect = lambda x: x
            transfer_record_crud.find_by_portfolio(
                portfolio_id="portfolio-001",
                direction=TRANSFERDIRECTION_TYPES.IN,
                start_date="2024-01-01",
                end_date="2024-12-31",
            )

        transfer_record_crud.find.assert_called_once()
        call_kwargs = transfer_record_crud.find.call_args[1]
        assert call_kwargs["filters"]["portfolio_id"] == "portfolio-001"
        assert call_kwargs["filters"]["direction"] == TRANSFERDIRECTION_TYPES.IN
        assert call_kwargs["order_by"] == "timestamp"

    @pytest.mark.unit
    def test_get_total_transfer_amount(self, transfer_record_crud):
        """get_total_transfer_amount 返回所有转账金额之和"""
        mock_record1 = MagicMock()
        mock_record1.money = Decimal("50000.00")
        mock_record2 = MagicMock()
        mock_record2.money = Decimal("30000.00")

        transfer_record_crud.find = MagicMock(return_value=[mock_record1, mock_record2])

        with patch("ginkgo.data.crud.transfer_record_crud.datetime_normalize", lambda x: x):
            result = transfer_record_crud.get_total_transfer_amount(
                portfolio_id="portfolio-001",
                direction=TRANSFERDIRECTION_TYPES.IN,
            )

        assert result == 80000.0


# ============================================================
# 构造与类型检查测试
# ============================================================


class TestTransferRecordCRUDConstruction:
    """TransferRecordCRUD 构造和类型检查测试"""

    @pytest.mark.unit
    def test_transfer_record_crud_construction(self, transfer_record_crud):
        """验证 model_class 为 MTransferRecord，_is_clickhouse 为 True"""
        from ginkgo.data.models import MTransferRecord

        assert transfer_record_crud.model_class is MTransferRecord
        assert transfer_record_crud._is_clickhouse is True
        assert transfer_record_crud._is_mysql is False

    @pytest.mark.unit
    def test_transfer_record_crud_has_required_methods(self, transfer_record_crud):
        """验证 BaseCRUD 的关键 hook 方法都存在且可调用"""
        required_methods = [
            "_do_add", "_do_find", "_do_modify", "_do_remove", "_do_count",
            "_get_field_config", "_get_enum_mappings",
            "_create_from_params", "_convert_input_item",
        ]

        for method_name in required_methods:
            assert hasattr(transfer_record_crud, method_name), f"缺少方法: {method_name}"
            assert callable(getattr(transfer_record_crud, method_name)), f"不可调用: {method_name}"
