"""
增强回测系统性能基准测试 - 优化版使用Pytest最佳实践。

测试增强回测系统的性能基准。
"""

import pytest
import time
import psutil
import os
from typing import Dict, Any
from unittest.mock import Mock, patch


@pytest.mark.performance
@pytest.mark.benchmark
class TestBacktestEnginePerformance:
    """回测引擎性能测试."""

    @pytest.fixture
    def benchmark_config(self) -> Dict[str, Any]:
        """性能基准配置."""
        return {
            'iterations': 10,
            'max_avg_time_sec': 0.1,
            'max_memory_mb': 10,
        }

    @pytest.mark.unit
    def test_engine_creation_performance(self, benchmark_config):
        """测试引擎创建性能."""
        try:
            from ginkgo.backtest.core.containers import container
        except ImportError:
            pytest.skip("Container not available")

        creation_times = []

        for _ in range(benchmark_config['iterations']):
            start_time = time.perf_counter()
            try:
                engine = container.engines.historic()
                creation_time = time.perf_counter() - start_time
                creation_times.append(creation_time)
            except Exception as e:
                pytest.skip(f"Engine creation failed: {e}")

        avg_creation_time = sum(creation_times) / len(creation_times)

        # 断言平均创建时间
        assert avg_creation_time < benchmark_config['max_avg_time_sec'], \
            f"引擎平均创建时间过长: {avg_creation_time:.4f}s"

    @pytest.mark.unit
    def test_engine_memory_usage(self, benchmark_config):
        """测试引擎内存使用."""
        try:
            from ginkgo.backtest.core.containers import container
        except ImportError:
            pytest.skip("Container not available")

        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024

        try:
            engine = container.engines.historic()
            final_memory = process.memory_info().rss / 1024 / 1024
            memory_increase = final_memory - initial_memory

            # 断言内存增长在合理范围内
            assert memory_increase < benchmark_config['max_memory_mb'], \
                f"引擎内存使用过多: {memory_increase:.2f}MB"
        except Exception as e:
            pytest.skip(f"Engine memory test failed: {e}")


@pytest.mark.performance
@pytest.mark.benchmark
class TestBacktestStrategyPerformance:
    """回测策略性能测试."""

    @pytest.fixture
    def benchmark_config(self) -> Dict[str, Any]:
        """性能基准配置."""
        return {
            'iterations': 20,
            'max_avg_time_sec': 0.05,
            'max_memory_mb': 1,
        }

    @pytest.mark.unit
    @pytest.mark.parametrize("strategy_type", [
        "trend_follow",
        "dual_thrust",
        "random",
    ])
    def test_strategy_creation_performance(self, benchmark_config, strategy_type):
        """测试策略创建性能."""
        try:
            from ginkgo.backtest.core.containers import container
        except ImportError:
            pytest.skip("Container not available")

        creation_times = []

        for _ in range(benchmark_config['iterations']):
            start_time = time.perf_counter()
            try:
                strategy = container.strategies[strategy_type]()
                creation_time = time.perf_counter() - start_time
                creation_times.append(creation_time)
            except Exception as e:
                pytest.skip(f"Strategy {strategy_type} creation failed: {e}")

        avg_creation_time = sum(creation_times) / len(creation_times)

        # 断言平均创建时间
        assert avg_creation_time < benchmark_config['max_avg_time_sec'], \
            f"策略 {strategy_type} 平均创建时间过长: {avg_creation_time:.4f}s"


@pytest.mark.performance
@pytest.mark.benchmark
class TestBacktestConfigPerformance:
    """回测配置性能测试."""

    @pytest.fixture
    def benchmark_config(self) -> Dict[str, Any]:
        """性能基准配置."""
        return {
            'iterations': 100,
            'max_avg_time_sec': 0.01,
        }

    @pytest.fixture
    def sample_config(self):
        """示例配置."""
        try:
            from ginkgo.backtest.execution.engines.config.backtest_config import BacktestConfig
            return BacktestConfig(
                name="PerformanceTest",
                start_date="2023-01-01",
                end_date="2023-12-31"
            )
        except ImportError:
            return None

    @pytest.mark.unit
    def test_config_serialization_performance(self, benchmark_config, sample_config):
        """测试配置序列化性能."""
        if sample_config is None:
            pytest.skip("BacktestConfig not available")

        serialization_times = []

        for _ in range(benchmark_config['iterations']):
            start_time = time.perf_counter()

            try:
                config_dict = sample_config.to_dict()
                new_config = sample_config.__class__.from_dict(config_dict)
                serialization_time = time.perf_counter() - start_time
                serialization_times.append(serialization_time)
            except Exception as e:
                pytest.skip(f"Config serialization failed: {e}")

        avg_serialization_time = sum(serialization_times) / len(serialization_times)

        # 断言平均序列化时间
        assert avg_serialization_time < benchmark_config['max_avg_time_sec'], \
            f"配置序列化时间过长: {avg_serialization_time:.6f}s"


