# Upstream: MarketDataService (市场数据业务服务)
# Downstream: BaseCRUD (继承提供标准CRUD能力)、MMarketSubscription (MySQL订阅模型)
# Role: MarketSubscriptionCRUD市场数据订阅CRUD操作提供用户交易对订阅管理


from typing import List, Optional, Dict, Any
import pandas as pd
from datetime import datetime
from sqlalchemy import and_

from ginkgo.data.crud.base_crud import BaseCRUD
from ginkgo.data.models.model_market_subscription import MMarketSubscription, SubscriptionDataType
from ginkgo.enums import SOURCE_TYPES
from ginkgo.libs import GLOG


class MarketSubscriptionCRUD(BaseCRUD[MMarketSubscription]):
    """
    市场数据订阅CRUD操作

    支持用户订阅管理：
    - 创建订阅
    - 查询订阅
    - 更新订阅
    - 删除订阅
    - 获取用户的活跃订阅列表
    """

    _model_class = MMarketSubscription

    def __init__(self):
        super().__init__(MMarketSubscription)

    def _get_enum_mappings(self) -> Dict[str, Any]:
        """定义字段到枚举的映射"""
        return {
            'source': SOURCE_TYPES,
        }

    def _get_field_config(self) -> dict:
        """定义MarketSubscription数据的字段配置"""
        return {
            'exchange': {'type': 'string', 'min': 2, 'max': 20},
            'environment': {'type': 'string', 'min': 5, 'max': 20},
            'symbol': {'type': 'string', 'min': 1, 'max': 50},
            'data_types': {'type': 'json'},
            'is_active': {'type': 'boolean'},
        }

    def _create_from_params(self, **kwargs) -> MMarketSubscription:
        """从参数创建MMarketSubscription实例"""
        return MMarketSubscription(**kwargs)

    def _convert_input_item(self, item: Any) -> Optional[MMarketSubscription]:
        """转换对象为MMarketSubscription"""
        if isinstance(item, MMarketSubscription):
            return item
        return None

    def _convert_models_to_business_objects(self, models: List) -> List:
        """转换模型为业务对象"""
        return models

    def _convert_output_items(self, items: List[MMarketSubscription], output_type: str = "model") -> List[Any]:
        """转换MMarketSubscription对象供业务层使用"""
        return items

    # ==================== 订阅专用CRUD操作 ====================

    def add_subscription(
        self,
        user_id: str,
        exchange: str,
        symbol: str,
        data_types: Optional[List[str]] = None,
        environment: str = "testnet"
    ) -> MMarketSubscription:
        """
        添加订阅

        Args:
            user_id: 用户ID
            exchange: 交易所类型 (okx/binance)
            symbol: 交易对代码
            data_types: 数据类型列表 (默认 ["ticker"])
            environment: 环境 (production/testnet)

        Returns:
            MMarketSubscription: 创建的订阅对象
        """
        if data_types is None:
            data_types = [SubscriptionDataType.TICKER]

        # 检查是否已存在
        existing = self.find(
            filters={
                "user_id": user_id,
                "exchange": exchange,
                "symbol": symbol,
                "is_del": False
            },
        )

        if existing:
            # 已存在，更新数据类型
            subscription = existing[0]
            subscription.set_data_types(data_types)
            subscription.is_active = True
            subscription.update_at = datetime.now()
            return self.add(subscription)

        # 创建新订阅
        subscription = MMarketSubscription(
            user_id=user_id,
            exchange=exchange,
            symbol=symbol,
            data_types=data_types,
            environment=environment,
            is_active=True,
            source=SOURCE_TYPES.LIVE
        )

        return self.add(subscription)

    def get_user_subscriptions(
        self,
        user_id: str,
        exchange: Optional[str] = None,
        environment: Optional[str] = None,
        active_only: bool = True
    ) -> List[MMarketSubscription]:
        """
        获取用户的订阅列表

        Args:
            user_id: 用户ID
            exchange: 过滤交易所类型
            environment: 过滤环境类型
            active_only: 是否只返回活跃订阅

        Returns:
            List[MMarketSubscription]: 订阅列表
        """
        filters = {"user_id": user_id, "is_del": False}
        if active_only:
            filters["is_active"] = True


        # 应用额外过滤
        filtered_results = []
        for subscription in results:
            if exchange and subscription.exchange != exchange:
                continue
            if environment and subscription.environment != environment:
                continue
            filtered_results.append(subscription)

        return filtered_results

    def get_subscription_by_uuid(self, uuid: str) -> Optional[MMarketSubscription]:
        """
        根据UUID获取订阅

        Args:
            uuid: 订阅UUID

        Returns:
            MMarketSubscription or None: 订阅对象
        """
        if not results:
            return None
        return results[0]

    def get_subscription(
        self,
        user_id: str,
        exchange: str,
        symbol: str
    ) -> Optional[MMarketSubscription]:
        """
        获取指定订阅

        Args:
            user_id: 用户ID
            exchange: 交易所类型
            symbol: 交易对代码

        Returns:
            MMarketSubscription or None: 订阅对象
        """
        results = self.find(
            filters={
                "user_id": user_id,
                "exchange": exchange,
                "symbol": symbol,
                "is_del": False
            },
        )
        if not results:
            return None
        return results[0]

    def update_subscription(
        self,
        uuid: str,
        data_types: Optional[List[str]] = None,
        is_active: Optional[bool] = None
    ) -> Optional[MMarketSubscription]:
        """
        更新订阅

        Args:
            uuid: 订阅UUID
            data_types: 新的数据类型列表
            is_active: 是否激活

        Returns:
            MMarketSubscription or None: 更新后的订阅对象
        """
        subscription = self.get_subscription_by_uuid(uuid)
        if not subscription:
            GLOG.WARN(f"Subscription not found: {uuid}")
            return None

        updates = {}

        if data_types is not None:
            subscription.set_data_types(data_types)
            # 将 JSON 字符串添加到更新
            updates["data_types"] = subscription.data_types

        if is_active is not None:
            updates["is_active"] = is_active

        if updates:
            updates["update_at"] = datetime.now()
            self.modify(filters={"uuid": uuid}, updates=updates)

        return self.get_subscription_by_uuid(uuid)

    def remove_subscription(
        self,
        uuid: str,
        soft_delete: bool = True
    ) -> bool:
        """
        删除订阅

        Args:
            uuid: 订阅UUID
            soft_delete: 是否软删除

        Returns:
            bool: 是否删除成功
        """
        subscription = self.get_subscription_by_uuid(uuid)
        if not subscription:
            GLOG.WARN(f"Subscription not found: {uuid}")
            return False

        if soft_delete:
            self.modify(filters={"uuid": uuid}, updates={"is_del": True, "is_active": False})
        else:
            self.delete(subscription)

        GLOG.INFO(f"Subscription removed: {uuid}")
        return True

    def remove_subscription_by_symbol(
        self,
        user_id: str,
        exchange: str,
        symbol: str
    ) -> bool:
        """
        根据交易对删除订阅

        Args:
            user_id: 用户ID
            exchange: 交易所类型
            symbol: 交易对代码

        Returns:
            bool: 是否删除成功
        """
        subscription = self.get_subscription(user_id, exchange, symbol)
        if not subscription:
            return False

        return self.remove_subscription(subscription.uuid)

    def get_all_active_symbols(
        self,
        exchange: Optional[str] = None,
        environment: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        获取所有活跃订阅的交易对（用于 DataManager 恢复订阅）

        Args:
            exchange: 过滤交易所类型
            environment: 过滤环境类型

        Returns:
            List[Dict]: 交易对信息列表 [{"user_id", "exchange", "symbol", "data_types"}]
        """
        filters = {"is_active": True, "is_del": False}

        # 应用额外过滤并转换为字典
        symbol_list = []
        for subscription in results:
            if exchange and subscription.exchange != exchange:
                continue
            if environment and subscription.environment != environment:
                continue

            symbol_list.append({
                "user_id": subscription.user_id,
                "exchange": subscription.exchange,
                "environment": subscription.environment,
                "symbol": subscription.symbol,
                "data_types": subscription.get_data_types()
            })

        return symbol_list

    def deactivate_user_subscriptions(
        self,
        user_id: str,
        exchange: Optional[str] = None
    ) -> int:
        """
        停用用户的所有订阅

        Args:
            user_id: 用户ID
            exchange: 交易所类型（可选）

        Returns:
            int: 停用的订阅数量
        """
        filters = {"user_id": user_id, "is_del": False}

        count = 0
        for subscription in results:
            if exchange and subscription.exchange != exchange:
                continue
            self.modify(filters={"uuid": subscription.uuid}, updates={"is_active": False})
            count += 1

        return count
