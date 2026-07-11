"""
BaseCRUD 文件拆分 characterization test

验证 base_crud.py（2308 行）拆分为多文件后，BaseCRUD 的
公开 API 和子类兼容性不受影响。

Related: #3833
"""

import pytest
from abc import ABC
from typing import Generic


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


def _get_base_crud():
    return _import_or_skip("ginkgo.data.crud.base_crud", "BaseCRUD")


# ===========================================================================
# 1. MRO correctness — BaseCRUD 继承链包含各内部实现类
# ===========================================================================


class TestMROCorrectness:
    """BaseCRUD 的 MRO 必须包含 _CoreCRUD 和三个内部实现类。"""

    @pytest.mark.tdd
    @pytest.mark.refactor
    def test_mro_contains_core_crud(self):
        BaseCRUD = _get_base_crud()
        mro_names = [c.__name__ for c in BaseCRUD.__mro__]
        assert "_CoreCRUD" in mro_names, (
            f"_CoreCRUD not in BaseCRUD MRO: {mro_names}"
        )

    @pytest.mark.tdd
    @pytest.mark.refactor
    def test_mro_contains_conversion(self):
        BaseCRUD = _get_base_crud()
        mro_names = [c.__name__ for c in BaseCRUD.__mro__]
        assert "_Conversion" in mro_names, (
            f"_Conversion not in BaseCRUD MRO: {mro_names}"
        )

    @pytest.mark.tdd
    @pytest.mark.refactor
    def test_mro_contains_validation(self):
        BaseCRUD = _get_base_crud()
        mro_names = [c.__name__ for c in BaseCRUD.__mro__]
        assert "_Validation" in mro_names, (
            f"_Validation not in BaseCRUD MRO: {mro_names}"
        )

    @pytest.mark.tdd
    @pytest.mark.refactor
    def test_mro_contains_streaming(self):
        BaseCRUD = _get_base_crud()
        mro_names = [c.__name__ for c in BaseCRUD.__mro__]
        assert "_Streaming" in mro_names, (
            f"_Streaming not in BaseCRUD MRO: {mro_names}"
        )

    @pytest.mark.tdd
    @pytest.mark.refactor
    def test_mro_order_core_before_impls(self):
        """_CoreCRUD 必须在内部实现类之前出现。"""
        BaseCRUD = _get_base_crud()
        mro_names = [c.__name__ for c in BaseCRUD.__mro__]
        core_idx = mro_names.index("_CoreCRUD")
        conversion_idx = mro_names.index("_Conversion")
        assert core_idx < conversion_idx, (
            f"_CoreCRUD (idx={core_idx}) should appear before _Conversion (idx={conversion_idx})"
        )


# ===========================================================================
# 2. Method availability — _Conversion methods
# ===========================================================================


class TestConversionMethods:
    """类型转换方法必须在 BaseCRUD 上仍可访问。"""

    CONVERSION_METHODS = [
        "_create_from_params",
        "_convert_input_item",
        "_convert_input_batch",
        "_convert_output_items",
        "_get_enum_mappings",
        "_process_dataframe_output",
        "_convert_to_business_objects",
        "_convert_models_to_business_objects",
        "_convert_models_to_dataframe",
        "_safe_enum_convert",
        "_convert_enum_values",
        "_normalize_single_enum_value",
        "_validate_item_enum_fields",
    ]

    @pytest.mark.tdd
    @pytest.mark.refactor
    @pytest.mark.parametrize("method_name", CONVERSION_METHODS)
    def test_conversion_method_available(self, method_name):
        BaseCRUD = _get_base_crud()
        assert hasattr(BaseCRUD, method_name), f"BaseCRUD missing method: {method_name}"
        assert callable(getattr(BaseCRUD, method_name)), f"BaseCRUD.{method_name} is not callable"


# ===========================================================================
# 3. Method availability — _Validation methods
# ===========================================================================


class TestValidationMethods:
    """验证方法必须在 BaseCRUD 上仍可访问。"""

    VALIDATION_METHODS = [
        "_validate_before_database",
        "_get_field_config",
        "_get_database_required_config",
        "_get_mysql_required_config",
        "_get_clickhouse_required_config",
        "_clean_clickhouse_strings",
    ]

    @pytest.mark.tdd
    @pytest.mark.refactor
    @pytest.mark.parametrize("method_name", VALIDATION_METHODS)
    def test_validation_method_available(self, method_name):
        BaseCRUD = _get_base_crud()
        assert hasattr(BaseCRUD, method_name), f"BaseCRUD missing method: {method_name}"
        assert callable(getattr(BaseCRUD, method_name)), f"BaseCRUD.{method_name} is not callable"

    @pytest.mark.tdd
    @pytest.mark.refactor
    def test_clickhouse_string_fields_class_attribute(self):
        BaseCRUD = _get_base_crud()
        assert hasattr(BaseCRUD, "CLICKHOUSE_STRING_FIELDS"), "BaseCRUD missing CLICKHOUSE_STRING_FIELDS"
        assert isinstance(BaseCRUD.CLICKHOUSE_STRING_FIELDS, list)


# ===========================================================================
# 4. Method availability — _Streaming methods
# ===========================================================================


