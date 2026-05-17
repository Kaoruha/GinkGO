"""
TDD RED: BaseCRUD Mixin 组合 characterization test

验证 BaseCRUD 拆分为 CoreCRUD + ConversionMixin + ValidationMixin + StreamingMixin
后的向后兼容性。此文件在 Mixin 类创建前为 SKIP 状态（RED phase），
重构完成后应全部 PASS（GREEN phase）。

Related: #3833
"""

import pytest
from abc import ABC


# ---------------------------------------------------------------------------
# Helpers: safe import with skip
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
    """Import BaseCRUD, skip if the import chain fails."""
    return _import_or_skip("ginkgo.data.crud.base_crud", "BaseCRUD")


# ===========================================================================
# 1. MRO correctness
# ===========================================================================


class TestMROCorrectness:
    """Refactor 后 BaseCRUD 的 MRO 必须包含 CoreCRUD 和三个 Mixin。"""

    @pytest.mark.tdd
    @pytest.mark.refactor
    def test_mro_contains_core_crud(self):
        BaseCRUD = _get_base_crud()
        CoreCRUD = _import_or_skip("ginkgo.data.crud.base_crud", "CoreCRUD")

        assert CoreCRUD in BaseCRUD.__mro__, (
            f"CoreCRUD not in BaseCRUD MRO: {[c.__name__ for c in BaseCRUD.__mro__]}"
        )

    @pytest.mark.tdd
    @pytest.mark.refactor
    def test_mro_contains_conversion_mixin(self):
        BaseCRUD = _get_base_crud()
        ConversionMixin = _import_or_skip(
            "ginkgo.data.crud.mixins.conversion_mixin", "ConversionMixin"
        )

        assert ConversionMixin in BaseCRUD.__mro__, (
            f"ConversionMixin not in BaseCRUD MRO: {[c.__name__ for c in BaseCRUD.__mro__]}"
        )

    @pytest.mark.tdd
    @pytest.mark.refactor
    def test_mro_contains_validation_mixin(self):
        BaseCRUD = _get_base_crud()
        ValidationMixin = _import_or_skip(
            "ginkgo.data.crud.mixins.validation_mixin", "ValidationMixin"
        )

        assert ValidationMixin in BaseCRUD.__mro__, (
            f"ValidationMixin not in BaseCRUD MRO: {[c.__name__ for c in BaseCRUD.__mro__]}"
        )

    @pytest.mark.tdd
    @pytest.mark.refactor
    def test_mro_contains_streaming_mixin(self):
        BaseCRUD = _get_base_crud()
        StreamingMixin = _import_or_skip(
            "ginkgo.data.crud.mixins.streaming_mixin", "StreamingMixin"
        )

        assert StreamingMixin in BaseCRUD.__mro__, (
            f"StreamingMixin not in BaseCRUD MRO: {[c.__name__ for c in BaseCRUD.__mro__]}"
        )

    @pytest.mark.tdd
    @pytest.mark.refactor
    def test_mro_order_core_before_mixins(self):
        """CoreCRUD 必须在 Mixin 之前出现（CoreCRUD 负责核心 CRUD 操作）。"""
        BaseCRUD = _get_base_crud()
        # 只要 BaseCRUD 能导入，CoreCRUD 和 Mixin 也一定能导入
        mro_names = [c.__name__ for c in BaseCRUD.__mro__]
        assert "CoreCRUD" in mro_names, (
            f"CoreCRUD not found in MRO: {mro_names}"
        )
        assert "ConversionMixin" in mro_names, (
            f"ConversionMixin not found in MRO: {mro_names}"
        )
        core_idx = mro_names.index("CoreCRUD")
        conversion_idx = mro_names.index("ConversionMixin")
        assert core_idx < conversion_idx, (
            f"CoreCRUD (idx={core_idx}) should appear before ConversionMixin (idx={conversion_idx})"
        )


# ===========================================================================
# 2. Method availability — ConversionMixin methods
# ===========================================================================


