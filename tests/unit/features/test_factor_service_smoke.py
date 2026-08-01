"""#6792/#6793/#6791 factor_service 新方法 smoke(#6685 diff coverage gate 采集)。

mock factor_engine/expression_engine/registry(不连 DB),调起三个新方法
各分支补覆盖信号:calculate_factors_by_library(增量物化 5 分支) /
walk_forward_factor_evaluation(走步切折) / calculate_alpha158_factors
(get_all_factors→get_all_expressions 改名)。
"""
import os
import sys
from unittest.mock import patch, MagicMock

_path = os.path.join(os.path.dirname(__file__), "..", "..", "..")
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.features.services.factor_service import FactorService
from ginkgo.data.services.base_service import ServiceResult

START = "2024-01-01"
END_SHORT = "2024-01-10"
END_LONG = "2024-12-31"


def _make_service() -> FactorService:
    """构造全依赖 mock 的 FactorService(GLOG/registry 隔离,不连 DB)。"""
    with patch("ginkgo.libs.GLOG"), \
         patch("ginkgo.features.definitions.registry.factor_registry", MagicMock()):
        return FactorService(factor_engine=MagicMock(), expression_engine=MagicMock())


def _ok(**data) -> ServiceResult:
    """成功 ServiceResult 速写。"""
    return ServiceResult(success=True, data=data)


def test_calculate_by_library_incremental_skips_materialized():
    """增量物化:已物化 entity 跳过,engine 只算未物化的(覆盖 168-203)。"""
    svc = _make_service()
    svc.factor_registry.get_factors_by_library.return_value = {"ROC5": "$close/shift(5)"}
    svc.expression_engine.validate_expressions.return_value = _ok()
    crud = MagicMock()
    crud.get_materialized_entities.return_value = {"A"}  # A 已物化 → 跳过
    svc.factor_engine.calculate_and_store.return_value = _ok(
        processed_entities=1, total_factors_stored=5)

    r = svc.calculate_factors_by_library(
        "alpha158", ["A", "B"], START, END_SHORT, incremental=True, factor_crud=crud)

    assert r.success
    assert r.data["skipped_entities"] == 1
    assert r.data["total_factors_stored"] == 5
    # target_ids 过滤掉 A,只剩 B
    assert svc.factor_engine.calculate_and_store.call_args.kwargs["entity_ids"] == ["B"]


def test_calculate_by_library_all_materialized_zero_write():
    """全已物化 → 零写入(processed/stored=0,不调 engine,覆盖 181-185)。"""
    svc = _make_service()
    svc.factor_registry.get_factors_by_library.return_value = {"ROC5": "..."}
    svc.expression_engine.validate_expressions.return_value = _ok()
    crud = MagicMock()
    crud.get_materialized_entities.return_value = {"A", "B"}  # 全已物化

    r = svc.calculate_factors_by_library("alpha158", ["A", "B"], START, END_SHORT, factor_crud=crud)

    assert r.success
    assert r.data["processed_entities"] == 0
    assert r.data["total_factors_stored"] == 0
    svc.factor_engine.calculate_and_store.assert_not_called()


def test_calculate_by_library_library_not_found():
    """library 找不到 → error(覆盖 156-158)。"""
    svc = _make_service()
    svc.factor_registry.get_factors_by_library.return_value = {}

    r = svc.calculate_factors_by_library("ghost", ["A"], START, END_SHORT)

    assert not r.success
    assert "not found" in r.error
    svc.factor_engine.calculate_and_store.assert_not_called()


def test_calculate_by_library_validation_fails():
    """表达式验证失败 → error(覆盖 160-163)。"""
    svc = _make_service()
    svc.factor_registry.get_factors_by_library.return_value = {"BAD": "$$$"}
    svc.expression_engine.validate_expressions.return_value = ServiceResult(success=False, error="syntax")

    r = svc.calculate_factors_by_library("alpha158", ["A"], START, END_SHORT)

    assert not r.success
    assert "验证失败" in r.error


def test_walk_forward_factor_evaluation_folds():
    """走步切折:evaluator 注入,产 n_folds 折 PIT(覆盖 254-323)。"""
    svc = _make_service()
    crud = MagicMock()
    crud.get_factors_by_entity.return_value = []  # 窗口空(不连 DB)
    evaluator = MagicMock(return_value=0.5)

    r = svc.walk_forward_factor_evaluation(
        "ROC5", ["A"], START, END_LONG, evaluator=evaluator, n_folds=3, factor_crud=crud)

    assert r.success
    assert len(r.data["folds"]) == 3
    assert r.data["n_folds"] == 3


def test_walk_forward_requires_crud():
    """crud None → error(覆盖 255-258)。"""
    svc = _make_service()

    r = svc.walk_forward_factor_evaluation(
        "ROC5", ["A"], START, END_LONG, evaluator=lambda f: 0, factor_crud=None)

    assert not r.success
    assert "required" in r.error


def test_calculate_alpha158_uses_get_all_expressions():
    """calculate_alpha158_factors 走 get_all_expressions 改名行(覆盖 81, #6791 命名修复)。"""
    svc = _make_service()
    svc.factor_engine.calculate_and_store.return_value = _ok(
        processed_entities=1, total_factors_stored=1)

    with patch("ginkgo.features.definitions.Alpha158Factors.get_all_expressions",
               return_value={"ROC5": "$close/shift(5)"}) as m:
        r = svc.calculate_alpha158_factors(["A"], START, END_SHORT)
        m.assert_called_once()

    assert r.success
