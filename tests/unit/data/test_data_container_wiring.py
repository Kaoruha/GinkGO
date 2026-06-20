"""TDD tests for DI container wiring bugs #5504 / #5554.

#5504: BacktestTaskService 的 engine_service 注入了 CRUD(get_crud,"engine")
       而非 EngineService provider → 调用业务方法 AttributeError。
#5554: backtest_task_crud provider 重复定义（141/164），后者静默覆盖前者。
"""
import re
from pathlib import Path

from ginkgo.data import containers as containers_module
from ginkgo.data.containers import container


class TestBacktestTaskServiceWiring:
    """#5504: engine_service 必须注入 EngineService，而非 CRUD。"""

    def test_engine_service_injected_is_engine_service_provider(self):
        """backtest_task_service 的 engine_service 应来自 engine_service provider。"""
        bts_provider = container.backtest_task_service
        injected = bts_provider.kwargs.get("engine_service")
        # 修复后：注入的是 container.engine_service provider（EngineService）
        # 修复前：是 providers.Singleton(get_crud, "engine")（CRUD）
        assert injected is container.engine_service, (
            "engine_service 应注入 container.engine_service provider，"
            "而非 get_crud(\"engine\") CRUD（#5504）"
        )

    def test_engine_service_provider_is_engine_service_class(self):
        """engine_service provider 应装配 EngineService 类。"""
        from ginkgo.data.services.engine_service import EngineService
        es_provider = container.engine_service
        # dependency_injector Singleton 的 .cls 暴露被装配的类
        assert getattr(es_provider, "cls", None) is EngineService


class TestNoDuplicateBacktestTaskCrud:
    """#5554: backtest_task_crud 不得重复定义。"""

    def test_backtest_task_crud_defined_once(self):
        """源文件中 backtest_task_crud provider 定义应仅出现一次。"""
        src = Path(containers_module.__file__).read_text(encoding="utf-8")
        # 匹配顶层的 `backtest_task_crud = providers.Singleton(...)` 赋值
        matches = re.findall(r"^\s+backtest_task_crud\s*=\s*providers\.", src, re.MULTILINE)
        assert len(matches) == 1, (
            f"backtest_task_crud 应只定义一次，实际 {len(matches)} 次（#5554 重复 provider）"
        )
