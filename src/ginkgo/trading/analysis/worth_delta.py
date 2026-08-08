"""权益序列相邻差分(纯函数,无状态)。

替换 8 个权益分析器重复的 _last_worth 差分逻辑:
    pnl = current - last              # 绝对盈亏(profit/consecutive_pnl/win_rate)
    return = (current - last) / last   # 相对收益(sharpe/sortino/skew/volatility/var_cvar/win_rate)

设计:
- 纯函数,无状态。_last_worth 状态仍归各 analyzer(行为等价,零风险)。
- 入参 float 化(analyzer 喂 numpy 要 float;worth 经 get_worth 取出为 Decimal 原生)。
- last<=0 时 return_ 为 None(除零守卫,与原 `if _last_worth > 0` 一致);pnl 仍算。
- last is None(首次调用)返回 None(无差分),调用方据此 init。

# Upstream: portfolio_info_access.get_worth (Decimal 原生 worth)
# Downstream: 8 个权益分析器(sharpe/sortino/skew_kurtosis/volatility/var_cvar/profit/consecutive_pnl/win_rate)
"""
from dataclasses import dataclass
from typing import Optional


@dataclass
class WorthDelta:
    """权益相邻差分结果。"""

    pnl: float  # 绝对盈亏 (current - last)
    return_: Optional[float]  # 相对收益;last<=0 时 None(除零守卫)


def worth_delta(current, last) -> Optional[WorthDelta]:
    """权益序列相邻差分。

    Args:
        current: 本期 worth(Decimal/float/int,内部 float 化)
        last: 上期 worth;None 表示首次调用,返回 None

    Returns:
        WorthDelta 或 None(首次)。last<=0 时 return_ 为 None,pnl 仍算。
    """
    if last is None:
        return None
    cur = float(current)
    lst = float(last)
    pnl = cur - lst
    ret = (pnl / lst) if lst > 0 else None
    return WorthDelta(pnl=pnl, return_=ret)
