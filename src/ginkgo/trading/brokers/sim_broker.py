"""
SimBroker - 回测模拟撮合Broker

基于新的BaseBroker和IBroker接口，提供统一的回测模拟撮合功能。
支持滑点、态度设置、手续费计算等回测功能。
"""

import pandas as pd
import random
from decimal import Decimal
from typing import Dict, List, Optional, Any
from scipy import stats

from ginkgo.trading.bases.base_broker import BaseBroker
from ginkgo.trading.interfaces.broker_interface import IBroker, BrokerExecutionResult
from ginkgo.trading.entities import Order
from ginkgo.enums import DIRECTION_TYPES, ORDER_TYPES, ATTITUDE_TYPES, ORDERSTATUS_TYPES
from ginkgo.libs import to_decimal, Number


class SimBroker(BaseBroker, IBroker):
    """
    回测模拟撮合Broker

    基于新的BaseBroker和IBroker接口，提供回测专用的模拟撮合功能。
    支持滑点、态度设置、手续费计算等回测功能。

    核心特点：
    - 立即执行：支持同步立即执行（回测模式）
    - 模拟撮合：基于随机价格和滑点模型
    - 完整验证：订单验证、资金检查、价格限制
    - 内存管理：使用BaseBroker的市场数据缓存
    """

    def __init__(self, name: str = "SimBroker", **config):
        """
        初始化SimBroker

        Args:
            name: Broker名称
            config: 配置字典，包含：
                - attitude: 撮合态度 (OPTIMISTIC/PESSIMISTIC/RANDOM)
                - commission_rate: 手续费率 (默认0.0003)
                - commission_min: 最小手续费 (默认5)
                - slip_base: 滑点基数 (默认0.01)
        """
        super().__init__(name=name)

        # 模拟交易配置
        self._attitude = config.get("attitude", ATTITUDE_TYPES.RANDOM)
        self._commission_rate = Decimal(str(config.get("commission_rate", 0.0003)))
        self._commission_min = config.get("commission_min", 5)
        self._slip_base = config.get("slip_base", 0.01)

        # 设置市场属性（用于Router市场映射）
        self.market = "SIM"  # 通用模拟市场，支持所有品种

        self.log("INFO", f"SimBroker initialized with attitude={self._attitude.name}, commission_rate={self._commission_rate}")

    # ============= IBroker接口实现 =============
    def submit_order_event(self, event) -> BrokerExecutionResult:
        """
        提交订单事件 - 同步立即执行（回测模式）

        Args:
            event: 订单事件对象

        Returns:
            BrokerExecutionResult: 执行结果（立即返回最终状态）
        """
        order = event.payload
        self.log("INFO", f"📝 [SIMBROKER] ORDER EVENT RECEIVED: {order.direction.name} {order.volume} {order.code} (uuid: {order.uuid[:8]})")
        self.log("DEBUG", f"🔍 [EVENT CONTEXT] portfolio_id={getattr(event, 'portfolio_id', 'N/A')}, "
                        f"engine_id={getattr(event, 'engine_id', 'N/A')}, "
                        f"run_id={getattr(event, 'run_id', 'N/A')}")

        # 保存事件上下文，用于后续Position创建
        self._current_event = event

        # 基础验证
        if not self.validate_order(order):
            self.log("ERROR", f"❌ [SIMBROKER] Order validation failed: {order.uuid[:8]}")
            return BrokerExecutionResult(
                status=ORDERSTATUS_TYPES.NEW,  # REJECTED
                error_message="Order validation failed by SimBroker"
            )

        broker_order_id = f"SIM_{order.uuid[:8]}"
        self.log("DEBUG", f"🔧 [SIMBROKER] Generated broker_order_id: {broker_order_id}")

        # 直接同步撮合（回测模式特点）
        try:
            self.log("DEBUG", f"⚡ [SIMBROKER] Starting synchronous execution...")
            result = self._simulate_execution_sync(order, broker_order_id)
            self.log("INFO", f"✅ [SIMBROKER] EXECUTION COMPLETE: {result.status.name} "
                           f"{result.filled_volume} {order.code} @ {result.filled_price} (trade_id: {result.trade_id})")
            self.log("INFO", f"💰 [SIMBROKER] Commission: {result.commission}, Error: {result.error_message}")

            # 如果订单完全成交，打印详细信息
            if result.status == ORDERSTATUS_TYPES.FILLED:
                self.log("INFO", f"🎉 [SIMBROKER] ORDER FULLY EXECUTED!")
                self.log("INFO", f"📊 [SIMBROKER] EXECUTION SUMMARY: {result.filled_volume} shares @ {result.filled_price}, commission={result.commission}")
            else:
                self.log("WARN", f"⚠️ [SIMBROKER] ORDER NOT FILLED: status={result.status.name}")
                self.log("WARN", f"🔍 [SIMBROKER] DETAILS: filled_volume={result.filled_volume}, filled_price={result.filled_price}, error='{result.error_message}'")
                self.log("WARN", f"🔍 [SIMBROKER] BROKER_ORDER_ID: {result.broker_order_id}, TRADE_ID: {result.trade_id}")
            return result
        except Exception as e:
            self.log("ERROR", f"❌ [SIMBROKER] Execution error: {e}")
            return BrokerExecutionResult(
                status=ORDERSTATUS_TYPES.NEW,  # REJECTED
                broker_order_id=broker_order_id,
                error_message=f"SimBroker execution error: {str(e)}"
            )

    
    def validate_order(self, order: Order) -> bool:
        """
        验证订单基础有效性

        Args:
            order: 订单对象

        Returns:
            bool: 是否有效
        """
        self.log("DEBUG", f"🔍 [SIMBROKER] VALIDATING ORDER: {order.uuid[:8]}")

        if not order or not hasattr(order, 'uuid'):
            self.log("ERROR", f"❌ [SIMBROKER] Invalid order object: no uuid attribute")
            return False

        if not order.code or not isinstance(order.code, str):
            self.log("ERROR", f"❌ [SIMBROKER] Invalid order code: '{order.code}'")
            return False

        if order.volume <= 0:
            self.log("ERROR", f"❌ [SIMBROKER] Invalid volume: {order.volume} <= 0")
            return False

        # 检查是否有市场数据
        self.log("DEBUG", f"📊 [SIMBROKER] Checking market data for {order.code}...")
        market_data = self.get_market_data(order.code)
        if market_data is None:
            self.log("ERROR", f"❌ [SIMBROKER] No market data for {order.code}")
            return False

        self.log("DEBUG", f"✅ [SIMBROKER] Market data found for {order.code}: type={type(market_data)}")
        if hasattr(market_data, 'close'):
            self.log("DEBUG", f"💰 [SIMBROKER] Close price: {market_data.close}")

        self.log("DEBUG", f"✅ [SIMBROKER] Order validation PASSED for {order.uuid[:8]}")
        return True

    def supports_immediate_execution(self) -> bool:
        """SimBroker支持立即执行（回测模式）"""
        return True

    def requires_manual_confirmation(self) -> bool:
        """SimBroker不需要人工确认"""
        return False

    def supports_api_trading(self) -> bool:
        """SimBroker不支持真实API交易"""
        return False

    def cancel_order(self, order_id: str) -> BrokerExecutionResult:
        """
        取消订单（模拟环境中订单立即执行，无法取消）

        Args:
            order_id: 订单ID

        Returns:
            BrokerExecutionResult: 取消结果
        """
        self.log("WARN", f"🚫 CANCEL REQUESTED: {order_id} (SimBroker orders execute immediately)")
        return BrokerExecutionResult(
            status=ORDERSTATUS_TYPES.NEW,  # REJECTED
            error_message="Cannot cancel: SimBroker orders execute immediately"
        )

    # ============= 核心同步执行逻辑 =============
    def _simulate_execution_sync(self, order: Order, broker_order_id: str) -> BrokerExecutionResult:
        """
        同步模拟撮合核心逻辑 - 立即返回最终执行结果

        Args:
            order: 订单对象
            broker_order_id: Broker订单ID

        Returns:
            BrokerExecutionResult: 执行结果
        """
        self.log("DEBUG", f"🎯 [SIMBROKER] SIMULATE EXECUTION START: {order.uuid[:8]}")

        try:
            # 1. 获取市场数据
            self.log("DEBUG", f"📊 [SIMBROKER] Step 1: Getting market data for {order.code}...")
            market_data = self.get_market_data(order.code)
            if market_data is None:
                self.log("ERROR", f"❌ [SIMBROKER] No market data for {order.code}")
                return BrokerExecutionResult(
                    status=ORDERSTATUS_TYPES.NEW,  # REJECTED
                    broker_order_id=broker_order_id,
                    error_message=f"No market data available for {order.code}"
                )
            self.log("DEBUG", f"✅ [SIMBROKER] Market data obtained for {order.code}")

            # 2. 价格验证
            self.log("DEBUG", f"💰 [SIMBROKER] Step 2: Validating price data...")
            if not self._is_price_valid(order.code, market_data):
                self.log("ERROR", f"❌ [SIMBROKER] Invalid price data for {order.code}")
                return BrokerExecutionResult(
                    status=ORDERSTATUS_TYPES.CANCELED,
                    broker_order_id=broker_order_id,
                    error_message="Invalid price data"
                )
            self.log("DEBUG", f"✅ [SIMBROKER] Price validation passed")

            # 3. 订单类型检查
            self.log("DEBUG", f"📋 [SIMBROKER] Step 3: Checking if order can be filled...")
            if not self._can_order_be_filled(order, market_data):
                self.log("ERROR", f"❌ [SIMBROKER] Order cannot be filled at current price")
                return BrokerExecutionResult(
                    status=ORDERSTATUS_TYPES.CANCELED,
                    broker_order_id=broker_order_id,
                    error_message="Order cannot be filled at current price"
                )
            self.log("DEBUG", f"✅ [SIMBROKER] Order can be filled")

            # 4. 涨跌停检查
            self.log("DEBUG", f"🚫 [SIMBROKER] Step 4: Checking price limits...")
            if self._is_limit_blocked(order, market_data):
                self.log("ERROR", f"❌ [SIMBROKER] Price limit blocked for {order.code}")
                return BrokerExecutionResult(
                    status=ORDERSTATUS_TYPES.CANCELED,
                    broker_order_id=broker_order_id,
                    error_message="Price limit up/down"
                )
            self.log("DEBUG", f"✅ [SIMBROKER] No price limit restrictions")

            # 5. 计算成交价格（已包含滑点效应）
            self.log("DEBUG", f"🧮 [SIMBROKER] Step 5: Calculating transaction price...")
            transaction_price = self._calculate_transaction_price(order, market_data)
            self.log("DEBUG", f"💰 [SIMBROKER] Transaction price calculated: {transaction_price}")

            # 6. 调整成交数量（资金检查）
            self.log("DEBUG", f"📊 [SIMBROKER] Step 6: Adjusting volume for funds...")
            transaction_volume = self._adjust_volume_for_funds(order, transaction_price)
            self.log("DEBUG", f"📈 [SIMBROKER] Transaction volume: {transaction_volume}")
            if transaction_volume == 0:
                self.log("ERROR", f"❌ [SIMBROKER] Insufficient funds for execution")
                return BrokerExecutionResult(
                    status=ORDERSTATUS_TYPES.CANCELED,
                    broker_order_id=broker_order_id,
                    error_message="Insufficient funds for execution"
                )

            # 7. 计算费用
            self.log("DEBUG", f"💸 [SIMBROKER] Step 7: Calculating commission...")
            transaction_money = transaction_price * transaction_volume
            commission = self._calculate_commission(transaction_money, order.direction == DIRECTION_TYPES.LONG)
            self.log("DEBUG", f"💰 [SIMBROKER] Transaction money: {transaction_money}, Commission: {commission}")

            # 8. SimBroker不管理持仓，只负责撮合和生成事件
            self.log("DEBUG", f"🏠 [SIMBROKER] Step 8: SIMBROKER DOES NOT MANAGE POSITIONS")
            self.log("DEBUG", f"📊 [SIMBROKER] Position management is Portfolio's responsibility")
            self.log("DEBUG", f"✅ [SIMBROKER] Order execution completed, portfolio will manage positions")

            # 9. SimBroker只负责撮合，事件发布由Router处理
            self.log("DEBUG", f"📋 [SIMBROKER] Step 9: SimBroker matching completed")
            self.log("DEBUG", f"📋 [SIMBROKER] Router will handle event creation and publishing")
            self.log("INFO", f"✅ [SIMBROKER] Matching complete: {transaction_volume} {order.code} @ {transaction_price}")

            # 10. 创建执行结果（包含完整Order对象）
            result = BrokerExecutionResult(
                status=ORDERSTATUS_TYPES.FILLED,
                broker_order_id=broker_order_id,
                filled_volume=transaction_volume,
                filled_price=float(transaction_price),
                commission=float(commission),
                trade_id=f"SIM_TRADE_{order.uuid[:8]}",
                order=order  # 传入完整的Order对象，用于生成事件的payload
            )

            self.log("INFO", f"🎉 [SIMBROKER] SIMULATION SUCCESS: FILLED {transaction_volume} {order.code} @ {transaction_price}")
            return result

        except Exception as e:
            self.log("ERROR", f"❌ [SIMBROKER] Simulation execution error: {e}")
            import traceback
            self.log("ERROR", f"❌ [SIMBROKER] Traceback: {traceback.format_exc()}")
            return BrokerExecutionResult(
                status=ORDERSTATUS_TYPES.NEW,  # REJECTED
                broker_order_id=broker_order_id,
                error_message=f"Simulation error: {str(e)}"
            )

    # ============= 价格和费用计算方法 =============

    def _calculate_transaction_price(self, order: Order, market_data: Any) -> Decimal:
        """
        计算成交价格 - 从MatchMakingSim.get_random_transaction_price()提取

        Args:
            order: 订单对象
            market_data: 市场数据

        Returns:
            Decimal: 成交价格
        """
        if hasattr(order, "order_type") and order.order_type == ORDER_TYPES.LIMITORDER:
            return to_decimal(order.limit_price)

        # 市价单使用随机价格模拟滑点
        # 处理Bar对象或字典格式
        if hasattr(market_data, 'low') and hasattr(market_data, 'high'):
            low_price = market_data.low
            high_price = market_data.high
        elif isinstance(market_data, dict):
            low_price = market_data.get("low")
            high_price = market_data.get("high")
        else:
            # 如果无法获取价格数据，使用当前价格
            low_price = high_price = getattr(market_data, 'close', None) or 0

        return self._get_random_transaction_price(
            order.direction, low_price, high_price, self._attitude
        )

    def _get_random_transaction_price(self, direction: DIRECTION_TYPES, low: Number, high: Number, attitude) -> Decimal:
        """
        随机成交价格计算 - 直接从MatchMakingSim提取

        Args:
            direction: 买卖方向
            low: 最低价
            high: 最高价
            attitude: 撮合态度

        Returns:
            Decimal: 随机成交价格
        """
        low = float(to_decimal(low))
        high = float(to_decimal(high))
        mean = (low + high) / 2
        std_dev = (high - low) / 6

        from ginkgo.enums import ATTITUDE_TYPES
        from scipy import stats

        if attitude == ATTITUDE_TYPES.RANDOM:
            rs = stats.norm.rvs(loc=mean, scale=std_dev, size=1)
        else:
            skewness_right = mean
            skewness_left = -mean
            if attitude == ATTITUDE_TYPES.OPTIMISTIC:
                if direction == DIRECTION_TYPES.LONG:
                    rs = stats.skewnorm.rvs(skewness_right, loc=mean, scale=std_dev, size=1)
                else:
                    rs = stats.skewnorm.rvs(skewness_left, loc=mean, scale=std_dev, size=1)
            elif attitude == ATTITUDE_TYPES.PESSIMISTIC:
                if direction == DIRECTION_TYPES.LONG:
                    rs = stats.skewnorm.rvs(skewness_left, loc=mean, scale=std_dev, size=1)
                else:
                    rs = stats.skewnorm.rvs(skewness_right, loc=mean, scale=std_dev, size=1)

        rs = max(low, min(high, rs[0]))  # 限制在合理范围内
        return to_decimal(round(rs, 2))

    def _calculate_commission(self, transaction_money: Number, is_long: bool) -> Decimal:
        """
        计算手续费（A股标准）

        Args:
            transaction_money: 交易金额
            is_long: 是否为买入

        Returns:
            Decimal: 手续费（包含佣金和印花税）
        """
        # 基础佣金（买卖均收）
        commission = to_decimal(transaction_money) * self._commission_rate
        commission = max(commission, to_decimal(self._commission_min))

        # 印花税（仅卖出收取）
        if not is_long:  # 卖出
            stamp_duty = to_decimal(transaction_money) * Decimal("0.001")  # 0.1%印花税
            commission += stamp_duty

        return commission

    def _adjust_volume_for_funds(self, order: Order, price: Decimal) -> int:
        """
        根据资金调整成交数量（简化版本，假设资金充足）

        Args:
            order: 订单对象
            price: 成交价格

        Returns:
            int: 调整后的成交数量
        """
        # 回测模式下，假设资金充足，直接返回订单数量
        # 实际资金检查由Portfolio层面的风控处理
        return order.volume

    def _is_price_valid(self, code: str, price_data: Any) -> bool:
        """价格有效性检查"""
        if price_data is None:
            return False

        # 检查必要字段是否存在
        if hasattr(price_data, 'index'):  # pandas Series
            required_fields = ["open", "high", "low", "close", "volume"]
            return all(field in price_data.index for field in required_fields)
        else:  # 其他类型（如字典或对象）
            return all(hasattr(price_data, field) or (isinstance(price_data, dict) and field in price_data)
                      for field in ["open", "high", "low", "close", "volume"])

    def _can_order_be_filled(self, order: Order, price_data: Any) -> bool:
        """
        订单是否可以成交 - 基于价格位置和态度的概率成交机制

        Args:
            order: 订单对象
            price_data: 价格数据，包含low, high等字段

        Returns:
            bool: 是否可以成交
        """
        # 市价单总是可以成交
        if not (hasattr(order, "order_type") and order.order_type == ORDER_TYPES.LIMITORDER):
            return True

        # 获取价格数据
        if hasattr(price_data, 'low'):
            low_price = float(price_data.low)
            high_price = float(price_data.high)
        elif isinstance(price_data, dict):
            low_price = float(price_data.get("low", 0))
            high_price = float(price_data.get("high", 0))
        else:
            return True  # 无法获取价格数据，默认可成交

        limit_price = float(order.limit_price)

        # 基本可行性检查：限价必须在当日价格区间内
        if order.direction == DIRECTION_TYPES.LONG:
            if limit_price < low_price:
                return False
        else:  # 卖出
            if limit_price > high_price:
                return False

        # 简化的成交概率模型
        if self._attitude == ATTITUDE_TYPES.OPTIMISTIC:
            return True  # 乐观态度，总是成交
        elif self._attitude == ATTITUDE_TYPES.PESSIMISTIC:
            return random.random() > 0.3  # 悲观态度，70%成交概率
        else:  # RANDOM
            return random.random() > 0.2  # 随机态度，80%成交概率

    def _is_limit_blocked(self, order: Order, price_data: Any) -> bool:
        """检查是否因涨跌停无法成交（简化版本）"""
        # 简化版本，不实现涨跌停逻辑
        return False

    # ============= 状态查询方法 =============
    def get_broker_status(self) -> Dict[str, Any]:
        """
        获取SimBroker状态

        Returns:
            Dict[str, Any]: 状态信息
        """
        return {
            'name': self.name,
            'market': getattr(self, 'market', 'SIM'),
            'execution_mode': 'backtest',
            'attitude': self._attitude.name if hasattr(self._attitude, 'name') else str(self._attitude),
            'commission_rate': float(self._commission_rate) if self._commission_rate else 0.0,
            'commission_min': float(self._commission_min) if self._commission_min else 0.0,
            'market_data_count': len(self._current_market_data) if hasattr(self, '_current_market_data') else 0,
            'position_count': len(self._current_positions) if hasattr(self, '_current_positions') else 0,
            'supports_immediate_execution': self.supports_immediate_execution(),
            'requires_manual_confirmation': self.requires_manual_confirmation(),
            'supports_api_trading': self.supports_api_trading()
        }