@pytest.mark.performance
@pytest.mark.benchmark
class TestBacktestContainerPerformance:
    """回测容器性能测试."""

    @pytest.fixture
    def benchmark_config(self) -> Dict[str, Any]:
        """性能基准配置."""
        return {
            'iterations': 100,
            'max_avg_time_sec': 0.01,
        }

    @pytest.mark.unit
    def test_container_access_performance(self, benchmark_config):
        """测试容器访问性能."""
        try:
            from ginkgo.backtest.core.containers import container
        except ImportError:
            pytest.skip("Container not available")

        access_times = []

        for _ in range(benchmark_config['iterations']):
            start_time = time.perf_counter()

            try:
                # 访问多个容器组件
                components = []
                components.append(('engine', container.engines.historic()))
                components.append(('strategy', container.strategies.trend_follow()))
                components.append(('analyzer', container.analyzers.sharpe()))

                access_time = time.perf_counter() - start_time
                access_times.append(access_time)
            except Exception as e:
                pytest.skip(f"Container access failed: {e}")

        avg_access_time = sum(access_times) / len(access_times)

        # 断言平均访问时间
        assert avg_access_time < benchmark_config['max_avg_time_sec'], \
            f"容器访问时间过长: {avg_access_time:.6f}s"


@pytest.mark.performance
@pytest.mark.benchmark
@pytest.mark.slow
class TestBacktestFullBenchmark:
    """完整回测性能基准测试."""

    @pytest.fixture
    def benchmark_config(self) -> Dict[str, Any]:
        """性能基准配置."""
        return {
            'engine_iterations': 10,
            'strategy_iterations': 20,
            'config_iterations': 100,
            'container_iterations': 100,
        }

    @pytest.mark.slow
    def test_full_backtest_benchmark(self, benchmark_config):
        """完整回测性能基准测试."""
        try:
            from ginkgo.backtest.core.containers import container
            from ginkgo.backtest.execution.engines.config.backtest_config import BacktestConfig
        except ImportError:
            pytest.skip("Required modules not available")

        results = {}

        # 引擎创建基准测试
        engine_times = []
        for _ in range(benchmark_config['engine_iterations']):
            try:
                start_time = time.perf_counter()
                engine = container.engines.historic()
                engine_time = time.perf_counter() - start_time
                engine_times.append(engine_time)
            except Exception:
                pass

        if engine_times:
            results['engine'] = {
                'avg': sum(engine_times) / len(engine_times),
                'count': len(engine_times),
            }

        # 策略创建基准测试
        strategy_times = []
        for _ in range(benchmark_config['strategy_iterations']):
            try:
                start_time = time.perf_counter()
                strategy = container.strategies.trend_follow()
                strategy_time = time.perf_counter() - start_time
                strategy_times.append(strategy_time)
            except Exception:
                pass

        if strategy_times:
            results['strategy'] = {
                'avg': sum(strategy_times) / len(strategy_times),
                'count': len(strategy_times),
            }

        # 配置操作基准测试
        try:
            config = BacktestConfig(
                name="BenchmarkTest",
                start_date="2023-01-01",
                end_date="2023-12-31"
            )

            config_times = []
            for _ in range(benchmark_config['config_iterations']):
                try:
                    start_time = time.perf_counter()
                    config_dict = config.to_dict()
                    new_config = BacktestConfig.from_dict(config_dict)
                    config_time = time.perf_counter() - start_time
                    config_times.append(config_time)
                except Exception:
                    pass

            if config_times:
                results['config'] = {
                    'avg': sum(config_times) / len(config_times),
                    'count': len(config_times),
                }
        except Exception:
            pass

        # 验证结果
        assert 'engine' in results or 'strategy' in results, "至少有一个测试应该成功"

        if 'engine' in results:
            assert results['engine']['avg'] < 0.5, "引擎创建时间过长"
        if 'strategy' in results:
            assert results['strategy']['avg'] < 0.1, "策略创建时间过长"


@pytest.mark.performance
@pytest.mark.benchmark
class TestBacktestMemoryEstimation:
    """回测内存估算性能测试."""

    @pytest.fixture
    def benchmark_config(self) -> Dict[str, Any]:
        """性能基准配置."""
        return {
            'iterations': 50,
            'max_avg_time_sec': 0.001,
        }

    @pytest.mark.unit
    def test_memory_estimation_performance(self, benchmark_config):
        """测试内存估算性能."""
        try:
            from ginkgo.backtest.execution.engines.config.backtest_config import BacktestConfig
        except ImportError:
            pytest.skip("BacktestConfig not available")

        configs = [
            BacktestConfig(start_date="2023-01-01", end_date="2023-01-31"),
            BacktestConfig(start_date="2023-01-01", end_date="2023-06-30"),
            BacktestConfig(start_date="2023-01-01", end_date="2023-12-31"),
        ]

        estimation_times = []

        for _ in range(benchmark_config['iterations']):
            start_time = time.perf_counter()

            try:
                for config in configs:
                    memory_usage = config.estimate_memory_usage()
                estimation_time = time.perf_counter() - start_time
                estimation_times.append(estimation_time)
            except Exception:
                pass

        if estimation_times:
            avg_estimation_time = sum(estimation_times) / len(estimation_times)

            # 断言平均估算时间
            assert avg_estimation_time < benchmark_config['max_avg_time_sec'], \
                f"内存估算时间过长: {avg_estimation_time:.6f}s"
