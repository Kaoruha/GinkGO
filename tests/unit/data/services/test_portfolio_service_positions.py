"""
#5783: PortfolioService.get_positions 持仓查询（验收2）

背景：数据层 PositionCRUD.find_by_portfolio 早已存在，但 portfolio_service
从未接线持仓查询，portfolio 层无 /positions 端点（验收2 未达标）。
本测试覆盖新增公开方法 get_positions 的行为，序列化字段对齐既有
load_persisted_state（portfolio_service.py:420-440），不引入新数据形状。
"""

import os
import sys
from decimal import Decimal
from unittest.mock import patch, MagicMock

import pytest

_path = os.path.join(os.path.dirname(__file__), '..', '..', '..')
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.data.services.portfolio_service import PortfolioService
from ginkgo.data.services.base_service import ServiceResult


def _make_position(code="000001.SZ", volume=100):
    """构造 mock MPosition（字段对齐 load_persisted_state 序列化）。"""
    m = MagicMock()
    m.portfolio_id = "p1"
    m.engine_id = "e1"
    m.task_id = "t1"
    m.code = code
    m.cost = Decimal("10.5")
    m.volume = volume
    m.frozen_volume = 0
    m.settlement_frozen_volume = 0
    m.settlement_days = 0
    m.settlement_queue_json = None
    m.frozen_money = Decimal("0")
    m.price = Decimal("11.0")
    m.fee = Decimal("5")
    m.uuid = "u-" + code
    return m


@pytest.fixture
def service_with_positions():
    """PortfolioService + mock position crud（含 1 活跃 + 1 零仓位）。"""
    active = _make_position("000001.SZ", 100)
    closed = _make_position("600000.SH", 0)
    mock_crud = MagicMock()
    mock_crud.find_by_portfolio.return_value = [active, closed]
    mock_crud.get_active_positions.return_value = [active]
    with patch("ginkgo.libs.GLOG"):
        svc = PortfolioService(
            crud_repo=MagicMock(),
            portfolio_file_mapping_crud=MagicMock(),
        )
    svc._get_position_crud = lambda: mock_crud
    return svc, mock_crud


@pytest.mark.unit
class TestPortfolioServiceGetPositions:
    """#5783: get_positions 持仓查询行为。"""

    def test_get_positions_returns_all_serialized(self, service_with_positions):
        """get_positions 返回 portfolio 全部持仓，字段序列化对齐 load_persisted_state。"""
        svc, mock_crud = service_with_positions
        result = svc.get_positions("p1")

        assert result.is_success()
        assert len(result.data) == 2
        first = result.data[0]
        assert first["code"] == "000001.SZ"
        assert first["volume"] == 100
        # Decimal 经 str() 序列化（对齐 load_persisted_state:430）
        assert first["cost"] == "10.5"
        assert first["price"] == "11.0"
        mock_crud.find_by_portfolio.assert_called_once_with("p1")

    def test_get_positions_active_only_filters_zero_volume(self, service_with_positions):
        """active_only=True 只返回 volume>0 持仓（走 get_active_positions）。"""
        svc, mock_crud = service_with_positions
        result = svc.get_positions("p1", active_only=True)

        assert result.is_success()
        assert len(result.data) == 1
        assert result.data[0]["code"] == "000001.SZ"
        assert result.data[0]["volume"] == 100
        mock_crud.get_active_positions.assert_called_once_with("p1")
        mock_crud.find_by_portfolio.assert_not_called()

    def test_get_positions_empty_portfolio_returns_empty_list(self):
        """无持仓的 portfolio 返回空列表（非错误，不抛异常）。"""
        mock_crud = MagicMock()
        mock_crud.find_by_portfolio.return_value = []
        with patch("ginkgo.libs.GLOG"):
            svc = PortfolioService(
                crud_repo=MagicMock(),
                portfolio_file_mapping_crud=MagicMock(),
            )
        svc._get_position_crud = lambda: mock_crud

        result = svc.get_positions("empty-portfolio")

        assert result.is_success()
        assert result.data == []
