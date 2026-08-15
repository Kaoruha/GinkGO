"""
性能: 273MB RSS, 2.42s, 24 tests [PASS]
系统服务单元测试

测试 SystemService，验证系统状态获取、Worker 格式化、组件计数等功能。
使用 mock 隔离所有外部依赖（数据库、Redis、Kafka、service_hub）。
"""

import pytest
from unittest.mock import MagicMock, patch

from ginkgo.core.services.system_service import SystemService


# ── SystemService 构造测试 ──────────────────────────────────────────


@pytest.mark.unit
class TestSystemServiceConstruction:
    """SystemService 构造测试"""

    def test_construction(self):
        """正常构造"""
        service = SystemService()
        assert service._service_name == "SystemService"

    def test_version_attribute(self):
        """版本号属性"""
        assert hasattr(SystemService, "VERSION")
        assert isinstance(SystemService.VERSION, str)

    def test_start_time_attribute(self):
        """启动时间属性"""
        assert hasattr(SystemService, "_start_time")


# ── SystemService 系统状态测试 ──────────────────────────────────────


@pytest.mark.unit
class TestSystemServiceStatus:
    """SystemService 系统状态测试"""

    def test_get_system_status_success(self):
        """成功获取系统状态"""
        service = SystemService()

        # mock 内部方法
        service._get_module_status = MagicMock(return_value={"data": True})
        service._check_infrastructure = MagicMock(return_value={"mysql": "ok"})

        with patch("ginkgo.core.services.system_service.GCONF") as mock_conf:
            type(mock_conf).DEBUGMODE = MagicMock(return_value=False)
            status = service.get_system_status()

        assert status["status"] == "running"
        assert "version" in status
        assert "uptime" in status
        assert "modules" in status
        assert "infrastructure" in status
        assert "debug_mode" in status

    def test_get_system_status_with_exception(self):
        """获取系统状态异常"""
        service = SystemService()

        def raise_error():
            raise RuntimeError("test error")

        service._get_module_status = raise_error
        service._check_infrastructure = raise_error

        with patch("ginkgo.core.services.system_service.GCONF") as mock_conf:
            type(mock_conf).DEBUGMODE = MagicMock(return_value=False)
            status = service.get_system_status()

        assert status["status"] == "error"
        assert "error" in status


# ── SystemService Worker 状态测试 ───────────────────────────────────


@pytest.mark.unit
class TestSystemServiceWorkers:
    """SystemService Worker 状态测试"""

    def test_get_workers_status_no_redis_service(self):
        """无 Redis 服务时返回空列表"""
        service = SystemService()
        mock_redis_service = MagicMock()
        mock_redis_service.return_value = None
        with patch("ginkgo.service_hub") as mock_hub:
            mock_hub.data.redis_service = mock_redis_service
            result = service.get_workers_status()
        assert result["data"] == []
        assert result["components"] == {}

    def test_get_workers_status_redis_error(self):
        """Redis 服务失败时返回空列表"""
        service = SystemService()
        mock_redis_service = MagicMock()
        mock_redis_service.return_value = None
        with patch("ginkgo.service_hub") as mock_hub:
            mock_hub.data.redis_service = mock_redis_service
            result = service.get_workers_status()
        # redis_service 为 None 时返回空
        assert result["data"] == []

    def test_get_workers_status_success(self):
        """成功获取 Worker 状态"""
        service = SystemService()
        with patch("ginkgo.service_hub") as mock_hub:
            # 构建返回对象
            mock_redis = MagicMock()
            mock_status_result = MagicMock()
            mock_status_result.success = True
            mock_status_result.data = {
                "data_workers": [
                    {"worker_id": "dw-1", "status": "running", "task_count": 5, "last_heartbeat": "2024-01-01"}
                ],
                "backtest_workers": [
                    {"worker_id": "bw-1", "status": "running", "active_tasks": 2, "max_tasks": 4, "last_heartbeat": "2024-01-01"}
                ],
                "execution_nodes": [
                    {"node_id": "en-1", "status": "running", "active_portfolios": 3, "last_heartbeat": "2024-01-01"}
                ],
                "schedulers": [
                    {"node_id": "sc-1", "status": "running", "running_tasks": 1, "pending_tasks": 2, "last_heartbeat": "2024-01-01"}
                ],
                "task_timers": [
                    {"node_id": "tt-1", "status": "running", "jobs_count": 5, "last_heartbeat": "2024-01-01"}
                ],
            }
            mock_redis.get_all_components_status.return_value = mock_status_result
            mock_hub.data.redis_service.return_value = mock_redis
            result = service.get_workers_status()

        assert len(result["data"]) == 5
        assert result["components"]["data_workers"] == 1
        assert result["components"]["backtest_workers"] == 1
        assert result["components"]["execution_nodes"] == 1
        assert result["components"]["schedulers"] == 1
        assert result["components"]["task_timers"] == 1


