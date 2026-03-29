"""health_check.py 模块单元测试

测试健康检查工具中的纯逻辑函数。
注：check_clickhouse_ready / check_mysql_ready / check_redis_ready /
     check_mongo_ready / check_kafka_ready / check_docker_containers_running
     均依赖外部服务（网络/数据库/Docker），不适合纯函数测试，已跳过。

可测试内容：check_port_open（本地端口）和 wait_for_service / wait_for_services（用 mock check_func）。
"""

import pytest
import time
import socket
import threading
from ginkgo.libs.utils.health_check import (
    check_port_open,
    wait_for_service,
    wait_for_services,
    get_ginkgo_services_config,
)


# ============================================================
# check_port_open
# ============================================================
@pytest.mark.unit
class TestCheckPortOpen:
    """check_port_open 端口检查测试（使用本地临时端口）"""

    def _find_free_port(self):
        """找到一个空闲端口"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]

    def _start_tcp_server(self, port):
        """启动一个简单的 TCP 服务器用于测试"""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind(("127.0.0.1", port))
        server.listen(1)
        server.settimeout(2)
        return server

    def test_open_port_returns_true(self):
        """已开放的端口应返回 True"""
        port = self._find_free_port()
        server = self._start_tcp_server(port)
        try:
            assert check_port_open("127.0.0.1", port) is True
        finally:
            server.close()

    def test_closed_port_returns_false(self):
        """未开放的端口应返回 False"""
        port = self._find_free_port()
        # 确保端口未开放
        assert check_port_open("127.0.0.1", port) is False

    def test_localhost_with_standard_port(self):
        """检查 127.0.0.1 上的未开放端口"""
        # 选择一个非常高的端口号，几乎不可能开放
        assert check_port_open("127.0.0.1", 59999) is False

    def test_invalid_host_returns_false(self):
        """无效主机名应返回 False"""
        # 使用一个不可能解析的主机名
        assert check_port_open("this.host.does.not.exist.invalid", 80) is False


# ============================================================
# wait_for_service
# ============================================================
@pytest.mark.unit
class TestWaitForService:
    """wait_for_service 等待服务就绪测试"""

    def test_immediately_ready(self):
        """服务立即就绪"""
        call_count = 0

        def always_ready():
            nonlocal call_count
            call_count += 1
            return True

        result = wait_for_service(always_ready, "test-service", max_wait=5, check_interval=0.1)
        assert result is True
        assert call_count == 1

    def test_never_ready_timeout(self):
        """服务始终未就绪，超时返回 False"""
        def never_ready():
            return False

        start = time.time()
        result = wait_for_service(never_ready, "test-service", max_wait=1, check_interval=0.1)
        elapsed = time.time() - start
        assert result is False
        assert elapsed >= 1

    def test_ready_after_delay(self):
        """服务延迟后变为就绪"""
        attempt = 0

        def eventually_ready():
            nonlocal attempt
            attempt += 1
            return attempt >= 3

        result = wait_for_service(eventually_ready, "test-service", max_wait=5, check_interval=0.05)
        assert result is True
        assert attempt >= 3

    def test_check_func_exception_propagates(self):
        """检查函数抛异常时，异常会向上传播（源码未做 try-except）"""
        def failing_check():
            raise ConnectionError("connection failed")

        with pytest.raises(ConnectionError):
            wait_for_service(failing_check, "test-service", max_wait=1, check_interval=0.1)

    def test_zero_max_wait_returns_false_if_not_ready(self):
        """max_wait 为 0 时，如果未就绪应立即返回 False"""
        def not_ready():
            return False

        result = wait_for_service(not_ready, "test-service", max_wait=0, check_interval=0)
        assert result is False


# ============================================================
# wait_for_services
# ============================================================
@pytest.mark.unit
class TestWaitForServices:
    """wait_for_services 多服务等待测试"""

    def test_all_services_ready(self):
        """所有服务均就绪"""
        config = {
            "svc_a": {"check_function": lambda: True, "required": True},
            "svc_b": {"check_function": lambda: True, "required": True},
        }
        result = wait_for_services(config, max_wait=5)
        assert result is True

    def test_required_service_not_ready(self):
        """必需服务未就绪"""
        config = {
            "svc_a": {"check_function": lambda: False, "required": True},
        }
        result = wait_for_services(config, max_wait=1)
        assert result is False

    def test_optional_service_not_ready(self):
        """可选服务未就绪不影响整体"""
        config = {
            "svc_required": {"check_function": lambda: True, "required": True},
            "svc_optional": {"check_function": lambda: False, "required": False},
        }
        result = wait_for_services(config, max_wait=2)
        assert result is True

    def test_empty_config(self):
        """空配置直接返回 True"""
        result = wait_for_services({}, max_wait=1)
        assert result is True

    def test_mixed_required_and_optional(self):
        """混合必需和可选服务：slow_ready 在 3 次后变为就绪，sleep 间隔 3 秒"""
        attempt = 0

        def slow_ready():
            nonlocal attempt
            attempt += 1
            return attempt >= 2

        config = {
            "svc_slow": {"check_function": slow_ready, "required": True},
            "svc_opt": {"check_function": lambda: False, "required": False},
        }
        # wait_for_services 内部 sleep(3)，所以 max_wait 需要足够大
        result = wait_for_services(config, max_wait=10)
        assert result is True


# ============================================================
# get_ginkgo_services_config
# ============================================================
@pytest.mark.unit
class TestGetGinkgoServicesConfig:
    """get_ginkgo_services_config 服务配置获取测试"""

    def test_returns_dict(self):
        """应返回字典"""
        config = get_ginkgo_services_config()
        assert isinstance(config, dict)

    def test_contains_expected_services(self):
        """应包含预期的服务"""
        config = get_ginkgo_services_config()
        expected = {"ClickHouse", "MySQL", "Redis", "Kafka", "MongoDB"}
        assert set(config.keys()) == expected

    def test_each_config_has_required_fields(self):
        """每个服务配置应包含必要字段"""
        config = get_ginkgo_services_config()
        for name, cfg in config.items():
            assert "check_function" in cfg, f"{name} 缺少 check_function"
            assert "required" in cfg, f"{name} 缺少 required"
            assert callable(cfg["check_function"]), f"{name} 的 check_function 不可调用"
