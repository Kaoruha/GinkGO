"""
MappingService client 层收口薄封装（#6456：消除 CLI→CRUD 直连）的委托正确性测试。

验证 get_active_portfolio_file_bindings / create_file_binding 忠实委托底层 CRUD，
语义（is_del 守卫 / raw create 无 dedup / type 原值透传）与原 portfolio_cli 直连
``portfolio_file_mapping().find(...).create(...)`` 一致。不依赖真实 DB。
"""
import pytest
from unittest.mock import MagicMock

from ginkgo.data.services.base_service import ServiceResult
from ginkgo.data.services.mapping_service import MappingService


def _svc():
    pfm = MagicMock()
    return MappingService(
        engine_portfolio_mapping_crud=MagicMock(),
        portfolio_file_mapping_crud=pfm,
        engine_handler_mapping_crud=MagicMock(),
        param_crud=MagicMock(),
    ), pfm


@pytest.mark.unit
class TestGetMappingServiceClientSeams:
    """get_active_portfolio_file_bindings / create_file_binding 委托正确性（#6456 service seam）。"""

    def test_get_active_bindings_filters_is_del_false(self):
        """get_active_portfolio_file_bindings 忠实传 is_del=False（排除已解绑软删组件）。"""
        svc, pfm = _svc()
        pfm.find.return_value = ["b1", "b2"]

        result = svc.get_active_portfolio_file_bindings(portfolio_uuid="P1")

        assert result.success
        pfm.find.assert_called_once_with(filters={"portfolio_id": "P1", "is_del": False})
        assert result.data == ["b1", "b2"]

    def test_get_active_bindings_distinct_from_get_portfolio_file_bindings(self):
        """与 get_portfolio_file_bindings 的差别：后者不带 is_del（含软删绑定）。"""
        svc, pfm = _svc()
        pfm.find.return_value = []

        svc.get_portfolio_file_bindings(portfolio_uuid="P1")

        # get_portfolio_file_bindings 仅 portfolio_id，无 is_del
        assert pfm.find.call_args.kwargs["filters"] == {"portfolio_id": "P1"}
        pfm.find.reset_mock()

        svc.get_active_portfolio_file_bindings(portfolio_uuid="P1")

        # get_active 额外带 is_del=False
        assert pfm.find.call_args.kwargs["filters"] == {"portfolio_id": "P1", "is_del": False}

    def test_get_active_bindings_error_returns_service_result_error(self):
        """CRUD 抛错 → ServiceResult.error（不向 client 传播异常）。"""
        svc, pfm = _svc()
        pfm.find.side_effect = Exception("DB error")

        result = svc.get_active_portfolio_file_bindings(portfolio_uuid="P1")

        assert not result.success
        assert "DB error" in result.error

    def test_create_file_binding_raw_create_no_dedup(self):
        """create_file_binding 忠实 raw create：直接 create，无 dedup find，type 取原值。

        与 create_portfolio_file_binding 的差别：后者含 dedup find + FILE_TYPES 枚举包装。
        paper-portfolio 复制路径要求 raw 语义（源含重复 file_id 时 dedup 会错误合并参数）。
        """
        svc, pfm = _svc()
        new_mapping = MagicMock(uuid="new-uuid")
        pfm.create.return_value = new_mapping

        result = svc.create_file_binding(
            portfolio_id="P1", file_id="F1", name="MyComp", file_type_value=6
        )

        # 无 dedup find（仅一次 create 调用）
        pfm.find.assert_not_called()
        pfm.create.assert_called_once_with(
            portfolio_id="P1", file_id="F1", name="MyComp", type=6
        )
        assert result is new_mapping
        assert result.uuid == "new-uuid"
