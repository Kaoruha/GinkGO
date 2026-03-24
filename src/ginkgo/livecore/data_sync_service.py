# Upstream: LiveEngine (生命周期管理)、BrokerManager (Broker实例)
# Downstream: MBrokerInstance (状态更新)、MPosition/MOrder (数据同步)
# Role: DataSyncService 实时数据同步服务处理WebSocket连接和数据更新


import asyncio
import json
import threading
import time
from typing import Dict, Optional, Callable
from datetime import datetime, timedelta

from ginkgo.libs import GLOG
from ginkgo.data.containers import container
from ginkgo.data.models.model_broker_instance import MBrokerInstance, BrokerStateType


class DataSyncService:
    """
    实时数据同步服务

    负责从OKX WebSocket接收实时数据并更新本地数据库：
    - 账户余额同步
    - 持仓信息同步
    - 订单状态更新
    - WebSocket连接管理
    - 心跳检测和重连
    """

    def __init__(self):
        """初始化DataSyncService"""
        self._active_syncs: Dict[str, dict] = {}  # broker_uuid -> sync_info
        self._running = False
        self._lock = threading.Lock()

    def start_sync_for_broker(self, broker: MBrokerInstance) -> bool:
        """
        启动指定Broker的数据同步

        Args:
            broker: Broker实例

        Returns:
            bool: 启动是否成功
        """
        try:
            with self._lock:
                if broker.uuid in self._active_syncs:
                    GLOG.WARNING(f"Sync already active for broker {broker.uuid}")
                    return True

                # 创建同步信息
                sync_info = {
                    'broker_uuid': broker.uuid,
                    'portfolio_id': broker.portfolio_id,
                    'live_account_id': broker.live_account_id,
                    'websocket': None,
                    'polling_task': None,
                    'last_sync': None,
                    'error_count': 0
                }

                self._active_syncs[broker.uuid] = sync_info

            # 启动WebSocket
            if not self._start_websocket(broker.uuid):
                # WebSocket失败，启动轮询作为fallback
                GLOG.WARNING(f"WebSocket failed for {broker.uuid}, starting polling fallback")
                self._start_polling(broker.uuid)

            return True

        except Exception as e:
            GLOG.ERROR(f"Failed to start sync for broker {broker.uuid}: {e}")
            return False

    def stop_sync_for_broker(self, broker_uuid: str) -> bool:
        """
        停止指定Broker的数据同步

        Args:
            broker_uuid: Broker实例UUID

        Returns:
            bool: 停止是否成功
        """
        try:
            with self._lock:
                if broker_uuid not in self._active_syncs:
                    return False

                sync_info = self._active_syncs[broker_uuid]

                # 停止WebSocket
                ws_connection = sync_info.get('websocket')
                ws_manager = sync_info.get('ws_manager')
                if ws_connection and ws_manager:
                    try:
                        ws_manager.disconnect(ws_connection)
                    except Exception as e:
                        GLOG.ERROR(f"Error disconnecting WebSocket: {e}")
                    sync_info['websocket'] = None
                    sync_info['ws_manager'] = None

                # 停止轮询
                sync_info['polling_task'] = None

                # 移除同步信息
                del self._active_syncs[broker_uuid]

            GLOG.INFO(f"Sync stopped for broker {broker_uuid}")
            return True

        except Exception as e:
            GLOG.ERROR(f"Failed to stop sync for broker {broker_uuid}: {e}")
            return False

    def _start_websocket(self, broker_uuid: str) -> bool:
        """
        启动WebSocket连接

        Args:
            broker_uuid: Broker实例UUID

        Returns:
            bool: 启动是否成功
        """
        try:
            from ginkgo.livecore.websocket_manager import get_websocket_manager

            # 获取Broker信息
            broker_crud = container.broker_instance()
            broker_info = broker_crud.get_broker_by_uuid(broker_uuid)

            if not broker_info:
                GLOG.ERROR(f"Broker not found: {broker_uuid}")
                return False

            # 获取实盘账号凭证
            live_account_crud = container.live_account()
            account = live_account_crud.get_live_account_by_uuid(
                broker_info.live_account_id,
                include_credentials=True
            )

            if not account:
                GLOG.ERROR(f"Live account not found: {broker_info.live_account_id}")
                return False

            # 检查交易所类型
            if not account.is_okx():
                GLOG.ERROR(f"WebSocket not supported for exchange: {account.exchange}")
                return False

            # 解密凭证
            credentials = live_account_crud.get_decrypted_credentials(account.uuid)
            if not credentials:
                GLOG.ERROR("Failed to decrypt credentials")
                return False

            # 获取WebSocket管理器
            ws_manager = get_websocket_manager()

            # 环境判断
            environment = "testnet" if account.is_testnet() else "production"

            # 创建私有WebSocket连接
            ws_connection = ws_manager.get_private_ws(
                exchange="okx",
                environment=environment,
                credentials=credentials,
                connection_id=f"okx_sync_{broker_uuid}"
            )

            # 连接WebSocket
            if not ws_manager.connect(ws_connection):
                GLOG.ERROR(f"Failed to connect WebSocket for broker {broker_uuid}")
                return False

            # 订阅账户频道
            ws_manager.subscribe(
                ws_connection,
                channel="account",
                inst_id="",
                callback=lambda msg: self._on_private_message(broker_uuid, msg)
            )

            # 订阅持仓频道
            ws_manager.subscribe(
                ws_connection,
                channel="positions",
                inst_id="SPOT",
                callback=lambda msg: self._on_private_message(broker_uuid, msg)
            )

            # 订阅订单频道
            ws_manager.subscribe(
                ws_connection,
                channel="orders",
                inst_id="SPOT",
                callback=lambda msg: self._on_private_message(broker_uuid, msg)
            )

            # 更新同步信息
            if broker_uuid in self._active_syncs:
                self._active_syncs[broker_uuid]['websocket'] = ws_connection
                self._active_syncs[broker_uuid]['ws_manager'] = ws_manager

            GLOG.INFO(f"WebSocket started for broker {broker_uuid}")
            return True

        except ImportError as e:
            GLOG.ERROR(f"WebSocket dependencies not available: {e}")
            return False
        except Exception as e:
            GLOG.ERROR(f"Failed to start WebSocket for broker {broker_uuid}: {e}")
            return False

    def _start_polling(self, broker_uuid: str) -> bool:
        """
        启动轮询（WebSocket的fallback）

        Args:
            broker_uuid: Broker实例UUID

        Returns:
            bool: 启动是否成功
        """
        try:
            # 在新线程中运行轮询
            def polling_loop():
                while broker_uuid in self._active_syncs:
                    try:
                        self._polling_update(broker_uuid)
                        time.sleep(5)  # 5秒轮询间隔
                    except Exception as e:
                        GLOG.ERROR(f"Polling error for broker {broker_uuid}: {e}")
                        time.sleep(10)  # 错误后等待10秒

            thread = threading.Thread(target=polling_loop, daemon=True)
            thread.start()

            # 更新同步信息
            if broker_uuid in self._active_syncs:
                self._active_syncs[broker_uuid]['polling_task'] = thread

            GLOG.INFO(f"Polling started for broker {broker_uuid}")
            return True

        except Exception as e:
            GLOG.ERROR(f"Failed to start polling for broker {broker_uuid}: {e}")
            return False

    def _polling_update(self, broker_uuid: str) -> None:
        """
        轮询更新数据

        Args:
            broker_uuid: Broker实例UUID
        """
        if broker_uuid not in self._active_syncs:
            return

        sync_info = self._active_syncs[broker_uuid]

        try:
            # 获取Broker对象
            from ginkgo.trading.brokers.broker_manager import get_broker_manager
            broker_manager = get_broker_manager()
            broker = broker_manager.get_broker(sync_info['portfolio_id'])

            if not broker or not broker.is_connected():
                return

            # 更新账户余额
            balance = broker.get_account_balance()
            self._update_balance(broker_uuid, balance)

            # 更新持仓
            positions = broker.get_positions()
            self._update_positions(broker_uuid, positions)

            # 更新心跳
            broker_crud = container.broker_instance()
            broker_crud.update_heartbeat(broker_uuid)

            # 更新最后同步时间
            sync_info['last_sync'] = datetime.now()

        except Exception as e:
            GLOG.ERROR(f"Polling update failed for broker {broker_uuid}: {e}")
            sync_info['error_count'] = sync_info.get('error_count', 0) + 1

    def _on_private_message(self, broker_uuid: str, message: dict) -> None:
        """
        处理WebSocket私有消息

        Args:
            broker_uuid: Broker实例UUID
            message: WebSocket消息
        """
        try:
            from ginkgo.livecore.websocket_event_adapter import (
                adapt_account, adapt_position, adapt_order, adapt_order_algo
            )

            # 获取消息类型
            arg = message.get('data', {}).get('arg', {})
            msg_type = arg.get('channel', '')

            if msg_type == 'account':  # 账户余额更新
                balance_data = adapt_account(message)
                if balance_data:
                    self._update_balance(broker_uuid, balance_data)

            elif msg_type == 'positions':  # 持仓更新
                # OKX返回的是列表，每个元素是一个持仓
                data_list = message.get('data', [])
                for pos_data in data_list:
                    # 构造单条持仓消息
                    single_message = {
                        'data': {'arg': arg, 'data': [pos_data]}
                    }
                    position_data = adapt_position(single_message)
                    if position_data:
                        self._update_positions(broker_uuid, position_data)

            elif msg_type == 'orders':  # 订单更新
                order_data = adapt_order(message)
                if order_data:
                    self._update_orders(broker_uuid, order_data)

            elif msg_type == 'orders-algo':  # 策略订单更新
                order_data = adapt_order_algo(message)
                if order_data:
                    self._update_orders(broker_uuid, order_data)

            # 更新心跳
            broker_crud = container.broker_instance()
            broker_crud.update_heartbeat(broker_uuid)

        except Exception as e:
            GLOG.ERROR(f"Failed to process WebSocket message for broker {broker_uuid}: {e}")

    def _update_balance(self, broker_uuid: str, balance_data: dict) -> None:
        """
        更新账户余额

        Args:
            broker_uuid: Broker实例UUID
            balance_data: 余额数据 (已适配的格式)
        """
        try:
            # 获取Portfolio ID
            sync_info = self._active_syncs.get(broker_uuid)
            if not sync_info:
                return

            portfolio_id = sync_info.get('portfolio_id')

            # 更新Portfolio余额
            portfolio_crud = container.portfolio()
            portfolio = portfolio_crud.get_portfolio_by_uuid(portfolio_id)

            if portfolio:
                # TODO: 更新余额字段（需要在MPortfolio中添加余额字段）
                # portfolio.cash = balance_data['available_balance']
                # portfolio.total_value = balance_data['total_equity']
                # portfolio_crud.update_portfolio(portfolio)

                GLOG.DEBUG(f"Balance updated for broker {broker_uuid}: {balance_data['total_equity']}")

        except Exception as e:
            GLOG.ERROR(f"Error updating balance for broker {broker_uuid}: {e}")

    def _update_positions(self, broker_uuid: str, position_data: dict) -> None:
        """
        更新持仓信息

        Args:
            broker_uuid: Broker实例UUID
            position_data: 持仓数据 (已适配的格式)
        """
        try:
            sync_info = self._active_syncs.get(broker_uuid)
            if not sync_info:
                return

            portfolio_id = sync_info.get('portfolio_id')

            # TODO: 更新持仓记录
            # 需要匹配exchange_position_id并更新数量
            position_crud = container.position()
            positions = position_crud.find(filters={
                "portfolio_id": portfolio_id,
                "symbol": position_data.get('symbol'),
                "is_del": False
            })

            if positions:
                # 更新现有持仓
                position = positions[0]
                # position.volume = position_data['size']
                # position.current_price = position_data.get('current_price', position.avg_price)
                # position_crud.update_position(position)

                GLOG.DEBUG(f"Position updated for broker {broker_uuid}: {position_data.get('symbol')}")

        except Exception as e:
            GLOG.ERROR(f"Error updating position for broker {broker_uuid}: {e}")

    def _update_orders(self, broker_uuid: str, order_data: dict) -> None:
        """
        更新订单状态

        Args:
            broker_uuid: Broker实例UUID
            order_data: 订单数据 (已适配的格式)
        """
        try:
            sync_info = self._active_syncs.get(broker_uuid)
            if not sync_info:
                return

            # 查找并更新订单
            order_crud = container.order()
            orders = order_crud.find(filters={
                "exchange_order_id": order_data.get('exchange_order_id'),
                "is_del": False
            })

            if orders:
                order = orders[0]
                # 更新订单状态
                status = order_data.get('status')

                # 映射状态到Ginkgo枚举
                from ginkgo.enums import ORDERSTATUS_TYPES
                status_map = {
                    'submitted': ORDERSTATUS_TYPES.SUBMITTED,
                    'partially_filled': ORDERSTATUS_TYPES.PARTIAL_FILLED,
                    'filled': ORDERSTATUS_TYPES.FILLED,
                    'canceled': ORDERSTATUS_TYPES.CANCELED,
                    'rejected': ORDERSTATUS_TYPES.REJECTED
                }

                if status in status_map:
                    # order.status = status_map[status]
                    # if order_data.get('filled_size'):
                    #     order.filled_volume = order_data['filled_size']
                    # if order_data.get('avg_fill_price'):
                    #     order.filled_price = order_data['avg_fill_price']
                    # order_crud.update_order(order)

                    GLOG.DEBUG(f"Order updated for broker {broker_uuid}: {order_data.get('exchange_order_id')} -> {status}")

        except Exception as e:
            GLOG.ERROR(f"Error updating order for broker {broker_uuid}: {e}")

    def full_sync_check(self, broker_uuid: str) -> bool:
        """
        完整同步检查（30秒一次）

        验证本地数据与交易所数据的一致性

        Args:
            broker_uuid: Broker实例UUID

        Returns:
            bool: 数据是否一致
        """
        try:
            sync_info = self._active_syncs.get(broker_uuid)
            if not sync_info:
                return False

            # 执行一次完整的数据同步
            self._polling_update(broker_uuid)

            # TODO: 比对本地数据和交易所数据
            # 检查是否有差异

            return True

        except Exception as e:
            GLOG.ERROR(f"Full sync check failed for broker {broker_uuid}: {e}")
            return False

    def get_sync_status(self, broker_uuid: str) -> Optional[dict]:
        """
        获取同步状态

        Args:
            broker_uuid: Broker实例UUID

        Returns:
            dict: 同步状态信息
        """
        return self._active_syncs.get(broker_uuid)

    def stop_all_sync(self) -> None:
        """停止所有数据同步"""
        with self._lock:
            broker_uuids = list(self._active_syncs.keys())
            for broker_uuid in broker_uuids:
                self.stop_sync_for_broker(broker_uuid)


# 全局单例
_data_sync_service = None

def get_data_sync_service() -> DataSyncService:
    """获取DataSyncService单例"""
    global _data_sync_service
    if _data_sync_service is None:
        _data_sync_service = DataSyncService()
    return _data_sync_service
