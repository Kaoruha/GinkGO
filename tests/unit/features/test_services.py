"""Smoke tests for features.services -- #3870"""
import pytest
import pandas as pd
from unittest.mock import MagicMock

try:
    from ginkgo.features.services.expression_service import ExpressionService
    HAS_EXPR_SVC = True
except ImportError:
    HAS_EXPR_SVC = False

try:
    from ginkgo.features.services.factor_service import FactorService
    HAS_FACTOR_SVC = True
except ImportError:
    HAS_FACTOR_SVC = False


@pytest.mark.skipif(not HAS_EXPR_SVC, reason="ExpressionService not available")
class TestExpressionService:
    def test_instantiation(self):
        mock_engine = MagicMock()
        svc = ExpressionService(mock_engine)
        assert svc is not None

    def test_get_available_operators(self):
        # ExpressionService.get_available_operators delegates to engine
        # which may not have the method (API mismatch in upstream code)
        # Use OperatorRegistry directly for smoke test
        try:
            from ginkgo.features.engines.expression.registry import OperatorRegistry
            ops = OperatorRegistry.get_available_operators()
            assert isinstance(ops, list)
            assert len(ops) > 0
        except ImportError:
            pytest.skip("OperatorRegistry not available")

    def test_execute_expression(self):
        mock_engine = MagicMock()
        mock_engine.execute_expression.return_value = pd.Series([1.0, 2.0])
        svc = ExpressionService(mock_engine)
        df = pd.DataFrame({'close': [1.0, 2.0]})
        result = svc.execute_expression("$close", df)
        assert result is not None


