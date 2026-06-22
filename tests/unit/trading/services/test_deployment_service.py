# Related: #3625
# 测试签名已更新匹配当前 deploy(portfolio_id, mode, account_id, name) 接口
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)

import pytest
from unittest.mock import MagicMock
from ginkgo.enums import PORTFOLIO_MODE_TYPES

# #3626 已修: MDeployment() 实例化不再触发 MUserCredential mapper 错误, 全部测试可跑。
# deploy→_deploy_core 路径现可经公共接口测(见 test_deploy_propagates_source_initial_capital)。

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


def _mock_portfolio_found():
    mock_portfolio = MagicMock()
    mock_portfolio.name = "TestPortfolio"
    return MagicMock(success=True, data=[mock_portfolio])


class TestDeploymentServiceDeploy:

    def test_deploy_rejects_nonexistent_portfolio(self):
        """源组合不存在时应拒绝部署"""
        svc = _make_svc()
        svc._portfolio_service.get.return_value = MagicMock(success=False, data=None)

        result = svc.deploy(portfolio_id="nonexistent", mode=PORTFOLIO_MODE_TYPES.PAPER)
        assert not result.success
        assert "组合不存在" in result.error

    def test_deploy_rejects_frozen_portfolio(self):
        """已冻结的组合应拒绝部署"""
        svc = _make_svc()
        svc._portfolio_service.get.return_value = _mock_portfolio_found()
        svc._portfolio_service.is_portfolio_frozen.return_value = True

        result = svc.deploy(portfolio_id="p1", mode=PORTFOLIO_MODE_TYPES.PAPER)
        assert not result.success
        assert "已部署" in result.error

    def test_deploy_rejects_live_without_account(self):
        """实盘模式缺少 account_id 应拒绝"""
        svc = _make_svc()
        svc._portfolio_service.get.return_value = _mock_portfolio_found()
        svc._portfolio_service.is_portfolio_frozen.return_value = False

        result = svc.deploy(portfolio_id="p1", mode=PORTFOLIO_MODE_TYPES.LIVE, account_id=None)
        assert not result.success
        assert "account_id" in result.error

    def test_deploy_propagates_source_initial_capital(self):
        """#6200 部署时目标组合应继承源组合 initial_capital(非 service 默认 1000000)。

        根因: _deploy_core 调 portfolio_service.add 时漏传 initial_capital。
        通过公共 deploy() 接口验证: add 被调用时须带 initial_capital == 源组合 capital。
        """
        svc = _make_svc()
        # 源组合: capital=500000 (≠ service 默认 1000000, 才能区分"继承" vs "默认")
        source_portfolio = MagicMock()
        source_portfolio.name = "Src"
        source_portfolio.initial_capital = 500000
        svc._portfolio_service.get.return_value = MagicMock(success=True, data=[source_portfolio])
        svc._portfolio_service.is_portfolio_frozen.return_value = False
        # _deploy_core 依赖: 空映射、deployment_crud(MDeployment 已可实例化, #3626 已修)、add 返回 uuid
        svc._mapping_service.get_portfolio_mappings.return_value = MagicMock(success=True, data=[])
        svc._portfolio_service.add.return_value = MagicMock(success=True, data={"uuid": "new_pid"})
        svc._deployment_crud.modify.return_value = None

        result = svc.deploy(portfolio_id="src_pid", mode=PORTFOLIO_MODE_TYPES.PAPER, name="Deployed")

        assert result.success, f"deploy 应成功: {result.error}"
        # 行为断言: 创建目标组合时须透传源组合 capital
        svc._portfolio_service.add.assert_called_once()
        _, kwargs = svc._portfolio_service.add.call_args
        assert kwargs.get("initial_capital") == 500000, (
            f"部署未透传 initial_capital, add 收到 kwargs={kwargs}"
        )

    def test_deploy_paper_creates_deployment_and_calls_core(self):
        """PAPER 模式应创建 deployment 记录并调用 _deploy_core"""
        svc = _make_svc()
        svc._portfolio_service.get.return_value = _mock_portfolio_found()
        svc._portfolio_service.is_portfolio_frozen.return_value = False

        expected = MagicMock(success=True)
        expected.data = {"portfolio_id": "p_new", "deployment_id": "d1"}
        svc._deploy_core = MagicMock(return_value=expected)

        result = svc.deploy(portfolio_id="p1", mode=PORTFOLIO_MODE_TYPES.PAPER, name="Paper-001")
        assert result.success
        svc._deployment_crud.add.assert_called_once()
        svc._deploy_core.assert_called_once()


class TestDeploymentServiceErrorMessages:
    """#5327 错误信息不应重复"""

    def test_error_message_no_duplicate_prefix(self):
        """#5327 deploy 异常时 service error 不应包含 '部署失败:' 前缀（CLI 负责加）"""
        svc = _make_svc()
        svc._portfolio_service.get.return_value = _mock_portfolio_found()
        svc._portfolio_service.is_portfolio_frozen.return_value = False
        svc._deployment_crud.add.return_value = MagicMock(success=True, data=MagicMock(uuid="d1"))

        # _deploy_core 抛 RuntimeError（如 line 136: 创建Portfolio失败: ...）
        svc._deploy_core = MagicMock(side_effect=RuntimeError("创建Portfolio失败: 投资组合名称已存在"))

        result = svc.deploy(portfolio_id="p1", mode=PORTFOLIO_MODE_TYPES.PAPER, name="Dup")
        assert not result.success
        # service error 不应有 "部署失败:" 前缀（CLI 层加）
        assert not result.error.startswith("部署失败:")


class TestGetDeploymentInfo:
    """#5939: get_deployment_info 按 deployment_id(uuid 主键) 查, 非 target_portfolio_id。

    根因: deploy 返回的 Deployment ID 是部署记录 uuid, 但 info 命令按 target_portfolio_id
    查询, 致 deploy info <deployment_id> 报"未找到"。查询键须对齐主键(arch_backtest_id_boundary)。
    """

    def _make_deployment(self, uuid="d1"):
        d = MagicMock()
        d.uuid = uuid
        d.source_task_id = None
        d.target_portfolio_id = "tgt-1"
        d.source_portfolio_id = "src-1"
        d.mode = 1
        d.account_id = None
        d.status = 2
        d.create_at = None
        return d

    def test_get_info_by_deployment_id_uuid(self):
        """get_deployment_info(deployment_id) 按 uuid 查到正确记录。"""
        svc = _make_svc()
        dep = self._make_deployment(uuid="d-abc")
        svc._deployment_crud.get_by_uuid.return_value = [dep]

        result = svc.get_deployment_info("d-abc")

        assert result.success, result.error
        svc._deployment_crud.get_by_uuid.assert_called_once_with("d-abc")
        assert result.data["target_portfolio_id"] == "tgt-1"

    def test_get_info_not_found_returns_error(self):
        """deployment_id 查不到 → success=False + 未找到提示。"""
        svc = _make_svc()
        svc._deployment_crud.get_by_uuid.return_value = []

        result = svc.get_deployment_info("nonexistent-id")

        assert not result.success
        assert "未找到" in result.error
