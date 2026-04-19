# Upstream: BrokerManager (Broker实例管理)、LiveEngine (生命周期管理)
# Downstream: BaseCRUD (继承提供标准CRUD能力)、MBrokerInstance (MySQL Broker实例模型)
# Role: BrokerInstanceCRUD Broker实例CRUD操作提供Broker状态跟踪和心跳管理功能


from typing import List, Optional, Dict
from datetime import datetime, timedelta
from sqlalchemy import and_, or_

from ginkgo.data.crud.base_crud import BaseCRUD
from ginkgo.data.models.model_broker_instance import MBrokerInstance, BrokerStateType
from ginkgo.enums import SOURCE_TYPES
from ginkgo.libs import GLOG
from ginkgo.data.access_control import restrict_crud_access


@restrict_crud_access
class BrokerInstanceCRUD(BaseCRUD[MBrokerInstance]):
    """
    Broker实例CRUD操作

    支持Broker实例的生命周期管理：
    - 创建和更新Broker实例状态
    - 心跳超时检测
    - 按Portfolio或实盘账号查询
    - 错误统计和订单统计
    """

    _model_class = MBrokerInstance

    def __init__(self):
        super().__init__(MBrokerInstance)

    def _get_enum_mappings(self) -> Dict[str, any]:
        """定义字段到枚举的映射"""
        return {
            'source': SOURCE_TYPES,
        }

    def _get_field_config(self) -> dict:
        """定义BrokerInstance数据的字段配置"""
        return {
            'portfolio_id': {
                'type': 'string',
                'min': 1,
                'max': 32,
                'required': True
            },
            'live_account_id': {
                'type': 'string',
                'min': 1,
                'max': 32,
                'required': True
            },
            'state': {
                'type': 'string',
                'min': 5,
                'max': 20,
                'required': True
            }
        }

    def add_broker_instance(
        self,
        portfolio_id: str,
        live_account_id: str,
        state: str = "uninitialized"
    ) -> MBrokerInstance:
        """
        添加Broker实例

        Args:
            portfolio_id: Portfolio ID
            live_account_id: 实盘账号ID
            state: 初始状态 (默认: uninitialized)

        Returns:
            MBrokerInstance: 创建的Broker实例
        """
        # 验证状态枚举
        BrokerStateType.from_str(state)

        broker = MBrokerInstance(
            portfolio_id=portfolio_id,
            live_account_id=live_account_id,
            state=state
        )
        return self.add(broker)

    def update_broker_instance_status(
        self,
        broker_uuid: str,
        state: str,
        error_message: Optional[str] = None,
        process_id: Optional[int] = None
    ) -> bool:
        """
        更新Broker实例状态

        Args:
            broker_uuid: Broker实例UUID
            state: 新状态
            error_message: 错误消息 (可选)
            process_id: 进程ID (可选)

        Returns:
            bool: 更新是否成功
        """
        try:
            # 查询现有实例
            broker = self.get_broker_by_uuid(broker_uuid)
            if broker is None:
                GLOG.ERROR(f"Broker instance not found: {broker_uuid}")
                return False

            # 验证状态转换
            try:
                broker.set_state(state)
            except ValueError as e:
                GLOG.ERROR(f"Invalid state transition for {broker_uuid}: {e}")
                return False

            # 更新字段
            update_data = {"state": state}
            if error_message is not None:
                update_data["error_message"] = error_message
                broker.increment_error(error_message)
            if process_id is not None:
                update_data["process_id"] = process_id

            # 执行更新
            self.update(broker_uuid, **update_data)
            return True

        except Exception as e:
            GLOG.ERROR(f"Failed to update broker instance status: {e}")
            return False

    def get_broker_by_portfolio(self, portfolio_id: str) -> Optional[MBrokerInstance]:
        """
        根据Portfolio ID获取Broker实例

        Args:
            portfolio_id: Portfolio ID

        Returns:
            MBrokerInstance: Broker实例，如果不存在则返回None
        """
        filters = {
            "portfolio_id": portfolio_id,
            "is_del": False
        }
        return self.find(filters=filters).first()

    def get_broker_by_live_account(self, live_account_id: str) -> List[MBrokerInstance]:
        """
        根据实盘账号ID获取所有Broker实例

        Args:
            live_account_id: 实盘账号ID

        Returns:
            List[MBrokerInstance]: Broker实例列表
        """
        filters = {
            "live_account_id": live_account_id,
            "is_del": False
        }
        return self.find(filters=filters)

    def get_broker_by_uuid(self, broker_uuid: str) -> Optional[MBrokerInstance]:
        """
        根据UUID获取Broker实例

        Args:
            broker_uuid: Broker实例UUID

        Returns:
            MBrokerInstance: Broker实例，如果不存在则返回None
        """
        return self.get(broker_uuid)

    def update_heartbeat(self, broker_uuid: str) -> bool:
        """
        更新Broker心跳时间

        Args:
            broker_uuid: Broker实例UUID

        Returns:
            bool: 更新是否成功
        """
        try:
            broker = self.get_broker_by_uuid(broker_uuid)
            if broker is None:
                return False

            broker.update_heartbeat()
            self.update(broker_uuid, heartbeat_at=datetime.now(datetime.timezone.utc))
            return True

        except Exception as e:
            GLOG.ERROR(f"Failed to update heartbeat for {broker_uuid}: {e}")
            return False

    def check_timeout(self, timeout_seconds: int = 30) -> List[MBrokerInstance]:
        """
        检查心跳超时的Broker实例

        Args:
            timeout_seconds: 超时秒数 (默认: 30秒)

        Returns:
            List[MBrokerInstance]: 超时的Broker实例列表
        """
        try:
            timeout_threshold = datetime.now(datetime.timezone.utc) - timedelta(seconds=timeout_seconds)

            # 查询所有活跃状态但心跳超时的实例
            active_states = [BrokerStateType.RUNNING, BrokerStateType.INITIALIZING, BrokerStateType.RECOVERING]

            results = self.find(filters={"is_del": False})
            timeout_brokers = []

            for broker in results:
                if broker.state in active_states:
                    if broker.heartbeat_at is None or broker.heartbeat_at < timeout_threshold:
                        timeout_brokers.append(broker)

            return timeout_brokers

        except Exception as e:
            GLOG.ERROR(f"Failed to check timeout brokers: {e}")
            return []

    def get_active_brokers(self) -> List[MBrokerInstance]:
        """
        获取所有活跃状态的Broker实例

        Returns:
            List[MBrokerInstance]: 活跃Broker实例列表
        """
        results = self.find(filters={"is_del": False})
        return [b for b in results if b.is_active()]

    def increment_order_count(
        self,
        broker_uuid: str,
        order_type: str  # "submitted", "filled", "cancelled", "rejected"
    ) -> bool:
        """
        增加订单计数

        Args:
            broker_uuid: Broker实例UUID
            order_type: 订单类型 (submitted/filled/cancelled/rejected)

        Returns:
            bool: 更新是否成功
        """
        try:
            broker = self.get_broker_by_uuid(broker_uuid)
            if broker is None:
                return False

            if order_type == "submitted":
                broker.record_order_submitted()
                self.update(broker_uuid,
                    total_submitted=broker.total_submitted,
                    last_order_at=broker.last_order_at)
            elif order_type == "filled":
                broker.record_order_filled()
                self.update(broker_uuid, total_filled=broker.total_filled)
            elif order_type == "cancelled":
                broker.record_order_cancelled()
                self.update(broker_uuid, total_cancelled=broker.total_cancelled)
            elif order_type == "rejected":
                broker.record_order_rejected()
                self.update(broker_uuid, total_rejected=broker.total_rejected)
            else:
                GLOG.WARNING(f"Unknown order type: {order_type}")
                return False

            return True

        except Exception as e:
            GLOG.ERROR(f"Failed to increment order count: {e}")
            return False
