# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: Live Broker Base LiveBrokerBase实盘经纪商基类定义实盘交易接口提供相关功能和接口实现






"""
LiveBrokerBase - 实盘交易基础类

基于新的BaseBroker和IBroker接口，提供实盘交易的通用功能。
不同市场的实盘Broker可以继承此类并实现特定的API调用逻辑。
"""

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Dict, List, Optional, Any

from ginkgo.trading.bases.base_broker import BaseBroker
from ginkgo.trading.interfaces.broker_interface import IBroker, BrokerExecutionResult
from ginkgo.trading.entities import Order
from ginkgo.enums import ORDERSTATUS_TYPES, DIRECTION_TYPES, ORDER_TYPES, ATTITUDE_TYPES
from ginkgo.libs import to_decimal, Number


class LiveBrokerBase(BaseBroker, IBroker, ABC):
    """
    实盘交易基础类

    核心特点：
    - API交易：通过券商API进行真实交易
    - 异步执行：订单提交后异步返回执行结果
    - 风控前置：在提交到券商前进行本地风控检查
    - 市场适配：不同市场继承此类实现特定逻辑
    """

    def __init__(self, name: str, market: str, **config):
        """
        初始化LiveBrokerBase

        Args:
            name: Broker名称
            market: 市场（A股、港股、美股、期货等）
            config: 配置字典，包含：
                - api_key: API密钥
                - api_secret: API密钥
                - account_id: 账户ID
                - commission_rate: 手续费率
                - commission_min: 最小手续费
                - dry_run: 是否为模拟运行（默认False）
        """
        super().__init__(name=name)

        # 市场标识
        self.market = market

        # API配置
        self._api_key = config.get("api_key")
        self._api_secret = config.get("api_secret")
        self._account_id = config.get("account_id")
        self._dry_run = config.get("dry_run", False)  # 模拟运行模式

        # 交易配置
        self._commission_rate = Decimal(str(config.get("commission_rate", self._get_default_commission_rate())))
        self._commission_min = config.get("commission_min", self._get_default_commission_min())

        # API连接状态
        self._api_connected = False

        # 计数器用于生成broker_order_id
        self._order_counter = 1

        self.log("INFO", f"LiveBrokerBase initialized for {market}, "
                        f"dry_run={self._dry_run}, "
                        f"commission_rate={self._commission_rate}")

    @abstractmethod
    def _get_default_commission_rate(self) -> Decimal:
        """获取默认手续费率（由子类实现）"""
        pass

    @abstractmethod
    def _get_default_commission_min(self) -> float:
        """获取默认最小手续费（由子类实现）"""
        pass

    @abstractmethod
    def _connect_api(self) -> bool:
        """连接API（由子类实现）"""
        pass

    @abstractmethod
    def _disconnect_api(self) -> bool:
        """断开API连接（由子类实现）"""
        pass

    @abstractmethod
    def _submit_to_exchange(self, order: Order) -> BrokerExecutionResult:
        """提交订单到交易所（由子类实现）"""
        pass

    @abstractmethod
    def _cancel_from_exchange(self, broker_order_id: str) -> BrokerExecutionResult:
        """从交易所撤销订单（由子类实现）"""
        pass

    @abstractmethod
    def _query_from_exchange(self, broker_order_id: str) -> BrokerExecutionResult:
        """从交易所查询订单状态（由子类实现）"""
        pass

    # ============= IBroker接口实现 =============
    def submit_order(self, order: Order) -> BrokerExecutionResult:
        """
        提交订单到实盘市场

        Args:
            order: 订单对象

        Returns:
            BrokerExecutionResult: 提交结果（异步执行）
        """
        self.log("INFO", f"📝 ORDER RECEIVED: {order.direction.name} {order.volume} {order.code}")

        # 基础验证
        if not self.validate_order(order):
            self.log("WARN", f"❌ Order validation failed: {order.uuid[:8]}")
            return BrokerExecutionResult(
                status=ORDERSTATUS_TYPES.NEW,  # REJECTED
                error_message="Order validation failed by LiveBroker"
            )

        # API连接检查
        if not self._api_connected:
            self.log("ERROR", f"❌ API not connected for {self.market}")
            return BrokerExecutionResult(
                status=ORDERSTATUS_TYPES.NEW,  # REJECTED
                error_message=f"API not connected for {self.market}"
            )

        # 生成broker_order_id
        broker_order_id = f"{self.market.upper()}_LIVE_{self._order_counter:06d}"
        self._order_counter += 1

        try:
            # 提交到交易所
            if self._dry_run:
                result = self._simulate_live_execution(order, broker_order_id)
            else:
                result = self._submit_to_exchange(order)

            self.log("INFO", f"📤 SUBMITTED TO EXCHANGE: {broker_order_id} - {result.status.name}")
            return result

        except Exception as e:
            self.log("ERROR", f"❌ Submit to exchange failed: {e}")
            return BrokerExecutionResult(
                status=ORDERSTATUS_TYPES.NEW,  # REJECTED
                broker_order_id=broker_order_id,
                error_message=f"Exchange submission error: {str(e)}"
            )

    def validate_order(self, order: Order) -> bool:
        """
        验证订单基础有效性

        Args:
            order: 订单对象

        Returns:
            bool: 是否有效
        """
        if not order or not hasattr(order, 'uuid'):
            return False
        if not order.code or not isinstance(order.code, str):
            return False
        if order.volume <= 0:
            return False

        # 实盘交易需要检查代码格式是否符合对应市场规则
        return self._validate_stock_code(order.code)

    def supports_immediate_execution(self) -> bool:
        """实盘Broker不支持立即执行"""
        return False

    def requires_manual_confirmation(self) -> bool:
        """实盘Broker不需要人工确认"""
        return False

    def supports_api_trading(self) -> bool:
        """实盘Broker支持API交易"""
        return True

    def cancel_order(self, broker_order_id: str) -> BrokerExecutionResult:
        """
        撤销订单

        Args:
            broker_order_id: Broker订单ID

        Returns:
            BrokerExecutionResult: 撤销结果
        """
        self.log("INFO", f"🚫 CANCEL REQUESTED: {broker_order_id}")

        if not self._api_connected:
            return BrokerExecutionResult(
                status=ORDERSTATUS_TYPES.NEW,  # REJECTED
                error_message="API not connected"
            )

        try:
            if self._dry_run:
                result = BrokerExecutionResult(
                    status=ORDERSTATUS_TYPES.CANCELED,
                    broker_order_id=broker_order_id,
                    error_message=None
                )
            else:
                result = self._cancel_from_exchange(broker_order_id)

            self.log("INFO", f"🚫 CANCEL RESULT: {broker_order_id} - {result.status.name}")
            return result

        except Exception as e:
            self.log("ERROR", f"❌ Cancel from exchange failed: {e}")
            return BrokerExecutionResult(
                status=ORDERSTATUS_TYPES.NEW,  # REJECTED
                broker_order_id=broker_order_id,
                error_message=f"Exchange cancel error: {str(e)}"
            )

    # ============= 子类可重写的方法 =============
    def _validate_stock_code(self, code: str) -> bool:
        """
        验证股票代码格式（子类可重写）

        Args:
            code: 股票代码

        Returns:
            bool: 是否有效
        """
        # 基础验证，子类可以实现特定市场的代码格式验证
        return bool(code) and len(code) > 0

    def _simulate_live_execution(self, order: Order, broker_order_id: str) -> BrokerExecutionResult:
        """
        模拟实盘执行（dry_run模式）

        Args:
            order: 订单对象
            broker_order_id: Broker订单ID

        Returns:
            BrokerExecutionResult: 模拟执行结果
        """
        self.log("INFO", f"🔄 DRY RUN MODE: Simulating execution for {broker_order_id}")

        # 模拟异步提交流程
        result = BrokerExecutionResult(
            status=ORDERSTATUS_TYPES.SUBMITTED,
            broker_order_id=broker_order_id,
            error_message=None
        )

        # 在实际实现中，这里会启动一个异步任务来模拟执行结果
        # 目前只返回SUBMITTED状态
        return result

    def _calculate_commission(self, transaction_money: Number, is_long: bool) -> Decimal:
        """
        计算手续费（子类可重写）

        Args:
            transaction_money: 交易金额
            is_long: 是否为买入

        Returns:
            Decimal: 手续费
        """
        money = to_decimal(transaction_money)
        commission = money * self._commission_rate
        commission = max(commission, to_decimal(self._commission_min))

        # A股卖出需要印花税（子类可以重写这个逻辑）
        if not is_long and self.market == "A股":
            stamp_duty = money * Decimal("0.001")  # 0.1%印花税
            commission += stamp_duty

        return commission

    # ============= 连接管理 =============
    def connect(self) -> bool:
        """连接API"""
        try:
            if self._dry_run:
                self._api_connected = True
                self.log("INFO", f"✅ DRY RUN MODE: Connected to {self.market}")
                return True

            self._api_connected = self._connect_api()
            if self._api_connected:
                self.log("INFO", f"✅ Connected to {self.market} API")
            else:
                self.log("ERROR", f"❌ Failed to connect to {self.market} API")

            return self._api_connected

        except Exception as e:
            self.log("ERROR", f"❌ Connection error: {e}")
            self._api_connected = False
            return False

    def disconnect(self) -> bool:
        """断开API连接"""
        try:
            if self._dry_run:
                self._api_connected = False
                self.log("INFO", f"✅ DRY RUN MODE: Disconnected from {self.market}")
                return True

            success = self._disconnect_api()
            self._api_connected = False

            if success:
                self.log("INFO", f"✅ Disconnected from {self.market} API")
            else:
                self.log("ERROR", f"❌ Failed to disconnect from {self.market} API")

            return success

        except Exception as e:
            self.log("ERROR", f"❌ Disconnection error: {e}")
            return False

    # ============= 状态查询方法 =============
    def get_broker_status(self) -> Dict[str, Any]:
        """
        获取Broker状态

        Returns:
            Dict[str, Any]: 状态信息
        """
        return {
            'name': self.name,
            'market': self.market,
            'execution_mode': 'live_api',
            'api_connected': self._api_connected,
            'dry_run': self._dry_run,
            'commission_rate': float(self._commission_rate),
            'has_credentials': bool(self._api_key and self._api_secret)
        }