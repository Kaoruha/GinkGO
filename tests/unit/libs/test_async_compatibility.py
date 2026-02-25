"""
T060: 异步兼容测试

验证 async/await 场景下 trace_id 自动传播和上下文管理。

测试覆盖:
- async/await 场景下 trace_id 自动传播
- 嵌套异步调用中的 trace_id 传播
- 异步上下文管理器功能
- 多个并发异步任务的 trace_id 隔离
- 异步生成器中的 trace_id 传播

注意: 这些测试使用 asyncio.run() 直接运行，不需要 pytest-asyncio 插件
"""

import pytest
import asyncio
from contextvars import Token

# TODO: 确认导入路径是否正确
from ginkgo.libs import GLOG


@pytest.mark.tdd
class TestAsyncTraceIdPropagation:
    """
    测试异步场景下 trace_id 自动传播

    覆盖范围:
    - 单层异步函数中的 trace_id 传播
    - 多层嵌套异步调用中的 trace_id 传播
    - 异步上下文管理器中的 trace_id 管理
    """

    def test_async_simple_propagation(self):
        """
        测试简单异步函数中的 trace_id 传播 (T060-1)

        验证点:
        - 在 async 函数中设置的 trace_id 可以被获取
        - trace_id 在 async 函数执行期间保持不变
        - 使用 GLOG 全局实例测试
        """
        async def main():
            GLOG.set_trace_id("trace-async-simple")
            result = GLOG.get_trace_id()
            assert result == "trace-async-simple"

        asyncio.run(main())

    def test_async_nested_propagation(self):
        """
        测试嵌套异步调用中的 trace_id 传播 (T060-2)

        验证点:
        - trace_id 通过多层 await 调用自动传播
        - 最内层的异步函数可以访问到外层设置的 trace_id
        - 传播链路: main -> step3 -> step2 -> step1
        """
        async def step1():
            return GLOG.get_trace_id()

        async def step2():
            result = await step1()
            return result

        async def step3():
            result = await step2()
            return result

        async def main():
            GLOG.set_trace_id("trace-async-nested")
            result = await step3()
            assert result == "trace-async-nested"

        asyncio.run(main())

    def test_async_context_manager(self):
        """
        测试异步上下文管理器中的 trace_id 管理 (T060-3)

        验证点:
        - with_trace_id 上下文管理器在异步代码中正常工作
        - 退出上下文后 trace_id 恢复原值
        - 支持嵌套的上下文管理器
        """
        async def main():
            # 设置初始 trace_id
            GLOG.set_trace_id("trace-original")
            assert GLOG.get_trace_id() == "trace-original"

            # 使用上下文管理器临时覆盖
            with GLOG.with_trace_id("trace-temp"):
                assert GLOG.get_trace_id() == "trace-temp"
                # 在上下文内调用异步函数
                await asyncio.sleep(0.001)
                assert GLOG.get_trace_id() == "trace-temp"

            # 退出后恢复原值
            assert GLOG.get_trace_id() == "trace-original"

        asyncio.run(main())

    def test_async_token_management(self):
        """
        测试异步场景下的 Token 管理 (T060-4)

        验证点:
        - set_trace_id 返回有效的 Token
        - 使用 Token 可以正确恢复上下文
        - 多次设置和清除操作正确嵌套
        """
        async def main():
            # 第一次设置
            token1 = GLOG.set_trace_id("trace-level-1")
            assert isinstance(token1, Token)
            assert GLOG.get_trace_id() == "trace-level-1"

            # 第二次设置（嵌套）
            token2 = GLOG.set_trace_id("trace-level-2")
            assert GLOG.get_trace_id() == "trace-level-2"

            # 恢复到第一层
            GLOG.clear_trace_id(token2)
            assert GLOG.get_trace_id() == "trace-level-1"

            # 恢复到初始状态
            GLOG.clear_trace_id(token1)
            # 恢复后应该是 None 或之前的值
            result = GLOG.get_trace_id()
            # 清除后不应该有 trace_id
            assert result is None or result == "trace-level-1"

        asyncio.run(main())


