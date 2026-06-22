"""TDD for bar_adjustment sort order -- #5501

get_precomputed_adjustment_factors 临时因子分支用 iloc[-1]/iloc[0] 取因子，
假设 DataFrame 升序；上游 adjustfactor_service.get 不保证排序（crud 无 order_by），
降序输入时 FORE/BACK 方向反。#5501 修复：显式 sort_values('timestamp')。

注：仅「临时因子」测试分支受影响；生产核心 calculate_adjusted_prices /
apply_matrix_adjustment 用 merge(on="timestamp") 顺序无关，不受影响。
"""
import pytest
from unittest.mock import MagicMock

import pandas as pd

from ginkgo.data.services import bar_adjustment
from ginkgo.enums import ADJUSTMENT_TYPES


def _make_descending_factors() -> pd.DataFrame:
    """降序（newest first）adjustfactor DataFrame，无预计算列 → 走临时因子分支。

    最新日期 2025-01-03 因子 1.2 最大（正常：时间越近复权因子越大）。
    """
    return pd.DataFrame({
        "timestamp": ["2025-01-03", "2025-01-02", "2025-01-01"],  # 降序
        "adjustfactor": [1.2, 1.1, 1.0],
    })


def _make_mock_service(df: pd.DataFrame) -> MagicMock:
    """构造 adjustfactor_service mock，data 支持 len() + to_dataframe()。

    MagicMock 默认 __len__ 返回 0 会触发 L146 空分支，须显式配非 0。
    """
    mock_svc = MagicMock()
    mock_result = MagicMock()
    mock_result.success = True
    mock_data = MagicMock()
    mock_data.__len__ = MagicMock(return_value=len(df))
    mock_data.to_dataframe.return_value = df
    mock_result.data = mock_data
    mock_svc.get.return_value = mock_result
    return mock_svc


class TestPrecomputedFactorsSortOrder:
    """#5501: 降序输入时复权方向须正确（显式排序，不依赖上游顺序契约）。"""

    def test_fore_descending_input_latest_factor_is_base(self):
        """FORE 复权：降序输入时最新日期系数应=1.0（latest/自身）。

        bug: iloc[-1] 在降序下取到最早因子(1.0)，最新日期系数=1.0/1.2≈0.833≠1。
        修复后: 显式升序排序，iloc[-1]=1.2（最新），最新日期系数=1.2/1.2=1.0。
        """
        df_desc = _make_descending_factors()
        mock_svc = _make_mock_service(df_desc)

        result = bar_adjustment.get_precomputed_adjustment_factors(
            code="000001.SZ",
            dates=["2025-01-01", "2025-01-02", "2025-01-03"],
            adjustment_type=ADJUSTMENT_TYPES.FORE,
            adjustfactor_service=mock_svc,
        )

        row_latest = result[result["timestamp"] == "2025-01-03"].iloc[0]
        assert row_latest["foreadjustfactor"] == pytest.approx(1.0), (
            "FORE 最新日期系数应为 1.0（最新因子/自身）；降序输入下 iloc[-1] 取到最早因子致方向反"
        )

    def test_back_descending_input_earliest_factor_is_base(self):
        """BACK 复权：降序输入时最早日期系数应=1.0（earliest/自身）。

        bug: iloc[0] 在降序下取到最新因子(1.2)，最早日期系数=1.0/1.2≈0.833≠1。
        修复后: 显式升序，iloc[0]=1.0（最早 2025-01-01），最早日期系数=1.0/1.0=1.0。
        """
        df_desc = _make_descending_factors()
        mock_svc = _make_mock_service(df_desc)

        result = bar_adjustment.get_precomputed_adjustment_factors(
            code="000001.SZ",
            dates=["2025-01-01", "2025-01-02", "2025-01-03"],
            adjustment_type=ADJUSTMENT_TYPES.BACK,
            adjustfactor_service=mock_svc,
        )

        row_earliest = result[result["timestamp"] == "2025-01-01"].iloc[0]
        assert row_earliest["backadjustfactor"] == pytest.approx(1.0), (
            "BACK 最早日期系数应为 1.0（最早因子/自身）；降序输入下 iloc[0] 取到最新因子致方向反"
        )

    def test_fore_factor_values_correct_after_sort(self):
        """FORE 复权系数值正确性：升序排序后 latest=1.2，各日期系数=1.2/历史因子。

        2025-01-01: 1.2/1.0=1.2, 2025-01-02: 1.2/1.1≈1.0909, 2025-01-03: 1.2/1.2=1.0。
        断言全部三个值，锁死方向（非仅端点）。
        """
        df_desc = _make_descending_factors()
        mock_svc = _make_mock_service(df_desc)

        result = bar_adjustment.get_precomputed_adjustment_factors(
            code="000001.SZ",
            dates=["2025-01-01", "2025-01-02", "2025-01-03"],
            adjustment_type=ADJUSTMENT_TYPES.FORE,
            adjustfactor_service=mock_svc,
        )
        result = result.set_index("timestamp")

        assert result.loc["2025-01-01", "foreadjustfactor"] == pytest.approx(1.2)
        assert result.loc["2025-01-02", "foreadjustfactor"] == pytest.approx(1.2 / 1.1)
        assert result.loc["2025-01-03", "foreadjustfactor"] == pytest.approx(1.0)
