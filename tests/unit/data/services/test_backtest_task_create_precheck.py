"""#6640: backtest create 时校验 portfolio 必需组件（清单：strategy/selector/sizer，
与装配层 component_loader 实际要求的必需组件一致）。缺必需组件时拒绝创建并返回
具体组件名 + 绑定命令，而非让用户跑到 run 阶段才看到笼统的 'No portfolios bound to engine'。

预检在 service 层（API/CLI 共享），调 portfolio_service.get_components 查绑定组件。
"""
import pytest
from unittest.mock import MagicMock

from ginkgo.data.services.backtest_task_service import BacktestTaskService
from ginkgo.data.services.base_service import ServiceResult

_PORTFOLIO_ID = "aa11223344556677889900aabbccddee"

# 成员名 → 生产数字串映射（FILE_TYPES value，与 get_components 实际返回格式一致）。
# 生产路径：MPortfolioFileMapping.type 经 FILE_TYPES.validate_input 转 int 存储，
# get_components 用 `mapping.type.name if hasattr(mapping.type, "name") else str(mapping.type)`，
# int 无 .name → 返回 str(int)，即数字串 "6"/"4"/"5"。
# #6643 P0 回归保护：mock 必须用生产数字串格式，原 mock 用成员名 "STRATEGY" 掩盖了
# requirements.py str 分支对数字串的归一化 bug（全绿却生产炸）。
_MEMBER_TO_PROD = {"STRATEGY": "6", "SELECTOR": "4", "SIZER": "5"}


def _portfolio_service_with(*component_types):
    """构造 mock portfolio_service，get_components 返回含指定类型组件的 ServiceResult。

    component_type 字段模拟 PortfolioService.get_components 的【生产返回格式】：
    数字字符串（FILE_TYPES value 的 str 形式，"6"/"4"/"5"），非成员名 "STRATEGY"。
    调用方仍传可读成员名（"STRATEGY" 等），由本 helper 映射到生产格式。
    """
    svc = MagicMock()
    components = [
        {"component_type": _MEMBER_TO_PROD[t], "component_name": f"{t.lower()}_1"}
        for t in component_types
    ]
    svc.get_components.return_value = ServiceResult.success(components)
    return svc


class TestCreatePrecheck:
    """#6640: create() 预检 portfolio 必需组件（清单单点定义于装配层 requirements 模块）。"""

    @pytest.mark.unit
    def test_missing_sizer_rejected_with_bind_hint(self):
        """有 strategy+selector 缺 sizer → 拒绝创建 + 错误含 Sizer 与 bind-component 命令。"""
        crud = MagicMock()
        portfolio_svc = _portfolio_service_with("STRATEGY", "SELECTOR")
        svc = BacktestTaskService(crud, portfolio_service=portfolio_svc)

        result = svc.create(name="repro", portfolio_id=_PORTFOLIO_ID)

        assert not result.is_success(), "缺 Sizer 应拒绝创建"
        assert "Sizer" in result.error
        assert "bind-component" in result.error
        assert "--type sizer" in result.error
        # 拒绝创建：crud.create 未被调用
        crud.create.assert_not_called()

    @pytest.mark.unit
    def test_all_required_present_creates_normally(self):
        """回归保护：strategy+selector+sizer 齐全 → 正常创建，crud.create 被调用。"""
        crud = MagicMock()
        crud.create.return_value = MagicMock(uuid=_PORTFOLIO_ID)
        portfolio_svc = _portfolio_service_with("STRATEGY", "SELECTOR", "SIZER")
        svc = BacktestTaskService(crud, portfolio_service=portfolio_svc)

        result = svc.create(name="ok", portfolio_id=_PORTFOLIO_ID)

        assert result.is_success(), "必需组件齐全应正常创建"
        crud.create.assert_called_once()

    @pytest.mark.unit
    def test_no_portfolio_service_does_not_block_create(self):
        """向后兼容：portfolio_service 未注入（旧调用方）→ 不阻断创建。"""
        crud = MagicMock()
        crud.create.return_value = MagicMock(uuid=_PORTFOLIO_ID)
        svc = BacktestTaskService(crud)  # 不注入 portfolio_service

        result = svc.create(name="legacy", portfolio_id=_PORTFOLIO_ID)

        assert result.is_success(), "portfolio_service 未注入时应放行（保守）"
        crud.create.assert_called_once()

    @pytest.mark.unit
    def test_get_components_failure_does_not_block_create(self):
        """保守放行：portfolio_service.get_components 失败 → 不阻断（装配层兜底）。"""
        crud = MagicMock()
        crud.create.return_value = MagicMock(uuid=_PORTFOLIO_ID)
        portfolio_svc = MagicMock()
        portfolio_svc.get_components.return_value = ServiceResult.error("db error")
        svc = BacktestTaskService(crud, portfolio_service=portfolio_svc)

        result = svc.create(name="dbfail", portfolio_id=_PORTFOLIO_ID)

        assert result.is_success(), "get_components 失败应放行，交装配层兜底"
        crud.create.assert_called_once()

    @pytest.mark.unit
    def test_missing_multiple_components_lists_all(self):
        """缺 strategy+sizer（仅绑 selector）→ 错误信息含两者 + 各自绑定命令。"""
        crud = MagicMock()
        portfolio_svc = _portfolio_service_with("SELECTOR")
        svc = BacktestTaskService(crud, portfolio_service=portfolio_svc)

        result = svc.create(name="multi", portfolio_id=_PORTFOLIO_ID)

        assert not result.is_success()
        assert "Strategy" in result.error
        assert "Sizer" in result.error
        assert "--type strategy" in result.error
        assert "--type sizer" in result.error