class TestStreamingMethods:
    """流式查询方法必须在 BaseCRUD 上仍可访问。"""

    STREAMING_METHODS = [
        "stream_find",
        "stream_find_with_progress",
        "stream_find_resumable",
        "stream_find_with_detailed_progress",
        "stream_find_with_monitoring",
        "is_streaming_enabled",
        "enable_streaming",
        "disable_streaming",
        "get_streaming_metrics",
        "get_streaming_session_metrics",
        "get_checkpoint_status",
        "list_checkpoints",
        "delete_checkpoint",
        "get_memory_statistics",
        "optimize_streaming_resources",
        "enable_memory_monitoring",
        "disable_memory_monitoring",
        "_initialize_streaming",
        "_get_streaming_engine",
        "_build_streaming_query",
        "_fallback_to_traditional_query",
        "_adjust_filters_for_resume",
        "_save_checkpoint_progress",
        "_estimate_total_records",
    ]

    @pytest.mark.tdd
    @pytest.mark.refactor
    @pytest.mark.parametrize("method_name", STREAMING_METHODS)
    def test_streaming_method_available(self, method_name):
        BaseCRUD = _get_base_crud()
        assert hasattr(BaseCRUD, method_name), f"BaseCRUD missing method: {method_name}"
        assert callable(getattr(BaseCRUD, method_name)), f"BaseCRUD.{method_name} is not callable"


# ===========================================================================
# 5. Method availability — Core CRUD methods
# ===========================================================================


class TestCoreCRUDMethods:
    """核心 CRUD 方法必须在 BaseCRUD 上仍可访问。"""

    CORE_METHODS = [
        "add", "add_batch", "create", "find", "remove", "modify",
        "replace", "count", "exists", "soft_remove",
        "_do_add", "_do_add_batch", "_do_find", "_do_remove",
        "_do_modify", "_do_count", "_do_exists", "_do_soft_remove",
        "_parse_filters", "_get_connection", "get_session",
    ]

    @pytest.mark.tdd
    @pytest.mark.refactor
    @pytest.mark.parametrize("method_name", CORE_METHODS)
    def test_core_method_available(self, method_name):
        BaseCRUD = _get_base_crud()
        assert hasattr(BaseCRUD, method_name), f"BaseCRUD missing method: {method_name}"
        assert callable(getattr(BaseCRUD, method_name)), f"BaseCRUD.{method_name} is not callable"


# ===========================================================================
# 6. BaseCRUD properties
# ===========================================================================


class TestBaseCRUDProperties:
    """BaseCRUD 必须保持 ABC 和 Generic 特性。"""

    @pytest.mark.tdd
    @pytest.mark.refactor
    def test_basecrud_is_abstract(self):
        BaseCRUD = _get_base_crud()
        assert issubclass(BaseCRUD, ABC)

    @pytest.mark.tdd
    @pytest.mark.refactor
    def test_basecrud_is_generic(self):
        BaseCRUD = _get_base_crud()
        assert issubclass(BaseCRUD, Generic)


# ===========================================================================
# 7. Concrete subclass compatibility
# ===========================================================================


class TestConcreteSubclassCompatibility:
    """具体 CRUD 子类必须在重构后仍正常工作。"""

    @pytest.mark.tdd
    @pytest.mark.refactor
    def test_bar_crud_is_subclass_of_base_crud(self):
        BarCRUD = _import_or_skip("ginkgo.data.crud", "BarCRUD")
        BaseCRUD = _get_base_crud()
        assert issubclass(BarCRUD, BaseCRUD)

    @pytest.mark.tdd
    @pytest.mark.refactor
    def test_bar_crud_inherits_core_methods(self):
        BarCRUD = _import_or_skip("ginkgo.data.crud", "BarCRUD")
        for method in ["add", "find", "remove", "modify", "count"]:
            assert hasattr(BarCRUD, method), f"BarCRUD missing core method: {method}"

    @pytest.mark.tdd
    @pytest.mark.refactor
    def test_bar_crud_inherits_streaming_methods(self):
        BarCRUD = _import_or_skip("ginkgo.data.crud", "BarCRUD")
        assert hasattr(BarCRUD, "stream_find"), "BarCRUD missing stream_find"

    @pytest.mark.tdd
    @pytest.mark.refactor
    def test_bar_crud_inherits_conversion_methods(self):
        BarCRUD = _import_or_skip("ginkgo.data.crud", "BarCRUD")
        assert hasattr(BarCRUD, "_convert_output_items"), "BarCRUD missing _convert_output_items"
        assert hasattr(BarCRUD, "_create_from_params"), "BarCRUD missing _create_from_params"

    @pytest.mark.tdd
    @pytest.mark.refactor
    def test_bar_crud_mro_contains_base_crud(self):
        BarCRUD = _import_or_skip("ginkgo.data.crud", "BarCRUD")
        BaseCRUD = _get_base_crud()
        assert BaseCRUD in BarCRUD.__mro__

    @pytest.mark.tdd
    @pytest.mark.refactor
    def test_order_crud_is_subclass_of_base_crud(self):
        OrderCRUD = _import_or_skip("ginkgo.data.crud", "OrderCRUD")
        BaseCRUD = _get_base_crud()
        assert issubclass(OrderCRUD, BaseCRUD)

    @pytest.mark.tdd
    @pytest.mark.refactor
    def test_signal_crud_is_subclass_of_base_crud(self):
        SignalCRUD = _import_or_skip("ginkgo.data.crud", "SignalCRUD")
        BaseCRUD = _get_base_crud()
        assert issubclass(SignalCRUD, BaseCRUD)


# ===========================================================================
# 8. CRUDResult 已下线（issue #6628 / ADR-010 收口）
# ===========================================================================


class TestCRUDResultRemoved:
    """AC #6628 ①: CRUDResult 不再作为与 ModelList 并行的结果协议存在。"""

    @pytest.mark.tdd
    @pytest.mark.refactor
    def test_crud_result_not_exported_from_base_crud(self):
        import ginkgo.data.crud.base_crud as base_crud_module

        assert not hasattr(base_crud_module, "CRUDResult"), (
            "CRUDResult 应已从 base_crud 下线（#6628），"
            "数据层只保留 ModelList 单一结果协议"
        )
