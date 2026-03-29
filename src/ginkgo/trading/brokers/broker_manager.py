# Upstream: LiveEngine (生命周期管理)、PortfolioService (Portfolio关联)
# Downstream: MBrokerInstance (Broker实例模型)、BrokerInstanceCRUD (CRUD操作)、OKXBroker (OKX实现)
# Role: BrokerManager 管理实盘Broker实例的生命周期


from typing import Dict, Optional, List
from datetime import datetime

from ginkgo.libs import GLOG
from ginkgo.data.containers import container
from ginkgo.data.models.model_broker_instance import MBrokerInstance, BrokerStateType
from ginkgo.data.models.model_portfolio import MPortfolio
from ginkgo.data.models.model_live_account import AccountStatusType, ExchangeType


class BrokerManager:
    """
    Broker实例管理器

    负责管理Portfolio与实盘账号之间的Broker实例生命周期：
    - 创建和销毁Broker实例
    - 启动、停止、暂停、恢复Broker
    - 紧急停止所有Broker
    - 处理Portfolio变更时的Broker重建
    """

    def __init__(self):
        """初始化BrokerManager"""
        self._brokers: Dict[str, any] = {}  # broker_uuid -> broker_instance
        self._broker_instance_crud = None
        self._live_account_crud = None
        self._portfolio_crud = None

    def _get_cruds(self):
        """延迟加载CRUD"""
        if self._broker_instance_crud is None:
            self._broker_instance_crud = container.broker_instance_crud()
            self._live_account_crud = container.live_account_crud()
            self._portfolio_crud = container.portfolio_crud()
        return self._broker_instance_crud, self._live_account_crud, self._portfolio_crud

    def startup_create_all_brokers(self) -> Dict[str, bool]:
        """
        启动时创建所有Live Portfolio的Broker实例

        扫描所有mode=LIVE的Portfolio，为每个创建对应的Broker实例。

        Returns:
            Dict[str, bool]: portfolio_id -> 创建是否成功
        """
        results = {}
        broker_crud, live_account_crud, portfolio_crud = self._get_cruds()

        try:
            # 查询所有实盘Portfolio
            # 注意：MPortfolio.mode=2表示实盘模式
            portfolios = portfolio_crud.find(filters={"mode": 2, "is_del": False})

            for portfolio in portfolios:
                if portfolio.live_account_id:
                    try:
                        success = self.create_broker(portfolio.uuid, portfolio.live_account_id)
                        results[portfolio.uuid] = success

                        if success:
                            # 自动启动Broker
                            self.start_broker(portfolio.uuid)
                    except Exception as e:
                        GLOG.ERROR(f"Failed to create broker for portfolio {portfolio.uuid}: {e}")
                        results[portfolio.uuid] = False
                else:
                    GLOG.WARNING(f"Portfolio {portfolio.uuid} has mode=LIVE but no live_account_id")
                    results[portfolio.uuid] = False

            GLOG.INFO(f"Broker startup complete: {sum(1 for s in results.values() if s)}/{len(results)} succeeded")
            return results

        except Exception as e:
            GLOG.ERROR(f"Failed to startup brokers: {e}")
            return results

    def create_broker(self, portfolio_id: str, live_account_id: str) -> bool:
        """
        创建Broker实例

        Args:
            portfolio_id: Portfolio ID
            live_account_id: 实盘账号ID

        Returns:
            bool: 创建是否成功
        """
        broker_crud, live_account_crud, portfolio_crud = self._get_cruds()

        try:
            # 验证实盘账号存在
            live_account = live_account_crud.get_live_account_by_uuid(live_account_id)
            if not live_account:
                GLOG.ERROR(f"Live account not found: {live_account_id}")
                return False

            # 验证实盘账号状态
            if live_account.status != AccountStatusType.ENABLED:
                GLOG.ERROR(f"Live account {live_account_id} is not enabled: {live_account.status}")
                return False

            # 检查是否已存在Broker实例
            existing_broker = broker_crud.get_broker_by_portfolio(portfolio_id)
            if existing_broker:
                GLOG.WARNING(f"Broker already exists for portfolio {portfolio_id}, recreating...")
                self.destroy_broker(portfolio_id)

            # 创建数据库记录
            broker = broker_crud.add_broker_instance(
                portfolio_id=portfolio_id,
                live_account_id=live_account_id,
                state="uninitialized"
            )

            # 创建实际的Broker对象（延迟加载）
            broker_obj = self._create_broker_object(broker)
            self._brokers[broker.uuid] = broker_obj

            # 更新状态为初始化中
            broker_crud.update_broker_instance_status(broker.uuid, "initializing")

            GLOG.INFO(f"Broker instance created: {broker.uuid} for portfolio {portfolio_id}")
            return True

        except Exception as e:
            GLOG.ERROR(f"Failed to create broker for portfolio {portfolio_id}: {e}")
            return False

    def _create_broker_object(self, broker_instance: MBrokerInstance):
        """
        创建实际的Broker对象

        Args:
            broker_instance: Broker实例数据模型

        Returns:
            Broker对象
        """
        # 延迟导入OKXBroker避免循环依赖
        from ginkgo.trading.brokers.okx_broker import OKXBroker

        live_account_crud = container.live_account_crud()
        live_account = live_account_crud.get_live_account_by_uuid(broker_instance.live_account_id)

        if live_account.exchange == ExchangeType.OKX:
            return OKXBroker(
                broker_uuid=broker_instance.uuid,
                portfolio_id=broker_instance.portfolio_id,
                live_account_id=broker_instance.live_account_id,
                api_key=live_account.api_key,  # 已经是加密后的值
                api_secret=live_account.api_secret,
                passphrase=live_account.passphrase,
                environment=live_account.environment
            )
        else:
            raise ValueError(f"Unsupported exchange: {live_account.exchange}")

    def destroy_broker(self, portfolio_id: str) -> bool:
        """
        销毁Broker实例

        Args:
            portfolio_id: Portfolio ID

        Returns:
            bool: 销毁是否成功
        """
        broker_crud, _, _ = self._get_cruds()

        try:
            # 查找Broker实例
            broker = broker_crud.get_broker_by_portfolio(portfolio_id)
            if not broker:
                GLOG.WARNING(f"No broker found for portfolio {portfolio_id}")
                return False

            # 如果正在运行，先停止
            if broker.state in [BrokerStateType.RUNNING, BrokerStateType.PAUSED]:
                self.stop_broker(portfolio_id)

            # 从内存中移除
            if broker.uuid in self._brokers:
                broker_obj = self._brokers[broker.uuid]
                try:
                    # 断开API连接
                    if hasattr(broker_obj, 'disconnect'):
                        broker_obj.disconnect()
                except Exception as e:
                    GLOG.ERROR(f"Error disconnecting broker {broker.uuid}: {e}")

                del self._brokers[broker.uuid]

            # 更新数据库状态
            broker_crud.update(broker.uuid, is_del=True, state="stopped")

            GLOG.INFO(f"Broker instance destroyed: {broker.uuid}")
            return True

        except Exception as e:
            GLOG.ERROR(f"Failed to destroy broker for portfolio {portfolio_id}: {e}")
            return False

    def recreate_broker(self, portfolio_id: str) -> bool:
        """
        重建Broker实例（用于live_account_id变更时）

        Args:
            portfolio_id: Portfolio ID

        Returns:
            bool: 重建是否成功
        """
        try:
            # 获取Portfolio信息
            portfolio_crud = container.portfolio_crud()
            portfolio = portfolio_crud.get(portfolio_id)
            if not portfolio or not portfolio.live_account_id:
                GLOG.ERROR(f"Portfolio {portfolio_id} not found or no live_account_id")
                return False

            # 销毁现有Broker
            if self.destroy_broker(portfolio_id):
                # 创建新Broker
                return self.create_broker(portfolio_id, portfolio.live_account_id)

            return False

        except Exception as e:
            GLOG.ERROR(f"Failed to recreate broker for portfolio {portfolio_id}: {e}")
            return False

    def start_broker(self, portfolio_id: str) -> bool:
        """
        启动Broker实例

        Args:
            portfolio_id: Portfolio ID

        Returns:
            bool: 启动是否成功
        """
        broker_crud, _, _ = self._get_cruds()

        try:
            broker = broker_crud.get_broker_by_portfolio(portfolio_id)
            if not broker:
                GLOG.ERROR(f"No broker found for portfolio {portfolio_id}")
                return False

            if broker.uuid not in self._brokers:
                GLOG.ERROR(f"Broker object not in memory: {broker.uuid}")
                return False

            broker_obj = self._brokers[broker.uuid]

            # 连接交易所API
            if hasattr(broker_obj, 'connect'):
                if not broker_obj.connect():
                    broker_crud.update_broker_instance_status(
                        broker.uuid,
                        "error",
                        error_message="Failed to connect to exchange API"
                    )
                    return False

            # 更新状态
            broker_crud.update_broker_instance_status(broker.uuid, "running", process_id=self._get_process_id())

            GLOG.INFO(f"Broker started: {broker.uuid}")
            return True

        except Exception as e:
            GLOG.ERROR(f"Failed to start broker for portfolio {portfolio_id}: {e}")
            # 尝试更新状态为错误
            try:
                broker_crud.update_broker_instance_status(
                    broker.uuid,
                    "error",
                    error_message=str(e)
                )
            except Exception as e:
                GLOG.ERROR(f"Failed to update broker status to error for portfolio {portfolio_id}: {e}")
            return False

    def stop_broker(self, portfolio_id: str) -> bool:
        """
        停止Broker实例

        Args:
            portfolio_id: Portfolio ID

        Returns:
            bool: 停止是否成功
        """
        broker_crud, _, _ = self._get_cruds()

        try:
            broker = broker_crud.get_broker_by_portfolio(portfolio_id)
            if not broker:
                return False

            if broker.uuid in self._brokers:
                broker_obj = self._brokers[broker.uuid]

                # 断开API连接
                if hasattr(broker_obj, 'disconnect'):
                    broker_obj.disconnect()

            # 更新状态
            broker_crud.update_broker_instance_status(broker.uuid, "stopped")

            GLOG.INFO(f"Broker stopped: {broker.uuid}")
            return True

        except Exception as e:
            GLOG.ERROR(f"Failed to stop broker for portfolio {portfolio_id}: {e}")
            return False

    def pause_broker(self, portfolio_id: str) -> bool:
        """
        暂停Broker实例

        Args:
            portfolio_id: Portfolio ID

        Returns:
            bool: 暂停是否成功
        """
        broker_crud, _, _ = self._get_cruds()

        try:
            broker = broker_crud.get_broker_by_portfolio(portfolio_id)
            if not broker or broker.state != BrokerStateType.RUNNING:
                GLOG.ERROR(f"Cannot pause broker: not running for portfolio {portfolio_id}")
                return False

            # 更新状态
            broker_crud.update_broker_instance_status(broker.uuid, "paused")

            GLOG.INFO(f"Broker paused: {broker.uuid}")
            return True

        except Exception as e:
            GLOG.ERROR(f"Failed to pause broker for portfolio {portfolio_id}: {e}")
            return False

    def resume_broker(self, portfolio_id: str) -> bool:
        """
        恢复Broker实例

        Args:
            portfolio_id: Portfolio ID

        Returns:
            bool: 恢复是否成功
        """
        broker_crud, _, _ = self._get_cruds()

        try:
            broker = broker_crud.get_broker_by_portfolio(portfolio_id)
            if not broker or broker.state != BrokerStateType.PAUSED:
                GLOG.ERROR(f"Cannot resume broker: not paused for portfolio {portfolio_id}")
                return False

            # 更新状态
            broker_crud.update_broker_instance_status(broker.uuid, "running")

            GLOG.INFO(f"Broker resumed: {broker.uuid}")
            return True

        except Exception as e:
            GLOG.ERROR(f"Failed to resume broker for portfolio {portfolio_id}: {e}")
            return False

    def emergency_stop_all(self) -> int:
        """
        紧急停止所有Broker实例

        Returns:
            int: 成功停止的Broker数量
        """
        broker_crud, _, _ = self._get_cruds()

        stopped_count = 0

        try:
            # 获取所有活跃的Broker
            active_brokers = broker_crud.get_active_brokers()

            for broker in active_brokers:
                if self.stop_broker(broker.portfolio_id):
                    stopped_count += 1

            GLOG.WARNING(f"Emergency stop completed: {stopped_count}/{len(active_brokers)} brokers stopped")
            return stopped_count

        except Exception as e:
            GLOG.ERROR(f"Failed to emergency stop brokers: {e}")
            return stopped_count

    def _get_process_id(self) -> int:
        """获取当前进程ID"""
        import os
        return os.getpid()

    def get_broker(self, portfolio_id: str) -> Optional[any]:
        """
        获取指定Portfolio的Broker对象

        Args:
            portfolio_id: Portfolio ID

        Returns:
            Broker对象，如果不存在则返回None
        """
        broker_crud, _, _ = self._get_cruds()
        broker = broker_crud.get_broker_by_portfolio(portfolio_id)

        if broker and broker.uuid in self._brokers:
            return self._brokers[broker.uuid]

        return None


# 全局单例
_broker_manager = None

def get_broker_manager() -> BrokerManager:
    """获取BrokerManager单例"""
    global _broker_manager
    if _broker_manager is None:
        _broker_manager = BrokerManager()
    return _broker_manager
