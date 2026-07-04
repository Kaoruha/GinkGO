"""TDD for bar_adjustment DF 出口契约切换 -- #6625

ADR-010 出口①：复权因子读取改走 ``AdjustfactorService.get_adjustfactors_df``，
``ServiceResult.data`` 即 ``pandas.DataFrame``，不再 ``result.data.to_dataframe()``。

本文件锁定的行为（与 #5501 排序回归解耦，专注契约语义）：
- path1 ``get_precomputed_adjustment_factors``：成功（预计算列）/ 空 / 异常
- path2 ``apply_price_adjustment``：成功（K 线复权）/ 空 / 异常

排序方向正确性由 ``test_bar_adjustment_sort_order.py`` 覆盖（#5501）。
"""
from unittest.mock import MagicMock

import pandas as pd

from ginkgo.data.services import bar_adjustment
from ginkgo.data.services.base_service import ServiceResult
from ginkgo.enums import ADJUSTMENT_TYPES


def _df_service(df: pd.DataFrame, success: bool = True) -> MagicMock:
    """构造 mock：get_adjustfactors_df 返 ServiceResult(data=df)。"""
    mock_svc = MagicMock()
    mock_svc.get_adjustfactors_df.return_value = ServiceResult(
        success=success, message="mock", data=df,
    )
    return mock_svc


class TestGetPrecomputedFactorsDFContract:
    """path1: get_precomputed_adjustment_factors 消费 DF 出口。"""

    def test_success_with_precomputed_factor_column_returned_directly(self):
        """DF 已含 foreadjustfactor 列 → 直接返回 [timestamp, factor] 子集。

        命中 ``if factor_column in df_factors.columns`` 早出分支（非临时因子计算）。
        """
        df = pd.DataFrame({
            "timestamp": ["2025-01-01", "2025-01-02"],
            "foreadjustfactor": [1.0, 1.1],
            "backadjustfactor": [1.0, 0.9],
            "adjustfactor": [1.0, 1.1],
        })
        svc = _df_service(df)

        result = bar_adjustment.get_precomputed_adjustment_factors(
            code="000001.SZ",
            dates=["2025-01-01", "2025-01-02"],
            adjustment_type=ADJUSTMENT_TYPES.FORE,
            adjustfactor_service=svc,
        )

        assert list(result.columns) == ["timestamp", "foreadjustfactor"]
        assert len(result) == 2
        # 必须走 DF 出口，不能再调 .get() + to_dataframe()
        svc.get_adjustfactors_df.assert_called_once()
        svc.get.assert_not_called()

    def test_empty_result_returns_empty_df_with_expected_columns(self):
        """service 返空 DataFrame → 返回 [timestamp, factor_column] 空壳。"""
        svc = _df_service(pd.DataFrame())

        result = bar_adjustment.get_precomputed_adjustment_factors(
            code="000001.SZ",
            dates=["2025-01-01"],
            adjustment_type=ADJUSTMENT_TYPES.FORE,
            adjustfactor_service=svc,
        )

        assert result.empty
        assert list(result.columns) == ["timestamp", "foreadjustfactor"]

    def test_failure_returns_empty_df(self):
        """service success=False → 返回空 DF（不抛异常）。"""
        svc = _df_service(pd.DataFrame(), success=False)

        result = bar_adjustment.get_precomputed_adjustment_factors(
            code="000001.SZ",
            dates=["2025-01-01"],
            adjustment_type=ADJUSTMENT_TYPES.BACK,
            adjustfactor_service=svc,
        )

        assert result.empty
        assert list(result.columns) == ["timestamp", "backadjustfactor"]


class TestApplyPriceAdjustmentDFContract:
    """path2: apply_price_adjustment 消费 DF 出口。"""

    @staticmethod
    def _bars_df() -> pd.DataFrame:
        return pd.DataFrame({
            "code": ["000001.SZ", "000001.SZ"],
            "timestamp": ["2025-01-01", "2025-01-02"],
            "open": [10.0, 11.0],
            "high": [11.0, 12.0],
            "low": [9.0, 10.0],
            "close": [10.5, 11.5],
            "volume": [1000, 1100],
            "amount": [10500.0, 12650.0],
        })

    def test_success_applies_fore_factor_to_prices(self):
        """FORE 因子=2.0 → 所有价格 ×2（向量化 merge 复权）。"""
        factors = pd.DataFrame({
            "timestamp": ["2025-01-01", "2025-01-02"],
            "foreadjustfactor": [2.0, 2.0],
        })
        svc = _df_service(factors)
        bars = self._bars_df()

        result = bar_adjustment.apply_price_adjustment(
            bars_data=bars, code="000001.SZ",
            adjustment_type=ADJUSTMENT_TYPES.FORE, adjustfactor_service=svc,
        )

        assert isinstance(result, pd.DataFrame)
        assert result["close"].tolist() == [21.0, 23.0]
        svc.get_adjustfactors_df.assert_called_once()
        svc.get.assert_not_called()

    def test_empty_factors_returns_original_bars(self):
        """service 返空 DF → 原始 bars 不变（仅格式透传）。"""
        svc = _df_service(pd.DataFrame())
        bars = self._bars_df()

        result = bar_adjustment.apply_price_adjustment(
            bars_data=bars, code="000001.SZ",
            adjustment_type=ADJUSTMENT_TYPES.FORE, adjustfactor_service=svc,
        )

        assert result.equals(bars)

    def test_failure_returns_original_bars(self):
        """service success=False → 原始 bars 不变。"""
        svc = _df_service(pd.DataFrame(), success=False)
        bars = self._bars_df()

        result = bar_adjustment.apply_price_adjustment(
            bars_data=bars, code="000001.SZ",
            adjustment_type=ADJUSTMENT_TYPES.BACK, adjustfactor_service=svc,
        )

        assert result.equals(bars)