# ── SystemService 格式化测试 ────────────────────────────────────────


@pytest.mark.unit
class TestSystemServiceFormatting:
    """SystemService 数据格式化测试"""

    def test_format_workers_empty(self):
        """空组件列表"""
        service = SystemService()
        workers = service._format_workers({})
        assert workers == []

    def test_format_workers_data_worker(self):
        """DataWorker 格式化"""
        service = SystemService()
        components = {
            "data_workers": [
                {
                    "worker_id": "dw-1",
                    "status": "running",
                    "task_count": 10,
                    "last_heartbeat": "2024-01-01T00:00:00",
                }
            ]
        }
        workers = service._format_workers(components)
        assert len(workers) == 1
        assert workers[0]["id"] == "dw-1"
        assert workers[0]["type"] == "data_worker"
        assert workers[0]["status"] == "running"
        assert workers[0]["task_count"] == 10

    def test_format_workers_backtest_worker(self):
        """BacktestWorker 格式化"""
        service = SystemService()
        components = {
            "backtest_workers": [
                {
                    "worker_id": "bw-1",
                    "status": "running",
                    "active_tasks": 2,
                    "max_tasks": 4,
                    "last_heartbeat": "2024-01-01",
                }
            ]
        }
        workers = service._format_workers(components)
        assert workers[0]["type"] == "backtest_worker"
        assert workers[0]["task_count"] == 2
        assert workers[0]["max_tasks"] == 4

    def test_format_workers_execution_node(self):
        """ExecutionNode 格式化"""
        service = SystemService()
        components = {
            "execution_nodes": [
                {
                    "node_id": "en-1",
                    "status": "running",
                    "active_portfolios": 3,
                    "last_heartbeat": "2024-01-01",
                }
            ]
        }
        workers = service._format_workers(components)
        assert workers[0]["type"] == "execution_node"
        assert workers[0]["portfolio_count"] == 3

    def test_format_workers_missing_fields(self):
        """缺失字段使用默认值"""
        service = SystemService()
        components = {
            "data_workers": [{"worker_id": "dw-1"}]  # 缺少其他字段
        }
        workers = service._format_workers(components)
        assert workers[0]["status"] == "unknown"
        assert workers[0]["task_count"] == 0

    def test_count_components(self):
        """组件计数"""
        service = SystemService()
        components = {
            "data_workers": [1, 2],
            "backtest_workers": [1],
            "execution_nodes": [],
            "schedulers": [1, 2, 3],
            "task_timers": [1],
        }
        counts = service._count_components(components)
        assert counts["data_workers"] == 2
        assert counts["backtest_workers"] == 1
        assert counts["execution_nodes"] == 0
        assert counts["schedulers"] == 3
        assert counts["task_timers"] == 1

    def test_count_components_empty(self):
        """空组件计数"""
        service = SystemService()
        counts = service._count_components({})
        assert counts["data_workers"] == 0


# ── SystemService 基础设施检查测试 ──────────────────────────────────


