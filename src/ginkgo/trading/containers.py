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

    数据源与 LoadBalancer.assign_portfolios 同源: 经 HeartbeatChecker 读
    `node:metrics:{id}` Hash 的 `portfolio_count`（load_balancer.py:73,80,82 即此值）。

    注意: 不能用 RedisService.get_execution_node_status() —— 该方法从心跳键
    `heartbeat:node:{id}` 取 active_portfolios，但执行节点心跳键只存裸 ISO 时间戳
    （heartbeat_manager.py:194 setex 直存非 JSON），parse_heartbeat_data 走 {"raw": data}
    分支，active_portfolios 恒为 0，致 used_slots 恒 0、满载集群也放行（review #6568
    指出的 #4800 假成功根因）。真容量数据写在另一 Hash node:metrics:{id}，LoadBalancer
    一直读的就是它。

    lazy import Scheduler.MAX_PORTFOLIOS_PER_NODE 保证与 LoadBalancer 容量阈值同源。
    Redis 不可用等异常时 fail-open（available_slots=1），不因基础设施故障阻塞 deploy。
    """

    def _check():
        try:
            from ginkgo.data.containers import container
            from ginkgo.livecore.scheduler.heartbeat import HeartbeatChecker
            from ginkgo.livecore.scheduler.scheduler import Scheduler

            # 与 LoadBalancer 同源: HeartbeatChecker.get_healthy_nodes() 返回
            # [{node_id, metrics:{portfolio_count, queue_size, cpu_usage}}]，
            # 读 node:metrics:{id} Hash（非心跳键的 active_portfolios）。
            redis_client = container.redis_service().redis
            healthy_nodes = HeartbeatChecker(redis_client).get_healthy_nodes()

            max_per = Scheduler.MAX_PORTFOLIOS_PER_NODE
            total = len(healthy_nodes) * max_per
            used = sum(
                int(n.get("metrics", {}).get("portfolio_count", 0))
                for n in healthy_nodes
            )
            return {
                "healthy_nodes": len(healthy_nodes),
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
