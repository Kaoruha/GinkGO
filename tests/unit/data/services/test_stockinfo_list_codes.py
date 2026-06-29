"""
#5866: StockinfoService.list_all_codes 单元测试（Mock 依赖）

bars sync 端点 codes=["all"] 需展开为 stockinfo 全表 code 列表，
此方法提供该展开能力的 service 层入口。
"""

import sys
import os
import pytest
from unittest.mock import patch, MagicMock

_path = os.path.join(os.path.dirname(__file__), '..', '..', '..')
if _path in sys.path:
    pass
else:
    sys.path.insert(0, _path)

from ginkgo.data.services.stockinfo_service import StockinfoService
from ginkgo.data.services.base_service import ServiceResult
from ginkgo.data.crud.model_conversion import ModelList


@pytest.fixture
def mock_deps():
    return {
        "crud_repo": MagicMock(),
        "data_source": MagicMock(),
    }


@pytest.fixture
def service(mock_deps):
    with patch("ginkgo.libs.GLOG"):
        return StockinfoService(
            crud_repo=mock_deps["crud_repo"],
            data_source=mock_deps["data_source"],
        )


class TestListAllCodes:
    """#5866: list_all_codes 列出 stockinfo 全表 code（供 bars sync codes=['all'] 展开）"""

    @pytest.mark.unit
    def test_returns_codes_from_all_stockinfo(self, service, mock_deps):
        """无过滤时返回所有 stockinfo 的 code 列表"""
        from types import SimpleNamespace
        # _find_modellist 返回可迭代的 model 列表；list_all_codes 遍历提取 .code
        mock_deps["crud_repo"].find.return_value = [
            SimpleNamespace(code="000001.SZ"),
            SimpleNamespace(code="000002.SZ"),
            SimpleNamespace(code="000026.SZ"),
        ]

        result = service.list_all_codes()

        assert result.success is True
        assert result.data == ["000001.SZ", "000002.SZ", "000026.SZ"]

    @pytest.mark.unit
    def test_returns_empty_list_when_no_stockinfo(self, service, mock_deps):
        """stockinfo 表空时返回空列表（非 error），调用方可据此判空"""
        mock_deps["crud_repo"].find.return_value = []

        result = service.list_all_codes()

        assert result.success is True
        assert result.data == []

    @pytest.mark.unit
    def test_returns_error_when_crud_fails(self, service, mock_deps):
        """crud 异常时返回 ServiceResult.error（不向上抛）"""
        mock_deps["crud_repo"].find.side_effect = RuntimeError("DB down")

        result = service.list_all_codes()

        assert result.success is False
