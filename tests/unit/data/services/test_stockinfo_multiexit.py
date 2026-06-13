"""
ADR-010 Phase 4 Task 4.2：StockinfoService 多出口方法契约测试（类型即契约）。

出口① get_stockinfos_df -> data 是 pd.DataFrame
出口② get_stockinfos    -> data 是 List[StockInfo]
向后兼容 get()         -> 不再透传裸 ModelList

设计：用 MagicMock 桩 _crud_repo.find，返回真实 ModelList（带 mock crud_instance
支持 to_dataframe），断言 data 的运行时类型而非源码字面量（计划原 inspect 源码
断言与实现自相矛盾，已纠偏）。
"""

import sys
import os
import inspect

import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

_path = os.path.join(os.path.dirname(__file__), "..", "..", "..")
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.data.crud.model_conversion import ModelList
from ginkgo.data.services.stockinfo_service import StockinfoService
from ginkgo.entities import StockInfo


# ============================================================
# 辅助：构造 service + 桩 crud_repo.find
# ============================================================


def _make_empty_modellist() -> ModelList:
    """构造空 ModelList（to_dataframe 返空 DataFrame）。"""
    crud_stub = MagicMock()
    crud_stub._convert_models_to_dataframe.return_value = pd.DataFrame()
    return ModelList([], crud_stub)


def _make_service(find_return) -> StockinfoService:
    """StockinfoService 实例，_crud_repo.find 桩为 find_return。"""
    with patch("ginkgo.libs.GLOG"):
        crud_repo = MagicMock()
        crud_repo.find.return_value = find_return
        data_source = MagicMock()
        svc = StockinfoService(crud_repo=crud_repo, data_source=data_source)
    return svc


# ============================================================
# 出口① get_stockinfos_df
# ============================================================


@pytest.mark.unit
def test_get_stockinfos_df_returns_dataframe_empty():
    """出口①：空结果 data 是 pd.DataFrame，非 [] / None / ModelList。"""
    svc = _make_service(_make_empty_modellist())
    result = svc.get_stockinfos_df()
    assert result.success is True
    assert isinstance(result.data, pd.DataFrame)
    assert not isinstance(result.data, ModelList)
    assert len(result.data) == 0


@pytest.mark.unit
def test_get_stockinfos_df_exists_and_takes_same_params():
    """出口①方法存在且签名与 get() 一致（接受同样的过滤参数）。"""
    assert hasattr(StockinfoService, "get_stockinfos_df")
    sig = inspect.signature(StockinfoService.get_stockinfos_df)
    # 至少要能接受 code/limit 这些 get() 的常用参数
    assert "code" in sig.parameters
    assert "limit" in sig.parameters


# ============================================================
# 出口② get_stockinfos
# ============================================================


@pytest.mark.unit
def test_get_stockinfos_returns_empty_list():
    """出口②：空结果 data 是空 list（非 ModelList）。"""
    svc = _make_service(_make_empty_modellist())
    result = svc.get_stockinfos()
    assert result.success is True
    assert result.data == []
    assert isinstance(result.data, list)
    assert not isinstance(result.data, ModelList)


@pytest.mark.unit
def test_get_stockinfos_returns_entity_list():
    """出口②：非空结果元素是 StockInfo Entity。"""
    # 构造一条 MStockInfo（Mapper.from_model 会转 Entity）
    from ginkgo.data.models import MStockInfo

    model = MStockInfo(code="000001", code_name="平安银行", industry="银行")
    crud_stub = MagicMock()
    crud_stub._convert_models_to_dataframe.return_value = pd.DataFrame()
    model_list = ModelList([model], crud_stub)

    svc = _make_service(model_list)
    result = svc.get_stockinfos()
    assert result.success is True
    assert isinstance(result.data, list)
    assert len(result.data) == 1
    assert isinstance(result.data[0], StockInfo)
    assert result.data[0].code == "000001"


# ============================================================
# 向后兼容 get()
# ============================================================


@pytest.mark.unit
def test_backward_compat_get_no_longer_leaks_modellist():
    """get() 向后兼容，但 data 不再是裸 ModelList。"""
    svc = _make_service(_make_empty_modellist())
    result = svc.get()
    assert result.success is True
    assert not isinstance(result.data, ModelList)


@pytest.mark.unit
def test_backward_compat_get_returns_entity_list():
    """get() 委托到 Entity 出口 get_stockinfos()，返 List[StockInfo]。

    P0 修复：原 c7f64489 错委托到 DF 出口（get().data 是 DataFrame），
    破坏 kafka_service/tick_service/seeding 3 个真实调用方的迭代/.code/len 消费。
    现改委托 get_stockinfos()，返 List[StockInfo]，与原 ModelList 迭代语义兼容。
    """
    svc = _make_service(_make_empty_modellist())
    result = svc.get()
    assert isinstance(result.data, list)
    # 空 ModelList -> 空 list
    assert len(result.data) == 0
    # 关键回归点：不是 DataFrame（c7f64489 错委托的返回类型）
    assert not isinstance(result.data, pd.DataFrame)


# ============================================================
# DRY：三个出口共用 _build_filters / _build_query
# ============================================================


@pytest.mark.unit
def test_build_filters_extracted():
    """_build_filters 辅助方法已抽出（DRY）。"""
    assert hasattr(StockinfoService, "_build_filters")
