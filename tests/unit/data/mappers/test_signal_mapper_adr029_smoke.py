"""SignalMapper.model_to_entity 反向映射 smoke（ADR-029 Task 6）。

``model_to_entity``（ORM→Entity：uuid 还原 + business_timestamp 还原，L73/89/90/91）
被 containers import 链触达但 smoke 不调方法体 → diff coverage gate 红。本 smoke
直调 model_to_entity 补覆盖信号，并锁定 ADR-029 新增的 business_timestamp 还原分支。
"""
import datetime

from ginkgo.data.mappers.signal_mapper import SignalMapper
from ginkgo.data.models.model_signal import MSignal


def _make_msignal() -> MSignal:
    """构造字段齐全的 MSignal（Signal entity 构造要求 code/strength/volume 等非 None）。"""
    m = MSignal()
    for k, v in dict(
        portfolio_id="p",
        engine_id="e",
        task_id="t",
        code="000001",
        direction=1,
        source=1,
        reason="r",
        uuid="u",
        volume=100,
        weight=1.0,
        strength=0.5,
        confidence=0.5,
    ).items():
        setattr(m, k, v)
    return m


def test_model_to_entity_restores_uuid():
    """ORM→Entity：uuid 还原（ADR-029 Task 6 补丢 uuid bug，L73/89/91）。"""
    m = _make_msignal()
    ent = SignalMapper.model_to_entity(m)
    assert ent.uuid == "u"


def test_model_to_entity_restores_business_timestamp():
    """business_timestamp 非 None → entity_kwargs 消费分支（L89-91）。"""
    m = _make_msignal()
    m.business_timestamp = datetime.datetime(2025, 1, 2)
    ent = SignalMapper.model_to_entity(m)
    assert ent.business_timestamp == datetime.datetime(2025, 1, 2)
