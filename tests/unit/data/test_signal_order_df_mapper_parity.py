# Upstream: ADR-025（DF 出口下沉 mapper）/ ADR-031 c1（enum 映射经 __table__ 反射）
# Downstream: SignalMapper.to_dataframe / OrderMapper.to_dataframe vs _Conversion._convert_models_to_dataframe
# Role: 对照实证 mapper DF 出口与 CRUD DF 出口同构（signal=CH / order=MySQL 各一组）


"""DF 下沉 mapper 对照实证（ADR-025 / ADR-031 Future Work）。

验证 ``Mapper.to_dataframe(models)`` 与 CRUD ``_convert_models_to_dataframe``
输出等价——signal(ClickHouse)与 order(MySQL)各一组。enum 映射两路同源（均经
``__table__.columns[].info['enum']`` 反射，ADR-031 c1），故 DataFrame 同构。

行为差异（非输出差异）：CRUD 版有副作用（setattr 改 model 的 enum 字段），
mapper 版纯转换（改 dict 副本，不动 model）。测试用 deepcopy 隔离两路输入，
确保对照公平；并显式断言 mapper 无副作用。

模型构造用「空模型 + setattr 原始 int」模拟 DB 读出的原始行（enum 列存 int），
避开 ``__init__`` 的 validate_input，保证 ``__dict__`` 内是干净的 int——这是
``to_dataframe`` 的真实输入态。enum 字段须全部显式 set：CRUD 路 ``hasattr``
经 SA 描述符对 enum 列恒 True（default -1），mapper 路 ``d.get`` 只看 ``__dict__``，
未显式 set 的 enum 列会让两路 DataFrame 列集分歧。

Stub 继承 ``_Conversion`` 提供 ``model_class``，避免实例化 CRUD 连库（与 c1
反射测试 ``test_signal_enum_reflection_c1`` 同模式）；signal/order CRUD 均
未 override ``_convert_models_to_dataframe``，故 Stub 的混入实现即真实路径。

Run: pytest tests/unit/data/test_signal_order_df_mapper_parity.py -v -o addopts=""
"""

import copy

import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from ginkgo.data.models import MSignal, MOrder
from ginkgo.enums import (
    DIRECTION_TYPES,
    ORDER_TYPES,
    ORDERSTATUS_TYPES,
    SOURCE_TYPES,
)
from ginkgo.data.crud.mixins._conversion import _Conversion
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


class _SignalConv(_Conversion):
    """Stub：提供 model_class 即可走 _convert_models_to_dataframe 真实路径。"""

    model_class = MSignal


class _OrderConv(_Conversion):
    model_class = MOrder


@pytest.mark.unit
class TestSignalOrderDfMapperParity:
    """Mapper.to_dataframe 与 CRUD _convert_models_to_dataframe 输出同构。"""

    def test_signal_df_mapper_equals_crud(self):
        """signal：mapper DF == CRUD DF（同源模型 deepcopy 给两路，check_like 忽略列序）。

        构造一次再 deepcopy：base model ``__init__`` 自动生成 uuid/create_at
        （随机/now），两次 ``_make_signals()`` 会产出不同自动字段——必须同源。
        deepcopy 必要：CRUD 版 setattr 有副作用，不隔离会污染 mapper 输入。
        """
        base = _make_signals()
        crud_df = _SignalConv()._convert_models_to_dataframe(copy.deepcopy(base))
        mapper_df = SignalMapper.to_dataframe(copy.deepcopy(base))
        assert_frame_equal(mapper_df, crud_df, check_like=True)

    def test_order_df_mapper_equals_crud(self):
        """order：mapper DF == CRUD DF（同源 deepcopy，理由同 signal）。"""
        base = _make_orders()
        crud_df = _OrderConv()._convert_models_to_dataframe(copy.deepcopy(base))
        mapper_df = OrderMapper.to_dataframe(copy.deepcopy(base))
        assert_frame_equal(mapper_df, crud_df, check_like=True)

    def test_signal_df_enum_columns_are_enum_instances(self):
        """signal DF 的 enum 列经 mapper 还原为 enum 实例（非裸 int）。"""
        df = SignalMapper.to_dataframe(_make_signals())
        assert all(isinstance(v, DIRECTION_TYPES) for v in df["direction"])
        assert all(isinstance(v, SOURCE_TYPES) for v in df["source"])

    def test_order_df_enum_columns_are_enum_instances(self):
        """order DF 的 enum 列经 mapper 还原为 enum 实例。"""
        df = OrderMapper.to_dataframe(_make_orders())
        assert all(isinstance(v, DIRECTION_TYPES) for v in df["direction"])
        assert all(isinstance(v, ORDER_TYPES) for v in df["order_type"])
        assert all(isinstance(v, ORDERSTATUS_TYPES) for v in df["status"])

    def test_empty_models_returns_empty_df(self):
        """空列表两路都返空 DataFrame（边界一致）。"""
        assert SignalMapper.to_dataframe([]).empty
        assert OrderMapper.to_dataframe([]).empty
        assert _SignalConv()._convert_models_to_dataframe([]).empty

    def test_mapper_no_side_effect_on_model(self):
        """mapper 纯转换：调用后 model 的 enum 字段仍是原始 int（未被 setattr 改）。

        对照 CRUD 版的副作用——这是 mapper 优于 CRUD 的点（无突变）。
        """
        signals = _make_signals()
        SignalMapper.to_dataframe(signals)
        assert isinstance(signals[0].direction, int)
        assert not isinstance(signals[0].direction, DIRECTION_TYPES)

        orders = _make_orders()
        OrderMapper.to_dataframe(orders)
        assert isinstance(orders[0].status, int)
        assert not isinstance(orders[0].status, ORDERSTATUS_TYPES)
