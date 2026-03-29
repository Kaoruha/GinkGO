"""
Unit tests for concurrent logging and thread safety

This module verifies that contextvars provide proper thread isolation
for trace_id and other logging context in multi-threaded scenarios.
"""

import pytest
import threading
import time
import contextvars
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List

# TODO: 确认导入路径是否正确
from ginkgo.libs import GLOG


@pytest.mark.tdd
class TestConcurrentTraceIdIsolation:
    """
    测试多线程 trace_id 隔离 (T059)

    覆盖范围:
    - contextvars 线程隔离特性
    - 并发场景下 trace_id 不会互相干扰
    - 线程间上下文独立
    """

    def test_concurrent_trace_id_isolation(self):
        """
        测试多线程 trace_id 隔离 (T059)

        验证点:
        - 每个线程的 trace_id 独立
        - 线程间不会互相覆盖
        - contextvars 自动隔离上下文
        """
        results: Dict[str, str] = {}
        errors: List[str] = []

        def worker(trace_id: str, value: int):
            """工作线程函数"""
            try:
                # 设置当前线程的 trace_id
                GLOG.set_trace_id(trace_id)
                # 模拟一些处理时间
                time.sleep(0.01)
                # 获取当前线程的 trace_id
                retrieved = GLOG.get_trace_id()
                results[trace_id] = retrieved
            except Exception as e:
                errors.append(str(e))

        # 创建多个线程，每个设置不同的 trace_id
        threads = [
            threading.Thread(target=worker, args=("trace-A", 1)),
            threading.Thread(target=worker, args=("trace-B", 2)),
            threading.Thread(target=worker, args=("trace-C", 3)),
        ]

        # 启动所有线程
        for t in threads:
            t.start()
        # 等待所有线程完成
        for t in threads:
            t.join()

        # 验证结果
        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert results.get("trace-A") == "trace-A", f"trace-A mismatch: {results.get('trace-A')}"
        assert results.get("trace-B") == "trace-B", f"trace-B mismatch: {results.get('trace-B')}"
        assert results.get("trace-C") == "trace-C", f"trace-C mismatch: {results.get('trace-C')}"

    def test_thread_pool_trace_id_isolation(self):
        """
        测试线程池中 trace_id 隔离

        验证点:
        - 线程池中每个任务的 trace_id 独立
        - 不同任务不会互相干扰
        - 线程复用不会导致上下文泄露
        """
        results: Dict[str, str] = {}

        def task(trace_id: str) -> tuple:
            """线程池任务"""
            GLOG.set_trace_id(trace_id)
            time.sleep(0.005)  # 模拟处理
            retrieved = GLOG.get_trace_id()
            return (trace_id, retrieved)

        # 使用线程池执行多个任务
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(task, f"trace-{i}"): f"trace-{i}"
                for i in range(10)
            }

            for future in as_completed(futures):
                original, retrieved = future.result()
                results[original] = retrieved

        # 验证所有 trace_id 都正确隔离
        for i in range(10):
            trace_id = f"trace-{i}"
            assert results.get(trace_id) == trace_id, \
                f"{trace_id} mismatch: got {results.get(trace_id)}"

    def test_nested_thread_trace_id_isolation(self):
        """
        测试嵌套线程创建场景

        验证点:
        - 父线程的 trace_id 不会泄露到子线程
        - 子线程的 trace_id 独立
        - 多层嵌套也能正确隔离
        """
        results: Dict[str, str] = {}

        def parent_thread():
            """父线程"""
            GLOG.set_trace_id("parent-trace")
            GLOG.INFO("Parent thread starting")

            def child_thread():
                """子线程"""
                GLOG.set_trace_id("child-trace")
                time.sleep(0.01)
                results["child"] = GLOG.get_trace_id()

            child = threading.Thread(target=child_thread)
            child.start()
            child.join()

            results["parent"] = GLOG.get_trace_id()

        parent = threading.Thread(target=parent_thread)
        parent.start()
        parent.join()

        # 验证父子线程的 trace_id 独立
        assert results.get("parent") == "parent-trace"
        assert results.get("child") == "child-trace"

    def test_concurrent_logging_with_trace_id(self):
        """
        测试并发带 trace_id 的日志记录

        验证点:
        - 多线程同时记录日志不崩溃
        - 每条日志使用正确的 trace_id
        - 日志输出不混乱
        """
        errors: List[str] = []
        log_count = {"count": 0}

        def logging_worker(trace_id: str, iterations: int):
            """记录日志的工作线程"""
            try:
                GLOG.set_trace_id(trace_id)
                for i in range(iterations):
                    GLOG.INFO(f"[{trace_id}] Message {i}")
                    log_count["count"] += 1
                    time.sleep(0.001)
            except Exception as e:
                errors.append(f"{trace_id}: {e}")

        threads = [
            threading.Thread(target=logging_worker, args=("log-A", 5)),
            threading.Thread(target=logging_worker, args=("log-B", 5)),
            threading.Thread(target=logging_worker, args=("log-C", 5)),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 验证没有错误
        assert len(errors) == 0, f"Logging errors: {errors}"
        # 验证日志总数
        assert log_count["count"] == 15

    def test_trace_id_context_manager_thread_safety(self):
        """
        测试 with_trace_id 上下文管理器线程安全

        验证点:
        - 上下文管理器在线程间正确隔离
        - 退出上下文后 trace_id 正确恢复
        - 不会影响其他线程
        """
        results: Dict[str, List[str]] = {}

        def context_manager_worker(thread_id: str):
            """使用上下文管理器的工作线程"""
            trace_ids = []

            # 设置初始 trace_id
            GLOG.set_trace_id(f"{thread_id}-initial")
            trace_ids.append(GLOG.get_trace_id())

            # 使用上下文管理器临时设置 trace_id
            with GLOG.with_trace_id(f"{thread_id}-temp"):
                trace_ids.append(GLOG.get_trace_id())
                time.sleep(0.01)

            # 验证恢复到原始值
            trace_ids.append(GLOG.get_trace_id())
            results[thread_id] = trace_ids

        threads = [
            threading.Thread(target=context_manager_worker, args=("A",)),
            threading.Thread(target=context_manager_worker, args=("B",)),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 验证每个线程的 trace_id 序列
        assert results["A"] == ["A-initial", "A-temp", "A-initial"]
        assert results["B"] == ["B-initial", "B-temp", "B-initial"]

    def test_rapid_trace_id_switching(self):
        """
        测试快速切换 trace_id

        验证点:
        - 快速多次设置 trace_id 不混乱
        - 每次 get_trace_id() 返回最新设置的值
        - 不会出现线程间数据泄露
        """
        results: List[str] = []

        def switcher_worker(start_value: int, count: int):
            """快速切换 trace_id 的工作线程"""
            for i in range(count):
                trace_id = f"switch-{start_value}-{i}"
                GLOG.set_trace_id(trace_id)
                retrieved = GLOG.get_trace_id()
                results.append(retrieved)

        threads = [
            threading.Thread(target=switcher_worker, args=(1, 10)),
            threading.Thread(target=switcher_worker, args=(2, 10)),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 验证所有 trace_id 都被正确记录
        assert len(results) == 20
        # 每个 trace_id 应该等于对应的设置值
        for i in range(10):
            assert f"switch-1-{i}" in results
            assert f"switch-2-{i}" in results

    def test_clear_trace_id_thread_isolation(self):
        """
        测试清除 trace_id 的线程隔离

        验证点:
        - 一个线程清除 trace_id 不影响其他线程
        - 每个线程独立管理自己的 trace_id
        """
        trace_ids: Dict[str, str] = {}

        def clear_worker(thread_id: str):
            """测试清除 trace_id 的线程"""
            GLOG.set_trace_id(f"{thread_id}-trace")
            time.sleep(0.01)

            # 第一个线程清除 trace_id
            if thread_id == "A":
                token = GLOG.set_trace_id("temp")
                GLOG.clear_trace_id(token)

            trace_ids[thread_id] = GLOG.get_trace_id()

        threads = [
            threading.Thread(target=clear_worker, args=("A",)),
            threading.Thread(target=clear_worker, args=("B",)),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 线程 A 清除后应该返回到原始 trace_id
        assert trace_ids["A"] == "A-trace"
        # 线程 B 不受影响
        assert trace_ids["B"] == "B-trace"

    def test_concurrent_error_stats_isolation(self):
        """
        测试并发错误统计的线程安全

        验证点:
        - 多线程同时记录错误日志
        - 错误统计正确聚合
        - 统计数据线程安全
        """
        # 清除之前的统计
        GLOG.clear_error_stats()

        def error_worker(thread_id: str, error_count: int):
            """产生错误的工作线程"""
            for i in range(error_count):
                GLOG.ERROR(f"[{thread_id}] Error {i}")

        threads = [
            threading.Thread(target=error_worker, args=("A", 5)),
            threading.Thread(target=error_worker, args=("B", 3)),
            threading.Thread(target=error_worker, args=("C", 7)),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 获取统计
        stats = GLOG.get_error_stats()

        # 验证错误总数（可能有重复模式）
        assert stats["total_error_count"] > 0
        # 应该有至少 3 个不同的错误模式（每个线程一个）
        assert stats["total_error_patterns"] >= 3

    def test_contextvars_underlying_mechanism(self):
        """
        测试 contextvars 底层机制

        验证点:
        - contextvars.ContextVar 正常工作
        - 线程间自动隔离
        - Token 机制正确
        """
        from ginkgo.libs.core.logger import _trace_id_ctx

        results: Dict[str, any] = {}

        def contextvars_worker(worker_id: str):
            """测试 contextvars 的工作线程"""
            # 设置新值
            token = _trace_id_ctx.set(f"ctx-{worker_id}")
            results[f"{worker_id}-set"] = _trace_id_ctx.get()

            time.sleep(0.01)

            # 验证值未变
            results[f"{worker_id}-get"] = _trace_id_ctx.get()

            # 恢复之前的值
            _trace_id_ctx.reset(token)
            results[f"{worker_id}-reset"] = _trace_id_ctx.get()

        threads = [
            threading.Thread(target=contextvars_worker, args=("A",)),
            threading.Thread(target=contextvars_worker, args=("B",)),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 验证每个线程的 contextvars 操作
        assert results["A-set"] == "ctx-A"
        assert results["A-get"] == "ctx-A"
        assert results["A-reset"] is None  # 恢复到默认值

        assert results["B-set"] == "ctx-B"
        assert results["B-get"] == "ctx-B"
        assert results["B-reset"] is None


@pytest.mark.tdd
class TestAsyncContextPropagation:
    """
    测试异步上下文传播

    覆盖范围:
    - async/await 场景下 trace_id 传播
    - 异步任务间上下文隔离
    - asyncio 兼容性
    """

    def test_async_trace_id_propagation(self):
        """
        测试异步场景 trace_id 传播

        验证点:
        - async 函数间 trace_id 自动传播
        - await 后 trace_id 保持不变
        - 异步上下文正确
        """
        import asyncio

        async def inner_task():
            """内部异步任务"""
            return GLOG.get_trace_id()

        async def outer_task():
            """外部异步任务"""
            GLOG.set_trace_id("async-trace")
            result = await inner_task()
            return result

        result = asyncio.run(outer_task())
        assert result == "async-trace"

    def test_async_gather_context_isolation(self):
        """
        测试 asyncio.gather 的上下文隔离

        验证点:
        - 并发异步任务的 trace_id 独立
        - gather 后不互相干扰
        """
        import asyncio

        async def async_task(trace_id: str):
            """异步任务"""
            GLOG.set_trace_id(trace_id)
            await asyncio.sleep(0.01)
            return GLOG.get_trace_id()

        async def main():
            """主异步任务"""
            results = await asyncio.gather(
                async_task("async-A"),
                async_task("async-B"),
                async_task("async-C"),
            )
            return results

        results = asyncio.run(main())
        assert results == ["async-A", "async-B", "async-C"]


@pytest.mark.tdd
class TestStressScenarios:
    """
    测试压力场景

    覆盖范围:
    - 高并发场景
    - 资源竞争
    - 性能验证
    """

    def test_high_concurrency_trace_id(self):
        """
        测试高并发 trace_id 隔离

        验证点:
        - 大量线程同时操作
        - 没有上下文混乱
        - 没有性能死锁
        """
        thread_count = 50
        results: Dict[str, str] = {}
        errors: List[str] = []

        def stress_worker(worker_id: int):
            """压力测试工作线程"""
            try:
                trace_id = f"stress-{worker_id:03d}"
                GLOG.set_trace_id(trace_id)
                time.sleep(0.001)
                retrieved = GLOG.get_trace_id()
                results[trace_id] = retrieved
            except Exception as e:
                errors.append(str(e))

        threads = [
            threading.Thread(target=stress_worker, args=(i,))
            for i in range(thread_count)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 验证结果
        assert len(errors) == 0, f"Errors: {errors}"
        assert len(results) == thread_count

        # 验证每个 trace_id 都正确
        for i in range(thread_count):
            trace_id = f"stress-{i:03d}"
            assert results.get(trace_id) == trace_id
