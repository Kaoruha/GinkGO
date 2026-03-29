"""
负载均衡算法模块

纯算法模块，接收 (healthy_nodes, current_plan, orphaned_portfolios)
返回新的调度计划。不依赖 Redis/Kafka，便于独立单元测试。
"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

ORPHANED_MARKER = "__ORPHANED__"


class LoadBalancer:
    """Portfolio 负载均衡分配器"""

    def __init__(self, max_portfolios_per_node: int = 5):
        self.max_portfolios_per_node = max_portfolios_per_node

    def assign_portfolios(
        self,
        healthy_nodes: List[Dict],
        current_plan: Dict[str, str],
        orphaned_portfolios: List[str],
    ) -> Dict[str, str]:
        """
        负载均衡算法：分配 Portfolio 到 ExecutionNode

        策略：
        1. 保留当前已有的分配（除非 Node 离线）
        2. 优先分配到负载最低的 Node
        3. 每个 Node 最多运行 max_portfolios_per_node 个 Portfolio
        4. 如果没有可用 Node，标记为孤儿

        Args:
            healthy_nodes: 健康的 Node 列表
            current_plan: 当前调度计划 {portfolio_id: node_id}
            orphaned_portfolios: 需要重新分配的 portfolio_id 列表

        Returns:
            Dict: 新的调度计划 {portfolio_id: node_id}
        """
        new_plan = {}

        # 1. 保留当前健康的分配
        healthy_node_ids = {n['node_id'] for n in healthy_nodes}
        for portfolio_id, node_id in current_plan.items():
            if node_id == ORPHANED_MARKER:
                continue
            if node_id in healthy_node_ids:
                new_plan[portfolio_id] = node_id

        # 2. 重新分配孤儿 Portfolio
        if orphaned_portfolios:
            if not healthy_nodes:
                for portfolio_id in orphaned_portfolios:
                    new_plan[portfolio_id] = ORPHANED_MARKER
                    logger.warning(
                        f"Portfolio {portfolio_id[:8]}... marked as orphaned "
                        f"(waiting for available node)"
                    )
                return new_plan

            # 按负载排序（负载低的优先）
            sorted_nodes = sorted(
                healthy_nodes,
                key=lambda n: n['metrics']['portfolio_count']
            )

            for portfolio_id in orphaned_portfolios:
                assigned = False
                for node in sorted_nodes:
                    node_id = node['node_id']
                    portfolio_count = node['metrics']['portfolio_count']

                    if portfolio_count < self.max_portfolios_per_node:
                        new_plan[portfolio_id] = node_id
                        assigned = True
                        node['metrics']['portfolio_count'] += 1
                        break

                if not assigned:
                    logger.warning(
                        f"No available node for portfolio {portfolio_id[:8]}... "
                        f"(all {len(healthy_nodes)} nodes at max capacity {self.max_portfolios_per_node})"
                    )

            # 发送负载均衡完成通知
            try:
                from ginkgo.notifier.core.notification_service import notify

                portfolio_distribution = {}
                for node_id in [n['node_id'] for n in healthy_nodes]:
                    count = sum(1 for pid in new_plan.values() if pid == node_id)
                    portfolio_distribution[node_id] = count

                notify(
                    f"负载均衡完成 - {len(orphaned_portfolios)}个Portfolio已重新分配",
                    level="INFO",
                    module="Scheduler",
                    details={
                        "重新分配数": len(orphaned_portfolios),
                        "可用节点数": len(healthy_nodes),
                        "负载分布": str(portfolio_distribution)
                    }
                )
            except Exception as e:
                logger.warning(f"Failed to send load balancing notification: {e}")

        return new_plan

    @staticmethod
    def get_plan_changes(
        old_plan: Dict[str, str],
        new_plan: Dict[str, str],
    ) -> Dict[str, tuple]:
        """
        比较新旧调度计划的变化

        Args:
            old_plan: 旧计划 {portfolio_id: node_id}
            new_plan: 新计划 {portfolio_id: node_id}

        Returns:
            Dict: 变化字典 {portfolio_id: (old_node_id, new_node_id)}
        """
        changes = {}
        all_portfolio_ids = set(old_plan.keys()) | set(new_plan.keys())

        for portfolio_id in all_portfolio_ids:
            old_node = old_plan.get(portfolio_id)
            new_node = new_plan.get(portfolio_id)

            if old_node != new_node:
                changes[portfolio_id] = (old_node, new_node)

        return changes