class TestConversionMixinMethods:
    """ConversionMixin 提取的方法必须在 BaseCRUD 上仍可访问。"""

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

        assert hasattr(BaseCRUD, method_name), (
            f"BaseCRUD missing method: {method_name}"
        )
        assert callable(getattr(BaseCRUD, method_name)), (
            f"BaseCRUD.{method_name} is not callable"
        )


# ===========================================================================
# 3. Method availability — ValidationMixin methods
# ===========================================================================


class TestValidationMixinMethods:
    """ValidationMixin 提取的方法必须在 BaseCRUD 上仍可访问。"""

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

        assert hasattr(BaseCRUD, method_name), (
            f"BaseCRUD missing method: {method_name}"
        )
        assert callable(getattr(BaseCRUD, method_name)), (
            f"BaseCRUD.{method_name} is not callable"
        )

    @pytest.mark.tdd
    @pytest.mark.refactor
    def test_clickhouse_string_fields_class_attribute(self):
        """CLICKHOUSE_STRING_FIELDS 类属性必须在 BaseCRUD 上保留。"""
        BaseCRUD = _get_base_crud()

        assert hasattr(BaseCRUD, "CLICKHOUSE_STRING_FIELDS"), (
            "BaseCRUD missing CLICKHOUSE_STRING_FIELDS"
        )
        assert isinstance(BaseCRUD.CLICKHOUSE_STRING_FIELDS, list)


# ===========================================================================
# 4. Method availability — StreamingMixin methods
# ===========================================================================


class TestStreamingMixinMethods:
    """StreamingMixin 提取的方法必须在 BaseCRUD 上仍可访问。"""

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
        # Internal streaming helpers
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

        assert hasattr(BaseCRUD, method_name), (
            f"BaseCRUD missing method: {method_name}"
        )
        assert callable(getattr(BaseCRUD, method_name)), (
            f"BaseCRUD.{method_name} is not callable"
        )


# ===========================================================================
# 5. Method availability — CoreCRUD methods
# ===========================================================================


class TestCoreCRUDMethods:
    """CoreCRUD 的核心 CRUD 方法必须在 BaseCRUD 上仍可访问。"""

    CORE_METHODS = [
        "add",
        "add_batch",
        "create",
        "find",
        "remove",
        "modify",
        "replace",
        "count",
        "exists",
        "soft_remove",
        # Internal core helpers
        "_do_add",
        "_do_add_batch",
        "_do_find",
        "_do_remove",
        "_do_modify",
        "_do_count",
        "_do_exists",
        "_do_soft_remove",
        "_parse_filters",
        "_get_connection",
        "get_session",
    ]

    @pytest.mark.tdd
    @pytest.mark.refactor
    @pytest.mark.parametrize("method_name", CORE_METHODS)
    def test_core_method_available(self, method_name):
        BaseCRUD = _get_base_crud()

        assert hasattr(BaseCRUD, method_name), (
            f"BaseCRUD missing method: {method_name}"
        )
        assert callable(getattr(BaseCRUD, method_name)), (
            f"BaseCRUD.{method_name} is not callable"
        )


# ===========================================================================
# 6. isinstance / issubclass checks
# ===========================================================================


