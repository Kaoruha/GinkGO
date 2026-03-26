# Upstream: CLI启动命令、系统启动钩子
# Downstream: DataSyncService、HeartbeatMonitor、BrokerRecoveryService、BrokerManager
# Role: LiveEngine 整合LiveCore所有组件，提供统一启动入口


import signal
import threading
import time
import warnings
from typing import Optional, Dict, Any
from datetime import datetime

from ginkgo.libs import GLOG, GCONF
from ginkgo.data.containers import container


class LiveEngine:
    """
    实盘交易引擎

    整合所有LiveCore组件，提供统一的生命周期管理：
    - 初始化：加载实盘Portfolio并创建Broker实例
    - 启动：启动数据同步、心跳监控、恢复服务
    - 停止：优雅关闭所有组件
    - 信号处理：响应系统信号实现安全退出
    """

    def __init__(self):
        """初始化LiveEngine"""
        warnings.warn(
            "LiveEngine is deprecated. Use TimeControlledEventEngine(mode=EXECUTION_MODE.LIVE) instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        self._running = False
        self._data_sync_service = None
        self._heartbeat_monitor = None
        self._recovery_service = None
        self._broker_manager = None
        self._signal_handlers_installed = False
        self._lock = threading.RLock()
        self._shutdown_event = threading.Event()

        # 组件状态追踪
        self._component_status: Dict[str, bool] = {
            "data_sync": False,
            "heartbeat_monitor": False,
            "broker_recovery": False,
        }

    def initialize(self) -> bool:
        """
        初始化LiveEngine

        加载所有实盘Portfolio并创建对应的Broker实例

        Returns:
            bool: 初始化是否成功
        """
        try:
            GLOG.info("=" * 60)
            GLOG.info("Initializing LiveEngine")
            GLOG.info("=" * 60)

            # 1. 获取所有配置了实盘账号的Portfolio
            portfolio_crud = container.portfolio()
            live_account_crud = container.live_account()

            # 获取所有已启用的实盘账号
            enabled_accounts = live_account_crud.find(filters={
                "is_del": False,
                "status": "enabled"
            })

            if not enabled_accounts:
                GLOG.WARNING("No enabled live accounts found")
                return True

            GLOG.info(f"Found {len(enabled_accounts)} enabled live account(s)")

            # 2. 获取BrokerManager
            from ginkgo.trading.brokers.broker_manager import get_broker_manager
            self._broker_manager = get_broker_manager()

            # 3. 为每个实盘账号创建Broker实例
            created_count = 0
            for account in enabled_accounts:
                try:
                    # 查找绑定到此账号的Portfolio
                    portfolios = portfolio_crud.find(filters={
                        "is_del": False,
                        "live_account_id": account.uuid
                    })

                    if not portfolios:
                        GLOG.WARNING(f"No portfolio found for live account: {account.name}")
                        continue

                    for portfolio in portfolios:
                        # 检查是否已存在Broker实例
                        broker_crud = container.broker_instance()
                        existing = broker_crud.get_broker_by_portfolio(portfolio.uuid)

                        if existing:
                            GLOG.info(f"Broker already exists for portfolio {portfolio.uuid}, skipping")
                            continue

                        # 创建新Broker实例
                        success = self._broker_manager.create_broker(
                            portfolio_id=portfolio.uuid,
                            live_account_id=account.uuid
                        )

                        if success:
                            created_count += 1
                            GLOG.info(f"Created broker for portfolio {portfolio.uuid}")
                        else:
                            GLOG.ERROR(f"Failed to create broker for portfolio {portfolio.uuid}")

                except Exception as e:
                    GLOG.ERROR(f"Error creating broker for account {account.uuid}: {e}")

            GLOG.info(f"LiveEngine initialization complete: {created_count} broker(s) created")
            return True

        except Exception as e:
            GLOG.ERROR(f"Failed to initialize LiveEngine: {e}")
            return False

    def start(self) -> bool:
        """
        启动LiveEngine

        启动数据同步服务、心跳监控、恢复服务

        Returns:
            bool: 启动是否成功
        """
        with self._lock:
            if self._running:
                GLOG.WARNING("LiveEngine is already running")
                return True

            try:
                GLOG.info("=" * 60)
                GLOG.info("Starting LiveEngine")
                GLOG.info("=" * 60)

                # 1. 安装信号处理器
                self._install_signal_handlers()

                # 2. 启动心跳监控
                if not self._start_heartbeat_monitor():
                    GLOG.ERROR("Failed to start heartbeat monitor")
                    return False

                # 3. 启动数据同步服务
                if not self._start_data_sync():
                    GLOG.ERROR("Failed to start data sync service")
                    # 不返回失败，允许降级运行

                # 4. 初始化恢复服务（懒加载）
                from ginkgo.livecore.broker_recovery_service import get_broker_recovery_service
                self._recovery_service = get_broker_recovery_service()

                # 5. 注册恢复回调到心跳监控
                if self._heartbeat_monitor and self._recovery_service:
                    self._heartbeat_monitor.add_timeout_callback(
                        self._on_broker_timeout
                    )
                    self._component_status["broker_recovery"] = True

                # 6. 启动所有已停止的Broker
                self._startup_brokers()

                self._running = True
                GLOG.info("LiveEngine started successfully")
                return True

            except Exception as e:
                GLOG.ERROR(f"Failed to start LiveEngine: {e}")
                self.stop()
                return False

    def stop(self) -> bool:
        """
        停止LiveEngine

        优雅关闭所有组件

        Returns:
            bool: 停止是否成功
        """
        with self._lock:
            if not self._running:
                GLOG.WARNING("LiveEngine is not running")
                return True

            try:
                GLOG.info("=" * 60)
                GLOG.info("Stopping LiveEngine")
                GLOG.info("=" * 60)

                self._running = False
                self._shutdown_event.set()

                # 1. 停止心跳监控
                if self._heartbeat_monitor:
                    try:
                        self._heartbeat_monitor.stop_monitoring()
                        self._component_status["heartbeat_monitor"] = False
                        GLOG.info("Heartbeat monitor stopped")
                    except Exception as e:
                        GLOG.ERROR(f"Error stopping heartbeat monitor: {e}")

                # 2. 停止数据同步（包括WebSocket连接）
                if self._data_sync_service:
                    try:
                        # 停止所有同步并关闭WebSocket
                        broker_crud = container.broker_instance()
                        active_brokers = broker_crud.get_active_brokers()
                        for broker in active_brokers:
                            self._data_sync_service.stop_sync_for_broker(broker.uuid)

                        self._component_status["data_sync"] = False
                        GLOG.info("Data sync service stopped")
                    except Exception as e:
                        GLOG.ERROR(f"Error stopping data sync service: {e}")

                # 3. 停止WebSocket管理器
                try:
                    self._shutdown_websocket_manager()
                except Exception as e:
                    GLOG.ERROR(f"Error stopping WebSocket manager: {e}")

                # 4. 停止所有Broker
                if self._broker_manager:
                    try:
                        stopped_count = self._broker_manager.stop_all_brokers()
                        GLOG.info(f"Stopped {stopped_count} broker(s)")
                    except Exception as e:
                        GLOG.ERROR(f"Error stopping brokers: {e}")

                GLOG.info("LiveEngine stopped")
                return True

            except Exception as e:
                GLOG.ERROR(f"Error during LiveEngine shutdown: {e}")
                return False

    def wait(self) -> None:
        """
        等待LiveEngine退出

        阻塞直到收到停止信号
        """
        try:
            while self._running and not self._shutdown_event.is_set():
                time.sleep(1)
        except KeyboardInterrupt:
            GLOG.info("Received keyboard interrupt")
            self.stop()

    def _install_signal_handlers(self) -> None:
        """安装信号处理器"""
        if self._signal_handlers_installed:
            return

        def signal_handler(signum, frame):
            GLOG.info(f"Received signal {signum}")
            self._shutdown_event.set()
            self.stop()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        self._signal_handlers_installed = True
        GLOG.info("Signal handlers installed")

    def _start_heartbeat_monitor(self) -> bool:
        """启动心跳监控"""
        try:
            from ginkgo.livecore.heartbeat_monitor import get_heartbeat_monitor

            self._heartbeat_monitor = get_heartbeat_monitor()

            # 从配置获取超时设置
            timeout_seconds = GCONF.get("live.heartbeat_timeout", 30)
            check_interval = GCONF.get("live.heartbeat_check_interval", 10)

            success = self._heartbeat_monitor.start_monitoring()

            if success:
                self._component_status["heartbeat_monitor"] = True
                GLOG.info(f"Heartbeat monitor started (timeout={timeout_seconds}s, interval={check_interval}s)")
                return True
            else:
                GLOG.ERROR("Failed to start heartbeat monitor")
                return False

        except Exception as e:
            GLOG.ERROR(f"Error starting heartbeat monitor: {e}")
            return False

    def _start_data_sync(self) -> bool:
        """启动数据同步服务"""
        try:
            from ginkgo.livecore.data_sync_service import DataSyncService

            self._data_sync_service = DataSyncService()

            # 为所有Broker启动数据同步
            broker_crud = container.broker_instance()
            active_brokers = broker_crud.get_active_brokers()

            sync_count = 0
            for broker in active_brokers:
                try:
                    if self._data_sync_service.start_sync_for_broker(broker.uuid):
                        sync_count += 1
                except Exception as e:
                    GLOG.ERROR(f"Error starting sync for broker {broker.uuid}: {e}")

            if sync_count > 0:
                self._component_status["data_sync"] = True
                GLOG.info(f"Data sync service started for {sync_count} broker(s)")
                return True
            else:
                GLOG.WARNING("No data sync services started")
                return False

        except Exception as e:
            GLOG.ERROR(f"Error starting data sync service: {e}")
            return False

    def _startup_brokers(self) -> None:
        """启动所有已配置的Broker"""
        try:
            broker_crud = container.broker_instance()
            brokers = broker_crud.find(filters={"is_del": False})

            started_count = 0
            for broker in brokers:
                if broker.state in ["uninitialized", "stopped"]:
                    try:
                        if self._broker_manager.start_broker(broker.portfolio_id):
                            started_count += 1
                    except Exception as e:
                        GLOG.ERROR(f"Error starting broker {broker.uuid}: {e}")

            GLOG.info(f"Started {started_count} broker(s)")

        except Exception as e:
            GLOG.ERROR(f"Error in _startup_brokers: {e}")

    def _on_broker_timeout(self, broker_uuid: str) -> None:
        """
        Broker超时回调

        Args:
            broker_uuid: Broker实例UUID
        """
        try:
            GLOG.WARNING(f"Broker timeout detected: {broker_uuid}, initiating recovery")

            broker_crud = container.broker_instance()
            broker = broker_crud.get_broker_by_uuid(broker_uuid)

            if not broker:
                GLOG.ERROR(f"Broker not found for recovery: {broker_uuid}")
                return

            if self._recovery_service:
                # 异步恢复避免阻塞心跳监控
                def recovery_task():
                    self._recovery_service.recover_broker(
                        broker_uuid,
                        broker.portfolio_id
                    )

                thread = threading.Thread(target=recovery_task, daemon=True)
                thread.start()

        except Exception as e:
            GLOG.ERROR(f"Error in timeout callback for {broker_uuid}: {e}")

    def _shutdown_websocket_manager(self) -> None:
        """关闭WebSocket管理器"""
        try:
            from ginkgo.livecore.websocket_manager import get_websocket_manager
            ws_manager = get_websocket_manager()
            ws_manager.shutdown()
            GLOG.info("WebSocket manager shutdown complete")
        except ImportError:
            # WebSocket不可用，跳过
            pass
        except Exception as e:
            GLOG.ERROR(f"Error shutting down WebSocket manager: {e}")

    def get_component_status(self) -> Dict[str, bool]:
        """获取组件状态"""
        return self._component_status.copy()

    def is_running(self) -> bool:
        """检查引擎是否正在运行"""
        return self._running


# 全局单例
_live_engine = None

def get_live_engine() -> LiveEngine:
    """获取LiveEngine单例"""
    global _live_engine
    if _live_engine is None:
        _live_engine = LiveEngine()
    return _live_engine
