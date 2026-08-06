"""PortfolioService ADR-029 §Decision 1 batch 收敛 smoke（persist_portfolio_state）。

F3 已锁 PositionService.save_positions 的 **add path**（单 entity → crud.add）；
persist_portfolio_state 的 **batch path**（L402：list[Position] → PositionMapper.
entity_to_model → position_crud.batch_create，注释"Position 实体 → MPosition，ADR-010"）
是兄弟盲区。本 smoke 补锁，使 §Decision 1 在 portfolio 持仓持久化路径也有锚点。
"""
from unittest.mock import MagicMock

from ginkgo.entities import Position
from ginkgo.data.models.model_position import MPosition
from ginkgo.data.services.portfolio_service import PortfolioService


def test_persist_portfolio_state_batch_via_mapper():
    """persist_portfolio_state：state['positions'] 各 Position → PositionMapper.
    entity_to_model → position_crud.batch_create（L402,ADR-010 收敛）。

    锁 batch path mapper 收敛（F8a,F3 add-path 同形）：回退 L402（跳过 mapper，
    裸 Position 直送 batch_create）则 isinstance(MPosition) FAIL。
    """
    main_crud = MagicMock()
    pos_crud = MagicMock()
    svc = PortfolioService(
        crud_repo=main_crud,
        portfolio_file_mapping_crud=MagicMock(),
    )
    svc._get_position_crud = lambda: pos_crud  # 注入 position crud

    pos = Position(portfolio_id="p", engine_id="e", task_id="t", code="000001", volume=100)
    state = {"cash": "100", "frozen": "0", "fee": "0", "positions": [pos]}

    res = svc.persist_portfolio_state("pid", state)
    assert res.success
    pos_crud.delete_by_portfolio.assert_called_once_with("pid")
    pos_crud.batch_create.assert_called_once()
    batch_arg = pos_crud.batch_create.call_args[0][0]
    assert len(batch_arg) == 1
    assert isinstance(batch_arg[0], MPosition)  # 锁 mapper.entity_to_model 收敛(非裸 entity)
