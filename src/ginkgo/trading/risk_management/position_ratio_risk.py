from typing import List, Dict
from decimal import Decimal
from ginkgo.trading.bases.risk_base import RiskBase as BaseRiskManagement
from ginkgo.trading.entities.signal import Signal
from ginkgo.trading.entities.order import Order
from ginkgo.trading.events import EventPriceUpdate
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES, EVENT_TYPES, ORDER_TYPES
from ginkgo.libs import Number, to_decimal


class PositionRatioRisk(BaseRiskManagement):
    """
    持仓比例风控模块
    控制单个股票持仓比例和总持仓比例，防止过度集中持仓
    """

    __abstract__ = False

    def __init__(
        self,
        name: str = "PositionRatioRisk",
        max_position_ratio: Number = 0.2,
        max_total_position_ratio: Number = 0.8,
        *args,
        **kwargs,
    ):
        """
        Args:
            max_position_ratio(Number): 单个股票最大持仓比例，小数形式（例如：0.2表示20%）
            max_total_position_ratio(Number): 总持仓比例上限，小数形式（例如：0.8表示80%）
        """
        super(PositionRatioRisk, self).__init__(name, *args, **kwargs)
        self._max_position_ratio = to_decimal(max_position_ratio)
        self._max_total_position_ratio = to_decimal(max_total_position_ratio)
        ratio_percent = float(self._max_position_ratio * 100)
        total_percent = float(self._max_total_position_ratio * 100)
        self.set_name(f"{name}_{ratio_percent:.0f}%_{total_percent:.0f}%")

    @property
    def max_position_ratio(self) -> Decimal:
        return self._max_position_ratio

    @property
    def max_total_position_ratio(self) -> Decimal:
        return self._max_total_position_ratio

    def cal(self, portfolio_info: Dict, order: Order) -> Order:
        """
        订单风控检查，调整订单规模以符合持仓比例限制
        Args:
            portfolio_info(Dict): 投资组合信息
            order(Order): 待处理的订单
        Returns:
            Order: 处理后的订单（可能被调整或拒绝）
        """
        self.log(
            "INFO",
            f"PositionRatioRisk: Processing order - Code: {order.code}, Direction: {order.direction}, Volume: {order.volume}, Type: {order.order_type}, Limit Price: {order.limit_price}",
        )

        if order.direction != DIRECTION_TYPES.LONG:
            # 卖出订单不受持仓比例限制
            self.log("INFO", f"PositionRatioRisk: Sell order for {order.code} passed through without restriction")
            return order

        # 计算当前总资产
        total_worth = to_decimal(portfolio_info.get("worth", 0))
        if total_worth <= 0:
            self.log("WARN", f"PositionRatioRisk: Invalid total worth: {total_worth}")
            return None

        self.log("INFO", f"PositionRatioRisk: Portfolio total worth: {total_worth}")

        # 计算当前持仓总价值
        positions = portfolio_info.get("positions", {})
        total_position_value = to_decimal(0)
        current_position_value = to_decimal(0)
        position_count = 0

        for code, position in positions.items():
            if position and position.volume > 0:
                position_value = to_decimal(position.volume) * to_decimal(position.price)
                total_position_value += position_value
                position_count += 1
                self.log(
                    "INFO",
                    f"PositionRatioRisk: Position {code} - Volume: {position.volume}, Price: {position.price}, Value: {position_value}",
                )
                if code == order.code:
                    current_position_value = position_value

        # 计算当前总持仓比例
        current_total_ratio = total_position_value / total_worth
        self.log(
            "INFO",
            f"PositionRatioRisk: Current positions - Count: {position_count}, Total value: {total_position_value}, Total ratio: {float(current_total_ratio):.2%}",
        )
        self.log("INFO", f"PositionRatioRisk: Current position value for {order.code}: {current_position_value}")

        # 根据订单类型获取执行价格
        if order.order_type == ORDER_TYPES.MARKETORDER:
            # 市价订单：优先从当前市场价格获取，backup使用limit_price
            execution_price = self._get_current_price(portfolio_info, order.code)
            if execution_price <= 0 and order.limit_price > 0:
                execution_price = to_decimal(order.limit_price)
        else:
            # 限价订单：使用limit_price
            execution_price = to_decimal(order.limit_price)

        self.log(
            "INFO",
            f"PositionRatioRisk: Order {order.code}, type: {order.order_type}, limit_price: {order.limit_price}, execution_price: {execution_price}",
        )

        if execution_price <= 0:
            self.log(
                "WARNING",
                f"PositionRatioRisk: Invalid execution price {execution_price} for {order.code}, order type: {order.order_type}, limit_price: {order.limit_price}",
            )
            return None

        # 计算订单执行后的预期持仓价值
        order_value = to_decimal(order.volume) * execution_price
        expected_position_value = current_position_value + order_value
        expected_total_value = total_position_value + order_value

        self.log(
            "INFO",
            f"PositionRatioRisk: Order value calculation - Volume: {order.volume}, Price: {execution_price}, Order value: {order_value}",
        )

        # 检查单股持仓比例
        expected_position_ratio = expected_position_value / total_worth
        current_position_ratio = current_position_value / total_worth if current_position_value > 0 else 0

        self.log("INFO", f"PositionRatioRisk: Single position ratio check for {order.code}")
        self.log(
            "INFO",
            f"  Current ratio: {float(current_position_ratio):.2%}, Expected ratio: {float(expected_position_ratio):.2%}, Limit: {float(self._max_position_ratio):.2%}",
        )

        if expected_position_ratio > self._max_position_ratio:
            # 计算允许的最大订单价值
            max_allowed_position_value = total_worth * self._max_position_ratio
            max_allowed_order_value = max_allowed_position_value - current_position_value

            self.log(
                "INFO",
                f"PositionRatioRisk: Single position limit exceeded - Max allowed position value: {max_allowed_position_value}, Max allowed order value: {max_allowed_order_value}",
            )

            if max_allowed_order_value <= 0:
                self.log(
                    "INFO",
                    f"PositionRatioRisk: Single position ratio limit reached for {order.code} - current ratio: {float(current_position_ratio):.2%}, limit: {float(self._max_position_ratio):.2%}",
                )
                return None

            # 调整订单量
            adjusted_volume = max_allowed_order_value / execution_price
            original_volume = order.volume
            if adjusted_volume < to_decimal(order.volume):
                self.log(
                    "INFO",
                    f"PositionRatioRisk: Adjusting order volume for single position ratio - {order.code}: {original_volume} → {int(adjusted_volume)} (from {float(expected_position_ratio):.2%} to {float(self._max_position_ratio):.2%})",
                )
                order.volume = int(adjusted_volume)
                order.frozen = adjusted_volume * execution_price
                order.remain = order.frozen

        # 检查总持仓比例
        expected_total_ratio = expected_total_value / total_worth

        self.log("INFO", f"PositionRatioRisk: Total position ratio check")
        self.log(
            "INFO",
            f"  Current total ratio: {float(current_total_ratio):.2%}, Expected total ratio: {float(expected_total_ratio):.2%}, Limit: {float(self._max_total_position_ratio):.2%}",
        )

        if expected_total_ratio > self._max_total_position_ratio:
            # 计算允许的最大总持仓价值
            max_allowed_total_value = total_worth * self._max_total_position_ratio
            max_allowed_order_value = max_allowed_total_value - total_position_value

            self.log(
                "INFO",
                f"PositionRatioRisk: Total position limit exceeded - Max allowed total value: {max_allowed_total_value}, Max allowed order value: {max_allowed_order_value}",
            )

            if max_allowed_order_value <= 0:
                self.log(
                    "INFO",
                    f"PositionRatioRisk: Total position ratio limit reached - current ratio: {float(current_total_ratio):.2%}, limit: {float(self._max_total_position_ratio):.2%}",
                )
                return None

            # 调整订单量
            adjusted_volume = max_allowed_order_value / execution_price
            original_volume = order.volume
            if adjusted_volume < to_decimal(order.volume):
                self.log(
                    "INFO",
                    f"PositionRatioRisk: Adjusting order volume for total position ratio - {order.code}: {original_volume} → {int(adjusted_volume)} (from {float(expected_total_ratio):.2%} to {float(self._max_total_position_ratio):.2%})",
                )
                order.volume = int(adjusted_volume)
                order.frozen = adjusted_volume * execution_price
                order.remain = order.frozen

        # 如果调整后的订单量为0，则拒绝订单
        if order.volume <= 0:
            self.log(
                "INFO", f"PositionRatioRisk: Order rejected due to position ratio limits - final volume: {order.volume}"
            )
            return None

        # 记录最终结果
        final_order_value = to_decimal(order.volume) * execution_price
        final_position_ratio = (current_position_value + final_order_value) / total_worth
        final_total_ratio = (total_position_value + final_order_value) / total_worth

        self.log(
            "INFO",
            f"PositionRatioRisk: Order approved - Final volume: {order.volume}, Final position ratio: {float(final_position_ratio):.2%}, Final total ratio: {float(final_total_ratio):.2%}",
        )

        return order

    def _get_current_price(self, portfolio_info: Dict, code: str) -> Decimal:
        """
        获取股票当前市场价格
        优先从持仓信息中获取，然后从数据源获取

        Args:
            portfolio_info(Dict): 投资组合信息
            code(str): 股票代码
        Returns:
            Decimal: 当前价格，如果无法获取则返回0
        """
        # 方法1：从持仓信息中获取当前价格
        positions = portfolio_info.get("positions", {})
        if code in positions and positions[code] is not None:
            position = positions[code]
            if hasattr(position, "price") and position.price > 0:
                return to_decimal(position.price)

        # 方法2：从数据源获取最新价格
        if self._data_feeder is not None:
            try:
                # 获取当前时间戳
                current_time = portfolio_info.get("now")
                if current_time and hasattr(self._data_feeder, "get_latest_price"):
                    price = self._data_feeder.get_latest_price(code, current_time)
                    if price and price > 0:
                        return to_decimal(price)
            except Exception as e:
                self.log("WARNING", f"PositionRatioRisk: Failed to get current price from feeder: {e}")

        # 如果无法获取，记录警告并返回0
        self.log("WARNING", f"PositionRatioRisk: Unable to get current price for {code}")
        return to_decimal(0)

    def generate_signals(self, portfolio_info: Dict, event) -> List[Signal]:
        """
        生成持仓比例风控信号
        当持仓比例超过预警阈值时，可以生成减仓信号

        Args:
            portfolio_info(Dict): 投资组合信息
            event: 事件对象
        Returns:
            List[Signal]: 风控信号列表
        """
        signals = []

        # 只处理价格更新事件
        if not isinstance(event, EventPriceUpdate) and event.event_type != EVENT_TYPES.PRICEUPDATE:
            return signals

        # 计算当前总资产
        total_worth = to_decimal(portfolio_info.get("worth", 0))
        if total_worth <= 0:
            return signals

        self.log("INFO", f"PositionRatioRisk: Monitoring position ratios - Portfolio worth: {total_worth}")

        positions = portfolio_info.get("positions", {})
        total_position_value = to_decimal(0)
        position_details = []

        # 首先收集所有持仓信息
        for code, position in positions.items():
            if position and position.volume > 0:
                position_value = position.volume * position.price
                position_ratio = position_value / total_worth
                total_position_value += position_value

                position_details.append(
                    {
                        "code": code,
                        "value": position_value,
                        "ratio": position_ratio,
                        "volume": position.volume,
                        "price": position.price,
                    }
                )

                self.log(
                    "INFO",
                    f"PositionRatioRisk: Position {code} - Volume: {position.volume}, Price: {position.price}, Value: {position_value}, Ratio: {float(position_ratio):.2%}",
                )

        # 记录总持仓情况
        total_ratio = total_position_value / total_worth if total_worth > 0 else 0
        self.log(
            "INFO",
            f"PositionRatioRisk: Total positions - Count: {len(position_details)}, Total value: {total_position_value}, Total ratio: {float(total_ratio):.2%}",
        )

        # 检查每个持仓的比例并生成信号
        for pos_detail in position_details:
            code = pos_detail["code"]
            position_ratio = pos_detail["ratio"]

            # 如果单股持仓比例超过预警阈值（设为max_position_ratio的120%），生成减仓信号
            warning_ratio = self._max_position_ratio * to_decimal(1.2)
            if position_ratio > warning_ratio:
                # 转换为float进行格式化显示
                position_ratio_float = float(position_ratio)
                warning_ratio_float = float(warning_ratio)
                max_ratio_float = float(self._max_position_ratio)

                self.log("INFO", f"PositionRatioRisk: Position ratio warning triggered for {code}")
                self.log(
                    "INFO",
                    f"  Current ratio: {position_ratio_float:.2%}, Warning threshold: {warning_ratio_float:.2%}, Max allowed: {max_ratio_float:.2%}",
                )

                signal = Signal(
                    portfolio_id=portfolio_info["uuid"],
                    engine_id=self.engine_id,  # 使用self获取engine_id
                    timestamp=portfolio_info["now"],
                    code=code,
                    direction=DIRECTION_TYPES.SHORT,  # 减仓
                    reason=f"Position Ratio Warning ({position_ratio_float:.2%} > {warning_ratio_float:.2%})",
                    source=SOURCE_TYPES.STRATEGY,  # 风控生成的信号也标记为策略来源
                )
                signals.append(signal)
                self.log("INFO", f"PositionRatioRisk: Generated reduction signal for {code}")

        if signals:
            self.log("INFO", f"PositionRatioRisk: Generated {len(signals)} position ratio warning signals")
        else:
            self.log("INFO", f"PositionRatioRisk: No position ratio warnings triggered")

        return signals
