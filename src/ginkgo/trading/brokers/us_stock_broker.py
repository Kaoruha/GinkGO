# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: Us Stock Broker经纪商继承BaseBroker提供USStockBroker美股交易模拟






"""
USStockBroker - 美股实盘交易Broker

基于LiveBrokerBase，实现美股市场的实盘交易功能。
支持T+0交易，支持盘前盘后交易等美股特色规则。
"""

from decimal import Decimal
from typing import Dict, Any

from ginkgo.trading.brokers.live_broker_base import LiveBrokerBase
from ginkgo.trading.interfaces.broker_interface import BrokerExecutionResult
from ginkgo.trading.entities import Order
from ginkgo.enums import ORDERSTATUS_TYPES, DIRECTION_TYPES, ORDER_TYPES
from ginkgo.libs import to_decimal, GLOG


class USStockBroker(LiveBrokerBase):
    """
    美股实盘交易Broker

    核心特点：
    - 美股代码格式验证（如 AAPL, TSLA, MSFT）
    - T+0交易制度（当天可买卖）
    - 支持盘前盘后交易
    - 多种订单类型（市价、限价、止损等）
    - 无最小交易数量限制
    - 美元结算
    """

    def __init__(self, name: str = "USStockBroker", **config):
        """
        初始化USStockBroker

        Args:
            name: Broker名称
            config: 配置字典，包含：
                - api_key: 券商API密钥
                - api_secret: 券商API密钥
                - account_id: 资金账户ID
                - commission_rate: 手续费率 (默认0.005)
                - commission_min: 最小手续费 (默认0.99)
                - extended_hours: 是否支持盘前盘后交易 (默认False)
                - dry_run: 是否为模拟运行（默认False）
        """
        super().__init__(name=name, market="美股", **config)

        # 美股特有配置
        self._extended_hours = config.get("extended_hours", False)  # 盘前盘后交易

        GLOG.INFO(f"USStockBroker initialized with account_id={self._account_id}, "
                        f"extended_hours={self._extended_hours}")

    def _get_default_commission_rate(self) -> Decimal:
        """获取美股默认手续费率"""
        return Decimal("0.005")  # 千分之5（部分券商免佣金）

    def _get_default_commission_min(self) -> float:
        """获取美股默认最小手续费"""
        return 0.99  # 0.99美元

    def _connect_api(self) -> bool:
        """
        连接美股券商API

        Returns:
            bool: 连接是否成功
        """
        try:
            # TODO: 实现具体的美股券商API连接逻辑
            # 例如：
            # import alpaca_trade_api as tradeapi
            # self._api = tradeapi.REST(
            #     key_id=self._api_key,
            #     secret_key=self._api_secret,
            #     base_url='https://paper-api.alpaca.markets'
            # )
            # account = self._api.get_account()
            # if account.status != 'ACTIVE':
            #     raise Exception("Account not active")

            GLOG.INFO("🔗 美股券商API连接成功（模拟）")
            return True

        except Exception as e:
            GLOG.ERROR(f"❌ 美股券商API连接失败: {e}")
            return False

    def _disconnect_api(self) -> bool:
        """
        断开美股券商API连接

        Returns:
            bool: 断开是否成功
        """
        try:
            # TODO: 实现具体的断开逻辑
            # self._api.close()

            GLOG.INFO("🔌 美股券商API断开成功（模拟）")
            return True

        except Exception as e:
            GLOG.ERROR(f"❌ 美股券商API断开失败: {e}")
            return False

    def _submit_to_exchange(self, order: Order) -> BrokerExecutionResult:
        """
        提交订单到美股交易所

        Args:
            order: 订单对象

        Returns:
            BrokerExecutionResult: 提交结果
        """
        try:
            # TODO: 实现具体的美股订单提交逻辑
            # 示例逻辑（需要根据具体券商API调整）：
            # order_params = self._build_us_order_params(order)
            # response = self._api.submit_order(**order_params)
            # broker_order_id = response.id

            broker_order_id = f"US_SUBMIT_{order.uuid[:8]}"

            # 美股规则检查
            if not self._validate_us_order_rules(order):
                return BrokerExecutionResult(
                    status=ORDERSTATUS_TYPES.NEW,  # REJECTED
                    broker_order_id=broker_order_id,
                    error_message="Order violates 美股交易规则"
                )

            GLOG.INFO(f"📈 订单已提交到美股交易所: {broker_order_id}")

            return BrokerExecutionResult(
                status=ORDERSTATUS_TYPES.SUBMITTED,
                broker_order_id=broker_order_id,
                error_message=None
            )

        except Exception as e:
            GLOG.ERROR(f"❌ 美股订单提交失败: {e}")
            return BrokerExecutionResult(
                status=ORDERSTATUS_TYPES.NEW,  # REJECTED
                error_message=f"美股订单提交失败: {str(e)}"
            )

    def _cancel_from_exchange(self, broker_order_id: str) -> BrokerExecutionResult:
        """
        从美股交易所撤销订单

        Args:
            broker_order_id: Broker订单ID

        Returns:
            BrokerExecutionResult: 撤销结果
        """
        try:
            # TODO: 实现具体的美股撤单逻辑
            GLOG.INFO(f"🚫 美股撤单请求已发送: {broker_order_id}")

            return BrokerExecutionResult(
                status=ORDERSTATUS_TYPES.CANCELED,
                broker_order_id=broker_order_id,
                error_message=None
            )

        except Exception as e:
            GLOG.ERROR(f"❌ 美股撤单失败: {e}")
            return BrokerExecutionResult(
                status=ORDERSTATUS_TYPES.NEW,  # REJECTED
                broker_order_id=broker_order_id,
                error_message=f"美股撤单失败: {str(e)}"
            )

    def _query_from_exchange(self, broker_order_id: str) -> BrokerExecutionResult:
        """
        从美股交易所查询订单状态

        Args:
            broker_order_id: Broker订单ID

        Returns:
            BrokerExecutionResult: 查询结果
        """
        try:
            # TODO: 实现具体的美股查单逻辑
            GLOG.DEBUG(f"🔍 查询美股订单状态: {broker_order_id}")

            return BrokerExecutionResult(
                status=ORDERSTATUS_TYPES.SUBMITTED,  # 模拟状态
                broker_order_id=broker_order_id,
                filled_volume=0,
                filled_price=0.0,
                error_message=None
            )

        except Exception as e:
            GLOG.ERROR(f"❌ 美股查单失败: {e}")
            return BrokerExecutionResult(
                status=ORDERSTATUS_TYPES.NEW,  # REJECTED
                broker_order_id=broker_order_id,
                error_message=f"美股查单失败: {str(e)}"
            )

    def _validate_stock_code(self, code: str) -> bool:
        """
        验证美股代码格式

        Args:
            code: 股票代码

        Returns:
            bool: 是否有效
        """
        if not code:
            return False

        # 美股代码通常是1-5个字母，不包含数字
        # 例如：AAPL, TSLA, MSFT, GOOGL, BRK.A
        clean_code = code.split('.')[0]  # 移除可能的后缀

        # 检查是否只包含字母
        if not clean_code.replace('.', '').replace('-', '').isalpha():
            return False

        # 检查长度（1-5个字母，特殊情况如BRK.A）
        if len(clean_code) < 1 or len(clean_code) > 10:
            return False

        return True

    def _validate_us_order_rules(self, order: Order) -> bool:
        """
        验证美股订单规则

        Args:
            order: 订单对象

        Returns:
            bool: 是否符合规则
        """
        # 美股没有最小交易数量限制，可以买1股
        min_trade_size = 1

        if order.volume < min_trade_size:
            GLOG.WARN(f"美股最小交易数量为{min_trade_size}股: {order.volume}")
            return False

        # 检查限价单价格
        if hasattr(order, 'order_type') and order.order_type == ORDER_TYPES.LIMITORDER:
            if order.limit_price <= 0:
                GLOG.WARN(f"美股限价单价格必须大于0: {order.limit_price}")
                return False

            # 美股价格精度检查（通常是2位小数）
            if isinstance(order.limit_price, float):
                price_str = f"{order.limit_price:.6f}"
                if len(price_str.split('.')[-1]) > 6:
                    GLOG.WARN(f"美股价格精度过高: {order.limit_price}")
                    return False

        # 检查是否在交易时间内
        if not self._is_market_hours():
            if not self._extended_hours:
                GLOG.WARN("美股非交易时间，且未启用盘前盘后交易")
                return False

        return True

    def _is_market_hours(self) -> bool:
        """
        检查当前是否为美股交易时间

        Returns:
            bool: 是否在交易时间内
        """
        # TODO: 实现具体的美股交易时间检查逻辑
        # 美股常规交易时间：9:30 AM - 4:00 PM EST
        # 盘前：4:00 AM - 9:30 AM EST
        # 盘后：4:00 PM - 8:00 PM EST

        # 简化处理，返回True
        return True

    def _calculate_commission(self, transaction_money, is_long: bool) -> Decimal:
        """
        计算美股手续费

        美股手续费相对简单：
        - 大部分券商现在免佣金
        - 部分券商仍收取每股费用或固定费用

        Args:
            transaction_money: 交易金额（美元）
            is_long: 是否为买入

        Returns:
            Decimal: 手续费
        """
        money = to_decimal(transaction_money)

        # 佣金（买卖双向）
        commission = money * self._commission_rate
        commission = max(commission, to_decimal(self._commission_min))

        # 美股没有印花税、过户费等额外费用

        return commission

    def supports_extended_hours(self) -> bool:
        """
        是否支持盘前盘后交易

        Returns:
            bool: 是否支持
        """
        return self._extended_hours

    def get_market_schedule(self) -> Dict[str, Any]:
        """
        获取美股交易时间表

        Returns:
            Dict[str, Any]: 交易时间信息
        """
        return {
            'regular_trading': '9:30 AM - 4:00 PM EST',
            'pre_market': '4:00 AM - 9:30 AM EST',
            'after_hours': '4:00 PM - 8:00 PM EST',
            'extended_hours_enabled': self._extended_hours,
            'timezone': 'EST/EDT'
        }

    def get_broker_status(self) -> Dict[str, Any]:
        """
        获取美股Broker状态

        Returns:
            Dict[str, Any]: 状态信息
        """
        base_status = super().get_broker_status()
        base_status.update({
            'currency': 'USD',
            'extended_hours': self._extended_hours,
            'market_schedule': self.get_market_schedule(),
            'market_features': ['T+0', '无最小交易限制', '支持盘前盘后', '多种订单类型']
        })
        return base_status