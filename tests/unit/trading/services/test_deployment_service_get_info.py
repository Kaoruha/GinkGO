# Related: #5952, #5939
# deploy info 传 deployment uuid（记录主键），不应被当 target_portfolio_id 查。
# get_deployment_info 改用 get_by_uuid，返回结果补 deployment_id 字段。
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)

from unittest.mock import MagicMock

from ginkgo.enums import PORTFOLIO_MODE_TYPES
from ginkgo.trading.services.deployment_service import DeploymentService


def _make_svc(**overrides):
    svc = DeploymentService.__new__(DeploymentService)
    svc._portfolio_service = overrides.get("portfolio_service", MagicMock())
    svc._mapping_service = overrides.get("mapping_service", MagicMock())
    svc._file_service = overrides.get("file_service", MagicMock())
    svc._deployment_crud = overrides.get("deployment_crud", MagicMock())
    svc._broker_instance_crud = overrides.get("broker_instance_crud", MagicMock())
    svc._live_account_service = overrides.get("live_account_service", MagicMock())
    svc._mongo_driver = overrides.get("mongo_driver", None)
    svc._param_crud = overrides.get("param_crud", MagicMock())
    return svc


def _mock_record(uuid="d00112621a4e406a8b87b8842ca82968"):
    record = MagicMock()
    record.uuid = uuid
    record.source_task_id = "src-task-1"
    record.target_portfolio_id = "tp-1"
    record.source_portfolio_id = "sp-1"
    record.mode = PORTFOLIO_MODE_TYPES.PAPER
    record.account_id = "acc-1"
    record.status = "ACTIVE"
    record.create_at = None
    return record


class TestDeploymentServiceGetInfo:

    def test_get_by_uuid_called_with_deployment_id(self):
        """#5952: get_deployment_info 按 deployment uuid 查询，不得用 target_portfolio_id 字段"""
        svc = _make_svc()
        svc._deployment_crud.get_by_uuid.return_value = [_mock_record()]

        svc.get_deployment_info("d00112621a4e406a8b87b8842ca82968")

        svc._deployment_crud.get_by_uuid.assert_called_once_with("d00112621a4e406a8b87b8842ca82968")
        svc._deployment_crud.get_by_target_portfolio.assert_not_called()

    def test_returns_record_with_deployment_id_field(self):
        """#5952: 返回结果必须含 deployment_id（与 list_deployments 输出对齐）"""
        svc = _make_svc()
        svc._deployment_crud.get_by_uuid.return_value = [_mock_record()]

        result = svc.get_deployment_info("d00112621a4e406a8b87b8842ca82968")

        assert result.success
        assert result.data["deployment_id"] == "d00112621a4e406a8b87b8842ca82968"
        assert result.data["target_portfolio_id"] == "tp-1"

    def test_not_found_returns_error(self):
        """#5952: uuid 无匹配记录时返回失败"""
        svc = _make_svc()
        svc._deployment_crud.get_by_uuid.return_value = []

        result = svc.get_deployment_info("nonexistent")

        assert not result.success
        assert "未找到" in result.error