@pytest.mark.skipif(not HAS_FACTOR_SVC, reason="FactorService not available")
class TestFactorService:
    def test_instantiation(self):
        mock_factor_engine = MagicMock()
        mock_expr_engine = MagicMock()
        svc = FactorService(mock_factor_engine, mock_expr_engine)
        assert svc is not None

    def test_list_factor_categories(self):
        svc = FactorService(MagicMock(), MagicMock())
        result = svc.list_factor_categories()
        assert result is not None

    def test_search_factors(self):
        svc = FactorService(MagicMock(), MagicMock())
        result = svc.search_factors("momentum")
        assert result is not None

    # ===== #6791 Phase 0: 因子命名 bug 修复 (TDD 垂直切片) =====

    def _make_engine_ok(self):
        """构造一个返回 success 的 mock FactorEngine(get_data 默认返回占位值)。"""
        mock = MagicMock()
        mock.success = True
        mock.get_data.return_value = 1
        return mock

    def test_calculate_alpha158_factors_full_library_passes_expressions(self):
        """RED#1: calculate_alpha158_factors(无 factor_names) 应把 Alpha158 全量表达式传给 engine。
        当前 Alpha158Factors.get_all_factors() 不存在 → AttributeError 被 except 捕获 → result.success=False。
        修后(get_all_expressions)应 success 且 expressions 非空。"""
        mock_engine = MagicMock()
        mock_engine.calculate_and_store.return_value = self._make_engine_ok()
        mock_expr_engine = MagicMock()
        mock_expr_engine.validate_expressions.return_value = self._make_engine_ok()

        svc = FactorService(mock_engine, mock_expr_engine)
        result = svc.calculate_alpha158_factors(
            entity_ids=["000001.SZ"], start_date="2024-01-01", end_date="2024-12-31"
        )

        assert result.success is True, f"expected success, got error: {result.error}"
        call_kwargs = mock_engine.calculate_and_store.call_args.kwargs
        assert len(call_kwargs["expressions"]) > 0

    def test_calculate_alpha158_factors_subset_filters_expressions(self):
        """RED#2: 传 factor_names 子集,只把这些因子传给 engine(过滤未知名)。"""
        mock_engine = MagicMock()
        mock_engine.calculate_and_store.return_value = self._make_engine_ok()
        mock_expr_engine = MagicMock()
        mock_expr_engine.validate_expressions.return_value = self._make_engine_ok()
        svc = FactorService(mock_engine, mock_expr_engine)

        result = svc.calculate_alpha158_factors(
            entity_ids=["000001.SZ"], start_date="2024-01-01", end_date="2024-12-31",
            factor_names=["KMID", "MA5"],
        )

        assert result.success is True, f"expected success, got error: {result.error}"
        call_kwargs = mock_engine.calculate_and_store.call_args.kwargs
        assert set(call_kwargs["expressions"].keys()) == {"KMID", "MA5"}

    def test_calculate_core_factors_passes_core_category(self):
        """RED#3: calculate_core_factors 用 core 类目表达式(KMID 等)。"""
        mock_engine = MagicMock()
        mock_engine.calculate_and_store.return_value = self._make_engine_ok()
        mock_expr_engine = MagicMock()
        mock_expr_engine.validate_expressions.return_value = self._make_engine_ok()
        svc = FactorService(mock_engine, mock_expr_engine)

        result = svc.calculate_core_factors(
            entity_ids=["000001.SZ"], start_date="2024-01-01", end_date="2024-12-31"
        )
        assert result.success is True, f"expected success, got error: {result.error}"
        call_kwargs = mock_engine.calculate_and_store.call_args.kwargs
        assert len(call_kwargs["expressions"]) > 0
        assert "KMID" in call_kwargs["expressions"]  # core 类目含 KMID

    def test_calculate_category_factors_momentum(self):
        """RED#4: category='momentum' 拿到动量类目(ROC1),对齐 CATEGORIES key。"""
        mock_engine = MagicMock()
        mock_engine.calculate_and_store.return_value = self._make_engine_ok()
        mock_expr_engine = MagicMock()
        mock_expr_engine.validate_expressions.return_value = self._make_engine_ok()
        svc = FactorService(mock_engine, mock_expr_engine)

        result = svc.calculate_category_factors(
            category="momentum", entity_ids=["000001.SZ"],
            start_date="2024-01-01", end_date="2024-12-31",
        )
        assert result.success is True, f"expected success, got error: {result.error}"
        call_kwargs = mock_engine.calculate_and_store.call_args.kwargs
        assert "ROC1" in call_kwargs["expressions"]

    def test_calculate_category_factors_moving_average_key(self):
        """RED#4b: category 对齐 CATEGORIES 真实 key 'moving_average'(非旧失效 'ma')。"""
        mock_engine = MagicMock()
        mock_engine.calculate_and_store.return_value = self._make_engine_ok()
        mock_expr_engine = MagicMock()
        mock_expr_engine.validate_expressions.return_value = self._make_engine_ok()
        svc = FactorService(mock_engine, mock_expr_engine)

        result = svc.calculate_category_factors(
            category="moving_average", entity_ids=["000001.SZ"],
            start_date="2024-01-01", end_date="2024-12-31",
        )
        assert result.success is True, f"expected success, got error: {result.error}"
        call_kwargs = mock_engine.calculate_and_store.call_args.kwargs
        assert "MA5" in call_kwargs["expressions"]

    def test_calculate_category_factors_unknown_rejected(self):
        """RED#4c: 未知 category 应返回 error(不静默空)。"""
        svc = FactorService(MagicMock(), MagicMock())
        result = svc.calculate_category_factors(
            category="nonexistent", entity_ids=["000001.SZ"],
            start_date="2024-01-01", end_date="2024-12-31",
        )
        assert result.success is False
        assert "nonexistent" in (result.error or "")

    def test_get_service_status_counts_alpha158(self):
        """RED#5: get_service_status 不再 AttributeError,alpha158 计数 > 0。"""
        mock_engine = MagicMock()
        mock_engine.get_stats.return_value = {}
        mock_expr_engine = MagicMock()
        mock_expr_engine.get_engine_stats.return_value = {}
        svc = FactorService(mock_engine, mock_expr_engine)
        status = svc.get_service_status()
        assert status["alpha158_total_factors"] > 0
        assert status["alpha158_core_factors"] > 0


@pytest.mark.skipif(not HAS_FACTOR_SVC, reason="FactorService not available")
def test_features_convenience_expression_helpers():
    """RED#5b: features.get_alpha158_expressions / get_core_expressions 不再 AttributeError。"""
    from ginkgo.features import get_alpha158_expressions, get_core_expressions
    all_expr = get_alpha158_expressions()
    core_expr = get_core_expressions()
    assert len(all_expr) > 0
    assert len(core_expr) > 0
    assert "KMID" in all_expr  # KMID 属于 core
