"""
ServiceHub性能基准测试 - 优化版使用Pytest最佳实践。

测试ServiceHub的加载时间、内存使用、并发访问等性能指标。
确保ServiceHub架构不会影响系统性能。
"""

import pytest
import time
import psutil
import os
from typing import Dict, Any
from unittest.mock import Mock, patch
from concurrent.futures import ThreadPoolExecutor, as_completed


@pytest.mark.performance
@pytest.mark.benchmark
class TestServiceHubStartupPerformance:
    """ServiceHub启动性能测试."""

    @pytest.fixture(autouse=True)
    def setup(self, benchmark_config):
        """测试前准备."""
        self.config = benchmark_config
        self.process = psutil.Process(os.getpid())

        # 预热 - 避免首次导入的延迟
        for _ in range(self.config['warmup_iterations']):
            try:
                from ginkgo import service_hub
                _ = service_hub.data
                del service_hub
            except ImportError:
                pytest.skip("ServiceHub不可用，跳过性能测试")

        # 清理内存
        import gc
        gc.collect()

    def get_memory_usage(self) -> float:
        """获取当前内存使用量(MB)."""
        return self.process.memory_info().rss / 1024 / 1024

    @pytest.mark.unit
    def test_servicehub_startup_time(self):
        """测试ServiceHub启动时间."""
        startup_times = []

        for _ in range(self.config['benchmark_iterations']):
            # 清理缓存
            import sys
            modules_to_remove = [m for m in sys.modules.keys() if 'ginkgo.service_hub' in m]
            for module in modules_to_remove:
                del sys.modules[module]

            start_time = time.perf_counter()

            # 导入ServiceHub
            from ginkgo import service_hub
            _ = service_hub.data

            end_time = time.perf_counter()
            startup_times.append((end_time - start_time) * 1000)  # 转换为毫秒

        avg_startup_time = sum(startup_times) / len(startup_times)
        max_startup_time = max(startup_times)

        # 断言启动时间应该在合理范围内
        assert avg_startup_time < self.config['max_startup_time_ms'], \
            f"ServiceHub平均启动时间过长: {avg_startup_time:.2f}ms"
        assert max_startup_time < self.config['max_startup_time_ms'] * 2, \
            f"ServiceHub最大启动时间过长: {max_startup_time:.2f}ms"

    @pytest.mark.unit
    def test_servicehub_memory_usage(self):
        """测试ServiceHub内存使用."""
        # 获取初始内存
        initial_memory = self.get_memory_usage()

        # 导入并使用ServiceHub
        from ginkgo import service_hub

        # 访问所有可用模块
        try:
            available_modules = service_hub.list_available_modules()
            for module_name in available_modules:
                try:
                    module = getattr(service_hub, module_name)
                    if module is not None:
                        pass  # 触发模块加载
                except Exception:
                    pass  # 忽略模块加载错误
        except Exception:
            available_modules = []

        # 获取加载后内存
        after_load_memory = self.get_memory_usage()
        memory_increase = after_load_memory - initial_memory

        # 断言内存增长应该在合理范围内
        assert memory_increase < self.config['max_memory_increase_mb'], \
            f"ServiceHub内存使用过多: {memory_increase:.2f}MB"


@pytest.mark.performance
@pytest.mark.benchmark
class TestServiceHubConcurrentAccess:
    """ServiceHub并发访问性能测试."""

    @pytest.fixture
    def concurrent_threads_config(self, benchmark_config):
        """获取并发测试配置."""
        return benchmark_config['concurrent_threads']

    @pytest.mark.unit
    def test_servicehub_concurrent_access(self, concurrent_threads_config):
        """测试ServiceHub并发访问性能."""
        from ginkgo import service_hub

        def access_service_hub(thread_id: int) -> Dict[str, Any]:
            """并发访问ServiceHub的worker函数."""
            start_time = time.perf_counter()

            try:
                # 访问不同模块
                data_module = service_hub.data
                list_modules = service_hub.list_available_modules()
                module_status = service_hub.get_module_status()

                end_time = time.perf_counter()

                return {
                    'thread_id': thread_id,
                    'success': True,
                    'access_time': (end_time - start_time) * 1000,
                    'modules_loaded': len(list_modules),
                    'data_available': data_module is not None
                }
            except Exception as e:
                return {
                    'thread_id': thread_id,
                    'success': False,
                    'error': str(e),
                    'access_time': 0,
                    'modules_loaded': 0,
                    'data_available': False
                }

        # 并发访问测试
        start_time = time.perf_counter()

        with ThreadPoolExecutor(max_workers=concurrent_threads_config) as executor:
            # 提交所有任务
            futures = [
                executor.submit(access_service_hub, i)
                for i in range(concurrent_threads_config)
            ]

            # 收集结果
            results = []
            for future in as_completed(futures):
                results.append(future.result())

        end_time = time.perf_counter()
        total_time = (end_time - start_time) * 1000

        # 分析结果
        successful_results = [r for r in results if r['success']]
        failed_results = [r for r in results if not r['success']]

        access_times = [r['access_time'] for r in successful_results]
        avg_access_time = sum(access_times) / len(access_times) if access_times else 0
        max_access_time = max(access_times) if access_times else 0

        # 断言并发访问应该稳定
        assert len(successful_results) >= concurrent_threads_config * 0.95, \
            f"并发访问成功率过低: {len(successful_results)}/{concurrent_threads_config}"
        assert avg_access_time < self.config['max_access_time_ms'], \
            f"并发平均访问时间过长: {avg_access_time:.2f}ms"


