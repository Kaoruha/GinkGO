# Related: #6285
# deploy info 输出打磨：status 返回枚举名、source_task_id deploy 记录后回显。
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


def _mock_deployment(status=1, source_task_id=None):
    d = MagicMock()
    d.source_task_id = source_task_id
    d.target_portfolio_id = "t1"
    d.source_portfolio_id = "s1"
    d.mode = 1
    d.account_id = None
    d.status = status
    d.create_at = None
    return d


def _mock_portfolio_found():
    mp = MagicMock()
    mp.name = "Src"
    return MagicMock(success=True, data=[mp])


class TestDeploymentInfoStatusName:
    """#6285: get_deployment_info / list_deployments 返回 status_name 枚举名"""

    def test_info_returns_status_name_deployed(self):
        svc = _make_svc()
        svc._deployment_crud.get_by_target_portfolio.return_value = [_mock_deployment(status=1)]

        result = svc.get_deployment_info("t1")
        assert result.success
        assert result.data["status"] == 1  # 原始 int 仍保留（向后兼容）
        assert result.data["status_name"] == "DEPLOYED"

    def test_list_returns_status_name(self):
        svc = _make_svc()
        svc._deployment_crud.find.return_value = [_mock_deployment(status=0), _mock_deployment(status=3)]

        result = svc.list_deployments()
        assert result.success
        assert result.data[0]["status_name"] == "PENDING"
        assert result.data[1]["status_name"] == "STOPPED"

    def test_list_passes_pagination_to_find(self):
        svc = _make_svc()
        svc._deployment_crud.find.return_value = [_mock_deployment(status=0)]

        result = svc.list_deployments(page=1, page_size=10)

        assert result.success
        svc._deployment_crud.find.assert_called_once_with(
            page=1,
            page_size=10,
            order_by="create_at",
            desc_order=True,
        )

    def test_list_page_size_zero_disables_pagination(self):
        svc = _make_svc()
        svc._deployment_crud.find.return_value = [_mock_deployment(status=0)]

        result = svc.list_deployments(page=1, page_size=0)

        assert result.success
        svc._deployment_crud.find.assert_called_once_with(
            page=None,
            page_size=None,
            order_by="create_at",
            desc_order=True,
        )


class TestDeploymentRecordsSourceTask:
    """#6285: deploy 记录 source_task_id，info/list 回显"""

    def test_deploy_records_source_task_id(self):
        """deploy(--source-task) 传入的 task id 应写入 MDeployment.source_task_id"""
        svc = _make_svc()
        svc._portfolio_service.get.return_value = _mock_portfolio_found()
        svc._portfolio_service.is_portfolio_frozen.return_value = False
        svc._deploy_core = MagicMock(
            return_value=MagicMock(success=True, data={"portfolio_id": "p_new", "deployment_id": "d1"})
        )

        result = svc.deploy(
            portfolio_id="p1",
            mode=PORTFOLIO_MODE_TYPES.PAPER,
            source_task_id="backtest_task_abc",
        )
        assert result.success, f"deploy 应成功: {result.error}"

        svc._deployment_crud.add.assert_called_once()
        created = svc._deployment_crud.add.call_args.args[0]
        assert created.source_task_id == "backtest_task_abc"