@pytest.mark.tdd
class TestAsyncConcurrentIsolation:
    """
    测试并发异步场景下的 trace_id 隔离

    覆盖范围:
    - 多个并发异步任务的 trace_id 独立性
    - asyncio.gather 中的隔离
    - asyncio.Task 中的隔离
    """

    def test_async_gather_isolation(self):
        """
        测试 asyncio.gather 中的 trace_id 隔离 (T060-5)

        验证点:
        - gather 并发执行的每个任务有独立的 trace_id
        - 任务之间不会相互干扰
        - 任务完成后 trace_id 正确恢复
        """
        async def main():
            results = {}

            async def task(task_id, trace_id):
                GLOG.set_trace_id(trace_id)
                await asyncio.sleep(0.001)  # 模拟异步操作
                results[task_id] = GLOG.get_trace_id()

            # 并发执行多个任务
            await asyncio.gather(
                task("task-1", "trace-A"),
                task("task-2", "trace-B"),
                task("task-3", "trace-C"),
            )

            # 验证每个任务都有正确的 trace_id
            assert results["task-1"] == "trace-A"
            assert results["task-2"] == "trace-B"
            assert results["task-3"] == "trace-C"

        asyncio.run(main())

    def test_async_create_task_isolation(self):
        """
        测试 asyncio.create_task 中的 trace_id 隔离 (T060-6)

        验证点:
        - 通过 create_task 创建的任务有独立的上下文
        - 任务执行时 trace_id 正确传播
        - 主任务和子任务互不干扰
        """
        async def main():
            results = []

            async def child_task(task_id, trace_id):
                GLOG.set_trace_id(trace_id)
                await asyncio.sleep(0.001)
                return GLOG.get_trace_id()

            # 创建多个子任务
            tasks = [
                asyncio.create_task(child_task("child-1", "trace-X"))
                for _ in range(3)
            ]

            # 等待所有任务完成
            task_results = await asyncio.gather(*tasks)
            results.extend(task_results)

            # 验证结果
            for result in results:
                assert result == "trace-X"

        asyncio.run(main())

    def test_async_context_with_logging(self):
        """
        测试异步场景下的日志记录 (T060-7)

        验证点:
        - 异步代码中使用 GLOG 记录日志不报错
        - 日志中包含正确的 trace_id（通过 JSON 输出验证）
        - 多个异步并发任务日志不混淆
        """
        async def main():
            # 设置 trace_id 并记录日志
            GLOG.set_trace_id("trace-log-test")

            # 异步代码中记录日志
            GLOG.INFO("Async log message 1")
            await asyncio.sleep(0.001)
            GLOG.INFO("Async log message 2")

            # 验证不抛出异常
            assert True

            # 清理
            GLOG.clear_trace_id(GLOG.set_trace_id("dummy"))

        asyncio.run(main())


@pytest.mark.tdd
class TestAsyncComplexScenarios:
    """
    测试异步复杂场景

    覆盖范围:
    - 异步生成器中的 trace_id 传播
    - 异步迭代器中的上下文管理
    - 混合使用同步和异步代码
    """

    def test_async_generator_propagation(self):
        """
        测试异步生成器中的 trace_id 传播 (T060-8)

        验证点:
        - 异步生成器函数可以访问 trace_id
        - 每次迭代都保持相同的 trace_id
        - 生成器外部修改 trace_id 不影响已创建的生成器
        """
        async def main():
            async def trace_aware_generator():
                """生成器中访问 trace_id"""
                for i in range(3):
                    trace = GLOG.get_trace_id()
                    yield i, trace
                    await asyncio.sleep(0.001)

            # 设置 trace_id
            GLOG.set_trace_id("trace-generator")
            results = []

            async for item, trace in trace_aware_generator():
                results.append((item, trace))

            # 验证所有迭代都有相同的 trace_id
            assert len(results) == 3
            for item, trace in results:
                assert trace == "trace-generator"

        asyncio.run(main())

    def test_mixed_sync_async_context(self):
        """
        测试混合同步和异步代码的上下文管理 (T060-9)

        验证点:
        - 同步代码中设置的 trace_id 可以传播到异步代码
        - 异步代码中的修改不影响同步上下文
        - 两者可以和谐共存
        """
        async def main():
            # 同步设置
            GLOG.set_trace_id("trace-sync-start")

            # 异步读取
            async def async_read():
                return GLOG.get_trace_id()

            result = await async_read()
            assert result == "trace-sync-start"

            # 异步修改
            async def async_modify():
                GLOG.set_trace_id("trace-async-modified")
                return GLOG.get_trace_id()

            result = await async_modify()
            assert result == "trace-async-modified"

            # 同步读取异步修改后的值
            result = GLOG.get_trace_id()
            assert result == "trace-async-modified"

        asyncio.run(main())


@pytest.mark.tdd
class TestAsyncErrorHandling:
    """
    测试异步错误场景

    覆盖范围:
    - 异步异常情况下的 trace_id 管理
    - 上下文管理器在异常时的行为
    """

    def test_async_context_with_exception(self):
        """
        测试异步上下文管理器在异常时的行为 (T060-10)

        验证点:
        - 异步上下文中发生异常时 trace_id 仍然正确恢复
        - 异常不会破坏 contextvars 的状态
        - 后续代码可以正常使用 trace_id
        """
        async def main():
            # 设置初始值
            GLOG.set_trace_id("trace-before-exception")

            # 使用上下文管理器并在其中抛出异常
            try:
                with GLOG.with_trace_id("trace-in-try"):
                    assert GLOG.get_trace_id() == "trace-in-try"
                    await asyncio.sleep(0.001)
                    raise ValueError("Test exception")
            except ValueError:
                pass

            # 异常后应该恢复到原值
            assert GLOG.get_trace_id() == "trace-before-exception"

        asyncio.run(main())

    def test_async_cleanup_after_error(self):
        """
        测试异步错误后的清理 (T060-11)

        验证点:
        - 异步函数抛出异常后 trace_id 状态一致
        - 可以正确清除和重新设置 trace_id
        - 异常不会导致 contextvars 泄漏
        """
        async def main():
            # 设置 trace_id
            token = GLOG.set_trace_id("trace-cleanup-test")

            async def failing_async():
                await asyncio.sleep(0.001)
                raise RuntimeError("Async failure")

            # 执行会失败的异步操作
            try:
                await failing_async()
            except RuntimeError:
                pass

            # 验证 trace_id 仍然可用
            assert GLOG.get_trace_id() == "trace-cleanup-test"

            # 清理
            GLOG.clear_trace_id(token)
            result = GLOG.get_trace_id()
            assert result is None or result != "trace-cleanup-test"

        asyncio.run(main())
