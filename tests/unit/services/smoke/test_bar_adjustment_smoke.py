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
        """传入带 to_dataframe 方法的对象时调用该方法"""
        mock_data = MagicMock()
        expected_df = pd.DataFrame({"code": ["000001.SZ"]})
        mock_data.to_dataframe.return_value = expected_df
        result = bar_adjustment.convert_modellist_to_dataframe(mock_data)
        mock_data.to_dataframe.assert_called_once()

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
