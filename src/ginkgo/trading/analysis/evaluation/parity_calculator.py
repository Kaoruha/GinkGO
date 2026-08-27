# Upstream: gate_definitions (G2 阈值), pandas 净值/换手序列 (取数在 FunnelEvaluator/CLI 侧)
# Downstream: FunnelEvaluator, evaluation_cli (eval parity)
# Role: G2 人看报告半边 — 回测 baseline vs 模拟盘(或另一次回测)同窗一致性 5 项指标


"""
ParityCalculator — 回测 vs 模拟盘 同窗一致性计算 (纯计算，无 DB 依赖)

与在线偏差链路 (DeviationChecker/LiveDeviationDetector) 的分界:
- 在线链路 = 机器哨兵: 逐日 z-score, 超阈值即告警/熔断
- 本模块   = 人看报告: 同窗全期对比, 相关性/收益差带宽/换手偏差/回撤形态
baseline 序列取数口径与 live_deviation_detector 对齐 (同为日频净值链)。

输入: 两条日频序列 DataFrame (timestamp + value 列, 经 DataProvider.get 获得)。
"""

import math
from dataclasses import dataclass, field
from typing import Dict, Optional

import pandas as pd

from ginkgo.libs import GLOG
from ginkgo.trading.analysis.evaluation.gate_definitions import (
    GateDefinition,
    get_gate,
)


@dataclass
class ParityResult:
    """同窗对比结果 — 每项要么有值，要么 None(样本不足/缺数据)"""

    baseline_label: str = ""
    candidate_label: str = ""
    overlap_days: int = 0
    overlap_start: Optional[str] = None
    overlap_end: Optional[str] = None
    daily_return_corr: Optional[float] = None
    cum_return_diff: Optional[float] = None
    cum_return_band: Optional[float] = None
    band_ratio: Optional[float] = None
    turnover_deviation_pct: Optional[float] = None
    drawdown_shape_corr: Optional[float] = None
    notes: list = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "baseline": self.baseline_label,
            "candidate": self.candidate_label,
            "overlap_days": self.overlap_days,
            "overlap_start": self.overlap_start,
            "overlap_end": self.overlap_end,
            "daily_return_corr": self.daily_return_corr,
            "cum_return_diff": self.cum_return_diff,
            "cum_return_band": self.cum_return_band,
            "band_ratio": self.band_ratio,
            "turnover_deviation_pct": self.turnover_deviation_pct,
            "drawdown_shape_corr": self.drawdown_shape_corr,
            "notes": list(self.notes),
        }


def _daily_series(df: pd.DataFrame) -> pd.Series:
    """取日频净值序列 (index=date, value=净值)，按日期排序去重"""
    s = df.set_index(pd.to_datetime(df["timestamp"]).dt.date)["value"]
    return s[~s.index.duplicated(keep="last")].sort_index().astype(float)


def _drawdown_series(nav: pd.Series) -> pd.Series:
    """净值序列 → 回撤序列 (相对历史高点, ≤0)"""
    peak = nav.cummax()
    return (nav - peak) / peak


