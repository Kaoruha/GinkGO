"""
Unit tests for PositionService.

Verifies that PositionService orchestrates position persistence
through PositionCRUD, providing the `save_positions` interface
that PortfolioLive depends on.

ADR-029 Task 5:service 走 mapper.entity_to_model 收敛转换 + 顺修 add(entity) bug。
测试改用真实 Position entity,验证 add 收到 MPosition 而非 raw entity。
"""
import pandas as pd
import pytest
from unittest.mock import MagicMock, call

from ginkgo.data.services.position_service import PositionService
from ginkgo.data.services.base_service import ServiceResult
from ginkgo.data.models import MPosition
from ginkgo.entities import Position


@pytest.fixture
def mock_crud():
    return MagicMock()


@pytest.fixture
def service(mock_crud):
    return PositionService(crud_repo=mock_crud)


@pytest.fixture
def mock_position():
    """Real Position entity(替代旧 MagicMock duck-type)。

    ADR-029 后 service 内部走 PositionMapper.entity_to_model 转换,真实 entity
    才能验证转换链路。MagicMock 在 mapper 内 decimal 转换炸,且无法验证
    「add 收到 MPosition 而非 raw entity」契约。
    """
    return Position(
        portfolio_id="p-001",
        engine_id="e-001",
        task_id="t-001",
        code="000001.SZ",
        cost=10.5,
        volume=100,
        frozen_volume=0,
        frozen_money=0,
        price=11.0,
        fee=0.5,
    )


class TestSavePositions:
    """save_positions is the primary interface used by PortfolioLive."""

    def test_empty_list(self, service, mock_crud):
        result = service.save_positions([])
        assert result.is_success()
        # Should delete existing then create none
        mock_crud.delete_by_portfolio.assert_not_called()

    def test_saves_positions_via_add(self, service, mock_crud, mock_position):
        result = service.save_positions([mock_position])

        assert result.is_success()
        # ADR-029 Task 5:add 收 MPosition(经 mapper.entity_to_model 转换),非 raw entity
        mock_crud.add.assert_called_once()
        added = mock_crud.add.call_args[0][0]
        assert isinstance(added, MPosition)
        assert added.code == "000001.SZ"
        assert int(added.volume) == 100
        # 不走 create(model 实例应走 add 路径)
        mock_crud.create.assert_not_called()

    def test_multiple_positions(self, service, mock_crud, mock_position):
        pos2 = Position(
            portfolio_id="p-001",
            engine_id="e-001",
            task_id="t-001",
            code="600000.SH",
            cost=20.0,
            volume=200,
            frozen_volume=0,
            frozen_money=0,
            price=21.0,
            fee=1.0,
        )

        result = service.save_positions([mock_position, pos2])
        assert result.is_success()
        assert mock_crud.add.call_count == 2
        # 两次 add 都收 MPosition(转换链路完整)
        for call_args in mock_crud.add.call_args_list:
            assert isinstance(call_args[0][0], MPosition)

    def test_crud_failure_returns_error(self, service, mock_crud, mock_position):
        mock_crud.add.side_effect = Exception("DB write failed")

        result = service.save_positions([mock_position])
        assert result.is_success() is False
        assert "DB write failed" in result.error


class TestGetPositions:
    """Query positions by portfolio."""

    def test_find_by_portfolio(self, service, mock_crud):
        mock_crud.find_by_portfolio.return_value = []

        result = service.get_positions("p-001")
        assert result.is_success()
        mock_crud.find_by_portfolio.assert_called_once_with("p-001")

    def test_get_portfolio_value(self, service, mock_crud):
        mock_crud.get_portfolio_value.return_value = {
            "total_market_value": 10000,
            "total_cost": 9000,
        }

        result = service.get_portfolio_value("p-001")
        assert result.is_success()
        assert result.data["total_market_value"] == 10000


class TestGetPositionsDfFilters:
    """get_positions_df 的 engine_id/task_id 过滤透传（#4743）

    PositionModel 与 Signal/Order 对称持有 engine_id + task_id，
    但 position 的 filter builder 仅连了 portfolio_id。此处验证三维过滤透传。
    """

    def test_filters_by_engine_and_task(self, service, mock_crud):
        """engine_id + task_id 应透传到 crud.find 的 filters"""
        model_list = MagicMock()
        model_list.to_dataframe.return_value = pd.DataFrame()
        mock_crud.find.return_value = model_list

        service.get_positions_df(
            portfolio_id="p1", engine_id="e1", task_id="t1"
        )

        _, kwargs = mock_crud.find.call_args
        filters = kwargs["filters"]
        assert filters == {
            "is_del": False,
            "portfolio_id": "p1",
            "engine_id": "e1",
            "task_id": "t1",
        }

    def test_omits_unset_filters(self, service, mock_crud):
        """未传的过滤维度不应进入 filters（避免误加 None）"""
        model_list = MagicMock()
        model_list.to_dataframe.return_value = pd.DataFrame()
        mock_crud.find.return_value = model_list

        service.get_positions_df(portfolio_id="p1")

        _, kwargs = mock_crud.find.call_args
        assert kwargs["filters"] == {"is_del": False, "portfolio_id": "p1"}
