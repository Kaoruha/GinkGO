"""Smoke test for bar_adjustment module -- #3823"""
import pytest
from unittest.mock import MagicMock, patch

import pandas as pd

try:
    from ginkgo.data.services import bar_adjustment
    HAS_MODULE = True
except ImportError:
    HAS_MODULE = False


@pytest.mark.skipif(not HAS_MODULE, reason="ginkgo.data.services.bar_adjustment not importable")
class TestBarAdjustmentSmoke:
    """冒烟测试：验证模块可导入及公开函数可调用"""

    def test_module_importable(self):
        assert hasattr(bar_adjustment, "convert_modellist_to_dataframe")
        assert hasattr(bar_adjustment, "calculate_adjusted_prices")
        assert hasattr(bar_adjustment, "apply_price_adjustment")

    def test_convert_modellist_to_dataframe_with_df(self):
        """传入 DataFrame 时直接返回拷贝"""
        df = pd.DataFrame({"code": ["000001.SZ"], "close": [10.0]})
        result = bar_adjustment.convert_modellist_to_dataframe(df)
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1

    def test_convert_modellist_to_dataframe_with_modellist(self):
        """传入 list[MBar] 时手动反射字段构造 DataFrame

        ADR-029 §Decision 9：``convert_modellist_to_dataframe`` 不再走
        ``bars_data.to_dataframe()``（list 无此方法），改为直接反射 bar 字段。
        """
        mock_bar = MagicMock()
        mock_bar.code = "000001.SZ"
        mock_bar.timestamp = "2025-01-01"
        mock_bar.open = 10.0
        mock_bar.high = 11.0
        mock_bar.low = 9.0
        mock_bar.close = 10.5
        mock_bar.volume = 1000
        mock_bar.amount = 10500.0
        result = bar_adjustment.convert_modellist_to_dataframe([mock_bar])
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert result.iloc[0]["code"] == "000001.SZ"

    def test_calculate_adjusted_prices_callable(self):
        """calculate_adjusted_prices 在无复权因子时原样返回"""
        from ginkgo.enums import ADJUSTMENT_TYPES

        bars_df = pd.DataFrame({
            "timestamp": ["2025-01-01"],
            "open": [10.0], "high": [11.0], "low": [9.0], "close": [10.5],
            "volume": [1000], "amount": [10500.0],
        })
        factors_df = pd.DataFrame({
            "timestamp": ["2025-01-01"],
            "foreadjustfactor": [1.0],
        })
        result = bar_adjustment.calculate_adjusted_prices(
            bars_df, factors_df, ADJUSTMENT_TYPES.FORE,
        )
        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1

    def test_apply_price_adjustment_callable_with_empty_code(self):
        """空 code 时返回原始数据"""
        df = pd.DataFrame({"close": [10.0]})
        result = bar_adjustment.apply_price_adjustment(
            bars_data=df, code="", adjustment_type=MagicMock(), adjustfactor_service=MagicMock(),
        )
        assert result is df
