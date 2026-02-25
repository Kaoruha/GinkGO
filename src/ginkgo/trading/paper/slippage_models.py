# Upstream: ginkgo.enums
# Downstream: ginkgo.trading.paper.paper_engine
# Role: 滑点模型 - 固定滑点、百分比滑点、无滑点

"""
滑点模型

提供交易滑点计算功能:
- SlippageModel: 滑点模型抽象基类
- FixedSlippage: 固定滑点
- PercentageSlippage: 百分比滑点
- NoSlippage: 无滑点

Usage:
    from ginkgo.trading.paper.slippage_models import FixedSlippage
    from ginkgo.enums import DIRECTION_TYPES

    model = FixedSlippage(slippage=Decimal("0.02"))
    adjusted_price = model.apply(Decimal("10.00"), DIRECTION_TYPES.LONG)
    # adjusted_price = 10.02 (买入时价格上升)
"""

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Union

from ginkgo.enums import DIRECTION_TYPES


class SlippageModel(ABC):
    """
    滑点模型抽象基类

    定义滑点计算的标准接口。
    滑点模拟真实交易中买卖价差和市场冲击。
    """

    @abstractmethod
    def apply(self, price: Decimal, direction: DIRECTION_TYPES) -> Decimal:
        """
        应用滑点到价格

        Args:
            price: 原始价格
            direction: 交易方向 (LONG=买入, SHORT=卖出)

        Returns:
            调整后的价格 (含滑点)

        Note:
            - 买入 (LONG): 价格上升 (买入成本增加)
            - 卖出 (SHORT): 价格下降 (卖出收入减少)
        """
        pass

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"


class FixedSlippage(SlippageModel):
    """
    固定滑点模型

    使用固定的金额作为滑点。

    Example:
        model = FixedSlippage(slippage=Decimal("0.02"))
        # 买入 10.00 -> 10.02
        # 卖出 10.00 -> 9.98
    """

    def __init__(self, slippage: Union[Decimal, float, str]):
        """
        初始化固定滑点模型

        Args:
            slippage: 固定滑点金额 (必须为正数)

        Raises:
            ValueError: 如果滑点为负数
        """
        if isinstance(slippage, (float, int)):
            slippage = Decimal(str(slippage))
        elif isinstance(slippage, str):
            slippage = Decimal(slippage)

        if slippage < 0:
            raise ValueError(f"滑点不能为负数: {slippage}")

        self.slippage = slippage

    def apply(self, price: Decimal, direction: DIRECTION_TYPES) -> Decimal:
        """
        应用固定滑点

        买入时加滑点，卖出时减滑点。
        """
        if isinstance(price, (float, int)):
            price = Decimal(str(price))

        if direction == DIRECTION_TYPES.LONG:
            # 买入：价格上升
            return price + self.slippage
        else:
            # 卖出：价格下降
            return price - self.slippage

    def __repr__(self) -> str:
        return f"FixedSlippage(slippage={self.slippage})"


class PercentageSlippage(SlippageModel):
    """
    百分比滑点模型

    使用价格的百分比作为滑点。

    Example:
        model = PercentageSlippage(percentage=Decimal("0.001"))  # 0.1%
        # 买入 10.00 -> 10.01
        # 卖出 10.00 -> 9.99
    """

    def __init__(self, percentage: Union[Decimal, float, str]):
        """
        初始化百分比滑点模型

        Args:
            percentage: 滑点百分比 (如 0.001 表示 0.1%)

        Raises:
            ValueError: 如果百分比为负数
        """
        if isinstance(percentage, (float, int)):
            percentage = Decimal(str(percentage))
        elif isinstance(percentage, str):
            percentage = Decimal(percentage)

        if percentage < 0:
            raise ValueError(f"滑点百分比不能为负数: {percentage}")

        self.percentage = percentage

    def apply(self, price: Decimal, direction: DIRECTION_TYPES) -> Decimal:
        """
        应用百分比滑点

        滑点 = 价格 * 百分比
        """
        if isinstance(price, (float, int)):
            price = Decimal(str(price))

        slippage = price * self.percentage

        if direction == DIRECTION_TYPES.LONG:
            # 买入：价格上升
            return price + slippage
        else:
            # 卖出：价格下降
            return price - slippage

    def __repr__(self) -> str:
        return f"PercentageSlippage(percentage={self.percentage})"


class NoSlippage(SlippageModel):
    """
    无滑点模型

    返回原始价格，不应用任何滑点。
    用于测试或理想情况模拟。
    """

    def apply(self, price: Decimal, direction: DIRECTION_TYPES) -> Decimal:
        """
        不应用滑点，返回原始价格
        """
        if isinstance(price, (float, int)):
            price = Decimal(str(price))
        return price

    def __repr__(self) -> str:
        return "NoSlippage()"


# 默认滑点模型工厂函数
def get_default_slippage_model() -> SlippageModel:
    """
    获取默认滑点模型

    默认使用 0.1% 百分比滑点
    """
    return PercentageSlippage(percentage=Decimal("0.001"))
