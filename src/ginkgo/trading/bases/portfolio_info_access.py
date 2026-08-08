"""portfolio_info 访问工具函数(无状态)。

集中持仓/市值/现价/P&L 的提取逻辑,供 Risk/Strategy/Sizer 等组件复用。
消除 risk_management 17 子类的重复内联 .get() 与求和(#6470)。

设计:纯函数(非 mixin)。
- Ginkgo 现有 mixin(ContextMixin/TimeMixin/NamedMixin/EngineBindableMixin/LotAlignableMixin)
  全部持实例状态(self._xxx);portfolio_info 访问无状态,归 utils 函数先例
  (trading/evaluation/utils/ast_helpers.py),不进 entities/mixins/。
- 对称:Strategy/Sizer/Selector 同样收 portfolio_info,可复用,无 RiskBase-only 不对称。
- 不碰 Base 类层级(函数在类外),绕开 Base 禁令。
"""
from typing import Any, Dict, Optional


def get_positions(portfolio_info: Dict[str, Any]) -> Dict[str, Any]:
    """归一化取出 positions,统一返回 {code: position} dict。

    portfolio_base 构建处 positions 形态不一致:
    - portfolio_base.py:887 路径为 dict(self.positions)
    - portfolio_base.py:851 路径为 list(self._positions.values())
    各 risk 消费方既 [code] 索引又 .values()/.get(code),仅 dict 形态成立。
    本函数将 list 归一为 dict,dict 原样返回,缺失/None 返回 {}。

    Args:
        portfolio_info: 组件 cal/generate_signals 收到的 portfolio_info dict

    Returns:
        Dict[str, Any]: {code: position} 映射,永不返回 None
    """
    positions = portfolio_info.get("positions")
    if not positions:
        return {}
    if isinstance(positions, dict):
        return positions
    # list 形态:按 .code 归一,跳过 None/空元素
    return {
        pos.code: pos for pos in positions if pos and getattr(pos, "code", None)
    }


def total_market_value(portfolio_info: Dict[str, Any]) -> Any:
    """组合总市值(各持仓 market_value 之和)。

    替换 concentration_risk(1×)/volatility_risk(1×) 重复的内联:
        sum(pos.market_value for pos in positions.values() if pos and pos.market_value)
    持原守卫语义:跳过 None/0/缺字段的持仓。

    Args:
        portfolio_info: 组件收到的 portfolio_info dict

    Returns:
        各 position.market_value 之和(类型随 market_value,通常 Decimal/float);空则 0
    """
    return sum(
        (pos.market_value if pos else 0)
        for pos in get_positions(portfolio_info).values()
        if pos and getattr(pos, "market_value", None)
    )


def current_price(portfolio_info: Dict[str, Any], code: str) -> Optional[Any]:
    """取某 code 的现价,无则 None(不兜底假价)。

    替换 concentration_risk 的 portfolio_info.get("prices", {}).get(order.code, 100)。
    原代码缺价时回退 100(假价,掩盖数据缺失);本函数返回 None,调用方显式决定
    回退(守 refactor 行为:concentration 调用处保留 `or 100`,行为不变)。

    Args:
        portfolio_info: 组件收到的 portfolio_info dict
        code: 标的代码

    Returns:
        现价或 None
    """
    prices = portfolio_info.get("prices") or {}
    return prices.get(code)


def pnl_ratio(position: Any) -> Any:
    """持仓盈亏比率(dict/object 双兼容)。

    修复 profit_target_risk #3957 bug:
        getattr(position, 'profit_loss_ratio', 0)
    在 position 为 dict 时恒返回 0(dict 无属性),止盈永不触发(master 8 测试红)。
    本函数 dict 走 .get 键、object 走 getattr,双形态正确读取。
    注:loss_limit_risk 从 event 现价 + position.cost 实算(语义不同),不经此函数。

    Args:
        position: portfolio_info["positions"][code] 取出的持仓(dict 或对象)

    Returns:
        profit_loss_ratio 值;缺失/None position 返回 0
    """
    if position is None:
        return 0
    if isinstance(position, dict):
        return position.get("profit_loss_ratio", 0) or 0
    return getattr(position, "profit_loss_ratio", 0) or 0


def get_worth(portfolio_info: Dict[str, Any]) -> Any:
    """归一取出 worth(组合净值),保留原生类型。

    替换 8 个权益分析器重复的 worth 读取(口径分歧):
        float(to_decimal(portfolio_info.get("worth", 0)))   # 包装口径
        portfolio_info.get("worth", 0)                       # 裸读口径
    统一为单点读取,保留 worth 原生类型(Decimal,与 total_market_value 一致);
    分析器需 float 时由 worth_delta 入参 float 化,不在本函数转。

    Args:
        portfolio_info: 组件收到的 portfolio_info dict

    Returns:
        worth 值(通常 Decimal);缺失/None 返回 0,永不 None
    """
    worth = portfolio_info.get("worth", 0)
    return worth if worth is not None else 0
