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
