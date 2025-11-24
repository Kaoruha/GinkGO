"""
ServiceHub性能基准测试

测试ServiceHub的加载时间、内存使用、并发访问等性能指标。
确保ServiceHub架构不会影响系统性能。
"""

import time
import threading
import pytest
import psutil
import os
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor, as_completed

# 测试配置
WARMUP_ITERATIONS = 3
BENCHMARK_ITERATIONS = 10
CONCURRENT_THREADS = 50


class TestServiceHubPerformance:
    """ServiceHub性能测试套件"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """测试前准备"""
        # 获取进程对象用于内存监控
        self.process = psutil.Process(os.getpid())

        # 预热 - 避免首次导入的延迟
        for _ in range(WARMUP_ITERATIONS):
            try:
                from ginkgo import service_hub
                # 访问主要模块触发加载
                _ = service_hub.data
                del service_hub
            except ImportError:
                pytest.skip("ServiceHub不可用，跳过性能测试")

        # 清理内存
        import gc
        gc.collect()

    def get_memory_usage(self) -> float:
        """获取当前内存使用量(MB)"""
        return self.process.memory_info().rss / 1024 / 1024

    def test_servicehub_startup_time(self):
        """测试ServiceHub启动时间"""
        startup_times = []

        for _ in range(BENCHMARK_ITERATIONS):
            # 清理缓存
            import sys
            modules_to_remove = [m for m in sys.modules.keys() if 'ginkgo.service_hub' in m]
            for module in modules_to_remove:
                del sys.modules[module]

            start_time = time.perf_counter()

            # 导入ServiceHub
            from ginkgo import service_hub

            # 触发主要模块加载
            _ = service_hub.data

            end_time = time.perf_counter()
            startup_times.append((end_time - start_time) * 1000)  # 转换为毫秒

        avg_startup_time = sum(startup_times) / len(startup_times)
        max_startup_time = max(startup_times)

        print(f"\nServiceHub启动性能:")
        print(f"  平均启动时间: {avg_startup_time:.2f}ms")
        print(f"  最大启动时间: {max_startup_time:.2f}ms")

        # 断言启动时间应该在合理范围内
        assert avg_startup_time < 100, f"ServiceHub平均启动时间过长: {avg_startup_time:.2f}ms"
        assert max_startup_time < 200, f"ServiceHub最大启动时间过长: {max_startup_time:.2f}ms"

    def test_servicehub_memory_usage(self):
        """测试ServiceHub内存使用"""
        # 获取初始内存
        initial_memory = self.get_memory_usage()

        # 导入并使用ServiceHub
        from ginkgo import service_hub

        # 访问所有可用模块
        available_modules = service_hub.list_available_modules()
        for module_name in available_modules:
            try:
                module = getattr(service_hub, module_name)
                if module is not None:
                    print(f"  已加载模块: {module_name}")
            except Exception as e:
                print(f"  模块加载失败 {module_name}: {e}")

        # 获取加载后内存
        after_load_memory = self.get_memory_usage()
        memory_increase = after_load_memory - initial_memory

        print(f"\nServiceHub内存使用:")
        print(f"  初始内存: {initial_memory:.2f}MB")
        print(f"  加载后内存: {after_load_memory:.2f}MB")
        print(f"  内存增长: {memory_increase:.2f}MB")

        # 断言内存增长应该在合理范围内 (<50MB)
        assert memory_increase < 50, f"ServiceHub内存使用过多: {memory_increase:.2f}MB"

    def test_servicehub_concurrent_access(self):
        """测试ServiceHub并发访问性能"""
        from ginkgo import service_hub

        def access_service_hub(thread_id: int) -> Dict[str, Any]:
            """并发访问ServiceHub的worker函数"""
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

        with ThreadPoolExecutor(max_workers=CONCURRENT_THREADS) as executor:
            # 提交所有任务
            futures = [
                executor.submit(access_service_hub, i)
                for i in range(CONCURRENT_THREADS)
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

        print(f"\nServiceHub并发访问测试:")
        print(f"  并发线程数: {CONCURRENT_THREADS}")
        print(f"  总测试时间: {total_time:.2f}ms")
        print(f"  成功访问: {len(successful_results)}/{len(results)}")
        print(f"  失败访问: {len(failed_results)}")
        print(f"  平均访问时间: {avg_access_time:.2f}ms")
        print(f"  最大访问时间: {max_access_time:.2f}ms")

        # 断言并发访问应该稳定
        assert len(successful_results) >= CONCURRENT_THREADS * 0.95, f"并发访问成功率过低: {len(successful_results)}/{CONCURRENT_THREADS}"
        assert avg_access_time < 50, f"并发平均访问时间过长: {avg_access_time:.2f}ms"
        assert max_access_time < 100, f"并发最大访问时间过长: {max_access_time:.2f}ms"

    def test_servicehub_cache_effectiveness(self):
        """测试ServiceHub缓存效果"""
        from ginkgo import service_hub

        # 清理缓存
        service_hub.clear_cache()

        # 首次访问时间
        start_time = time.perf_counter()
        data_module1 = service_hub.data
        first_access_time = (time.perf_counter() - start_time) * 1000

        # 缓存访问时间
        start_time = time.perf_counter()
        data_module2 = service_hub.data
        cached_access_time = (time.perf_counter() - start_time) * 1000

        print(f"\nServiceHub缓存效果:")
        print(f"  首次访问时间: {first_access_time:.2f}ms")
        print(f"  缓存访问时间: {cached_access_time:.2f}ms")
        print(f"  性能提升: {(first_access_time / cached_access_time) if cached_access_time > 0 else 0:.1f}x")

        # 断言缓存应该有效
        assert data_module1 is data_module2, "缓存应该返回同一个对象"
        assert cached_access_time < first_access_time * 0.5, "缓存访问应该显著快于首次访问"

    def test_servicehub_error_handling_performance(self):
        """测试ServiceHub错误处理性能"""
        from ginkgo import service_hub

        def test_diagnostic_performance():
            start_time = time.perf_counter()

            # 测试诊断功能
            issues = service_hub.diagnose_issues()
            status = service_hub.get_module_status()
            perf_stats = service_hub.get_performance_stats()

            end_time = time.perf_counter()
            return (end_time - start_time) * 1000, issues, status, perf_stats

        # 测试诊断功能性能
        diagnostic_times = []
        for _ in range(5):
            time_taken, issues, status, perf_stats = test_diagnostic_performance()
            diagnostic_times.append(time_taken)

        avg_diagnostic_time = sum(diagnostic_times) / len(diagnostic_times)

        print(f"\nServiceHub诊断功能性能:")
        print(f"  平均诊断时间: {avg_diagnostic_time:.2f}ms")
        print(f"  发现问题数: {len(issues)}")
        print(f"  模块状态数: {len(status)}")

        # 断言诊断功能应该快速
        assert avg_diagnostic_time < 20, f"诊断功能执行时间过长: {avg_diagnostic_time:.2f}ms"

    def test_servicehub_vs_services_performance_comparison(self):
        """对比ServiceHub与旧Services的性能"""
        # 测试ServiceHub性能
        service_hub_times = []
        for _ in range(BENCHMARK_ITERATIONS):
            start_time = time.perf_counter()
            from ginkgo import service_hub
            data = service_hub.data
            status = service_hub.get_module_status()
            end_time = time.perf_counter()
            service_hub_times.append((end_time - start_time) * 1000)

        # 测试旧Services性能（如果仍然可用）
        services_times = []
        try:
            for _ in range(BENCHMARK_ITERATIONS):
                start_time = time.perf_counter()
                from ginkgo import services
                data = services.data
                # 旧Services可能没有get_module_status方法
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

        print(f"\nServiceHub vs Services性能对比:")
        print(f"  ServiceHub平均时间: {avg_service_hub_time:.2f}ms")
        if avg_services_time > 0:
            print(f"  Services平均时间: {avg_services_time:.2f}ms")
            performance_ratio = avg_service_hub_time / avg_services_time
            print(f"  性能比率 (Hub/Services): {performance_ratio:.2f}")

            # ServiceHub性能应该不比旧Services差太多
            assert performance_ratio < 1.5, f"ServiceHub性能相比旧Services下降过多: {performance_ratio:.2f}x"
        else:
            print("  Services不可用，跳过对比")


@pytest.mark.performance
class TestServiceHubPerformanceRegression:
    """ServiceHub性能回归测试"""

    def test_performance_baseline(self):
        """建立性能基线"""
        # 这个测试用于建立性能基线，后续可以用于回归检测
        from ginkgo import service_hub

        # 基线测试指标
        metrics = {
            'startup_time_ms': 0,
            'memory_usage_mb': 0,
            'concurrent_access_time_ms': 0,
            'cache_effectiveness_ratio': 0
        }

        # 启动时间测试
        start_time = time.perf_counter()
        data = service_hub.data
        metrics['startup_time_ms'] = (time.perf_counter() - start_time) * 1000

        # 内存使用测试
        process = psutil.Process(os.getpid())
        metrics['memory_usage_mb'] = process.memory_info().rss / 1024 / 1024

        # 缓存效果测试
        start_time = time.perf_counter()
        data2 = service_hub.data
        cache_time = (time.perf_counter() - start_time) * 1000
        metrics['cache_effectiveness_ratio'] = metrics['startup_time_ms'] / cache_time if cache_time > 0 else 0

        print(f"\n性能基线指标:")
        for metric, value in metrics.items():
            print(f"  {metric}: {value:.2f}")

        # 这些基线值可以保存在配置文件中用于回归检测
        assert metrics['startup_time_ms'] < 100, "启动时间超出基线"
        assert metrics['memory_usage_mb'] < 200, "内存使用超出基线"
        assert metrics['cache_effectiveness_ratio'] > 2, "缓存效果不足"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])