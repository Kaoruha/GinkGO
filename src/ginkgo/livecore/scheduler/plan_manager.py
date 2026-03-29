"""
调度计划管理模块

管理 Redis 中的调度计划读写，检测孤儿 Portfolio、已删除 Portfolio、新 Portfolio。
"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class PlanManager:
    """调度计划读写与异常检测"""

    SCHEDULE_PLAN_KEY = "schedule:plan"

    def __init__(self, redis_client):
        self.redis_client = redis_client

    def get_current_schedule_plan(self) -> Dict[str, str]:
        """
        获取当前调度计划

        Returns:
            Dict: {portfolio_id: node_id}
        """
        try:
            plan = self.redis_client.hgetall(self.SCHEDULE_PLAN_KEY)
            return {
                k.decode('utf-8'): v.decode('utf-8')
                for k, v in plan.items()
            }
        except Exception as e:
            logger.error(f"Failed to get current schedule plan: {e}")
            return {}

    def detect_orphaned_portfolios(self, healthy_nodes, current_plan=None) -> List[str]:
        """
        检测离线 Node 的 Portfolio（孤儿 Portfolio）

        Args:
            healthy_nodes: 健康的 Node 列表
            current_plan: 当前调度计划（可选，为 None 时自动获取）

        Returns:
            List[str]: 需要重新分配的 portfolio_id 列表
        """
        try:
            if current_plan is None:
                current_plan = self.get_current_schedule_plan()

            healthy_node_ids = {n['node_id'] for n in healthy_nodes}

            orphaned = []
            for portfolio_id, node_id in current_plan.items():
                if node_id not in healthy_node_ids:
                    orphaned.append(portfolio_id)

            if orphaned:
                logger.warning(f"Orphan portfolios (node offline): {[p[:8] for p in orphaned]}")

                try:
                    from ginkgo.notifier.core.notification_service import notify

                    offline_nodes = set()
                    for portfolio_id in orphaned:
                        old_node = current_plan.get(portfolio_id)
                        if old_node and old_node != "__ORPHANED__":
                            offline_nodes.add(old_node)

                    notify(
                        f"检测到节点下线 - {len(offline_nodes)}个节点离线, {len(orphaned)}个Portfolio需要重新分配",
                        level="WARN",
                        module="Scheduler",
                        details={
                            "离线节点数": len(offline_nodes),
                            "离线节点": ", ".join(list(offline_nodes)[:5]),
                            "受影响Portfolio数": len(orphaned),
                            "需要重新分配": "是"
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to send node offline warning: {e}")

            return orphaned

        except Exception as e:
            logger.error(f"Failed to detect orphaned portfolios: {e}")
            return []

    def detect_deleted_portfolios(self, current_plan: Dict[str, str]) -> List[str]:
        """
        检测已删除的 Portfolio（调度计划中有，但数据库不存在的）

        Args:
            current_plan: 当前调度计划 {portfolio_id: node_id}

        Returns:
            List[str]: 需要从调度计划中移除的 portfolio_id 列表
        """
        try:
            all_portfolios = self._get_all_portfolios()
            existing_portfolio_ids = {p.uuid for p in all_portfolios}

            deleted = []
            for portfolio_id in current_plan.keys():
                if portfolio_id not in existing_portfolio_ids:
                    deleted.append(portfolio_id)

            if deleted:
                logger.warning(f"Deleted portfolios (removed from database): {[p[:8] for p in deleted]}")

            return deleted

        except Exception as e:
            logger.error(f"Failed to detect deleted portfolios: {e}")
            return []

    def discover_new_portfolios(self, current_plan: Dict[str, str]) -> List[str]:
        """
        发现新的 live portfolio（从数据库中查找 is_live=True 但不在调度计划中的）

        Args:
            current_plan: 当前调度计划 {portfolio_id: node_id}

        Returns:
            List[str]: 需要分配的 portfolio_id 列表
        """
        try:
            all_portfolios = self._get_all_portfolios()

            if not all_portfolios:
                return []

            assigned_ids = set(current_plan.keys())
            new_portfolios = [p.uuid for p in all_portfolios if p.uuid not in assigned_ids]

            if new_portfolios:
                logger.info(f"New portfolios: {[p[:8] for p in new_portfolios]}")

            return new_portfolios

        except Exception as e:
            logger.error(f"Failed to discover new portfolios: {e}")
            return []

    def get_all_portfolios(self) -> List[Dict]:
        """
        获取所有 live Portfolio

        Returns:
            List[Dict]: Portfolio 列表
        """
        return self._get_all_portfolios()

    @staticmethod
    def _get_all_portfolios() -> List[Dict]:
        """获取所有 live Portfolio（静态方法便于测试）"""
        try:
            from ginkgo import services

            portfolio_service = services.data.portfolio_service()
            result = portfolio_service.get(is_live=True)

            if result.success:
                return result.data
            else:
                logger.error(f"Failed to get portfolios: {result.message}")
                return []

        except Exception as e:
            logger.error(f"Failed to get portfolios: {e}")
            return []
