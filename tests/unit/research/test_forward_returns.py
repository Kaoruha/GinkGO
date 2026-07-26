"""前瞻收益计算器测试 -- #6794 验收2 (PIT 前瞻收益)

PIT: forward return at date d for period N = close[d+N]/close[d] - 1。
严格 PIT: 若 d + N > realized_cutoff (未来未实现), 该格置 NaN — 防止用未来收益
做 IC/decay 分析 (前瞻泄漏会让因子效果虚高)。
"""
import pytest
import pandas as pd
from datetime import datetime

from ginkgo.research.forward_returns import compute_forward_returns


def _bars():
    """构造小 bars: code=000001.SZ, 5 个交易日 close (每日 +10%)。"""
    return pd.DataFrame({
        "date": pd.to_datetime([
            "2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05",
        ]),
        "code": ["000001.SZ"] * 5,
        "close": [10.0, 11.0, 12.1, 13.31, 14.641],
    })


@pytest.mark.unit
class TestForwardReturns:
    def test_compute_forward_returns_basic(self):
        """return_1d: close[t+1]/close[t]-1, 已实现区间正确计算 (每日 +10%)。"""
        out = compute_forward_returns(_bars(), periods=[1])
        assert abs(out.loc[0, "return_1d"] - 0.10) < 1e-6
        assert abs(out.loc[1, "return_1d"] - 0.10) < 1e-6
        # 最后一天无 t+1 → NaN
        assert pd.isna(out.loc[4, "return_1d"])

    def test_pit_unrealized_returns_nan(self):
        """PIT 硬约束: d+N > realized_cutoff → NaN (未来未实现, 防前瞻泄漏)。"""
        # cutoff = 2024-01-03: 只允许 d+1 <= 01-03 (即 date <= 01-02 有 return_1d)
        out = compute_forward_returns(
            _bars(), periods=[1], realized_cutoff=datetime(2024, 1, 3),
        )
        # date=01-01: return_1d 用 01-02 close (01-02 <= cutoff 已实现) → 有值
        assert not pd.isna(out.loc[0, "return_1d"])
        # date=01-03: return_1d 需 01-04 close (01-04 > cutoff 未实现) → NaN
        assert pd.isna(out.loc[2, "return_1d"])

    def test_no_cutoff_computes_all_realized(self):
        """无 realized_cutoff: 算所有 d+N 在 bars 范围内的前瞻收益 (回测式全量)。"""
        out = compute_forward_returns(_bars(), periods=[1])
        # 无 cutoff: date=01-04 的 return_1d (用 01-05) 也有值 (bars 内已实现)
        assert not pd.isna(out.loc[3, "return_1d"])

    def test_multiple_periods_columns(self):
        """多周期: return_1d / return_5d 列都生成; 不足 N 的全 NaN。"""
        out = compute_forward_returns(_bars(), periods=[1, 5])
        assert "return_1d" in out.columns
        assert "return_5d" in out.columns
        # 5d 需至少 6 个点, 这里 5 个 → return_5d 全 NaN
        assert out["return_5d"].isna().all()

    def test_multi_code_isolated(self):
        """多 code: 各 code 内部按 date 排序算前瞻收益, 互不串扰。"""
        df = pd.DataFrame({
            "date": pd.to_datetime(["2024-01-01", "2024-01-02"] * 2),
            "code": ["000001.SZ", "000001.SZ", "000002.SZ", "000002.SZ"],
            "close": [10.0, 12.0, 20.0, 26.0],
        })
        out = compute_forward_returns(df, periods=[1])
        # 000001: 12/10-1 = +20%; 000002: 26/20-1 = +30% (各自独立)
        r1 = out[out["code"] == "000001.SZ"].loc[0, "return_1d"]
        r2 = out[out["code"] == "000002.SZ"].iloc[0]["return_1d"]
        assert abs(r1 - 0.20) < 1e-6
        assert abs(r2 - 0.30) < 1e-6
