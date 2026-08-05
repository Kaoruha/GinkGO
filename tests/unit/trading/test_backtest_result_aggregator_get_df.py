"""BacktestResultAggregator._get_dataframe 分支 smoke（ADR-029 Task 11 聚合出口）。

``_get_dataframe``（ServiceResult→DataFrame 出口：error/None→None、DataFrame 直返、
list→models_to_dataframe、其它→None，L195/207/208）被 containers import 链触达但
smoke 不调 → diff coverage gate 红。本 smoke 用 dummy self 直调覆盖各分支。
"""
import pandas as pd

from ginkgo.trading.analysis.backtest_result_aggregator import BacktestResultAggregator
from ginkgo.data.services.base_service import ServiceResult


def _call(result):
    """_get_dataframe 方法体不引用 self，用 dummy self 直调。"""
    return BacktestResultAggregator._get_dataframe(object(), result)


def test_get_dataframe_empty_list_returns_dataframe():
    """success + 空list → models_to_dataframe 假分支 → 空 DataFrame（L195/207/208）。"""
    out = _call(ServiceResult.success(data=[]))
    assert isinstance(out, pd.DataFrame)
    assert out.empty


def test_get_dataframe_error_result_returns_none():
    """error result → not is_success → None。"""
    assert _call(ServiceResult.error("boom")) is None


def test_get_dataframe_none_data_returns_none():
    """success + data=None → None。"""
    assert _call(ServiceResult.success(data=None)) is None


def test_get_dataframe_dataframe_passthrough():
    """success + DataFrame → 原样直返。"""
    df = pd.DataFrame({"a": [1]})
    out = _call(ServiceResult.success(data=df))
    pd.testing.assert_frame_equal(out, df)


def test_get_dataframe_unsupported_type_returns_none():
    """success + 非 DataFrame/list → None。"""
    assert _call(ServiceResult.success(data="not-supported")) is None
