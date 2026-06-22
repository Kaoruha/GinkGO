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

    def test_deploy_live_fails_when_account_update_fails(self):
        """#6073 LIVE 部署回写 live_account_id 失败时 deploy 应返回 error，不应静默成功。

        根因: _deploy_core step5c 调 portfolio_service.update 后丢弃返回值，
        update 失败时 live_account_id 未写入但部署仍标记成功，portfolio 与 account 关联丢失。
        """
        svc = _make_svc()
        source = MagicMock()
        source.name = "Src"
        source.initial_capital = 100000
        svc._portfolio_service.get.return_value = MagicMock(success=True, data=[source])
        svc._portfolio_service.is_portfolio_frozen.return_value = False
        svc._broker_instance_crud.get_broker_by_live_account.return_value = []  # 无冲突
        # _deploy_core 依赖
        svc._mapping_service.get_portfolio_mappings.return_value = MagicMock(success=True, data=[])
        svc._portfolio_service.add.return_value = MagicMock(success=True, data={"uuid": "new_pid"})
        # 关键: 回写 live_account_id 失败
        svc._portfolio_service.update.return_value = MagicMock(success=False, error="update failed")
        svc._deployment_crud.modify.return_value = None

        result = svc.deploy(portfolio_id="src", mode=PORTFOLIO_MODE_TYPES.LIVE, account_id="acc-1")

        # 失败时 deploy 必须返回 error，不得静默成功
        assert not result.success, f"update 失败时 deploy 不应静默成功: {result.error}"
        # 行为断言: update 被调用且传了 live_account_id
        svc._portfolio_service.update.assert_called_once()
        _, kwargs = svc._portfolio_service.update.call_args
        assert kwargs.get("live_account_id") == "acc-1"

    def test_deploy_live_succeeds_when_account_update_succeeds(self):
        """#6073 回归保护: update 成功时 LIVE 部署应正常完成，不得因检查逻辑误伤 happy path。"""
        svc = _make_svc()
        source = MagicMock()
        source.name = "Src"
        source.initial_capital = 100000
        svc._portfolio_service.get.return_value = MagicMock(success=True, data=[source])
        svc._portfolio_service.is_portfolio_frozen.return_value = False
        svc._broker_instance_crud.get_broker_by_live_account.return_value = []
        svc._mapping_service.get_portfolio_mappings.return_value = MagicMock(success=True, data=[])
        svc._portfolio_service.add.return_value = MagicMock(success=True, data={"uuid": "new_pid"})
        # update 成功
        svc._portfolio_service.update.return_value = MagicMock(success=True)
        svc._broker_instance_crud.add_broker_instance.return_value = MagicMock(success=True)
        svc._deployment_crud.modify.return_value = None

        result = svc.deploy(portfolio_id="src", mode=PORTFOLIO_MODE_TYPES.LIVE, account_id="acc-1")

        assert result.success, f"update 成功时 LIVE 部署应成功: {result.error}"


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


class TestDeploymentCloneKeepsAllBindings:
    """#6279: deploy 克隆必须保留全部组件绑定 (strategy/sizer 不被图同步删除)"""

    def _source_mappings(self):
        """4 类组件源映射 (selector/strategy/sizer/risk), 模拟 CLI bind-component 绑定"""
        return [
            {"uuid": "src_map_sel", "file_id": "f_sel", "type": 4, "name": "selector", "params": {}},
            {"uuid": "src_map_str", "file_id": "f_str", "type": 6, "name": "strategy", "params": {}},
            {"uuid": "src_map_siz", "file_id": "f_siz", "type": 5, "name": "sizer", "params": {}},
            {"uuid": "src_map_rsk", "file_id": "f_rsk", "type": 3, "name": "risk", "params": {}},
        ]

    def test_deploy_copies_all_four_mapping_types(self):
        """#6279 _deploy_core 必须对 4 类源映射各调一次 add_file + _copy_params_raw,
        而非只复制 risk/selector。"""
        svc = _make_svc()
        svc._mapping_service.get_portfolio_mappings.return_value = MagicMock(
            success=True, data=self._source_mappings()
        )
        svc._portfolio_service.add.return_value = MagicMock(success=True, data={"uuid": "new_pid"})
        # add_file 每次返回新 mapping_id
        svc._mapping_service.add_file.side_effect = [
            MagicMock(success=True, data={"mapping_id": f"new_map_{i}"}) for i in range(4)
        ]
        # _copy_params_raw 依赖: 源每条映射 1 个 param
        svc._param_crud.find_by_mapping_id.return_value = [MagicMock(index=0, value="v", source=0)]
        svc._deployment_crud.modify.return_value = None
        # 关闭图拷贝路径以便隔离测 mapping 循环 (图路径单独测)
        svc._mongo_driver = None

        result = svc._deploy_core(
            source_portfolio_id="src_pid",
            mode=PORTFOLIO_MODE_TYPES.PAPER,
            account_id=None,
            name="Paper",
            portfolio_name="Src",
            deployment_id="d1",
        )

        assert result.success, f"_deploy_core 应成功: {result.error}"
        # 4 类组件必须各复制一次 (回归锚点: 旧 bug 只复制 risk/selector 2 类)
        assert svc._mapping_service.add_file.call_count == 4, (
            f"应复制全部 4 类映射, 实际 {svc._mapping_service.add_file.call_count}"
        )
        # 参数原始复制也要 4 次
        assert svc._param_crud.add.call_count == 4

    def test_deploy_copy_graph_uses_sync_mysql_false(self):
        """#6279 图拷贝必须传 sync_mysql=False, 否则 create_from_graph_editor 会删掉
        deploy step5 已建的 strategy/sizer 映射 (它们不在源 Mongo 图里)。"""
        svc = _make_svc()
        svc._mapping_service.get_portfolio_mappings.return_value = MagicMock(
            success=True, data=self._source_mappings()
        )
        svc._portfolio_service.add.return_value = MagicMock(success=True, data={"uuid": "new_pid"})
        svc._mapping_service.add_file.side_effect = [
            MagicMock(success=True, data={"mapping_id": f"new_map_{i}"}) for i in range(4)
        ]
        svc._param_crud.find_by_mapping_id.return_value = []
        svc._deployment_crud.modify.return_value = None
        # 开启图拷贝路径
        svc._mongo_driver = MagicMock()
        svc._mapping_service.get_portfolio_graph.return_value = MagicMock(
            success=True, data={"nodes": [], "edges": []}
        )
        svc._mapping_service.create_from_graph_editor.return_value = MagicMock(success=True)

        result = svc._deploy_core(
            source_portfolio_id="src_pid",
            mode=PORTFOLIO_MODE_TYPES.PAPER,
            account_id=None,
            name="Paper",
            portfolio_name="Src",
            deployment_id="d1",
        )

        assert result.success, f"_deploy_core 应成功: {result.error}"
        svc._mapping_service.create_from_graph_editor.assert_called_once()
        _, kwargs = svc._mapping_service.create_from_graph_editor.call_args
        assert kwargs.get("sync_mysql") is False, (
            f"deploy 图拷贝必须 sync_mysql=False 以免覆盖 step5 映射, 实际 kwargs={kwargs}"
        )

