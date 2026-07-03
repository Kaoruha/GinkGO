# Upstream: client/deploy_cli, api/deployment, api/saga_transaction, tests
# Downstream: DeploymentService (trading/services), data/containers (依赖获取)
# Role: trading 层依赖注入容器，管理交易相关服务的实例化

from dependency_injector import containers, providers


class TradingContainer(containers.DeclarativeContainer):
    deployment_service = providers.Singleton(object)


trading_container = TradingContainer()

_deployment_service_instance = None


def _make_capacity_checker():
    """#4800: 构造集群容量预检 callable，供 DeploymentService.deploy 早失败用。

    复用 RedisService.get_execution_node_status()（data 层公共 API）聚合可用槽位。
    lazy import Scheduler.MAX_PORTFOLIOS_PER_NODE 保证与 LoadBalancer 容量阈值同源。
    Redis 不可用等异常时 fail-open（available_slots=1），不因基础设施故障阻塞 deploy。
    """

    def _check():
        try:
            from ginkgo.data.containers import container
            from ginkgo.livecore.scheduler.scheduler import Scheduler

            redis_svc = container.redis_service()
            result = redis_svc.get_execution_node_status()
            nodes = result.data if (result and result.success and result.data) else []
            # 仅计 running 节点（stale 视为不可用）
            healthy = [n for n in nodes if n.get("status") == "running"]
            max_per = Scheduler.MAX_PORTFOLIOS_PER_NODE
            total = len(healthy) * max_per
            used = sum(int(n.get("active_portfolios", 0)) for n in healthy)
            return {
                "healthy_nodes": len(healthy),
                "max_per_node": max_per,
                "total_slots": total,
                "used_slots": used,
                "available_slots": total - used,
            }
        except Exception:
            # Redis 不可用 / scheduler import 失败: 容量未知，fail-open 不阻塞 deploy
            return {
                "healthy_nodes": 0,
                "max_per_node": 0,
                "total_slots": 0,
                "used_slots": 0,
                "available_slots": 1,
            }

    return _check


def _get_deployment_service():
    """Lazy factory for DeploymentService."""
    global _deployment_service_instance
    if _deployment_service_instance is None:
        from ginkgo.data.containers import container
        from ginkgo.trading.services.deployment_service import DeploymentService

        _deployment_service_instance = DeploymentService(
            portfolio_service=container.portfolio_service(),
            mapping_service=container.portfolio_mapping_service(),
            file_service=container.file_service(),
            deployment_crud=container.deployment_crud(),
            broker_instance_crud=container.broker_instance_crud(),
            live_account_service=container.live_account_service(),
            mongo_driver=container.mongo_driver(),
            param_crud=container.cruds.param(),
            # #4800: 注入集群容量预检（防 paper worker 容量满时 deploy 假成功）
            capacity_checker=_make_capacity_checker(),
        )
    return _deployment_service_instance


trading_container.deployment_service.override(
    providers.Singleton(_get_deployment_service)
)
