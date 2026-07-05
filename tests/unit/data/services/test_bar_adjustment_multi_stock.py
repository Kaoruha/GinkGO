"""Tests for batch adjustfactor prefetch in apply_price_adjustment_multi_stock -- #6588

Verifies the N+1 elimination: multi-stock entry prefetches the full-market
adjustfactor in a single service call (code=None) instead of one call per code.

Adapted to ADR-010 exit-① (get_adjustfactors_df): result.data is already a DataFrame.
"""
import pandas as pd
import pytest
from unittest.mock import MagicMock

try:
    from ginkgo.data.services import bar_adjustment
    from ginkgo.enums import ADJUSTMENT_TYPES
    from ginkgo.libs import to_decimal as to_dec
    HAS_MODULE = True
except ImportError:
    HAS_MODULE = False

pytestmark = pytest.mark.skipif(not HAS_MODULE, reason="bar_adjustment not importable")


def _make_bars_df():
    """3 股 × 1 日 bars"""
    return pd.DataFrame([
        {"code": "000001.SZ", "timestamp": pd.Timestamp("2025-01-01"),
         "open": 10.0, "high": 11.0, "low": 9.0, "close": 10.0,
         "volume": 1000, "amount": 10000.0},
        {"code": "000002.SZ", "timestamp": pd.Timestamp("2025-01-01"),
         "open": 20.0, "high": 21.0, "low": 19.0, "close": 20.0,
         "volume": 2000, "amount": 40000.0},
        {"code": "600000.SH", "timestamp": pd.Timestamp("2025-01-01"),
         "open": 5.0, "high": 5.5, "low": 4.5, "close": 5.0,
         "volume": 500, "amount": 2500.0},
    ])


def _make_factors_df(codes, factor=2.0):
    """全市场 factors（含 code 列，用于按 code 切分）"""
    return pd.DataFrame([
        {"code": c, "timestamp": pd.Timestamp("2025-01-01"),
         "foreadjustfactor": factor, "backadjustfactor": 1.0 / factor,
         "adjustfactor": factor}
        for c in codes
    ])


def _make_service(factors_df):
    """mock adjustfactor_service：get_adjustfactors_df 返回 ServiceResult-like，data=factors_df (DataFrame)。

    ADR-010 出口①：data 已是 DataFrame，不再走 to_dataframe()。
    """
    svc = MagicMock()
    result = MagicMock()
    result.success = True
    result.data = factors_df
    svc.get_adjustfactors_df.return_value = result
    return svc


