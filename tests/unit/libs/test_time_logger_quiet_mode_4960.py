"""
TDD tests for #4960: daemon/批量化场景下 time_logger 逐调用 ⚡ FUNCTION 日志噪音。

复现：`ginkgo data sync day --daemon` 在 DEBUGMODE 下输出 15000+ 行
`⚡ FUNCTION send / send_message executed in ...`，因为 send_bar_all_signal
按每只股票循环触发两个 @time_logger 装饰方法。

契约：`quiet_function_timing()` 上下文管理器在批处理路径中静默逐调用 timing，
退出时打印一行汇总（次数/总耗时/avg/max）。其余调用点行为不变。
"""

import pytest


@pytest.fixture(autouse=True)
def _reset_config_singleton():
    """每个用例给 GinkgoConfig 单例一个干净起点（time_logger 读 _gconf）。"""
    from ginkgo.libs.core.config import GinkgoConfig

    if hasattr(GinkgoConfig, "_instance"):
        del GinkgoConfig._instance
    yield
    if hasattr(GinkgoConfig, "_instance"):
        del GinkgoConfig._instance


class TestQuietFunctionTiming:
    """quiet_function_timing 上下文静默 time_logger 的逐调用 ⚡ FUNCTION 打印。"""

    def test_quiet_context_suppresses_per_call_function_print(self, capfd):
        """
        在 quiet_function_timing 上下文内调用被装饰函数，
        不再逐次打印 `⚡ FUNCTION ... executed in ...`。

        复现 #4960：批处理路径（daemon 逐股 Kafka send）每只股票都触发
        time_logger 的 finally 分支打印，15000+ 行噪音淹没真实输出。
        """
        from ginkgo.libs.utils.common import time_logger, quiet_function_timing

        @time_logger(enabled=True, threshold=-1)
        def fast_op():
            return 42

        with quiet_function_timing():
            assert fast_op() == 42
            assert fast_op() == 42

        captured = capfd.readouterr()
        # 逐调用 timing 标志 `executed in` 不得出现（stdout / stderr 都不能有）
        assert "executed in" not in captured.err
        assert "executed in" not in captured.out

    def test_quiet_context_emits_summary_with_count_and_func_name(self, capfd):
        """
        上下文退出时打印一行汇总，含函数名与调用次数。

        验收 #4960：daemon 模式输出「汇总为主，非逐调用打印」。
        汇总走 stderr（与 time_logger 诊断一致，#6465），stdout 保持干净。
        """
        from ginkgo.libs.utils.common import time_logger, quiet_function_timing

        @time_logger(enabled=True, threshold=-1)
        def fast_op():
            return "ok"

        with quiet_function_timing():
            for _ in range(3):
                fast_op()

        captured = capfd.readouterr()
        # 汇总标记
        assert "FUNCTION timing summary" in captured.err
        # 函数名 + 次数
        assert "fast_op" in captured.err
        assert "3 calls" in captured.err
        # 汇总走 stderr，stdout 干净
        assert "FUNCTION" not in captured.out

    def test_without_quiet_context_per_call_timing_still_prints(self, capfd):
        """
        回归守卫：不在 quiet_function_timing 上下文内时，time_logger 仍逐次打印。

        复现：本修复不得改变既有非批处理路径的诊断行为。
        """
        from ginkgo.libs.utils.common import time_logger

        @time_logger(enabled=True, threshold=-1)
        def fast_op():
            return 1

        fast_op()

        captured = capfd.readouterr()
        # 既有行为：逐调用 `executed in` 走 stderr
        assert "executed in" in captured.err
        assert "fast_op" in captured.err

    def test_quiet_context_does_not_swallow_exceptions(self, capfd):
        """
        with 体内抛出的异常必须原样传播，不得被 quiet_function_timing 的
        finally 汇总逻辑吞掉（finally 内 return/吞异常是常见陷阱）。
        """
        from ginkgo.libs.utils.common import time_logger, quiet_function_timing

        @time_logger(enabled=True, threshold=-1)
        def boom():
            raise ValueError("kaboom")

        with pytest.raises(ValueError, match="kaboom"):
            with quiet_function_timing():
                boom()

