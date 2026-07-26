#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Upstream: bar_service.get_bars_df (data 层, bars DataFrame)
# Downstream: ICAnalyzer / FactorDecayAnalyzer / factor_analysis_service (#6794)
# Role: 前瞻收益计算器 — PIT 硬约束 (d+N <= realized_cutoff, #6794 验收2)

"""
前瞻收益计算器 (#6794 验收2)。

forward return at date d for period N = close[d+N] / close[d] - 1。

PIT 硬约束: 只计算 d+N <= realized_cutoff 的前瞻收益 (评估日之后已实现的收益);
            d+N > realized_cutoff 的格子置 NaN, 防止用未实现未来收益做 IC/decay
            分析 (前瞻泄漏会让因子效果虚高)。

典型用法 (编排器内):
    bars = bar_service.get_bars_df(code=..., start_date=..., end_date=...)
    fwd = compute_forward_returns(bars, periods=[1,5,10,20],
                                  realized_cutoff=evaluation_end_date)
    # fwd 含 return_1d / return_5d / ... 列, 喂给 ICAnalyzer(factor_df, fwd)
"""

from typing import List, Optional
from datetime import datetime

import pandas as pd
import numpy as np


def compute_forward_returns(
    bars_df: pd.DataFrame,
    periods: List[int] = (1, 5, 10, 20),
    realized_cutoff: Optional[datetime] = None,
    date_col: str = "date",
    code_col: str = "code",
    close_col: str = "close",
) -> pd.DataFrame:
    """计算 PIT 前瞻收益 (return_Nd 列)。

    Args:
        bars_df: K线 DataFrame, 需含 date_col / code_col / close_col
        periods: 周期列表 (默认 1/5/10/20 日)
        realized_cutoff: PIT 截止时间; d+N 超过此值的格子置 NaN (防前瞻泄漏)。
                         None = 算所有 bars 内已实现的 d+N (回测式全量)。
        date_col / code_col / close_col: 列名

    Returns:
        bars_df 副本 + return_{N}d 列 (各周期前瞻收益; 未实现或不足 N 的为 NaN)
    """
    out = bars_df.copy()

    required = [date_col, code_col, close_col]
    missing = [c for c in required if c not in out.columns]
    if missing:
        raise ValueError(f"bars_df 缺少必需列: {missing}")

    cutoff = pd.Timestamp(realized_cutoff) if realized_cutoff is not None else None

    for period in periods:
        col = f"return_{period}d"
        out[col] = np.nan

        # 按 code 分组, 组内按 date 排序后向量化算前瞻收益 (codes 互不串扰)
        for _, grp in out.groupby(code_col, sort=False):
            grp = grp.sort_values(date_col)
            closes = grp[close_col]
            dates = grp[date_col]

            # close[i+period] / close[i] - 1; trailing period 行 shift 后为 NaN
            fwd = closes.shift(-period) / closes - 1.0

            # PIT: d+N 必须 <= cutoff (未实现 → NaN); 同时排除 base == 0
            mask = closes != 0
            if cutoff is not None:
                mask &= dates.shift(-period) <= cutoff

            out.loc[grp.index, col] = fwd.where(mask, np.nan)

    return out
