"""
ExecutionNode.load_portfolio 测试

验证实盘 Portfolio 加载链路中 ServiceResult 错误处理行为。
覆盖 #3943 code review 发现的 is_success 缺括号 bug。
"""
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.data.services.base_service import ServiceResult


@pytest.mark.unit
class TestServiceResultIsSuccessCall:
    """验证 ServiceResult.is_success 必须作为方法调用（带括号）"""

    def test_is_success_without_parens_is_truthy_on_failure(self):
        """is_success 不加 () 时返回 bound method，永远 truthy — 这是 #3943 的根因"""
        failed = ServiceResult(success=False, error="something failed")
        assert bool(failed.is_success) is True
        assert failed.is_success() is False

    def test_not_is_success_without_parens_never_enters_error_branch(self):
        """`not result.is_success` 对失败结果为 False，错误分支永远不执行"""
        failed = ServiceResult(success=False, error="fail")
        assert (not failed.is_success) is False   # BUG: should be True
        assert (not failed.is_success()) is True   # Correct


@pytest.mark.unit
class TestLoadPortfolioAssemblyFailure:
    """#3943: assemble_live_portfolio 返回失败时 load_portfolio 应 return False

    测试直接验证 node.py:523 的条件分支：
    `if not load_result.is_success:` 缺括号时 bound method 永远 truthy。
    """

    def test_assembly_failure_returns_false(self):
        """当 assemble_live_portfolio 返回 ServiceResult(success=False) 时应返回 False

        这里直接测试 load_portfolio 中对 is_success 的调用是否正确。
        通过 patch 使 portfolio_service.get 成功、assemble_live_portfolio 失败，
        然后验证 load_portfolio 是否进入了错误分支。
        """
        from ginkgo.workers.execution_node.node import ExecutionNode

        mock_portfolio = MagicMock()
        mock_portfolio.is_live = True

        failed_result = ServiceResult(success=False, error="assembly error")

        mock_ps = MagicMock()
        mock_ps.get.return_value = ServiceResult(success=True, data=[mock_portfolio])

        mock_assembly = MagicMock()
        mock_assembly.assemble_live_portfolio.return_value = failed_result

        # Patch import path used inside load_portfolio's local import
        import ginkgo.workers.execution_node.node as node_mod
        original_eas = getattr(node_mod, "EngineAssemblyService", None)

        with patch.object(node_mod, "services") as mock_svc:
            mock_svc.data.portfolio_service.return_value = mock_ps

            # Patch the local import inside the method
            with patch("ginkgo.trading.services.engine_assembly_service.EngineAssemblyService",
                       return_value=mock_assembly):
                node = ExecutionNode(node_id="test-node")
                # Patch services on the instance's module level too
                with patch.object(node_mod, "services", mock_svc):
                    result = node.load_portfolio("test-uuid-1234")

        assert result is False