class TestInstanceChecks:
    """BaseCRUD 必须是各 Mixin 和 CoreCRUD 的子类。"""

    @pytest.mark.tdd
    @pytest.mark.refactor
    def test_basecrud_subclass_of_core_crud(self):
        BaseCRUD = _get_base_crud()
        CoreCRUD = _import_or_skip("ginkgo.data.crud.base_crud", "CoreCRUD")

        assert issubclass(BaseCRUD, CoreCRUD)

    @pytest.mark.tdd
    @pytest.mark.refactor
    def test_basecrud_subclass_of_conversion_mixin(self):
        BaseCRUD = _get_base_crud()
        ConversionMixin = _import_or_skip(
            "ginkgo.data.crud.mixins.conversion_mixin", "ConversionMixin"
        )

        assert issubclass(BaseCRUD, ConversionMixin)

    @pytest.mark.tdd
    @pytest.mark.refactor
    def test_basecrud_subclass_of_validation_mixin(self):
        BaseCRUD = _get_base_crud()
        ValidationMixin = _import_or_skip(
            "ginkgo.data.crud.mixins.validation_mixin", "ValidationMixin"
        )

        assert issubclass(BaseCRUD, ValidationMixin)

    @pytest.mark.tdd
    @pytest.mark.refactor
    def test_basecrud_subclass_of_streaming_mixin(self):
        BaseCRUD = _get_base_crud()
        StreamingMixin = _import_or_skip(
            "ginkgo.data.crud.mixins.streaming_mixin", "StreamingMixin"
        )

        assert issubclass(BaseCRUD, StreamingMixin)

    @pytest.mark.tdd
    @pytest.mark.refactor
    def test_basecrud_still_abstract(self):
        """BaseCRUD should remain abstract (ABC) after refactoring."""
        BaseCRUD = _get_base_crud()

        assert issubclass(BaseCRUD, ABC)

    @pytest.mark.tdd
    @pytest.mark.refactor
    def test_basecrud_still_generic(self):
        """BaseCRUD should still be parameterizable with Generic[T]."""
        from typing import Generic
        BaseCRUD = _get_base_crud()

        assert issubclass(BaseCRUD, Generic)


# ===========================================================================
# 7. Concrete subclass compatibility
# ===========================================================================


class TestConcreteSubclassCompatibility:
    """Concrete CRUD 子类（如 BarCRUD）必须在重构后仍正常工作。"""

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
        assert hasattr(BarCRUD, "is_streaming_enabled"), (
            "BarCRUD missing is_streaming_enabled"
        )

    @pytest.mark.tdd
    @pytest.mark.refactor
    def test_bar_crud_inherits_conversion_methods(self):
        BarCRUD = _import_or_skip("ginkgo.data.crud", "BarCRUD")

        assert hasattr(BarCRUD, "_convert_output_items"), (
            "BarCRUD missing _convert_output_items"
        )
        assert hasattr(BarCRUD, "_create_from_params"), (
            "BarCRUD missing _create_from_params"
        )

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
# 8. CRUDResult still works
# ===========================================================================


class TestCRUDResultCompatibility:
    """CRUDResult 必须从 base_crud 模块继续可导入。"""

    @pytest.mark.tdd
    @pytest.mark.refactor
    def test_crud_result_importable(self):
        CRUDResult = _import_or_skip("ginkgo.data.crud.base_crud", "CRUDResult")

        assert CRUDResult is not None

    @pytest.mark.tdd
    @pytest.mark.refactor
    def test_crud_result_has_expected_methods(self):
        CRUDResult = _import_or_skip("ginkgo.data.crud.base_crud", "CRUDResult")

        for method in ["to_business_objects", "to_dataframe", "first", "count", "__len__"]:
            assert hasattr(CRUDResult, method), (
                f"CRUDResult missing method: {method}"
            )


# ===========================================================================
# 9. Mixin imports from package
# ===========================================================================


class TestMixinPackageImports:
    """Mixin 类必须从 ginkgo.data.crud.mixins 包可导入。"""

    @pytest.mark.tdd
    @pytest.mark.refactor
    def test_import_conversion_mixin_from_package(self):
        ConversionMixin = _import_or_skip(
            "ginkgo.data.crud.mixins", "ConversionMixin"
        )
        assert ConversionMixin is not None

    @pytest.mark.tdd
    @pytest.mark.refactor
    def test_import_validation_mixin_from_package(self):
        ValidationMixin = _import_or_skip(
            "ginkgo.data.crud.mixins", "ValidationMixin"
        )
        assert ValidationMixin is not None

    @pytest.mark.tdd
    @pytest.mark.refactor
    def test_import_streaming_mixin_from_package(self):
        StreamingMixin = _import_or_skip(
            "ginkgo.data.crud.mixins", "StreamingMixin"
        )
        assert StreamingMixin is not None

    @pytest.mark.tdd
    @pytest.mark.refactor
    def test_core_crud_importable_from_base_crud(self):
        CoreCRUD = _import_or_skip("ginkgo.data.crud.base_crud", "CoreCRUD")
        assert CoreCRUD is not None