class ParityCalculator:
    """回测 vs 模拟盘 同窗一致性计算器 (纯计算)"""

    def compare(
        self,
        baseline: pd.DataFrame,
        candidate: pd.DataFrame,
        baseline_label: str = "baseline",
        candidate_label: str = "candidate",
        baseline_turnover: Optional[pd.DataFrame] = None,
        candidate_turnover: Optional[pd.DataFrame] = None,
    ) -> ParityResult:
        """对比两条日频净值序列

        Args:
            baseline: 回测净值 (timestamp+value)
            candidate: 模拟盘/另一次回测净值 (timestamp+value)
            baseline_label/candidate_label: 展示标签
            baseline_turnover/candidate_turnover: 可选换手序列
                (order_count 日频, timestamp+value)，缺省时换手 gate 报样本不足

        Returns:
            ParityResult — 指标缺数据时对应字段为 None，不猜值
        """
        result = ParityResult(
            baseline_label=baseline_label, candidate_label=candidate_label
        )

        b = _daily_series(baseline)
        c = _daily_series(candidate)
        if b.empty or c.empty:
            result.notes.append("净值序列为空，无法对比")
            return result

        # --- 同窗对齐 (按日期交集) ---
        common = b.index.intersection(c.index)
        result.overlap_days = len(common)
        if result.overlap_days < 2:
            result.notes.append(f"重叠交易日仅 {result.overlap_days} 天，无法计算一致性指标")
            return result
        result.overlap_start = str(common.min())
        result.overlap_end = str(common.max())

        b_win = b.loc[common]
        c_win = c.loc[common]

        # --- 1. 日收益相关性 ---
        b_ret = b_win.pct_change().dropna()
        c_ret = c_win.pct_change().dropna()
        if len(b_ret) >= 2 and b_ret.std() > 0 and c_ret.std() > 0:
            result.daily_return_corr = float(b_ret.corr(c_ret))
        else:
            result.notes.append("日收益序列无波动，相关性不可算 (策略可能未交易)")

        # --- 2. 累计收益差 + 带宽 ---
        b_cum = b_win.iloc[-1] / b_win.iloc[0] - 1.0
        c_cum = c_win.iloc[-1] / c_win.iloc[0] - 1.0
        result.cum_return_diff = float(abs(b_cum - c_cum))
        if len(b_ret) >= 2 and b_ret.std() > 0:
            # 带宽 = 1.5 × baseline 同窗日收益波动 × sqrt(重叠天数)
            result.cum_return_band = float(
                get_gate("g2_cum_return_band").threshold * b_ret.std() * math.sqrt(len(b_ret))
            )
            result.band_ratio = (
                result.cum_return_diff / result.cum_return_band
                if result.cum_return_band > 0 else None
            )
        else:
            result.notes.append("baseline 同窗无波动，累计收益带宽不可算")

        # --- 3. 换手偏差 (order_count 同窗日频合计) ---
        if baseline_turnover is not None and candidate_turnover is not None:
            bt = _daily_series(baseline_turnover)
            ct = _daily_series(candidate_turnover)
            bt_win = bt.reindex(common).fillna(0.0)
            ct_win = ct.reindex(common).fillna(0.0)
            b_total, c_total = float(bt_win.sum()), float(ct_win.sum())
            if b_total > 0:
                result.turnover_deviation_pct = float(
                    abs(c_total - b_total) / b_total * 100.0
                )
            elif c_total == 0:
                result.turnover_deviation_pct = 0.0  # 双方都零交易
            else:
                result.notes.append("baseline 同窗零成交而候选有成交，换手偏差记 100%+")
                result.turnover_deviation_pct = None
        else:
            result.notes.append("换手序列缺失，换手偏差未评估")

        # --- 4. 回撤形态相关性 ---
        b_dd = _drawdown_series(b_win)
        c_dd = _drawdown_series(c_win)
        if b_dd.std() > 0 and c_dd.std() > 0:
            result.drawdown_shape_corr = float(b_dd.corr(c_dd))
        else:
            result.notes.append("回撤序列无波动，形态相关性不可算")

        GLOG.DEBUG(
            f"ParityCalculator: {baseline_label} vs {candidate_label} "
            f"overlap={result.overlap_days}d corr={result.daily_return_corr}"
        )
        return result

    # ============================================================
    # gate 求值 (供 FunnelEvaluator 编排)
    # ============================================================

    @staticmethod
    def evaluate_gate(result: ParityResult, gate: GateDefinition) -> Optional[bool]:
        """按 gate 定义对 ParityResult 求值

        Returns:
            True=PASS / False=FAIL / None=样本不足 (INSUFFICIENT_DATA)
        """
        field_map = {
            "g2_overlap_days": result.overlap_days,
            "g2_daily_return_corr": result.daily_return_corr,
            "g2_band_ratio": result.band_ratio,
            "g2_turnover_deviation": result.turnover_deviation_pct,
            "g2_drawdown_shape": result.drawdown_shape_corr,
        }
        # 累计收益差 gate 用 band_ratio (≤1.5 倍带宽) 而非绝对值
        key = "g2_band_ratio" if gate.id == "g2_cum_return_band" else gate.id
        value = field_map.get(key)
        if value is None:
            return None
        # 重叠不足 2 天时无有效对比, 一律样本不足 (而非 FAIL)
        if gate.id == "g2_overlap_days" and result.overlap_days < 2:
            return None
        if gate.direction == "gte":
            return value >= gate.threshold
        return value <= gate.threshold