@pytest.mark.unit
class TestSystemServiceInfrastructure:
    """SystemService 基础设施检查测试"""

    def test_check_infrastructure_returns_all(self):
        """基础设施检查返回所有检查项"""
        service = SystemService()

        service._check_mysql = MagicMock(return_value={"status": "ok"})
        service._check_redis = MagicMock(return_value={"status": "ok"})
        service._check_kafka = MagicMock(return_value={"status": "ok"})
        service._check_clickhouse = MagicMock(return_value={"status": "ok"})

        result = service._check_infrastructure()
        assert "mysql" in result
        assert "redis" in result
        assert "kafka" in result
        assert "clickhouse" in result

    def test_check_mysql_error(self):
        """MySQL 检查错误"""
        service = SystemService()
        with patch("ginkgo.service_hub") as mock_hub:
            mock_hub.data.stockinfo_service.side_effect = Exception("connection refused")
            result = service._check_mysql()
        assert result["status"] == "error"
        assert "connection refused" in result["error"]

    def test_check_redis_error(self):
        """Redis 检查错误"""
        service = SystemService()
        with patch("ginkgo.service_hub") as mock_hub:
            mock_hub.data.redis_service.side_effect = Exception("connection refused")
            result = service._check_redis()
        assert result["status"] == "error"

    def test_check_clickhouse_error(self):
        """ClickHouse 检查错误"""
        service = SystemService()
        with patch("ginkgo.service_hub") as mock_hub:
            mock_hub.data.cruds.bar.side_effect = Exception("not configured")
            result = service._check_clickhouse()
        assert result["status"] == "error"

    def test_check_kafka_error(self):
        """Kafka 检查错误 - mock KafkaConsumer 抛出异常"""
        service = SystemService()
        with patch("ginkgo.core.services.system_service.GCONF") as mock_conf:
            type(mock_conf).KAFKAHOST = MagicMock(return_value="invalid_host")
            type(mock_conf).KAFKAPORT = MagicMock(return_value=1)
            with patch("kafka.KafkaConsumer") as mock_consumer_cls:
                mock_consumer_cls.side_effect = Exception("connection refused")
                result = service._check_kafka()
        assert result["status"] == "error"


# ── SystemService 模块状态测试 ─────────────────────────────────────


@pytest.mark.unit
class TestSystemServiceModuleStatus:
    """SystemService 模块状态测试"""

    def test_get_module_status(self):
        """获取模块加载状态"""
        service = SystemService()
        with patch("ginkgo.service_hub") as mock_hub:
            mock_hub._module_cache = {"data": True}
            mock_hub._module_errors = {}
            mock_hub._performance_stats = {}
            mock_hub.data = MagicMock()
            mock_hub.trading = MagicMock()
            mock_hub.core = MagicMock()
            mock_hub.ml = None
            mock_hub.features = None
            mock_hub.notifier = None
            mock_hub.research = None
            mock_hub.validation = None
            mock_hub.paper = None
            mock_hub.comparison = None
            mock_hub.optimization = None

            status = service._get_module_status()
        assert isinstance(status, dict)
        assert "data" in status

    def test_get_module_status_unavailable(self):
        """模块不可用时状态"""
        service = SystemService()
        with patch("ginkgo.service_hub") as mock_hub:
            mock_hub._module_cache = {}
            mock_hub._module_errors = {"data": "import error"}
            mock_hub._performance_stats = {}
            # 所有属性返回 None
            for attr in ['data', 'trading', 'core', 'ml', 'features', 'notifier',
                         'research', 'validation', 'paper', 'comparison', 'optimization']:
                setattr(mock_hub, attr, None)

            status = service._get_module_status()
        assert "data" in status
        assert status["data"]["available"] is False

    def test_get_module_status_public_method(self):
        """公开方法调用内部方法"""
        service = SystemService()
        service._get_module_status = MagicMock(return_value={"mock": True})
        result = service.get_module_status()
        assert result == {"mock": True}

    def test_get_infrastructure_status_public_method(self):
        """公开方法调用内部方法"""
        service = SystemService()
        service._check_infrastructure = MagicMock(return_value={"mock": True})
        result = service.get_infrastructure_status()
        assert result == {"mock": True}


# ── SystemService 错误统计测试 (#6785) ────────────────────────────────


@pytest.mark.unit
class TestSystemServiceErrorStats:
    """SystemService 错误统计包装测试 (#6785)。

    GLOG.get_error_stats/clear_error_stats 已实现 (logger.py:519/538)，本切片在
    SystemService 暴露包装，供 API 层 /system/error-stats 端点走 Service 层调用。
    """

    def test_get_error_stats_returns_glog_stats(self):
        """get_error_stats 透传 GLOG.get_error_stats 的进程内错误统计。"""
        service = SystemService()
        glog_stats = {
            "total_error_patterns": 2,
            "top_error_patterns": [{"pattern_hash": "h1", "count": 3}],
            "total_error_count": 5,
        }
        with patch("ginkgo.core.services.system_service.GLOG.get_error_stats",
                   return_value=glog_stats) as mock_glog:
            result = service.get_error_stats()

        mock_glog.assert_called_once()
        assert result == glog_stats

    def test_reset_error_stats_clears_glog(self):
        """reset_error_stats 调 GLOG.clear_error_stats 清零进程内错误统计。"""
        service = SystemService()
        with patch("ginkgo.core.services.system_service.GLOG.clear_error_stats") as mock_clear:
            result = service.reset_error_stats()

        mock_clear.assert_called_once()
        assert result == {"reset": True}


