"""
#3859 — 流式查询 SQL 注入修复 characterization tests

`_build_streaming_query` 历史 f-string 拼接 filter value（列名有 hasattr
白名单保护，但值无防护）。本测试验证 value 经参数化占位符绑定，注入字符串
被当字面值而非 SQL 片段。

Related: #3859
"""

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _import_or_skip(module_path: str, name: str):
    """Import a name from a module, skip test if import fails."""
    import importlib
    try:
        mod = importlib.import_module(module_path)
        return getattr(mod, name)
    except (ImportError, AttributeError, ModuleNotFoundError) as exc:
        pytest.skip(f"Cannot import {name} from {module_path}: {exc}")


def _make_crud():
    """构造最小 CRUD 实例，跳过 driver/session init。

    `_build_streaming_query` 只读 `self.model_class`（__tablename__ + hasattr 列
    检查），不碰其他实例状态，故 `object.__new__` 跳 `__init__` 后手动设
    `model_class` 即可。

    用真实 `StockInfoCRUD`（已 override `_model_class` 通过 `__init_subclass__`
    验证）而非自造假子类——`__init_subclass__` 强制 `_model_class` 继承
    MClickBase/MMysqlBase，假 model 无法绕过。
    """
    StockInfoCRUD = _import_or_skip(
        "ginkgo.data.crud.stock_info_crud", "StockInfoCRUD"
    )
    MStockInfo = _import_or_skip(
        "ginkgo.data.models.model_stock_info", "MStockInfo"
    )
    crud = object.__new__(StockInfoCRUD)
    crud.model_class = MStockInfo
    return crud


# ===========================================================================
# Slice 1 — tracer: equal 操作符 value 参数化（注入防护核心语义）
# ===========================================================================

class TestEqualOperatorParameterized:
    """filter value 经 %(name)s 占位符绑定，不拼进 SQL 字符串。"""

    def test_value_in_params_not_in_query(self):
        """注入字符串必须进 params dict，不出现在 SQL 模板里。"""
        crud = _make_crud()
        injection = "'; DROP TABLE fake_table; --"

        result = crud._build_streaming_query(filters={"code": injection})

        assert isinstance(result, tuple) and len(result) == 2, (
            "_build_streaming_query 必须返回 (query, params) 元组"
        )
        query, params = result

        # 注入字符串不应出现在 SQL 模板（当字面值被绑定）
        assert injection not in query
        assert "DROP TABLE" not in query.upper()
        # 注入字符串应在 params dict（参数化绑定）
        assert injection in list(params.values())

    def test_query_uses_named_placeholder(self):
        """SQL 模板用 %(name)s 命名占位符，value 不裸露。"""
        crud = _make_crud()

        query, params = crud._build_streaming_query(filters={"code": "000001"})

        assert "code = %(" in query, f"应用命名占位符: {query}"
        assert "000001" not in query
        assert "000001" in list(params.values())


# ===========================================================================
# Slice 2 — in 操作符：多值绑定多个独立占位符
# ===========================================================================

class TestInOperatorParameterized:
    def test_in_values_each_get_own_placeholder(self):
        crud = _make_crud()
        injection_in_list = "evil'); DROP TABLE t; --"
        values = ["000001", injection_in_list, "000002"]

        query, params = crud._build_streaming_query(filters={"code__in": values})

        # 注入字符串不进 SQL 模板
        assert "DROP" not in query.upper()
        assert "evil" not in query
        # 每个值在 params 里
        for v in values:
            assert v in list(params.values())
        # 三个独立占位符
        assert query.count("%(") == 3

    def test_in_non_iterable_skipped(self):
        """in 操作符 value 非 list/tuple 时静默跳过（保留原行为）。"""
        crud = _make_crud()

        query, params = crud._build_streaming_query(filters={"code__in": "000001"})

        assert "WHERE" not in query
        assert params == {}


# ===========================================================================
# Slice 3 — like 操作符：% 在 Python 值侧，SQL 模板无裸 %
# ===========================================================================

class TestLikeOperatorParameterized:
    def test_like_percent_in_value_not_in_template(self):
        crud = _make_crud()

        query, params = crud._build_streaming_query(filters={"code__like": "000"})

        assert "LIKE %(" in query
        assert "000" not in query  # value 不裸露
        bound = list(params.values())[0]
        assert bound == "%000%"  # % 包在绑定值侧
        # SQL 模板不应有裸 %（除 %(name)s 占位符语法）
        import re
        bare_pct = re.findall(r"%(?!\()", query)
        assert bare_pct == [], f"SQL 模板有裸 %: {bare_pct}"


# ===========================================================================
# Slice 4 — 比较操作符 gte/lte/gt/lt
# ===========================================================================

class TestComparisonOperatorsParameterized:
    @pytest.mark.parametrize("op,sql_op", [
        ("gte", ">="), ("lte", "<="), ("gt", ">"), ("lt", "<"),
    ])
    def test_comparison_value_bound_not_concatenated(self, op, sql_op):
        crud = _make_crud()
        injection = "1 OR 1=1"

        query, params = crud._build_streaming_query(
            filters={f"code__{op}": injection}
        )

        assert sql_op in query
        assert "%(" in query
        assert "1 OR 1=1" not in query
        assert injection in list(params.values())


# ===========================================================================
# Slice 5 — 边界：无 filters / 多条件 AND 唯一 key
# ===========================================================================

class TestEdgeCases:
    def test_no_filters_returns_plain_select(self):
        crud = _make_crud()

        query, params = crud._build_streaming_query(filters=None)

        assert query == "SELECT * FROM stock_info"
        assert params == {}

    def test_multiple_conditions_unique_param_keys(self):
        crud = _make_crud()

        query, params = crud._build_streaming_query(
            filters={"code": "000001", "code_name": "平安银行"}
        )

        assert query.count("%(") == 2
        assert len(params) == 2
        assert "000001" not in query
        assert "平安银行" not in query
        assert "000001" in list(params.values())
        assert "平安银行" in list(params.values())

    def test_order_by_unchanged(self):
        """order_by 列名白名单保护（非用户 value），行为不变。"""
        crud = _make_crud()

        query, params = crud._build_streaming_query(
            filters={"code": "000001"}, order_by="code", desc_order=True
        )

        assert query.endswith("ORDER BY code DESC")
        assert params == {"flt_code_eq_0": "000001"}


# ===========================================================================
# Slice 6 — stream_find 接线：params 流到 execute_stream（端到端）
# ===========================================================================

class TestStreamFindPassesParams:
    def test_stream_find_binds_params_to_execute_stream(self):
        """stream_find 必须把 _build_streaming_query 的 params 传给 execute_stream。"""
        from unittest.mock import MagicMock

        crud = _make_crud()
        fake_engine = MagicMock()
        fake_engine.execute_stream.return_value = iter([])
        crud._get_streaming_engine = lambda: fake_engine
        crud._streaming_config = None  # 避免降级分支

        injection = "'; DROP TABLE stock_info; --"
        list(crud.stream_find(filters={"code": injection}, batch_size=10))

        fake_engine.execute_stream.assert_called_once()
        kwargs = fake_engine.execute_stream.call_args.kwargs
        assert "params" in kwargs, "stream_find 未传 params 给 execute_stream"
        assert injection in list(kwargs["params"].values())
        assert "DROP" not in kwargs["query"].upper()
