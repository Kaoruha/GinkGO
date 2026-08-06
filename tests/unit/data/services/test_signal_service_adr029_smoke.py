"""SignalService ADR-029 Task 6 写路径 smoke（add + get_signals_df）。

``add``（kwargs→Signal entity→SignalMapper→crud.add，退役隐式 _create_from_params
hook）+ ``get_signals_df``（出口① DataFrame）被 containers import 链触达但 smoke
不调方法体 → diff coverage gate 红。本 smoke mock crud 调起方法体补覆盖信号。
"""
import datetime

import pandas as pd

from ginkgo.enums import DIRECTION_TYPES
from ginkgo.data.models.model_signal import MSignal
from ginkgo.data.services.signal_service import SignalService


class _FakeCrud:
    def __init__(self):
        self.added = []

    def add(self, model):
        self.added.append(model)

    def find(self, filters=None, page=None, page_size=None, order_by=None, desc_order=None):
        return [MSignal()]


def test_add_signal_persists_via_mapper():
    """add：Signal entity → SignalMapper.entity_to_model → crud.add（L66-96）。"""
    crud = _FakeCrud()
    svc = SignalService(crud_repo=crud)
    res = svc.add(
        portfolio_id="p",
        engine_id="e",
        task_id="t",
        code="000001",
        direction=DIRECTION_TYPES.LONG,
        reason="momentum",
    )
    assert res.success
    assert len(crud.added) == 1
    assert isinstance(crud.added[0], MSignal)  # 锁 mapper.entity_to_model 收敛(非裸 entity)


def test_get_signals_df_returns_dataframe():
    """get_signals_df：find→[MSignal()] → models_to_dataframe（L216）产非空 DF。
    补 ``assert not empty`` 锁住出口真调了转换——回退/跳过 L216（→ else pd.DataFrame()
    空 DF）则断言 FAIL（silent-pass 防护，与 result_service DF 出口同形）。"""
    svc = SignalService(crud_repo=_FakeCrud())
    res = svc.get_signals_df(engine_id="e")
    assert res.success
    assert isinstance(res.data, pd.DataFrame)
    assert not res.data.empty  # 锁 L216 真产非空 DF(回退→空 DF→FAIL)


def test_add_signal_with_explicit_timestamp():
    """传 timestamp → entity.timestamp 覆盖分支（L84-85）。"""
    crud = _FakeCrud()
    svc = SignalService(crud_repo=crud)
    res = svc.add(
        portfolio_id="p",
        engine_id="e",
        task_id="t",
        code="000001",
        direction=DIRECTION_TYPES.LONG,
        reason="r",
        timestamp="2025-01-02",
    )
    assert res.success
    # 锁 L84-85 覆盖分支:timestamp 经 datetime_normalize 存 datetime(2025,1,2)。
    # 若删掉该 if,entity.timestamp 回退 TimeMixin 默认(now)→ 此断言失败。
    assert crud.added[0].timestamp == datetime.datetime(2025, 1, 2)


class _BoomCrud:
    def add(self, model):
        raise RuntimeError("db down")

    def find(self, **kwargs):
        raise RuntimeError("db down")


def test_add_signal_exception_returns_error():
    """crud.add 抛异常 → except → ServiceResult.error（L94-96）。"""
    svc = SignalService(crud_repo=_BoomCrud())
    res = svc.add(
        portfolio_id="p",
        engine_id="e",
        task_id="t",
        code="000001",
        direction=DIRECTION_TYPES.LONG,
        reason="r",
    )
    assert not res.success