# ── SystemService Worker 任务下钻测试 (#6910) ─────────────────────────


@pytest.mark.unit
class TestWorkerTasks:
    """get_worker_tasks + _format_workers 透传 task_uuids（Worker 管理页下钻）。"""

    def _heartbeat_components(self):
        return {
            "backtest_workers": [{
                "worker_id": "bw1", "status": "running", "running_tasks": 1,
                "max_tasks": 5, "last_heartbeat": "2026-08-15T10:00:00",
                "task_uuids": ["t-1", "t-2"],
            }],
        }

    def test_format_workers_passes_task_uuids(self):
        """_format_workers 不丢 task_uuids（此前被丢弃，下钻无数据源）。"""
        from ginkgo.core.services.system_service import SystemService
        svc = SystemService()
        workers = svc._format_workers(self._heartbeat_components())
        assert workers[0]["type"] == "backtest_worker"
        assert workers[0]["task_uuids"] == ["t-1", "t-2"]

    def test_get_worker_tasks_returns_task_details(self):
        """心跳 task_uuids → MySQL 任务明细（name/status/progress）。"""
        from ginkgo.core.services.system_service import SystemService

        task = MagicMock()
        task.task_id = "t-1"
        task.name = "bt-name"
        task.status = "running"
        task.progress = 42
        task.portfolio_id = "p-1"

        redis_svc = MagicMock()
        redis_svc.get_all_components_status.return_value = MagicMock(
            success=True, data=self._heartbeat_components())
        bw_status = MagicMock(success=True, data=[{
            "worker_id": "bw1", "status": "running", "active_tasks": 1,
            "max_tasks": 5, "last_heartbeat": "x", "task_uuids": ["t-1"],
        }])
        redis_svc.get_backtest_worker_status.return_value = bw_status

        task_svc = MagicMock()
        task_svc.get_by_task_id.return_value = MagicMock(success=True, data=task)

        svc = SystemService()
        with patch("ginkgo.service_hub") as hub, \
             patch("ginkgo.data.containers.container") as cont:
            hub.data.redis_service.return_value = redis_svc
            cont.backtest_task_service.return_value = task_svc
            result = svc.get_worker_tasks("bw1")

        assert result["found"] is True
        assert result["tasks"] == [{
            "task_id": "t-1", "name": "bt-name", "status": "running",
            "progress": 42, "portfolio_id": "p-1",
        }]

    def test_get_worker_tasks_unknown_worker(self):
        """未知 worker_id → found=False + 空 tasks（非异常）。"""
        from ginkgo.core.services.system_service import SystemService

        redis_svc = MagicMock()
        redis_svc.get_backtest_worker_status.return_value = MagicMock(
            success=True, data=[])

        svc = SystemService()
        with patch("ginkgo.service_hub") as hub:
            hub.data.redis_service.return_value = redis_svc
            result = svc.get_worker_tasks("nope")

        assert result == {"worker_id": "nope", "found": False, "tasks": []}

    def test_get_worker_tasks_orphan_uuid_still_listed(self):
        """心跳持有但 MySQL 无记录（任务刚结束）→ 仍列出，字段兜底。"""
        from ginkgo.core.services.system_service import SystemService

        redis_svc = MagicMock()
        redis_svc.get_backtest_worker_status.return_value = MagicMock(
            success=True, data=[{
                "worker_id": "bw1", "task_uuids": ["t-gone"],
                "status": "running", "active_tasks": 1,
                "max_tasks": 5, "last_heartbeat": "x",
            }])
        task_svc = MagicMock()
        task_svc.get_by_task_id.return_value = MagicMock(success=False, data=None)

        svc = SystemService()
        with patch("ginkgo.service_hub") as hub, \
             patch("ginkgo.data.containers.container") as cont:
            hub.data.redis_service.return_value = redis_svc
            cont.backtest_task_service.return_value = task_svc
            result = svc.get_worker_tasks("bw1")

        assert result["found"] is True
        assert result["tasks"] == [{
            "task_id": "t-gone", "name": "", "status": "unknown",
            "progress": 0, "portfolio_id": "",
        }]
