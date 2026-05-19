"""
EngineAssemblyService._instantiate_component CRUD 直调修复测试

#3943 code review: _instantiate_component 应通过 ParamService 而非 container.cruds.param() 获取参数。
"""
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
import sys

project_root = Path(__file__).parent.parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.trading.services.engine_assembly_service import EngineAssemblyService


def _make_param(index, value):
    p = MagicMock()
    p.index = index
    p.value = value
    return p


@pytest.mark.unit
class TestInstantiateComponentUsesParamService:
    """#3943: _instantiate_component 应通过 Service 层获取参数，不直接访问 CRUD"""

    def test_uses_param_service_not_crud(self):
        """当 mount_id 存在时，应调用 ParamService.find_by_mapping_id 而非 container.cruds.param()"""
        service = EngineAssemblyService()

        mock_param_service = MagicMock()
        mock_param_service.find_by_mapping_id.return_value = [
            _make_param(0, '"TestStrategy"'),
        ]

        mock_file_service = MagicMock()
        mock_file_result = MagicMock()
        mock_file_result.success = False
        mock_file_result.data = None
        mock_file_service.get_by_uuid.return_value = mock_file_result

        # ServiceHub.data returns a namespace with .param_service() etc.
        mock_data_ns = MagicMock()
        mock_data_ns.param_service.return_value = mock_param_service
        mock_data_ns.file_service.return_value = mock_file_service

        mock_hub = MagicMock()
        mock_hub.data = mock_data_ns

        # Patch the ServiceHub singleton that `from ginkgo import services` returns
        import ginkgo
        with patch.object(ginkgo, "services", mock_hub):
            config = {"component_id": "file-123", "mount_id": "mount-456"}
            result = service._instantiate_component(config, "strategy")

            # ParamService should be called with mapping_id
            mock_param_service.find_by_mapping_id.assert_called_once_with("mount-456")
