"""
#5808 — add_file 重复绑定去重

表象：POST /node-graphs/{uuid}/files 同一组件多次绑定，mappings 出现重复 auto_binding 条目。
根因：portfolio_mapping_service.add_file 类型校验后直接落库 MPortfolioFileMapping，
      不检查同 (portfolio_uuid, file_id) 是否已存在绑定。
契约：
  - 同 (portfolio, file_id) 已绑定时，add_file 幂等返回已存在 mapping，不创建重复条目
  - 返回 data 标记 already_existed=True，供调用方区分新绑定 vs 已存在
  - 未绑定时正常创建（已由 test_portfolio_mapping_add_file_type_validation 覆盖）
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
    fake_file = MagicMock()
    fake_file.type = type_int
    fake_file.name = name
    return ServiceResult.success(data={"file": fake_file})


class TestAddFileDedup:
    """add_file 重复绑定时必须幂等，不产生重复 mapping (#5808)"""

    def test_already_bound_returns_existing_no_duplicate(self):
        """同 (portfolio, file_id) 已绑定 → 返已存在 mapping，不新增"""
        svc, mock_mapping, mock_file = _make_svc()
        mock_file.get_by_uuid.return_value = _file_found(FILE_TYPES.STRATEGY.value)

        existing = MagicMock()
        existing.uuid = "existing-mapping"
        existing.file_id = "f1"
        existing.type = FILE_TYPES.STRATEGY
        mock_mapping.find_by_portfolio.return_value = [existing]

        result = svc.add_file(
            portfolio_uuid="p1",
            file_id="f1",
            file_type=FILE_TYPES.STRATEGY,
        )

        assert result.success, "已绑定时应幂等返回 success，而非报错或重复创建"
        assert result.data["mapping_id"] == "existing-mapping", "应返回已存在 mapping 的 id"
        assert result.data.get("already_existed") is True, "应标记 already_existed 供调用方区分"
        # 关键：不创建重复 mapping
        mock_mapping.add.assert_not_called()

    def test_different_file_still_creates(self):
        """portfolio 已绑定 f1，再绑 f2 → f2 正常创建（去重不影响新绑定）"""
        svc, mock_mapping, mock_file = _make_svc()
        mock_file.get_by_uuid.return_value = _file_found(FILE_TYPES.STRATEGY.value)

        existing = MagicMock()
        existing.uuid = "m1"
        existing.file_id = "f1"  # 已绑定的是 f1，不是 f2
        existing.type = FILE_TYPES.STRATEGY
        mock_mapping.find_by_portfolio.return_value = [existing]

        new_mapping = MagicMock()
        new_mapping.uuid = "m2"
        mock_mapping.add.return_value = new_mapping

        result = svc.add_file(
            portfolio_uuid="p1",
            file_id="f2",
            file_type=FILE_TYPES.STRATEGY,
        )

        assert result.success
        assert result.data["mapping_id"] == "m2"
        assert result.data.get("already_existed") is not True, "新绑定不应标记 already_existed"
        mock_mapping.add.assert_called_once()
