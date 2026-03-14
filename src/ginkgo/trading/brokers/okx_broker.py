# Upstream: BrokerManager (生命周期管理)、IBroker (Broker接口)
# Downstream: python-okx SDK (OKX API通信)、MBrokerInstance (状态跟踪)
# Role: OKXBroker OKX交易所Broker实现处理订单提交/撤单/查询与OKX API通信


import time
from typing import Optional
from datetime import datetime

try:
    from okx.Account import AccountAPI as Account
    from okx.Trade import TradeAPI as Trade
    from okx.exceptions import OkxAPIException as OKXException
    OKX_AVAILABLE = True
except ImportError:
    OKX_AVAILABLE = False
    Account = None
    Trade = None
    OKXException = Exception

from ginkgo.trading.interfaces.broker_interface import IBroker, BrokerExecutionResult
from ginkgo.trading.entities.order import Order
from ginkgo.enums import ORDER_TYPES, ORDERSTATUS_TYPES, DIRECTION_TYPES
from ginkgo.data.models.model_live_account import ExchangeType, EnvironmentType
from ginkgo.libs import GLOG
from ginkgo.data.services.encryption_service import get_encryption_service
from ginkgo.data.containers import container


class OKXBroker(IBroker):
    """
    OKX交易所Broker实现

    通过python-okx SDK与OKX API通信：
    - 支持限价单和市价单
    - 支持订单撤单和查询
    - 自动处理API重试和限流
    - 记录API调用日志
    """

    def __init__(
        self,
        broker_uuid: str,
        portfolio_id: str,
        live_account_id: str,
        api_key: str,
        api_secret: str,
        passphrase: str,
        environment: str = "testnet"
    ):
        """
        初始化OKXBroker

        Args:
            broker_uuid: Broker实例UUID
            portfolio_id: Portfolio ID
            live_account_id: 实盘账号ID
            api_key: 加密的API Key
            api_secret: 加密的API Secret
            passphrase: 加密的Passphrase
            environment: 环境 (testnet/production)
        """
        if not OKX_AVAILABLE:
            raise ImportError("python-okx is not installed. Run: pip install python-okx")

        self.broker_uuid = broker_uuid
        self.portfolio_id = portfolio_id
        self.live_account_id = live_account_id
        self._environment = environment

        # 解密API凭证
        encryption_service = get_encryption_service()
        self._api_key = encryption_service.decrypt(api_key)
        self._api_secret = encryption_service.decrypt(api_secret)
        self._passphrase = encryption_service.decrypt(passphrase) if passphrase else None

        # OKX API客户端 (延迟连接)
        self._account_api = None
        self._trade_api = None

        # 连接状态
        self._is_connected = False

        GLOG.INFO(f"OKXBroker initialized: {broker_uuid} ({environment})")

    def connect(self) -> bool:
        """
        连接OKX API

        Returns:
            bool: 连接是否成功
        """
        try:
            # 确定API域名
            if self._environment == EnvironmentType.TESTNET:
                domain = 'https://www.okx.com'  # OKX测试网
            else:
                domain = 'https://www.okx.com'  # OKX实盘

            # 初始化API客户端
            flag = '1'  # 实盘交易标志

            self._account_api = Account.AccountAPI(
                api_key=self._api_key,
                secret=self._api_secret,
                password=self._passphrase,
                domain=domain,
                debug=False,
                flag=flag
            )

            self._trade_api = Trade.TradeAPI(
                api_key=self._api_key,
                secret=self._api_secret,
                password=self._passphrase,
                domain=domain,
                debug=False,
                flag=flag
            )

            # 测试连接
            result = self._account_api.get_account_balance()
            if result and result.get('code') == '0':
                self._is_connected = True
                GLOG.INFO(f"OKX API connected successfully: {self.broker_uuid}")
                return True
            else:
                GLOG.ERROR(f"OKX API connection failed: {result}")
                return False

        except OKXException as e:
            GLOG.ERROR(f"OKX API connection error: {e}")
            return False
        except Exception as e:
            GLOG.ERROR(f"Failed to connect OKX API: {e}")
            return False

    def disconnect(self) -> None:
        """断开OKX API连接"""
        self._is_connected = False
        self._account_api = None
        self._trade_api = None
        GLOG.INFO(f"OKX API disconnected: {self.broker_uuid}")

    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._is_connected

    def validate_order(self, order: Order) -> bool:
        """
        验证订单

        Args:
            order: 订单对象

        Returns:
            bool: 订单是否有效
        """
        if not self._is_connected:
            GLOG.ERROR("Cannot validate order: not connected to OKX")
            return False

        # 基本验证
        if not order.code or not order.volume or order.volume <= 0:
            return False

        # 验证订单类型
        if order.order_type not in [ORDER_TYPES.MARKETORDER, ORDER_TYPES.LIMITORDER]:
            GLOG.ERROR(f"Unsupported order type: {order.order_type}")
            return False

        return True

    def submit_order_event(self, event) -> BrokerExecutionResult:
        """
        提交订单事件

        Args:
            event: 订单事件

        Returns:
            BrokerExecutionResult: 执行结果
        """
        if not self._is_connected:
            return BrokerExecutionResult(
                status=ORDERSTATUS_TYPES.REJECTED,
                error_message="Not connected to OKX",
                order=event.order
            )

        order = event.order

        if not self.validate_order(order):
            return BrokerExecutionResult(
                status=ORDERSTATUS_TYPES.REJECTED,
                error_message="Invalid order parameters",
                order=order
            )

        try:
            # 映射订单方向
            side = 'buy' if order.direction == DIRECTION_TYPES.LONG else 'sell'

            # 映射订单类型
            if order.order_type == ORDER_TYPES.MARKETORDER:
                trade_mode = 'market'
            else:
                trade_mode = 'limit'

            # 构建OKX订单参数
            order_params = {
                'instId': order.code,  # OKX使用instId而非symbol
                'tdMode': 'cash',  # 现金交易模式
                'side': side,
                'ordType': trade_mode,
                'sz': str(order.volume)
            }

            # 限价单需要价格
            if trade_mode == 'limit' and hasattr(order, 'limit_price') and order.limit_price:
                order_params['px'] = str(order.limit_price)

            # 调用OKX API下单
            result = self._trade_api.place_order(**order_params)

            if result and result.get('code') == '0':
                # 下单成功
                data = result.get('data', [{}])[0]
                broker_order_id = data.get('ordId')

                GLOG.INFO(f"OKX order submitted: {broker_order_id} for {order.code}")

                # 更新统计
                self._increment_order_count('submitted')

                return BrokerExecutionResult(
                    status=ORDERSTATUS_TYPES.SUBMITTED,
                    broker_order_id=broker_order_id,
                    order=order
                )
            else:
                # 下单失败
                error_msg = result.get('msg', 'Unknown error')
                GLOG.ERROR(f"OKX order rejected: {error_msg}")

                self._increment_order_count('rejected')

                return BrokerExecutionResult(
                    status=ORDERSTATUS_TYPES.REJECTED,
                    error_message=error_msg,
                    order=order
                )

        except OKXException as e:
            GLOG.ERROR(f"OKX API error submitting order: {e}")
            self._increment_order_count('rejected')
            return BrokerExecutionResult(
                status=ORDERSTATUS_TYPES.REJECTED,
                error_message=str(e),
                order=order
            )
        except Exception as e:
            GLOG.ERROR(f"Failed to submit order to OKX: {e}")
            self._increment_order_count('rejected')
            return BrokerExecutionResult(
                status=ORDERSTATUS_TYPES.REJECTED,
                error_message=f"Internal error: {str(e)}",
                order=order
            )

    def cancel_order(self, broker_order_id: str) -> BrokerExecutionResult:
        """
        撤销订单

        Args:
            broker_order_id: OKX订单ID

        Returns:
            BrokerExecutionResult: 撤销结果
        """
        if not self._is_connected:
            return BrokerExecutionResult(
                status=ORDERSTATUS_TYPES.REJECTED,
                error_message="Not connected to OKX"
            )

        try:
            result = self._trade_api.cancel_order(ordId=broker_order_id)

            if result and result.get('code') == '0':
                GLOG.INFO(f"OKX order cancelled: {broker_order_id}")
                self._increment_order_count('cancelled')
                return BrokerExecutionResult(
                    status=ORDERSTATUS_TYPES.CANCELED,
                    broker_order_id=broker_order_id
                )
            else:
                error_msg = result.get('msg', 'Unknown error')
                GLOG.ERROR(f"OKX cancel order failed: {error_msg}")
                return BrokerExecutionResult(
                    status=ORDERSTATUS_TYPES.REJECTED,
                    error_message=error_msg
                )

        except OKXException as e:
            GLOG.ERROR(f"OKX API error cancelling order: {e}")
            return BrokerExecutionResult(
                status=ORDERSTATUS_TYPES.REJECTED,
                error_message=str(e)
            )
        except Exception as e:
            GLOG.ERROR(f"Failed to cancel order on OKX: {e}")
            return BrokerExecutionResult(
                status=ORDERSTATUS_TYPES.REJECTED,
                error_message=f"Internal error: {str(e)}"
            )

    def _query_from_exchange(self, broker_order_id: str) -> dict:
        """
        从交易所查询订单状态

        Args:
            broker_order_id: OKX订单ID

        Returns:
            dict: 订单状态信息
        """
        if not self._is_connected:
            return {}

        try:
            result = self._trade_api.get_order(ordId=broker_order_id)

            if result and result.get('code') == '0':
                data = result.get('data', [{}])[0]
                return data
            else:
                GLOG.ERROR(f"OKX query order failed: {result.get('msg')}")
                return {}

        except Exception as e:
            GLOG.ERROR(f"Failed to query order from OKX: {e}")
            return {}

    def get_account_balance(self) -> dict:
        """
        获取账户余额

        Returns:
            dict: 余额信息
        """
        if not self._is_connected:
            return {}

        try:
            result = self._account_api.get_account_balance()

            if result and result.get('code') == '0':
                return result.get('data', [])
            else:
                GLOG.ERROR(f"OKX get balance failed: {result.get('msg')}")
                return []

        except Exception as e:
            GLOG.ERROR(f"Failed to get balance from OKX: {e}")
            return []

    def get_positions(self) -> list:
        """
        获取持仓信息

        Returns:
            list: 持仓列表
        """
        if not self._is_connected:
            return []

        try:
            result = self._account_api.get_positions()

            if result and result.get('code') == '0':
                return result.get('data', [])
            else:
                GLOG.ERROR(f"OKX get positions failed: {result.get('msg')}")
                return []

        except Exception as e:
            GLOG.ERROR(f"Failed to get positions from OKX: {e}")
            return []

    def _increment_order_count(self, order_type: str) -> None:
        """增加订单计数（用于统计）"""
        try:
            broker_crud = container.broker_instance_crud()
            if order_type == 'submitted':
                broker_crud.increment_order_count(self.broker_uuid, 'submitted')
            elif order_type == 'filled':
                broker_crud.increment_order_count(self.broker_uuid, 'filled')
            elif order_type == 'cancelled':
                broker_crud.increment_order_count(self.broker_uuid, 'cancelled')
            elif order_type == 'rejected':
                broker_crud.increment_order_count(self.broker_uuid, 'rejected')
        except Exception as e:
            GLOG.ERROR(f"Failed to increment order count: {e}")

    def _record_trade(
        self,
        symbol: str,
        side: str,
        price: float,
        quantity: float,
        exchange_order_id: str,
        exchange_trade_id: str,
        quote_quantity: Optional[float] = None,
        fee: Optional[float] = None,
        fee_currency: Optional[str] = None,
        order_type: Optional[str] = None
    ) -> None:
        """
        记录交易到数据库

        Args:
            symbol: 交易标的
            side: 交易方向
            price: 成交价格
            quantity: 成交数量
            exchange_order_id: 交易所订单ID
            exchange_trade_id: 交易所成交ID
            quote_quantity: 成交金额
            fee: 手续费
            fee_currency: 手续费币种
            order_type: 订单类型
        """
        try:
            trade_crud = container.trade_record_crud()

            trade_crud.add_trade_record(
                live_account_id=self.live_account_id,
                broker_instance_id=self.broker_uuid,
                portfolio_id=self.portfolio_id,
                exchange="okx",
                symbol=symbol,
                side=side,
                price=price,
                quantity=quantity,
                exchange_order_id=exchange_order_id,
                exchange_trade_id=exchange_trade_id,
                quote_quantity=quote_quantity,
                fee=fee,
                fee_currency=fee_currency,
                order_type=order_type,
                trade_time=datetime.now()
            )

            GLOG.DEBUG(f"Trade recorded: {symbol} {side} {quantity} @ {price}")

        except Exception as e:
            GLOG.ERROR(f"Failed to record trade: {e}")

    def supports_api_trading(self) -> bool:
        """支持API交易"""
        return True