class TestMultiStockBatchPrefetch:
    def test_prefetch_calls_get_once_with_code_none(self):
        """N>1 股输入：get_adjustfactors_df 恰好调用 1 次，且 code=None（全市场预取）"""
        bars_df = _make_bars_df()
        svc = _make_service(_make_factors_df(["000001.SZ", "000002.SZ", "600000.SH"]))

        bar_adjustment.apply_price_adjustment_multi_stock(
            bars_df, ADJUSTMENT_TYPES.FORE, svc)

        assert svc.get_adjustfactors_df.call_count == 1
        _, kwargs = svc.get_adjustfactors_df.call_args
        assert kwargs.get("code", None) is None

    def test_prefetch_applies_factors_per_code(self):
        """预取路径仍正确复权：close * foreadjustfactor(2.0)"""
        bars_df = _make_bars_df()
        svc = _make_service(_make_factors_df(["000001.SZ", "000002.SZ", "600000.SH"]))

        out = bar_adjustment.apply_price_adjustment_multi_stock(
            bars_df, ADJUSTMENT_TYPES.FORE, svc)

        assert isinstance(out, pd.DataFrame)
        # 每股 close 翻倍
        for code, orig_close in [("000001.SZ", 10.0), ("000002.SZ", 20.0), ("600000.SH", 5.0)]:
            row = out[out["code"] == code].iloc[0]
            assert row["close"] == pytest.approx(orig_close * 2.0)

    def test_prefetch_result_equivalent_to_per_stock(self):
        """预取路径结果与逐股路径等价（同样输入下输出一致）"""
        bars_df = _make_bars_df()
        codes = ["000001.SZ", "000002.SZ", "600000.SH"]
        factors_all = _make_factors_df(codes)

        # 批量路径：multi_stock 一次预取全市场
        svc_batch = _make_service(factors_all)
        out_batch = bar_adjustment.apply_price_adjustment_multi_stock(
            bars_df.copy(), ADJUSTMENT_TYPES.FORE, svc_batch)

        # 逐股路径：每股独立 apply_price_adjustment（代表既单股计算）
        # apply_price_adjustment 现走 ADR-010 出口① get_adjustfactors_df
        svc_per = MagicMock()
        per_results = {}
        for c in codes:
            r = MagicMock()
            r.success = True
            r.data = factors_all[factors_all["code"] == c].reset_index(drop=True)
            per_results[c] = r
        svc_per.get_adjustfactors_df.side_effect = lambda **kw: per_results[kw["code"]]
        per_dfs = []
        for c in codes:
            stock = bars_df[bars_df["code"] == c].copy()
            per_dfs.append(bar_adjustment.apply_price_adjustment(
                stock, c, ADJUSTMENT_TYPES.FORE, svc_per))
        out_per = pd.concat(per_dfs, ignore_index=True)

        # 比较核心数值（忽略行序）
        pd.testing.assert_frame_equal(
            out_batch.sort_values(["code", "timestamp"]).reset_index(drop=True),
            out_per.sort_values(["code", "timestamp"]).reset_index(drop=True),
            check_dtype=False,
        )

    def test_empty_dataframe_returns_empty(self):
        """空 DataFrame 输入直接返回（不查 service）"""
        svc = MagicMock()
        out = bar_adjustment.apply_price_adjustment_multi_stock(
            pd.DataFrame(), ADJUSTMENT_TYPES.FORE, svc)
        assert out.empty
        svc.get_adjustfactors_df.assert_not_called()

    def test_empty_modellist_returns_empty(self):
        """空 ModelList 输入直接返回（不查 service）"""
        svc = MagicMock()
        out = bar_adjustment.apply_price_adjustment_multi_stock(
            [], ADJUSTMENT_TYPES.FORE, svc)
        assert out == []
        svc.get_adjustfactors_df.assert_not_called()

    def test_no_factors_returns_original_per_code(self):
        """预取 factors 为空时，每股指数据原样返回（仍只调 1 次 get_adjustfactors_df）"""
        bars_df = _make_bars_df()
        svc = MagicMock()
        empty_result = MagicMock()
        empty_result.success = False
        empty_result.data = pd.DataFrame()
        svc.get_adjustfactors_df.return_value = empty_result

        out = bar_adjustment.apply_price_adjustment_multi_stock(
            bars_df, ADJUSTMENT_TYPES.FORE, svc)

        assert svc.get_adjustfactors_df.call_count == 1
        # 无 factors → 原值未变
        assert set(out["code"]) == {"000001.SZ", "000002.SZ", "600000.SH"}
        assert out[out["code"] == "000001.SZ"]["close"].iloc[0] == 10.0

    def test_modellist_input_prefetch_path(self):
        """ModelList 输入也走预取路径（get_adjustfactors_df 恰好 1 次，code=None）"""
        from ginkgo.data.models import MBar

        bars = []
        for code, close in [("000001.SZ", 10.0), ("000002.SZ", 20.0)]:
            bar = MBar()
            bar.code = code
            bar.timestamp = pd.Timestamp("2025-01-01")
            bar.open = to_dec(close)
            bar.high = to_dec(close + 1)
            bar.low = to_dec(close - 1)
            bar.close = to_dec(close)
            bar.volume = 1000
            bar.amount = to_dec(close * 1000)
            bars.append(bar)

        factors_all = _make_factors_df(["000001.SZ", "000002.SZ"])
        svc = _make_service(factors_all)

        out = bar_adjustment.apply_price_adjustment_multi_stock(
            bars, ADJUSTMENT_TYPES.FORE, svc)

        assert svc.get_adjustfactors_df.call_count == 1
        _, kwargs = svc.get_adjustfactors_df.call_args
        assert kwargs.get("code", None) is None
        assert len(out) == 2
        # 复权应用：close * 2.0
        out_by_code = {b.code: float(b.close) for b in out}
        assert out_by_code["000001.SZ"] == pytest.approx(20.0)
        assert out_by_code["000002.SZ"] == pytest.approx(40.0)
