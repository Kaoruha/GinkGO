"""
Pytest配置和共享fixtures for performance tests.
"""

import pytest
import psutil
import os
from typing import Dict, Any
from unittest.mock import Mock, patch


@pytest.fixture
def performance_monitor():
    """性能监控fixture."""
    class PerformanceMonitor:
        def __init__(self):
            self.process = psutil.Process(os.getpid())
            self.start_memory = None
            self.start_time = None

        def start(self):
            """开始监控."""
            self.start_memory = self.get_memory_usage()
            self.start_time = self.get_time()

        def stop(self) -> Dict[str, float]:
            """停止监控并返回统计."""
            return {
                "memory_delta": self.get_memory_usage() - self.start_memory,
                "time_delta": self.get_time() - self.start_time,
            }

        def get_memory_usage(self) -> float:
            """获取当前内存使用量(MB)."""
            return self.process.memory_info().rss / 1024 / 1024

        def get_time(self) -> float:
            """获取当前时间."""
            import time
            return time.perf_counter()

        def get_cpu_usage(self) -> float:
            """获取CPU使用率(%)."""
            return self.process.cpu_percent()

    return PerformanceMonitor()


@pytest.fixture
def benchmark_config() -> Dict[str, Any]:
    """性能基准测试配置."""
    return {
        "warmup_iterations": 3,
        "benchmark_iterations": 10,
        "concurrent_threads": 50,
        "max_startup_time_ms": 100,
        "max_memory_increase_mb": 50,
        "max_access_time_ms": 50,
    }


@pytest.fixture
def mock_service_hub():
    """Mock ServiceHub实例."""
    hub = Mock()
    hub.data = Mock()
    hub.list_available_modules = Mock(return_value=['data', 'trading', 'analysis'])
    hub.get_module_status = Mock(return_value={'data': 'active', 'trading': 'active'})
    hub.get_performance_stats = Mock(return_value={'uptime': 1000, 'calls': 100})
    hub.clear_cache = Mock()
    return hub


@pytest.fixture
def sample_backtest_config():
    """示例回测配置."""
    try:
        from ginkgo.backtest.execution.engines.config.backtest_config import BacktestConfig
        return BacktestConfig(name="Test", start_date="2023-01-01", end_date="2023-12-31")
    except ImportError:
        return None


def pytest_configure(config):
    """Pytest配置钩子."""
    # 注册自定义标记
    config.addinivalue_line("markers", "unit: 单元测试标记")
    config.addinivalue_line("markers", "integration: 集成测试标记")
    config.addinivalue_line("markers", "performance: 性能测试标记")
    config.addinivalue_line("markers", "benchmark: 基准测试标记")
    config.addinivalue_line("markers", "slow: 慢速测试标记")
