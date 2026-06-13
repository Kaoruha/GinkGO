"""
#6103: ComponentLoader._resolve_component_params 走注入的 param_service

消除 container.cruds.param() service locator（#3943 同类模式，复刻到 loader 路径）。
loader 的 _instantiate_component_from_file 因动态 exec_module 难以整体测试，
故把"取参数"提取为独立方法 _resolve_component_params 作为测试面（deep module）。
"""
import sys
import pytest
from pathlib import Path
from unittest.mock import MagicMock

project_root = Path(__file__).parent.parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)


def _make_param(index, value):
    p = MagicMock()
    p.index = index
    p.value = value
    return p


@pytest.mark.unit
class TestResolveComponentParams:
    """_resolve_component_params 用注入的 param_service 取参，json 解析 + 按 index 排序"""

    def test_uses_injected_param_service_and_parses_values(self):
        from ginkgo.trading.services._assembly.component_loader import ComponentLoader

        mock_param_service = MagicMock()
        # index 故意乱序，验证按 index 排序
        mock_param_service.find_by_mapping_id.return_value = [
            _make_param(1, "14"),
            _make_param(0, '"TestStrategy"'),
        ]
        loader = ComponentLoader(param_service=mock_param_service)

        params, indices = loader._resolve_component_params("mapping-1")

        # 走注入的 service，不走 container.cruds
        mock_param_service.find_by_mapping_id.assert_called_once_with("mapping-1")
        # 按 index 排序：0 在前
        assert indices == [0, 1]
        # json 解析：'"TestStrategy"'→"TestStrategy", "14"→14
        assert params == ["TestStrategy", 14]

    def test_no_params_returns_empty(self):
        """param_service 返回空 → ([], []) 不崩溃"""
        from ginkgo.trading.services._assembly.component_loader import ComponentLoader

        mock_param_service = MagicMock()
        mock_param_service.find_by_mapping_id.return_value = []
        loader = ComponentLoader(param_service=mock_param_service)

        params, indices = loader._resolve_component_params("mapping-empty")

        assert params == []
        assert indices == []

    def test_none_param_service_raises_not_silently_drops(self):
        """#6103 回归防护：param_service 未注入必须抛异常，禁止 WARN+返空。

        重构前 loader 内部用 container.cruds.param() 全局查找，对所有调用方生效；
        重构后改注入，凡漏传 param_service 的调用方（实盘/模拟盘/回测手写构造），
        若静默返空会让组件以默认参数实例化 → 用户策略阈值/手数/风控比例丢失。
        故 None 必须装配期即炸，而非静默退化。
        """
        from ginkgo.trading.services._assembly.component_loader import ComponentLoader

        loader = ComponentLoader(param_service=None)  # 模拟漏传的调用方
        with pytest.raises(ValueError, match="param_service not injected"):
            loader._resolve_component_params("mapping-x")
