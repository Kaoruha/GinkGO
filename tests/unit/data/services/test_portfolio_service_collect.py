"""
PortfolioService.collect_portfolio_components 单元测试

验证：从 client/portfolio_cli.py 并入的数据装配逻辑（读 file_mapping 按类型分组 +
读 param 按 file_id 分配 + JSON 解析），返回 ServiceResult。
"""

import sys
import os
import pytest
from unittest.mock import MagicMock, patch

_path = os.path.join(os.path.dirname(__file__), '..', '..', '..')
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.data.services.portfolio_service import PortfolioService
from ginkgo.data.services.base_service import ServiceResult
from ginkgo.enums import FILE_TYPES


@pytest.fixture
def mock_deps():
    return {
        "crud_repo": MagicMock(),
        "portfolio_file_mapping_crud": MagicMock(),
        "param_crud": MagicMock(),
    }


@pytest.fixture
def service(mock_deps):
    with patch("ginkgo.libs.GLOG"):
        svc = PortfolioService(
            crud_repo=mock_deps["crud_repo"],
            portfolio_file_mapping_crud=mock_deps["portfolio_file_mapping_crud"],
            param_crud=mock_deps["param_crud"],
        )
        return svc


def _make_mapping(uuid, file_id, name, mtype):
    """构造 mock file_mapping 对象"""
    m = MagicMock()
    m.uuid = uuid
    m.file_id = file_id
    m.name = name
    m.type = mtype
    return m


def _make_param(mapping_id, index, value):
    """构造 mock param 对象"""
    p = MagicMock()
    p.mapping_id = mapping_id
    p.index = index
    p.value = value
    return p


# ============================================================
# 切片 1（tracer bullet）：正常路径 — 分组 + 参数分配 + JSON 解析 + 字段契约
# ============================================================

def test_collect_portfolio_components_groups_by_type_with_params(service, mock_deps):
    """给定 1 strategy + 1 selector 各自带参数，按类型分组并正确分配参数。

    锁定契约：输出 dict 5 key 齐全；元素含 {name, file_id, type, mapping_uuid,
    parameters:[{index, value, raw_value}]}；`[...]` value 解析为 list。
    """
    # Arrange: file_mapping 返回 1 strategy + 1 selector
    strat_mapping = _make_mapping("mount-s1", "file-s1", "MyStrategy", FILE_TYPES.STRATEGY.value)
    sel_mapping = _make_mapping("mount-sel1", "file-sel1", "FixedSelector", FILE_TYPES.SELECTOR.value)
    mock_deps["portfolio_file_mapping_crud"].find.return_value = [strat_mapping, sel_mapping]

    # param_crud.find 按 mapping_id 返回不同参数
    strat_param = _make_param("mount-s1", index=0, value="MyStrategy")
    sel_param = _make_param("mount-sel1", index=0, value='["SP500", "NASDAQ"]')

    def param_find(filters):
        mid = filters.get("mapping_id")
        if mid == "mount-s1":
            return [strat_param]
        if mid == "mount-sel1":
            return [sel_param]
        return []
    mock_deps["param_crud"].find.side_effect = param_find

    # Act
    result = service.collect_portfolio_components(portfolio_id="port-001")

    # Assert: ServiceResult 成功
    assert result.is_success()
    data = result.data

    # 5 key 齐全（即使空 list）
    assert set(data.keys()) == {"strategies", "risk_managers", "analyzers", "selectors", "sizers"}
    assert len(data["strategies"]) == 1
    assert len(data["selectors"]) == 1
    assert len(data["risk_managers"]) == 0
    assert len(data["analyzers"]) == 0
    assert len(data["sizers"]) == 0

    # strategy 元素字段契约
    strat = data["strategies"][0]
    assert strat["file_id"] == "file-s1"
    assert strat["name"] == "MyStrategy"
    assert strat["mapping_uuid"] == "mount-s1"
    assert strat["type"] == FILE_TYPES.STRATEGY.value
    assert len(strat["parameters"]) == 1
    assert strat["parameters"][0]["index"] == 0
    assert strat["parameters"][0]["value"] == "MyStrategy"  # 非 JSON → 原值
    assert strat["parameters"][0]["raw_value"] == "MyStrategy"

    # selector 参数 JSON 解析
    sel = data["selectors"][0]
    assert sel["parameters"][0]["value"] == ["SP500", "NASDAQ"]  # JSON 解析为 list
    assert sel["parameters"][0]["raw_value"] == '["SP500", "NASDAQ"]'  # 原始串保留


# ============================================================
# 切片 2：空 portfolio — 5 key 均为空 list
# ============================================================

def test_collect_returns_empty_lists_for_portfolio_with_no_bindings(service, mock_deps):
    """portfolio 无组件绑定 → 5 key 均为空 list（结构完整）。"""
    mock_deps["portfolio_file_mapping_crud"].find.return_value = []

    result = service.collect_portfolio_components(portfolio_id="port-empty")

    assert result.is_success()
    data = result.data
    assert set(data.keys()) == {"strategies", "risk_managers", "analyzers", "selectors", "sizers"}
    for v in data.values():
        assert v == []


# ============================================================
# 切片 3：异常路径 — param_crud 未注入 → ServiceResult 失败（不静默）
# ============================================================

def test_collect_returns_error_when_param_crud_not_injected(mock_deps):
    """param_crud 未注入 → ServiceResult 失败（对齐 #6103 不静默 WARN+返空）。"""
    with patch("ginkgo.libs.GLOG"):
        svc = PortfolioService(
            crud_repo=mock_deps["crud_repo"],
            portfolio_file_mapping_crud=mock_deps["portfolio_file_mapping_crud"],
            # 不传 param_crud
        )

    result = svc.collect_portfolio_components(portfolio_id="port-001")

    assert not result.is_success()
    assert "param_crud not injected" in result.error
    # 短路：file_mapping_crud 不应被调用
    mock_deps["portfolio_file_mapping_crud"].find.assert_not_called()


# ============================================================
# 切片 4：参数按 index 排序（多参数乱序输入）
# ============================================================

def test_collect_sorts_params_by_index(service, mock_deps):
    """同一组件多个参数乱序返回 → 按 index 升序排列。"""
    mapping = _make_mapping("mount-1", "file-1", "MyStrategy", FILE_TYPES.STRATEGY.value)
    mock_deps["portfolio_file_mapping_crud"].find.return_value = [mapping]

    # 故意乱序返回
    p2 = _make_param("mount-1", index=2, value="third")
    p0 = _make_param("mount-1", index=0, value="first")
    p1 = _make_param("mount-1", index=1, value="second")
    mock_deps["param_crud"].find.return_value = [p2, p0, p1]

    result = service.collect_portfolio_components(portfolio_id="port-1")

    assert result.is_success()
    params = result.data["strategies"][0]["parameters"]
    assert [p["index"] for p in params] == [0, 1, 2]
    assert [p["value"] for p in params] == ["first", "second", "third"]
