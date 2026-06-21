# #5776 — add_file 必须校验 file_id 实际类型与请求 file_type 一致
"""
表象：策略组件可被绑定到 selector/sizer/risk 角色（add_file 无类型校验）。
根因：portfolio_mapping_service.add_file 直接落库 MPortfolioFileMapping，
      不校验 MFile.type（文件实际类型）与请求 file_type 是否一致。
契约：
  - file_id 实际类型 ≠ 请求 file_type → ServiceResult.error，不创建 mapping
  - file_id 实际类型 == 请求 file_type → 正常创建 mapping
  - file_id 不存在 → ServiceResult.error
"""
from unittest.mock import MagicMock

from ginkgo.enums import FILE_TYPES
from ginkgo.data.services.portfolio_mapping_service import PortfolioMappingService
from ginkgo.data.services.base_service import ServiceResult


def _make_svc():
    mock_mapping = MagicMock()
    mock_param = MagicMock()
    mock_mongo = MagicMock()
    mock_file = MagicMock()
    svc = PortfolioMappingService(
        mapping_crud=mock_mapping,
        param_service=mock_param,
        mongo_driver=mock_mongo,
        file_service=mock_file,
    )
    return svc, mock_mapping, mock_file


def _file_found(type_int: int, name: str = "fake_component"):
    """构造 get_by_uuid 成功返回：data={"file": obj(.type=type_int)}"""
    fake_file = MagicMock()
    fake_file.type = type_int
    fake_file.name = name
    return ServiceResult.success(data={"file": fake_file})


class TestAddFileTypeValidation:
    """add_file 必须校验 file_id 实际类型与请求 file_type 一致"""

    def test_type_mismatch_rejected_no_mapping_created(self):
        """策略文件(STRATEGY=6) 不应能绑成 SELECTOR(4) 角色"""
        svc, mock_mapping, mock_file = _make_svc()
        mock_file.get_by_uuid.return_value = _file_found(FILE_TYPES.STRATEGY.value)

        result = svc.add_file(
            portfolio_uuid="p1",
            file_id="f1",
            file_type=FILE_TYPES.SELECTOR,
        )

        assert not result.success, "类型不匹配应被拒绝，实际返回 success"
        assert "mismatch" in result.error.lower(), f"错误信息应说明类型不匹配: {result.error}"
        # 关键：不应落库 mapping
        mock_mapping.add.assert_not_called()

    def test_type_match_accepted_mapping_created(self):
        """策略文件(STRATEGY=6) 绑成 STRATEGY(6) → 正常创建"""
        svc, mock_mapping, mock_file = _make_svc()
        mock_file.get_by_uuid.return_value = _file_found(FILE_TYPES.STRATEGY.value)
        mock_mapping_obj = MagicMock()
        mock_mapping_obj.uuid = "m1"
        mock_mapping.add.return_value = mock_mapping_obj

        result = svc.add_file(
            portfolio_uuid="p1",
            file_id="f1",
            file_type=FILE_TYPES.STRATEGY,
        )

        assert result.success, f"类型匹配应成功，实际: {result.error}"
        mock_mapping.add.assert_called_once()

    def test_file_not_found_rejected(self):
        """file_id 不存在 → 拒绝，不创建 mapping"""
        svc, mock_mapping, mock_file = _make_svc()
        mock_file.get_by_uuid.return_value = ServiceResult.error("File not found")

        result = svc.add_file(
            portfolio_uuid="p1",
            file_id="ghost-id",
            file_type=FILE_TYPES.STRATEGY,
        )

        assert not result.success
        mock_mapping.add.assert_not_called()
