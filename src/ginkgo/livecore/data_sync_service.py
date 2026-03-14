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
                if sync_info.get('websocket'):
                    # TODO: 关闭WebSocket连接
                    sync_info['websocket'] = None

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
            # TODO: 实现OKX WebSocket连接
            # python-okx SDK提供WebSocket接口
            # 需要订阅private频道以接收账户、持仓、订单更新

            GLOG.INFO(f"WebSocket started for broker {broker_uuid}")

            # 更新同步信息
            if broker_uuid in self._active_syncs:
                self._active_syncs[broker_uuid]['websocket'] = 'connected'

            return True

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
            msg_type = message.get('data', {}).get('arg', {}).get('channel', '')

            if msg_type == 'account':  # 账户余额更新
                balance_data = message.get('data', [])
                self._update_balance(broker_uuid, balance_data)

            elif msg_type == 'positions':  # 持仓更新
                position_data = message.get('data', [])
                self._update_positions(broker_uuid, position_data)

            elif msg_type == 'orders':  # 订单更新
                order_data = message.get('data', [])
                self._update_orders(broker_uuid, order_data)

            # 更新心跳
            broker_crud = container.broker_instance()
            broker_crud.update_heartbeat(broker_uuid)

        except Exception as e:
            GLOG.ERROR(f"Failed to process WebSocket message for broker {broker_uuid}: {e}")

    def _update_balance(self, broker_uuid: str, balance_data: list) -> None:
        """
        更新账户余额

        Args:
            broker_uuid: Broker实例UUID
            balance_data: 余额数据
        """
        # TODO: 更新MPortfolio中的余额字段
        # 需要通过PortfolioService或直接更新数据库
        pass

    def _update_positions(self, broker_uuid: str, position_data: list) -> None:
        """
        更新持仓信息

        Args:
            broker_uuid: Broker实例UUID
            position_data: 持仓数据
        """
        # TODO: 更新MPosition中的持仓信息
        # 需要匹配exchange_position_id并更新数量
        pass

    def _update_orders(self, broker_uuid: str, order_data: list) -> None:
        """
        更新订单状态

        Args:
            broker_uuid: Broker实例UUID
            order_data: 订单数据
        """
        # TODO: 更新MOrder中的订单状态
        # 需要匹配exchange_order_id并更新状态
        pass

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


# 全局单例
_data_sync_service = None

def get_data_sync_service() -> DataSyncService:
    """获取DataSyncService单例"""
    global _data_sync_service
    if _data_sync_service is None:
        _data_sync_service = DataSyncService()
    return _data_sync_service
