# Upstream: API Server (ginkgo serve api), CLI (ginkgo status)
# Downstream: RedisService, stockinfo_service, KafkaConsumer, bar_crud, BacktestTaskService
# Role: 系统状态和基础设施健康检查(MySQL/Redis/Kafka/ClickHouse)

"""
System Service - 系统状态和基础设施管理服务

提供系统状态检查、基础设施健康检查、模块状态管理、Worker状态管理等功能。
"""

from typing import Dict, Any, List
from time import time

from ginkgo.libs.core.config import GCONF
from ginkgo.libs import GLOG
from ginkgo.libs.utils.version import get_version


class SystemService:
    """
    系统服务 - 管理系统状态、基础设施健康检查和模块状态

    职责：
    - 获取系统运行状态（版本、运行时间、调试模式）
    - 检查基础设施健康状态（MySQL、Redis、Kafka、ClickHouse）
    - 获取各模块容器加载状态
    - 获取所有Worker/组件状态
    """

    VERSION = get_version()
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
                "env": GCONF.ENV,
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

    def get_worker_tasks(self, worker_id: str) -> Dict[str, Any]:
        """
        获取回测 Worker 当前活跃任务详情（Worker 管理页行内下钻）。

        数据链路：心跳 BacktestWorkerHeartbeat.task_uuids (#6846) → MySQL
        backtest_task（task_id = task_uuid）。心跳持有但 MySQL 无记录的任务
        仍列出（字段兜底），避免"任务刚结束就消失"的闪断。
        """
        try:
            from ginkgo import service_hub
            from ginkgo.data.containers import container

            redis_service = service_hub.data.redis_service()
            if not redis_service:
                return {"worker_id": worker_id, "found": False, "tasks": []}

            bw_result = redis_service.get_backtest_worker_status()
            workers = (bw_result.data or []) if bw_result.success else []
            worker = next(
                (w for w in workers if w.get("worker_id") == worker_id), None)
            if worker is None:
                return {"worker_id": worker_id, "found": False, "tasks": []}

            task_service = container.backtest_task_service()
            tasks = []
            for task_uuid in worker.get("task_uuids") or []:
                r = task_service.get_by_task_id(task_uuid)
                if r.success and r.data is not None:
                    t = r.data
                    tasks.append({
                        "task_id": getattr(t, "task_id", task_uuid),
                        "name": getattr(t, "name", "") or "",
                        "status": getattr(t, "status", "unknown"),
                        "progress": getattr(t, "progress", 0),
                        "portfolio_id": getattr(t, "portfolio_id", ""),
                    })
                else:
                    tasks.append({
                        "task_id": task_uuid, "name": "", "status": "unknown",
                        "progress": 0, "portfolio_id": "",
                    })
            return {"worker_id": worker_id, "found": True, "tasks": tasks}
        except Exception as e:
            GLOG.ERROR(f"Failed to get worker tasks for {worker_id}: {e}")
            return {"worker_id": worker_id, "found": False, "tasks": []}

    def get_infrastructure_status(self) -> Dict[str, Any]:
        """获取基础设施状态"""
        return self._check_infrastructure()

    def get_module_status(self) -> Dict[str, Any]:
        """获取模块加载状态"""
        return self._get_module_status()

    # ===== 错误统计 (#6785) =====

    def get_error_stats(self) -> Dict[str, Any]:
        """获取进程内错误统计（透传 GLOG.get_error_stats）。

        #6785: GLOG 已在进程内累计错误模式统计 (logger.py:519)，本方法在 Service 层
        暴露，供 API /system/error-stats 端点查询当前 API 进程累计的错误热点。
        """
        return GLOG.get_error_stats()

    def reset_error_stats(self) -> Dict[str, Any]:
        """清零进程内错误统计（调 GLOG.clear_error_stats）。

        #6785: 排障后清零，便于观察新一轮错误分布。POST /system/error-stats/reset 调用。
        """
        GLOG.clear_error_stats()
        return {"reset": True}

    # ===== Worker 数据格式化 =====

    def _format_workers(self, components: Dict[str, Any]) -> List[Dict[str, Any]]:
        """将组件数据格式化为统一的Worker列表"""
        workers = []

        def _normalize_status(status: str) -> str:
            """统一 status 为小写字符串，兼容枚举格式如 WORKER_STATUS_TYPES.RUNNING"""
            if not status or status == "unknown":
                return "unknown"
            # 兼容 "WORKER_STATUS_TYPES.RUNNING" 格式，取最后一段
            if "." in status:
                status = status.split(".")[-1]
            return status.lower()

        # DataWorker
        for w in components.get("data_workers", []):
            workers.append({
                "id": w.get("worker_id", "unknown"),
                "type": "data_worker",
                "status": _normalize_status(w.get("status", "unknown")),
                "task_count": w.get("task_count", 0),
                "last_heartbeat": w.get("last_heartbeat", ""),
            })

        # BacktestWorker
        for w in components.get("backtest_workers", []):
            workers.append({
                "id": w.get("worker_id", "unknown"),
                "type": "backtest_worker",
                "status": _normalize_status(w.get("status", "unknown")),
                "task_count": w.get("active_tasks", 0),
                "max_tasks": w.get("max_tasks", 0),
                "last_heartbeat": w.get("last_heartbeat", ""),
                "task_uuids": w.get("task_uuids", []),
            })

        # ExecutionNode
        for w in components.get("execution_nodes", []):
            workers.append({
                "id": w.get("node_id", "unknown"),
                "type": "execution_node",
                "status": _normalize_status(w.get("status", "unknown")),
                "portfolio_count": w.get("active_portfolios", 0),
                "last_heartbeat": w.get("last_heartbeat", ""),
            })

        # Scheduler
        for w in components.get("schedulers", []):
            workers.append({
                "id": w.get("node_id", "unknown"),
                "type": "scheduler",
                "status": _normalize_status(w.get("status", "unknown")),
                "running_tasks": w.get("running_tasks", 0),
                "pending_tasks": w.get("pending_tasks", 0),
                "last_heartbeat": w.get("last_heartbeat", ""),
            })

        # TaskTimer
        for w in components.get("task_timers", []):
            workers.append({
                "id": w.get("node_id", "unknown"),
                "type": "task_timer",
                "status": _normalize_status(w.get("status", "unknown")),
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
                           'research', 'validation', 'comparison', 'optimization']:
            # 注：'paper' 已移除——ServiceHub 注册表无此模块（引擎统一后 paper 是部署模式非模块容器）
            try:
                module = getattr(service_hub, module_name, None)
                if module is not None:
                    status[module_name] = {
                        'available': True,
                        'type': type(module).__name__,
                        'error': None,
                        'cached': module_name in service_hub._module_cache,
                        # ServiceHub 重构后无 _performance_stats 属性（__getattr__ 对下划线开头直接 raise），
                        # 原 load_time 统计源已不存在，置 0 兜底（#933746 前模块加载成功反被判不可用）
                        'load_time': 0.0
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
                request_timeout_ms=5000
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
