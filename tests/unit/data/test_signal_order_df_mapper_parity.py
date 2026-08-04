# Upstream: ADR-025（DF 出口下沉 mapper）/ ADR-031 c1（enum 映射经 __table__ 反射）
# Downstream: SignalMapper.models_to_dataframe / OrderMapper.models_to_dataframe
# Role: mapper DF 出口行为单测（enum 还原 / 空 DF / 无副作用）——signal(CH)/order(MySQL)各一组

"""Mapper DF 出口行为单测（ADR-025 / ADR-031 c1）。

历史版本对照 ``Mapper.to_dataframe`` 与 CRUD ``_convert_models_to_dataframe``
输出等价；ADR-029 §Decision 1 退役 CRUD 转换钩子族后，CRUD DF 出口已下沉为
``Mapper.models_to_dataframe``（service 层调用），对照失去一方。本文件保留
mapper 自身行为验证：enum 列还原为 enum 实例、空列表返空 DF、调用无副作用。

模型构造用「空模型 + setattr 原始 int」模拟 DB 读出的原始行（enum 列存 int），
避开 ``__init__`` 的 validate_input，保证 ``__dict__`` 内是干净的 int——这是
``models_to_dataframe`` 的真实输入态。

Run: pytest tests/unit/data/test_signal_order_df_mapper_parity.py -v -o addopts=""
"""

import pandas as pd
import pytest

from ginkgo.data.models import MSignal, MOrder
from ginkgo.enums import (
    DIRECTION_TYPES,
    ORDER_TYPES,
    ORDERSTATUS_TYPES,
    SOURCE_TYPES,
)
from ginkgo.data.mappers.signal_mapper import SignalMapper
from ginkgo.data.mappers.order_mapper import OrderMapper


def _make_signals():
    """两行 MSignal，enum 列原始 int（模拟 DB 行），enum 字段全部显式 set。"""
    rows = []
    for code, direction, source, volume in [
        ("000001.SZ", DIRECTION_TYPES.LONG.value, SOURCE_TYPES.BACKTEST.value, 100),
        ("600000.SH", DIRECTION_TYPES.SHORT.value, SOURCE_TYPES.SIM.value, 200),
    ]:
        m = MSignal()
        m.portfolio_id = "p1"
        m.engine_id = "e1"
        m.task_id = "t1"
        m.code = code
        m.direction = direction  # 原始 int
        m.source = source
        m.volume = volume
        rows.append(m)
    return rows


def _make_orders():
    """两行 MOrder，enum 列原始 int，enum 字段全部显式 set。"""
    rows = []
    for code, direction, otype, status, source, volume, price in [
        (
            "000001.SZ",
            DIRECTION_TYPES.LONG.value,
            ORDER_TYPES.LIMITORDER.value,
            ORDERSTATUS_TYPES.NEW.value,
            SOURCE_TYPES.BACKTEST.value,
            100,
            10.5,
        ),
        (
            "600000.SH",
            DIRECTION_TYPES.SHORT.value,
            ORDER_TYPES.MARKETORDER.value,
            ORDERSTATUS_TYPES.FILLED.value,
            SOURCE_TYPES.SIM.value,
            200,
            20.5,
        ),
    ]:
        m = MOrder()
        m.portfolio_id = "p1"
        m.engine_id = "e1"
        m.task_id = "t1"
        m.uuid = f"u-{code}"
        m.code = code
        m.direction = direction  # 原始 int
        m.order_type = otype
        m.status = status
        m.source = source
        m.volume = volume
        m.limit_price = price
        rows.append(m)
    return rows


@pytest.mark.unit
class TestSignalOrderDfMapperBehavior:
    """Mapper.models_to_dataframe 输出行为（enum 还原 / 空 DF / 无副作用）。"""

    def test_signal_df_enum_columns_are_enum_instances(self):
        """signal DF 的 enum 列经 mapper 还原为 enum 实例（非裸 int）。"""
        df = SignalMapper.models_to_dataframe(_make_signals())
        assert all(isinstance(v, DIRECTION_TYPES) for v in df["direction"])
        assert all(isinstance(v, SOURCE_TYPES) for v in df["source"])

    def test_order_df_enum_columns_are_enum_instances(self):
        """order DF 的 enum 列经 mapper 还原为 enum 实例。"""
        df = OrderMapper.models_to_dataframe(_make_orders())
        assert all(isinstance(v, DIRECTION_TYPES) for v in df["direction"])
        assert all(isinstance(v, ORDER_TYPES) for v in df["order_type"])
        assert all(isinstance(v, ORDERSTATUS_TYPES) for v in df["status"])

    def test_empty_models_returns_empty_df(self):
        """空列表 mapper 返空 DataFrame（边界一致）。"""
        assert SignalMapper.models_to_dataframe([]).empty
        assert OrderMapper.models_to_dataframe([]).empty

    def test_mapper_no_side_effect_on_model(self):
        """mapper 纯转换：调用后 model 的 enum 字段仍是原始 int（未被 setattr 改）。"""
        signals = _make_signals()
        SignalMapper.models_to_dataframe(signals)
        assert isinstance(signals[0].direction, int)
        assert not isinstance(signals[0].direction, DIRECTION_TYPES)

        orders = _make_orders()
        OrderMapper.models_to_dataframe(orders)
        assert isinstance(orders[0].status, int)
        assert not isinstance(orders[0].status, ORDERSTATUS_TYPES)
