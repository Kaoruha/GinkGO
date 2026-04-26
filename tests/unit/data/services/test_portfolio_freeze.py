"""
PortfolioService 冻结相关测试

覆盖 update() 忽略 mode 参数等冻结机制相关行为。
"""

import sys
import os
import pytest
from unittest.mock import MagicMock

_path = os.path.join(os.path.dirname(__file__), '..', '..', '..')
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.data.services.portfolio_service import PortfolioService


def test_update_ignores_mode_parameter():
    """update() 应忽略 mode 参数，不传递到 CRUD 层"""
    service = PortfolioService.__new__(PortfolioService)
    mock_crud = MagicMock()
    service._crud_repo = mock_crud
    service._deployment_crud = None  # avoid freeze check

    result = service.update(
        portfolio_id="test-uuid",
        name="new-name",
        mode=1,  # 应被忽略
    )

    assert result.is_success()
    # 验证 modify 没有收到 mode
    call_args = mock_crud.modify.call_args
    updates = call_args[1]["updates"]
    assert "mode" not in updates
    assert "name" in updates


def test_is_portfolio_frozen_with_active_deployment():
    """有活跃部署时应返回 True"""
    service = PortfolioService.__new__(PortfolioService)
    mock_deployment_crud = MagicMock()
    mock_portfolio_crud = MagicMock()

    mock_deployment = MagicMock()
    mock_deployment.target_portfolio_id = "target-uuid"
    mock_deployment.status = 1  # DEPLOYED
    mock_deployment_crud.find.return_value = [mock_deployment]

    mock_target = MagicMock()
    mock_portfolio_crud.find.return_value = [mock_target]

    service._deployment_crud = mock_deployment_crud
    service._crud_repo = mock_portfolio_crud

    assert service.is_portfolio_frozen("source-uuid") is True


def test_is_portfolio_frozen_no_deployment():
    """无部署记录时应返回 False"""
    service = PortfolioService.__new__(PortfolioService)
    mock_deployment_crud = MagicMock()
    mock_deployment_crud.find.return_value = []
    service._deployment_crud = mock_deployment_crud

    assert service.is_portfolio_frozen("source-uuid") is False


def test_is_portfolio_frozen_target_deleted():
    """target 已删除时应返回 False（可解冻）"""
    service = PortfolioService.__new__(PortfolioService)
    mock_deployment_crud = MagicMock()
    mock_portfolio_crud = MagicMock()

    mock_deployment = MagicMock()
    mock_deployment.target_portfolio_id = "target-uuid"
    mock_deployment.status = 1  # DEPLOYED
    mock_deployment_crud.find.return_value = [mock_deployment]

    # target 已删除
    mock_portfolio_crud.find.return_value = []

    service._deployment_crud = mock_deployment_crud
    service._crud_repo = mock_portfolio_crud

    assert service.is_portfolio_frozen("source-uuid") is False
