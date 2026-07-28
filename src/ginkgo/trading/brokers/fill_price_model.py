# Upstream: ginkgo.trading.paper.slippage_models, ginkgo.enums, ginkgo.libs
# Downstream: ginkgo.trading.brokers.sim_broker (SimBroker 注入)
# Role: FillPriceModel 成交价模型契约 + 实现 (ADR-037 D1, Epic #6851)

"""
FillPriceModel - 成交价模型

定义 SimBroker 成交价计算的可替换策略 (ADR-037 D1)。两套"滑点"概念边界:
- AttitudePricing: scipy 态度采样, 成交价 ∈ [low, high] (移植 sim_broker._get_random_transaction_price)
- DeterministicSlippage: 包装 SlippageModel, 成交价 = close ± slippage (买卖价差/冲击成本)

二者互斥择一, 不叠加 (ADR-037 Considered Options 否决方案 A)。
"""

from typing import Protocol
from decimal import Decimal

from ginkgo.libs import Number, to_decimal
from ginkgo.enums import DIRECTION_TYPES, ATTITUDE_TYPES


class FillPriceModel(Protocol):
    """
    成交价模型契约 (ADR-037 D1)

    SimBroker 通过此契约计算成交价, 实现可替换 (AttitudePricing / DeterministicSlippage)。
    """

    def calculate_fill_price(
        self,
        direction: DIRECTION_TYPES,
        low: Number,
        high: Number,
        close: Number,
        attitude: ATTITUDE_TYPES,
        rng,
    ) -> Decimal:
        """
        计算成交价

        Args:
            direction: 买卖方向 (LONG=买, SHORT=卖)
            low: 当日最低价 (AttitudePricing 采样区间下界)
            high: 当日最高价 (AttitudePricing 采样区间上界)
            close: 当日收盘价 (DeterministicSlippage 基准价)
            attitude: 撮合态度 (AttitudePricing 用, DeterministicSlippage 忽略)
            rng: 随机数生成器 (AttitudePricing 用, DeterministicSlippage 忽略)

        Returns:
            Decimal: 成交价
        """
        ...


class DeterministicSlippage:
    """
    确定性滑点成交价模型 (ADR-037 D1)

    包装 SlippageModel (Fixed/Percentage/No), 成交价 = SlippageModel.apply(close, direction)。
    接通 --slippage 的执行侧 (B2 装配注入)。
    """

    def __init__(self, slippage_model):
        """
        Args:
            slippage_model: SlippageModel 实例 (FixedSlippage/PercentageSlippage/NoSlippage)
        """
        self._slippage_model = slippage_model

    def calculate_fill_price(
        self,
        direction: DIRECTION_TYPES,
        low: Number,
        high: Number,
        close: Number,
        attitude: ATTITUDE_TYPES,
        rng,
    ) -> Decimal:
        return self._slippage_model.apply(to_decimal(close), direction)

    def __repr__(self) -> str:
        return f"DeterministicSlippage({self._slippage_model!r})"


class AttitudePricing:
    """
    态度采样成交价模型 (ADR-037 D1)

    移植 sim_broker._get_random_transaction_price (scipy 态度采样, 逐字节复刻保零回归)。
    成交价 ∈ [low, high]: mean=(low+high)/2, std_dev=(high-low)/6。
    - RANDOM: norm 正态采样
    - OPTIMISTIC: LONG→右偏(成交价偏高, 买贵), SHORT→左偏(卖便宜)
    - PESSIMISTIC: LONG→左偏, SHORT→右偏
    涨停/跌停 (high==low): 锁定价直接返回, 不采样 (#5491)。
    """

    def calculate_fill_price(
        self,
        direction: DIRECTION_TYPES,
        low: Number,
        high: Number,
        close: Number,
        attitude: ATTITUDE_TYPES,
        rng,
    ) -> Decimal:
        low_f = float(to_decimal(low))
        high_f = float(to_decimal(high))
        # #5491: 一字板 (high==low) 锁定价直接返回, 显式 guard 消除 scipy 版本依赖
        if high_f == low_f:
            return to_decimal(round(high_f, 2))
        mean = (low_f + high_f) / 2
        std_dev = (high_f - low_f) / 6

        from scipy import stats

        if attitude == ATTITUDE_TYPES.RANDOM:
            rs = stats.norm.rvs(loc=mean, scale=std_dev, size=1, random_state=rng)
        else:
            skewness_right = mean
            skewness_left = -mean
            if attitude == ATTITUDE_TYPES.OPTIMISTIC:
                if direction == DIRECTION_TYPES.LONG:
                    rs = stats.skewnorm.rvs(
                        skewness_right, loc=mean, scale=std_dev, size=1, random_state=rng
                    )
                else:
                    rs = stats.skewnorm.rvs(
                        skewness_left, loc=mean, scale=std_dev, size=1, random_state=rng
                    )
            elif attitude == ATTITUDE_TYPES.PESSIMISTIC:
                if direction == DIRECTION_TYPES.LONG:
                    rs = stats.skewnorm.rvs(
                        skewness_left, loc=mean, scale=std_dev, size=1, random_state=rng
                    )
                else:
                    rs = stats.skewnorm.rvs(
                        skewness_right, loc=mean, scale=std_dev, size=1, random_state=rng
                    )

        raw_result = rs[0]
        clipped = max(low_f, min(high_f, raw_result))  # 限制在 [low, high] 内
        return to_decimal(round(clipped, 2))

    def __repr__(self) -> str:
        return "AttitudePricing()"


def build_fill_price_model(slippage_rate=None) -> FillPriceModel:
    """根据 slippage_rate 构建成交价模型 (ADR-037 D2 统一断点)

    回测侧 (create_broker_from_config) 与模拟侧 (assemble_engine) 共用此工厂,
    避免两处分别内联装配逻辑。

    - slippage_rate is None: AttitudePricing (零回归默认, scipy 态度采样)
    - slippage_rate is not None: DeterministicSlippage(PercentageSlippage)
      (百分比小数, 0.001 = 0.1%)
    """
    if slippage_rate is None:
        return AttitudePricing()
    from ginkgo.trading.paper.slippage_models import PercentageSlippage
    return DeterministicSlippage(PercentageSlippage(percentage=Decimal(str(slippage_rate))))
