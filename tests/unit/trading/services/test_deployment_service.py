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
from ginkgo.enums import PORTFOLIO_MODE_TYPES, FILE_TYPES

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


class TestDeploymentServiceCloneCompleteness:
    """#6279 回归测试: deploy 克隆须完整镜像源组合全部组件绑定(含 strategy/sizer)。

    背景: issue 报告 paper 部署后 Strategies:0(只见 risk+selector 2 类)。
    验证当前 _deploy_core 经 deploy() 公共接口完整复制 4 类 mapping + 参数。
    #6164 曾修 deploy 丢参, 本测试锁定克隆完整性防回归。
    """

    @staticmethod
    def _four_mappings():
        """源组合 4 类完整绑定(selector/strategy/sizer/risk)"""
        return [
            {"uuid": "m_sel", "file_id": "f_sel", "type": FILE_TYPES.SELECTOR.value, "name": "sel"},
            {"uuid": "m_str", "file_id": "f_str", "type": FILE_TYPES.STRATEGY.value, "name": "strat"},
            {"uuid": "m_siz", "file_id": "f_siz", "type": FILE_TYPES.SIZER.value, "name": "sizer"},
            {"uuid": "m_rsk", "file_id": "f_rsk", "type": FILE_TYPES.RISKMANAGER.value, "name": "risk"},
        ]

    @staticmethod
    def _make_clone_svc():
        svc = _make_svc()
        svc._portfolio_service.get.return_value = _mock_portfolio_found()
        svc._portfolio_service.is_portfolio_frozen.return_value = False
        svc._mapping_service.get_portfolio_mappings.return_value = MagicMock(
            success=True, data=TestDeploymentServiceCloneCompleteness._four_mappings()
        )
        svc._portfolio_service.add.return_value = MagicMock(success=True, data={"uuid": "new_pid"})
        svc._mapping_service.add_file.return_value = MagicMock(
            success=True, data={"mapping_id": "new_m"}
        )
        svc._deployment_crud.add.return_value = MagicMock(success=True, data=MagicMock(uuid="d1"))
        svc._deployment_crud.modify.return_value = None
        svc._mapping_service.get_portfolio_graph.return_value = MagicMock(
            success=True, data={"nodes": [], "edges": []}
        )
        svc._mapping_service.create_from_graph_editor.return_value = MagicMock(success=True)
        svc._param_crud.find_by_mapping_id.return_value = []
        return svc

    def test_deploy_paper_clones_all_four_component_types(self):
        """PAPER 部署须复制全部 4 类组件绑定(含 strategy/sizer), 不得漏类型。

        防回归: issue 指控 strategy/sizer 被漏(只复制 risk+selector)。
        """
        svc = self._make_clone_svc()
        result = svc.deploy(portfolio_id="src", mode=PORTFOLIO_MODE_TYPES.PAPER, name="Clone")
        assert result.success, f"deploy 应成功: {result.error}"
        # 核心: add_file 须被调用 4 次(4 类全复制)
        assert svc._mapping_service.add_file.call_count == 4, (
            f"应复制 4 类 mapping, 实际 {svc._mapping_service.add_file.call_count}"
        )
        cloned_types = {
            c.kwargs.get("file_type") for c in svc._mapping_service.add_file.call_args_list
        }
        # 防回归重点: strategy 和 sizer 必须在复制结果(issue 指控漏的两类)
        assert FILE_TYPES.STRATEGY in cloned_types, f"strategy 未被克隆: {cloned_types}"
        assert FILE_TYPES.SIZER in cloned_types, f"sizer 未被克隆: {cloned_types}"
        assert cloned_types == {
            FILE_TYPES.SELECTOR, FILE_TYPES.STRATEGY, FILE_TYPES.SIZER, FILE_TYPES.RISKMANAGER,
        }, f"克隆类型集合不符: {cloned_types}"

    def test_deploy_paper_clones_mapping_params(self):
        """部署须复制每个 mapping 的参数(_copy_params_raw 对每个源 mapping 触发)"""
        svc = self._make_clone_svc()
        fake_param = MagicMock()
        svc._param_crud.find_by_mapping_id.return_value = [fake_param]
        result = svc.deploy(portfolio_id="src", mode=PORTFOLIO_MODE_TYPES.PAPER, name="Clone")
        assert result.success, f"deploy 应成功: {result.error}"
        # find_by_mapping_id 须对每个源 mapping 调用(4 类 params 各读取一次)
        assert svc._param_crud.find_by_mapping_id.call_count == 4, (
            f"应读取 4 个 mapping 的 params, 实际 "
            f"{svc._param_crud.find_by_mapping_id.call_count}"
        )
        # 参数须写入新 mapping(_copy_params_raw 调 param_crud.add)
        assert svc._param_crud.add.called, "参数未复制到新 mapping"