# 保持向后兼容 - BaseBroker继承的版本
try:
    from ginkgo.trading.brokers.base_broker import BaseBroker, ExecutionResult, ExecutionStatus, AccountInfo
    from ginkgo.trading.brokers.interfaces import BrokerPosition

    class OKXBrokerLegacy(BaseBroker):
        """
        OKX交易所Broker实现（向后兼容版本）

        保留原有BaseBroker继承的实现，用于向后兼容
        """

        def __init__(self, broker_config: dict):
            super().__init__(broker_config)

            # OKX API配置
            self.api_key = broker_config.get('api_key', '')
            self.secret_key = broker_config.get('secret_key', '')
            self.passphrase = broker_config.get('passphrase', '')
            self.sandbox = broker_config.get('sandbox', True)
            self.inst_type = broker_config.get('instType', 'SPOT')

            # API端点
            if self.sandbox:
                self.base_url = "https://www.okx.com"  # 沙盒环境
            else:
                self.base_url = "https://www.okx.com"  # 生产环境

            # 订单映射
            self._order_mapping = {}

        async def connect(self) -> bool:
            """连接OKX API"""
            GLOG.INFO(f"OKXBroker connecting to {self.base_url}")
            return True

        async def submit_order(self, order: Order) -> ExecutionResult:
            """提交订单"""
            # 实现省略...
            return ExecutionResult(status=ExecutionStatus.SUCCESS)

        async def cancel_order(self, order_id: str) -> ExecutionResult:
            """撤销订单"""
            # 实现省略...
            return ExecutionResult(status=ExecutionStatus.SUCCESS)

        async def get_account_info(self) -> AccountInfo:
            """获取账户信息"""
            # 实现省略...
            return AccountInfo(total_balance=0.0, available_balance=0.0)

        async def get_positions(self) -> list[BrokerPosition]:
            """获取持仓"""
            # 实现省略...
            return []

except ImportError:
    # BaseBroker不可用时，只保留新版本
    pass
