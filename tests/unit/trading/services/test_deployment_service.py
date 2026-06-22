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


class TestDeploymentServiceAccountValidation:
    """#6281: deploy live 非法 account 应在校验阶段拦截，不穿透到 _deploy_core"""

    def test_deploy_live_rejects_nonexistent_account(self):
        """非法 account_id 在 deploy 阶段就被拦（#6281），不走到 _deploy_core 撞 DB 漂移"""
        svc = _make_svc()
        svc._portfolio_service.get.return_value = _mock_portfolio_found()
        svc._portfolio_service.is_portfolio_frozen.return_value = False
        # account 不存在
        svc._live_account_service.get_account_by_uuid.return_value = {"success": False, "data": None}
        # broker 查询返回空（未被占用）
        svc._broker_instance_crud.get_broker_by_live_account.return_value = []
        # 若穿透到 _deploy_core，说明存在性校验缺失
        svc._deploy_core = MagicMock(side_effect=AssertionError("account 校验应先拦截，不应走到 _deploy_core"))

        result = svc.deploy(portfolio_id="p1", mode=PORTFOLIO_MODE_TYPES.LIVE, account_id="fake_nonexistent")

        assert not result.success
        assert "实盘账户不存在" in result.error
        svc._live_account_service.get_account_by_uuid.assert_called_once_with("fake_nonexistent")
        svc._deploy_core.assert_not_called()

    def test_deploy_live_swallows_live_account_update_column_missing(self, monkeypatch):
        """#6281: 回写 live_account_id 遇 DB 漂移(列缺失)时降级，部署仍成功不裸抛 1054"""
        svc = _make_svc()
        svc._portfolio_service.get.return_value = _mock_portfolio_found()
        svc._portfolio_service.is_portfolio_frozen.return_value = False
        svc._live_account_service.get_account_by_uuid.return_value = {"success": True, "data": {"uuid": "acc"}}
        svc._broker_instance_crud.get_broker_by_live_account.return_value = []
        svc._deployment_crud.add.return_value = MagicMock(success=True, data=MagicMock(uuid="d1"))
        # _deploy_core 依赖
        svc._mapping_service.get_portfolio_mappings.return_value = MagicMock(success=True, data=[])
        svc._portfolio_service.add.return_value = MagicMock(success=True, data={"uuid": "new_pid"})
        svc._broker_instance_crud.add_broker_instance.return_value = None
        svc._deployment_crud.modify.return_value = None
        # update 回写 live_account_id 抛 1054（DB 漂移列缺失）
        svc._portfolio_service.update.side_effect = Exception("(1054, Unknown column 'portfolio.live_account_id')")
        # mock Kafka producer 避免真实连接
        monkeypatch.setattr("ginkgo.data.drivers.ginkgo_kafka.GinkgoProducer", MagicMock())

        result = svc.deploy(portfolio_id="p1", mode=PORTFOLIO_MODE_TYPES.LIVE, account_id="acc", name="L")

        assert result.success, f"update 列缺失应降级不阻断部署: {result.error}"
