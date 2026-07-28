"""FactorAnalysisService 测试 -- #6794 验收1 (IC/IR/decay/turnover/分位收益) + 验收2 (PIT)

编排器: 读 PIT 因子 + bars → 前瞻收益 → IC/Decay/Layering 三分析器 + 内联 turnover。

fixture: 5 code (ICAnalyzer 每日需 >=5 code 才算 IC), factor base 与未来日收益正相关
         (factor rank E>D>C>B>A, return_1d rank E>D>C>B>A → Spearman IC ≈ 1.0)。
"""
import pytest
import pandas as pd
from datetime import datetime

try:
    from ginkgo.features.services.factor_analysis_service import FactorAnalysisService
    HAS_SVC = True
except ImportError:
    HAS_SVC = False


def _factor_df():
    """5 code × 10 日; factor_value base 与未来收益正相关。"""
    dates = pd.date_range("2024-01-01", periods=10, freq="D")
    rows = []
    for code, base in [("A", 1.0), ("B", 2.0), ("C", 3.0), ("D", 4.0), ("E", 5.0)]:
        for i, d in enumerate(dates):
            rows.append({"date": d, "code": code, "factor_value": base + i * 0.1})
    return pd.DataFrame(rows)


def _bars_df():
    """12 日 bars; factor 高的 code 日收益高 (正 IC)。A 不动, E 涨最快。"""
    dates = pd.date_range("2024-01-01", periods=12, freq="D")
    rows = []
    growth = {"A": 1.0, "B": 1.01, "C": 1.02, "D": 1.03, "E": 1.04}
    for code in ["A", "B", "C", "D", "E"]:
        price = 100.0
        for d in dates:
            rows.append({"date": d, "code": code, "close": price})
            price *= growth[code]
    return pd.DataFrame(rows)


@pytest.mark.skipif(not HAS_SVC, reason="FactorAnalysisService not available")
@pytest.mark.unit
class TestFactorAnalysisService:
    def test_analyze_produces_nonempty_report(self):
        """编排器输出非空报告: ic/ir/decay/turnover/layering_spread 都有键。"""
        svc = FactorAnalysisService()
        result = svc.analyze_from_dataframes(
            factor_df=_factor_df(),
            bars_df=_bars_df(),
            periods=[1],
            n_groups=5,
            realized_cutoff=datetime(2024, 1, 12),
        )
        assert result.success
        for key in ("ic", "ir", "decay", "turnover", "layering_spread"):
            assert key in result.data, f"报告缺键: {key}"

    def test_ic_positive_for_aligned_factor_return(self):
        """factor 与未来收益正相关 → IC > 0 (rank E>D>C>B>A 一致)。"""
        svc = FactorAnalysisService()
        result = svc.analyze_from_dataframes(
            factor_df=_factor_df(), bars_df=_bars_df(),
            periods=[1], n_groups=5, realized_cutoff=datetime(2024, 1, 12),
        )
        assert result.success
        assert result.data["ic"] is not None
        assert result.data["ic"] > 0

    def test_pit_cutoff_graceful(self):
        """realized_cutoff 早: PIT 截断大部分前瞻收益, 仍 success (graceful degrade)。"""
        svc = FactorAnalysisService()
        result = svc.analyze_from_dataframes(
            factor_df=_factor_df(), bars_df=_bars_df(),
            periods=[1], n_groups=5, realized_cutoff=datetime(2024, 1, 3),
        )
        # 不因样本少崩; ic 可能为 None (样本不足) 但 success 必为 True
        assert result.success

    def test_turnover_computed_as_float(self):
        """turnover 实际计算 (非空桩): 返回 float (factor rank 稳定时为 0.0)。"""
        svc = FactorAnalysisService()
        result = svc.analyze_from_dataframes(
            factor_df=_factor_df(), bars_df=_bars_df(),
            periods=[1], n_groups=5, realized_cutoff=datetime(2024, 1, 12),
        )
        assert isinstance(result.data["turnover"], float)

    def test_analyze_factor_end_to_end_mock(self):
        """验收4: analyze_factor 端到端 (mock crud+bar_service) 产出非空报告。

        覆盖数据获取层: crud.get_factors_by_entity(factor_names List, entity_type) +
        bar_service.get_bars_df(timestamp 列归一 date, close Decimal→float)。
        """
        from types import SimpleNamespace
        from decimal import Decimal
        from unittest.mock import MagicMock
        from ginkgo.data.services.base_service import ServiceResult

        # 5 code × 10 日 因子 (factor base 正相关未来收益)
        dates = pd.date_range("2024-01-01", periods=10, freq="D")
        factors_by_entity = {}
        for code, base in [("A", 1.0), ("B", 2.0), ("C", 3.0), ("D", 4.0), ("E", 5.0)]:
            factors_by_entity[code] = [
                SimpleNamespace(
                    entity_id=code, factor_name="ROC",
                    factor_value=Decimal(str(base + i * 0.1)), timestamp=d,
                )
                for i, d in enumerate(dates)
            ]

        crud = MagicMock()
        crud.get_factors_by_entity.side_effect = (
            lambda entity_type, entity_id, **kw: factors_by_entity.get(entity_id, [])
        )

        # bars: 12 日, factor 高涨得快 (正 IC); bar 用 timestamp 列 (非 date)
        bar_dates = pd.date_range("2024-01-01", periods=12, freq="D")
        growth = {"A": 1.0, "B": 1.01, "C": 1.02, "D": 1.03, "E": 1.04}
        bar_rows = []
        for code in ["A", "B", "C", "D", "E"]:
            price = 100.0
            for d in bar_dates:
                bar_rows.append({"timestamp": d, "code": code, "close": price})
                price *= growth[code]
        bars_mock = pd.DataFrame(bar_rows)

        bar_service = MagicMock()
        bar_service.get_bars_df.return_value = ServiceResult(success=True, data=bars_mock)

        svc = FactorAnalysisService()
        result = svc.analyze_factor(
            factor_name="ROC", entity_ids=["A", "B", "C", "D", "E"],
            start_date="2024-01-01", end_date="2024-01-12",
            factor_crud=crud, bar_service=bar_service, entity_type="stock",
        )
        assert result.success
        assert result.data["ic"] is not None
        assert result.data["ic"] > 0
        assert isinstance(result.data["turnover"], float)
