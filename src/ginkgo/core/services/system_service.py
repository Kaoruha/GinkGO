"""
System Service - 系统状态和基础设施管理服务

提供系统状态检查、基础设施健康检查、模块状态管理、Worker状态管理等功能。
"""

from typing import Dict, Any, List
from time import time

from ginkgo.libs.core.config import GCONF
from ginkgo.libs import GLOG


class SystemService:
    """
    系统服务 - 管理系统状态、基础设施健康检查和模块状态

    职责：
    - 获取系统运行状态（版本、运行时间、调试模式）
    - 检查基础设施健康状态（MySQL、Redis、Kafka、ClickHouse）
    - 获取各模块容器加载状态
    - 获取所有Worker/组件状态
    """

    VERSION = "0.11.0"
    _start_time = time()

    def __init__(self):
        """初始化系统服务"""
        self._service_name = "SystemService"

    def get_system_status(self) -> Dict[str, Any]:
        """
        获取系统整体状态

        Returns:
            Dict: 包含系统状态、版本、运行时间、模块状态、基础设施状态
        """
        try:
            uptime = time() - SystemService._start_time

            return {
                "status": "running",
                "version": SystemService.VERSION,
                "uptime": f"{int(uptime // 3600)}h {int((uptime % 3600) // 60)}m",
                "modules": self._get_module_status(),
                "infrastructure": self._check_infrastructure(),
                "debug_mode": GCONF.DEBUGMODE,
            }
        except Exception as e:
            GLOG.ERROR(f"Failed to get system status: {e}")
            return {"status": "error", "version": SystemService.VERSION, "error": str(e)}

    def get_workers_status(self) -> Dict[str, Any]:
        """
        获取所有Worker/组件状态

        Returns:
            Dict: 包含 data, components 字段
        """
        try:
            from ginkgo import service_hub
            redis_service = service_hub.data.redis_service()
            if not redis_service:
                return {"data": [], "components": {}}

            result = redis_service.get_all_components_status()
            if not result.success:
                return {"data": [], "components": {}, "error": result.error}

            components = result.data
            workers = self._format_workers(components)
            counts = self._count_components(components)

            return {"data": workers, "components": counts}
        except Exception as e:
            GLOG.ERROR(f"Failed to get workers status: {e}")
            return {"data": [], "components": {}}

    def get_infrastructure_status(self) -> Dict[str, Any]:
        """获取基础设施状态"""
        return self._check_infrastructure()

    def get_module_status(self) -> Dict[str, Any]:
        """获取模块加载状态"""
        return self._get_module_status()

    # ===== Worker 数据格式化 =====

    def _format_workers(self, components: Dict[str, Any]) -> List[Dict[str, Any]]:
        """将组件数据格式化为统一的Worker列表"""
        workers = []

        # DataWorker
        for w in components.get("data_workers", []):
            workers.append({
                "id": w.get("worker_id", "unknown"),
                "type": "data_worker",
                "status": w.get("status", "unknown"),
                "task_count": w.get("task_count", 0),
                "last_heartbeat": w.get("last_heartbeat", ""),
            })

        # BacktestWorker
        for w in components.get("backtest_workers", []):
            workers.append({
                "id": w.get("worker_id", "unknown"),
                "type": "backtest_worker",
                "status": w.get("status", "unknown"),
                "task_count": w.get("active_tasks", 0),
                "max_tasks": w.get("max_tasks", 0),
                "last_heartbeat": w.get("last_heartbeat", ""),
            })

        # ExecutionNode
        for w in components.get("execution_nodes", []):
            workers.append({
                "id": w.get("node_id", "unknown"),
                "type": "execution_node",
                "status": w.get("status", "unknown"),
                "portfolio_count": w.get("active_portfolios", 0),
                "last_heartbeat": w.get("last_heartbeat", ""),
            })

        # Scheduler
        for w in components.get("schedulers", []):
            workers.append({
                "id": w.get("node_id", "unknown"),
                "type": "scheduler",
                "status": w.get("status", "unknown"),
                "running_tasks": w.get("running_tasks", 0),
                "pending_tasks": w.get("pending_tasks", 0),
                "last_heartbeat": w.get("last_heartbeat", ""),
            })

        # TaskTimer
        for w in components.get("task_timers", []):
            workers.append({
                "id": w.get("node_id", "unknown"),
                "type": "task_timer",
                "status": w.get("status", "unknown"),
                "jobs_count": w.get("jobs_count", 0),
                "last_heartbeat": w.get("last_heartbeat", ""),
            })

        return workers

    def _count_components(self, components: Dict[str, Any]) -> Dict[str, int]:
        """统计各类型组件数量"""
        return {
            "data_workers": len(components.get("data_workers", [])),
            "backtest_workers": len(components.get("backtest_workers", [])),
            "execution_nodes": len(components.get("execution_nodes", [])),
            "schedulers": len(components.get("schedulers", [])),
            "task_timers": len(components.get("task_timers", [])),
        }

    # ===== 模块状态 =====

    def _get_module_status(self) -> Dict[str, Any]:
        """获取所有模块的加载状态"""
        from ginkgo import service_hub

        status = {}
        for module_name in ['data', 'trading', 'core', 'ml', 'features', 'notifier',
                           'research', 'validation', 'paper', 'comparison', 'optimization']:
            try:
                module = getattr(service_hub, module_name, None)
                if module is not None:
                    status[module_name] = {
                        'available': True,
                        'type': type(module).__name__,
                        'error': None,
                        'cached': module_name in service_hub._module_cache,
                        'load_time': service_hub._performance_stats.get(module_name, {}).get('load_time', 0.0)
                    }
                else:
                    status[module_name] = {
                        'available': False,
                        'type': None,
                        'error': service_hub._module_errors.get(module_name, '未知错误'),
                        'cached': False,
                        'load_time': 0.0
                    }
            except Exception as e:
                status[module_name] = {
                    'available': False,
                    'type': None,
                    'error': str(e),
                    'cached': False,
                    'load_time': 0.0
                }
        return status

    # ===== 基础设施检查 =====

    def _check_infrastructure(self) -> Dict[str, Any]:
        """检查所有基础设施组件的健康状态"""
        return {
            "mysql": self._check_mysql(),
            "redis": self._check_redis(),
            "kafka": self._check_kafka(),
            "clickhouse": self._check_clickhouse(),
        }

    def _check_mysql(self) -> Dict[str, Any]:
        """检查 MySQL 连接状态"""
        try:
            from ginkgo import service_hub
            start = time()
            stockinfo_service = service_hub.data.stockinfo_service()
            stockinfo_service.count()
            latency = int((time() - start) * 1000)
            return {"status": "connected", "latency_ms": latency}
        except Exception as e:
            return {"status": "error", "error": str(e)[:50]}

    def _check_redis(self) -> Dict[str, Any]:
        """检查 Redis 连接状态"""
        try:
            from ginkgo import service_hub
            start = time()
            redis_service = service_hub.data.redis_service()
            redis_service.ping()
            latency = int((time() - start) * 1000)
            return {"status": "connected", "latency_ms": latency}
        except Exception as e:
            return {"status": "error", "error": str(e)[:50]}

    def _check_kafka(self) -> Dict[str, Any]:
        """检查 Kafka 连接状态"""
        try:
            from kafka import KafkaConsumer
            consumer = KafkaConsumer(
                bootstrap_servers=[f"{GCONF.KAFKAHOST}:{GCONF.KAFKAPORT}"],
                request_timeout_ms=5000,
                api_version_auto_timeout_ms=5000
            )
            topics = consumer.topics()
            consumer.close()
            return {"status": "connected", "topics": len(topics) if topics else 0}
        except Exception as e:
            return {"status": "error", "error": str(e)[:50]}

    def _check_clickhouse(self) -> Dict[str, Any]:
        """检查 ClickHouse 连接状态"""
        try:
            from ginkgo import service_hub
            bar_crud = service_hub.data.cruds.bar()
            return {"status": "connected"} if bar_crud else {"status": "not_configured"}
        except Exception as e:
            return {"status": "error", "error": str(e)[:50]}