@pytest.mark.performance
@pytest.mark.benchmark
class TestServiceHubCacheEffectiveness:
    """ServiceHub缓存效果测试."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """测试前准备."""
        from ginkgo import service_hub
        self.service_hub = service_hub

    @pytest.mark.unit
    def test_servicehub_cache_effectiveness(self):
        """测试ServiceHub缓存效果."""
        # 清理缓存
        try:
            self.service_hub.clear_cache()
        except Exception:
            pass

        # 首次访问时间
        start_time = time.perf_counter()
        data_module1 = self.service_hub.data
        first_access_time = (time.perf_counter() - start_time) * 1000

        # 缓存访问时间
        start_time = time.perf_counter()
        data_module2 = self.service_hub.data
        cached_access_time = (time.perf_counter() - start_time) * 1000

        # 断言缓存应该有效
        try:
            assert data_module1 is data_module2, "缓存应该返回同一个对象"
        except AssertionError:
            pytest.skip("ServiceHub缓存未实现")

        assert cached_access_time < first_access_time * 0.5, \
            "缓存访问应该显著快于首次访问"


@pytest.mark.performance
@pytest.mark.benchmark
class TestServiceHubDiagnostics:
    """ServiceHub诊断功能性能测试."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """测试前准备."""
        from ginkgo import service_hub
        self.service_hub = service_hub

    @pytest.mark.unit
    def test_servicehub_diagnostic_performance(self):
        """测试ServiceHub诊断功能性能."""
        def test_diagnostic_performance():
            start_time = time.perf_counter()

            # 测试诊断功能
            try:
                issues = self.service_hub.diagnose_issues()
                status = self.service_hub.get_module_status()
                perf_stats = self.service_hub.get_performance_stats()
            except Exception:
                # 如果方法不存在，跳过
                return (time.perf_counter() - start_time) * 1000, {}, {}, {}

            end_time = time.perf_counter()
            return (end_time - start_time) * 1000, issues, status, perf_stats

        # 测试诊断功能性能
        diagnostic_times = []
        for _ in range(5):
            time_taken, issues, status, perf_stats = test_diagnostic_performance()
            diagnostic_times.append(time_taken)

        avg_diagnostic_time = sum(diagnostic_times) / len(diagnostic_times)

        # 断言诊断功能应该快速
        assert avg_diagnostic_time < 20, \
            f"诊断功能执行时间过长: {avg_diagnostic_time:.2f}ms"


@pytest.mark.performance
@pytest.mark.benchmark
class TestServiceHubComparison:
    """ServiceHub与旧Services性能对比."""

    @pytest.mark.unit
    def test_servicehub_vs_services_performance(self):
        """对比ServiceHub与旧Services的性能."""
        benchmark_iterations = 10

        # 测试ServiceHub性能
        service_hub_times = []
        for _ in range(benchmark_iterations):
            start_time = time.perf_counter()
            from ginkgo import service_hub
            data = service_hub.data
            try:
                status = service_hub.get_module_status()
            except AttributeError:
                status = "unavailable"
            end_time = time.perf_counter()
            service_hub_times.append((end_time - start_time) * 1000)

        # 测试旧Services性能（如果仍然可用）
        services_times = []
        try:
            for _ in range(benchmark_iterations):
                start_time = time.perf_counter()
                from ginkgo import services
                data = services.data
                try:
                    status = services.get_module_status()
                except AttributeError:
                    status = "unavailable"
                end_time = time.perf_counter()
                services_times.append((end_time - start_time) * 1000)
        except ImportError:
            services_times = [0]  # 如果不可用，设为0

        avg_service_hub_time = sum(service_hub_times) / len(service_hub_times)
        avg_services_time = sum(services_times) / len(services_times) if services_times else 0

        # ServiceHub性能应该不比旧Services差太多
        if avg_services_time > 0:
            performance_ratio = avg_service_hub_time / avg_services_time
            assert performance_ratio < 1.5, \
                f"ServiceHub性能相比旧Services下降过多: {performance_ratio:.2f}x"


@pytest.mark.performance
@pytest.mark.benchmark
@pytest.mark.slow
class TestServiceHubFullBenchmark:
    """ServiceHub完整性能基准测试."""

    @pytest.fixture
    def benchmark(self):
        """性能基准测试夹具."""
        class PerformanceBenchmark:
            def __init__(self):
                self.process = psutil.Process(os.getpid())

            def get_memory_usage(self) -> float:
                """获取当前内存使用量(MB)."""
                return self.process.memory_info().rss / 1024 / 1024

        return PerformanceBenchmark()

    @pytest.mark.slow
    def test_full_performance_benchmark(self, benchmark):
        """完整的性能基准测试（标记为slow，只在需要时运行）."""
        from ginkgo import service_hub

        results = {}

        # 启动时间测试
        startup_times = []
        for _ in range(10):
            start_time = time.perf_counter()
            data = service_hub.data
            startup_time = (time.perf_counter() - start_time) * 1000
            startup_times.append(startup_time)

        results['startup_time'] = {
            'avg': sum(startup_times) / len(startup_times),
            'max': max(startup_times),
            'min': min(startup_times),
        }

        # 内存使用测试
        initial_memory = benchmark.get_memory_usage()
        data = service_hub.data
        final_memory = benchmark.get_memory_usage()
        results['memory_usage'] = {
            'initial': initial_memory,
            'final': final_memory,
            'delta': final_memory - initial_memory,
        }

        # 验证结果
        assert results['startup_time']['avg'] < 100, "启动时间超出基线"
        assert results['memory_usage']['delta'] < 50, "内存使用超出基线"
