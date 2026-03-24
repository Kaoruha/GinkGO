# Upstream: BrokerManager (生命周期管理)、IBroker (Broker接口)
# Downstream: python-okx SDK (OKX API通信)、MBrokerInstance (状态跟踪)
# Role: OKXBroker OKX交易所Broker实现处理订单提交/撤单/查询与OKX API通信


import time
import asyncio
from functools import wraps
from typing import Optional, Callable, Any, List
from datetime import datetime
from enum import Enum

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


class NetworkErrorType(Enum):
    """网络错误类型"""
    SSL_TIMEOUT = "SSL handshake timeout"
    SSL_EOF = "SSL unexpected EOF"
    CONNECTION_REFUSED = "Connection refused"
    CONNECTION_RESET = "Connection reset by peer"
    TIMEOUT = "Request timeout"
    UNKNOWN = "Unknown network error"


class RetryConfig:
    """重试配置"""
    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter


class OKXBroker(IBroker):
    """
    OKX交易所Broker实现

    通过python-okx SDK与OKX API通信：
    - 支持限价单和市价单
    - 支持订单撤单和查询
    - 自动处理API重试和限流
    - 记录API调用日志
    """

    # 可重试的错误关键字
    RETRYABLE_ERRORS = [
        "SSL",
        "timeout",
        "Connection refused",
        "Connection reset",
        "UNEXPECTED_EOF",
        "handshake",
        "EOF occurred",
        "110",  # Connection timed out
        "111",  # Connection refused
        "104",  # Connection reset by peer
    ]

    # 默认重试配置
    DEFAULT_RETRY_CONFIG = RetryConfig(
        max_retries=3,
        base_delay=1.0,
        max_delay=30.0,
        exponential_base=2.0,
        jitter=True
    )

    @staticmethod
    def _classify_network_error(error: Exception) -> Optional[NetworkErrorType]:
        """
        分类网络错误类型

        Args:
            error: 异常对象

        Returns:
            NetworkErrorType: 错误类型，无法分类返回None
        """
        error_msg = str(error).lower()

        if "ssl" in error_msg and "handshake" in error_msg:
            return NetworkErrorType.SSL_TIMEOUT
        elif "ssl" in error_msg and "eof" in error_msg:
            return NetworkErrorType.SSL_EOF
        elif "connection refused" in error_msg:
            return NetworkErrorType.CONNECTION_REFUSED
        elif "connection reset" in error_msg:
            return NetworkErrorType.CONNECTION_RESET
        elif "timeout" in error_msg:
            return NetworkErrorType.TIMEOUT
        else:
            return NetworkErrorType.UNKNOWN

    @staticmethod
    def _is_retryable_error(error: Exception) -> bool:
        """
        判断错误是否可重试

        Args:
            error: 异常对象

        Returns:
            bool: 是否可重试
        """
        error_msg = str(error)

        # 检查是否包含可重试错误的关键字
        for keyword in OKXBroker.RETRYABLE_ERRORS:
            if keyword.lower() in error_msg.lower():
                return True

        # 检查特定错误类型
        if isinstance(error, (ConnectionError, TimeoutError)):
            return True

        return False

    @staticmethod
    def _calculate_delay(attempt: int, config: RetryConfig) -> float:
        """
        计算重试延迟时间（指数退避 + 抖动）

        Args:
            attempt: 当前尝试次数（从0开始）
            config: 重试配置

        Returns:
            float: 延迟时间（秒）
        """
        # 指数退避
        delay = min(
            config.base_delay * (config.exponential_base ** attempt),
            config.max_delay
        )

        # 添加抖动（±20%随机波动）
        if config.jitter:
            import random
            delay = delay * (0.8 + random.random() * 0.4)

        return delay

    def __init__(
        self,
        broker_uuid: str,
        portfolio_id: str,
        live_account_id: str,
        api_key: str,
        api_secret: str,
        passphrase: str,
        environment: str = "testnet",
        retry_config: Optional[RetryConfig] = None
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
            retry_config: 重试配置（可选）
        """
        if not OKX_AVAILABLE:
            raise ImportError("python-okx is not installed. Run: pip install python-okx")

        self.broker_uuid = broker_uuid
        self.portfolio_id = portfolio_id
        self.live_account_id = live_account_id
        self._environment = environment
        self._retry_config = retry_config or self.DEFAULT_RETRY_CONFIG

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

        # 错误统计
        self._error_counts = {
            "ssl_timeout": 0,
            "ssl_eof": 0,
            "connection_refused": 0,
            "connection_reset": 0,
            "timeout": 0,
            "other": 0
        }

        # 最后错误时间（用于避免频繁重试）
        self._last_error_time = None
        self._error_cooldown = 5  # 错误冷却期（秒）

        GLOG.INFO(f"OKXBroker initialized: {broker_uuid} ({environment})")

    def _execute_with_retry(
        self,
        func: Callable,
        *args,
        operation_name: str = "API call",
        **kwargs
    ) -> Any:
        """
        执行API调用并自动重试

        Args:
            func: 要执行的函数
            *args: 函数参数
            operation_name: 操作名称（用于日志）
            **kwargs: 函数关键字参数

        Returns:
            Any: 函数执行结果

        Raises:
            Exception: 重试耗尽后抛出最后一次异常
        """
        last_exception = None

        for attempt in range(self._retry_config.max_retries):
            try:
                result = func(*args, **kwargs)

                # 重试成功后记录日志
                if attempt > 0:
                    error_type = self._classify_network_error(last_exception)
                    GLOG.INFO(
                        f"[{self.broker_uuid[:8]}] {operation_name} "
                        f"succeeded after {attempt} retries "
                        f"(error was: {error_type.value if error_type else 'Unknown'})"
                    )

                return result

            except Exception as e:
                last_exception = e

                # 检查是否为可重试错误
                if not self._is_retryable_error(e):
                    GLOG.ERROR(
                        f"[{self.broker_uuid[:8]}] {operation_name} failed "
                        f"with non-retryable error: {e}"
                    )
                    raise

                # 还有重试机会
                if attempt < self._retry_config.max_retries - 1:
                    # 计算延迟
                    delay = self._calculate_delay(attempt, self._retry_config)

                    # 分类错误
                    error_type = self._classify_network_error(e)
                    if error_type:
                        self._increment_error_count(error_type)

                    GLOG.WARNING(
                        f"[{self.broker_uuid[:8]}] {operation_name} failed "
                        f"(attempt {attempt + 1}/{self._retry_config.max_retries}): {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )

                    time.sleep(delay)
                else:
                    # 最后一次尝试失败
                    error_type = self._classify_network_error(e)
                    GLOG.ERROR(
                        f"[{self.broker_uuid[:8]}] {operation_name} failed "
                        f"after {self._retry_config.max_retries} attempts. "
                        f"Final error: {e} ({error_type.value if error_type else 'Unknown'})"
                    )

        raise last_exception

    def _increment_error_count(self, error_type: NetworkErrorType) -> None:
        """增加错误计数"""
        error_key = {
            NetworkErrorType.SSL_TIMEOUT: "ssl_timeout",
            NetworkErrorType.SSL_EOF: "ssl_eof",
            NetworkErrorType.CONNECTION_REFUSED: "connection_refused",
            NetworkErrorType.CONNECTION_RESET: "connection_reset",
            NetworkErrorType.TIMEOUT: "timeout",
            NetworkErrorType.UNKNOWN: "other",
        }.get(error_type, "other")

        self._error_counts[error_key] += 1

    def get_error_stats(self) -> dict:
        """获取错误统计"""
        return self._error_counts.copy()

    def connect(self) -> bool:
        """
        连接OKX API（带重试机制）

        Returns:
            bool: 连接是否成功
        """
        def _do_connect():
            # 确定API域名
            if self._environment == EnvironmentType.TESTNET:
                domain = 'https://www.okx.com'  # OKX测试网
            else:
                domain = 'https://www.okx.com'  # OKX实盘

            # 初始化API客户端
            flag = '0'  # '0'=实盘, '1'=模拟盘

            self._account_api = Account.AccountAPI(
                api_key=self._api_key,
                api_secret_key=self._api_secret,
                passphrase=self._passphrase,
                domain=domain,
                debug=False,
                flag=flag,
                timeout=10  # 设置超时时间
            )

            self._trade_api = Trade.TradeAPI(
                api_key=self._api_key,
                api_secret_key=self._api_secret,
                passphrase=self._passphrase,
                domain=domain,
                debug=False,
                flag=flag,
                timeout=10  # 设置超时时间
            )

            # 测试连接
            result = self._account_api.get_account_balance()
            if result and result.get('code') == '0':
                self._is_connected = True
                return True
            else:
                raise Exception(f"OKX API connection test failed: {result}")

        try:
            self._execute_with_retry(_do_connect, operation_name="Connect to OKX API")
            GLOG.INFO(f"OKX API connected successfully: {self.broker_uuid}")
            return True
        except Exception as e:
            GLOG.ERROR(f"Failed to connect OKX API after retries: {e}")
            self._is_connected = False
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
        获取账户余额（带重试机制）

        Returns:
            dict: 余额信息
        """
        if not self._is_connected:
            GLOG.ERROR("Cannot get balance: not connected to OKX")
            return {}

        def _do_get_balance():
            result = self._account_api.get_account_balance()

            if result and result.get('code') == '0':
                return result.get('data', [])
            else:
                error_msg = result.get('msg', 'Unknown error')
                raise Exception(f"OKX get balance failed: {error_msg}")

        try:
            return self._execute_with_retry(_do_get_balance, operation_name="Get account balance")
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
            GLOG.ERROR("Cannot get positions: not connected to OKX")
            return []

        def _do_get_positions():
            result = self._account_api.get_positions()

            if result and result.get('code') == '0':
                return result.get('data', [])
            else:
                error_msg = result.get('msg', 'Unknown error')
                raise Exception(f"OKX get positions failed: {error_msg}")

        try:
            return self._execute_with_retry(_do_get_positions, operation_name="Get positions")
        except Exception as e:
            GLOG.ERROR(f"Failed to get positions from OKX: {e}")
            return []

    def get_open_orders(self) -> list:
        """
        获取挂单信息

        Returns:
            list: 挂单列表，格式符合 IBroker 接口定义
            [
                {
                    "order_id": str,           # 订单ID (OKX ordId)
                    "symbol": str,             # 交易标的 (OKX instId)
                    "side": str,               # buy/sell
                    "order_type": str,         # 订单类型 (market/limit)
                    "size": str,               # 数量 (OKX sz)
                    "price": str,              # 价格 (OKX px，限价单)
                    "filled_size": str,        # 已成交数量 (OKX fillSz)
                    "status": str,             # 订单状态
                    "created_at": str          # 创建时间 (OKX cTime)
                }
            ]
        """
        if not self._is_connected:
            GLOG.ERROR("Cannot get open orders: not connected to OKX")
            return []

        def _do_get_orders():
            # 获取现货订单列表
            result = self._trade_api.get_order_list(
                instType='SPOT'  # 现货交易
            )

            if result and result.get('code') == '0':
                orders_data = result.get('data', [])

                # 转换为标准格式
                open_orders = []
                for order in orders_data:
                    # 只返回未完成订单
                    state = order.get('state', '')
                    if state in ['live', 'partially_filled']:
                        open_orders.append({
                            'order_id': order.get('ordId', ''),
                            'symbol': order.get('instId', ''),
                            'side': order.get('side', ''),  # buy/sell
                            'order_type': order.get('ordType', ''),  # market/limit
                            'size': order.get('sz', ''),
                            'price': order.get('px', '0'),  # 限价单有价格，市价单为 0
                            'filled_size': order.get('fillSz', '0'),
                            'status': state,
                            'created_at': order.get('cTime', '')
                        })

                return open_orders
            else:
                error_msg = result.get('msg', 'Unknown error')
                raise Exception(f"OKX get open orders failed: {error_msg}")

        try:
            return self._execute_with_retry(_do_get_orders, operation_name="Get open orders")
        except Exception as e:
            GLOG.ERROR(f"Failed to get open orders from OKX: {e}")
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

    def get_ticker(self, inst_id: str) -> dict:
        """
        获取交易对行情（带重试机制）

        Args:
            inst_id: 交易对ID (如 BTC-USDT)

        Returns:
            dict: 行情数据
        """
        if not self._is_connected:
            GLOG.ERROR("Cannot get ticker: not connected to OKX")
            return {}

        def _do_get_ticker():
            try:
                from okx.PublicData import PublicAPI
                public_api = PublicAPI(
                    domain=self._account_api.domain if self._account_api else 'https://www.okx.com',
                    debug=False,
                    timeout=10
                )
                result = public_api.get_ticker(instId=inst_id)

                if result and result.get('code') == '0':
                    return result.get('data', [{}])[0]
                else:
                    error_msg = result.get('msg', 'Unknown error')
                    raise Exception(f"OKX get ticker failed: {error_msg}")
            except Exception as e:
                raise Exception(f"Failed to get ticker: {e}")

        try:
            return self._execute_with_retry(
                lambda: _do_get_ticker(),
                operation_name=f"Get ticker for {inst_id}"
            )
        except Exception as e:
            GLOG.ERROR(f"Failed to get ticker from OKX: {e}")
            return {}

    def get_top_volume_pairs(self, limit: int = 20) -> list:
        """
        获取成交量最大的交易对（带重试机制）

        Args:
            limit: 返回数量

        Returns:
            list: 交易对列表
        """
        if not self._is_connected:
            GLOG.ERROR("Cannot get top volume pairs: not connected to OKX")
            return []

        def _do_get_top_volume():
            try:
                from okx.PublicData import PublicAPI
                public_api = PublicAPI(
                    domain=self._account_api.domain if self._account_api else 'https://www.okx.com',
                    debug=False,
                    timeout=10
                )
                result = public_api.get_tickers(instType='SPOT')

                if result and result.get('code') == '0':
                    tickers = result.get('data', [])
                    # 按24小时成交量排序
                    sorted_tickers = sorted(
                        tickers,
                        key=lambda x: float(x.get('volCcy24h', 0)),
                        reverse=True
                    )
                    return sorted_tickers[:limit]
                else:
                    error_msg = result.get('msg', 'Unknown error')
                    raise Exception(f"OKX get tickers failed: {error_msg}")
            except Exception as e:
                raise Exception(f"Failed to get top volume pairs: {e}")

        try:
            return self._execute_with_retry(
                lambda: _do_get_top_volume(),
                operation_name="Get top volume pairs"
            )
        except Exception as e:
            GLOG.ERROR(f"Failed to get top volume pairs from OKX: {e}")
            return []

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

    # ==================== WebSocket 支持 ====================

    def enable_websocket(self) -> bool:
        """
        启用WebSocket连接

        使用WebSocket接收订单状态推送，替代轮询方式

        Returns:
            bool: 启用是否成功
        """
        try:
            from ginkgo.livecore.websocket_manager import get_websocket_manager, WebSocketType

            ws_manager = get_websocket_manager()

            # 准备凭证
            credentials = {
                "api_key": self._api_key,
                "api_secret": self._api_secret,
                "passphrase": self._passphrase
            }

            # 获取私有WebSocket连接（每个Broker独立连接）
            self._ws_connection = ws_manager.get_private_ws(
                exchange="okx",
                environment=self._environment,
                credentials=credentials,
                connection_id=f"okx_private_{self.broker_uuid}"
            )

            # 连接WebSocket
            if ws_manager.connect(self._ws_connection):
                self._ws_enabled = True
                GLOG.INFO(f"WebSocket enabled for OKXBroker: {self.broker_uuid}")

                # 订阅订单频道
                self._subscribe_order_channels()

                return True
            else:
                GLOG.ERROR(f"Failed to connect WebSocket for broker: {self.broker_uuid}")
                return False

        except ImportError as e:
            GLOG.ERROR(f"WebSocket dependencies not available: {e}")
            return False
        except Exception as e:
            GLOG.ERROR(f"Failed to enable WebSocket: {e}")
            return False

    def _subscribe_order_channels(self) -> None:
        """订阅订单相关频道"""
        try:
            from ginkgo.livecore.websocket_manager import get_websocket_manager
            ws_manager = get_websocket_manager()

            # 订阅普通订单频道
            ws_manager.subscribe(
                self._ws_connection,
                channel="orders",
                inst_id="SPOT",  # 现货订单
                callback=self._on_order_message
            )

            # 订阅策略订单频道
            ws_manager.subscribe(
                self._ws_connection,
                channel="orders-algo",
                inst_id="SPOT",
                callback=self._on_order_algo_message
            )

            GLOG.INFO(f"Subscribed to order channels for broker: {self.broker_uuid}")

        except Exception as e:
            GLOG.ERROR(f"Failed to subscribe order channels: {e}")

    def _on_order_message(self, message: dict) -> None:
        """
        处理订单消息

        Args:
            message: WebSocket订单消息
        """
        try:
            from ginkgo.livecore.websocket_event_adapter import adapt_order

            order_data = adapt_order(message)
            if not order_data:
                return

            exchange_order_id = order_data.get("exchange_order_id")
            status = order_data.get("status")

            GLOG.DEBUG(f"Order update via WebSocket: {exchange_order_id} -> {status}")

            # TODO: 更新本地订单状态
            # 需要通过broker_order_id查找并更新MOrder
            # 如果有设置_result_callback，可以调用回调通知

        except Exception as e:
            GLOG.ERROR(f"Error processing order message: {e}")

    def _on_order_algo_message(self, message: dict) -> None:
        """
        处理策略订单消息

        Args:
            message: WebSocket策略订单消息
        """
        # 策略订单处理逻辑与普通订单类似
        self._on_order_message(message)

    def subscribe_account_ws(self, callback=None) -> bool:
        """
        订阅账户余额推送 (WebSocket)

        Args:
            callback: 回调函数 (可选)

        Returns:
            bool: 订阅是否成功
        """
        if not hasattr(self, '_ws_connection') or not self._ws_connection:
            if not self.enable_websocket():
                return False

        try:
            from ginkgo.livecore.websocket_manager import get_websocket_manager
            ws_manager = get_websocket_manager()

            def default_callback(message):
                from ginkgo.livecore.websocket_event_adapter import adapt_account
                data = adapt_account(message)
                if data:
                    if not hasattr(self, '_account_cache'):
                        self._account_cache = {}
                    self._account_cache['balance'] = data
                    GLOG.DEBUG(f"Account balance updated via WebSocket: {data['total_equity']}")

            cb = callback or default_callback

            return ws_manager.subscribe(
                self._ws_connection,
                channel="account",
                inst_id="",  # account频道不需要instId
                callback=cb
            )

        except Exception as e:
            GLOG.ERROR(f"Failed to subscribe account via WebSocket: {e}")
            return False

    def subscribe_positions_ws(self, callback=None) -> bool:
        """
        订阅持仓推送 (WebSocket)

        Args:
            callback: 回调函数 (可选)

        Returns:
            bool: 订阅是否成功
        """
        if not hasattr(self, '_ws_connection') or not self._ws_connection:
            if not self.enable_websocket():
                return False

        try:
            from ginkgo.livecore.websocket_manager import get_websocket_manager
            ws_manager = get_websocket_manager()

            def default_callback(message):
                from ginkgo.livecore.websocket_event_adapter import adapt_position
                data = adapt_position(message)
                if data:
                    if not hasattr(self, '_positions_cache'):
                        self._positions_cache = {}
                    symbol = data.get('symbol')
                    if symbol:
                        self._positions_cache[symbol] = data
                    GLOG.DEBUG(f"Position updated via WebSocket: {symbol}")

            cb = callback or default_callback

            return ws_manager.subscribe(
                self._ws_connection,
                channel="positions",
                inst_id="SPOT",
                callback=cb
            )

        except Exception as e:
            GLOG.ERROR(f"Failed to subscribe positions via WebSocket: {e}")
            return False

    def unsubscribe_account_ws(self) -> bool:
        """取消订阅账户余额"""
        if hasattr(self, '_ws_connection') and self._ws_connection:
            from ginkgo.livecore.websocket_manager import get_websocket_manager
            ws_manager = get_websocket_manager()
            return ws_manager.unsubscribe(self._ws_connection, "account", "")
        return False

    def unsubscribe_positions_ws(self) -> bool:
        """取消订阅持仓"""
        if hasattr(self, '_ws_connection') and self._ws_connection:
            from ginkgo.livecore.websocket_manager import get_websocket_manager
            ws_manager = get_websocket_manager()
            return ws_manager.unsubscribe(self._ws_connection, "positions", "SPOT")
        return False

    def get_cached_account_balance(self) -> Optional[dict]:
        """
        获取缓存的账户余额（来自WebSocket推送）

        Returns:
            dict: 余额数据或None
        """
        return getattr(self, '_account_cache', {}).get('balance')

    def get_cached_positions(self) -> dict:
        """
        获取缓存的持仓数据（来自WebSocket推送）

        Returns:
            dict: 持仓数据 {symbol: position_data}
        """
        return getattr(self, '_positions_cache', {})


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
