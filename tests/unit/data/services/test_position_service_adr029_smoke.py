"""PositionService ADR-029 Task 5 写路径 smoke（save / get_df / upsert-create）。

三个方法体被 containers import 链触达但 smoke 不调 → diff coverage gate 红：
- ``save_positions``（L40：走 mapper.entity_to_model 收敛 + 顺修 add(entity) bug）
- ``get_positions_df``（L128：find → models_to_dataframe 出口）
- ``upsert_position`` create 分支（L180：existing=None → mapper.entity_to_model → add）
本 smoke mock crud 调起方法体补覆盖信号。
"""
import pandas as pd

from ginkgo.entities import Position
from ginkgo.data.models.model_position import MPosition
from ginkgo.data.services.position_service import PositionService


class _FakeCrud:
    """记录 add 调用；find 返模型列表；get_position 返 None 触发 upsert 创建分支。"""

    def __init__(self):
        self.added = []

    def add(self, model):
        self.added.append(model)

    def find(self, filters=None, page=None, page_size=None, order_by=None, desc_order=None):
        return [MPosition(portfolio_id="p", engine_id="e", code="000001")]

    def get_position(self, portfolio_id=None, code=None):
        return None  # → upsert else 分支（create）


def _make_position() -> Position:
    return Position(portfolio_id="p", engine_id="e", task_id="t", code="000001", volume=100)


def test_save_positions_persists_via_mapper():
    """save_positions：list 各元素 → PositionMapper.entity_to_model → crud.add（L40）。"""
    crud = _FakeCrud()
    svc = PositionService(crud_repo=crud)
    res = svc.save_positions([_make_position()])
    assert res.success
    assert len(crud.added) == 1
    assert isinstance(crud.added[0], MPosition)  # 锁 mapper.entity_to_model 收敛(顺修 add(entity) bug)


def test_get_positions_df_returns_dataframe():
    """get_positions_df：find → models_to_dataframe（L128）。"""
    svc = PositionService(crud_repo=_FakeCrud())
    res = svc.get_positions_df(portfolio_id="p")
    assert res.success
    assert isinstance(res.data, pd.DataFrame)


def test_upsert_position_create_branch():
    """get_position→None → else 创建分支：mapper.entity_to_model → add（L180）。"""
    crud = _FakeCrud()
    svc = PositionService(crud_repo=crud)
    res = svc.upsert_position(_make_position())
    assert res.success
    assert res.data["created"] is True
    assert len(crud.added) == 1
    assert isinstance(crud.added[0], MPosition)  # 锁创建分支走 mapper.entity_to_model(非裸 entity)
