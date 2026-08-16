# Upstream: 行情订阅 API (market/subscriptions)
# Downstream: BaseService (继承), MarketSubscriptionCRUD (数据访问)
# Role: 用户行情订阅的业务服务层——列表/创建/更新/删除，Model→前端契约序列化

"""
Market Subscription Service

用户行情订阅服务：
- list_subscriptions: 按用户查询订阅（交易所/环境/激活态过滤）
- create_subscription: 创建（或重新激活已存在订阅）
- update_subscription: 更新数据类型/激活态（含归属校验）
- delete_subscription: 软删除（含归属校验）

序列化契约对齐前端 MarketSubscription 类型（8 字段，丢弃 user_id/is_del
内部字段；data_types 由 JSON 字符串还原为 list）。
"""

from typing import Optional

from ginkgo.data.services.base_service import BaseService, ServiceResult


def _serialize(sub) -> dict:
    """MMarketSubscription → 前端契约 dict"""
    return {
        "uuid": sub.uuid,
        "exchange": sub.exchange,
        "environment": sub.environment,
        "symbol": sub.symbol,
        "data_types": sub.get_data_types(),
        "is_active": bool(sub.is_active),
        "create_at": sub.create_at.isoformat() if sub.create_at else None,
        "update_at": sub.update_at.isoformat() if sub.update_at else None,
    }


class MarketSubscriptionService(BaseService):
    """
    行情订阅服务
    """

    def list_subscriptions(
        self,
        user_id: str,
        exchange: Optional[str] = None,
        environment: Optional[str] = None,
        active_only: bool = True,
    ) -> ServiceResult:
        """
        按用户查询订阅列表

        Returns:
            ServiceResult: {"subscriptions": [...], "total": N}
        """
        try:
            subs = self._crud_repo.get_user_subscriptions(
                user_id=user_id,
                exchange=exchange,
                environment=environment,
                active_only=active_only,
            )
            data = [_serialize(s) for s in subs]
            return ServiceResult.success(
                data={"subscriptions": data, "total": len(data)},
                message=f"Found {len(data)} subscriptions",
            )
        except Exception as e:
            return ServiceResult.error(f"Failed to list subscriptions: {str(e)}")

    def create_subscription(
        self,
        user_id: str,
        exchange: str,
        symbol: str,
        data_types: Optional[list] = None,
        environment: str = "production",
    ) -> ServiceResult:
        """
        创建订阅（同 user+exchange+symbol 已存在时更新 data_types 并激活）
        """
        try:
            record = self._crud_repo.add_subscription(
                user_id=user_id,
                exchange=exchange,
                symbol=symbol,
                data_types=data_types,
                environment=environment,
            )
            if record is None:
                return ServiceResult.error("Failed to create subscription")
            return ServiceResult.success(
                data=_serialize(record),
                message=f"Subscribed to {symbol}",
            )
        except Exception as e:
            return ServiceResult.error(f"Failed to create subscription: {str(e)}")

    def update_subscription(
        self,
        uuid: str,
        user_id: str,
        data_types: Optional[list] = None,
        is_active: Optional[bool] = None,
    ) -> ServiceResult:
        """
        更新订阅（数据类型/激活态）。归属不符 → error(403 语义)。
        """
        try:
            existing = self._crud_repo.get_subscription_by_uuid(uuid)
            if existing is None:
                return ServiceResult.error(f"Subscription not found: {uuid}")
            if existing.user_id != user_id:
                return ServiceResult.error("无权访问该订阅")

            record = self._crud_repo.update_subscription(
                uuid=uuid,
                data_types=data_types,
                is_active=is_active,
            )
            if record is None:
                return ServiceResult.error(f"Failed to update subscription: {uuid}")
            return ServiceResult.success(data=_serialize(record), message="Subscription updated")
        except Exception as e:
            return ServiceResult.error(f"Failed to update subscription: {str(e)}")

    def delete_subscription(self, uuid: str, user_id: str) -> ServiceResult:
        """
        删除订阅（软删除）。归属不符 → error(403 语义)。
        """
        try:
            existing = self._crud_repo.get_subscription_by_uuid(uuid)
            if existing is None:
                return ServiceResult.error(f"Subscription not found: {uuid}")
            if existing.user_id != user_id:
                return ServiceResult.error("无权访问该订阅")

            removed = self._crud_repo.remove_subscription(uuid)
            if not removed:
                return ServiceResult.error(f"Failed to delete subscription: {uuid}")
            return ServiceResult.success(data={"uuid": uuid}, message="Subscription deleted")
        except Exception as e:
            return ServiceResult.error(f"Failed to delete subscription: {str(e)}")
